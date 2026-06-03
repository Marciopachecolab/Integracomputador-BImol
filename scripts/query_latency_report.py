#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Gera resumo de latencia (P50/P95/P99) das consultas instrumentadas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.core.query_latency import summarize_query_latency


def main() -> int:
    parser = argparse.ArgumentParser(description="Resumo de latencia de consultas")
    parser.add_argument("--operation", default="history.read")
    parser.add_argument("--backend", default="")
    parser.add_argument("--last-n", type=int, default=5000)
    parser.add_argument(
        "--out",
        default="snapshots/query_latency_report.json",
        help="Caminho do JSON de saida",
    )
    args = parser.parse_args()

    summary = summarize_query_latency(
        operation=args.operation or None,
        backend=args.backend or None,
        last_n=args.last_n,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[query-latency] report={out_path}")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
