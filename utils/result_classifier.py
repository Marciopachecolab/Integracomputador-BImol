# -*- coding: utf-8 -*-
"""Classificador único de resultados RT-PCR."""

from typing import Optional
from config.ct_thresholds import CTThresholdsVR1E2


def classificar_resultado(
    ct_alvo: Optional[float],
    ct_rp: Optional[float],
    thresholds: CTThresholdsVR1E2,
) -> str:
    """
    Classifica resultado RT-PCR baseado em CTs do alvo e RP.
    
    Args:
        ct_alvo: Valor de CT do alvo viral (ou None se não detectado)
        ct_rp: Valor de CT do controle interno (RP)
        thresholds: Objeto com os thresholds de classificação
    
    Returns:
        str: "Detectado", "Nao Detectado", "Inconclusivo" ou "Invalido"
    
    Regras de classificação:
        1. RP inválido (fora 15-35 ou None) → "Invalido"
        2. CT alvo ausente (None) → "Nao Detectado"
        3. CT alvo <= 38 → "Detectado"
        4. CT alvo 38.01-40 → "Inconclusivo"
        5. CT alvo > 40 → "Nao Detectado"
    
    Exemplos:
        >>> classificar_resultado(25.0, 20.0, VR1E2_THRESHOLDS)
        'Detectado'
        >>> classificar_resultado(39.0, 25.0, VR1E2_THRESHOLDS)
        'Inconclusivo'
        >>> classificar_resultado(25.0, 10.0, VR1E2_THRESHOLDS)
        'Invalido'
    """
    # 1) Validação de RP
    if ct_rp is None or not (thresholds.RP_MIN <= ct_rp <= thresholds.RP_MAX):
        return "Invalido"

    # 2) Casos de alvo ausente
    if ct_alvo is None:
        return "Nao Detectado"

    # 3) Faixas de CT do alvo
    if ct_alvo <= thresholds.DETECT_MAX:
        return "Detectado"
    
    if thresholds.INCONC_MIN <= ct_alvo <= thresholds.INCONC_MAX:
        return "Inconclusivo"
    
    return "Nao Detectado"
