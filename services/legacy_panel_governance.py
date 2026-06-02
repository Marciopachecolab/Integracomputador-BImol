"""Governanca de uso do writer legado painel_* para rollout controlado."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, open_with_retry

DEFAULT_REPORT_PATH = Path("snapshots/legacy_panel_exit_report.json")
DEFAULT_CRITERIA_PATH = Path("config/legacy_panel_exit_criteria.json")


def _resolve_default_log_path() -> Path:
    """Resolve o path do log de governança via config service, com fallback seguro."""
    env_path = os.getenv("INTEGRAGAL_LEGACY_PANEL_GOV_LOG_PATH")
    if env_path:
        return Path(env_path)
    try:
        from services.core.config_service import config_service
        paths = config_service.get_paths()
        logs_dir = paths.get("logs_dir")
        if logs_dir:
            return Path(logs_dir) / "legacy_panel_rollout.csv"
    except Exception:
        pass
    return Path("logs/legacy_panel_rollout.csv")


@dataclass(frozen=True)
class LegacyPanelExitCriteria:
    """Criterios de saida para descontinuar o legado painel_*."""

    min_assisted_runs: int = 3
    max_legacy_usage_in_window: int = 0
    window_days: int = 30


@dataclass(frozen=True)
class LegacyPanelExitReport:
    """Resultado de avaliacao da governanca do legado painel_*."""

    criteria_met: bool
    assisted_runs_ok: int
    legacy_usage_in_window: int
    artifacts_in_window: int
    window_start: str
    window_end: str
    criteria: LegacyPanelExitCriteria

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["criteria"] = asdict(self.criteria)
        return payload


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_log_path(path: Optional[Path] = None) -> Path:
    if path is not None:
        return path
    return _resolve_default_log_path()


def _resolve_report_path(path: Optional[Path] = None) -> Path:
    env_path = os.getenv("INTEGRAGAL_LEGACY_PANEL_GOV_REPORT_PATH")
    if path is not None:
        return path
    if env_path:
        return Path(env_path)
    return DEFAULT_REPORT_PATH


def _resolve_criteria_path(path: Optional[Path] = None) -> Path:
    env_path = os.getenv("INTEGRAGAL_LEGACY_PANEL_GOV_CRITERIA_PATH")
    if path is not None:
        return path
    if env_path:
        return Path(env_path)
    return DEFAULT_CRITERIA_PATH


def _parse_timestamp(value: str) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def record_legacy_panel_event(
    event_type: str,
    *,
    user_id: Optional[str] = None,
    note: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    log_path: Optional[Path] = None,
) -> None:
    """Registra eventos de uso do legado painel_* para auditoria."""

    if os.getenv("INTEGRAGAL_DISABLE_LEGACY_PANEL_GOV_LOG", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return

    path = _resolve_log_path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    policy = RetryPolicy.from_env()
    payload = {
        "timestamp_utc": _now_utc().isoformat(),
        "event_type": event_type,
        "user_id": user_id or "",
        "note": note or "",
        "details_json": json.dumps(details or {}, ensure_ascii=False),
    }

    try:
        with CSVFileLock(path):
            exists = path.exists()
            with open_with_retry(path, "a", encoding="utf-8", newline="", policy=policy) as handle:
                writer = csv.DictWriter(handle, fieldnames=list(payload.keys()), delimiter=";")
                if not exists:
                    writer.writeheader()
                writer.writerow(payload)
    except Exception:
        # Best-effort logging: nunca bloquear o fluxo principal por falha de auditoria.
        return


def load_legacy_panel_events(log_path: Optional[Path] = None) -> list[Dict[str, str]]:
    """Carrega eventos registrados para o legado painel_*."""

    path = _resolve_log_path(log_path)
    if not path.exists():
        return []

    policy = RetryPolicy.from_env()
    try:
        with CSVFileLock(path):
            with open_with_retry(path, "r", encoding="utf-8", newline="", policy=policy) as handle:
                reader = csv.DictReader(handle, delimiter=";")
                return [dict(row) for row in reader]
    except Exception:
        return []


def load_exit_criteria(criteria_path: Optional[Path] = None) -> LegacyPanelExitCriteria:
    """Carrega criterios de saida (com defaults seguros)."""

    path = _resolve_criteria_path(criteria_path)
    if not path.exists():
        return LegacyPanelExitCriteria()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return LegacyPanelExitCriteria(
            min_assisted_runs=int(raw.get("min_assisted_runs", 3)),
            max_legacy_usage_in_window=int(raw.get("max_legacy_usage_in_window", 0)),
            window_days=int(raw.get("window_days", 30)),
        )
    except Exception:
        return LegacyPanelExitCriteria()


def scan_painel_artifacts(
    *,
    reports_root: Path,
    window_days: int,
    now: Optional[datetime] = None,
) -> list[Path]:
    """Lista artefatos painel_* gerados dentro da janela de observacao."""

    cutoff = (now or _now_utc()) - timedelta(days=window_days)
    artifacts: list[Path] = []
    if not reports_root.exists():
        return artifacts

    for path in reports_root.glob("painel_*_exame.csv"):
        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except OSError:
            continue
        if modified >= cutoff:
            artifacts.append(path)
    return artifacts


def evaluate_exit_criteria(
    *,
    criteria: Optional[LegacyPanelExitCriteria] = None,
    log_path: Optional[Path] = None,
    reports_root: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> LegacyPanelExitReport:
    """Avalia criterios de saida do legado painel_*."""

    effective_criteria = criteria or load_exit_criteria()
    reference_now = now or _now_utc()
    window_start = reference_now - timedelta(days=effective_criteria.window_days)

    events = load_legacy_panel_events(log_path)
    assisted_runs_ok = 0
    legacy_usage_in_window = 0

    for event in events:
        event_type = (event.get("event_type") or "").strip().lower()
        timestamp = _parse_timestamp(event.get("timestamp_utc") or "")
        if event_type == "assisted_run_ok":
            assisted_runs_ok += 1
        if event_type == "legacy_panel_enabled" and timestamp and timestamp >= window_start:
            legacy_usage_in_window += 1

    artifacts = scan_painel_artifacts(
        reports_root=reports_root or Path("reports"),
        window_days=effective_criteria.window_days,
        now=reference_now,
    )

    criteria_met = (
        assisted_runs_ok >= effective_criteria.min_assisted_runs
        and legacy_usage_in_window <= effective_criteria.max_legacy_usage_in_window
        and len(artifacts) == 0
    )

    return LegacyPanelExitReport(
        criteria_met=criteria_met,
        assisted_runs_ok=assisted_runs_ok,
        legacy_usage_in_window=legacy_usage_in_window,
        artifacts_in_window=len(artifacts),
        window_start=window_start.isoformat(),
        window_end=reference_now.isoformat(),
        criteria=effective_criteria,
    )


def write_exit_report(
    report: LegacyPanelExitReport,
    *,
    report_path: Optional[Path] = None,
) -> Path:
    """Grava o relatório de governanca em JSON."""

    path = _resolve_report_path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _parse_args(argv: Optional[Iterable[str]] = None):
    import argparse

    parser = argparse.ArgumentParser(
        description="Governanca do legado painel_* (rollout e monitoramento)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record", help="Registra evento de governanca.")
    record.add_argument("event_type", help="Tipo de evento (ex: assisted_run_ok).")
    record.add_argument("--user", dest="user_id", default=None, help="Usuario logado.")
    record.add_argument("--note", default=None, help="Observacao.")

    check = subparsers.add_parser("check", help="Avalia criterios de saida.")
    check.add_argument("--report", dest="report_path", default=None)

    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _parse_args(argv)
    if args.command == "record":
        record_legacy_panel_event(
            args.event_type,
            user_id=args.user_id,
            note=args.note,
        )
        return 0
    if args.command == "check":
        report = evaluate_exit_criteria()
        write_exit_report(report, report_path=Path(args.report_path) if args.report_path else None)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
