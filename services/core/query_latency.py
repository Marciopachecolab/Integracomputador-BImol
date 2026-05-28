# -*- coding: utf-8 -*-
"""Telemetria simples de latencia para consultas operacionais."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from services.core.config_service import config_service
from services.persistence.csv_contracts import get_csv_contract
from utils.csv_lock import CSVFileLock
from utils.logger import registrar_log
from utils.network_io import RetryPolicy, open_with_retry, path_exists_with_retry

_CONTRACT = get_csv_contract("query_latency.csv")
_DELIMITER = _CONTRACT.delimiter if _CONTRACT else ";"
_ENCODING = _CONTRACT.encoding if _CONTRACT else "utf-8"
_HEADERS = list(_CONTRACT.required_headers) if _CONTRACT else [
    "timestamp",
    "operation",
    "backend",
    "duration_ms",
    "result_count",
    "meta",
]


def get_query_latency_path() -> Path:
    """Retorna caminho canônico da telemetria de latência."""
    try:
        paths = config_service.get_paths()
    except Exception:
        paths = {}
    logs_dir = paths.get("logs_dir")
    if logs_dir:
        return Path(logs_dir) / "query_latency.csv"
    gal_history_csv = paths.get("gal_history_csv", "logs/historico_analises.csv")
    return Path(gal_history_csv).parent / "query_latency.csv"


def _ensure_file(path: Path, policy: RetryPolicy) -> None:
    if path_exists_with_retry(path, policy=policy):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with CSVFileLock(path):
        if path_exists_with_retry(path, policy=policy):
            return
        with open_with_retry(
            path,
            "w",
            newline="",
            encoding=_ENCODING,
            policy=policy,
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=_HEADERS, delimiter=_DELIMITER)
            writer.writeheader()


def _percentile(sorted_values: list[float], p: float) -> float:
    """Calcula percentil discreto simples para série ordenada."""
    if not sorted_values:
        return 0.0
    if p <= 0:
        return sorted_values[0]
    if p >= 100:
        return sorted_values[-1]
    index = max(0, int(round((p / 100) * len(sorted_values) + 0.5)) - 1)
    return sorted_values[min(index, len(sorted_values) - 1)]


def record_query_latency(
    *,
    operation: str,
    backend: str,
    duration_ms: float,
    result_count: int,
    meta: Optional[Dict[str, object]] = None,
) -> None:
    """Persiste uma amostra de latência de consulta."""
    path = get_query_latency_path()
    policy = RetryPolicy.from_env()
    _ensure_file(path, policy)
    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "operation": str(operation or "").strip(),
        "backend": str(backend or "").strip(),
        "duration_ms": f"{float(duration_ms):.2f}",
        "result_count": str(int(result_count)),
        "meta": json.dumps(meta or {}, ensure_ascii=False),
    }
    try:
        with CSVFileLock(path):
            with open_with_retry(
                path,
                "a",
                newline="",
                encoding=_ENCODING,
                policy=policy,
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=_HEADERS, delimiter=_DELIMITER)
                writer.writerow(payload)
    except Exception as exc:  # pragma: no cover - telemetria nao deve quebrar fluxo
        registrar_log("QueryLatency", f"Falha ao registrar latencia: {exc}", "WARNING")


def summarize_query_latency(
    *,
    operation: Optional[str] = None,
    backend: Optional[str] = None,
    last_n: int = 5000,
) -> Dict[str, float | int | str]:
    """
    Retorna sumário com p50/p95/p99 de `duration_ms`.

    A leitura é best-effort e nunca deve interromper a operação.
    """
    path = get_query_latency_path()
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(path, policy=policy):
        return {
            "operation": operation or "",
            "backend": backend or "",
            "count": 0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
        }

    try:
        with CSVFileLock(path):
            df = pd.read_csv(path, sep=_DELIMITER, encoding=_ENCODING)
    except Exception as exc:  # pragma: no cover
        registrar_log("QueryLatency", f"Falha ao ler telemetria: {exc}", "WARNING")
        return {
            "operation": operation or "",
            "backend": backend or "",
            "count": 0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
        }

    if operation:
        df = df[df["operation"].astype(str).str.strip() == operation]
    if backend:
        df = df[df["backend"].astype(str).str.strip() == backend]
    if int(last_n or 0) > 0 and len(df) > int(last_n):
        df = df.tail(int(last_n))

    values = sorted(pd.to_numeric(df.get("duration_ms"), errors="coerce").dropna().tolist())
    return {
        "operation": operation or "",
        "backend": backend or "",
        "count": int(len(values)),
        "p50_ms": round(_percentile(values, 50), 2),
        "p95_ms": round(_percentile(values, 95), 2),
        "p99_ms": round(_percentile(values, 99), 2),
    }


def evaluate_query_latency_budget(
    summary: Dict[str, float | int | str],
    *,
    min_count: int = 30,
    p95_limit_ms: float = 1500.0,
    p99_limit_ms: float = 2500.0,
) -> Dict[str, float | int | str | bool]:
    """Avalia orçamento/SLO de latência com base no sumário calculado."""
    count = int(summary.get("count", 0) or 0)
    p95 = float(summary.get("p95_ms", 0.0) or 0.0)
    p99 = float(summary.get("p99_ms", 0.0) or 0.0)

    enough_samples = count >= int(min_count)
    p95_ok = p95 <= float(p95_limit_ms)
    p99_ok = p99 <= float(p99_limit_ms)
    budget_ok = enough_samples and p95_ok and p99_ok

    return {
        **summary,
        "min_count": int(min_count),
        "p95_limit_ms": float(p95_limit_ms),
        "p99_limit_ms": float(p99_limit_ms),
        "enough_samples": enough_samples,
        "p95_ok": p95_ok,
        "p99_ok": p99_ok,
        "budget_ok": budget_ok,
    }
