"""

Ajustes no AnalysisService para suportar o motor de analise.

Este módulo define o serviço de análise de placas, centralizando:

- Carregamento de arquivos de resultados e extração

- Chamada do motor de analise (services.engine.analysis_engine)

- Interação com o AppState

- Integração com cadastros (exames_config, regras, etc.)

"""



from __future__ import annotations



import datetime
import time

from dataclasses import dataclass

from pathlib import Path

from typing import Any, Dict, Iterable, List, Optional



import pandas as pd
import numpy as np



from models import AppState

from services.contract_catalog import get_contract_catalog
from services.core.config_loader import carregar_exames_metadata
from services.analysis.analysis_helpers import identificar_colunas_pcr, canonicalizar_alvo_pcr

from services.engine.analysis_engine import AnalysisEngine

from services.system_paths import BASE_DIR

from services.core.runtime_flags import (
    is_contract_analysis_runtime_enabled,
    is_analysis_exams_registry_read_enabled,
    is_analysis_runtime_registry_rules_enabled,
    is_contract_parser_enabled,
)
from services.exam_catalog_availability import (
    build_availability_report,
    persist_availability_report,
)
from services.analysis.analysis_runtime_contract import (
    build_runtime_rule_profile_from_cfg,
    classify_ct_with_runtime_profile,
    safe_float as runtime_safe_float,
)
from services.analysis.analysis_runtime_observability import (
    build_runtime_parity_report,
    build_runtime_promotion_gate,
    persist_runtime_parity_report,
    persist_runtime_promotion_gate,
)
from services.analysis.analysis_runtime_rollout import (
    build_runtime_cutover_audit,
    build_runtime_rollout_stage_audit,
    build_runtime_rollout_audit,
    build_runtime_stabilization_closure_audit,
    persist_runtime_cutover_audit,
    persist_runtime_rollout_stage_audit,
    persist_runtime_rollout_audit,
    persist_runtime_stabilization_closure_audit,
    resolve_runtime_rollout_decision,
)
from services.exam_registry import get_exam_cfg
# from config.business_rules import ... (REMOVED - Logic Centralized)
from services.analysis.logic_engine import classificar_ct
from config.business_rules import CT_MIN_RP_VALIDO, CT_MAX_RP_VALIDO

from utils.dataframe_validator import validate_merge_quality, log_unmapped_details
from utils.io_utils import read_data_with_auto_detection
from utils.text_normalizer import _normalize_col_key

from utils.logger import registrar_log
from domain.resultado_geral import (
    RESULTADO_INVALIDO,
    RESULTADO_INDETERMINADO,
    RESULTADO_INDETERMINADO_AMPL,
    RESULTADO_NAO_DETECTAVEL,
    is_amostra_vazia,
    is_amp_status_indeterminante,
    reclassificar_alvo_por_amp_status,
)





# ---------------------------------------------------------------------------

# Dataclasses de apoio

# ---------------------------------------------------------------------------





@dataclass

class AnaliseResultado:

    """

    Representa o resultado de uma análise de placa/protocolo.



    A ideia é encapsular, em um só objeto, os principais artefatos produzidos

    pela análise, mantendo compatibilidade com o que a UI espera.

    """



    df_processado: pd.DataFrame

    resumo: Dict[str, Any]

    metadados: Dict[str, Any]

    caminho_entrada_resultados: Optional[Path] = None

    caminho_entrada_extracao: Optional[Path] = None


class AnalysisCompletenessError(RuntimeError):
    """Erro fail-closed quando uma placa cheia perde grupos na análise."""


_VALIDO_LABELS = {"válido", "valido", "vã¡lido"}
_INVALIDO_LABELS = {"inválido", "invalido", "invã¡lido"}
_DETECTAVEL_LABELS = {"detectável", "detectavel", "detectã¡vel", "detectado"}
_NAO_DETECTAVEL_LABELS = {
    "não detectável",
    "nao detectavel",
    "nã£o detectã¡vel",
    "não detectavel",
    "nã£o detectavel",
}
_INDETERMINADO_LABELS = {"indeterminado", "inconclusivo", "inc"}
_SUGESTAO_REPETICAO_COLS = (
    "Sugest\u00e3o_de_repeti\u00e7\u00e3o",
    "Sugestao_de_repeticao",
    "Sugest\u00c3\u00a3o_de_repeti\u00c3\u00a7\u00c3\u00a3o",
)
_SUGESTAO_REPETICAO_CANONICAL = "Sugest\u00e3o_de_repeti\u00e7\u00e3o"
_SUGESTAO_REPETICAO_KEY = _normalize_col_key(_SUGESTAO_REPETICAO_CANONICAL)


def _normalize_text(value: Any) -> str:
    """Normaliza texto para comparacoes robustas entre variantes de encoding."""
    if pd.isna(value):
        return ""
    return str(value).strip().casefold()


def _is_indeterminado_label(value: Any) -> bool:
    """Reconhece um rotulo Indeterminado, inclusive o derivado "Indeterminado (ampl)"."""
    t = _normalize_text(value)
    return (
        t in _INDETERMINADO_LABELS
        or t.startswith("indeterminado")
        or t.startswith("inconclusivo")
    )


def _is_indeterminado_ampl_label(value: Any) -> bool:
    """True somente para o rotulo derivado de Amp Status (`Indeterminado (ampl)`)."""
    t = _normalize_text(value)
    return _is_indeterminado_label(t) and "ampl" in t


