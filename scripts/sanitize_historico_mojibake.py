#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Saneamento controlado de mojibake para historico CSV (dry-run/apply/restore).

Fluxo:
1) dry-run: detecta e reporta alteracoes sugeridas, sem gravar.
2) apply: cria backup e aplica saneamento com lock/retry.
3) restore: restaura arquivo a partir de backup gerado.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List

import pandas as pd

# Garante import dos modulos locais quando executado via subprocess.
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, open_with_retry
from utils.text_normalizer import repair_mojibake_text

DEFAULT_CSV_PATH = Path("logs/historico_analises.csv")
DEFAULT_REPORT_PATH = Path("snapshots/historico_mojibake_sanitization_report.json")


@dataclass(frozen=True)
class CellChange:
    row_index: int
    column: str
    old_value: str
    new_value: str


def _read_csv(path: Path, policy: RetryPolicy) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8", "utf-8-sig"):
        try:
            with open_with_retry(path, "r", encoding=encoding, newline="", policy=policy) as handle:
                return pd.read_csv(handle, sep=";")
        except Exception as exc:  # noqa: PERF203 - necessario para fallback de encoding
            last_error = exc
    if last_error:
        raise last_error
    raise RuntimeError(f"Nao foi possivel ler CSV: {path}")


def _sanitize_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, List[CellChange]]:
    sanitized = df.copy()
    changes: List[CellChange] = []

    for column in sanitized.columns:
        series = sanitized[column]
        for row_index, value in series.items():
            if pd.isna(value):
                continue
            if not isinstance(value, str):
                continue
            repaired = repair_mojibake_text(value)
            if repaired != value:
                sanitized.at[row_index, column] = repaired
                changes.append(
                    CellChange(
                        row_index=int(row_index),
                        column=str(column),
                        old_value=value,
                        new_value=repaired,
                    )
                )

    return sanitized, changes


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _build_backup_path(csv_path: Path, backup_dir: Path | None = None) -> Path:
    target_dir = backup_dir or csv_path.parent
    _ensure_parent(target_dir)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return target_dir / f"{csv_path.stem}.backup_{stamp}.csv"


def _copy_file(src: Path, dst: Path, policy: RetryPolicy) -> None:
    _ensure_parent(dst)
    with open_with_retry(src, "rb", policy=policy) as src_handle:
        with open_with_retry(dst, "wb", policy=policy) as dst_handle:
            shutil.copyfileobj(src_handle, dst_handle)


def _write_csv(df: pd.DataFrame, path: Path, policy: RetryPolicy) -> None:
    with open_with_retry(path, "w", encoding="utf-8", newline="", policy=policy) as handle:
        df.to_csv(handle, sep=";", index=False)


def _write_report(
    report_path: Path,
    *,
    mode: str,
    csv_path: Path,
    backup_path: Path | None,
    df_before: pd.DataFrame,
    changes: Iterable[CellChange],
) -> None:
    changes_list = list(changes)
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "csv_path": str(csv_path),
        "backup_path": str(backup_path) if backup_path else None,
        "summary": {
            "rows": int(len(df_before)),
            "columns": int(len(df_before.columns)),
            "changes": int(len(changes_list)),
        },
        "changes": [asdict(item) for item in changes_list],
    }
    _ensure_parent(report_path)
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _print_summary(mode: str, csv_path: Path, backup_path: Path | None, changes: List[CellChange]) -> None:
    print(
        f"[mojibake-sanitize] mode={mode} csv_path={csv_path} "
        f"changes={len(changes)} backup={backup_path or '-'}"
    )


def cmd_dry_run(args: argparse.Namespace) -> int:
    policy = RetryPolicy.from_env()
    csv_path = Path(args.csv_path)
    report_path = Path(args.report)
    df_before = _read_csv(csv_path, policy)
    _, changes = _sanitize_dataframe(df_before)
    _write_report(
        report_path,
        mode="dry-run",
        csv_path=csv_path,
        backup_path=None,
        df_before=df_before,
        changes=changes,
    )
    _print_summary("dry-run", csv_path, None, changes)
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    policy = RetryPolicy.from_env()
    csv_path = Path(args.csv_path)
    report_path = Path(args.report)
    backup_dir = Path(args.backup_dir) if args.backup_dir else None

    with CSVFileLock(csv_path):
        df_before = _read_csv(csv_path, policy)
        df_after, changes = _sanitize_dataframe(df_before)
        backup_path = _build_backup_path(csv_path, backup_dir=backup_dir)
        _copy_file(csv_path, backup_path, policy)
        _write_csv(df_after, csv_path, policy)

    # Invariantes basicas
    if len(df_before) != len(df_after) or list(df_before.columns) != list(df_after.columns):
        raise RuntimeError("Invariante violada: estrutura do CSV mudou durante o saneamento.")

    _write_report(
        report_path,
        mode="apply",
        csv_path=csv_path,
        backup_path=backup_path,
        df_before=df_before,
        changes=changes,
    )
    _print_summary("apply", csv_path, backup_path, changes)
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    policy = RetryPolicy.from_env()
    csv_path = Path(args.csv_path)
    backup_path = Path(args.backup_path)
    report_path = Path(args.report)

    if not backup_path.exists():
        raise FileNotFoundError(f"Backup nao encontrado: {backup_path}")

    with CSVFileLock(csv_path):
        _copy_file(backup_path, csv_path, policy)

    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "restore",
        "csv_path": str(csv_path),
        "backup_path": str(backup_path),
        "summary": {
            "restored": True,
        },
    }
    _ensure_parent(report_path)
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[mojibake-sanitize] mode=restore csv_path={csv_path} backup={backup_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Saneamento controlado de mojibake para historico CSV.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dry_run = subparsers.add_parser("dry-run", help="Apenas detecta alteracoes sugeridas.")
    dry_run.add_argument("--csv-path", default=str(DEFAULT_CSV_PATH))
    dry_run.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    dry_run.set_defaults(func=cmd_dry_run)

    apply_cmd = subparsers.add_parser("apply", help="Aplica saneamento e cria backup automatico.")
    apply_cmd.add_argument("--csv-path", default=str(DEFAULT_CSV_PATH))
    apply_cmd.add_argument("--backup-dir", default=None)
    apply_cmd.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    apply_cmd.set_defaults(func=cmd_apply)

    restore_cmd = subparsers.add_parser("restore", help="Restaura CSV a partir de backup.")
    restore_cmd.add_argument("--csv-path", default=str(DEFAULT_CSV_PATH))
    restore_cmd.add_argument("--backup-path", required=True)
    restore_cmd.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    restore_cmd.set_defaults(func=cmd_restore)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
