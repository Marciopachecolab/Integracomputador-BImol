# -*- coding: utf-8 -*-
"""Helpers para mascaramento de dados sensiveis em logs operacionais."""

from __future__ import annotations


def mask_patient_name(value: object) -> str:
    """
    Mascara nome de paciente para logs.

    Estrategia:
    - vazio -> ""
    - 1..2 chars -> "*" repetido
    - >=3 chars -> primeira letra + "***" + ultima letra
    """
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= 2:
        return "*" * len(text)
    return f"{text[0]}***{text[-1]}"

