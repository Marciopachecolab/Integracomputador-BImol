# -*- coding: utf-8 -*-
"""Use case para sincronizar edicoes do mapa da placa para a aba de analise."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional

import pandas as pd

# Colunas calculadas pelo domínio que nunca devem ser sobrescritas pelo sync do mapa.
# Resultado_geral é calculado por domain.resultado_geral; Selecionado e Sugestão_de_repetição
# são estado de UI derivado do resultado — não pertencem ao mapa.
_PROTECTED_COLS = frozenset({
    "Resultado_geral",
    "Selecionado",
    "Sugestão_de_repetição",
    "Sugestao_de_repeticao",
})


_WELL_RE = re.compile(r"^([A-Za-z])0*([0-9]{1,2})$")


def normalize_well_id(value: object) -> str:
    """Normaliza identificador de poco para comparacao contratual."""
    raw = str(value or "").strip().upper()
    if not raw:
        return ""
    match = _WELL_RE.match(raw)
    if not match:
        return raw
    return f"{match.group(1)}{int(match.group(2))}"


def _well_in_group(group_id: object, single_well: str) -> bool:
    wells = [normalize_well_id(part) for part in str(group_id or "").split("+")]
    target = normalize_well_id(single_well)
    return bool(target) and target in wells


@dataclass(frozen=True)
class PlateSyncResult:
    dataframe: pd.DataFrame
    merge_key: Optional[str]
    updated_cells: int
    fallback_used: bool = False


def sync_plate_to_analysis(
    df_analysis: pd.DataFrame,
    df_updated: pd.DataFrame,
) -> PlateSyncResult:
    """
    Aplica merge dos dados editados no mapa para o DataFrame de analise.

    Regra principal:
    - merge por `Poco`/`Poço` (com suporte a grupos `A1+A2`);
    - quando chave nao existe, usa fallback por substituicao direta.
    """
    base = df_analysis.copy()
    incoming = df_updated.copy()

    merge_key: Optional[str] = None
    if "Poco" in base.columns and "Poco" in incoming.columns:
        merge_key = "Poco"
    elif "Poço" in base.columns and "Poço" in incoming.columns:
        merge_key = "Poço"

    updated_cells = 0
    if merge_key is None:
        result = incoming.copy()
        if "Selecionado" not in result.columns:
            result.insert(0, "Selecionado", False)
        cols = ["Selecionado"] + [c for c in result.columns if c != "Selecionado"]
        return PlateSyncResult(
            dataframe=result[cols],
            merge_key=None,
            updated_cells=0,
            fallback_used=True,
        )

    base[merge_key] = base[merge_key].astype(str).str.strip()
    incoming[merge_key] = incoming[merge_key].astype(str).str.strip()
    map_columns = [c for c in incoming.columns if c != merge_key and c not in _PROTECTED_COLS]

    for col in map_columns:
        for _, row in incoming.iterrows():
            poco_id = row.get(merge_key, "")
            mask = base[merge_key].apply(lambda group: _well_in_group(group, poco_id))
            if bool(mask.any()):
                updated_cells += int(mask.sum())
                base.loc[mask, col] = row.get(col)

    if "Selecionado" not in base.columns:
        base.insert(0, "Selecionado", False)
    cols = ["Selecionado"] + [c for c in base.columns if c != "Selecionado"]
    return PlateSyncResult(
        dataframe=base[cols],
        merge_key=merge_key,
        updated_cells=updated_cells,
        fallback_used=False,
    )
