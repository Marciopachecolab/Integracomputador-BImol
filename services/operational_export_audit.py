# -*- coding: utf-8 -*-
"""Trilha de auditoria para exportacoes do visualizador operacional (F8)."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

from services.shared_paths import resolve_logs_dir as _shared_resolve_logs_dir
from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, open_with_retry, path_exists_with_retry
from utils.logger import registrar_log

_HEADERS = [
    "timestamp",
    "operator",
    "view",
    "file_format",
    "output_file",
    "row_count",
    "corrida_ids",
    "status",
    "error",
]


def _resolve_logs_dir(logs_dir: Optional[str | Path]) -> Path:
    return _shared_resolve_logs_dir(logs_dir)


def get_export_audit_path(*, logs_dir: Optional[str | Path] = None) -> Path:
    """Retorna caminho canonico do arquivo de auditoria de exportacao."""
    return _resolve_logs_dir(logs_dir) / "export_audit_trail.csv"


def _ensure_file(path: Path, policy: RetryPolicy) -> None:
    if path_exists_with_retry(path, policy=policy):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with CSVFileLock(path):
        if path_exists_with_retry(path, policy=policy):
            return
        with open_with_retry(path, "w", newline="", encoding="utf-8", policy=policy) as handle:
            writer = csv.DictWriter(handle, fieldnames=_HEADERS, delimiter=";")
            writer.writeheader()


def record_export_audit(
    *,
    logs_dir: Optional[str | Path],
    operator: str,
    view: str,
    file_format: str,
    output_file: str,
    row_count: int,
    corrida_ids: Iterable[str],
    status: str,
    error: str,
) -> None:
    """Registra evento de exportacao com rastreio por corrida e operador."""
    path = get_export_audit_path(logs_dir=logs_dir)
    policy = RetryPolicy.from_env()
    _ensure_file(path, policy)

    corrida_tokens: List[str] = []
    for value in corrida_ids:
        token = str(value or "").strip()
        if token:
            corrida_tokens.append(token)

    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "operator": str(operator or "").strip(),
        "view": str(view or "").strip(),
        "file_format": str(file_format or "").strip().lower(),
        "output_file": str(output_file or "").strip(),
        "row_count": str(int(row_count)),
        "corrida_ids": ",".join(corrida_tokens),
        "status": str(status or "").strip().lower() or "success",
        "error": str(error or "").strip(),
    }

    try:
        with CSVFileLock(path):
            with open_with_retry(path, "a", newline="", encoding="utf-8", policy=policy) as handle:
                writer = csv.DictWriter(handle, fieldnames=_HEADERS, delimiter=";")
                writer.writerow(payload)
    except Exception as exc:  # pragma: no cover
        registrar_log("ExportAudit", f"Falha ao registrar trilha de exportacao: {exc}", "WARNING")


def read_export_audit(*, logs_dir: Optional[str | Path] = None, limit: int = 200) -> pd.DataFrame:
    """Le eventos recentes de auditoria de exportacao."""
    path = get_export_audit_path(logs_dir=logs_dir)
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(path, policy=policy):
        return pd.DataFrame(columns=_HEADERS)
    try:
        df = pd.read_csv(path, sep=";", encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        registrar_log("ExportAudit", f"Falha ao ler trilha de exportacao: {exc}", "WARNING")
        return pd.DataFrame(columns=_HEADERS)
    if int(limit or 0) > 0 and len(df) > int(limit):
        return df.tail(int(limit)).reset_index(drop=True)
    return df


__all__ = ["get_export_audit_path", "record_export_audit", "read_export_audit"]
