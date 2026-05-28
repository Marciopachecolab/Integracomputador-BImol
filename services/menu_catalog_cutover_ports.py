# -*- coding: utf-8 -*-
"""Contrato de portas para orquestracao de corte da compat layer do menu."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Optional


@dataclass(frozen=True)
class MenuCatalogCutoverPorts:
    """Portas necessarias para orquestrar relatorio/piloto de cutover."""

    resolve_report_path: Callable[..., Path]
    build_cutover_decision: Callable[..., dict[str, Any]]
    build_global_shutdown_decision: Callable[..., dict[str, Any]]
    record_fallback_event: Callable[..., None]
    get_menu_compat_off_users: Callable[[], Iterable[str]]


__all__ = ["MenuCatalogCutoverPorts"]
