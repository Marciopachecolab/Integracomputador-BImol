# -*- coding: utf-8 -*-
"""Geracao do artefato completo de corrida (CSV por execucao)."""

from __future__ import annotations

import csv
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import pandas as pd

from services.core.config_service import config_service
from services.analysis.full_run_contract import (
    FullRunMetadata,
    build_full_run_metadata,
    build_full_run_row,
    classify_sample_status,
    normalize_source_column_name,
)
from services.shared_io import flush_and_fsync as _shared_flush_and_fsync
from services.shared_text import safe_str as _shared_safe_str
from utils.csv_lock import CSVFileLock
from utils.csv_safety import sanitize_csv_value
from utils.logger import registrar_log
from utils.network_io import RetryPolicy, open_with_retry


def _safe_str(value: object) -> str:
    return _shared_safe_str(value)


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    token = _safe_str(value).lower()
    return token in {"1", "true", "yes", "sim", "y", "x", "[x]", "selecionado"}


def _pick_column(columns: Iterable[str], aliases: Iterable[str]) -> Optional[str]:
    normalized = {normalize_source_column_name(col): col for col in columns}
    for alias in aliases:
        key = normalize_source_column_name(alias)
        if key in normalized:
            return normalized[key]
    return None


def _sanitize_filename(value: object) -> str:
    raw = _safe_str(value).lower()
    safe = re.sub(r"[^a-z0-9._-]+", "_", raw).strip("_")
    return safe or "corrida"


def _resolve_reports_dir(reports_dir: Optional[str] = None) -> Path:
    if reports_dir:
        return Path(reports_dir)
    try:
        paths = config_service.get_paths()
        value = (
            paths.get("reports_dir")
            or paths.get("default_results_folder")
            or "reports"
        )
    except Exception:
        value = "reports"
    return Path(value)


def _flush_and_fsync(handle) -> None:
    _shared_flush_and_fsync(handle)


def _build_records(
    *,
    df: pd.DataFrame,
    metadata: FullRunMetadata,
) -> List[Dict[str, str]]:
    codigo_col = _pick_column(df.columns, ("amostra_codigo", "codigo", "código", "code"))
    selecionado_col = _pick_column(df.columns, ("selecionado",))
    envio_status_col = _pick_column(
        df.columns,
        ("status_gal", "status_envio", "envio_status"),
    )

    records: List[Dict[str, str]] = []
    for _, src in df.iterrows():
        source_row: Mapping[str, Any] = src.to_dict()
        codigo = src.get(codigo_col, "") if codigo_col else ""
        selecionado = _to_bool(src.get(selecionado_col, False)) if selecionado_col else False
        envio_status = src.get(envio_status_col, "") if envio_status_col else ""
        status = classify_sample_status(
            codigo=codigo,
            selecionado=selecionado,
            envio_status=envio_status,
        )
        records.append(
            build_full_run_row(
                source_row=source_row,
                metadata=metadata,
                status_amostra_corrida=status,
            )
        )
    return records


def _fieldnames_from_records(records: List[Dict[str, str]]) -> List[str]:
    if not records:
        return []
    ordered = list(records[0].keys())
    seen = set(ordered)
    for row in records[1:]:
        for key in row.keys():
            if key in seen:
                continue
            ordered.append(key)
            seen.add(key)
    return ordered


def write_full_run_artifact_csv(
    *,
    df: pd.DataFrame,
    exame: object,
    lote: object,
    data_exame: object,
    usuario: object,
    arquivo_corrida: object,
    corrida_id: object = "",
    nome_corrida: object = "",
    quem_fez_extracao: object = "",
    quem_preparou_placa: object = "",
    observacoes: object = "",
    reports_dir: Optional[str] = None,
    timestamp_execucao: object = "",
) -> Path:
    """Gera CSV completo da corrida (todas as linhas da analise + metadados)."""
    if df is None or df.empty:
        raise ValueError("df vazio para artefato de corrida completa")

    metadata = build_full_run_metadata(
        exame=exame,
        lote=lote,
        data_exame=data_exame,
        usuario=usuario,
        arquivo_corrida=arquivo_corrida,
        corrida_id=corrida_id,
        nome_corrida=nome_corrida,
        quem_fez_extracao=quem_fez_extracao,
        quem_preparou_placa=quem_preparou_placa,
        observacoes=observacoes,
        timestamp_execucao=timestamp_execucao,
    )
    records = _build_records(df=df, metadata=metadata)
    if not records:
        raise ValueError("nenhum registro valido para artefato de corrida completa")

    fieldnames = _fieldnames_from_records(records)
    if not fieldnames:
        raise ValueError("falha ao resolver colunas do artefato de corrida completa")

    root = _resolve_reports_dir(reports_dir)
    root.mkdir(parents=True, exist_ok=True)
    ts_token = datetime.now().strftime("%Y%m%dT%H%M%S")
    corrida_token = _sanitize_filename(metadata.corrida_id)
    file_path = root / f"corrida_completa_{corrida_token}_{ts_token}.csv"
    tmp_path = file_path.with_name(f"{file_path.name}.tmp")
    policy = RetryPolicy.from_env()

    with CSVFileLock(file_path):
        try:
            with open_with_retry(
                tmp_path,
                "w",
                encoding="utf-8",
                newline="",
                policy=policy,
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=",")
                writer.writeheader()
                for row in records:
                    writer.writerow(
                        {key: sanitize_csv_value(row.get(key, "")) for key in fieldnames}
                    )
                _flush_and_fsync(handle)
            os.replace(tmp_path, file_path)
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    registrar_log(
        "FullRunArtifact",
        f"Artefato completo da corrida gerado: {file_path}",
        "INFO",
    )
    return file_path
