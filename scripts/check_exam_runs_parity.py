#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CLI para validar paridade SQL x CSV de corridas por exame."""

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

from services.exam_runs_parity import (
    verify_sql_csv_parity_batch,
    verify_sql_csv_parity_for_run,
)
from services.persistence.exam_runs_sqlite import default_exam_runs_db_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Valida paridade SQL x CSV por corrida (modo run) "
            "ou em lote por exame/faixa de datas (modo batch)."
        )
    )
    parser.add_argument("--exame-slug", default="", help="Slug do exame (ex.: vr1e2_biomanguinhos).")
    parser.add_argument("--corrida-id", default="", help="ID da corrida a validar (modo run).")
    parser.add_argument("--data-inicio", default="", help="Data inicial YYYY-MM-DD (modo batch).")
    parser.add_argument("--data-fim", default="", help="Data final YYYY-MM-DD (modo batch).")
    parser.add_argument("--logs-dir", default="logs", help="Diretorio com corridas_<slug>.csv.")
    parser.add_argument(
        "--db-path",
        default=str(default_exam_runs_db_path()),
        help="Path do SQLite com tabela exam_runs.",
    )
    parser.add_argument("--json-out", default="", help="Arquivo JSON para salvar o relatório.")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.corrida_id:
        if not args.exame_slug:
            raise SystemExit("--exame-slug e obrigatorio quando --corrida-id for informado.")
        report = verify_sql_csv_parity_for_run(
            exame_slug=args.exame_slug,
            corrida_id=args.corrida_id,
            logs_dir=args.logs_dir,
            db_path=args.db_path,
        )
    else:
        report = verify_sql_csv_parity_batch(
            logs_dir=args.logs_dir,
            db_path=args.db_path,
            exame_slug=args.exame_slug or None,
            data_inicio=args.data_inicio or None,
            data_fim=args.data_fim or None,
        )

    payload = asdict(report)
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.json_out:
        output = Path(args.json_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return 0 if report.is_parity_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
