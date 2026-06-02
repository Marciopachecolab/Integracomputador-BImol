# -*- coding: utf-8 -*-
"""
Relatorio estatistico - calculos centralizados para a UI.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import re

import pandas as pd
from utils.text_result_classifier import classify_result_text

# Detecta controles CN/CP e variantes de "controle negativo/positivo"
_CONTROL_RE = re.compile(r"(?:^|\b)(CN|CP)\b|CONTROLE.*(NEG|POS)", re.IGNORECASE)


def _is_control(sample_value: Any) -> bool:
    if sample_value is None:
        return False
    return bool(_CONTROL_RE.search(str(sample_value)))


def _classificar_resultado(value: Any) -> str | None:
    token = classify_result_text(value)
    if token == "INC":
        return "ind"
    if token == "ND":
        return "nd"
    if token == "DET":
        return "det"
    return None


def _result_columns(df: pd.DataFrame) -> List[str]:
    return [
        c
        for c in df.columns
        if str(c).startswith("Res_") or str(c).startswith("Resultado_")
    ]


def _alvo_from_col(col: str) -> str:
    if col.startswith("Res_"):
        name = col[len("Res_") :]
    elif col.startswith("Resultado_"):
        name = col[len("Resultado_") :]
    else:
        name = col
    return name.replace("_", " ").strip()


def calcular_estatisticas_relatorio(
    df_analise: pd.DataFrame,
) -> Tuple[List[Dict[str, int | str]], int]:
    if df_analise is None or df_analise.empty:
        return [], 0

    df_work = df_analise.copy()
    if "Amostra" in df_work.columns:
        df_work = df_work[~df_work["Amostra"].apply(_is_control)]

    total = len(df_work)
    result_cols = _result_columns(df_work)
    if not result_cols:
        return [], total

    table_data: List[Dict[str, int | str]] = []
    for col in result_cols:
        alvo = _alvo_from_col(col)
        alvo_upper = alvo.upper()
        if (
            alvo_upper.startswith("RP")
            or "RP_" in alvo_upper
            or "RP-" in alvo_upper
            or alvo_upper == "GERAL"
        ):
            continue

        nd = det = ind = 0
        for val in df_work[col]:
            cls = _classificar_resultado(val)
            if cls == "nd":
                nd += 1
            elif cls == "det":
                det += 1
            elif cls == "ind":
                ind += 1

        table_data.append(
            {"Alvo": alvo, "ND": nd, "Det": det, "Ind": ind, "Total": total}
        )

    return table_data, total
