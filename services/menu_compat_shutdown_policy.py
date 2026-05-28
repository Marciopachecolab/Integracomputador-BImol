"""Governanca canonica do shutdown global da compat layer do menu."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


ENV_MENU_COMPAT_GLOBAL_MAX_USED = "INTEGRAGAL_MENU_COMPAT_GLOBAL_MAX_USED"
ENV_MENU_COMPAT_GLOBAL_MAX_ERRORS = "INTEGRAGAL_MENU_COMPAT_GLOBAL_MAX_ERRORS"
ENV_MENU_COMPAT_GLOBAL_LOOKBACK_DAYS = "INTEGRAGAL_MENU_COMPAT_GLOBAL_LOOKBACK_DAYS"
ENV_MENU_COMPAT_SHUTDOWN_GOV_FILE = "INTEGRAGAL_MENU_COMPAT_SHUTDOWN_GOV_FILE"


def _coerce_non_negative_int(raw_value: Optional[str], default: int) -> int:
    try:
        value = int(str(raw_value or "").strip())
    except Exception:
        return int(default)
    return max(0, value)


def _default_policy() -> dict[str, int]:
    return {
        "max_legacy_used": 0,
        "max_errors": 0,
        "lookback_days": 7,
    }


def _resolve_governance_path() -> Path:
    raw_path = os.getenv(ENV_MENU_COMPAT_SHUTDOWN_GOV_FILE, "").strip()
    if raw_path:
        return Path(raw_path)
    return Path(__file__).resolve().parents[1] / "config" / "menu_compat_shutdown_governance.json"


def _load_from_file() -> dict[str, int]:
    path = _resolve_governance_path()
    if not path.exists():
        return _default_policy()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _default_policy()
    node = payload.get("menu_compat_global_shutdown", {})
    if not isinstance(node, dict):
        node = {}
    return {
        "max_legacy_used": _coerce_non_negative_int(node.get("max_legacy_used"), 0),  # type: ignore[arg-type]
        "max_errors": _coerce_non_negative_int(node.get("max_errors"), 0),  # type: ignore[arg-type]
        "lookback_days": max(
            1,
            _coerce_non_negative_int(node.get("lookback_days"), 7),  # type: ignore[arg-type]
        ),
    }


def get_menu_compat_global_shutdown_policy() -> dict[str, int]:
    """Retorna politica canonica com precedencia file -> env."""
    policy = _load_from_file()
    policy["max_legacy_used"] = _coerce_non_negative_int(
        os.getenv(ENV_MENU_COMPAT_GLOBAL_MAX_USED),
        int(policy.get("max_legacy_used", 0)),
    )
    policy["max_errors"] = _coerce_non_negative_int(
        os.getenv(ENV_MENU_COMPAT_GLOBAL_MAX_ERRORS),
        int(policy.get("max_errors", 0)),
    )
    policy["lookback_days"] = max(
        1,
        _coerce_non_negative_int(
            os.getenv(ENV_MENU_COMPAT_GLOBAL_LOOKBACK_DAYS),
            int(policy.get("lookback_days", 7)),
        ),
    )
    return policy


def get_menu_compat_global_shutdown_thresholds() -> tuple[int, int]:
    """Retorna thresholds da politica global de shutdown."""
    policy = get_menu_compat_global_shutdown_policy()
    return int(policy["max_legacy_used"]), int(policy["max_errors"])


__all__ = [
    "get_menu_compat_global_shutdown_policy",
    "get_menu_compat_global_shutdown_thresholds",
]
