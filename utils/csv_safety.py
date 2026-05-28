# -*- coding: utf-8 -*-
"""
CSV Safety - Sanitização para prevenir CSV Injection (R2)

Protege contra injeção de fórmulas maliciosas via valores de célula CSV.

CWE-1236: Improper Neutralization of Formula Elements in a CSV File
"""

from typing import Any
import re


def sanitize_csv_value(value: Any) -> str:
    """
    Sanitiza valor para prevenir CSV Injection.
    
    Excel/LibreOffice interpretam valores começando com =, +, -, @, \t, \r como fórmulas.
    Atacantes podem injetar: =CMD|'/C calc'!A1
    
    Args:
        value: Valor a ser sanitizado
    
    Returns:
        String segura para incluir em CSV
    
    Examples:
        >>> sanitize_csvvalue("Normal text")
        "Normal text"
        
        >>> sanitize_csv_value("=1+1")
        "'=1+1"  # Escapado com apóstrofo
        
        >>> sanitize_csv_value("=CMD|'/C calc'!A1")
        "'=CMD|'/C calc'!A1"  # Neutralizado
    """
    if value is None:
        return ""
    
    # Converter para string
    s = str(value).strip()
    
    # Lista de caracteres perigosos (iniciam fórmulas)
    dangerous_prefixes = ('=', '+', '-', '@', '\t', '\r', '\n')
    
    # Se começa com caracter perigoso, escapar com apóstrofo
    if s and s[0] in dangerous_prefixes:
        return "'" + s
    
    # Também escapar pipes e comandos suspeitos
    suspicious_patterns = [
        r'cmd',
        r'powershell',
        r'system',
        r'exec',
        r'!A\d+',  # Referências de célula Excel
    ]
    
    s_lower = s.lower()
    for pattern in suspicious_patterns:
        if re.search(pattern, s_lower):
            return "'" + s
    
    return s


def sanitize_dataframe_for_csv(df):
    """
    Sanitiza DataFrame inteiro para exportação CSV segura.
    
    Args:
        df: DataFrame Pandas
    
    Returns:
        DataFrame com valores sanitizados
    
    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"col": ["=SUM(A1)", "normal"]})
        >>> df_safe = sanitize_dataframe_for_csv(df)
        >>> df_safe.to_csv("output.csv")  # Seguro
    """
    import pandas as pd
    
    # Aplicar sanitização em todas as colunas
    df_safe = df.copy()
    
    for col in df_safe.columns:
        if df_safe[col].dtype == 'object':  # Apenas colunas de texto
            df_safe[col] = df_safe[col].apply(sanitize_csv_value)
    
    return df_safe
