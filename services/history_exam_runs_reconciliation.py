# -*- coding: utf-8 -*-
"""Reconciliacao cruzada entre historico_analises e exam_runs."""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from services.dedupe_keys import DEDUPE_FIELDS, build_dedupe_key
from services.analysis.exam_runs_row_mapper import slugify
from services.persistence.exam_runs_sqlite import ExamRunsSQLiteRepository
from utils.logger import registrar_log

_DEDUPE_KEY = Tuple[str, str, str, str]


@dataclass(frozen=True)
class HistoryExamRunsReconciliationReport:
    exame_slug_filter: Optional[str]
    data_inicio: Optional[str]
    data_fim: Optional[str]
    alert_threshold: float
    block_threshold: float
    history_rows: int
    exam_runs_rows: int
    history_keyed_rows: int
    exam_runs_keyed_rows: int
    history_missing_key_rows: int
    exam_runs_missing_key_rows: int
    history_duplicate_keys: List[str] = field(default_factory=list)
    exam_runs_duplicate_keys: List[str] = field(default_factory=list)
    missing_in_exam_runs: List[str] = field(default_factory=list)
    missing_in_history: List[str] = field(default_factory=list)
    field_mismatches: List[str] = field(default_factory=list)
    inconsistency_rate: float = 0.0
    alert_level: str = "ok"
    is_consistent: bool = True


def _clean(value: object) -> str:
    return str(value or "").strip()


def _normalize(value: object) -> str:
    return _clean(value).lower()


def _serialize_key(key: _DEDUPE_KEY) -> str:
    return "|".join(key)


def _parse_date(value: Optional[str]) -> Optional[date]:
    raw = _clean(value)
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _date_in_range(value: object, start: Optional[date], end: Optional[date]) -> bool:
    if start is None and end is None:
        return True
    parsed = _parse_date(_clean(value))
    if parsed is None:
        return False
    if start is not None and parsed < start:
        return False
    if end is not None and parsed > end:
        return False
    return True


def _history_table_exists(db_path: Path) -> bool:
    if not db_path.exists():
        return False
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='historico_analises' LIMIT 1"
        ).fetchone()
    return bool(row)


