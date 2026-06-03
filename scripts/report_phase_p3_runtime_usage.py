#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Consolida telemetria runtime da Fase P3 (AR-03 e AR-04)."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.core.config_service import config_service

DEFAULT_OUTPUT = Path("snapshots/phase_p3_runtime_usage_summary.json")


def _resolve_log_path(explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit)
    try:
        paths = config_service.get_paths()
        return Path(paths.get("log_file", "logs/sistema.log"))
    except Exception:
        return Path("logs/sistema.log")


def _parse_kv(details: str) -> Dict[str, str]:
    payload: Dict[str, str] = {}
    for part in str(details or "").split():
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        payload[key.strip()] = value.strip()
    return payload


def _read_rows(path: Path) -> Iterable[List[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter=";")
        for row in reader:
            if row:
                yield row


def _base_summary(events: List[Dict[str, str]]) -> Dict[str, Any]:
    if not events:
        return {
            "matched_total": 0,
            "events_by_type": {},
            "first_seen": None,
            "last_seen": None,
        }

    return {
        "matched_total": int(len(events)),
        "events_by_type": dict(Counter(item.get("event", "unknown") for item in events)),
        "first_seen": events[0]["timestamp"],
        "last_seen": events[-1]["timestamp"],
    }


def build_report(*, log_path: Path, hours: int) -> Dict[str, Any]:
    if not log_path.exists():
        return {
            "status": "log_not_found",
            "log_path": str(log_path),
            "window_hours": int(hours),
            "processar_exame": _base_summary([]),
            "suspected_orphan": _base_summary([]),
            "suspected_orphan_by_function": {},
        }

    now = datetime.now()
    cutoff = now - timedelta(hours=int(hours))
    process_events: List[Dict[str, str]] = []
    orphan_events: List[Dict[str, str]] = []
    by_function: Counter[str] = Counter()

    for row in _read_rows(log_path):
        if len(row) < 5:
            continue
        raw_ts, action, details = row[0], row[3], row[4]
        if action != "RuntimeUsage":
            continue
        try:
            ts = datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if ts < cutoff:
            continue

        payload = _parse_kv(details)
        payload["timestamp"] = raw_ts
        feature = payload.get("feature", "")
        if feature == "analysis_engine.processar_exame":
            process_events.append(payload)
        elif feature == "suspected_orphan":
            orphan_events.append(payload)
            function_name = payload.get("function", "unknown")
            by_function[function_name] += 1

    return {
        "status": "ok",
        "log_path": str(log_path),
        "window_hours": int(hours),
        "processar_exame": _base_summary(process_events),
        "suspected_orphan": _base_summary(orphan_events),
        "suspected_orphan_by_function": dict(by_function),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resumo de telemetria runtime da fase P3 (AR-03/AR-04)."
    )
    parser.add_argument("--log-path", default=None)
    parser.add_argument("--hours", type=int, default=48)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    log_path = _resolve_log_path(args.log_path)
    report = build_report(log_path=log_path, hours=args.hours)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        (
            "[phase-p3-runtime] "
            f"status={report['status']} "
            f"processar_exame={report['processar_exame']['matched_total']} "
            f"suspected_orphan={report['suspected_orphan']['matched_total']} "
            f"output={output_path}"
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
