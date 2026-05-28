# -*- coding: utf-8 -*-
"""Writer contratual para logs/corridas_<slug_exame>.csv (SQLite-first)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import pandas as pd

from services.analysis.exam_runs_row_mapper import (
    CORE_FIELDS,
    build_rows,
    dedupe_key,
    ordered_dynamic_columns,
    resolve_logs_dir,
)
from services.persistence.exam_runs_sqlite import ExamRunsSQLiteRepository
from services.core.runtime_flags import is_exam_runs_sqlite_first_enabled
from services.shared_io import flush_and_fsync as _shared_flush_and_fsync
from utils.csv_lock import CSVFileLock
from utils.csv_safety import sanitize_csv_value
from utils.logger import registrar_log
from utils.network_io import RetryPolicy, open_with_retry, path_exists_with_retry


def _flush_and_fsync(handle) -> None:
    """Sincroniza os dados no disco para reduzir risco de perda em queda abrupta."""
    _shared_flush_and_fsync(handle)


def _append_rows_csv(
    *,
    exame_slug: str,
    rows: Sequence[Dict[str, str]],
    logs_dir: Optional[Path | str],
) -> int:
    if not rows:
        return 0

    logs_root = resolve_logs_dir(logs_dir)
    logs_root.mkdir(parents=True, exist_ok=True)
    file_path = logs_root / f"corridas_{exame_slug}.csv"
    policy = RetryPolicy.from_env()

    with CSVFileLock(file_path):
        existing_keys = set()
        if path_exists_with_retry(file_path, policy=policy):
            with open_with_retry(file_path, "rb", policy=policy) as handle:
                if handle.read(3) == b"\xef\xbb\xbf":
                    raise ValueError("ERR_ENCODING: BOM detectado em corridas_<slug_exame>.csv")
            with open_with_retry(file_path, "r", encoding="utf-8", newline="", policy=policy) as handle:
                reader = csv.DictReader(handle, delimiter=",")
                header = [str(col or "").strip() for col in (reader.fieldnames or [])]
                if not set(CORE_FIELDS).issubset(set(header)):
                    raise ValueError("ERR_SCHEMA: colunas core ausentes no arquivo existente")
                for existing in reader:
                    key = dedupe_key(existing)
                    if key is not None:
                        existing_keys.add(key)
        else:
            dynamic_cols = set().union(*(set(row.keys()) - set(CORE_FIELDS) for row in rows))
            header = list(CORE_FIELDS) + ordered_dynamic_columns(dynamic_cols)
            with open_with_retry(file_path, "w", encoding="utf-8", newline="", policy=policy) as handle:
                writer = csv.DictWriter(handle, fieldnames=header, delimiter=",")
                writer.writeheader()
                _flush_and_fsync(handle)

        unique_rows: List[Dict[str, str]] = []
        for row in rows:
            key = dedupe_key(row)
            if key is None or key in existing_keys:
                continue
            existing_keys.add(key)
            unique_rows.append(row)

        if not unique_rows:
            return 0

        with open_with_retry(file_path, "a", encoding="utf-8", newline="", policy=policy) as handle:
            writer = csv.DictWriter(handle, fieldnames=header, delimiter=",")
            for row in unique_rows:
                writer.writerow({col: sanitize_csv_value(row.get(col, "")) for col in header})
            _flush_and_fsync(handle)

    registrar_log(
        "ExamRunsCSV",
        f"Writer por exame atualizado: {file_path.name} (+{len(unique_rows)} linhas).",
        "INFO",
    )
    return len(unique_rows)


def append_exam_runs_csv(
    *,
    df: pd.DataFrame,
    exame: str,
    lote: str,
    data_exame: str,
    corrida_id: Optional[str] = None,
    equipamento_id: str = "",
    equipamento_modelo: str = "",
    logs_dir: Optional[Path | str] = None,
    arquivo_corrida: str = "",
    usuario_execucao: str = "",
    nome_corrida: str = "",
    quem_fez_extracao: str = "",
    quem_preparou_placa: str = "",
    observacoes: str = "",
    timestamp_execucao: str = "",
    sqlite_db_path: Optional[Path | str] = None,
    use_sqlite_first: Optional[bool] = None,
) -> int:
    """Persiste historico por exame em modo SQLite-first com fallback CSV."""
    if df is None or df.empty:
        return 0

    exame_slug, rows = build_rows(
        df=df,
        exame=exame,
        lote=lote,
        data_exame=data_exame,
        corrida_id=corrida_id,
        equipamento_id=equipamento_id,
        equipamento_modelo=equipamento_modelo,
        arquivo_corrida=arquivo_corrida,
        usuario_execucao=usuario_execucao,
        nome_corrida=nome_corrida,
        quem_fez_extracao=quem_fez_extracao,
        quem_preparou_placa=quem_preparou_placa,
        observacoes=observacoes,
        timestamp_execucao=timestamp_execucao,
    )
    if not rows:
        return 0

    sqlite_first = (
        is_exam_runs_sqlite_first_enabled()
        if use_sqlite_first is None
        else bool(use_sqlite_first)
    )
    rows_for_csv: Sequence[Dict[str, str]] = rows
    inserted_sql = 0

    if sqlite_first:
        try:
            repo = ExamRunsSQLiteRepository(db_path=sqlite_db_path)
            inserted_rows = repo.append_rows(rows)
            inserted_sql = len(inserted_rows)
            rows_for_csv = inserted_rows
        except Exception as exc:
            registrar_log(
                "ExamRunsCSV",
                f"Falha em SQLite-first; aplicando fallback CSV: {exc}",
                "WARNING",
            )
            rows_for_csv = rows

    inserted_csv = _append_rows_csv(
        exame_slug=exame_slug,
        rows=rows_for_csv,
        logs_dir=logs_dir,
    )
    return inserted_sql if sqlite_first else inserted_csv
