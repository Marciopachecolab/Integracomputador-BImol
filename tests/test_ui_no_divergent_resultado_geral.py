# -*- coding: utf-8 -*-
"""Guardiao: a UI nao implementa prioridade propria de Resultado_geral (FINDING-003).

A regra canonica de prioridade vive em `domain.resultado_geral`
(Invalido > Indeterminado > Detectavel > Nao Detectavel). A UI deve delegar a
ela, nunca replicar a logica clinica. O metodo morto `_calcular_geral_fallback`
em `ui/janela_analise_completa.py` invertia essa prioridade (Detectavel antes de
Invalido) e foi removido. Este guardiao impede sua reintroducao.

A verificacao e feita por AST sobre o codigo-fonte (sem importar a UI/Tk),
mantendo o teste leve e independente de ambiente grafico.
"""

import ast
import io
from pathlib import Path

ARQ = Path(__file__).resolve().parents[1] / "ui" / "janela_analise_completa.py"


def _funcoes_definidas(src: str):
    tree = ast.parse(src)
    return {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}


def test_fallback_divergente_removido():
    src = io.open(ARQ, encoding="utf-8").read()
    assert "_calcular_geral_fallback" not in _funcoes_definidas(src), (
        "Metodo morto com prioridade clinica divergente nao deve ser reintroduzido; "
        "delegue a domain.resultado_geral.calcular_resultado_geral."
    )


def test_ui_delega_ao_dominio():
    src = io.open(ARQ, encoding="utf-8").read()
    assert "calcular_resultado_geral" in src, (
        "A UI deve delegar o calculo de Resultado_geral ao dominio canonico."
    )
