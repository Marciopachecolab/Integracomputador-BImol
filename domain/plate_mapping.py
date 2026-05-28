# -*- coding: utf-8 -*-
"""
Domain rules for plate mapping generation.
"""

from typing import Dict, List

LINHAS = "ABCDEFGH"


def gerar_mapeamento_96() -> List[Dict]:
    """Gera o mapeamento para placa 96 (1:1)."""
    mapeamento: List[Dict] = []
    for i in range(96):
        linha_extracao = LINHAS[i % 8]
        coluna_extracao = (i // 8) + 1
        poco = f"{linha_extracao}{coluna_extracao}"
        mapeamento.append({"amostra": i + 1, "extracao": (poco,), "analise": (poco,)})
    return mapeamento


def gerar_mapeamento_48(parte: int = 1) -> List[Dict]:
    """Gera o mapeamento para placa 48 (1 amostra -> 2 pocos de analise)."""
    if parte not in [1, 2]:
        raise ValueError("Parte da placa para 48 pocos deve ser 1 ou 2.")

    mapeamento: List[Dict] = []
    col_offset_extracao = 0 if parte == 1 else 6

    for i in range(48):
        linha_idx = i % 8
        bloco_coluna_extracao = i // 8

        linha = LINHAS[linha_idx]
        coluna_extracao_real = col_offset_extracao + bloco_coluna_extracao + 1

        amostra_idx_global = (coluna_extracao_real - 1) * 8 + linha_idx

        coluna_analise_1 = 2 * bloco_coluna_extracao + 1
        coluna_analise_2 = 2 * bloco_coluna_extracao + 2

        mapeamento.append(
            {
                "amostra": amostra_idx_global + 1,
                "extracao": (f"{linha}{coluna_extracao_real}",),
                "analise": (f"{linha}{coluna_analise_1}", f"{linha}{coluna_analise_2}"),
            }
        )
    return mapeamento


def gerar_mapeamento_32(parte: int = 1) -> List[Dict]:
    """Gera o mapeamento para placa 32."""
    if parte not in [1, 2, 3]:
        raise ValueError("Parte da placa para 32 pocos deve ser 1, 2 ou 3.")

    mapeamento: List[Dict] = []
    col_offset_extracao = (parte - 1) * 4

    for i in range(32):
        linha_idx = i % 8
        bloco_coluna_extracao = i // 8

        linha = LINHAS[linha_idx]
        coluna_extracao = col_offset_extracao + bloco_coluna_extracao + 1

        amostra_idx_global = (coluna_extracao - 1) * 8 + linha_idx

        cols_analise = [f"{linha}{3 * bloco_coluna_extracao + j + 1}" for j in range(3)]

        mapeamento.append(
            {
                "amostra": amostra_idx_global + 1,
                "extracao": (f"{linha}{coluna_extracao}",),
                "analise": tuple(cols_analise),
            }
        )
    return mapeamento


def gerar_mapeamento_24(parte: int = 1) -> List[Dict]:
    """Gera o mapeamento para placa 24."""
    if parte not in [1, 2, 3, 4]:
        raise ValueError("Parte da placa para 24 pocos deve ser 1, 2, 3 ou 4.")

    mapeamento: List[Dict] = []
    col_offset_extracao = (parte - 1) * 3

    for i in range(24):
        linha_idx = i % 8
        bloco_coluna_extracao = i // 8

        linha = LINHAS[linha_idx]
        coluna_extracao = col_offset_extracao + bloco_coluna_extracao + 1

        amostra_idx_global = (coluna_extracao - 1) * 8 + linha_idx

        cols_analise = [f"{linha}{4 * bloco_coluna_extracao + j + 1}" for j in range(4)]

        mapeamento.append(
            {
                "amostra": amostra_idx_global + 1,
                "extracao": (f"{linha}{coluna_extracao}",),
                "analise": tuple(cols_analise),
            }
        )
    return mapeamento
