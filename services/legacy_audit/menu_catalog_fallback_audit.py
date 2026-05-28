# -*- coding: utf-8 -*-
"""Trilha auditavel para fallback legado do catalogo de exames no menu."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Optional

import pandas as pd

from services.legacy_audit import menu_catalog_cutover_policy
from services.legacy_audit.menu_catalog_audit_repository import MenuCatalogAuditRepository
from services.menu_catalog_cutover_ports import MenuCatalogCutoverPorts
from services.core.runtime_flags import (
    get_menu_compat_global_shutdown_policy,
    get_menu_compat_global_shutdown_thresholds,
    get_menu_compat_off_users,
)
from services.shared_paths import resolve_logs_dir as _resolve_logs_dir
from utils.logger import registrar_log

_HEADERS = ["timestamp", "actor", "mode", "outcome", "error"]
_DB_FILENAME = "menu_catalog_fallback_audit.db"
_CSV_FILENAME = "menu_catalog_fallback_audit.csv"  # compatibilidade legada
_REPORT_FILENAME = "menu_catalog_cutover_report.json"


def get_menu_catalog_fallback_audit_path(*, logs_dir: Optional[str | Path] = None) -> Path:
    """Retorna caminho legado CSV para compatibilidade transitória."""
    return _resolve_logs_dir(logs_dir) / _CSV_FILENAME


def get_menu_catalog_fallback_audit_db_path(*, logs_dir: Optional[str | Path] = None) -> Path:
    """Retorna caminho canonico SQLite da trilha de fallback legado."""
    return _resolve_logs_dir(logs_dir) / _DB_FILENAME


def get_menu_catalog_cutover_report_path(*, logs_dir: Optional[str | Path] = None) -> Path:
    """Retorna caminho do relatorio automatizado de corte da compat layer."""
    return _resolve_logs_dir(logs_dir) / _REPORT_FILENAME


def _repository(*, logs_dir: Optional[str | Path]) -> MenuCatalogAuditRepository:
    return MenuCatalogAuditRepository(
        db_path=get_menu_catalog_fallback_audit_db_path(logs_dir=logs_dir)
    )


def _accumulate_telemetry(
    telemetry: Optional[dict[str, int]],
    *,
    key: str,
    value: int,
) -> None:
    if telemetry is None:
        return
    telemetry[key] = int(telemetry.get(key, 0)) + int(value)


def _parse_timestamps(value: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(value, errors="coerce", format="ISO8601")
    except TypeError:  # pragma: no cover
        return pd.to_datetime(value, errors="coerce")


def _normalize_timestamp(value: Any) -> str:
    raw = str(value or "").strip()
    if raw:
        return raw
    return datetime.now().isoformat(timespec="seconds")


def _normalize_event(event: Mapping[str, Any]) -> dict[str, str]:
    return {
        "timestamp": _normalize_timestamp(event.get("timestamp", "")),
        "actor": str(event.get("actor", "") or "").strip(),
        "mode": str(event.get("mode", "") or "").strip(),
        "outcome": str(event.get("outcome", "") or "").strip().lower(),
        "error": str(event.get("error", "") or "").strip(),
    }


def record_menu_catalog_fallback_event(
    *,
    logs_dir: Optional[str | Path],
    event: Mapping[str, Any],
    max_rows: int = 2000,
) -> None:
    """Registra evento da trilha de fallback legado de catalogo em SQLite."""
    payload = _normalize_event(event)

    try:
        _repository(logs_dir=logs_dir).insert_event(
            timestamp=payload["timestamp"],
            actor=payload["actor"],
            mode=payload["mode"],
            outcome=payload["outcome"],
            error=payload["error"],
            max_rows=max_rows,
        )
    except Exception as exc:  # pragma: no cover
        registrar_log("MenuCatalogAudit", f"Falha ao registrar trilha de fallback: {exc}", "WARNING")


def _read_rows(
    *,
    logs_dir: Optional[str | Path],
    limit: int,
    telemetry: Optional[dict[str, int]] = None,
) -> pd.DataFrame:
    repo = _repository(logs_dir=logs_dir)
    if not get_menu_catalog_fallback_audit_db_path(logs_dir=logs_dir).exists():
        return pd.DataFrame(columns=_HEADERS)

    safe_limit = max(1, int(limit or 1))

    try:
        rows = repo.read_recent(limit=safe_limit, telemetry=telemetry)
    except Exception as exc:  # pragma: no cover
        registrar_log("MenuCatalogAudit", f"Falha ao ler trilha de fallback: {exc}", "WARNING")
        return pd.DataFrame(columns=_HEADERS)

    return pd.DataFrame(rows, columns=_HEADERS)


def read_menu_catalog_fallback_audit(
    *,
    logs_dir: Optional[str | Path] = None,
    limit: int = 200,
) -> pd.DataFrame:
    """Le eventos recentes da trilha de fallback legado."""
    return _read_rows(logs_dir=logs_dir, limit=limit)


def _coerce_reference_time(reference_time: Any) -> datetime:
    if isinstance(reference_time, datetime):
        return reference_time
    raw = str(reference_time or "").strip()
    if not raw:
        return datetime.now()
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return datetime.now()


def _filter_by_temporal_window(
    *,
    logs_dir: Optional[str | Path],
    lookback_days: int,
    reference_time: Any,
    telemetry: Optional[dict[str, int]] = None,
) -> pd.DataFrame:
    lookback = max(1, int(lookback_days or 1))
    cutoff_end = _coerce_reference_time(reference_time)
    cutoff_start = cutoff_end - timedelta(days=lookback)
    start_epoch = int(cutoff_start.timestamp())
    end_epoch = int(cutoff_end.timestamp())
    from services.legacy_audit import menu_invalid_timestamp_fallback_policy

    allow_global_invalid_fallback, _reason = (
        menu_invalid_timestamp_fallback_policy.is_global_invalid_timestamp_fallback_enabled(
            reference_time=cutoff_end
        )
    )
    repo = _repository(logs_dir=logs_dir)
    if not get_menu_catalog_fallback_audit_db_path(logs_dir=logs_dir).exists():
        _accumulate_telemetry(telemetry, key="invalid_timestamp_count", value=0)
        return pd.DataFrame(columns=_HEADERS)

    try:
        rows, invalid_count = repo.query_interval(
            start_epoch=start_epoch,
            end_epoch=end_epoch,
            allow_global_invalid_fallback=allow_global_invalid_fallback,
            telemetry=telemetry,
        )
    except Exception as exc:  # pragma: no cover
        registrar_log("MenuCatalogAudit", f"Falha ao consultar janela temporal: {exc}", "WARNING")
        _accumulate_telemetry(telemetry, key="invalid_timestamp_count", value=0)
        return pd.DataFrame(columns=_HEADERS)

    _accumulate_telemetry(
        telemetry,
        key="invalid_timestamp_count",
        value=int(invalid_count),
    )
    return pd.DataFrame(rows, columns=_HEADERS)


def build_menu_catalog_cutover_decision(
    *,
    logs_dir: Optional[str | Path] = None,
    lookback_rows: int = 500,
    max_legacy_used: int = 0,
    max_errors: int = 0,
    lookback_days: Optional[int] = None,
    reference_time: Any = None,
) -> dict[str, Any]:
    """Avalia se o corte da compat layer pode ser iniciado com base na trilha."""
    telemetry: dict[str, int] = {
        "lock_retry_count": 0,
        "invalid_timestamp_count": 0,
    }
    if lookback_days is not None:
        df = _filter_by_temporal_window(
            logs_dir=logs_dir,
            lookback_days=lookback_days,
            reference_time=reference_time,
            telemetry=telemetry,
        )
    else:
        df = _read_rows(
            logs_dir=logs_dir,
            limit=max(1, int(lookback_rows or 1)),
            telemetry=telemetry,
        )
        if not df.empty:
            timestamps = _parse_timestamps(df["timestamp"])
            telemetry["invalid_timestamp_count"] = int(timestamps.isna().sum())
    return menu_catalog_cutover_policy.build_cutover_decision_from_events(
        events_df=df,
        max_legacy_used=int(max_legacy_used),
        max_errors=int(max_errors),
        lookback_days=int(lookback_days) if lookback_days is not None else None,
        lookback_rows=int(lookback_rows),
        invalid_timestamp_count=int(telemetry.get("invalid_timestamp_count", 0)),
        lock_retry_count=int(telemetry.get("lock_retry_count", 0)),
    )


def _build_cutover_ports() -> MenuCatalogCutoverPorts:
    return MenuCatalogCutoverPorts(
        resolve_report_path=get_menu_catalog_cutover_report_path,
        build_cutover_decision=build_menu_catalog_cutover_decision,
        build_global_shutdown_decision=build_menu_catalog_global_shutdown_decision,
        record_fallback_event=record_menu_catalog_fallback_event,
        get_menu_compat_off_users=get_menu_compat_off_users,
    )


def generate_menu_catalog_cutover_report(
    *,
    logs_dir: Optional[str | Path] = None,
    lookback_days: int = 7,
    max_legacy_used: int = 0,
    max_errors: int = 0,
    reference_time: Any = None,
) -> dict[str, Any]:
    """Facade compativel para orquestrador de relatorio de corte."""
    from services.legacy_audit import menu_catalog_cutover_orchestrator

    menu_catalog_cutover_orchestrator.configure_menu_catalog_cutover_ports(
        _build_cutover_ports
    )
    return menu_catalog_cutover_orchestrator.generate_menu_catalog_cutover_report(
        logs_dir=logs_dir,
        lookback_days=lookback_days,
        max_legacy_used=max_legacy_used,
        max_errors=max_errors,
        reference_time=reference_time,
    )


def build_menu_catalog_global_shutdown_decision(
    *,
    logs_dir: Optional[str | Path] = None,
    lookback_days: Optional[int] = None,
    max_legacy_used: Optional[int] = None,
    max_errors: Optional[int] = None,
    reference_time: Any = None,
) -> dict[str, Any]:
    """Avalia criterio final para desligamento global da compat layer do menu."""
    policy = get_menu_compat_global_shutdown_policy()
    threshold_used, threshold_errors = get_menu_compat_global_shutdown_thresholds()
    effective_lookback_days = (
        int(lookback_days)
        if lookback_days is not None
        else int(policy.get("lookback_days", 7))
    )
    effective_max_legacy_used = (
        int(max_legacy_used) if max_legacy_used is not None else int(threshold_used)
    )
    effective_max_errors = (
        int(max_errors) if max_errors is not None else int(threshold_errors)
    )

    cutover_decision = build_menu_catalog_cutover_decision(
        logs_dir=logs_dir,
        lookback_days=effective_lookback_days,
        max_legacy_used=effective_max_legacy_used,
        max_errors=effective_max_errors,
        reference_time=reference_time,
    )
    temporal_df = _filter_by_temporal_window(
        logs_dir=logs_dir,
        lookback_days=effective_lookback_days,
        reference_time=reference_time,
    )
    return menu_catalog_cutover_policy.build_global_shutdown_decision_from_events(
        cutover_decision=cutover_decision,
        events_df=temporal_df,
        lookback_days=effective_lookback_days,
        max_legacy_used=int(effective_max_legacy_used),
        max_errors=int(effective_max_errors),
    )


def execute_menu_catalog_canary_off_pilot(
    *,
    logs_dir: Optional[str | Path] = None,
    lookback_days: int = 7,
    max_legacy_used: int = 0,
    max_errors: int = 0,
    reference_time: Any = None,
) -> dict[str, Any]:
    """Facade compativel para orquestrador de piloto canario OFF."""
    from services.legacy_audit import menu_catalog_cutover_orchestrator

    menu_catalog_cutover_orchestrator.configure_menu_catalog_cutover_ports(
        _build_cutover_ports
    )
    return menu_catalog_cutover_orchestrator.execute_menu_catalog_canary_off_pilot(
        logs_dir=logs_dir,
        lookback_days=lookback_days,
        max_legacy_used=max_legacy_used,
        max_errors=max_errors,
        reference_time=reference_time,
    )


__all__ = [
    "get_menu_catalog_fallback_audit_path",
    "get_menu_catalog_fallback_audit_db_path",
    "get_menu_catalog_cutover_report_path",
    "record_menu_catalog_fallback_event",
    "read_menu_catalog_fallback_audit",
    "build_menu_catalog_cutover_decision",
    "build_menu_catalog_global_shutdown_decision",
    "generate_menu_catalog_cutover_report",
    "execute_menu_catalog_canary_off_pilot",
]
