# -*- coding: utf-8 -*-
"""Regras de filtros rapidos do visualizador operacional (F8)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Optional


SUPPORTED_QUICK_FILTERS = {
    "hoje",
    "ultimos_7_dias",
    "status_valida",
    "nenhum",
}


def build_quick_filter_state(chip: str, *, now: Optional[datetime] = None) -> Dict[str, str]:
    """Retorna alteracoes de estado para um filtro rapido."""
    token = str(chip or "").strip().lower() or "nenhum"
    reference = now or datetime.now()
    today = reference.strftime("%Y-%m-%d")

    if token == "hoje":
        return {
            "periodo_inicio": today,
            "periodo_fim": today,
            "status": "",
        }
    if token == "ultimos_7_dias":
        return {
            "periodo_inicio": (reference - timedelta(days=7)).strftime("%Y-%m-%d"),
            "periodo_fim": today,
        }
    if token == "status_valida":
        return {
            "status": "valida",
        }
    return {}


__all__ = ["SUPPORTED_QUICK_FILTERS", "build_quick_filter_state"]