def _pick_existing_column(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _canonicalize_repetition_column(df_processado: pd.DataFrame) -> pd.DataFrame:
    """
    Canonicaliza coluna de sugestao de repeticao.

    Regra operacional:
    - Se houver duplicadas/aliases, manter o valor da coluna mais a direita.
    - Garantir apenas uma coluna canonica: ``Sugestão_de_repetição``.
    """
    if df_processado.empty and len(df_processado.columns) == 0:
        return df_processado

    original_cols = list(df_processado.columns)
    repeticao_cols = [
        col for col in original_cols if _normalize_col_key(col) == _SUGESTAO_REPETICAO_KEY
    ]
    if not repeticao_cols:
        return df_processado

    rightmost_col = repeticao_cols[-1]
    rightmost_series = df_processado[rightmost_col].copy()

    rightmost_idx = original_cols.index(rightmost_col)
    removed_before = sum(1 for col in repeticao_cols if original_cols.index(col) < rightmost_idx)
    insert_idx = max(0, rightmost_idx - removed_before)

    deduped = df_processado.drop(columns=repeticao_cols).copy()
    deduped.insert(min(insert_idx, len(deduped.columns)), _SUGESTAO_REPETICAO_CANONICAL, rightmost_series)
    return deduped


def _is_blank_series(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str).str.strip()
    return text == ""


def _is_rp_valid_series(series: pd.Series) -> pd.Series:
    return series.map(_normalize_text).isin(_VALIDO_LABELS)


def _apply_resultado_geral_vectorized(
    df_processado: pd.DataFrame,
    alvos_cols_res: List[str],
) -> pd.DataFrame:
    """
    Aplica preenchimento de ND e calcula Resultado_geral de forma vetorizada.

    Mantem o mesmo contrato funcional do fluxo legado:
    - RP invalido -> "Inválido", desmarca seleção
    - RP valido + alvo Indeterminado -> "Indeterminado", desmarca seleção, repetição "SIM"
    - RP valido + alvos Detectáveis -> "Detectável para ..."
    - RP valido + sem Detectáveis/Indeterminado -> "Não Detectável"
    """
    df_processado = _canonicalize_repetition_column(df_processado)

    if df_processado.empty:
        if "Resultado_geral" not in df_processado.columns:
            df_processado["Resultado_geral"] = pd.Series(dtype="object")
        return df_processado

    rp1 = df_processado.get("Res_RP_1", pd.Series("", index=df_processado.index))
    rp2 = df_processado.get("Res_RP_2", pd.Series("", index=df_processado.index))
    rp_valid_mask = _is_rp_valid_series(rp1) & _is_rp_valid_series(rp2)

    if alvos_cols_res:
        alvos_df = df_processado[alvos_cols_res].copy()
        blanks = alvos_df.apply(_is_blank_series)
        fill_mask = blanks & rp_valid_mask.to_numpy()[:, np.newaxis]
        alvos_df = alvos_df.mask(fill_mask, "Não detectável")
        df_processado.loc[:, alvos_cols_res] = alvos_df
    else:
        alvos_df = pd.DataFrame(index=df_processado.index)

    # Poco vazio (codigo em branco, "X" ou rotulo "Vazio...") e sempre Invalido,
    # para qualquer exame. Regra de dominio: domain.resultado_geral.is_amostra_vazia.
    amostra_series = df_processado.get(
        "Amostra", pd.Series("", index=df_processado.index)
    )
    amostra_vazia_mask = amostra_series.map(is_amostra_vazia)

    resultado_geral = pd.Series(RESULTADO_NAO_DETECTAVEL, index=df_processado.index, dtype="object")
    resultado_geral.loc[~rp_valid_mask] = RESULTADO_INVALIDO

    if not alvos_df.empty:
        alvos_norm = alvos_df.apply(lambda col: col.map(_normalize_text))
        indeterminado_matrix = alvos_norm.apply(lambda col: col.map(_is_indeterminado_label))
        has_indeterminado = indeterminado_matrix.any(axis=1)
        ampl_matrix = alvos_norm.apply(lambda col: col.map(_is_indeterminado_ampl_label))
        has_ampl = ampl_matrix.any(axis=1)
        detect_matrix = alvos_norm.isin(_DETECTAVEL_LABELS)
        has_detectavel = detect_matrix.any(axis=1)

        resultado_geral.loc[rp_valid_mask & has_indeterminado] = RESULTADO_INDETERMINADO
        # Quando a indeterminacao decorre da coluna Amp Status, preserva o rotulo
        # derivado "Indeterminado (ampl)" no Resultado_geral (grade e mapas).
        resultado_geral.loc[rp_valid_mask & has_ampl] = RESULTADO_INDETERMINADO_AMPL

        detect_idx = df_processado.index[rp_valid_mask & ~has_indeterminado & has_detectavel]
        if len(detect_idx) > 0:
            target_labels = (
                pd.Index(alvos_cols_res)
                .str.replace("Res_", "", regex=False)
                .str.replace("_", " ", regex=False)
                .tolist()
            )
            detect_np = detect_matrix.loc[detect_idx].to_numpy(dtype=bool)
            detect_text = []
            for row_mask in detect_np:
                selected = [target_labels[i] for i, flag in enumerate(row_mask) if flag]
                detect_text.append(f"Detectável para {', '.join(selected)}")
            resultado_geral.loc[detect_idx] = detect_text

        repeticao_col = _pick_existing_column(
            df_processado,
            (_SUGESTAO_REPETICAO_CANONICAL,),
        )
        if repeticao_col is None:
            repeticao_col = _SUGESTAO_REPETICAO_CANONICAL
            df_processado[repeticao_col] = "Não"
        df_processado.loc[rp_valid_mask & has_indeterminado, repeticao_col] = "SIM"

        if "Selecionado" not in df_processado.columns:
            df_processado.insert(0, "Selecionado", True)
        desmarcar_mask = ~rp_valid_mask
        df_processado.loc[desmarcar_mask, "Selecionado"] = False
        df_processado.loc[~desmarcar_mask, "Selecionado"] = True
    else:
        if "Selecionado" not in df_processado.columns:
            df_processado.insert(0, "Selecionado", True)
        df_processado.loc[~rp_valid_mask, "Selecionado"] = False
        df_processado.loc[rp_valid_mask, "Selecionado"] = True

    # Forca Invalido para pocos vazios, sobrepondo qualquer classificacao acima,
    # e remove-os da selecao de envio.
    if amostra_vazia_mask.any():
        resultado_geral.loc[amostra_vazia_mask] = RESULTADO_INVALIDO
        if "Selecionado" in df_processado.columns:
            df_processado.loc[amostra_vazia_mask, "Selecionado"] = False

    df_processado["Resultado_geral"] = resultado_geral
    return df_processado


def _avaliar_status_placa_vectorized(
    df_processado: pd.DataFrame,
    alvos_cols_res: List[str],
) -> str:
    """Avalia status de placa (CN/CP) sem iterar linha a linha."""
    if df_processado.empty:
        return "Indefinido"

    amostra = df_processado.get("Amostra", pd.Series("", index=df_processado.index)).fillna("").astype(str)
    cn_mask = amostra.str.contains("CN|CONTROLE.*NEG", case=False, na=False, regex=True)
    cp_mask = amostra.str.contains("CP|CONTROLE.*POS", case=False, na=False, regex=True)

    if not cn_mask.any() or not cp_mask.any():
        return "Indefinido"

    rp_cols = [col for col in df_processado.columns if col.startswith("Res_RP")]
    if not rp_cols:
        return "Inválida (RP ausente)"

    rp_valid_matrix = df_processado[rp_cols].apply(lambda col: col.map(_normalize_text).isin(_VALIDO_LABELS))
    rp_valid = rp_valid_matrix.all(axis=1)

    if alvos_cols_res:
        alvos_norm = df_processado[alvos_cols_res].apply(lambda col: col.map(_normalize_text))
        cn_ok = (rp_valid & alvos_norm.isin(_NAO_DETECTAVEL_LABELS).all(axis=1))[cn_mask].all()
        cp_ok = (rp_valid & alvos_norm.isin(_DETECTAVEL_LABELS).all(axis=1))[cp_mask].all()
    else:
        cn_ok = rp_valid[cn_mask].all()
        cp_ok = rp_valid[cp_mask].all()

    if cn_ok and cp_ok:
        return "Válida"

    motivos: List[str] = []
    if not cn_ok:
        motivos.append("CN incorreto")
    if not cp_ok:
        motivos.append("CP incorreto")
    return f"Inválida ({', '.join(motivos)})"


def _optimize_df_categorical_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Reduz memoria convertendo colunas textuais repetitivas para category.

    Nota:
        Colunas de resultado editaveis na UI (``Res_*`` e ``Resultado_*``)
        permanecem como ``object`` para evitar falhas ao atribuir novos labels
        que ainda nao existem no dominio categorico.
    """
    if df.empty:
        return df

    mutable_exact = {"Selecionado", "Resultado_geral", _SUGESTAO_REPETICAO_CANONICAL, "Sugestao_de_repeticao"}
    mutable_prefixes = ("Res_", "Resultado_")

    preferred = {"Status_Placa"}
    preferred.update({col for col in df.columns if col.startswith("Status_")})

    for col in df.columns:
        if col not in preferred:
            continue
        if col in mutable_exact or col.startswith(mutable_prefixes):
            continue
        if str(df[col].dtype) != "object":
            continue
        unique_count = df[col].nunique(dropna=False)
        if unique_count <= 1:
            df[col] = df[col].astype("category")
            continue
        # Colunas de resultado/status possuem dominio pequeno; category reduz memoria
        # mesmo quando a cardinalidade relativa e alta em DataFrames curtos.
        if unique_count <= 256:
            df[col] = df[col].astype("category")
    return df


# ---------------------------------------------------------------------------

# Classe principal AnalysisService

# ---------------------------------------------------------------------------





class AnalysisService:

    """

    Serviço de alto nível responsável por orquestrar a análise de placas.



    Ele faz a ponte entre:

    - AppState (estado global da aplicação)

    - Configurações de exames (banco/exames_config.csv e outros)

    - Motor de analise (AnalysisEngine)

    - Leitura dos arquivos de entrada (resultados e extração)

    """



    def __init__(self, app_state: AppState) -> None:

        self.app_state = app_state



        # Engine de analise que centraliza a logica principal
        # CORRIGIDO: AnalysisEngine nao aceita app_state no __init__
        self.engine = AnalysisEngine()



        # Cache de exames disponíveis (preenchido sob demanda)

        # O MenuHandler verifica se é None; se for, dispara o carregamento.

        self.exames_disponiveis: Optional[List[str]] = None



        # Ãšltimo resultado de análise realizado

        self.ultimo_resultado: Optional[AnaliseResultado] = None

        # Porta de extracao de equipamentos (Fase B)
        self._equipment_extraction_port = None
        self._exam_availability_samples_ms: List[float] = []
        self._exam_availability_slo_ms: float = 15.0 * 60.0 * 1000.0
        self._analysis_runtime_samples_ms: List[float] = []
        self._analysis_runtime_slo_ms: float = 15.0 * 60.0 * 1000.0



    # ------------------------------------------------------------------

    # API pública principal

    # ------------------------------------------------------------------

    def criar_orchestrator_port(self):

        """

        Retorna a implementacao inicial da porta de orquestracao (Fase B2-T01).

        """

        from application.analysis_orchestrator import AnalysisOrchestrator

        return AnalysisOrchestrator(
            app_state=self.app_state,
            analysis_service=self,
            runtime_flag_resolver=is_contract_analysis_runtime_enabled,
        )

    def _get_equipment_extraction_port(self):
        """Retorna porta de extracao de equipamentos (lazy)."""
        if self._equipment_extraction_port is None:
            from application.equipment_extraction_service import EquipmentExtractionService

            self._equipment_extraction_port = EquipmentExtractionService()
        return self._equipment_extraction_port



    def _listar_exames_legacy(self) -> List[str]:
        from services.exam_registry import registry as _reg
        config_exames = carregar_exames_metadata()
        all_names = sorted(str(name).strip() for name in config_exames.keys() if str(name).strip())
        # Se o registry ja foi carregado (tem exames), aplica filtro de ativos (fail-closed se vazio).
        # Se ainda nao foi carregado, devolve todos os legados como fallback.
        if _reg.exams:
            return [n for n in all_names if _reg.is_active(n)]
        return all_names

    def _listar_exames_registry_canonico(self) -> tuple[List[str], List[Any], List[str]]:
        from services.exam_registry import registry

        registry.load()
        cfgs = sorted(
            [cfg for cfg in registry.iter_active_exams() if str(getattr(cfg, "nome_exame", "")).strip()],
            key=lambda item: str(getattr(item, "nome_exame", "")).strip().lower(),
        )
        canonical = [str(cfg.nome_exame).strip() for cfg in cfgs]
        legacy = self._listar_exames_legacy()

        merged: List[str] = []
        seen: set[str] = set()
        for raw in canonical + legacy:
            name = str(raw or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(name)
        return merged, cfgs, legacy

    def _registrar_disponibilidade_e_paridade(
        self,
        *,
        source_mode: str,
        selected: List[str],
        registry_cfgs: List[Any],
        legacy_names: List[str],
        fetch_latency_ms: float,
    ) -> None:
        self._exam_availability_samples_ms.append(float(fetch_latency_ms))
        if len(self._exam_availability_samples_ms) > 200:
            self._exam_availability_samples_ms = self._exam_availability_samples_ms[-200:]

        report = build_availability_report(
            registry_configs=registry_cfgs,
            legacy_exam_names=legacy_names,
            selected_exam_names=selected,
            fetch_latency_ms=fetch_latency_ms,
            latency_samples_ms=self._exam_availability_samples_ms,
            p95_target_ms=self._exam_availability_slo_ms,
            source_mode=source_mode,
        )
        report_path = persist_availability_report(report)
        setattr(self.app_state, "exam_availability_report_path", str(report_path))
        setattr(self.app_state, "exam_availability_report", report)

    def listar_exames_disponiveis(self) -> List[str]:
        """
        Retorna a lista de exames disponiveis para selecao na analise.

        Quando a flag de rollout estiver ativa, usa o ExamRegistry como fonte
        canonica (V2), mantendo retrocompatibilidade com o catalogo legado.
        """
        started = time.perf_counter()
        usuario = getattr(self.app_state, "usuario_logado", None)

        try:
            if is_analysis_exams_registry_read_enabled(user_id=usuario):
                exames, cfgs, legacy = self._listar_exames_registry_canonico()
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                self._registrar_disponibilidade_e_paridade(
                    source_mode="registry_canonical_with_legacy_fallback",
                    selected=exames,
                    registry_cfgs=cfgs,
                    legacy_names=legacy,
                    fetch_latency_ms=elapsed_ms,
                )
                registrar_log(
                    "AnalysisService",
                    f"Exames disponiveis via registry canônico: {', '.join(exames)}",
                    "INFO",
                )
                self.exames_disponiveis = exames
                return exames

            exames = self._listar_exames_legacy()
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            self._registrar_disponibilidade_e_paridade(
                source_mode="legacy_csv",
                selected=exames,
                registry_cfgs=[],
                legacy_names=exames,
                fetch_latency_ms=elapsed_ms,
            )
            registrar_log(
                "AnalysisService",
                f"Exames disponiveis carregados no legado: {', '.join(exames)}",
                "INFO",
            )
            self.exames_disponiveis = exames
            return exames
        except Exception as exc:  # noqa: BLE001
            registrar_log(
                "AnalysisService",
                f"Erro ao carregar exames disponiveis: {exc}",
                "ERROR",
            )
            raise

    @staticmethod
    def _safe_float_runtime(value: Any, default: float) -> float:
        return runtime_safe_float(value, default)

    @staticmethod
    def _well_sort_key(well_value: Any) -> tuple[str, int]:
        raw = str(well_value or "").strip().upper()
        if not raw:
            return ("Z", 999)
        letter = raw[0]
        digits = "".join(ch for ch in raw[1:] if ch.isdigit())
        if not letter.isalpha() or not digits:
            return ("Z", 999)
        try:
            return (letter, int(digits))
        except Exception:
            return ("Z", 999)

    @classmethod
    def _expand_gabarito_by_group_size(
        cls,
        *,
        gabarito: pd.DataFrame,
        well_column: str,
        group_size: int,
    ) -> pd.DataFrame:
        if gabarito is None or gabarito.empty:
            return gabarito
        target_group_size = max(1, int(group_size or 1))
        if target_group_size == 1 or len(gabarito) >= 90:
            out = gabarito.copy()
            out[well_column] = out[well_column].astype(str).str.strip().str.upper()
            return out

        # Construcao do mapa reverso a partir do dominio, garantindo Isolamento de Dominio
        mapping_lookup = {}
        try:
            from domain.plate_mapping import (
                gerar_mapeamento_48,
                gerar_mapeamento_32,
                gerar_mapeamento_24,
            )
            if target_group_size == 2:
                for p in (1, 2):
                    for m in gerar_mapeamento_48(parte=p):
                        mapping_lookup[m["extracao"][0]] = m["analise"]
            elif target_group_size == 3:
                for p in (1, 2, 3):
                    for m in gerar_mapeamento_32(parte=p):
                        mapping_lookup[m["extracao"][0]] = m["analise"]
            elif target_group_size == 4:
                for p in (1, 2, 3, 4):
                    for m in gerar_mapeamento_24(parte=p):
                        mapping_lookup[m["extracao"][0]] = m["analise"]
        except ImportError:
            pass

        expanded_rows: list[dict[str, Any]] = []
        for row in gabarito.to_dict(orient="records"):
            well = str(row.get(well_column, "")).strip().upper()
            
            # Se o arquivo ja trouxe a propriedade Poco_Analise explicitamente preenchida
            explicit_analise = str(row.get("Poco_Analise", "")).strip()
            if explicit_analise:
                import re
                analises = [w.strip().upper() for w in re.split(r'[,\s]+', explicit_analise) if w.strip()]
                if len(analises) == target_group_size:
                    for analise_well in analises:
                        cloned = dict(row)
                        cloned[well_column] = analise_well
                        expanded_rows.append(cloned)
                    continue

            key = cls._well_sort_key(well)
            if key[0] == "Z":
                expanded_rows.append(dict(row))
                continue

            if well in mapping_lookup:
                for analise_well in mapping_lookup[well]:
                    cloned = dict(row)
                    cloned[well_column] = analise_well
                    expanded_rows.append(cloned)
            else:
                letter, base_num = key
                for offset in range(target_group_size):
                    cloned = dict(row)
                    cloned[well_column] = f"{letter}{base_num + offset}"
                    expanded_rows.append(cloned)

        expanded = pd.DataFrame(expanded_rows)
        if expanded.empty:
            return gabarito.copy()

        dedupe_cols = [well_column]
        for extra in ("Amostra", "Codigo"):
            if extra in expanded.columns:
                dedupe_cols.append(extra)
        expanded = expanded.drop_duplicates(subset=dedupe_cols, keep="first").reset_index(drop=True)
        expanded[well_column] = expanded[well_column].astype(str).str.strip().str.upper()
        return expanded

    @staticmethod
    def _is_vr1e2_full_plate_context(
        *,
        exame: str,
        group_size: int,
        raw_well_count: int,
    ) -> bool:
        normalized_exam = str(exame or "").strip().lower()
        return (
            "vr1" in normalized_exam
            and int(group_size or 1) == 2
            and int(raw_well_count or 0) >= 96
        )

    @classmethod
    def _expected_full_plate_groups(cls, *, raw_well_count: int, group_size: int) -> int:
        return int(raw_well_count or 0) // max(1, int(group_size or 1))

    @classmethod
    def _validate_full_plate_mapping_available(
        cls,
        *,
        exame: str,
        group_size: int,
        raw_well_count: int,
        has_valid_mapping: bool,
    ) -> None:
        if has_valid_mapping:
            return
        if not cls._is_vr1e2_full_plate_context(
            exame=exame,
            group_size=group_size,
            raw_well_count=raw_well_count,
        ):
            return
        raise AnalysisCompletenessError(
            "Mapeamento de placa incompleto: VR1e2 com placa cheia "
            f"({raw_well_count} poços) exige gabarito de extração com coluna Poco/Poço "
            "antes de gerar o relatorio."
        )

    @classmethod
    def _validate_full_plate_result_count(
        cls,
        *,
        exame: str,
        group_size: int,
        raw_well_count: int,
        processed_count: int,
    ) -> None:
        if not cls._is_vr1e2_full_plate_context(
            exame=exame,
            group_size=group_size,
            raw_well_count=raw_well_count,
        ):
            return
        expected_groups = cls._expected_full_plate_groups(
            raw_well_count=raw_well_count,
            group_size=group_size,
        )
        if int(processed_count or 0) == expected_groups:
            return
        raise AnalysisCompletenessError(
            "Mapeamento de placa incompleto: esperadas "
            f"{expected_groups} amostras/grupos para VR1e2 com placa cheia "
            f"({raw_well_count} poços, agrupamento {group_size}); "
            f"geradas {processed_count}."
        )

    @staticmethod
    def _normalize_contract_extractor_columns(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df

        out = df.copy()
        normalized_columns = {
            _normalize_col_key(str(column)): column
            for column in out.columns
        }
        aliases = {
            "bem": "Well",
            "amostra": "Sample",
            "alvo": "Target",
            "ct": "Ct",
            "ampstatus": "Amp Status",
        }
        for source_key, target_column in aliases.items():
            source_column = normalized_columns.get(source_key)
            if source_column is not None and target_column not in out.columns:
                out[target_column] = out[source_column]
        return out

    @classmethod
    def _build_sample_well_positions(cls, df_norm: pd.DataFrame) -> Dict[str, Dict[str, int]]:
        if df_norm is None or df_norm.empty:
            return {}
        if "Sample" not in df_norm.columns or "Well" not in df_norm.columns:
            return {}

        positions: Dict[str, Dict[str, int]] = {}
        grouped = df_norm.groupby("Sample", dropna=False)["Well"].apply(list).to_dict()
        for sample, wells in grouped.items():
            normalized = sorted(
                {str(w).strip().upper() for w in wells if str(w).strip()},
                key=cls._well_sort_key,
            )
            positions[str(sample)] = {well: idx + 1 for idx, well in enumerate(normalized)}
        return positions

    @classmethod
    def _resolve_rp_target_label(
        cls,
        sample: Any,
        well: Any,
        sample_well_positions: Dict[str, Dict[str, int]],
    ) -> str:
        sample_key = str(sample)
        well_key = str(well or "").strip().upper()
        position = sample_well_positions.get(sample_key, {}).get(well_key)
        if isinstance(position, int) and position > 0:
            return f"RP_{position}"

        sort_key = cls._well_sort_key(well_key)
        fallback_pos = 1 if sort_key[1] % 2 == 1 else 2
        return f"RP_{fallback_pos}"

    def _resolve_runtime_rule_profile(self, exame: str) -> Dict[str, Any]:
        """Resolve limiares de analise a partir do Registry/contrato V2."""
        cfg = get_exam_cfg(exame)
        return build_runtime_rule_profile_from_cfg(
            cfg,
            exam_name=exame,
            rp_min_fallback=CT_MIN_RP_VALIDO,
            rp_max_fallback=CT_MAX_RP_VALIDO,
        )

    def _classificar_ct_com_regra_runtime(self, ct_val: Any, *, target_name: str, profile: Dict[str, Any]) -> str:
        return classify_ct_with_runtime_profile(
            ct_val,
            target_name=str(target_name),
            profile=profile,
        )

    def _registrar_paridade_runtime_execucao(
        self,
        *,
        exame: str,
        route_mode: str,
        elapsed_ms: float,
        comparisons: List[Dict[str, str]],
        error_count: int = 0,
        rollout_decision: Dict[str, Any] | None = None,
    ) -> None:
        self._analysis_runtime_samples_ms.append(float(elapsed_ms))
        if len(self._analysis_runtime_samples_ms) > 200:
            self._analysis_runtime_samples_ms = self._analysis_runtime_samples_ms[-200:]

        report = build_runtime_parity_report(
            exame=exame,
            route_mode=route_mode,
            elapsed_ms=elapsed_ms,
            latency_samples_ms=self._analysis_runtime_samples_ms,
            p95_target_ms=self._analysis_runtime_slo_ms,
            comparisons=comparisons,
        )
        report_path = persist_runtime_parity_report(report)
        setattr(self.app_state, "analysis_runtime_report_path", str(report_path))
        setattr(self.app_state, "analysis_runtime_report", report)

        gate_report = build_runtime_promotion_gate(
            parity_report=report,
            error_count=int(error_count or 0),
            max_critical_divergences=0,
            max_error_rate=0.0,
        )
        gate_path = persist_runtime_promotion_gate(gate_report)
        setattr(self.app_state, "analysis_runtime_gate_path", str(gate_path))
        setattr(self.app_state, "analysis_runtime_gate", gate_report)
        setattr(self.app_state, "analysis_runtime_promotion_allowed", bool(gate_report.get("is_promotion_allowed", False)))
        if not bool(gate_report.get("is_promotion_allowed", False)):
            registrar_log(
                "AnalysisService",
                f"Promocao do runtime canonico bloqueada pelo gate F3.5: {gate_report.get('block_reasons', [])}",
                "WARNING",
            )

        runtime_rollout_decision = dict(rollout_decision or {})
        rollout_audit = build_runtime_rollout_audit(
            decision=runtime_rollout_decision,
            current_gate_report=gate_report,
            component="AnalysisService",
            route_mode=route_mode,
        )
        rollout_audit_path = persist_runtime_rollout_audit(rollout_audit)
        setattr(self.app_state, "analysis_runtime_rollout_audit_path", str(rollout_audit_path))
        setattr(self.app_state, "analysis_runtime_rollout_audit", rollout_audit)

        stage_audit = build_runtime_rollout_stage_audit(
            decision=runtime_rollout_decision,
            component="AnalysisService",
            route_mode=route_mode,
        )
        stage_audit_path = persist_runtime_rollout_stage_audit(stage_audit)
        setattr(self.app_state, "analysis_runtime_stage_audit_path", str(stage_audit_path))
        setattr(self.app_state, "analysis_runtime_stage_audit", stage_audit)

        cutover_audit = build_runtime_cutover_audit(
            decision=runtime_rollout_decision,
            current_gate_report=gate_report,
            component="AnalysisService",
            route_mode=route_mode,
        )
        cutover_audit_path = persist_runtime_cutover_audit(cutover_audit)
        setattr(self.app_state, "analysis_runtime_cutover_audit_path", str(cutover_audit_path))
        setattr(self.app_state, "analysis_runtime_cutover_audit", cutover_audit)

        closure_audit = build_runtime_stabilization_closure_audit(
            decision=runtime_rollout_decision,
            current_gate_report=gate_report,
            component="AnalysisService",
            route_mode=route_mode,
        )
        closure_audit_path = persist_runtime_stabilization_closure_audit(closure_audit)
        setattr(self.app_state, "analysis_runtime_stabilization_closure_audit_path", str(closure_audit_path))
        setattr(self.app_state, "analysis_runtime_stabilization_closure_audit", closure_audit)



    def _analisar_corrida_pipeline(

        self,

        exame: str,

        arquivo_resultados: Path,

        arquivo_extracao: Optional[Path] = None,

        lote: Optional[str] = None,

    ) -> AnaliseResultado:

        """

        Executa a análise completa de uma corrida para um determinado exame.



        Parâmetros

        ----------

        exame : str

            Nome do exame, conforme cadastro em exames_config.csv

        arquivo_resultados : Path

            Caminho para o arquivo de resultados do equipamento (CSV/XLSX/etc.)

        arquivo_extracao : Path, opcional

            Caminho para o arquivo de extração / mapeamento de amostras

        lote : str, opcional

            Identificação de lote, se fornecida pela UI

        """

        from domain.exam_scope import ExamForaDoEscopoError
        from services.exam_registry import registry as _scope_reg

        active_exams = getattr(_scope_reg, "active_exams", None)
        loaded_exams = getattr(_scope_reg, "exams", None)
        scope_configured = hasattr(_scope_reg, "active_exams") and (
            bool(active_exams) or bool(loaded_exams)
        )

        if scope_configured and not _scope_reg.is_active(exame):
            raise ExamForaDoEscopoError(exame)

        registrar_log(

            "info",

            f"[AnalysisService] Iniciando análise para exame='{exame}', "

            f"arquivo_resultados='{arquivo_resultados}', arquivo_extracao='{arquivo_extracao}', "

            f"lote='{lote}'",

        )

        usuario = getattr(self.app_state, "usuario_logado", None)
        pipeline_started = time.perf_counter()
        runtime_requested_enabled = is_analysis_runtime_registry_rules_enabled(user_id=usuario)
        runtime_rollout_decision = resolve_runtime_rollout_decision(
            requested_enabled=runtime_requested_enabled,
            exam_name=exame,
            user_id=usuario,
        )
        setattr(self.app_state, "analysis_runtime_rollout_decision", runtime_rollout_decision)
        runtime_registry_rules_enabled = bool(runtime_rollout_decision.get("effective_runtime_enabled", False))
        runtime_shadow_compare_enabled = bool(runtime_rollout_decision.get("shadow_compare_enabled", False))
        runtime_rule_profile: Dict[str, Any] = {}
        runtime_route_mode = "legacy_builtin_rules"
        runtime_scope = runtime_rollout_decision.get("scope", {}) if isinstance(runtime_rollout_decision, dict) else {}
        if runtime_requested_enabled and (not bool(runtime_scope.get("in_scope", True))):
            runtime_route_mode = "legacy_builtin_rules_scope_excluded"
        if runtime_registry_rules_enabled or runtime_shadow_compare_enabled:
            runtime_rule_profile = self._resolve_runtime_rule_profile(exame)
            if runtime_registry_rules_enabled:
                runtime_route_mode = (
                    "registry_v2_rules"
                    if runtime_rule_profile.get("has_v2")
                    else "registry_legacy_fallback_rules"
                )
            elif runtime_requested_enabled and runtime_rollout_decision.get("promotion_status") == "BLOCKED":
                runtime_route_mode = "legacy_builtin_rules_gate_blocked"
            elif runtime_requested_enabled and runtime_rollout_decision.get("promotion_status") == "APPROVED":
                runtime_route_mode = "legacy_builtin_rules_canary_hold"
            else:
                runtime_route_mode = "legacy_builtin_rules_shadow_mode"
        runtime_parity_comparisons: List[Dict[str, str]] = []

        parser_contract_enabled = is_contract_parser_enabled(user_id=usuario)
        if parser_contract_enabled and not self.app_state.tipo_de_placa_selecionado:
            detected = self._detectar_tipo_placa_sem_dialogo(arquivo_resultados)
            if not detected:
                raise RuntimeError(
                    "Tipo de placa obrigatorio quando o parser por contrato esta ativo."
                )

        # Fonte canônica para agrupamento funcional (tabela/mapa/regras)
        equipment_name = (
            str(getattr(self.app_state, "tipo_de_placa_selecionado", "") or "").strip()
            or str(getattr(self.app_state, "tipo_de_placa_detectado", "") or "").strip()
        )
        try:
            analysis_contract_decision = get_contract_catalog().resolve_analysis_contract_decision(
                exam_name=exame,
                equipment_name=equipment_name,
            )
        except Exception as contract_exc:
            registrar_log(
                "AnalysisService",
                f"Falha ao resolver contrato canônico de agrupamento: {contract_exc}",
                "WARNING",
            )
            analysis_contract_decision = {}

        try:
            contract_group_size = max(1, int(analysis_contract_decision.get("group_size", 1) or 1))
        except Exception:
            contract_group_size = 1
        self.app_state.bloco_tamanho = contract_group_size



        # 1. Carregar dados brutos dos arquivos

        # 1.1. Usar extrator específico se tipo de placa foi detectado (Fase 1.5)

        df_resultados = self._carregar_arquivo_resultados_com_extrator(arquivo_resultados)

        

        df_extracao = (

            self._carregar_arquivo_extracao(arquivo_extracao)

            if arquivo_extracao is not None

            else None

        )

        # Se houver gabarito/arquivo de extração, armazena-o no AppState para integração no motor de analise

        if df_extracao is not None:

            self.app_state.df_gabarito_extracao = df_extracao



        # 2. PROCESSAMENTO COMPLETO (fluxo principal)
        registrar_log("AnalysisService", "Processando dados com pivot completo e regras de análise", "INFO")
        processing_error_count = 0

        try:
            # ETAPA 1: Identificar colunas do arquivo RAW
            cols_raw = df_resultados.columns.tolist()
            
            # Identificar colunas via helper compartilhado (inclui regras de Cq/CT e Well Position).
            col_map = identificar_colunas_pcr(df_resultados)
            col_well = col_map["well"]
            col_sample = col_map["sample"]
            col_target = col_map["target"]
            col_ct = col_map["ct"]
            col_amp = col_map.get("amp_status")

            if not col_sample:
                registrar_log(
                    "AnalysisService",
                    "Coluna Sample nao encontrada. Usando Well como fallback.",
                    "WARNING",
                )

            # ========== LOGS DETALHADOS PARA DEBUG ==========
            registrar_log("AnalysisService",
                         f"ðŸ” DEBUG: TOTAL de colunas = {len(df_resultados.columns)}",
                         "DEBUG")
            
            # Mostrar TODAS as colunas com representação de bytes
            for idx, col in enumerate(df_resultados.columns):
                col_bytes = col.encode('utf-8', errors='replace').decode('utf-8')
                col_normalized = str(col).strip().lower()
                registrar_log("AnalysisService",
                             f"  Col[{idx}]: '{col}' | Bytes: '{col_bytes}' | Normalizado: '{col_normalized}'",
                             "DEBUG")
            
            registrar_log("AnalysisService",
                         f"âœ… Coluna identificada para CT = '{col_ct}'",
                         "INFO")
            
            # Mostrar primeiros 10 valores DA COLUNA CT
            if col_ct and col_ct in df_resultados.columns:
                sample_values = df_resultados[col_ct].head(10).tolist()
                registrar_log("AnalysisService",
                             f"ðŸ“Š Primeiros 10 valores da coluna CT '{col_ct}': {sample_values}",
                             "DEBUG")
            
            # Mostrar tipos de dados
            registrar_log("AnalysisService",
                         f"ðŸ”¢ Tipo da coluna CT: {df_resultados[col_ct].dtype if col_ct in df_resultados.columns else 'N/A'}",
                         "DEBUG")
            
            # ETAPA 2: Normalizar dados RAW
            df_norm = pd.DataFrame()
            
            def _clean_well_name(w):
                if pd.isna(w):
                    return ""
                w_str = str(w).strip().upper().replace(" ", "")
                if len(w_str) >= 2 and w_str[0].isalpha():
                    num_part = w_str[1:]
                    if num_part.isdigit():
                        return f"{w_str[0]}{int(num_part)}"
                return w_str
            
            df_norm['Well'] = df_resultados[col_well].apply(_clean_well_name)
            df_norm['Sample_Raw'] = df_resultados[col_sample].astype(str) if col_sample else df_norm['Well']
            df_norm['Target'] = (
                df_resultados[col_target]
                .astype(str)
                .str.strip()
                .str.upper()
                .apply(canonicalizar_alvo_pcr)
            )
            df_norm['Ct_Raw'] = df_resultados[col_ct]
            
            # Normalizar Ct
            def normalizar_ct(val):
                if pd.isna(val):
                    return None
                s = str(val).strip().upper()
                if s in ('', 'UNDETERMINED', 'UND', 'N/A', 'NA', 'NAN'):
                    return None
                try:
                    return round(float(s.replace(',', '.')), 2)
                except:
                    return None
            
            df_norm['Ct'] = df_norm['Ct_Raw'].apply(normalizar_ct)

            # Coluna "Amp Status" (opcional). Ausencia => coluna vazia, sem efeito.
            if col_amp and col_amp in df_resultados.columns:
                df_norm['Amp_Status'] = df_resultados[col_amp].astype(str)
            else:
                df_norm['Amp_Status'] = ""

            raw_well_count = int(df_norm['Well'].nunique())
            
            registrar_log("AnalysisService", 
                         f"ðŸ”„ DEBUG: Após normalização - Primeiros 20 valores Ct:\n{df_norm[['Well', 'Target', 'Ct_Raw', 'Ct']].head(20).to_string()}",
                         "DEBUG")
            
            registrar_log("AnalysisService",
                         f"ðŸ”„ DEBUG: Estatísticas Ct - Total linhas: {len(df_norm)}, Ct válidos: {df_norm['Ct'].notna().sum()}, Ct nulos: {df_norm['Ct'].isna().sum()}",
                         "DEBUG")
            
            registrar_log("AnalysisService", 
                         f"DEBUG: df_norm shape={df_norm.shape}, colunas={list(df_norm.columns)}",
                         "DEBUG")
            registrar_log("AnalysisService",
                         f"DEBUG: Primeiras linhas df_norm:\n{df_norm.head(10).to_string()}",
                         "DEBUG")
            
            # ETAPA 3: Integrar com gabarito (consolida A1+A2 â†’ mesma amostra)
            if hasattr(self.app_state, 'df_gabarito_extracao') and self.app_state.df_gabarito_extracao is not None:
                gabarito = self.app_state.df_gabarito_extracao.copy()
                
                registrar_log("AnalysisService",
                             f"DEBUG: Gabarito encontrado! Shape={gabarito.shape}, colunas={list(gabarito.columns)}",
                             "DEBUG")
                registrar_log("AnalysisService",
                             f"DEBUG: Primeiras linhas gabarito:\n{gabarito.head(10).to_string()}",
                             "DEBUG")
                
                if 'Poco' in gabarito.columns or 'PoÃ§o' in gabarito.columns:
                    col_poco_gab = 'Poco' if 'Poco' in gabarito.columns else 'PoÃ§o'
                    
                    # Renomear amostras vazias ('X' ou vazias) para manter rastreabilidade
                    # e garantir que não se fundam no pivot table (evitando perda de contagem).
                    if 'Amostra' in gabarito.columns:
                        # Normalize string to handle spaces and 'nan'
                        gabarito['Amostra_str'] = gabarito['Amostra'].astype(str).str.strip().str.upper()
                        mask_empty = gabarito['Amostra'].isna() | (gabarito['Amostra_str'] == 'X') | (gabarito['Amostra_str'] == '') | (gabarito['Amostra_str'] == 'NAN') | (gabarito['Amostra_str'] == 'NONE')
                        if mask_empty.any():
                            gabarito.loc[mask_empty, 'Amostra'] = 'Vazio_' + gabarito.loc[mask_empty, col_poco_gab].astype(str)
                            registrar_log("AnalysisService", f"Renomeados {mask_empty.sum()} poços vazios ('X') para validação de placa cheia.", "INFO")

                    # Se o gabarito veio da UI com Poco_Analise já mapeado, usamos ele
                    if 'Poco_Analise' in gabarito.columns:
                        # Explode a tupla/lista de Poco_Analise para múltiplas linhas
                        gabarito = gabarito.explode('Poco_Analise', ignore_index=True)
                        gabarito['Well_Gab'] = gabarito['Poco_Analise'].apply(_clean_well_name)
                        registrar_log("AnalysisService", f"Gabarito mapeado via Poco_Analise: {len(gabarito)} pocos", "INFO")
                    else:
                        group_size = max(1, int(getattr(self.app_state, "bloco_tamanho", 1) or 1))
                        gabarito = self._expand_gabarito_by_group_size(
                            gabarito=gabarito,
                            well_column=col_poco_gab,
                            group_size=group_size,
                        )
                        registrar_log(
                            "AnalysisService",
                            f"Gabarito expandido dinamicamente por contrato (group_size={group_size}): {len(gabarito)} pocos",
                            "INFO",
                        )
                        gabarito['Well_Gab'] = gabarito[col_poco_gab].apply(_clean_well_name)
                    
                    df_norm = df_norm.merge(
                        gabarito[['Well_Gab', 'Amostra', 'Codigo']],
                        left_on='Well',
                        right_on='Well_Gab',
                        how='outer'
                    )
                    # Preencher Well com Well_Gab caso seja um poço que estava no gabarito mas não no arquivo de resultados
                    df_norm['Well'] = df_norm['Well'].fillna(df_norm['Well_Gab'])
                    df_norm['Sample'] = df_norm['Amostra'].fillna(df_norm['Sample_Raw'])

                    indicator_col = None
                    if 'Amostra' in df_norm.columns:
                        indicator_col = 'Amostra'
                    elif 'Codigo' in df_norm.columns:
                        indicator_col = 'Codigo'

                    if indicator_col:
                        try:
                            validation_result = validate_merge_quality(
                                df_norm,
                                merge_key='Well',
                                indicator_column=indicator_col,
                                min_mapping_rate=0.50,
                            )
                            log_unmapped_details(
                                validation_result,
                                registrar_log,
                                context='AnalysisService',
                            )
                        except Exception as exc:
                            registrar_log(
                                'AnalysisService',
                                f'Falha na validacao do gabarito: {exc}',
                                'WARNING',
                            )
                    
                    registrar_log("AnalysisService",
                                 f"DEBUG: Após merge com gabarito - amostras únicas: {df_norm['Sample'].nunique()}",
                                 "DEBUG")
                    registrar_log("AnalysisService",
                                 f"DEBUG: Primeiras amostras únicas: {df_norm['Sample'].unique()[:5].tolist()}",
                                 "DEBUG")
                    
                    # NÃO FILTRAR poços vazios (marcados como 'X' no gabarito)
                    # A regra estabelecida exige que eles entrem na conta como 'Inválido'
                    sample_mask = df_norm['Sample'].notna()
                    df_norm = df_norm.loc[sample_mask].copy()
                    
                    registrar_log("AnalysisService",
                                 f"âœ… Após filtrar poços vazios: {df_norm['Sample'].nunique()} amostras",
                                 "INFO")
                else:
                    self._validate_full_plate_mapping_available(
                        exame=exame,
                        group_size=contract_group_size,
                        raw_well_count=raw_well_count,
                        has_valid_mapping=False,
                    )
                    df_norm['Sample'] = df_norm['Sample_Raw']
                    registrar_log("AnalysisService", "DEBUG: Gabarito sem coluna Poco/Poço", "WARNING")
            else:
                self._validate_full_plate_mapping_available(
                    exame=exame,
                    group_size=contract_group_size,
                    raw_well_count=raw_well_count,
                    has_valid_mapping=False,
                )
                df_norm['Sample'] = df_norm['Sample_Raw']
                registrar_log("AnalysisService", "DEBUG: Gabarito NÃO disponível", "WARNING")
            
            # ETAPA 4: Separar RP de outros alvos (subconjuntos enxutos para reduzir memoria)
            rp_mask = df_norm['Target'].str.contains('RP', na=False, case=False)
            base_cols = ['Sample', 'Well', 'Target', 'Ct']
            alvos_cols = ['Sample', 'Target', 'Ct']
            if 'Amp_Status' in df_norm.columns:
                alvos_cols.append('Amp_Status')
            df_rp = df_norm.loc[rp_mask, base_cols].copy()
            df_alvos = df_norm.loc[~rp_mask, alvos_cols].copy()
            
            # RP separado pela posicao do poco dentro do grupo da amostra
            # (RP_1, RP_2, RP_3... conforme contrato).
            if not df_rp.empty:
                sample_well_positions = self._build_sample_well_positions(df_norm)
                df_rp['Target_RP'] = df_rp.apply(
                    lambda row: self._resolve_rp_target_label(
                        row.get("Sample"),
                        row.get("Well"),
                        sample_well_positions,
                    ),
                    axis=1,
                )
                rp_dist = df_rp['Target_RP'].value_counts(dropna=False).to_dict()
                registrar_log(
                    "AnalysisService",
                    f"DEBUG: RP separado por posicao de grupo: {rp_dist}",
                    "DEBUG",
                )
            
            # ETAPA 5: PIVOT - 1 linha por amostra, alvos como colunas
            # IMPORTANTE: Pivotar ALVOS (não-RP)
            if not df_alvos.empty:
                pivot_ct_alvos = df_alvos.pivot_table(
                    index='Sample',
                    columns='Target',
                    values='Ct',
                    aggfunc='mean'  # Consolidar A1+A2 (alvos distribuídos em pares distintos)
                )
            else:
                pivot_ct_alvos = pd.DataFrame()

            # Pivot booleano de Amp Status por amostra x alvo: True se qualquer poço
            # do grupo (A1+A2) indicar falha de amplificacao (No Amp / Inconclusive).
            if not df_alvos.empty and 'Amp_Status' in df_alvos.columns:
                amp_flags = df_alvos.assign(
                    _amp_flag=df_alvos['Amp_Status'].map(is_amp_status_indeterminante)
                )
                pivot_amp = amp_flags.pivot_table(
                    index='Sample',
                    columns='Target',
                    values='_amp_flag',
                    aggfunc='max',
                )
            else:
                pivot_amp = pd.DataFrame()
            
            # Pivotar RP separadamente (RP_1 e RP_2 como colunas distintas)
            if not df_rp.empty:
                pivot_ct_rp = df_rp.pivot_table(
                    index='Sample',
                    columns='Target_RP',
                    values='Ct',
                    aggfunc='first'  # Usar primeiro valor (não fazer média!)
                )
            else:
                pivot_ct_rp = pd.DataFrame()
            
            # LOGS DETALHADOS DOS PIVOTS
            registrar_log("AnalysisService",
                         f"ðŸ“Š DEBUG PIVOT ALVOS: Shape={pivot_ct_alvos.shape if not pivot_ct_alvos.empty else 'vazio'}, Colunas={list(pivot_ct_alvos.columns) if not pivot_ct_alvos.empty else []}",
                         "DEBUG")
            if not pivot_ct_alvos.empty:
                registrar_log("AnalysisService",
                             f"ðŸ“Š DEBUG PIVOT ALVOS primeiras linhas:\n{pivot_ct_alvos.head(3).to_string()}",
                             "DEBUG")
            
            registrar_log("AnalysisService",
                         f"ðŸ“Š DEBUG PIVOT RP: Shape={pivot_ct_rp.shape if not pivot_ct_rp.empty else 'vazio'}, Colunas={list(pivot_ct_rp.columns) if not pivot_ct_rp.empty else []}",
                         "DEBUG")
            if not pivot_ct_rp.empty:
                registrar_log("AnalysisService",
                             f"ðŸ“Š DEBUG PIVOT RP primeiras linhas:\n{pivot_ct_rp.head(3).to_string()}",
                             "DEBUG")
            
            # ETAPA 6: Aplicar regras de análise
            # Regras específicas para VR1e2 Biomanguinhos:
            # - CT vazio/Undetermined â†’ Não Detectado
            # - 0 â‰¤ CT < 13 â†’ Não Detectado
            # - 13 â‰¤ CT < 35 â†’ Detectado
            # - 35 â‰¤ CT â‰¤ 40 â†’ Indeterminado
            # - CT > 40 â†’ Não Detectado
            
            # Valores de threshold agora gerenciados por services.logic_engine
            
            # Criar DataFrame final
            linhas = []
            
            # Definir TODAS as colunas possíveis (template)
            # Isso garante que todas as amostras tenham todas as colunas
            todos_alvos = pivot_ct_alvos.columns.tolist() if not pivot_ct_alvos.empty else []
            todos_rp = pivot_ct_rp.columns.tolist() if not pivot_ct_rp.empty else []
            
            # Iterar por todas as amostras únicas
            amostras_unicas = df_norm['Sample'].unique()
            
            for sample in amostras_unicas:
                # Inicializar linha com TODAS as colunas vazias
                linha = {}
                
                # Pre-inicializar todas as colunas de alvos como vazio
                for target in todos_alvos:
                    col_ct = f'CT_{target.replace(" ", "_")}'
                    col_res = f'Res_{target.replace(" ", "_")}'
                    linha[col_ct] = ''
                    linha[col_res] = ''
                
                # Pre-inicializar todas as colunas de RP como vazio
                for rp_target in todos_rp:
                    col_ct_rp = f'CT_{rp_target.replace(" ", "_")}'
                    col_res_rp = f'Res_{rp_target.replace(" ", "_")}'
                    linha[col_ct_rp] = ''
                    linha[col_res_rp] = ''
                
                # Adicionar colunas CT_* e Res_* para ALVOS
                if not pivot_ct_alvos.empty and sample in pivot_ct_alvos.index:
                    for target in pivot_ct_alvos.columns:
                        ct_val = pivot_ct_alvos.loc[sample, target]
                        col_ct = f'CT_{target.replace(" ", "_")}'
                        col_res = f'Res_{target.replace(" ", "_")}'
                        
                        # Aplicar regras de análise via Logic Engine
                        if pd.isna(ct_val) or ct_val is None:
                            linha[col_ct] = ''
                        else:
                            linha[col_ct] = ct_val

                        legacy_status = classificar_ct(ct_val)
                        if runtime_registry_rules_enabled:
                            canonical_status = self._classificar_ct_com_regra_runtime(
                                ct_val,
                                target_name=str(target),
                                profile=runtime_rule_profile,
                            )
                            linha[col_res] = canonical_status
                            runtime_parity_comparisons.append(
                                {
                                    "target": str(target),
                                    "ct": "" if pd.isna(ct_val) else str(ct_val),
                                    "legacy_status": str(legacy_status),
                                    "canonical_status": str(canonical_status),
                                }
                            )
                        elif runtime_shadow_compare_enabled:
                            canonical_status = self._classificar_ct_com_regra_runtime(
                                ct_val,
                                target_name=str(target),
                                profile=runtime_rule_profile,
                            )
                            linha[col_res] = legacy_status
                            runtime_parity_comparisons.append(
                                {
                                    "target": str(target),
                                    "ct": "" if pd.isna(ct_val) else str(ct_val),
                                    "legacy_status": str(legacy_status),
                                    "canonical_status": str(canonical_status),
                                }
                            )
                        else:
                            linha[col_res] = legacy_status

                        # Override Amp Status: alvo Detectavel/Indeterminado cujo
                        # "Amp Status" seja No Amp/Inconclusive vira "Indeterminado (ampl)".
                        # A regra de gate (so Detectavel/Indeterminado) fica no dominio.
                        if (
                            not pivot_amp.empty
                            and sample in pivot_amp.index
                            and target in pivot_amp.columns
                        ):
                            amp_flag = pivot_amp.loc[sample, target]
                            if pd.notna(amp_flag) and bool(amp_flag):
                                linha[col_res] = reclassificar_alvo_por_amp_status(
                                    linha[col_res], "No Amp"
                                )

                # Adicionar CT e Resultado RP (pode ter RP_1, RP_2, etc.)
                if not pivot_ct_rp.empty and sample in pivot_ct_rp.index:
                    rp_validos = []
                    for rp_target in pivot_ct_rp.columns:
                        ct_rp = pivot_ct_rp.loc[sample, rp_target]
                        col_ct_rp = f'CT_{rp_target.replace(" ", "_")}'
                        col_res_rp = f'Res_{rp_target.replace(" ", "_")}'
                        
                        linha[col_ct_rp] = ct_rp if not pd.isna(ct_rp) else ''
                        
                        # Validar RP (faixa configurada)
                        rp_min = (
                            self._safe_float_runtime(runtime_rule_profile.get("rp_min"), CT_MIN_RP_VALIDO)
                            if runtime_registry_rules_enabled
                            else CT_MIN_RP_VALIDO
                        )
                        rp_max = (
                            self._safe_float_runtime(runtime_rule_profile.get("rp_max"), CT_MAX_RP_VALIDO)
                            if runtime_registry_rules_enabled
                            else CT_MAX_RP_VALIDO
                        )
                        if (
                            not pd.isna(ct_rp)
                            and rp_min <= ct_rp <= rp_max
                        ):
                            linha[col_res_rp] = 'Válido'
                            rp_validos.append(True)
                        else:
                            linha[col_res_rp] = 'Inválido'
                            rp_validos.append(False)
                    
                    # Status da corrida: Válida se TODOS os RPs forem válidos
                    linha['Status_corrida'] = 'Válida' if all(rp_validos) else 'Inválida'
                else:
                    linha['Status_corrida'] = 'Inválida'
                
                linha[_SUGESTAO_REPETICAO_CANONICAL] = 'Não'
                linha['Sample'] = sample
                
                linhas.append(linha)
            
            df_processado = pd.DataFrame(linhas)
            self._validate_full_plate_result_count(
                exame=exame,
                group_size=contract_group_size,
                raw_well_count=raw_well_count,
                processed_count=len(df_processado),
            )
            
            # ETAPA 7: Adicionar Poço(s) no formato A1+A2 com ordenação numérica
            def ordenar_wells_numerico(wells_list):
                """Ordenar poços numericamente (A1, A2, A10) ao invés de alfabético"""
                def extrair_chave(well):
                    letra = well[0] if len(well) > 0 else 'Z'
                    try:
                        numero = int(well[1:]) if len(well) > 1 else 999
                    except:
                        numero = 999
                    return (letra, numero)
                return sorted(wells_list, key=extrair_chave)
            
            well_por_sample = df_norm.groupby('Sample')['Well'].apply(
                lambda x: '+'.join(ordenar_wells_numerico(list(set(x))))
            ).to_dict()
            df_processado.insert(0, 'PoÃ§o(s)', df_processado['Sample'].map(well_por_sample))
            
            # LOG: Amostras com múltiplos poços (debug)
            amostras_multi_poco = {k: v for k, v in well_por_sample.items() if '+' in v and v.count('+') > 1}
            if amostras_multi_poco:
                registrar_log("AnalysisService",
                             f"âš ï¸ AVISO: Amostras com mais de 2 poços: {list(amostras_multi_poco.items())[:5]}",
                             "DEBUG")
            
            # Renomear Sample â†’ Amostra
            df_processado = df_processado.rename(columns={'Sample': 'Amostra'})
            
            # Adicionar Selecionado
            df_processado.insert(0, 'Selecionado', True)
            
            # 1. ORDENAÇÃO POR POÇOS (A1+A2, B1+B2, ..., H11+H12)
            def ordenar_pocos(poco_str):
                """Extrair primeiro poço para ordenação alfabética/numérica"""
                if not poco_str or pd.isna(poco_str):
                    return ('Z', 999)
                primeiro = str(poco_str).split('+')[0]
                letra = primeiro[0]
                try:
                    numero = int(primeiro[1:])
                except:
                    numero = 999
                return (letra, numero)
            
            df_processado['_sort_key'] = df_processado['PoÃ§o(s)'].apply(ordenar_pocos)
            df_processado = df_processado.sort_values('_sort_key').drop('_sort_key', axis=1).reset_index(drop=True)
            
            # 2. MOVER COLUNA "AMOSTRA" PARA 2Âª POSIÇÃO  
            cols = df_processado.columns.tolist()
            if 'Amostra' in cols:
                amostra_idx = cols.index('Amostra')
                cols.insert(1, cols.pop(amostra_idx))
                df_processado = df_processado[cols]
            
            # 4/5. Resultado geral e selecao: versao vetorizada (T12)
            alvos_cols_res = [col for col in df_processado.columns if col.startswith('Res_') and 'RP' not in col]
            df_processado = _apply_resultado_geral_vectorized(df_processado, alvos_cols_res)

            # 3. VALIDACAO DE PLACA (CN e CP) - versao vetorizada (T12)
            status_placa = _avaliar_status_placa_vectorized(df_processado, alvos_cols_res)
            cn_mask = df_processado['Amostra'].str.contains('CN|CONTROLE.*NEG', case=False, na=False, regex=True)
            cp_mask = df_processado['Amostra'].str.contains('CP|CONTROLE.*POS', case=False, na=False, regex=True)
            if status_placa == "Indefinido":
                faltantes = []
                if not cn_mask.any():
                    faltantes.append("CN ausente")
                if not cp_mask.any():
                    faltantes.append("CP ausente")
                if faltantes:
                    registrar_log(
                        "AnalysisService",
                        f"Controles ausentes na validacao da placa: {', '.join(faltantes)}",
                        "WARNING",
                    )

            # Criar coluna Status_Placa
            if 'Status_corrida' in df_processado.columns:
                df_processado = df_processado.drop('Status_corrida', axis=1)
            df_processado['Status_Placa'] = status_placa

            # T13: reduzir memoria com category nas colunas textuais de baixa cardinalidade
            df_processado = _optimize_df_categorical_columns(df_processado)
            df_processado = _canonicalize_repetition_column(df_processado)
            
            registrar_log("AnalysisService", 
                         f"âœ… Processamento completo: {len(df_processado)} amostras",
                         "INFO")
            
            # LOG FINAL DETALHADO
            registrar_log("AnalysisService",
                         f"ðŸ“‹ DEBUG FINAL: DataFrame shape={df_processado.shape}, colunas={list(df_processado.columns)}",
                         "DEBUG")
            registrar_log("AnalysisService",
                         f"ðŸ“‹ DEBUG FINAL: Primeiras 3 linhas completas:\n{df_processado.head(3).to_string()}",
                         "DEBUG")
            
        except AnalysisCompletenessError as e:
            processing_error_count = 1
            registrar_log("AnalysisService", f"Erro de completude da placa: {e}", "ERROR")
            raise
        except Exception as e:
            processing_error_count = 1
            registrar_log("AnalysisService", f"âŒ Erro no processamento: {e}", "ERROR")
            import traceback
            registrar_log("AnalysisService", traceback.format_exc(), "DEBUG")
            df_processado = df_resultados
        
        # Criar objeto de resultado
        class ResultadoAnalise:
            def __init__(self, df):
                self.df_processado = df
                self.df_final = df
                self.metadados = {}
                self.resumo = {}
                self.status = "processado_completo"
        
        resultado_engine = ResultadoAnalise(df_processado)



        # 3. Montar objeto AnaliseResultado com metadados de equipamento (Fase 1.5)

        metadados_completos = resultado_engine.metadados.copy()

        

        # Injetar informações de equipamento detectado nos metadados

        if self.app_state.tipo_de_placa_detectado:

            metadados_completos['equipamento_detectado'] = self.app_state.tipo_de_placa_detectado

            metadados_completos['equipamento_selecionado'] = self.app_state.tipo_de_placa_selecionado

            

            if self.app_state.tipo_de_placa_config:

                config = self.app_state.tipo_de_placa_config

                metadados_completos['equipamento_modelo'] = config.modelo

                metadados_completos['equipamento_fabricante'] = config.fabricante

                metadados_completos['equipamento_tipo_placa'] = config.tipo_placa

                metadados_completos['equipamento_extrator'] = config.extrator_nome

        metadados_completos = self._enriquecer_metadados_contratos(
            metadados_completos=metadados_completos,
            exame=exame,
        )

        

        analise_resultado = AnaliseResultado(

            df_processado=resultado_engine.df_final,

            resumo=resultado_engine.resumo,

            metadados=metadados_completos,

            caminho_entrada_resultados=arquivo_resultados,

            caminho_entrada_extracao=arquivo_extracao,

        )

        elapsed_ms = (time.perf_counter() - pipeline_started) * 1000.0
        self._registrar_paridade_runtime_execucao(
            exame=exame,
            route_mode=runtime_route_mode,
            elapsed_ms=elapsed_ms,
            comparisons=runtime_parity_comparisons,
            error_count=processing_error_count,
            rollout_decision=runtime_rollout_decision,
        )



        # 4. Atualizar AppState com os dados resultantes

        self._atualizar_app_state_com_resultado(analise_resultado)



        # 5. Armazenar como último resultado

        self.ultimo_resultado = analise_resultado



        registrar_log(

            "info",

            "[AnalysisService] Análise concluída com sucesso. "

            f"Total de linhas no df_processado: {len(analise_resultado.df_processado)}",

        )



        return analise_resultado

    def analisar_corrida(
        self,
        exame: str,
        arquivo_resultados: Path,
        arquivo_extracao: Optional[Path] = None,
        lote: Optional[str] = None,
    ) -> AnaliseResultado:
        """
        Facade v1: delega para o pipeline central de analise.

        Mantido para compatibilidade de assinatura e para rollback simples.
        """
        return self._analisar_corrida_pipeline(
            exame=exame,
            arquivo_resultados=arquivo_resultados,
            arquivo_extracao=arquivo_extracao,
            lote=lote,
        )

    def analisar_corrida_v2(
        self,
        exame: str,
        arquivo_resultados: Path,
        arquivo_extracao: Optional[Path] = None,
        lote: Optional[str] = None,
    ) -> AnaliseResultado:
        """
        Análise de corrida PCR - Versão Refatorada (v2).

        Fluxo v2 executa o mesmo pipeline core de v1 sem delegacao direta
        entre metodos publicos, preservando paridade por construcao.
        """
        usuario = getattr(self.app_state, "usuario_logado", None)
        if is_contract_analysis_runtime_enabled(user_id=usuario):
            bundle = self._resolver_bundle_runtime_obrigatorio(exame=exame)
            self._aplicar_bundle_runtime_no_estado(bundle)

        registrar_log(
            "AnalysisService",
            f"[AnalysisService] v2 executando pipeline core: exame={exame}, lote={lote}, arquivo={arquivo_resultados.name}",
            "INFO",
        )
        return self._analisar_corrida_pipeline(
            exame=exame,
            arquivo_resultados=arquivo_resultados,
            arquivo_extracao=arquivo_extracao,
            lote=lote,
        )



    def executar_analise(

        self,

        app_state: AppState,

        parent_window: Any,

        exame: str,

        lote: str,

        arquivo_resultados: Optional[Path | str] = None,

    ) -> Any:

        """

        Metodo de compatibilidade utilizado pelo MenuHandler (UI).

        A camada de UI deve fornecer o arquivo de resultados; este service nao
        abre dialogs de selecao.

        """

        if app_state is not None and app_state is not self.app_state:

            self.app_state = app_state

            try:

                self.engine.app_state = app_state

            except Exception:

                pass

        if getattr(self.app_state, "dados_extracao", None) is not None:

            try:

                self.app_state.df_gabarito_extracao = self.app_state.dados_extracao

            except Exception:

                pass

        caminho_resolvido = arquivo_resultados or getattr(self.app_state, "caminho_arquivo_corrida", None)
        caminho_resolvido = str(caminho_resolvido or "").strip()
        if not caminho_resolvido:
            raise RuntimeError("Arquivo de resultados obrigatorio para iniciar a analise.")

        arquivo_resultados_path = Path(caminho_resolvido)
        if not arquivo_resultados_path.exists():
            raise RuntimeError(f"Arquivo de resultados nao encontrado: {arquivo_resultados_path}")

        self.app_state.caminho_arquivo_corrida = str(arquivo_resultados_path)

        usuario = getattr(self.app_state, "usuario_logado", None)

        parser_contract_enabled = is_contract_parser_enabled(user_id=usuario)

        tipo_placa_selecionado = None

        if parser_contract_enabled:
            self._limpar_contexto_tipo_placa()
            if parent_window is not None:
                registrar_log(
                    "AnalysisService",
                    "[AnalysisService] parent_window recebido e ignorado: deteccao segue sem UI modal.",
                    "DEBUG",
                )

            tipo_placa_selecionado = self._detectar_tipo_placa_sem_dialogo(
                arquivo_resultados_path
            )

            if not tipo_placa_selecionado:
                raise RuntimeError(
                    "Tipo de placa obrigatorio para continuar a analise com parser contratual."
                )
        else:
            self._limpar_contexto_tipo_placa()

        if tipo_placa_selecionado:
            registrar_log(
                "info",
                f"[AnalysisService] Prosseguindo com tipo de placa: {tipo_placa_selecionado}",
            )
        else:
            registrar_log(
                "info",
                "[AnalysisService] Parser contratual desativado; fluxo generico permitido.",
            )

        from application.analysis_orchestrator_port import AnalysisOrchestratorRequestDTO

        data_exame = getattr(self.app_state, "data_exame", None) or datetime.datetime.now().strftime(
            "%d/%m/%Y"
        )
        request = AnalysisOrchestratorRequestDTO(
            exam_name=exame,
            lote=lote,
            data_exame=str(data_exame),
            resultado_path=arquivo_resultados_path,
            extracao_path=None,
            equipment_hint=tipo_placa_selecionado,
            usuario=str(usuario or ""),
        )
        response = self.criar_orchestrator_port().execute(request)
        return response.df_resultado

    # ------------------------------------------------------------------

    # Funções auxiliares internas

    # ------------------------------------------------------------------



    def _carregar_arquivo_resultados(self, caminho: Path) -> pd.DataFrame:

        """

        Carrega o arquivo de resultados (saída do equipamento).



        Utiliza 'read_data_with_auto_detection', que já faz inferência de

        separadores, codificação e tipo de planilha.

        """

        registrar_log(

            "info",

            f"[AnalysisService] Carregando arquivo de resultados: '{caminho}'",

        )



        if not caminho.exists():

            msg = f"Arquivo de resultados não encontrado: {caminho}"

            registrar_log("erro", f"[AnalysisService] {msg}")

            raise FileNotFoundError(msg)



        df = read_data_with_auto_detection(caminho)

        if df is None:
            raise ValueError(
                f"Não foi possível ler a planilha de resultados '{getattr(caminho, 'name', caminho)}'. "
                "Verifique se o arquivo/aba tem o formato esperado (Well/Sample/Target/Ct)."
            )

        registrar_log(

            "debug",

            f"[AnalysisService] Arquivo de resultados carregado com shape={df.shape}",

        )

        return df



    def _carregar_arquivo_resultados_com_extrator(self, caminho: Path) -> pd.DataFrame:

        """

        Carrega arquivo de resultados usando extrator específico quando disponível (Fase 1.5).

        

        Se app_state.tipo_de_placa_config existir, usa o extrator específico do equipamento

        para normalizar dados para formato padrão ['bem', 'amostra', 'alvo', 'ct'].

        

        Caso contrário, faz fallback para leitura genérica com read_data_with_auto_detection.

        

        Args:

            caminho: Path para arquivo de resultados

            

        Returns:

            DataFrame normalizado (com extrator específico) ou DataFrame bruto (fallback)

        """

        registrar_log(

            "info",

            f"[AnalysisService] Carregando arquivo de resultados: '{caminho}'",

        )



        if not caminho.exists():

            msg = f"Arquivo de resultados não encontrado: {caminho}"

            registrar_log("erro", f"[AnalysisService] {msg}")

            raise FileNotFoundError(msg)

        

        # Fase 1.5: Verificar se há tipo de placa detectado

        if (

            hasattr(self.app_state, 'tipo_de_placa_config') 

            and self.app_state.tipo_de_placa_config is not None

        ):

            try:
                config = self.app_state.tipo_de_placa_config

                equipamento = self.app_state.tipo_de_placa_selecionado

                

                registrar_log(

                    "info",

                    f"[AnalysisService] Usando extrator específico para: {equipamento}",

                )

                

                # Usar porta de extracao dedicada
                df_normalizado = self._get_equipment_extraction_port().extract_results(caminho, config)
                df_normalizado = self._normalize_contract_extractor_columns(df_normalizado)

                

                registrar_log(

                    "info",

                    f"[AnalysisService] Extração específica concluída: {len(df_normalizado)} linhas, "

                    f"colunas={list(df_normalizado.columns)}",

                )

                

                return df_normalizado

                

            except Exception as exc:

                registrar_log(

                    "aviso",

                    f"[AnalysisService] Falha no extrator específico: {exc}. "

                    "Fazendo fallback para leitura genérica.",

                )

                # Continua para fallback

        

        # Fallback: leitura genérica

        registrar_log(

            "info",

            "[AnalysisService] Usando leitura genérica (sem extrator específico)",

        )

        

        df = read_data_with_auto_detection(caminho)

        if df is None:
            raise ValueError(
                f"Não foi possível ler a planilha de resultados '{getattr(caminho, 'name', caminho)}'. "
                "Verifique se o arquivo/aba tem o formato esperado (Well/Sample/Target/Ct)."
            )

        registrar_log(

            "debug",

            f"[AnalysisService] Arquivo de resultados carregado com shape={df.shape}",

        )

        

        return df



    def _detectar_e_confirmar_tipo_placa(

        self,

        arquivo_resultados: Path,

        parent_window: Any,

    ) -> Optional[str]:

        """

        Compatibilidade legada: hoje opera sem UI modal.

        A confirmacao interativa de equipamento foi movida para a camada de UI/use case.
        Este metodo preserva assinatura para rollback simples, mas delega para o fluxo
        sem dialogo no service.

        Returns:
            Nome do equipamento detectado ou None.

        """

        try:

            registrar_log(

                "info",

                f"[AnalysisService] Detectando tipo de placa em: {arquivo_resultados.name}",

            )

            if parent_window is not None:
                registrar_log(
                    "AnalysisService",
                    "[AnalysisService] parent_window ignorado no service; confirmacao pertence a UI.",
                    "DEBUG",
                )

            equipamento_selecionado = self._detectar_tipo_placa_sem_dialogo(arquivo_resultados)
            if not equipamento_selecionado:
                registrar_log(
                    "AnalysisService",
                    "[AnalysisService] Deteccao sem dialogo nao confirmou equipamento.",
                    "INFO",
                )
                return None

            registrar_log(
                "AnalysisService",
                f"[AnalysisService] Tipo de placa definido sem UI: {equipamento_selecionado}",
                "INFO",
            )
            return equipamento_selecionado



        except Exception as exc:

            registrar_log(

                "erro",

                f"[AnalysisService] Erro na detecção de tipo de placa: {exc}",

            )

            # Não propaga erro - continua sem detecção

            return None

    def _limpar_contexto_tipo_placa(self) -> None:
        """Limpa metadados de equipamento para evitar reaproveitamento residual."""
        self.app_state.tipo_de_placa_detectado = None
        self.app_state.tipo_de_placa_config = None
        self.app_state.tipo_de_placa_selecionado = None

    def _detectar_tipo_placa_sem_dialogo(self, arquivo_resultados: Path) -> Optional[str]:
        """
        Detecta equipamento sem UI modal.

        Uso principal: fluxos nao-interativos (scripts/testes) onde nao ha parent
        para confirmar selecao em dialog.
        """
        try:
            detection = self._get_equipment_extraction_port().detect_equipment(arquivo_resultados)
            equipamento = detection.equipamento
            if not equipamento:
                registrar_log(
                    "AnalysisService",
                    "[AnalysisService] Deteccao sem dialogo nao encontrou equipamento.",
                    "INFO",
                )
                return None

            config = self._get_equipment_extraction_port().resolve_config(equipamento)
            if not config:
                registrar_log(
                    "AnalysisService",
                    f"[AnalysisService] Equipamento detectado sem configuracao: {equipamento}",
                    "WARNING",
                )
                return None

            self.app_state.tipo_de_placa_detectado = equipamento
            self.app_state.tipo_de_placa_selecionado = equipamento
            self.app_state.tipo_de_placa_config = config
            registrar_log(
                "AnalysisService",
                f"[AnalysisService] Deteccao sem dialogo selecionou equipamento: {equipamento}",
                "INFO",
            )
            return equipamento
        except Exception as exc:
            registrar_log(
                "AnalysisService",
                f"[AnalysisService] Falha na deteccao sem dialogo: {exc}",
                "WARNING",
            )
            return None


    def _enriquecer_metadados_contratos(
        self,
        *,
        metadados_completos: Dict[str, Any],
        exame: str,
    ) -> Dict[str, Any]:
        """Injeta ids/versoes de contrato no metadado da corrida."""
        try:
            equipamento = (
                getattr(self.app_state, "tipo_de_placa_selecionado", None)
                or getattr(self.app_state, "tipo_de_placa_detectado", None)
                or ""
            )
            catalog = get_contract_catalog()
            bundle = catalog.resolve_runtime_bundle(
                exam_name=exame,
                equipment_name=equipamento,
            )
            exam_profile = bundle.exam_profile or {}
            equipment_profile = bundle.equipment_profile or {}
            metadados_completos["exam_id"] = exam_profile.get("exam_id", "")
            metadados_completos["equipment_id"] = equipment_profile.get("equipment_id", "")
            metadados_completos["analysis_rules_profile_id"] = exam_profile.get(
                "analysis_rules_profile_id", ""
            )
            metadados_completos["gal_profile_id"] = exam_profile.get("gal_profile_id", "")
            metadados_completos["storage_profile_id"] = exam_profile.get(
                "storage_profile_id", ""
            )
            metadados_completos["contract_versions"] = bundle.versions
            metadados_completos["contract_source_hierarchy"] = list(catalog.hierarchy)
            metadados_completos["analysis_contract_decision"] = catalog.resolve_analysis_contract_decision(
                exam_name=exame,
                equipment_name=equipamento,
            )
        except Exception as exc:
            registrar_log(
                "AnalysisService",
                f"Falha ao enriquecer metadados de contrato: {exc}",
                "WARNING",
            )
        return metadados_completos

    def _resolver_bundle_runtime_obrigatorio(self, *, exame: str):
        """Resolve bundle contratual e valida campos obrigatorios da fase 3."""
        equipamento = (
            getattr(self.app_state, "tipo_de_placa_selecionado", None)
            or getattr(self.app_state, "tipo_de_placa_detectado", None)
            or ""
        )
        catalog = get_contract_catalog()
        bundle = catalog.resolve_runtime_bundle(exam_name=exame, equipment_name=equipamento)

        exam_id = str((bundle.exam_profile or {}).get("exam_id", "")).strip()
        equipment_id = str((bundle.equipment_profile or {}).get("equipment_id", "")).strip()

        if not exam_id:
            raise RuntimeError(
                "Runtime contratual ativo: exam_id ausente no contrato do exame selecionado."
            )
        if not equipment_id:
            raise RuntimeError(
                "Runtime contratual ativo: equipment_id ausente no contrato do equipamento selecionado."
            )

        return bundle

    def _aplicar_bundle_runtime_no_estado(self, bundle: Any) -> None:
        """Persiste ids/versionamento de contrato no AppState para rastreabilidade."""
        exam_profile = getattr(bundle, "exam_profile", {}) or {}
        equipment_profile = getattr(bundle, "equipment_profile", {}) or {}
        versions = getattr(bundle, "versions", {}) or {}

        self.app_state.exam_id = str(exam_profile.get("exam_id", "")).strip() or None
        self.app_state.equipment_id = str(equipment_profile.get("equipment_id", "")).strip() or None
        self.app_state.analysis_rules_profile_id = (
            str(exam_profile.get("analysis_rules_profile_id", "")).strip() or None
        )
        self.app_state.gal_profile_id = str(exam_profile.get("gal_profile_id", "")).strip() or None
        self.app_state.storage_profile_id = (
            str(exam_profile.get("storage_profile_id", "")).strip() or None
        )
        self.app_state.contract_versions = {str(k): str(v) for k, v in versions.items()}


    def _carregar_arquivo_extracao(self, caminho: Path) -> pd.DataFrame:

        """

        Carrega o arquivo de extração / mapeamento de amostras.



        Também usa 'read_data_with_auto_detection' para reduzir a

        sensibilidade a variações de formato.

        """

        registrar_log(

            "info",

            f"[AnalysisService] Carregando arquivo de extração/mapeamento: '{caminho}'",

        )



        if not caminho.exists():

            msg = f"Arquivo de extração/mapeamento não encontrado: {caminho}"

            registrar_log("erro", f"[AnalysisService] {msg}")

            raise FileNotFoundError(msg)



        df = read_data_with_auto_detection(caminho)

        if df is None:
            raise ValueError(
                f"Não foi possível ler a planilha de extração/mapeamento '{getattr(caminho, 'name', caminho)}'."
            )

        registrar_log(

            "debug",

            f"[AnalysisService] Arquivo de extração/mapeamento carregado com shape={df.shape}",

        )

        return df



    def _atualizar_app_state_com_resultado(self, resultado: AnaliseResultado) -> None:

        """

        Atualiza o AppState com os artefatos produzidos pela análise.



        Isso permite que outras partes da UI (por exemplo, visualizadores de

        placa, relatórios, exportação GAL) acessem os dados de forma coerente.

        """

        try:

            # Guarda o DataFrame processado no estado da aplicação

            self.app_state.df_processado = resultado.df_processado



            # Resumo e metadados

            self.app_state.analise_resumo = resultado.resumo

            self.app_state.analise_metadados = resultado.metadados

            contract_decision: Dict[str, Any] = {}
            if isinstance(resultado.metadados, dict):
                raw_decision = resultado.metadados.get("analysis_contract_decision")
                if isinstance(raw_decision, dict):
                    contract_decision = dict(raw_decision)

            if not contract_decision:
                try:
                    exam_name = str(getattr(self.app_state, "exame_selecionado", "") or "").strip()
                    equipment_name = (
                        str(getattr(self.app_state, "tipo_de_placa_selecionado", "") or "").strip()
                        or str(getattr(self.app_state, "tipo_de_placa_detectado", "") or "").strip()
                    )
                    if exam_name:
                        contract_decision = get_contract_catalog().resolve_analysis_contract_decision(
                            exam_name=exam_name,
                            equipment_name=equipment_name,
                        )
                except Exception as decision_exc:
                    registrar_log(
                        "AnalysisService",
                        f"Falha ao resolver decisao contratual para agrupamento: {decision_exc}",
                        "WARNING",
                    )

            if contract_decision:
                try:
                    group_size = max(1, int(contract_decision.get("group_size", 1) or 1))
                except Exception:
                    group_size = 1
                try:
                    pocos_por_amostra = max(
                        1,
                        int(contract_decision.get("pocos_por_amostra", group_size) or group_size),
                    )
                except Exception:
                    pocos_por_amostra = group_size

                self.app_state.bloco_tamanho = group_size
                self.app_state.pocos_por_amostra = pocos_por_amostra
                self.app_state.esquema_agrupamento = str(
                    contract_decision.get("esquema_agrupamento", "")
                ).strip()
                self.app_state.analysis_contract_decision = contract_decision



            # Caminhos de origem

            self.app_state.caminho_arquivo_resultados = (

                str(resultado.caminho_entrada_resultados)

                if resultado.caminho_entrada_resultados is not None

                else None

            )

            # Nome base do arquivo de corrida (para hist?rico e mapa)
            if resultado.caminho_entrada_resultados is not None:
                try:
                    from pathlib import Path as _Path

                    self.app_state.caminho_arquivo_corrida = _Path(
                        resultado.caminho_entrada_resultados
                    ).name
                except Exception:
                    self.app_state.caminho_arquivo_corrida = str(
                        resultado.caminho_entrada_resultados
                    )
            else:
                self.app_state.caminho_arquivo_corrida = None

            self.app_state.caminho_arquivo_extracao = (

                str(resultado.caminho_entrada_extracao)

                if resultado.caminho_entrada_extracao is not None

                else None

            )



            # Marca data/hora da última análise

            self.app_state.data_hora_ultima_analise = datetime.datetime.now()



            registrar_log(

                "info",

                "[AnalysisService] AppState atualizado com resultado da análise.",

            )

        except Exception as exc:  # noqa: BLE001

            registrar_log(

                "erro",

                f"[AnalysisService] Erro ao atualizar AppState com resultado da análise: {exc}",

            )

            # Em caso de falha, não interrompemos necessariamente a execução,

            # mas a UI pode não refletir o último resultado corretamente.



    # ------------------------------------------------------------------

    # Utilitários adicionais (opcionais / de apoio)

    # ------------------------------------------------------------------



    def obter_ultimo_dataframe_processado(self) -> Optional[pd.DataFrame]:

        """

        Retorna o último DataFrame processado (se houver).

        """

        if self.ultimo_resultado is None:

            return None

        return self.ultimo_resultado.df_processado



    def obter_resumo_ultima_analise(self) -> Optional[Dict[str, Any]]:

        """

        Retorna o resumo da última análise (se houver).

        """

        if self.ultimo_resultado is None:

            return None

        return self.ultimo_resultado.resumo



    def obter_metadados_ultima_analise(self) -> Optional[Dict[str, Any]]:

        """

        Retorna os metadados da última análise (se houver).

        """

        if self.ultimo_resultado is None:

            return None

        return self.ultimo_resultado.metadados



    def resolver_caminho_relativo(self, relative_path: str) -> Optional[Path]:

        """

        Resolve um caminho relativo em relação ao BASE_DIR do sistema.



        Ãštil para componentes da UI que recebem apenas o nome de um arquivo

        e precisam localizar o caminho completo dentro da estrutura do

        Integragal.

        """

        try:

            base = Path(BASE_DIR)

            caminho = base / relative_path

        except Exception as exc:  # noqa: BLE001

            registrar_log(

                "erro",

                f"[AnalysisService] Erro ao resolver caminho relativo '{relative_path}': {exc}",

            )

            return None



        if not caminho.exists():

            registrar_log(

                "warning",

                f"[AnalysisService] Caminho relativo '{relative_path}' "

                f"resolvido para '{caminho}', mas o arquivo não existe.",

            )

            return None

        return caminho






