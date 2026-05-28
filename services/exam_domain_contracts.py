"""Contratos de dominio para tipo/filtro de alvos em exames RT-PCR."""

from __future__ import annotations

from typing import Final


SUPPORTED_FILTERS: Final[tuple[str, ...]] = ("FAM", "VIC", "ROX", "CY5", "NONE", "NED")
SUPPORTED_TYPES: Final[tuple[str, ...]] = (
    "VIRAL",
    "CONTROL_INTERNAL",
    "CONTROL_EXTERNAL",
    "RP",
    "BACTERIANO",
)

_TYPE_ALIAS: Final[dict[str, str]] = {
    "CI": "CONTROL_INTERNAL",
    "CONTROLINTERNAL": "CONTROL_INTERNAL",
    "CE": "CONTROL_EXTERNAL",
    "CONTROLEXTERNAL": "CONTROL_EXTERNAL",
}


def normalize_target_filter(value: object) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return "NONE"
    return text


def normalize_target_type(value: object) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return "VIRAL"
    return _TYPE_ALIAS.get(text, text)


def is_supported_target_filter(value: object) -> bool:
    return normalize_target_filter(value) in SUPPORTED_FILTERS


def is_supported_target_type(value: object) -> bool:
    return normalize_target_type(value) in SUPPORTED_TYPES


def is_control_internal_type(value: object) -> bool:
    return normalize_target_type(value) in {"CONTROL_INTERNAL", "RP"}


def uses_default_viral_rule(value: object) -> bool:
    return normalize_target_type(value) in {"VIRAL", "BACTERIANO"}
