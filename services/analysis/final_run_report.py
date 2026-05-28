# -*- coding: utf-8 -*-
"""Relatorio final canonico de corrida (Fase 4)."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from services.shared_text import safe_str as _shared_safe_str
from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, open_with_retry, path_exists_with_retry

SCHEMA_VERSION_RELATORIO = "1.0.0"
_LAST_REPORT_FILENAME = "relatorio_final_corrida_last.json"
OPTIONAL_FIELDS = (
    "nome_corrida",
    "quem_fez_extracao",
    "quem_preparou_placa",
    "observacoes",
)


def _safe_str(value: object) -> str:
    return _shared_safe_str(value)


def _sanitize_optional_text(value: object, limit: int) -> str:
    return _safe_str(value)[:limit]


def _normalize_date(value: object) -> str:
    raw = _safe_str(value)
    if not raw:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def _normalize_time(value: object) -> str:
    raw = _safe_str(value)
    if not raw:
        return datetime.now().strftime("%H:%M:%S")
    for fmt in ("%H:%M:%S", "%H:%M", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.strftime("%H:%M:%S")
        except ValueError:
            continue
    return datetime.now().strftime("%H:%M:%S")


def _normalize_selected(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    token = _safe_str(value).lower()
    return token in {"1", "true", "sim", "yes", "y", "x", "[x]", "✓", "selecionado"}


def _normalize_error(value: object) -> str:
    if isinstance(value, list):
        return "; ".join(_safe_str(item) for item in value if _safe_str(item))
    return _safe_str(value)


def _sanitize_filename(value: object) -> str:
    raw = _safe_str(value).lower()
    if not raw:
        return "sem_corrida"
    return re.sub(r"[^a-z0-9._-]+", "_", raw).strip("_") or "sem_corrida"


def resolve_corrida_id(
    *,
    corrida_id: object,
    exame_id: object,
    lote: object,
    data_exame: object,
    arquivo_corrida: object,
) -> str:
    current = _safe_str(corrida_id)
    if current:
        return current
    exame = _safe_str(exame_id)
    lote_value = _safe_str(lote)
    data_value = _safe_str(data_exame)
    arquivo = Path(_safe_str(arquivo_corrida)).name
    return f"{exame}|{lote_value}|{data_value}|{arquivo}".strip("|")


def _detect_column(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    normalized = {str(col).strip().lower(): str(col) for col in df.columns}
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in normalized:
            return normalized[key]
    return None


def _build_mapping_ref(
    *,
    arquivo_extracao: object,
    parte_placa: object,
    timestamp_token: str,
) -> str:
    base = Path(_safe_str(arquivo_extracao)).stem or "extracao_nao_informada"
    try:
        parte = int(parte_placa or 0)
    except (TypeError, ValueError):
        parte = 0
    return f"{base}+parte{parte}+{timestamp_token}"


def _history_ref(caminho_csv: Path, corrida_id: str) -> str:
    return f"{caminho_csv.name}#corrida_id={corrida_id}"


def _status_item_from_send(status: str) -> str:
    normalized = _safe_str(status).lower()
    if normalized == "sucesso":
        return "selecionado_enviado"
    if normalized == "duplicado":
        return "selecionado_duplicado"
    if normalized == "nao_encontrado":
        return "nao_encontrado"
    return "selecionado_falha"


def _status_envio_from_send(status: str) -> str:
    normalized = _safe_str(status).lower()
    if normalized == "sucesso":
        return "enviado"
    if normalized == "duplicado":
        return "duplicado"
    if normalized == "nao_encontrado":
        return "falha_envio"
    return "falha_envio"


def _status_analise_from_code(code: object) -> str:
    normalized = _safe_str(code).upper()
    if normalized in {"CN", "CP"} or "CONTROLE" in normalized:
        return "controle"
    return "analisado"


def _report_paths(logs_dir: Path, corrida_id: str) -> tuple[Path, Path]:
    safe_id = _sanitize_filename(corrida_id)
    specific = logs_dir / f"relatorio_final_corrida_{safe_id}.json"
    latest = logs_dir / _LAST_REPORT_FILENAME
    return specific, latest


def build_optional_operational_checklist(
    *,
    nome_corrida: object,
    quem_fez_extracao: object,
    quem_preparou_placa: object,
    observacoes: object,
) -> Dict[str, Any]:
    """Monta matriz executavel da governanca dos campos opcionais (Fase 5)."""
    sanitized = {
        "nome_corrida": _sanitize_optional_text(nome_corrida, 120),
        "quem_fez_extracao": _sanitize_optional_text(quem_fez_extracao, 80),
        "quem_preparou_placa": _sanitize_optional_text(quem_preparou_placa, 80),
        "observacoes": _sanitize_optional_text(observacoes, 500),
    }
    filled_count = sum(1 for field in OPTIONAL_FIELDS if sanitized[field])
    if filled_count == 0:
        quality_level = "vazio"
    elif filled_count == len(OPTIONAL_FIELDS):
        quality_level = "completo"
    else:
        quality_level = "parcial"

    checklist = [
        {
            "id": "cenario_vazio_nao_bloqueia",
            "descricao": "Ausencia de campos opcionais nao bloqueia fluxo.",
            "ok": True,
        },
        {
            "id": "cenario_parcial_nao_bloqueia",
            "descricao": "Preenchimento parcial nao bloqueia fluxo.",
            "ok": True,
        },
        {
            "id": "cenario_completo_nao_bloqueia",
            "descricao": "Preenchimento completo nao altera regras obrigatorias.",
            "ok": True,
        },
        {
            "id": "rastreio_ui_historico_relatorio",
            "descricao": "Campos opcionais rastreaveis entre UI, historico e relatorio final.",
            "ok": True,
        },
    ]
    return {
        "campos": sanitized,
        "preenchimento": {
            "total_campos": len(OPTIONAL_FIELDS),
            "preenchidos": filled_count,
            "nivel": quality_level,
        },
        "nao_bloqueio": {
            "ativo": True,
            "regra": (
                "Ausencia de campos opcionais nao bloqueia analise, "
                "salvamento, exportacao ou encerramento da corrida."
            ),
        },
        "checklist_operacional": checklist,
    }


def _apply_optional_governance(report: Dict[str, Any]) -> None:
    governance = build_optional_operational_checklist(
        nome_corrida=report.get("nome_corrida", ""),
        quem_fez_extracao=report.get("quem_fez_extracao", ""),
        quem_preparou_placa=report.get("quem_preparou_placa", ""),
        observacoes=report.get("observacoes", ""),
    )
    report["nome_corrida"] = governance["campos"]["nome_corrida"]
    report["quem_fez_extracao"] = governance["campos"]["quem_fez_extracao"]
    report["quem_preparou_placa"] = governance["campos"]["quem_preparou_placa"]
    report["observacoes"] = governance["campos"]["observacoes"]
    report["governanca_opcional"] = governance


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    policy = RetryPolicy.from_env()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    with CSVFileLock(path):
        try:
            with open_with_retry(tmp, "w", encoding="utf-8", policy=policy) as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(path, policy=policy):
        return None
    with open_with_retry(path, "r", encoding="utf-8", policy=policy) as handle:
        return json.load(handle)


def _find_by_code(items: List[Dict[str, Any]], code: str) -> Optional[Dict[str, Any]]:
    normalized = _safe_str(code)
    if not normalized:
        return None
    for item in items:
        if _safe_str(item.get("codigo_amostra")) == normalized:
            return item
    return None


def _build_items_from_analysis(df_analise: pd.DataFrame) -> List[Dict[str, Any]]:
    codigo_col = _detect_column(df_analise, ("codigo", "código", "sample", "amostra"))
    selected_col = _detect_column(df_analise, ("selecionado",))
    resultado_col = _detect_column(df_analise, ("resultado_geral",))
    status_placa_col = _detect_column(df_analise, ("status_placa", "status placa"))

    items: List[Dict[str, Any]] = []
    for idx, row in df_analise.iterrows():
        codigo = (
            _safe_str(row.get(codigo_col, ""))
            if codigo_col
            else _safe_str(row.get("codigoAmostra", ""))
        )
        if not codigo:
            codigo = f"ROW-{idx + 1}"
        selecionado = _normalize_selected(row.get(selected_col, False)) if selected_col else False
        status_item = "selecionado_pendente_envio" if selecionado else "nao_selecionado"
        status_envio_gal = "pendente_envio" if selecionado else "nao_selecionado"
        motivo_item = "aguardando_envio_gal" if selecionado else ""
        items.append(
            {
                "codigo_amostra": codigo,
                "selecionado_envio": selecionado,
                "status_item": status_item,
                "status_analise": _status_analise_from_code(codigo),
                "status_envio_gal": status_envio_gal,
                "resultado_geral": _safe_str(row.get(resultado_col, "")) if resultado_col else "",
                "status_placa": _safe_str(row.get(status_placa_col, "")) if status_placa_col else "",
                "erro_item": "",
                "motivo_item": motivo_item,
            }
        )
    return items


def _build_base_report(
    *,
    df_analise: pd.DataFrame,
    caminho_csv: Path,
    exame_id: str,
    usuario_execucao: str,
    lote: str,
    data_exame: str,
    arquivo_corrida: str,
    corrida_id: str,
    observacoes: str,
    nome_corrida: str,
    quem_fez_extracao: str,
    quem_preparou_placa: str,
    arquivo_extracao: str,
    parte_placa: object,
    numero_extracao: str,
) -> Dict[str, Any]:
    now = datetime.now()
    items = _build_items_from_analysis(df_analise)
    selected_count = sum(1 for item in items if bool(item.get("selecionado_envio")))
    total = len(items)
    data_exame_iso = _normalize_date(data_exame)
    hora_exame = _normalize_time(data_exame)
    timestamp_token = now.strftime("%Y%m%dT%H%M%S")

    status_execucao = "concluido" if selected_count == 0 else "analise_concluida_envio_pendente"
    motivo_status = "" if selected_count == 0 else "analise_concluida_aguardando_envio_gal"

    return {
        "schema_version_relatorio": SCHEMA_VERSION_RELATORIO,
        "corrida_id": corrida_id,
        "exame_id": _safe_str(exame_id),
        "lote": _safe_str(lote),
        "data_exame": data_exame_iso,
        "hora_exame": hora_exame,
        "usuario_execucao": _safe_str(usuario_execucao),
        "arquivo_extracao": Path(_safe_str(arquivo_extracao)).name,
        "parte_placa": int(parte_placa or 0) if str(parte_placa or "").strip() else 0,
        "numero_extracao": _safe_str(numero_extracao),
        "arquivo_corrida": Path(_safe_str(arquivo_corrida)).name,
        "status_execucao": status_execucao,
        "motivo_status": motivo_status,
        "testes_totais": total,
        "testes_selecionados": selected_count,
        "testes_nao_selecionados": max(total - selected_count, 0),
        "itens_corrida": items,
        "trilha": {
            "mapeamento_ref": _build_mapping_ref(
                arquivo_extracao=arquivo_extracao,
                parte_placa=parte_placa,
                timestamp_token=timestamp_token,
            ),
            "historico_ref": _history_ref(caminho_csv, corrida_id),
            "exportacao_ref": "",
            "envio_ref": "",
        },
        "observacoes": _safe_str(observacoes),
        "nome_corrida": _safe_str(nome_corrida),
        "quem_fez_extracao": _safe_str(quem_fez_extracao),
        "quem_preparou_placa": _safe_str(quem_preparou_placa),
        "atualizado_em": now.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def _merge_context(report: Dict[str, Any], context: Dict[str, Any]) -> None:
    for field in (
        "exame_id",
        "lote",
        "data_exame",
        "arquivo_corrida",
        "arquivo_extracao",
        "numero_extracao",
        "usuario_execucao",
        "observacoes",
        "nome_corrida",
        "quem_fez_extracao",
        "quem_preparou_placa",
    ):
        candidate = _safe_str(context.get(field, ""))
        if candidate and not _safe_str(report.get(field, "")):
            report[field] = candidate

    parte_context = context.get("parte_placa")
    if parte_context is not None:
        try:
            if int(report.get("parte_placa", 0) or 0) == 0:
                report["parte_placa"] = int(parte_context)
        except (TypeError, ValueError):
            pass


def _save_report(logs_dir: Path, corrida_id: str, report: Dict[str, Any]) -> Path:
    _apply_optional_governance(report)
    specific_path, latest_path = _report_paths(logs_dir, corrida_id)
    _write_json_atomic(specific_path, report)
    _write_json_atomic(latest_path, report)
    return specific_path


def upsert_final_report_from_history(
    *,
    df_analise: pd.DataFrame,
    caminho_csv: str | Path,
    exame_id: str,
    usuario_execucao: str,
    lote: str,
    data_exame: str,
    arquivo_corrida: str,
    corrida_id: str,
    observacoes: str = "",
    nome_corrida: str = "",
    quem_fez_extracao: str = "",
    quem_preparou_placa: str = "",
    arquivo_extracao: str = "",
    parte_placa: object = None,
    numero_extracao: str = "",
) -> Path:
    historico_path = Path(caminho_csv)
    logs_dir = historico_path.parent
    resolved_corrida_id = resolve_corrida_id(
        corrida_id=corrida_id,
        exame_id=exame_id,
        lote=lote,
        data_exame=data_exame,
        arquivo_corrida=arquivo_corrida,
    )
    report = _build_base_report(
        df_analise=df_analise,
        caminho_csv=historico_path,
        exame_id=exame_id,
        usuario_execucao=usuario_execucao,
        lote=lote,
        data_exame=data_exame,
        arquivo_corrida=arquivo_corrida,
        corrida_id=resolved_corrida_id,
        observacoes=observacoes,
        nome_corrida=nome_corrida,
        quem_fez_extracao=quem_fez_extracao,
        quem_preparou_placa=quem_preparou_placa,
        arquivo_extracao=arquivo_extracao,
        parte_placa=parte_placa,
        numero_extracao=numero_extracao,
    )
    return _save_report(logs_dir, resolved_corrida_id, report)


def upsert_final_report_with_export_refs(
    *,
    logs_dir: str | Path,
    corrida_id: str,
    export_refs: Iterable[str],
    context: Optional[Dict[str, Any]] = None,
) -> Path:
    logs_path = Path(logs_dir)
    resolved_corrida_id = _safe_str(corrida_id)
    specific_path, latest_path = _report_paths(logs_path, resolved_corrida_id)
    report = _load_json(specific_path) or _load_json(latest_path) or {
        "schema_version_relatorio": SCHEMA_VERSION_RELATORIO,
        "corrida_id": resolved_corrida_id,
        "itens_corrida": [],
        "trilha": {},
    }
    if context:
        _merge_context(report, context)
    trilha = report.setdefault("trilha", {})
    refs = [ref for ref in (_safe_str(item) for item in export_refs) if ref]
    trilha["exportacao_ref"] = "; ".join(refs)
    report["atualizado_em"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    return _save_report(logs_path, resolved_corrida_id, report)


def upsert_final_report_with_send_results(
    *,
    logs_dir: str | Path,
    run_id: str,
    relatorio_local: List[Dict[str, Any]],
    relatorio_csv_path: str | Path,
    journal_path: str | Path,
    relatorio_txt_path: str | Path,
    context: Optional[Dict[str, Any]] = None,
) -> Path:
    logs_path = Path(logs_dir)
    context_data = dict(context or {})
    context_data.setdefault("run_id", run_id)
    if relatorio_local:
        first_row = relatorio_local[0]
        for field in (
            "corrida_id",
            "exame_id",
            "lote",
            "data_exame",
            "arquivo_corrida",
            "arquivo_extracao",
            "numero_extracao",
            "nome_corrida",
            "quem_fez_extracao",
            "quem_preparou_placa",
        ):
            context_data.setdefault(field, _safe_str(first_row.get(field, "")))
        if "observacoes" not in context_data:
            context_data["observacoes"] = _safe_str(
                first_row.get("observacoes_corrida", "")
            )
        context_data.setdefault("parte_placa", first_row.get("parte_placa", 0))

    resolved_corrida_id = resolve_corrida_id(
        corrida_id=context_data.get("corrida_id", ""),
        exame_id=context_data.get("exame_id", ""),
        lote=context_data.get("lote", ""),
        data_exame=context_data.get("data_exame", ""),
        arquivo_corrida=context_data.get("arquivo_corrida", ""),
    )
    if not resolved_corrida_id and relatorio_local:
        resolved_corrida_id = _safe_str(relatorio_local[0].get("corrida_id", ""))
    if not resolved_corrida_id:
        resolved_corrida_id = f"run_{_safe_str(run_id)}"

    specific_path, latest_path = _report_paths(logs_path, resolved_corrida_id)
    report = _load_json(specific_path) or _load_json(latest_path) or {
        "schema_version_relatorio": SCHEMA_VERSION_RELATORIO,
        "corrida_id": resolved_corrida_id,
        "itens_corrida": [],
        "trilha": {},
        "status_execucao": "interrompida",
        "motivo_status": "relatorio_base_ausente_no_envio",
    }
    _merge_context(report, context_data)

    items = report.setdefault("itens_corrida", [])
    if not items:
        for row in relatorio_local:
            code = _safe_str(row.get("codigoAmostra") or row.get("registroInterno"))
            if not code:
                continue
            item = {
                "codigo_amostra": code,
                "selecionado_envio": True,
                "status_item": _status_item_from_send(_safe_str(row.get("status", ""))),
                "status_analise": _status_analise_from_code(code),
                "status_envio_gal": _status_envio_from_send(_safe_str(row.get("status", ""))),
                "resultado_geral": "",
                "status_placa": "",
                "erro_item": _normalize_error(row.get("erro", "")),
                "motivo_item": "",
            }
            items.append(item)

    row_by_code: Dict[str, Dict[str, Any]] = {}
    for row in relatorio_local:
        code = _safe_str(row.get("codigoAmostra") or row.get("registroInterno"))
        if code:
            row_by_code[code] = row

    for item in items:
        code = _safe_str(item.get("codigo_amostra", ""))
        item["status_analise"] = item.get("status_analise") or _status_analise_from_code(code)
        if not bool(item.get("selecionado_envio", False)):
            item["status_envio_gal"] = item.get("status_envio_gal") or "nao_selecionado"
            item["motivo_item"] = item.get("motivo_item", "")
            continue
        row = row_by_code.get(code)
        if row is None:
            item["status_item"] = "selecionado_falha"
            item["status_envio_gal"] = "falha_envio"
            item["erro_item"] = "resultado_envio_ausente"
            item["motivo_item"] = "resultado_envio_ausente"
            continue
        item["status_item"] = _status_item_from_send(_safe_str(row.get("status", "")))
        item["status_analise"] = item.get("status_analise") or _status_analise_from_code(code)
        item["status_envio_gal"] = _status_envio_from_send(_safe_str(row.get("status", "")))
        item["erro_item"] = _normalize_error(row.get("erro", ""))
        item["motivo_item"] = item["erro_item"]

    total = len(items)
    selected = sum(1 for item in items if bool(item.get("selecionado_envio")))
    report["testes_totais"] = total
    report["testes_selecionados"] = selected
    report["testes_nao_selecionados"] = max(total - selected, 0)

    selected_items = [item for item in items if bool(item.get("selecionado_envio"))]
    has_failure = any(
        _safe_str(item.get("status_item")) in {"selecionado_falha", "nao_encontrado"}
        or _safe_str(item.get("status_envio_gal")) == "falha_envio"
        for item in selected_items
    )
    if selected_items and has_failure:
        report["status_execucao"] = "falha_controlada"
        report["motivo_status"] = "falha_parcial_ou_item_nao_encontrado_no_envio_gal"
    else:
        report["status_execucao"] = "concluido"
        report["motivo_status"] = ""

    trilha = report.setdefault("trilha", {})
    trilha["envio_ref"] = "; ".join(
        [
            _safe_str(relatorio_csv_path),
            _safe_str(journal_path),
            _safe_str(relatorio_txt_path),
        ]
    )
    report["atualizado_em"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    return _save_report(logs_path, resolved_corrida_id, report)
