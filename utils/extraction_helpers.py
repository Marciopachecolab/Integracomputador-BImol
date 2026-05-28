# -*- coding: utf-8 -*-
"""Helpers puros de extração — sem dependência de tkinter."""

from typing import Optional

import pandas as pd

from utils.logger import registrar_log


def _extrair_numero_extracao(caminho_arquivo: str) -> Optional[str]:
    """Extrai o número da extração da célula C8 do arquivo de extração.

    Returns:
        String com o número da extração ou None se não encontrado.
    """
    try:
        df_c8 = pd.read_excel(
            caminho_arquivo,
            sheet_name="PLANILHA EXTRAÇÃO",
            usecols="C",
            skiprows=7,
            nrows=1,
            header=None,
            engine="openpyxl",
        )
        if not df_c8.empty and df_c8.iloc[0, 0] is not pd.NA:
            valor_c8 = str(df_c8.iloc[0, 0]).strip()
            if valor_c8 and valor_c8.upper() not in ("NAN", "NONE", ""):
                registrar_log(
                    "BuscaExtração",
                    f"Número extração encontrado em C8: {valor_c8}",
                    "INFO",
                )
                return valor_c8
        registrar_log(
            "BuscaExtração",
            "Célula C8 vazia ou inválida — número extração não encontrado",
            "WARNING",
        )
        return None
    except Exception as e:
        registrar_log(
            "BuscaExtração",
            f"Erro ao extrair número extração de C8: {e}",
            "WARNING",
        )
        return None
