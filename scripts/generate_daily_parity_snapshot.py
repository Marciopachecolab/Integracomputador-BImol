#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Gera snapshot diário de paridade SQL x CSV em `snapshots/`."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.exam_runs_parity import verify_sql_csv_parity_batch
from services.persistence.exam_runs_sqlite import default_exam_runs_db_path
from services.history_exam_runs_reconciliation import reconcile_history_exam_runs


def _parse_iso_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise SystemExit(f"--reference-date invalida: {value}. Use YYYY-MM-DD.") from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera JSON diário de paridade SQL x CSV em snapshots/."
    )
    parser.add_argument("--exame-slug", default="", help="Slug do exame (opcional).")
    parser.add_argument("--logs-dir", default="logs", help="Diretorio de corridas_<slug>.csv.")
    parser.add_argument(
        "--db-path",
        default=str(default_exam_runs_db_path()),
        help="Path do SQLite com tabela exam_runs.",
    )
    parser.add_argument("--output-dir", default="snapshots", help="Diretorio de saida do JSON.")
    parser.add_argument(
        "--reference-date",
        default="",
        help="Data de referencia YYYY-MM-DD (default: hoje local).",
    )
    parser.add_argument(
        "--offset-days",
        type=int,
        default=1,
        help="Dias para retroceder da data de referencia (default: 1).",
    )
    parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="Retorna exit code 1 quando houver divergencia de paridade.",
    )
    parser.add_argument(
        "--history-csv",
        default="",
        help="Caminho explicito para historico_analises.csv (opcional).",
    )
    parser.add_argument(
        "--reconciliation-alert-threshold",
        type=float,
        default=0.02,
        help="Limiar de alerta para reconciliacao historico x exam_runs.",
    )
    parser.add_argument(
        "--reconciliation-block-threshold",
        type=float,
        default=0.05,
        help="Limiar de bloqueio para reconciliacao historico x exam_runs.",
    )
    parser.add_argument(
        "--fail-on-reconciliation-alert",
        action="store_true",
        help="Retorna exit code 1 quando reconciliacao entrar em ALERT/BLOCK.",
    )
    parser.add_argument(
        "--fail-on-reconciliation-block",
        action="store_true",
        help="Retorna exit code 1 quando reconciliacao entrar em BLOCK.",
    )
    return parser


def _target_date(reference_date: str, offset_days: int) -> date:
    reference = _parse_iso_date(reference_date) if reference_date else date.today()
    return reference - timedelta(days=offset_days)


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    target = _target_date(args.reference_date, args.offset_days)
    target_iso = target.isoformat()

    report = verify_sql_csv_parity_batch(
        logs_dir=args.logs_dir,
        db_path=args.db_path,
        exame_slug=args.exame_slug or None,
        data_inicio=target_iso,
        data_fim=target_iso,
    )
    payload = asdict(report)
    payload["target_date"] = target_iso
    payload["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reconciliation = reconcile_history_exam_runs(
        logs_dir=args.logs_dir,
        db_path=args.db_path,
        history_csv_path=args.history_csv or None,
        exame_slug=args.exame_slug or None,
        data_inicio=target_iso,
        data_fim=target_iso,
        alert_threshold=float(args.reconciliation_alert_threshold),
        block_threshold=float(args.reconciliation_block_threshold),
    )
    payload["reconciliation"] = asdict(reconciliation)
    payload["overall_ok"] = bool(
        report.is_parity_ok and reconciliation.alert_level == "ok"
    )

    slug_tag = args.exame_slug or "all"
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"parity_daily_{slug_tag}_{target.strftime('%Y%m%d')}.json"
    output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "output": str(output_file),
                "is_parity_ok": report.is_parity_ok,
                "reconciliation_alert_level": reconciliation.alert_level,
                "overall_ok": payload["overall_ok"],
            },
            ensure_ascii=False,
        )
    )
    if args.fail_on_mismatch and not report.is_parity_ok:
        return 1
    if args.fail_on_reconciliation_alert and reconciliation.alert_level in {"alert", "block"}:
        return 1
    if args.fail_on_reconciliation_block and reconciliation.alert_level == "block":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
