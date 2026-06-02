#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Gera relatorio reproduzivel de latencia P50/P95 do merge de sincronizacao da placa."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from services.core.query_latency import evaluate_query_latency_budget, summarize_query_latency

DEFAULT_OUTPUT = Path("snapshots/plate_sync_latency_summary.json")


def build_report(
    *,
    operation: str,
    backend: str,
    last_n: int,
    min_count: int,
    p95_limit_ms: float,
    p99_limit_ms: float,
) -> Dict[str, Any]:
    summary = summarize_query_latency(
        operation=operation,
        backend=backend,
        last_n=last_n,
    )
    budget = evaluate_query_latency_budget(
        summary,
        min_count=min_count,
        p95_limit_ms=p95_limit_ms,
        p99_limit_ms=p99_limit_ms,
    )
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "backend": backend,
        "last_n": int(last_n),
        "summary": summary,
        "budget": budget,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Relatorio de latencia da sincronizacao de placa (P50/P95/P99)."
    )
    parser.add_argument("--operation", default="plate.sync.merge")
    parser.add_argument("--backend", default="use_case")
    parser.add_argument("--last-n", type=int, default=5000)
    parser.add_argument("--min-count", type=int, default=10)
    parser.add_argument("--p95-limit-ms", type=float, default=1500.0)
    parser.add_argument("--p99-limit-ms", type=float, default=2500.0)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_report(
        operation=args.operation,
        backend=args.backend,
        last_n=args.last_n,
        min_count=args.min_count,
        p95_limit_ms=args.p95_limit_ms,
        p99_limit_ms=args.p99_limit_ms,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        (
            "[plate-sync-latency] "
            f"backend={args.backend} count={payload['summary']['count']} "
            f"p50={payload['summary']['p50_ms']}ms "
            f"p95={payload['summary']['p95_ms']}ms "
            f"budget_ok={payload['budget']['budget_ok']} "
            f"output={output_path}"
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

