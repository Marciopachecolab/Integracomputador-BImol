"""
Utilitários para validação de operações com DataFrames.

REFATORAÇÃO #3 (2026-01-30): Validação de merge de gabarito.
Objetivo: Detectar wells não mapeados e validar qualidade de dados.
"""

import pandas as pd
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class MergeValidationResult:
    """Resultado da validação de merge."""
    total_rows: int
    mapped_rows: int
    unmapped_rows: int
    mapping_rate: float
    unmapped_keys: List[str]
    is_valid: bool
    validation_message: str


def validate_merge_quality(
    df: pd.DataFrame,
    merge_key: str,
    indicator_column: str,
    min_mapping_rate: float = 0.80,
    max_unmapped_to_log: int = 10
) -> MergeValidationResult:
    """
    Valida qualidade de um merge de DataFrames.
    
    Args:
        df: DataFrame após merge
        merge_key: Coluna usada como chave de merge (ex: 'Well')
        indicator_column: Coluna vinda do merge (ex: 'Amostra')
                          Usado para detectar NaN (não mapeado)
        min_mapping_rate: Taxa mínima de mapeamento aceitável (0.0-1.0)
        max_unmapped_to_log: Máximo de chaves não mapeadas para listar
    
    Returns:
        MergeValidationResult com métricas e status de validação
    
    Examples:
        >>> df_merged = df.merge(gabarito, left_on='Well', right_on='Well_Gab', how='left')
        >>> result = validate_merge_quality(
        ...     df_merged, merge_key='Well',
        ...     indicator_column='Amostra',
        ...     min_mapping_rate=0.80
        ... )
        >>> print(f"Taxa de mapeamento: {result.mapping_rate:.1%}")
        Taxa de mapeamento: 85.4%
        >>> if not result.is_valid:
        ...     print(f"⚠️ {result.validation_message}")
    """
    total_rows = len(df)
    unmapped_mask = df[indicator_column].isna()
    unmapped_rows = unmapped_mask.sum()
    mapped_rows = total_rows - unmapped_rows
    
    mapping_rate = mapped_rows / total_rows if total_rows > 0 else 0.0
    
    # Listar chaves não mapeadas (sample limitado)
    unmapped_keys = df.loc[unmapped_mask, merge_key].unique().tolist()[:max_unmapped_to_log]
    
    # Validar taxa mínima
    is_valid = mapping_rate >= min_mapping_rate
    
    if is_valid:
        validation_message = f"✅ Mapeamento OK: {mapping_rate:.1%} ({mapped_rows}/{total_rows} wells)"
    else:
        validation_message = (
            f"⚠️ Taxa de mapeamento BAIXA: {mapping_rate:.1%} "
            f"({mapped_rows}/{total_rows} wells). "
            f"Mínimo esperado: {min_mapping_rate:.1%}. "
            f"Wells não mapeados (sample): {unmapped_keys[:5]}"
        )
    
    return MergeValidationResult(
        total_rows=total_rows,
        mapped_rows=mapped_rows,
        unmapped_rows=unmapped_rows,
        mapping_rate=mapping_rate,
        unmapped_keys=unmapped_keys,
        is_valid=is_valid,
        validation_message=validation_message
    )


def add_data_source_flag(
    df: pd.DataFrame,
    source_column: str,
    flag_column_name: str = 'Data_Source',
    source_gabarito: str = 'GABARITO',
    source_fallback: str = 'FALLBACK'
) -> pd.DataFrame:
    """
    Adiciona flag indicando origem dos dados (gabarito vs fallback).
    
    Args:
        df: DataFrame com merge já realizado
        source_column: Coluna vinda do merge (ex: 'Amostra')
        flag_column_name: Nome da coluna de flag a criar
        source_gabarito: Valor para linhas mapeadas do gabarito
        source_fallback: Valor para linhas com fallback
    
    Returns:
        DataFrame com nova coluna de flag
    
    Examples:
        >>> df['Sample'] = df['Amostra'].fillna(df['Sample_Raw'])
        >>> df = add_data_source_flag(df, source_column='Amostra')
        >>> df['Data_Source'].value_counts()
        GABARITO    82
        FALLBACK    14
    """
    df = df.copy()
    df[flag_column_name] = source_fallback
    df.loc[df[source_column].notna(), flag_column_name] = source_gabarito
    return df


def log_unmapped_details(
    validation_result: MergeValidationResult,
    logger_func,
    context: str = "MergeValidation",
    log_level_ok: str = "INFO",
    log_level_warning: str = "WARNING"
):
    """
    Loga detalhes de validação de merge.
    
    Args:
        validation_result: Resultado da validação
        logger_func: Função de logging (ex: registrar_log)
        context: Contexto para o log
        log_level_ok: Nível de log se validação OK
        log_level_warning: Nível de log se validação falhou
    """
    if validation_result.is_valid:
        logger_func(context, validation_result.validation_message, log_level_ok)
    else:
        logger_func(context, validation_result.validation_message, log_level_warning)
        
        # Log adicional detalhado se houver muitos não mapeados
        if validation_result.unmapped_rows > 0:
            logger_func(
                context,
                f"📊 Detalhes: {validation_result.unmapped_rows} wells não mapeados. "
                f"Sample: {validation_result.unmapped_keys[:10]}",
                "DEBUG"
            )


__all__ = [
    'MergeValidationResult',
    'validate_merge_quality',
    'add_data_source_flag',
    'log_unmapped_details'
]
