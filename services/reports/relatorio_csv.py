# -*- coding: utf-8 -*-
"""
Escrita do relatorio.csv de envio GAL com transicoes de status.

Requisitos:
- Codificacao utf-8 sem BOM (padrao operacional).
- Uma linha por amostra (100% das amostras processadas).
- Timestamps para cada transicao de status definida no contrato.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from services.persistence.csv_contracts import get_csv_contract
from services.shared_text import safe_str_no_strip as _shared_safe_str_no_strip
from utils.csv_lock import CSVFileLock
from utils.privacy import mask_patient_name
from utils.csv_safety import sanitize_csv_value
from utils.network_io import RetryPolicy, open_with_retry, path_exists_with_retry

_RELATORIO_CONTRACT = get_csv_contract("relatorio.csv")
_RELATORIO_DELIMITER = _RELATORIO_CONTRACT.delimiter if _RELATORIO_CONTRACT else ";"
_RELATORIO_ENCODING = _RELATORIO_CONTRACT.encoding if _RELATORIO_CONTRACT else "utf-8"

RELATORIO_HEADERS: List[str] = [
    "run_id",
    "corrida_id",
    "exame_id",
    "codigo_amostra",
    "selecionado_envio",
    "status_item",
    "paciente",
    "usuario",
    "kit",
    "lote",
    "data_exame",
    "arquivo_corrida",
    "arquivo_extracao",
    "parte_placa",
    "numero_extracao",
    "nome_corrida",
    "quem_fez_extracao",
    "quem_preparou_placa",
    "observacoes_corrida",
    "qualidade_opcional",
    "observacao",
    "status_inicial",
    "ts_status_inicial",
    "status_envio",
    "ts_status_envio",
    "status_final",
    "ts_status_final",
    "status_atual",
    "erro",
    "campos_invalidos",
]


def _safe_str(value: Any) -> str:
    """Converte valores para string segura."""
    return _shared_safe_str_no_strip(value)


def _join_errors(errors: Any) -> str:
    """Normaliza lista de erros para string unica."""
    if isinstance(errors, list):
        return "; ".join(_safe_str(e) for e in errors if e is not None)
    return _safe_str(errors)


def _optional_quality(item: Dict[str, Any]) -> str:
    fields = (
        _safe_str(item.get("nome_corrida", "")),
        _safe_str(item.get("quem_fez_extracao", "")),
        _safe_str(item.get("quem_preparou_placa", "")),
        _safe_str(item.get("observacoes_corrida", "")),
    )
    filled = sum(1 for value in fields if value)
    if filled == 0:
        return "vazio"
    if filled == 4:
        return "completo"
    return "parcial"


def build_relatorio_rows(
    relatorio_local: Iterable[Dict[str, Any]],
    usuario: str,
    kit: str,
    observacao: str,
    run_id: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Constrói linhas normalizadas para o relatorio.csv.

    Args:
        relatorio_local: Lista de resultados por amostra.
        usuario: Usuário responsável pelo envio.
        kit: Código do kit utilizado.
        observacao: Observação geral do envio.
        run_id: Identificador da execução (opcional).

    Returns:
        Lista de dicionários com colunas normalizadas.
    """
    resolved_run_id = run_id or datetime.now().strftime("%Y%m%dT%H%M%S")
    rows: List[Dict[str, str]] = []

    for item in relatorio_local:
        codigo = item.get("codigoAmostra") or item.get("registroInterno") or ""
        status_atual = item.get("status") or item.get("status_final") or ""
        campos_invalidos = item.get("campos_invalidos") or []
        campos_invalidos_str = json.dumps(campos_invalidos, ensure_ascii=False)

        row = {
            "run_id": _safe_str(resolved_run_id),
            "corrida_id": _safe_str(item.get("corrida_id", "")),
            "exame_id": _safe_str(item.get("exame_id", "")),
            "codigo_amostra": _safe_str(codigo).strip(),
            "selecionado_envio": _safe_str(item.get("selecionado_envio", "true")),
            "status_item": _safe_str(item.get("status_item", status_atual)),
            "paciente": mask_patient_name(item.get("paciente", "")),
            "usuario": _safe_str(usuario),
            "kit": _safe_str(kit),
            "lote": _safe_str(item.get("lote", item.get("loteKit", ""))),
            "data_exame": _safe_str(item.get("data_exame", "")),
            "arquivo_corrida": _safe_str(item.get("arquivo_corrida", "")),
            "arquivo_extracao": _safe_str(item.get("arquivo_extracao", "")),
            "parte_placa": _safe_str(item.get("parte_placa", "")),
            "numero_extracao": _safe_str(item.get("numero_extracao", "")),
            "nome_corrida": _safe_str(item.get("nome_corrida", "")),
            "quem_fez_extracao": _safe_str(item.get("quem_fez_extracao", "")),
            "quem_preparou_placa": _safe_str(item.get("quem_preparou_placa", "")),
            "observacoes_corrida": _safe_str(item.get("observacoes_corrida", "")),
            "qualidade_opcional": _optional_quality(item),
            "observacao": _safe_str(observacao),
            "status_inicial": _safe_str(item.get("status_inicial", "")),
            "ts_status_inicial": _safe_str(item.get("ts_status_inicial", "")),
            "status_envio": _safe_str(item.get("status_envio", "")),
            "ts_status_envio": _safe_str(item.get("ts_status_envio", "")),
            "status_final": _safe_str(item.get("status_final", status_atual)),
            "ts_status_final": _safe_str(item.get("ts_status_final", "")),
            "status_atual": _safe_str(status_atual),
            "erro": _join_errors(item.get("erro", "")),
            "campos_invalidos": campos_invalidos_str,
        }
        rows.append(row)

    return rows


def write_relatorio_csv(path: Path, rows: Iterable[Dict[str, str]]) -> None:
    """
    Grava relatorio.csv com encoding utf-8 sem BOM via context manager.

    Args:
        path: Caminho do relatorio.csv.
        rows: Linhas normalizadas para escrita.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    policy = RetryPolicy.from_env()

    with CSVFileLock(path):
        file_exists = path_exists_with_retry(path, policy=policy) and path.stat().st_size > 0
        with open_with_retry(
            path, "a", encoding=_RELATORIO_ENCODING, newline="", policy=policy
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=RELATORIO_HEADERS,
                delimiter=_RELATORIO_DELIMITER,
            )
            if not file_exists:
                writer.writeheader()
            for row in rows:
                writer.writerow(
                    {h: sanitize_csv_value(row.get(h, "")) for h in RELATORIO_HEADERS}
                )
