# -*- coding: utf-8 -*-
"""Verificador de paridade SQL x CSV para corridas por exame."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from services.analysis.exam_runs_row_mapper import DEDUPE_FIELDS, clean_text, dedupe_key
from services.persistence.exam_runs_sqlite import ExamRunsSQLiteRepository


@dataclass(frozen=True)
class ExamRunParityReport:
    exame_slug: str
    corrida_id: str
    sql_rows: int
    csv_rows: int
    is_parity_ok: bool
    missing_in_sql: List[str] = field(default_factory=list)
    missing_in_csv: List[str] = field(default_factory=list)
    value_mismatches: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExamRunParityBatchReport:
    exame_slug_filter: Optional[str]
    data_inicio: Optional[str]
    data_fim: Optional[str]
    total_runs: int
    passed_runs: int
    failed_runs: int
    is_parity_ok: bool
    run_reports: List[ExamRunParityReport] = field(default_factory=list)


def _normalize_ct(value: str) -> str:
    raw = clean_text(value)
    if not raw:
        return ""
    try:
        return format(float(raw.replace(",", ".")), "g")
    except ValueError:
        return raw


def _normalize_field_value(field: str, value: str) -> str:
    if field.startswith("CT_"):
        return _normalize_ct(value)
    return clean_text(value)


def _row_id(row: Dict[str, str]) -> Optional[Tuple[str, str, str, str]]:
    return dedupe_key({k: clean_text(v) for k, v in row.items()})


def _serialize_key(key: Tuple[str, str, str, str]) -> str:
    return "|".join(key)


def _normalize_row(row: Dict[str, str]) -> Dict[str, str]:
    return {str(k): _normalize_field_value(str(k), str(v)) for k, v in row.items()}


def _parse_iso_date(value: str) -> Optional[date]:
    raw = clean_text(value)
    if not raw:
        return None
    formats = ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S")
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _date_in_range(value: str, data_inicio: Optional[date], data_fim: Optional[date]) -> bool:
    if data_inicio is None and data_fim is None:
        return True
    parsed = _parse_iso_date(value)
    if parsed is None:
        return False
    if data_inicio is not None and parsed < data_inicio:
        return False
    if data_fim is not None and parsed > data_fim:
        return False
    return True


def _filter_rows(
    rows: Iterable[Dict[str, str]],
    *,
    exame_slug: Optional[str],
    data_inicio: Optional[date],
    data_fim: Optional[date],
) -> List[Dict[str, str]]:
    filtered: List[Dict[str, str]] = []
    for row in rows:
        if exame_slug and clean_text(row.get("exame_slug", "")).lower() != exame_slug.lower():
            continue
        if not _date_in_range(clean_text(row.get("data_exame", "")), data_inicio, data_fim):
            continue
        filtered.append({str(k): clean_text(v) for k, v in row.items()})
    return filtered


def _read_csv_rows(csv_path: Path, corrida_id: str) -> List[Dict[str, str]]:
    if not csv_path.exists():
        return []
    rows: List[Dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=",")
        for row in reader:
            if clean_text(row.get("corrida_id", "")) != clean_text(corrida_id):
                continue
            rows.append({str(k): clean_text(v) for k, v in row.items()})
    return rows


def _read_sql_rows(repo: ExamRunsSQLiteRepository, corrida_id: str) -> List[Dict[str, str]]:
    return [
        {str(k): clean_text(v) for k, v in row.items()}
        for row in repo.list_rows()
        if clean_text(row.get("corrida_id", "")) == clean_text(corrida_id)
    ]


def _collect_csv_rows(logs_root: Path, exame_slug: Optional[str]) -> List[Dict[str, str]]:
    if exame_slug:
        candidates = [logs_root / f"corridas_{exame_slug}.csv"]
    else:
        candidates = sorted(logs_root.glob("corridas_*.csv"))

    rows: List[Dict[str, str]] = []
    for csv_path in candidates:
        if not csv_path.exists():
            continue
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=",")
            for row in reader:
                payload = {str(k): clean_text(v) for k, v in row.items()}
                if not payload.get("exame_slug"):
                    payload["exame_slug"] = csv_path.stem.replace("corridas_", "", 1)
                rows.append(payload)
    return rows


def _index_rows(rows: Iterable[Dict[str, str]]) -> Dict[Tuple[str, str, str, str], Dict[str, str]]:
    indexed: Dict[Tuple[str, str, str, str], Dict[str, str]] = {}
    for row in rows:
        key = _row_id(row)
        if key is None:
            continue
        indexed[key] = _normalize_row(row)
    return indexed


def _group_by_run(rows: Iterable[Dict[str, str]]) -> Dict[Tuple[str, str], List[Dict[str, str]]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, str]]] = {}
    for row in rows:
        exam = clean_text(row.get("exame_slug", "")).lower()
        run = clean_text(row.get("corrida_id", ""))
        if not exam or not run:
            continue
        grouped.setdefault((exam, run), []).append(row)
    return grouped


def _compare_rows(
    *,
    exame_slug: str,
    corrida_id: str,
    csv_rows: Sequence[Dict[str, str]],
    sql_rows: Sequence[Dict[str, str]],
) -> ExamRunParityReport:
    idx_csv = _index_rows(csv_rows)
    idx_sql = _index_rows(sql_rows)

    csv_keys = set(idx_csv.keys())
    sql_keys = set(idx_sql.keys())
    missing_in_sql = sorted(_serialize_key(k) for k in (csv_keys - sql_keys))
    missing_in_csv = sorted(_serialize_key(k) for k in (sql_keys - csv_keys))

    mismatches: List[str] = []
    for key in sorted(csv_keys & sql_keys):
        row_csv = idx_csv[key]
        row_sql = idx_sql[key]
        fields = set(row_csv.keys()) | set(row_sql.keys())
        fields = {field for field in fields if field not in DEDUPE_FIELDS}
        diff_fields = []
        for field in sorted(fields):
            if _normalize_field_value(field, row_csv.get(field, "")) != _normalize_field_value(
                field, row_sql.get(field, "")
            ):
                diff_fields.append(field)
        if diff_fields:
            mismatches.append(f"{_serialize_key(key)} -> {', '.join(diff_fields)}")

    is_ok = not missing_in_sql and not missing_in_csv and not mismatches
    return ExamRunParityReport(
        exame_slug=exame_slug,
        corrida_id=corrida_id,
        sql_rows=len(idx_sql),
        csv_rows=len(idx_csv),
        is_parity_ok=is_ok,
        missing_in_sql=missing_in_sql,
        missing_in_csv=missing_in_csv,
        value_mismatches=mismatches,
    )


def verify_sql_csv_parity_for_run(
    *,
    exame_slug: str,
    corrida_id: str,
    logs_dir: str | Path,
    db_path: str | Path,
) -> ExamRunParityReport:
    """Valida paridade SQL x CSV para uma corrida (corrida_id) de um exame."""
    logs_root = Path(logs_dir)
    csv_path = logs_root / f"corridas_{exame_slug}.csv"
    repo = ExamRunsSQLiteRepository(db_path=db_path)

    csv_rows = _read_csv_rows(csv_path, corrida_id)
    sql_rows = _read_sql_rows(repo, corrida_id)
    return _compare_rows(
        exame_slug=exame_slug,
        corrida_id=corrida_id,
        csv_rows=csv_rows,
        sql_rows=sql_rows,
    )


def verify_sql_csv_parity_batch(
    *,
    logs_dir: str | Path,
    db_path: str | Path,
    exame_slug: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
) -> ExamRunParityBatchReport:
    """Valida paridade SQL x CSV em lote por exame e intervalo de datas."""
    logs_root = Path(logs_dir)
    repo = ExamRunsSQLiteRepository(db_path=db_path)
    start_date = _parse_iso_date(data_inicio or "")
    end_date = _parse_iso_date(data_fim or "")

    csv_rows = _filter_rows(
        _collect_csv_rows(logs_root, exame_slug),
        exame_slug=exame_slug,
        data_inicio=start_date,
        data_fim=end_date,
    )
    sql_rows = _filter_rows(
        repo.list_rows(),
        exame_slug=exame_slug,
        data_inicio=start_date,
        data_fim=end_date,
    )

    grouped_csv = _group_by_run(csv_rows)
    grouped_sql = _group_by_run(sql_rows)
    run_keys = sorted(set(grouped_csv.keys()) | set(grouped_sql.keys()))

    run_reports: List[ExamRunParityReport] = []
    for run_exame, corrida_id in run_keys:
        run_reports.append(
            _compare_rows(
                exame_slug=run_exame,
                corrida_id=corrida_id,
                csv_rows=grouped_csv.get((run_exame, corrida_id), []),
                sql_rows=grouped_sql.get((run_exame, corrida_id), []),
            )
        )

    total = len(run_reports)
    failed = sum(1 for report in run_reports if not report.is_parity_ok)
    passed = total - failed
    return ExamRunParityBatchReport(
        exame_slug_filter=exame_slug,
        data_inicio=start_date.isoformat() if start_date else None,
        data_fim=end_date.isoformat() if end_date else None,
        total_runs=total,
        passed_runs=passed,
        failed_runs=failed,
        is_parity_ok=(failed == 0),
        run_reports=run_reports,
    )
