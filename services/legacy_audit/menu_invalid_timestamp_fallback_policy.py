"""Politica de governanca para fallback global de invalid_timestamp_count."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ENV_MENU_INVALID_TS_FALLBACK_MODE = "INTEGRAGAL_MENU_INVALID_TS_FALLBACK_MODE"
ENV_MENU_INVALID_TS_FALLBACK_CUTOVER_START = "INTEGRAGAL_MENU_INVALID_TS_FALLBACK_CUTOVER_START"
ENV_MENU_INVALID_TS_FALLBACK_GRACE_DAYS = "INTEGRAGAL_MENU_INVALID_TS_FALLBACK_GRACE_DAYS"
ENV_MENU_INVALID_TS_FALLBACK_GOV_FILE = "INTEGRAGAL_MENU_INVALID_TS_FALLBACK_GOV_FILE"

_ALLOWED_MODES = {"enabled", "progressive", "disabled"}


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


def _coerce_non_negative_int(raw_value: Any, default: int) -> int:
    try:
        value = int(str(raw_value or "").strip())
    except Exception:
        return int(default)
    return max(0, value)


def _default_policy() -> dict[str, Any]:
    return {
        "mode": "enabled",
        "cutover_start": "",
        "grace_days": 14,
    }


def _resolve_governance_path() -> Path:
    raw_path = os.getenv(ENV_MENU_INVALID_TS_FALLBACK_GOV_FILE, "").strip()
    if raw_path:
        return Path(raw_path)
    return (
        Path(__file__).resolve().parents[1]
        / "config"
        / "menu_invalid_timestamp_fallback_governance.json"
    )


def _load_from_file() -> dict[str, Any]:
    path = _resolve_governance_path()
    if not path.exists():
        return _default_policy()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _default_policy()
    node = payload.get("menu_invalid_timestamp_fallback", {})
    if not isinstance(node, dict):
        return _default_policy()

    mode = str(node.get("mode", "enabled") or "enabled").strip().lower()
    if mode not in _ALLOWED_MODES:
        raise ValueError("invalid_fallback_mode")
    return {
        "mode": mode,
        "cutover_start": str(node.get("cutover_start", "") or "").strip(),
        "grace_days": _coerce_non_negative_int(node.get("grace_days"), 14),
    }


def get_invalid_timestamp_fallback_policy() -> dict[str, Any]:
    """Retorna politica consolidada (arquivo -> env) para fallback global."""
    policy = _load_from_file()
    raw_mode = os.getenv(ENV_MENU_INVALID_TS_FALLBACK_MODE, "").strip().lower()
    if raw_mode:
        if raw_mode not in _ALLOWED_MODES:
            raise ValueError("invalid_fallback_mode")
        policy["mode"] = raw_mode

    raw_cutover = os.getenv(ENV_MENU_INVALID_TS_FALLBACK_CUTOVER_START, "").strip()
    if raw_cutover:
        policy["cutover_start"] = raw_cutover

    policy["grace_days"] = _coerce_non_negative_int(
        os.getenv(ENV_MENU_INVALID_TS_FALLBACK_GRACE_DAYS),
        int(policy.get("grace_days", 14)),
    )
    return policy


def is_global_invalid_timestamp_fallback_enabled(
    *,
    reference_time: Any = None,
) -> tuple[bool, str]:
    """Decide se fallback global pode ser usado para invalid_timestamp_count."""
    policy = get_invalid_timestamp_fallback_policy()
    mode = str(policy.get("mode", "enabled") or "enabled").strip().lower()
    if mode not in _ALLOWED_MODES:
        raise ValueError("invalid_fallback_mode")
    if mode == "disabled":
        return False, "mode_disabled"
    if mode == "enabled":
        return True, "mode_enabled"

    cutover_raw = str(policy.get("cutover_start", "") or "").strip()
    if not cutover_raw:
        raise ValueError("progressive_mode_requires_cutover_start")

    try:
        cutover_start = datetime.fromisoformat(cutover_raw)
    except ValueError:
        raise ValueError("invalid_progressive_cutover_start") from None

    grace_days = max(0, _coerce_non_negative_int(policy.get("grace_days"), 14))
    reference_dt = _coerce_reference_time(reference_time)
    if reference_dt <= (cutover_start + timedelta(days=grace_days)):
        return True, "progressive_grace_window"
    return False, "progressive_window_elapsed"


__all__ = [
    "get_invalid_timestamp_fallback_policy",
    "is_global_invalid_timestamp_fallback_enabled",
]
