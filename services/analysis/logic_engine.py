# -*- coding: utf-8 -*-
"""
services/logic_engine.py

Motor de lógica centralizado para classificação de resultados PCR.
Elimina a duplicação de regras entre UI e Service.

Dependências: config/business_rules.py
"""

from typing import Optional, Union

from domain.ct_rules import classificar_ct as _classificar_ct


def classificar_ct(ct_val: Union[float, str, None]) -> str:
    """Facade para domain.ct_rules.classificar_ct."""
    return _classificar_ct(ct_val)
