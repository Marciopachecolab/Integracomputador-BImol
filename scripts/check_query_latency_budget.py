#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Valida orçamento de latência para consultas instrumentadas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.core.query_latency import evaluate_query_latency_budget, summarize_query_latency


def _run_backend_check(
    *,
    operation: str,
    backend: str,
    last_n: int,
    min_count: int,
    p95_limit_ms: float,
    p99_limit_ms: float,
) -> dict:
    summary = summarize_query_latency(
        operation=operation or None,
        backend=backend or None,
        last_n=last_n,
    )
    return evaluate_query_latency_budget(
        summary,
        min_count=min_count,
        p95_limit_ms=p95_limit_ms,
        p99_limit_ms=p99_limit_ms,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check do orçamento de latência de consultas")
    parser.add_argument("--operation", default="history.read")
    parser.add_argument(
        "--backend",
        action="append",
        default=["provider", "csv_fallback"],
        help="Backend alvo (pode repetir). Ex.: --backend provider --backend csv_fallback",
    )
    parser.add_argument("--last-n", type=int, default=5000)
    parser.add_argument("--min-count", type=int, default=30)
    parser.add_argument("--p95-limit-ms", type=float, default=1500.0)
    parser.add_argument("--p99-limit-ms", type=float, default=2500.0)
    parser.add_argument(
        "--out",
        default="snapshots/query_latency_budget_check.json",
        help="Caminho do JSON de saida",
    )
    args = parser.parse_args()

    backends = []
    for backend in args.backend:
        item = str(backend or "").strip()
        if item and item not in backends:
            backends.append(item)

    checks = [
        _run_backend_check(
            operation=args.operation,
            backend=backend,
            last_n=args.last_n,
            min_count=args.min_count,
            p95_limit_ms=args.p95_limit_ms,
            p99_limit_ms=args.p99_limit_ms,
        )
        for backend in backends
    ]

    overall_ok = all(bool(item.get("budget_ok", False)) for item in checks) if checks else False
    payload = {
        "operation": args.operation,
        "checks": checks,
        "overall_ok": overall_ok,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[query-latency-budget] report={out_path}")
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
