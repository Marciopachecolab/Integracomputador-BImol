"""
Modulo oficial para formatacao GAL (fonte unica de verdade).

Importante:
- Nao implementar formatacao GAL fora deste modulo.

Responsabilidades:
- Formatar DataFrames de resultados para o contrato GAL.
- Aplicar metadados de exame (exam_cfg) para mapeamento.
- Gerar CSVs oficiais de envio ao GAL.
- Validar formato de saida conforme contrato.
"""

import os
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from services.contract_catalog import get_contract_catalog
from services.core.config_service import config_service
from services.exam_registry import get_exam_cfg
from services.core.runtime_flags import is_contractual_csv_legacy_fallback_enabled
from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, open_with_retry
from utils.logger import registrar_log
from utils.text_result_classifier import result_text_to_gal_code

_GAL_BASE_COLUMNS: tuple[str, ...] = (
    "codigoAmostra",
    "codigo",
    "requisicao",
    "paciente",
    "exame",
    "metodo",
    "registroInterno",
    "kit",
    "reteste",
    "loteKit",
    "dataProcessamentoFim",
    "valorReferencia",
    "observacao",
    "painel",
    "resultado",
)

_DEFAULT_EXPORT_FIELDS: tuple[str, ...] = (
    "Influenzaa",
    "influenzab",
    "coronavirusncov",
    "adenovirus",
    "vsincicialresp",
    "metapneumovirus",
    "rinovirus",
)
_TARGET_ALIASES: dict[str, str] = {
    "INFLUENZAA": "INF A",
    "INFLUENZAB": "INF B",
    "ADENOVIRUS": "ADV",
    "METAPNEUMOVIRUS": "HMPV",
    "RINOVIRUS": "HRV",
    "SARS-COV-2": "SC2",
    "SARSCOV2": "SC2",
    "CORONAVIRUSNCOV": "SC2",
    "VSINCICIALRESP": "RSV",
    "VSINCICIALRESPA": "RSV",
    "VSINCICIALRESPB": "RSV",
    "VSR": "RSV",
}


@dataclass(frozen=True)
class GalCsvExportResult:
    """Resultado da exportacao oficial de CSV GAL."""

    dataframe: pd.DataFrame
    gal_path: str
    gal_last_path: str


def _resolve_exam_cfg(exam_cfg=None, exame: str | None = None):
    return exam_cfg or (get_exam_cfg(exame) if exame else get_exam_cfg(""))


