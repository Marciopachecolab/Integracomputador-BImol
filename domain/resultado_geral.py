# -*- coding: utf-8 -*-
"""
Regra canônica de Resultado_geral.

Ponto único de implementação da prioridade:
  Inválido > Indeterminado > Detectável > Não Detectável

Nenhuma camada (UI, pipeline) deve replicar essa lógica — todas delegam aqui.
"""

from __future__ import annotations

from typing import Dict

RESULTADO_INVALIDO = "Inválido"
RESULTADO_INDETERMINADO = "Indeterminado"
RESULTADO_NAO_DETECTAVEL = "Não Detectável"
RESULTADO_DETECTAVEL_PREFIXO = "Detectável para"

_INDETERMINADO = {"indeterminado", "inconclusivo", "inc"}
_DETECTAVEL = {"detectável", "detectavel", "detectado"}


def _norm(s: object) -> str:
    # str(enum) em Python 3.11+ retorna 'ClassName.member' — usar .value quando disponível
    val = s.value if hasattr(s, "value") else s
    return str(val).strip().casefold()


def calcular_resultado_geral(rp_valido: bool, alvos: Dict[str, str]) -> str:
    """
    Calcula Resultado_geral com prioridade canônica.

    Args:
        rp_valido: True se o RP está dentro dos limites aceitáveis.
        alvos: {nome_alvo: resultado_string} — não incluir RP neste dict.

    Returns:
        Uma das constantes RESULTADO_* ou "Detectável para <alvos>".
    """
    if not rp_valido:
        return RESULTADO_INVALIDO

    detectaveis: list[str] = []
    has_indeterminado = False

    for nome, resultado in alvos.items():
        n = _norm(resultado)
        if n in _INDETERMINADO:
            has_indeterminado = True
        elif n in _DETECTAVEL:
            detectaveis.append(nome)

    if has_indeterminado:
        return RESULTADO_INDETERMINADO
    if detectaveis:
        return f"{RESULTADO_DETECTAVEL_PREFIXO} {', '.join(detectaveis)}"
    return RESULTADO_NAO_DETECTAVEL
