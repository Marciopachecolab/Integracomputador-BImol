# -*- coding: utf-8 -*-
"""Utilitarios contratuais para chave de deduplicacao."""

from __future__ import annotations

from typing import Mapping, Optional, Sequence, Tuple

DEDUPE_FIELDS: Tuple[str, str, str, str] = (
    "corrida_id",
    "amostra_codigo",
    "lote",
    "data_exame",
)


def normalize_dedupe_value(value: object) -> str:
    """Normaliza componente da chave de dedupe em formato contratual."""
    return str(value or "").strip().lower()


def build_dedupe_key(
    values: Mapping[str, object],
    *,
    fields: Sequence[str] = DEDUPE_FIELDS,
) -> Optional[tuple[str, ...]]:
    """
    Monta chave contratual de dedupe.

    Retorna None quando qualquer componente obrigatorio estiver vazio.
    """
    key = tuple(normalize_dedupe_value(values.get(field, "")) for field in fields)
    if not all(key):
        return None
    return key

