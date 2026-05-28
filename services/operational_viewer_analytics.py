# -*- coding: utf-8 -*-
"""Indicadores operacionais do visualizador tabular (F8)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from services.shared_paths import resolve_logs_dir as _shared_resolve_logs_dir
from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, path_exists_with_retry
from utils.logger import registrar_log


def _resolve_logs_dir(logs_dir: Optional[str | Path]) -> Path:
    return _shared_resolve_logs_dir(logs_dir)


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    if p <= 0:
        return values[0]
    if p >= 100:
        return values[-1]
    index = max(0, int(round((p / 100) * len(values) + 0.5)) - 1)
    return values[min(index, len(values) - 1)]


def _parse_meta(raw: object) -> Dict[str, object]:
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _calc_entry(group: pd.DataFrame) -> Dict[str, float | int]:
    latencies = sorted(pd.to_numeric(group.get("duration_ms"), errors="coerce").dropna().tolist())
    count = int(len(group))
    error_count = int(group.get("is_error", pd.Series(dtype=bool)).sum())
    return {
        "volume": count,
        "error_count": error_count,
        "error_rate": round((error_count / count) if count > 0 else 0.0, 4),
        "p50_ms": round(_percentile(latencies, 50), 2),
        "p95_ms": round(_percentile(latencies, 95), 2),
    }


def summarize_operational_viewer_metrics(
    *,
    logs_dir: Optional[str | Path] = None,
    last_n: int = 5000,
) -> Dict[str, object]:
    """Retorna volume, p50/p95 e taxa de erro por operacao e visao."""
    path = _resolve_logs_dir(logs_dir) / "query_latency.csv"
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(path, policy=policy):
        return {
            "total_events": 0,
            "query_volume": 0,
            "export_volume": 0,
            "by_view": {},
            "by_operation": {},
        }

    try:
        with CSVFileLock(path):
            df = pd.read_csv(path, sep=";", encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        registrar_log("ViewerAnalytics", f"Falha ao ler query_latency.csv: {exc}", "WARNING")
        return {
            "total_events": 0,
            "query_volume": 0,
            "export_volume": 0,
            "by_view": {},
            "by_operation": {},
        }

    if int(last_n or 0) > 0 and len(df) > int(last_n):
        df = df.tail(int(last_n)).reset_index(drop=True)

    df = df[df["operation"].astype(str).str.startswith("operational_viewer.")].copy()
    if df.empty:
        return {
            "total_events": 0,
            "query_volume": 0,
            "export_volume": 0,
            "by_view": {},
            "by_operation": {},
        }

    df["meta_dict"] = df.get("meta", pd.Series(dtype=str)).map(_parse_meta)
    df["view"] = df["meta_dict"].map(lambda m: str(m.get("view", "") or "").strip() or "unknown")
    df["is_error"] = df["meta_dict"].map(lambda m: bool(str(m.get("error", "")).strip()))

    by_operation: Dict[str, Dict[str, float | int]] = {}
    for op, group in df.groupby("operation"):
        by_operation[str(op)] = _calc_entry(group)

    by_view: Dict[str, Dict[str, float | int]] = {}
    for view, group in df.groupby("view"):
        by_view[str(view)] = _calc_entry(group)

    query_volume = int((df["operation"] == "operational_viewer.query").sum())
    export_volume = int((df["operation"] == "operational_viewer.export").sum())

    return {
        "total_events": int(len(df)),
        "query_volume": query_volume,
        "export_volume": export_volume,
        "by_view": by_view,
        "by_operation": by_operation,
    }


__all__ = ["summarize_operational_viewer_metrics"]
