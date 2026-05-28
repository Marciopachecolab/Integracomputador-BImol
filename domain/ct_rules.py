# -*- coding: utf-8 -*-
"""
Domain rules for PCR CT classification.
"""

import math
from enum import Enum
from typing import Union

from config.business_rules import (
    CT_MIN_DETECTAVEL,
    CT_MAX_DETECTAVEL,
    CT_MIN_INDETERMINADO,
    CT_MAX_INDETERMINADO,
)
from config.enums import ResultStatus


class ResultadoCt(str, Enum):
    """Resultado de classificação de CT. Herda de str para ser comparável com ResultStatus."""
    DETECTADO = "Detectável"
    INCONCLUSIVO = "Indeterminado"
    NAO_DETECTADO = "Não Detectável"


def _is_missing_ct_value(ct_val: Union[float, str, None]) -> bool:
    return ct_val is None or (isinstance(ct_val, float) and math.isnan(ct_val))


def classificar_ct(ct_val: Union[float, str, None]) -> str:
    """
    Classifica o resultado baseado no valor de CT.

    Regras (Biomanguinhos VR1e2):
    - Vazio/None -> "Nao Detectavel"
    - < CT_MIN_DETECTAVEL -> "Nao Detectavel"
    - CT_MIN_DETECTAVEL <= CT < CT_MAX_DETECTAVEL -> "Detectavel"
    - CT_MIN_INDETERMINADO <= CT <= CT_MAX_INDETERMINADO -> "Indeterminado"
    - > CT_MAX_INDETERMINADO -> "Nao Detectavel"

    Args:
        ct_val: Valor do CT (pode ser string com virgula, float ou None)

    Returns:
        ResultStatus em formato string
    """
    if _is_missing_ct_value(ct_val) or ct_val == "":
        return ResultStatus.NAO_DETECTAVEL

    try:
        val_str = str(ct_val).strip()
        if not val_str:
            return ResultStatus.NAO_DETECTAVEL

        ct = float(val_str.replace(",", "."))

        if ct < CT_MIN_DETECTAVEL:
            return ResultStatus.NAO_DETECTAVEL
        if CT_MIN_DETECTAVEL <= ct < CT_MAX_DETECTAVEL:
            return ResultStatus.DETECTAVEL
        if CT_MIN_INDETERMINADO <= ct <= CT_MAX_INDETERMINADO:
            return ResultStatus.INDETERMINADO
        return ResultStatus.NAO_DETECTAVEL
    except (ValueError, TypeError):
        return ResultStatus.NAO_DETECTAVEL
