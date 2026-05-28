"""
Conversor canônico para a coluna Selecionado do DataFrame de análise.

Aceita qualquer formato gravado pelo motor (strings "[X]"/"[ ]") ou pela UI
(bool True/False, "sim"/"nao", string vazia, None, NaN) e devolve bool.

Módulo puro — sem dependência de tkinter, customtkinter ou serviços externos.
"""

from __future__ import annotations

import math
from typing import Any

_VERDADEIRO = frozenset({"[x]", "sim", "true", "1", "x", "yes", "y", "selecionado"})
_CHECKMARKS = frozenset({"\u2713", "\u2714", "\u00e2\u0153\u201c"})


def _normalizar_selecionado(valor: Any) -> bool:
    """Normaliza qualquer formato de Selecionado para bool.

    Formatos aceitos:
    - bool True/False           → retorna como está
    - "[X]" / "[x]"             → True
    - "[ ]" / "" / "nao"        → False
    - "sim" / "true" / "1"      → True
    - None / NaN                → False
    """
    if valor is None:
        return False
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, float) and math.isnan(valor):
        return False
    stripped = str(valor).strip()
    return stripped in _CHECKMARKS or stripped.lower() in _VERDADEIRO