def _read_history_rows_sqlite(db_path: Path) -> List[Dict[str, str]]:
    if not _history_table_exists(db_path):
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT exame, equipamento, status_corrida, corrida_id, amostra_codigo, lote, data_exame
            FROM historico_analises
            """
        ).fetchall()
    return [{str(k): _clean(v) for k, v in dict(row).items()} for row in rows]


def _read_history_rows_csv(csv_path: Path) -> List[Dict[str, str]]:
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        return [{str(k): _clean(v) for k, v in row.items()} for row in reader]


def _read_exam_runs_rows_sqlite(db_path: Path) -> List[Dict[str, str]]:
    if not db_path.exists():
        return []
    repo = ExamRunsSQLiteRepository(db_path=db_path)
    return [{str(k): _clean(v) for k, v in row.items()} for row in repo.list_rows()]


def _read_exam_runs_rows_csv(logs_dir: Path, exame_slug: Optional[str]) -> List[Dict[str, str]]:
    candidates: Sequence[Path]
    if exame_slug:
        candidates = [logs_dir / f"corridas_{exame_slug}.csv"]
    else:
        candidates = sorted(logs_dir.glob("corridas_*.csv"))
    rows: List[Dict[str, str]] = []
    for path in candidates:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=",")
            for row in reader:
                payload = {str(k): _clean(v) for k, v in row.items()}
                if not payload.get("exame_slug"):
                    payload["exame_slug"] = path.stem.replace("corridas_", "", 1)
                rows.append(payload)
    return rows


def _history_matches_filter(
    row: Dict[str, str],
    *,
    exame_slug: Optional[str],
    start: Optional[date],
    end: Optional[date],
) -> bool:
    if exame_slug:
        if slugify(_clean(row.get("exame", ""))) != exame_slug:
            return False
    return _date_in_range(row.get("data_exame", ""), start, end)


def _exam_runs_matches_filter(
    row: Dict[str, str],
    *,
    exame_slug: Optional[str],
    start: Optional[date],
    end: Optional[date],
) -> bool:
    if exame_slug and _normalize(row.get("exame_slug", "")) != _normalize(exame_slug):
        return False
    return _date_in_range(row.get("data_exame", ""), start, end)


def _dedupe_key(row: Dict[str, str]) -> Optional[_DEDUPE_KEY]:
    key = build_dedupe_key(row, fields=DEDUPE_FIELDS)
    if key is None:
        return None
    # Normaliza corrida_id: CSV usa display name (spaces), exam_runs usa slug (underscores)
    corrida_id = slugify(key[0]) if key[0] else key[0]
    return corrida_id, key[1], key[2], key[3]


def _index_rows(
    rows: Iterable[Dict[str, str]],
) -> tuple[Dict[_DEDUPE_KEY, Dict[str, str]], int, List[str]]:
    indexed: Dict[_DEDUPE_KEY, Dict[str, str]] = {}
    missing_key_rows = 0
    duplicates: set[str] = set()
    for row in rows:
        key = _dedupe_key(row)
        if key is None:
            missing_key_rows += 1
            continue
        if key in indexed:
            duplicates.add(_serialize_key(key))
            continue
        indexed[key] = row
    return indexed, missing_key_rows, sorted(duplicates)


def _field_mismatch_fields(history_row: Dict[str, str], exam_row: Dict[str, str]) -> List[str]:
    mismatches: List[str] = []
    if slugify(_clean(history_row.get("exame", ""))) != _normalize(exam_row.get("exame_slug", "")):
        mismatches.append("exame_slug")
    if _normalize(history_row.get("status_corrida", "")) != _normalize(exam_row.get("status_placa", "")):
        mismatches.append("status")
    history_equip = _normalize(history_row.get("equipamento", ""))
    exam_equip = _normalize(exam_row.get("equipamento_modelo", ""))
    if history_equip and exam_equip and history_equip != exam_equip:
        mismatches.append("equipamento")
    return mismatches


def _resolve_alert_level(
    *,
    inconsistency_rate: float,
    alert_threshold: float,
    block_threshold: float,
) -> str:
    if inconsistency_rate >= max(block_threshold, 0.0):
        return "block"
    if inconsistency_rate >= max(alert_threshold, 0.0):
        return "alert"
    return "ok"


def reconcile_history_exam_runs(
    *,
    logs_dir: str | Path,
    db_path: str | Path,
    history_csv_path: Optional[str | Path] = None,
    exame_slug: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    alert_threshold: float = 0.02,
    block_threshold: float = 0.05,
) -> HistoryExamRunsReconciliationReport:
    """Reconcilia historico_analises com exam_runs por chave contratual."""
    logs_root = Path(logs_dir)
    db_file = Path(db_path)
    start = _parse_date(data_inicio)
    end = _parse_date(data_fim)
    exame_filter = _normalize(exame_slug or "") or None
    history_csv = Path(history_csv_path) if history_csv_path else logs_root / "historico_analises.csv"

    # Lê de ambas as fontes e usa a que tiver mais dados com chave válida,
    # pois em modo CSV o SQLite historico_analises pode estar vazio/legado.
    history_rows_sqlite = _read_history_rows_sqlite(db_file)
    history_rows_csv = _read_history_rows_csv(history_csv)
    sqlite_keyed = sum(1 for r in history_rows_sqlite if _dedupe_key(r) is not None)
    csv_keyed = sum(1 for r in history_rows_csv if _dedupe_key(r) is not None)
    history_rows = history_rows_csv if csv_keyed >= sqlite_keyed else history_rows_sqlite

    exam_rows = _read_exam_runs_rows_sqlite(db_file)
    if not exam_rows:
        exam_rows = _read_exam_runs_rows_csv(logs_root, exame_filter)

    history_filtered = [
        row
        for row in history_rows
        if _history_matches_filter(row, exame_slug=exame_filter, start=start, end=end)
    ]
    exam_filtered = [
        row
        for row in exam_rows
        if _exam_runs_matches_filter(row, exame_slug=exame_filter, start=start, end=end)
    ]

    history_index, history_missing_key_rows, history_duplicates = _index_rows(history_filtered)
    exam_index, exam_missing_key_rows, exam_duplicates = _index_rows(exam_filtered)

    history_keys = set(history_index.keys())
    exam_keys = set(exam_index.keys())
    missing_in_exam = sorted(_serialize_key(key) for key in (history_keys - exam_keys))
    missing_in_history = sorted(_serialize_key(key) for key in (exam_keys - history_keys))

    mismatches: List[str] = []
    for key in sorted(history_keys & exam_keys):
        fields = _field_mismatch_fields(history_index[key], exam_index[key])
        if fields:
            mismatches.append(f"{_serialize_key(key)} -> {', '.join(fields)}")

    union_size = max(len(history_keys | exam_keys), 1)
    inconsistency_count = (
        len(history_duplicates)
        + len(exam_duplicates)
        + len(missing_in_exam)
        + len(missing_in_history)
        + len(mismatches)
    )
    inconsistency_rate = inconsistency_count / union_size
    alert_level = _resolve_alert_level(
        inconsistency_rate=inconsistency_rate,
        alert_threshold=alert_threshold,
        block_threshold=block_threshold,
    )
    report = HistoryExamRunsReconciliationReport(
        exame_slug_filter=exame_filter,
        data_inicio=start.isoformat() if start else None,
        data_fim=end.isoformat() if end else None,
        alert_threshold=float(alert_threshold),
        block_threshold=float(block_threshold),
        history_rows=len(history_filtered),
        exam_runs_rows=len(exam_filtered),
        history_keyed_rows=len(history_index),
        exam_runs_keyed_rows=len(exam_index),
        history_missing_key_rows=history_missing_key_rows,
        exam_runs_missing_key_rows=exam_missing_key_rows,
        history_duplicate_keys=history_duplicates,
        exam_runs_duplicate_keys=exam_duplicates,
        missing_in_exam_runs=missing_in_exam,
        missing_in_history=missing_in_history,
        field_mismatches=mismatches,
        inconsistency_rate=round(inconsistency_rate, 6),
        alert_level=alert_level,
        is_consistent=(inconsistency_count == 0),
    )
    registrar_log(
        "HistoryExamRunsReconciliation",
        (
            f"Reconciliacao concluida: consistent={report.is_consistent}; "
            f"alert_level={report.alert_level}; "
            f"inconsistency_rate={report.inconsistency_rate}"
        ),
        "INFO",
    )
    return report
