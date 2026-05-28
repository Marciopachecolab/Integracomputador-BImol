# -*- coding: utf-8 -*-
"""Orquestracao de relatorio/piloto para corte da compat layer do menu."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from services.menu_catalog_cutover_ports import MenuCatalogCutoverPorts
from utils.network_io import RetryPolicy, open_with_retry

_CUTOVER_PORTS_RESOLVER: Callable[[], MenuCatalogCutoverPorts] | None = None


def configure_menu_catalog_cutover_ports(
    resolver: Callable[[], MenuCatalogCutoverPorts],
) -> None:
    """Registra resolver de portas para desacoplar orquestrador do facade."""
    global _CUTOVER_PORTS_RESOLVER
    _CUTOVER_PORTS_RESOLVER = resolver


def clear_menu_catalog_cutover_ports() -> None:
    """Limpa resolver registrado (util para isolamento de testes)."""
    global _CUTOVER_PORTS_RESOLVER
    _CUTOVER_PORTS_RESOLVER = None


def _resolve_ports() -> MenuCatalogCutoverPorts:
    if _CUTOVER_PORTS_RESOLVER is None:
        raise RuntimeError("cutover_ports_not_configured")
    return _CUTOVER_PORTS_RESOLVER()


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


def generate_menu_catalog_cutover_report(
    *,
    logs_dir: Optional[str | Path] = None,
    lookback_days: int = 7,
    max_legacy_used: int = 0,
    max_errors: int = 0,
    reference_time: Any = None,
) -> dict[str, Any]:
    """Gera relatorio de corte com portas injetadas por contrato."""
    ports = _resolve_ports()
    report_path = ports.resolve_report_path(logs_dir=logs_dir)
    decision = ports.build_cutover_decision(
        logs_dir=logs_dir,
        lookback_days=lookback_days,
        max_legacy_used=max_legacy_used,
        max_errors=max_errors,
        reference_time=reference_time,
    )
    global_shutdown_decision = ports.build_global_shutdown_decision(
        logs_dir=logs_dir,
        lookback_days=lookback_days,
        max_legacy_used=max_legacy_used,
        max_errors=max_errors,
        reference_time=reference_time,
    )
    generated_at = _coerce_reference_time(reference_time).isoformat(timespec="seconds")
    payload = {
        "generated_at": generated_at,
        "window": {"lookback_days": int(lookback_days)},
        "decision": decision,
        "global_shutdown_decision": global_shutdown_decision,
    }
    policy = RetryPolicy.from_env()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open_with_retry(report_path, "w", encoding="utf-8", policy=policy) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return {"report_path": str(report_path), **payload}


def execute_menu_catalog_canary_off_pilot(
    *,
    logs_dir: Optional[str | Path] = None,
    lookback_days: int = 7,
    max_legacy_used: int = 0,
    max_errors: int = 0,
    reference_time: Any = None,
) -> dict[str, Any]:
    """Executa piloto de canario OFF mantendo trilha reversivel."""
    ports = _resolve_ports()
    trail_mode = "operational_definitive" if logs_dir is None else "scoped_override"
    decision = ports.build_cutover_decision(
        logs_dir=logs_dir,
        lookback_days=lookback_days,
        max_legacy_used=max_legacy_used,
        max_errors=max_errors,
        reference_time=reference_time,
    )
    off_users = sorted(str(user) for user in ports.get_menu_compat_off_users())

    reason = ""
    pilot_status = "executed"
    if not off_users:
        pilot_status = "blocked"
        reason = "no_canary_off_users_configured"
    elif not decision["allow_cutover"]:
        pilot_status = "blocked"
        reason = "cutover_decision_blocked"

    event = {
        "timestamp": _coerce_reference_time(reference_time).isoformat(timespec="seconds"),
        "actor": "system",
        "mode": "pilot_canary_off",
        "outcome": pilot_status,
        "error": reason,
    }
    ports.record_fallback_event(logs_dir=logs_dir, event=event, max_rows=5000)

    report = generate_menu_catalog_cutover_report(
        logs_dir=logs_dir,
        lookback_days=lookback_days,
        max_legacy_used=max_legacy_used,
        max_errors=max_errors,
        reference_time=reference_time,
    )
    return {
        "trail_mode": trail_mode,
        "pilot_status": pilot_status,
        "reason": reason,
        "off_users_count": len(off_users),
        "off_users": off_users,
        "decision": decision,
        "report_path": report["report_path"],
    }


__all__ = [
    "clear_menu_catalog_cutover_ports",
    "configure_menu_catalog_cutover_ports",
    "generate_menu_catalog_cutover_report",
    "execute_menu_catalog_canary_off_pilot",
]
