# -*- coding: utf-8 -*-
"""Politica de decisao para corte e desligamento global da compat layer do menu."""

from __future__ import annotations

from typing import Any

import pandas as pd


_ALLOWED_PILOT_MODES = {"pilot_canary_off", "pilot_canary_off_operational"}


def build_cutover_decision_from_events(
    *,
    events_df: pd.DataFrame,
    max_legacy_used: int,
    max_errors: int,
    lookback_days: int | None,
    lookback_rows: int,
    invalid_timestamp_count: int,
    lock_retry_count: int,
) -> dict[str, Any]:
    """Calcula decisao de corte com base em eventos ja filtrados."""
    outcomes = events_df.get("outcome", pd.Series(dtype=str)).astype(str).str.lower()

    used_count = int((outcomes == "used").sum())
    error_count = int((outcomes == "error").sum())
    blocked_count = int((outcomes == "blocked").sum())

    reasons: list[str] = []
    if used_count > int(max_legacy_used):
        reasons.append("legacy_used_above_threshold")
    if error_count > int(max_errors):
        reasons.append("legacy_error_above_threshold")

    return {
        "allow_cutover": len(reasons) == 0,
        "reasons": reasons,
        "metrics": {
            "rows_analyzed": int(len(events_df)),
            "used_count": used_count,
            "error_count": error_count,
            "blocked_count": blocked_count,
            "max_legacy_used": int(max_legacy_used),
            "max_errors": int(max_errors),
            "lookback_days": int(lookback_days) if lookback_days is not None else None,
            "lookback_rows": int(lookback_rows),
            "invalid_timestamp_count": int(invalid_timestamp_count),
            "lock_retry_count": int(lock_retry_count),
        },
    }


def _coverage_days(events_df: pd.DataFrame) -> int:
    if events_df.empty:
        return 0
    timestamps = pd.to_datetime(events_df["timestamp"], errors="coerce", format="ISO8601")
    valid = timestamps.dropna()
    if valid.empty:
        return 0
    span = valid.max() - valid.min()
    return int(span.total_seconds() // 86400) + 1


def build_global_shutdown_decision_from_events(
    *,
    cutover_decision: dict[str, Any],
    events_df: pd.DataFrame,
    lookback_days: int,
    max_legacy_used: int,
    max_errors: int,
) -> dict[str, Any]:
    """Calcula decisao final de desligamento global apos corte."""
    coverage_days = _coverage_days(events_df)
    modes = events_df.get("mode", pd.Series(dtype=str)).astype(str).str.lower()
    pilot_events_count = int(modes.isin(_ALLOWED_PILOT_MODES).sum())

    reasons: list[str] = []
    reasons.extend(str(item) for item in cutover_decision.get("reasons", []))
    if coverage_days < int(max(1, lookback_days)):
        reasons.append("insufficient_temporal_evidence_7d")
    if pilot_events_count <= 0:
        reasons.append("missing_operational_pilot_evidence")

    unique_reasons: list[str] = []
    for reason in reasons:
        if reason and reason not in unique_reasons:
            unique_reasons.append(reason)

    return {
        "allow_global_shutdown": len(unique_reasons) == 0,
        "reasons": unique_reasons,
        "cutover_decision": cutover_decision,
        "evidence": {
            "lookback_days_required": int(max(1, lookback_days)),
            "rows_analyzed": int(len(events_df)),
            "coverage_days": int(coverage_days),
            "pilot_events_count": int(pilot_events_count),
            "max_legacy_used": int(max_legacy_used),
            "max_errors": int(max_errors),
        },
    }


__all__ = [
    "build_cutover_decision_from_events",
    "build_global_shutdown_decision_from_events",
]
