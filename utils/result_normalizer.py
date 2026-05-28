# -*- coding: utf-8 -*-
"""Normalizador de labels de resultados RT-PCR."""

from typing import Optional


# Mapeamento de todas as variações de texto para formato canônico
NORMALIZED_RESULTS = {
    # Detectado
    "DETECTADO": "Detectado",
    "Detectado": "Detectado",
    "Det": "Detectado",
    "DET": "Detectado",
    "Positivo": "Detectado",
    "POSITIVO": "Detectado",
    "POS": "Detectado",
    "Pos": "Detectado",
    # Não detectado
    "NAO DETECTADO": "Nao Detectado",
    "NÃO DETECTADO": "Nao Detectado",
    "Nao Detectado": "Nao Detectado",
    "ND": "Nao Detectado",
    "Negativo": "Nao Detectado",
    "NEGATIVO": "Nao Detectado",
    "NEG": "Nao Detectado",
    "Neg": "Nao Detectado",
    # Inconclusivo (aceita variantes Indeterminado/Inc)
    "INDETERMINADO": "Inconclusivo",
    "Indeterminado": "Inconclusivo",
    "Inc": "Inconclusivo",
    "INC": "Inconclusivo",
    "INCONCLUSIVO": "Inconclusivo",
    "Inconclusivo": "Inconclusivo",
    # Inválido
    "INVALIDO": "Invalido",
    "INVÁLIDO": "Invalido",
    "Invalido": "Invalido",
}


def normalize_result_label(raw: Optional[str]) -> Optional[str]:
    """
    Normaliza variações de texto de resultado para formato canônico.
    
    Converte diferentes formatos de resultado (abreviados, por extenso,
    maiúsculas, etc.) para o formato padrão usado internamente.
    
    Args:
        raw: String com resultado em formato variável
    
    Returns:
        str ou None: Resultado normalizado ou None se entrada for None
    
    Exemplos:
        >>> normalize_result_label("DET")
        'Detectado'
        >>> normalize_result_label("ND")
        'Nao Detectado'
        >>> normalize_result_label("Inc")
        'Inconclusivo'
        >>> normalize_result_label(None)
        None
    """
    if raw is None:
        return None
    
    key = str(raw).strip()
    return NORMALIZED_RESULTS.get(key, key)
