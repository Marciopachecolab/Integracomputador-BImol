# -*- coding: utf-8 -*-
"""
Layout puro do Mapa de Placa definitivo (impressao P&B, arquivamento).

Regras canonicas:
  - 8 linhas de blocos sempre; blocos por linha = 12 / pocos_por_amostra
  - Grid interno de alvos: 3 colunas, fill column-major
  - Classificacao consolidada por amostra com prioridade:
      Invalido > Indeterminado > Detectavel > Nao Detectavel
  - Em caso de mistura (Detectavel + Indeterminado), o resultado e Indeterminado

Esta camada nao depende de UI, openpyxl, pandas ou reportlab.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

GRID_COLS = 3
PLATE_ROWS = 8

CLASSIF_DETECTAVEL = "DETECTAVEL"
CLASSIF_NAO_DETECTAVEL = "NAO_DETECTAVEL"
CLASSIF_INDETERMINADO = "INDETERMINADO"
CLASSIF_INVALIDO = "INVALIDO"

_DETECTAVEL_TOKENS = {"detectavel", "detectado", "detectável"}
_INDETERMINADO_TOKENS = {"indeterminado", "inconclusivo", "inc", "ind"}
_INVALIDO_TOKENS = {"invalido", "inválido"}


def _norm(s: object) -> str:
    val = s.value if hasattr(s, "value") else s
    return str(val or "").strip().casefold()


def formatar_ct(ct: object) -> str:
    """Formata CT com 2 casas decimais e virgula, ou string vazia se nao detectado."""
    if ct is None:
        return ""
    if isinstance(ct, str):
        s = ct.strip()
        if not s:
            return ""
        try:
            valor = float(s.replace(",", "."))
        except ValueError:
            return s
    else:
        try:
            valor = float(ct)
        except (TypeError, ValueError):
            return ""
    try:
        import math
        if math.isnan(valor):
            return ""
    except Exception:
        pass
    return f"{valor:.2f}".replace(".", ",")


@dataclass(frozen=True)
class AlvoCelula:
    """Um par alvo/CT que ocupa uma celula do grid 3xN interno."""

    nome: str
    ct_formatado: str  # string vazia quando ND


@dataclass(frozen=True)
class BlocoAmostra:
    """Bloco completo de uma amostra no mapa."""

    codigo: str
    alvos: Tuple[AlvoCelula, ...]
    classificacao: str  # CLASSIF_*
    detectaveis: Tuple[str, ...]  # alvos detectaveis (para texto "DETECTAVEL PARA X, Y")
    poco_label: str = ""  # ex: "A1+A2+A3" — opcional, util para rodape
    ampl: bool = False  # indeterminado derivado da coluna "Amp Status" (No Amp/Inconclusive)

    @property
    def texto_resultado(self) -> str:
        if self.classificacao == CLASSIF_DETECTAVEL:
            if self.detectaveis:
                return f"DETECTAVEL PARA {', '.join(self.detectaveis)}."
            return "DETECTAVEL."
        if self.classificacao == CLASSIF_NAO_DETECTAVEL:
            return "NAO DETECTAVEL."
        if self.classificacao == CLASSIF_INDETERMINADO:
            if self.ampl:
                return "INDETERMINADO (AMPL)."
            return "INDETERMINADO."
        if self.classificacao == CLASSIF_INVALIDO:
            return "INVALIDO."
        return ""


@dataclass(frozen=True)
class ControleQuadro:
    """Linha do quadro de controles do rodape."""

    nome: str  # ex: "CN", "CP"
    alvo: str  # ex: "ZK"
    ct_formatado: str
    valido: bool


@dataclass(frozen=True)
class MapaPlaca:
    """Resultado final do layout pronto para o exporter."""

    nome_exame: str
    nome_placa: str
    placa_ok: bool
    blocos_por_linha: int
    linhas_blocos: int  # sempre 8
    blocos: Tuple[Tuple[Optional[BlocoAmostra], ...], ...]  # blocos[linha][coluna]
    controles: Tuple[ControleQuadro, ...]


def calcular_blocos_por_linha(pocos_por_amostra: int) -> int:
    """12 / pocos_por_amostra (com clamp)."""
    if pocos_por_amostra <= 0:
        return 12
    return max(1, 12 // pocos_por_amostra)


def distribuir_alvos_grid(alvos: Sequence[AlvoCelula]) -> Tuple[AlvoCelula, ...]:
    """
    Distribui alvos no grid 3 colunas column-major.

    Ex: 3 alvos -> coluna 1 cheia
        4 alvos -> coluna 1 cheia + primeira linha da col 2
        9 alvos -> 3 colunas cheias

    Retorna a tupla na ordem de leitura por linhas (linha1col1, linha1col2, linha1col3, linha2col1...).
    """
    if not alvos:
        return ()
    n = len(alvos)
    # 3 linhas minimo (col 1 cheia antes de ir pra col 2); cresce se >9 alvos
    linhas = max(3, (n + GRID_COLS - 1) // GRID_COLS)
    grid: List[List[Optional[AlvoCelula]]] = [
        [None for _ in range(GRID_COLS)] for _ in range(linhas)
    ]
    # column-major fill
    idx = 0
    for col in range(GRID_COLS):
        for row in range(linhas):
            if idx >= n:
                break
            grid[row][col] = alvos[idx]
            idx += 1
        if idx >= n:
            break
    # achatar em row-major (ordem de leitura)
    flat: List[AlvoCelula] = []
    for row in grid:
        for cell in row:
            if cell is not None:
                flat.append(cell)
            else:
                flat.append(AlvoCelula(nome="", ct_formatado=""))
    return tuple(flat)


def classificar_amostra(
    resultados_por_alvo: Dict[str, str],
    rp_valido: bool,
) -> Tuple[str, Tuple[str, ...]]:
    """
    Aplica a regra canonica de classificacao consolidada.

    Mistura Detectavel + Indeterminado -> INDETERMINADO (regra explicita do usuario).

    Returns:
        (classificacao, alvos_detectaveis)
    """
    if not rp_valido:
        return CLASSIF_INVALIDO, ()
    detectaveis: List[str] = []
    has_inderterm = False
    for alvo, resultado in resultados_por_alvo.items():
        norm = _norm(resultado)
        if (
            norm in _INDETERMINADO_TOKENS
            or norm.startswith("indeterminado")
            or norm.startswith("inconclusivo")
        ):
            has_inderterm = True
        elif norm in _DETECTAVEL_TOKENS:
            detectaveis.append(alvo)
    if has_inderterm:
        return CLASSIF_INDETERMINADO, ()
    if detectaveis:
        return CLASSIF_DETECTAVEL, tuple(detectaveis)
    return CLASSIF_NAO_DETECTAVEL, ()


def calcular_placa_ok(controles: Sequence[ControleQuadro]) -> bool:
    """Placa OK se todos os controles forem validos."""
    if not controles:
        return False
    return all(c.valido for c in controles)


def montar_mapa(
    nome_exame: str,
    nome_placa: str,
    pocos_por_amostra: int,
    blocos_lineares: Sequence[BlocoAmostra],
    controles: Sequence[ControleQuadro],
) -> MapaPlaca:
    """
    Monta o grid 8 linhas × N blocos-por-linha a partir de uma lista linear de blocos.

    Se vierem mais blocos do que cabem (8 × blocos_por_linha), os excedentes sao truncados.
    Se vierem menos, completa com None.
    """
    blocos_por_linha = calcular_blocos_por_linha(pocos_por_amostra)
    total_slots = PLATE_ROWS * blocos_por_linha
    blocos_seq = list(blocos_lineares[:total_slots])
    while len(blocos_seq) < total_slots:
        blocos_seq.append(None)  # type: ignore[arg-type]
    grade: List[Tuple[Optional[BlocoAmostra], ...]] = []
    for linha in range(PLATE_ROWS):
        ini = linha * blocos_por_linha
        fim = ini + blocos_por_linha
        grade.append(tuple(blocos_seq[ini:fim]))
    return MapaPlaca(
        nome_exame=nome_exame,
        nome_placa=nome_placa,
        placa_ok=calcular_placa_ok(controles),
        blocos_por_linha=blocos_por_linha,
        linhas_blocos=PLATE_ROWS,
        blocos=tuple(grade),
        controles=tuple(controles),
    )
