#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CLI de reconciliacao cruzada: historico_analises x exam_runs."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.history_exam_runs_reconciliation import reconcile_history_exam_runs
from services.path_resolver import resolve_banco_dir


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcilia historico_analises e exam_runs por chave contratual "
            "(corrida_id + amostra_codigo + lote + data_exame)."
        )
    )
    parser.add_argument("--logs-dir", default="logs", help="Diretorio com CSVs operacionais.")
    parser.add_argument(
        "--db-path",
        default=str(resolve_banco_dir() / "historico.db"),
        help="Banco SQLite com historico_analises/exam_runs.",
    )
    parser.add_argument(
        "--history-csv",
        default="",
        help="Caminho explicito do historico_analises.csv (opcional).",
    )
    parser.add_argument("--exame-slug", default="", help="Filtro por slug de exame.")
    parser.add_argument("--data-inicio", default="", help="Data inicial (YYYY-MM-DD).")
    parser.add_argument("--data-fim", default="", help="Data final (YYYY-MM-DD).")
    parser.add_argument("--alert-threshold", type=float, default=0.02, help="Limiar de alerta.")
    parser.add_argument("--block-threshold", type=float, default=0.05, help="Limiar de bloqueio.")
    parser.add_argument("--fail-on-alert", action="store_true", help="Retorna erro para ALERT/BLOCK.")
    parser.add_argument("--fail-on-block", action="store_true", help="Retorna erro somente para BLOCK.")
    parser.add_argument("--json-out", default="", help="Arquivo JSON de saida.")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    report = reconcile_history_exam_runs(
        logs_dir=args.logs_dir,
        db_path=args.db_path,
        history_csv_path=args.history_csv or None,
        exame_slug=args.exame_slug or None,
        data_inicio=args.data_inicio or None,
        data_fim=args.data_fim or None,
        alert_threshold=float(args.alert_threshold),
        block_threshold=float(args.block_threshold),
    )
    payload = asdict(report)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    print(rendered)

    if args.json_out:
        output = Path(args.json_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")

    if args.fail_on_alert and report.alert_level in {"alert", "block"}:
        return 1
    if args.fail_on_block and report.alert_level == "block":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
