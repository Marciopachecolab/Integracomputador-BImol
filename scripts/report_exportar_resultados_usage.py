#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Consolida telemetria de uso runtime de exportar_resultados_gal no sistema.log."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from services.core.config_service import config_service

DEFAULT_OUTPUT = Path("snapshots/exportar_resultados_gal_usage_summary.json")


def _resolve_log_path(explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit)
    try:
        paths = config_service.get_paths()
        return Path(paths.get("log_file", "logs/sistema.log"))
    except Exception:
        return Path("logs/sistema.log")


def _parse_details_kv(details: str) -> Dict[str, str]:
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


def build_usage_report(*, log_path: Path, hours: int) -> Dict[str, Any]:
    if not log_path.exists():
        return {
            "log_path": str(log_path),
            "window_hours": int(hours),
            "matched_total": 0,
            "events_by_type": {},
            "first_seen": None,
            "last_seen": None,
            "status": "log_not_found",
        }

    now = datetime.now()
    cutoff = now - timedelta(hours=int(hours))
    matched: List[Dict[str, str]] = []

    for row in _read_rows(log_path):
        if len(row) < 5:
            continue
        raw_ts, action, details = row[0], row[3], row[4]
        if action != "RuntimeUsage":
            continue
        if "feature=exportar_resultados_gal" not in details:
            continue
        try:
            ts = datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if ts < cutoff:
            continue
        payload = _parse_details_kv(details)
        payload["timestamp"] = raw_ts
        matched.append(payload)

    events = Counter(item.get("event", "unknown") for item in matched)
    first_seen = matched[0]["timestamp"] if matched else None
    last_seen = matched[-1]["timestamp"] if matched else None
    return {
        "log_path": str(log_path),
        "window_hours": int(hours),
        "matched_total": int(len(matched)),
        "events_by_type": dict(events),
        "first_seen": first_seen,
        "last_seen": last_seen,
        "status": "ok",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resumo de uso runtime da funcao exportar_resultados_gal."
    )
    parser.add_argument("--log-path", default=None)
    parser.add_argument("--hours", type=int, default=48)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    log_path = _resolve_log_path(args.log_path)
    report = build_usage_report(log_path=log_path, hours=args.hours)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        (
            "[exportar-usage] "
            f"status={report['status']} matched_total={report['matched_total']} "
            f"events={report['events_by_type']} output={output_path}"
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

