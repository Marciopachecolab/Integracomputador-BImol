# -*- coding: utf-8 -*-
"""Classificador textual canonico para resultados DET/ND/INC/INV."""

from __future__ import annotations

import unicodedata
from typing import Any, Optional


def _strip_accents(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ASCII", "ignore").decode("ASCII")


def _normalize_text(value: Any) -> str:
    return _strip_accents(str(value or "")).strip().upper()


def classify_result_text(value: Any) -> Optional[str]:
    """Classifica texto de resultado em token canonico DET/ND/INC/INV.

    Retorna ``None`` quando a entrada nao representa um resultado reconhecido.
    """
    text = _normalize_text(value)
    if not text:
        return None

    if "INVAL" in text or text == "INV":
        return "INV"
    # Ordem importa: "INDETERMINADO" contem "DET".
    if "INDETERMIN" in text or "INCONCL" in text or text == "INC":
        return "INC"
    # Ordem importa: "NAO DETECTAVEL" contem "DET".
    if "NAO" in text or text == "ND" or "NEG" in text:
        return "ND"
    if "DETECT" in text or text == "DET" or "POS" in text:
        return "DET"
    return None


def result_text_to_gal_code(value: Any) -> str:
    """Mapeia texto de resultado para codigo GAL (1/2/3)."""
    token = classify_result_text(value)
    if token == "DET":
        return "1"
    if token == "ND":
        return "2"
    if token == "INC":
        return "3"
    return ""
