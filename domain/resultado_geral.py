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
RESULTADO_INDETERMINADO_AMPL = "Indeterminado (ampl)"
RESULTADO_NAO_DETECTAVEL = "Não Detectável"
RESULTADO_DETECTAVEL_PREFIXO = "Detectável para"

_INDETERMINADO = {"indeterminado", "inconclusivo", "inc"}
_DETECTAVEL = {"detectável", "detectavel", "detectado"}

# Valores da coluna "Amp Status" da planilha de corrida que indicam falha de
# amplificacao e disparam a reclassificacao para "Indeterminado (ampl)".
_AMP_STATUS_INDETERMINADO = {"no amp", "inconclusive"}


def _norm(s: object) -> str:
    # str(enum) em Python 3.11+ retorna 'ClassName.member' — usar .value quando disponível
    val = s.value if hasattr(s, "value") else s
    return str(val).strip().casefold()


def _eh_indeterminado(n: str) -> bool:
    """True quando o texto normalizado representa um Indeterminado.

    Aceita o conjunto canonico (`indeterminado`, `inconclusivo`, `inc`) e tambem
    rotulos derivados com sufixo, como `indeterminado (ampl)`.
    """
    return (
        n in _INDETERMINADO
        or n.startswith("indeterminado")
        or n.startswith("inconclusivo")
    )


def is_amp_status_indeterminante(amp_status: object) -> bool:
    """True quando o valor da coluna "Amp Status" indica falha de amplificacao.

    Reconhece `No Amp` e `Inconclusive` de forma case-insensitive. Valores
    ausentes/`Amp`/vazios retornam False.
    """
    if amp_status is None:
        return False
    return str(amp_status).strip().casefold() in _AMP_STATUS_INDETERMINADO


def reclassificar_alvo_por_amp_status(resultado_alvo: object, amp_status: object) -> str:
    """Reclassifica o resultado de um alvo conforme a coluna "Amp Status".

    Quando o Amp Status indica falha de amplificacao (`No Amp`/`Inconclusive`) e o
    alvo havia sido classificado como Detectavel ou Indeterminado, o resultado passa
    a ser ``RESULTADO_INDETERMINADO_AMPL``. Alvos Nao Detectaveis (ou qualquer outro
    valor) permanecem inalterados.
    """
    resultado = "" if resultado_alvo is None else str(resultado_alvo)
    if not is_amp_status_indeterminante(amp_status):
        return resultado
    n = _norm(resultado)
    if n in _DETECTAVEL or _eh_indeterminado(n):
        return RESULTADO_INDETERMINADO_AMPL
    return resultado


def is_amostra_vazia(valor: object) -> bool:
    """Define o que e um "poco vazio" em qualquer exame.

    Um poco e considerado vazio (e portanto Invalido) quando o codigo/anotacao
    da amostra:
      - esta em branco/ausente;
      - e apenas "X";
      - comeca com o texto "Vazio" (ex.: rotulo "Vazio_A1");
      - e um marcador textual de ausencia ("NAN"/"NONE").

    Regra de dominio unica reutilizada pelo pipeline de analise.
    """
    if valor is None:
        return True
    s = str(valor).strip()
    if s == "":
        return True
    up = s.upper()
    if up in ("X", "NAN", "NONE"):
        return True
    if up.startswith("VAZIO"):
        return True
    return False


def calcular_resultado_geral(
    rp_valido: bool,
    alvos: Dict[str, str],
    amostra_vazia: bool = False,
) -> str:
    """
    Calcula Resultado_geral com prioridade canônica.

    Args:
        rp_valido: True se o RP está dentro dos limites aceitáveis.
        alvos: {nome_alvo: resultado_string} — não incluir RP neste dict.
        amostra_vazia: True quando o poço está vazio (sem código, "X" ou
            iniciando com "Vazio"). Poço vazio é sempre Inválido.

    Returns:
        Uma das constantes RESULTADO_* ou "Detectável para <alvos>".
    """
    if amostra_vazia:
        return RESULTADO_INVALIDO

    if not rp_valido:
        return RESULTADO_INVALIDO

    detectaveis: list[str] = []
    has_indeterminado = False

    for nome, resultado in alvos.items():
        n = _norm(resultado)
        if _eh_indeterminado(n):
            has_indeterminado = True
        elif n in _DETECTAVEL:
            detectaveis.append(nome)

    if has_indeterminado:
        return RESULTADO_INDETERMINADO
    if detectaveis:
        return f"{RESULTADO_DETECTAVEL_PREFIXO} {', '.join(detectaveis)}"
    return RESULTADO_NAO_DETECTAVEL