def _strip_accents(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("ASCII")


def _normalize_export_column_name(value: str) -> str:
    """Normaliza o nome de coluna exportavel para o contrato GAL."""
    return (
        _strip_accents(str(value))
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .lower()
    )


def _normalize_v2_ct_column_name(value: str, *, fallback_field: str) -> str:
    raw = str(value or "").strip() or f"{fallback_field}_ct"
    return (
        _strip_accents(raw)
        .replace(" ", "_")
        .replace("-", "_")
        .lower()
    )


def _resolve_gal_contract_runtime(cfg) -> dict[str, Any]:
    profile: dict[str, Any] = {}
    exam_ref = getattr(cfg, "nome_exame", "") or getattr(cfg, "exam_id", "") or getattr(cfg, "slug", "")
    profile_id = getattr(cfg, "gal_profile_id", "") or exam_ref

    try:
        catalog = get_contract_catalog()
        if profile_id:
            profile = dict(catalog.get_gal_profile(profile_id) or {})
        if not profile and exam_ref:
            bundle = catalog.resolve_runtime_bundle(exam_name=exam_ref)
            profile = dict(bundle.gal_profile or {})
    except Exception as exc:
        registrar_log("GAL Contract", f"Falha ao resolver gal_profile contratual: {exc}", "WARNING")

    export_fields = [str(item) for item in (profile.get("export_fields") or cfg.export_fields or []) if str(item).strip()]
    if not export_fields:
        export_fields = list(_DEFAULT_EXPORT_FIELDS)

    policy = profile.get("csv_schema_policy") or {}
    compatibility_mode = str(policy.get("compatibility_mode", "")).strip().lower()
    fallback_enabled = is_contractual_csv_legacy_fallback_enabled()
    schema_version = str(profile.get("csv_schema_version") or policy.get("active_version") or "1.0.0")
    if fallback_enabled:
        schema_version = str(policy.get("fallback_version") or policy.get("active_version") or "1.0.0")
    elif compatibility_mode == "dual_v1_v2" and profile.get("export_field_pairs"):
        schema_version = str(policy.get("candidate_version") or profile.get("csv_schema_version") or "2.0.0")

    export_field_pairs = [
        item for item in (profile.get("export_field_pairs") or []) if isinstance(item, dict)
    ]
    use_v2_pairs = bool(export_field_pairs) and str(schema_version).startswith("2") and not fallback_enabled
    return {
        "profile": profile,
        "schema_version": schema_version,
        "export_fields": export_fields,
        "export_field_pairs": export_field_pairs,
        "compatibility_mode": compatibility_mode,
        "fallback_enabled": fallback_enabled,
        "use_v2_pairs": use_v2_pairs,
    }


def _get_export_fields(cfg, contract_runtime: dict[str, Any] | None = None) -> list[str]:
    runtime_fields = []
    if contract_runtime:
        runtime_fields = [str(item) for item in (contract_runtime.get("export_fields") or []) if str(item).strip()]
    export_fields = runtime_fields or list(cfg.export_fields or [])
    if not export_fields:
        return list(_DEFAULT_EXPORT_FIELDS)
    return export_fields


def obter_colunas_contrato_gal(exam_cfg=None, exame: str | None = None) -> list[str]:
    """
    Retorna o schema canonico (ordenado) do CSV GAL para o exame.

    O contrato e composto por colunas base + colunas de analitos exportaveis.
    """
    cfg = _resolve_exam_cfg(exam_cfg=exam_cfg, exame=exame)
    contract_runtime = _resolve_gal_contract_runtime(cfg)
    columns = list(_GAL_BASE_COLUMNS)
    seen = set(columns)
    if contract_runtime.get("use_v2_pairs"):
        for pair in contract_runtime.get("export_field_pairs", []):
            field = str(pair.get("field", "")).strip()
            if not field:
                continue
            result_col = _normalize_export_column_name(field)
            ct_col = _normalize_v2_ct_column_name(
                pair.get("ct_field", ""),
                fallback_field=result_col,
            )
            for col_name in (result_col, ct_col):
                if col_name not in seen:
                    columns.append(col_name)
                    seen.add(col_name)
    else:
        for analito in _get_export_fields(cfg, contract_runtime=contract_runtime):
            col_name = _normalize_export_column_name(analito)
            if col_name not in seen:
                columns.append(col_name)
                seen.add(col_name)
    return columns


def _resolve_reports_dir(reports_dir: str | None) -> str:
    if reports_dir:
        return reports_dir
    try:
        paths = config_service.get_paths()
        return paths.get("reports_dir") or paths.get("default_results_folder") or "reports"
    except Exception:
        return "reports"


def _write_gal_csv(
    df_gal: pd.DataFrame,
    path: str,
    policy: RetryPolicy,
    *,
    sep: str = ",",
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f"{target.name}.{uuid.uuid4().hex}.tmp")

    try:
        with CSVFileLock(target), open_with_retry(
            tmp,
            "w",
            newline="",
            encoding="utf-8",
            policy=policy,
        ) as handle:
            # Contrato operacional: UTF-8 sem BOM e schema canonico ordenado.
            df_gal.to_csv(handle, index=False, sep=sep)
        os.replace(tmp, target)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def _normalize_lookup_key(column: str) -> str:
    return _strip_accents(str(column).strip()).replace(" ", "_").lower()


def _clean_result_lookup_key(value: str) -> str:
    return (
        _strip_accents(str(value))
        .upper()
        .replace("RESULTADO", "")
        .replace("_", "")
        .replace(" ", "")
    )


def _prepare_input_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    df_in = df.copy()
    for column in ("Unnamed: 0", "index"):
        if column in df_in.columns:
            df_in = df_in.drop(columns=[column])
    return df_in, {_normalize_lookup_key(col): col for col in df_in.columns}


def _get_input_series(
    df_in: pd.DataFrame,
    colmap: dict[str, str],
    candidate_names: list[str],
    *,
    default: str = "",
) -> pd.Series:
    for name in candidate_names:
        key = _normalize_lookup_key(name)
        if key in colmap:
            return df_in[colmap[key]]
    return pd.Series([default] * len(df_in))


def _find_source_column_by_candidates(
    colmap: dict[str, str],
    candidate_names: list[str],
) -> str | None:
    for name in candidate_names:
        key = _normalize_lookup_key(name)
        if key in colmap:
            return colmap[key]
    return None


def _resolve_exam_export_value(cfg) -> str:
    return getattr(cfg, "gal_exame_codigo", "") or cfg.nome_exame or "VRSRT"


def _build_base_dataframe(
    *,
    cfg,
    cod_col: pd.Series,
    exam_value: str,
    panel_value: str,
    lote_kit: str = "",
) -> pd.DataFrame:
    df_out = pd.DataFrame()
    df_out["codigoAmostra"] = cod_col
    df_out["codigo"] = cod_col
    df_out["requisicao"] = ""
    df_out["paciente"] = ""
    df_out["exame"] = exam_value
    df_out["metodo"] = "RTTR"
    df_out["registroInterno"] = cod_col
    df_out["kit"] = str(getattr(cfg, "kit_codigo", "1175") or "1175")
    df_out["reteste"] = ""
    df_out["loteKit"] = str(lote_kit or "")
    df_out["dataProcessamentoFim"] = datetime.now().strftime("%d/%m/%Y")
    df_out["valorReferencia"] = ""
    df_out["observacao"] = ""
    df_out["painel"] = panel_value
    df_out["resultado"] = ""
    return df_out


def _find_result_col(*, target_name: str, cfg, colmap: dict[str, str]) -> str | None:
    target_raw = (
        _strip_accents(str(target_name))
        .upper()
        .replace("_", " ")
        .replace("-", " ")
        .strip()
    )
    target_alias = _TARGET_ALIASES.get(target_raw, target_raw)
    normalized_target = cfg.normalize_target(target_alias).upper()
    normalized_target_key = _clean_result_lookup_key(normalized_target)

    for key, original in colmap.items():
        if _clean_result_lookup_key(key) == normalized_target_key:
            return original

    for prefix in ("Res_", "Resultado_"):
        candidate = f"{prefix}{normalized_target}"
        candidate_key = _clean_result_lookup_key(candidate)
        for key, original in colmap.items():
            if _clean_result_lookup_key(key) == candidate_key:
                return original
    return None


def _find_ct_col(*, target_name: str, cfg, colmap: dict[str, str]) -> str | None:
    target_raw = (
        _strip_accents(str(target_name))
        .upper()
        .replace("_", " ")
        .replace("-", " ")
        .strip()
    )
    target_alias = _TARGET_ALIASES.get(target_raw, target_raw)
    normalized_target = cfg.normalize_target(target_alias).upper()
    target_compact = normalized_target.replace(" ", "").replace("_", "")
    candidates = [
        f"CT_{normalized_target}",
        f"CT_{normalized_target.replace(' ', '_')}",
        f"CT_{target_compact}",
        f"CQ_{normalized_target}",
        f"CQ_{normalized_target.replace(' ', '_')}",
        f"CQ_{target_compact}",
        f"Cq_{normalized_target}",
        f"Cq_{normalized_target.replace(' ', '_')}",
        f"Cq_{target_compact}",
    ]
    return _find_source_column_by_candidates(colmap, candidates)


def _find_pair_by_field(contract_runtime: dict[str, Any], field_name: str) -> dict[str, Any] | None:
    token = _normalize_export_column_name(field_name)
    for pair in contract_runtime.get("export_field_pairs", []):
        pair_field = str(pair.get("field", "")).strip()
        if pair_field and _normalize_export_column_name(pair_field) == token:
            return pair
    return None


def _is_exportable(code: str, cfg) -> bool:
    if not code:
        return False
    normalized = str(code).upper()
    try:
        controls = cfg.controles or {"cn": [], "cp": []}
        cn_list = [str(item).upper() for item in (controls.get("cn") or [])]
        cp_list = [str(item).upper() for item in (controls.get("cp") or [])]
        for token in cn_list + cp_list:
            if token and token in normalized:
                return False
    except Exception:
        if "CN" in normalized or "CP" in normalized:
            return False
    return normalized.isdigit()


def _build_gal_dataframe_core(
    df_resultados: pd.DataFrame,
    *,
    cfg,
    panel_value: str,
    exam_value: str,
    include_only_exportable: bool,
    emit_debug_logs: bool,
    contract_runtime: dict[str, Any] | None = None,
    lote_kit: str = "",
) -> pd.DataFrame:
    runtime = contract_runtime or _resolve_gal_contract_runtime(cfg)
    df_in, colmap = _prepare_input_frame(df_resultados)
    cod_col = _get_input_series(df_in, colmap, ["codigo", "amostra"])
    df_out = _build_base_dataframe(
        cfg=cfg,
        cod_col=cod_col,
        exam_value=exam_value,
        panel_value=panel_value,
        lote_kit=lote_kit,
    )

    if include_only_exportable:
        mask = cod_col.apply(lambda value: _is_exportable(value, cfg))
        df_out = df_out.loc[mask].reset_index(drop=True)
        df_in = df_in.loc[mask].reset_index(drop=True)

    if runtime.get("use_v2_pairs"):
        for pair in runtime.get("export_field_pairs", []):
            field = str(pair.get("field", "")).strip()
            if not field:
                continue
            canonical_target = str(pair.get("canonical_target", field)).strip() or field
            result_output = _normalize_export_column_name(field)
            ct_output = _normalize_v2_ct_column_name(pair.get("ct_field", ""), fallback_field=result_output)

            result_candidates = [str(item) for item in (pair.get("source_result_column_candidates") or [])]
            ct_candidates = [str(item) for item in (pair.get("source_ct_column_candidates") or [])]

            result_col = _find_source_column_by_candidates(colmap, result_candidates)
            if not result_col:
                result_col = _find_result_col(target_name=canonical_target, cfg=cfg, colmap=colmap)

            ct_col = _find_source_column_by_candidates(colmap, ct_candidates)
            if not ct_col:
                ct_col = _find_ct_col(target_name=canonical_target, cfg=cfg, colmap=colmap)

            result_series = (
                df_in[result_col].apply(result_text_to_gal_code)
                if result_col and result_col in df_in.columns
                else pd.Series([""] * len(df_in))
            )
            ct_series = (
                df_in[ct_col]
                if ct_col and ct_col in df_in.columns
                else pd.Series([""] * len(df_in))
            )

            if emit_debug_logs:
                registrar_log(
                    "GAL Debug",
                    (
                        f"Schema v2 '{field}' ({canonical_target}) -> "
                        f"resultado='{result_col}' ct='{ct_col}'"
                    ),
                    "DEBUG",
                )

            df_out[result_output] = result_series
            df_out[ct_output] = ct_series
    else:
        for analito in _get_export_fields(cfg, contract_runtime=runtime):
            normalized_target = cfg.normalize_target(analito)
            pair = _find_pair_by_field(runtime, analito)
            result_candidates = [str(item) for item in (pair or {}).get("source_result_column_candidates", [])]
            result_col = _find_source_column_by_candidates(colmap, result_candidates)
            if not result_col:
                result_col = _find_result_col(target_name=normalized_target, cfg=cfg, colmap=colmap)

            if result_col and result_col in df_in.columns:
                series = df_in[result_col].apply(result_text_to_gal_code)
            else:
                series = pd.Series([""] * len(df_in))

            if emit_debug_logs:
                registrar_log(
                    "GAL Debug",
                    (
                        f"Procurando '{analito}' -> normalizado: '{normalized_target}' "
                        f"-> coluna encontrada: '{result_col}'"
                    ),
                    "DEBUG",
                )
                if result_col and result_col in df_in.columns:
                    registrar_log(
                        "GAL Debug",
                        f"  -> Valores: {series.value_counts().to_dict()}",
                        "DEBUG",
                    )
                elif result_col:
                    registrar_log(
                        "GAL Debug",
                        (
                            f"  -> AVISO: Coluna '{result_col}' nao existe no DataFrame. "
                            f"Colunas disponiveis: {[col for col in df_in.columns if 'Resultado' in str(col)]}"
                        ),
                        "WARNING",
                    )
                else:
                    registrar_log(
                        "GAL Debug",
                        f"  -> AVISO: Nao encontrou coluna para '{normalized_target}'",
                        "WARNING",
                    )

            df_out[_normalize_export_column_name(analito)] = series

    return df_out


def exportar_csv_gal_oficial(
    df_resultados: pd.DataFrame,
    exam_cfg=None,
    exame: str | None = None,
    reports_dir: str | None = None,
    timestamp_utc: datetime | None = None,
    lote_kit: str = "",
) -> GalCsvExportResult:
    """
    Gera os dois artefatos oficiais de CSV GAL.

    Saidas:
    - `gal_<timestamp>Z_exame.csv`
    - `gal_last_exame.csv`
    """
    df_gal = formatar_para_gal(df_resultados, exam_cfg=exam_cfg, exame=exame, lote_kit=lote_kit)
    output_dir = _resolve_reports_dir(reports_dir)
    os.makedirs(output_dir, exist_ok=True)

    ts_ref = timestamp_utc or datetime.now(timezone.utc)
    ts = ts_ref.strftime("%Y%m%dT%H%M%SZ")
    gal_path = os.path.join(output_dir, f"gal_{ts}_exame.csv")
    gal_last_path = os.path.join(output_dir, "gal_last_exame.csv")
    policy = RetryPolicy.from_env()

    _write_gal_csv(df_gal, gal_path, policy)
    _write_gal_csv(df_gal, gal_last_path, policy)

    registrar_log("GAL Export", f"CSV GAL oficial gerado: {gal_path}", "INFO")
    return GalCsvExportResult(dataframe=df_gal, gal_path=gal_path, gal_last_path=gal_last_path)


def formatar_para_gal(df, exam_cfg=None, exame: str | None = None, lote_kit: str = ""):
    """
    Formata o resultado para layout GAL usando metadados do exame (registry).
    
    Args:
        df: DataFrame com resultados brutos
        exam_cfg: Configuracao do exame (ExamConfig object) - opcional
        exame: Nome do exame para buscar configuracao - opcional
        
    Returns:
        DataFrame formatado no padrao GAL com colunas:
        - codigoAmostra, codigo, requisicao, paciente, exame, metodo
        - registroInterno, kit, reteste, loteKit, dataProcessamentoFim
        - valorReferencia, observacao, painel, resultado
        - Colunas de alvos (influenzaa, influenzab, adenovirus, etc.)
    """
    cfg = _resolve_exam_cfg(exam_cfg=exam_cfg, exame=exame)
    contract_runtime = _resolve_gal_contract_runtime(cfg)
    df_out = _build_gal_dataframe_core(
        df_resultados=df,
        cfg=cfg,
        panel_value=cfg.panel_tests_id or "12",
        exam_value=_resolve_exam_export_value(cfg),
        include_only_exportable=True,
        emit_debug_logs=False,
        contract_runtime=contract_runtime,
        lote_kit=lote_kit,
    )

    contract_columns = obter_colunas_contrato_gal(exam_cfg=cfg)
    for column in contract_columns:
        if column not in df_out.columns:
            df_out[column] = ""

    extra_columns = [column for column in df_out.columns if column not in contract_columns]
    if extra_columns:
        registrar_log(
            "GAL Contract",
            f"Colunas fora do contrato foram descartadas: {extra_columns}",
            "WARNING",
        )

    return df_out[contract_columns]


def gerar_painel_csvs(df_resultados, exam_cfg=None, exame: str | None = None, output_dir: str | None = None, lote_kit: str = ""):
    """
    Gera CSVs separados por painel (panel_tests_id) usando export_fields do exam_cfg.
    
    Cada painel recebe um CSV com:
    - Colunas padrao (codigoAmostra, codigo, etc.)
    - Apenas alvos de export_fields correspondentes ao painel
    
    Args:
        df_resultados: DataFrame com resultados brutos
        exam_cfg: Configuracao do exame (ExamConfig object) - opcional
        exame: Nome do exame para buscar configuracao - opcional
        output_dir: Diretorio de saida (padrao: reports/)
        
    Returns:
        dict {panel_id: caminho_arquivo}
    """
    if output_dir is None:
        try:
            paths = config_service.get_paths()
            output_dir = (
                paths.get("default_results_folder")
                or paths.get("reports_dir")
                or "reports"
            )
        except Exception:
            output_dir = "reports"
    os.makedirs(output_dir, exist_ok=True)

    cfg = exam_cfg or (get_exam_cfg(exame) if exame else get_exam_cfg(""))
    contract_runtime = _resolve_gal_contract_runtime(cfg)
    panel_id = cfg.panel_tests_id or "12"
    df_painel = _build_gal_dataframe_core(
        df_resultados=df_resultados,
        cfg=cfg,
        panel_value=panel_id,
        exam_value=cfg.nome_exame or "VRSRT",
        include_only_exportable=False,
        emit_debug_logs=False,
        contract_runtime=contract_runtime,
        lote_kit=lote_kit,
    )

    ts = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    painel_path = os.path.join(output_dir, f"painel_{panel_id}_{ts}_exame.csv")
    policy = RetryPolicy.from_env()
    _write_gal_csv(df_painel, painel_path, policy, sep=";")

    return {panel_id: painel_path}
