# -*- coding: utf-8 -*-
"""
utils/ct_formatter.py

Formatação de valores CT para exibição na interface.

FASE 2: Substituir "Undetermined" por "Und" e formatar valores numéricos.

Criado em: 2025-12-XX
Parte da refatoração UI - feature/ui-analise-placa-2025_12
"""

from typing import Any


def formatar_ct_display(ct_value: Any) -> str:
    """
    Formata valor CT para exibição na interface.
    
    Regras:
    - None, NaN, "Undetermined" → "—"
    - float válido → f"{ct:.2f}" (2 casas decimais)
    - outros → str(ct_value)

    Args:
        ct_value: Valor CT (float, None, str "Undetermined", etc.)

    Returns:
        String formatada para exibição

    Exemplos:
        >>> formatar_ct_display(None)
        '—'
        >>> formatar_ct_display("Undetermined")
        '—'
        >>> formatar_ct_display(35.678)
        '35.68'
        >>> formatar_ct_display(38.0)
        '38.00'
    """
    # Verificar None
    if ct_value is None:
        return "—"

    # Verificar string "Undetermined" (case-insensitive)
    if isinstance(ct_value, str):
        if ct_value.strip().lower() == "undetermined":
            return "—"

    # Tentar converter para float e formatar
    try:
        import math
        ct_float = float(ct_value)

        # Verificar NaN
        if math.isnan(ct_float):
            return "—"
        
        # Formatar com 2 casas decimais
        return f"{ct_float:.2f}"
        
    except (ValueError, TypeError):
        # Se não for conversível, retornar string original
        return str(ct_value)
