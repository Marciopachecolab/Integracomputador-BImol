#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Manage Windows Task Scheduler job for daily SQL/CSV parity snapshots."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.persistence.exam_runs_sqlite import default_exam_runs_db_path


DEFAULT_TASK_NAME = "Integragal\\ParityDailySnapshot"
DEFAULT_RUNNER_SCRIPT = PROJECT_ROOT / "scripts" / "run_daily_parity_snapshot.cmd"


def _quote(value: str | Path) -> str:
    text = str(value)
    return f"\"{text}\""


def _default_python_exe() -> Path:
    candidate = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if candidate.exists():
        return candidate
    return Path(sys.executable)


def resolve_runtime_path(value: str | Path) -> Path:
    """Resolve runtime path relative to project root when not absolute."""
    path = Path(value)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def _parse_start_time(value: str) -> str:
    try:
        datetime.strptime(value, "%H:%M")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"--start-time invalido: {value}. Use HH:MM em formato 24h."
        ) from exc
    return value


def build_action_command(
    *,
    python_exe: Path,
    script_path: Path,
    logs_dir: Path,
    db_path: Path,
    output_dir: Path,
    exame_slug: str,
    offset_days: int,
    fail_on_mismatch: bool,
    history_csv: str,
    reconciliation_alert_threshold: float,
    reconciliation_block_threshold: float,
    fail_on_reconciliation_alert: bool,
    fail_on_reconciliation_block: bool,
) -> str:
    parts = [
        _quote(python_exe),
        _quote(script_path),
        "--logs-dir",
        _quote(logs_dir),
        "--db-path",
        _quote(db_path),
        "--output-dir",
        _quote(output_dir),
        "--offset-days",
        str(offset_days),
        "--reconciliation-alert-threshold",
        str(reconciliation_alert_threshold),
        "--reconciliation-block-threshold",
        str(reconciliation_block_threshold),
    ]
    if exame_slug:
        parts.extend(["--exame-slug", _quote(exame_slug)])
    if history_csv:
        parts.extend(["--history-csv", _quote(history_csv)])
    if fail_on_mismatch:
        parts.append("--fail-on-mismatch")
    if not fail_on_reconciliation_alert and not fail_on_reconciliation_block:
        # Governance padrao: bloquear apenas divergencia de nivel BLOCK.
        fail_on_reconciliation_block = True
    if fail_on_reconciliation_alert:
        parts.append("--fail-on-reconciliation-alert")
    if fail_on_reconciliation_block:
        parts.append("--fail-on-reconciliation-block")
    return " ".join(parts)


def write_runner_script(*, runner_script: Path, action_command: str) -> None:
    """Write a CMD wrapper used by Task Scheduler to avoid /TR length limits."""
    runner_script.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "@echo off",
        action_command,
        "exit /b %ERRORLEVEL%",
        "",
    ]
    runner_script.write_text("\n".join(lines), encoding="utf-8")


def build_scheduler_tr_command(runner_script: Path) -> str:
    """Build schtasks /TR command using a short cmd wrapper path."""
    return f"cmd /c {_quote(runner_script)}"


def _build_register_command(
    *,
    task_name: str,
    start_time: str,
    action_command: str,
    run_user: str,
) -> list[str]:
    command = [
        "schtasks",
        "/Create",
        "/F",
        "/SC",
        "DAILY",
        "/TN",
        task_name,
        "/ST",
        start_time,
        "/TR",
        action_command,
    ]
    if run_user:
        command.extend(["/RU", run_user])
    return command


def _build_unregister_command(*, task_name: str) -> list[str]:
    return ["schtasks", "/Delete", "/F", "/TN", task_name]


def _build_query_command(*, task_name: str) -> list[str]:
    return ["schtasks", "/Query", "/TN", task_name, "/V", "/FO", "LIST"]


def _build_run_now_command(*, task_name: str) -> list[str]:
    return ["schtasks", "/Run", "/TN", task_name]


def _echo_command(command: Iterable[str]) -> None:
    print(" ".join(command))


def _execute(command: list[str], *, dry_run: bool) -> int:
    _echo_command(command)
    if dry_run:
        return 0
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    return int(result.returncode)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Register/query/unregister daily parity snapshot task (Windows Task Scheduler)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register", help="Create/update daily task.")
    register.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    register.add_argument("--start-time", type=_parse_start_time, default="06:00", help="HH:MM (24h).")
    register.add_argument("--exame-slug", default="")
    register.add_argument("--logs-dir", default="logs")
    register.add_argument("--db-path", default=str(default_exam_runs_db_path()))
    register.add_argument("--output-dir", default="snapshots")
    register.add_argument("--history-csv", default="")
    register.add_argument("--offset-days", type=int, default=1)
    register.add_argument("--python-exe", default=str(_default_python_exe()))
    register.add_argument("--runner-script", default=str(DEFAULT_RUNNER_SCRIPT))
    register.add_argument("--run-user", default="")
    register.add_argument("--fail-on-mismatch", action="store_true")
    register.add_argument("--reconciliation-alert-threshold", type=float, default=0.02)
    register.add_argument("--reconciliation-block-threshold", type=float, default=0.05)
    register.add_argument("--fail-on-reconciliation-alert", action="store_true")
    register.add_argument("--fail-on-reconciliation-block", action="store_true")
    register.add_argument("--dry-run", action="store_true")

    unregister = subparsers.add_parser("unregister", help="Delete task.")
    unregister.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    unregister.add_argument("--dry-run", action="store_true")

    query = subparsers.add_parser("query", help="Show current task details.")
    query.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    query.add_argument("--dry-run", action="store_true")

    run_now = subparsers.add_parser("run-now", help="Trigger task immediately.")
    run_now.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    run_now.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "register":
        logs_dir = resolve_runtime_path(args.logs_dir)
        db_path = resolve_runtime_path(args.db_path)
        output_dir = resolve_runtime_path(args.output_dir)
        python_exe = resolve_runtime_path(args.python_exe)

        action = build_action_command(
            python_exe=python_exe,
            script_path=PROJECT_ROOT / "scripts" / "generate_daily_parity_snapshot.py",
            logs_dir=logs_dir,
            db_path=db_path,
            output_dir=output_dir,
            exame_slug=args.exame_slug,
            offset_days=args.offset_days,
            fail_on_mismatch=bool(args.fail_on_mismatch),
            history_csv=str(resolve_runtime_path(args.history_csv)) if args.history_csv else "",
            reconciliation_alert_threshold=float(args.reconciliation_alert_threshold),
            reconciliation_block_threshold=float(args.reconciliation_block_threshold),
            fail_on_reconciliation_alert=bool(args.fail_on_reconciliation_alert),
            fail_on_reconciliation_block=bool(args.fail_on_reconciliation_block),
        )
        runner_script = resolve_runtime_path(args.runner_script)
        write_runner_script(runner_script=runner_script, action_command=action)
        task_action = build_scheduler_tr_command(runner_script)
        command = _build_register_command(
            task_name=args.task_name,
            start_time=args.start_time,
            action_command=task_action,
            run_user=args.run_user,
        )
        return _execute(command, dry_run=bool(args.dry_run))

    if args.command == "unregister":
        return _execute(
            _build_unregister_command(task_name=args.task_name),
            dry_run=bool(args.dry_run),
        )

    if args.command == "query":
        return _execute(
            _build_query_command(task_name=args.task_name),
            dry_run=bool(args.dry_run),
        )

    return _execute(
        _build_run_now_command(task_name=args.task_name),
        dry_run=bool(args.dry_run),
    )


if __name__ == "__main__":
    raise SystemExit(main())
