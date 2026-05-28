# -*- coding: utf-8 -*-
"""Pure extraction plate mapping calculations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

_KIT_PARTS = {"96": 1, "48": 2, "32": 3, "24": 4}
_KIT_WIDTHS = {"96": 12, "48": 6, "32": 4, "24": 3}
_ROW_LABELS = list("ABCDEFGH")


@dataclass(frozen=True)
class ExtractionMappingResult:
    """Result of building an extraction-to-analysis plate mapping."""

    kit: str
    parte: int
    mapeamento: pd.DataFrame
    preview_visual: pd.DataFrame
    bloco_fatiado: pd.DataFrame


def build_extraction_mapping(
    df_bloco: pd.DataFrame,
    kit: str,
    parte: int,
) -> ExtractionMappingResult:
    """Build base mapping and expanded visual preview for a selected kit/part."""
    kit_normalized = str(kit).strip()
    if kit_normalized not in _KIT_WIDTHS:
        raise ValueError("Kit deve ser 96, 48, 32 ou 24.")

    parte_normalized = int(parte or 1)
    max_partes = _KIT_PARTS[kit_normalized]
    if parte_normalized < 1 or parte_normalized > max_partes:
        raise ValueError(f"Parte da placa para {kit_normalized} pocos deve estar entre 1 e {max_partes}.")

    map_data = _load_plate_mapping(kit_normalized, parte_normalized)
    block_slice = _slice_block(df_bloco, kit_normalized, parte_normalized)
    flat_samples = _flatten_column_major(block_slice)

    base_rows: list[dict[str, Any]] = []
    preview_rows: list[dict[str, Any]] = []

    for index, map_item in enumerate(map_data):
        sample = flat_samples[index] if index < len(flat_samples) else ""
        analysis_wells = tuple(map_item.get("analise") or ())
        base_well = str(analysis_wells[0]) if analysis_wells else ""
        base_rows.append(
            {
                "Poco": base_well,
                "Poco_Analise": analysis_wells,
                "Amostra": sample,
                "Codigo": sample,
                "Poço": base_well,
                "Código": sample,
            }
        )
        for well in analysis_wells:
            preview_rows.append(
                {
                    "Poco": str(well),
                    "Amostra": sample,
                    "Codigo": sample,
                    "Poço": str(well),
                    "Código": sample,
                }
            )

    mapeamento = pd.DataFrame(base_rows)
    preview_visual = pd.DataFrame(preview_rows)
    return ExtractionMappingResult(
        kit=kit_normalized,
        parte=parte_normalized,
        mapeamento=mapeamento[
            ["Poco", "Poco_Analise", "Amostra", "Codigo", "Poço", "Código"]
        ],
        preview_visual=preview_visual[["Poco", "Amostra", "Codigo", "Poço", "Código"]],
        bloco_fatiado=_format_block_for_display(block_slice),
    )


def _load_plate_mapping(kit: str, parte: int) -> list[dict[str, Any]]:
    from domain.plate_mapping import (
        gerar_mapeamento_24,
        gerar_mapeamento_32,
        gerar_mapeamento_48,
        gerar_mapeamento_96,
    )

    mapping_builders = {
        "96": gerar_mapeamento_96,
        "48": lambda: gerar_mapeamento_48(parte),
        "32": lambda: gerar_mapeamento_32(parte),
        "24": lambda: gerar_mapeamento_24(parte),
    }
    return mapping_builders[kit]()


def _slice_block(df_bloco: pd.DataFrame, kit: str, parte: int) -> pd.DataFrame:
    width = _KIT_WIDTHS[kit]
    start_col = 0 if kit == "96" else (parte - 1) * width
    end_col = start_col + width
    return df_bloco.iloc[:, start_col:end_col].copy()


def _flatten_column_major(df: pd.DataFrame) -> list[str]:
    return [
        _format_sample_value(df.iat[row_index, col_index])
        for col_index in range(df.shape[1])
        for row_index in range(df.shape[0])
    ]


def _format_sample_value(value: Any) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _format_block_for_display(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.index = _ROW_LABELS[: len(out.index)]
    out.columns = [str(index + 1) for index in range(len(out.columns))]
    return out
