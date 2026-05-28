# -*- coding: utf-8 -*-
"""
config/column_constants.py

Constantes centralizadas para nomes de colunas do sistema IntegRAGal.
Elimina inconsistências entre Res_* e Resultado_*.

Criado: 2026-02-09
BUG FIX: Padronização de prefixos de colunas
"""

from typing import Tuple

# Prefixo PADRÃO para colunas de resultado (usado pelo analysis_service)
RESULT_PREFIX = "Res_"

# Prefixo legado para compatibilidade com dados antigos
RESULT_PREFIX_LEGACY = "Resultado_"

# Prefixo para colunas de CT
CT_PREFIX = "CT_"

# Tuple com ambos os prefixos para busca retrocompatível
RESULT_PREFIXES: Tuple[str, str] = (RESULT_PREFIX, RESULT_PREFIX_LEGACY)


def is_result_column(col_name: str) -> bool:
    """
    Verifica se uma coluna é de resultado (aceita ambos os prefixos).
    
    Args:
        col_name: Nome da coluna
        
    Returns:
        True se a coluna começa com Res_ ou Resultado_
    """
    return any(col_name.startswith(prefix) for prefix in RESULT_PREFIXES)


def normalize_result_column_name(col_name: str) -> str:
    """
    Normaliza nome de coluna de resultado para padrão Res_*.
    
    Args:
        col_name: Nome da coluna (ex: "Resultado_ADV" ou "Res_ADV")
        
    Returns:
        Nome normalizado (ex: "Res_ADV")
    """
    if col_name.startswith(RESULT_PREFIX_LEGACY):
        target = col_name[len(RESULT_PREFIX_LEGACY):]
        return f"{RESULT_PREFIX}{target}"
    return col_name


def extract_target_from_result_column(col_name: str) -> str:
    """
    Extrai o nome do alvo de uma coluna de resultado.

    Args:
        col_name: Nome da coluna (ex: "Res_ADV" ou "Resultado_ADV")

    Returns:
        Nome do alvo (ex: "ADV")
    """
    for prefix in RESULT_PREFIXES:
        if col_name.startswith(prefix):
            return col_name[len(prefix):]
    return col_name


def listar_colunas_alvo(columns) -> list:
    """
    Lista colunas de resultado de alvo a partir de um iterável de nomes.

    Aceita Res_* e Resultado_*; exclui colunas de controle interno de RP
    (Res_RP_*, Resultado_RP_*) e a coluna de resultado geral (Resultado_geral,
    Res_geral). Aceita lista, tuple, ou pandas.Index.

    Returns:
        list de nomes de coluna que representam alvos analisáveis.
    """
    resultado = []
    for col in columns:
        col_str = str(col)
        if not any(col_str.startswith(p) for p in RESULT_PREFIXES):
            continue
        alvo = extract_target_from_result_column(col_str).upper()
        if alvo == "GERAL":
            continue
        if alvo.startswith("RP") or "RP_" in alvo or "RP-" in alvo:
            continue
        resultado.append(col_str)
    return resultado
