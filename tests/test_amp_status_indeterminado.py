# -*- coding: utf-8 -*-
"""Guardioes da regra "Indeterminado (ampl)" disparada pela coluna Amp Status.

Regra (confirmada com o usuario):
  - Apos a analise por Ct, todo alvo classificado como Detectavel ou Indeterminado
    cujo valor de "Amp Status" seja "No Amp" ou "Inconclusive" passa a ser
    Indeterminado, seguindo as regras de Indeterminado, com rotulo
    "Indeterminado (ampl)" na analise e "INDETERMINADO (AMPL)." nos mapas de placa.
  - Alvos Nao Detectaveis nao sofrem o gatilho.
  - Exames sem a coluna "Amp Status" mantem o comportamento anterior.
"""

import numpy as np
import pandas as pd

from domain.resultado_geral import (
    RESULTADO_INDETERMINADO,
    RESULTADO_INDETERMINADO_AMPL,
    RESULTADO_NAO_DETECTAVEL,
    calcular_resultado_geral,
    is_amp_status_indeterminante,
    reclassificar_alvo_por_amp_status,
)
from services.analysis.analysis_service import _apply_resultado_geral_vectorized
from utils.text_result_classifier import classify_result_text, result_text_to_gal_code


# ---------------------------------------------------------------------------
# Dominio: deteccao e reclassificacao
# ---------------------------------------------------------------------------

def test_is_amp_status_indeterminante_reconhece_valores_gatilho():
    assert is_amp_status_indeterminante("No Amp") is True
    assert is_amp_status_indeterminante("no amp") is True
    assert is_amp_status_indeterminante("Inconclusive") is True
    assert is_amp_status_indeterminante("INCONCLUSIVE") is True
    # Valores que NAO disparam
    assert is_amp_status_indeterminante("Amp") is False
    assert is_amp_status_indeterminante("") is False
    assert is_amp_status_indeterminante(None) is False


def test_reclassifica_detectavel_com_no_amp():
    assert reclassificar_alvo_por_amp_status("Detectável", "No Amp") == RESULTADO_INDETERMINADO_AMPL


def test_reclassifica_indeterminado_com_inconclusive():
    assert reclassificar_alvo_por_amp_status("Indeterminado", "Inconclusive") == RESULTADO_INDETERMINADO_AMPL


def test_nao_detectavel_nao_sofre_gatilho_mesmo_com_no_amp():
    assert reclassificar_alvo_por_amp_status("Não Detectável", "No Amp") == "Não Detectável"


def test_sem_amp_status_mantem_resultado_original():
    assert reclassificar_alvo_por_amp_status("Detectável", "Amp") == "Detectável"
    assert reclassificar_alvo_por_amp_status("Detectável", None) == "Detectável"


def test_rotulo_ampl_e_tratado_como_indeterminado_na_agregacao():
    alvos = {"SC2": RESULTADO_INDETERMINADO_AMPL}
    assert calcular_resultado_geral(rp_valido=True, alvos=alvos) == RESULTADO_INDETERMINADO


def test_rotulo_ampl_classifica_como_inc_para_gal():
    # Cor da tabela e codigo GAL dependem desta classificacao por substring.
    assert classify_result_text(RESULTADO_INDETERMINADO_AMPL) == "INC"
    assert result_text_to_gal_code(RESULTADO_INDETERMINADO_AMPL) == "3"


# ---------------------------------------------------------------------------
# Pipeline vetorizado: Resultado_geral reflete o rotulo ampl
# ---------------------------------------------------------------------------

def test_vectorized_resultado_geral_ampl():
    df = pd.DataFrame(
        [
            {
                "Selecionado": True,
                "Amostra": "101",
                "Res_RP_1": "Válido",
                "Res_RP_2": "Válido",
                "Res_SC2": RESULTADO_INDETERMINADO_AMPL,
            },
            {
                "Selecionado": True,
                "Amostra": "102",
                "Res_RP_1": "Válido",
                "Res_RP_2": "Válido",
                "Res_SC2": "Detectável",
            },
        ]
    )

    out = _apply_resultado_geral_vectorized(df, ["Res_SC2"])

    # Amostra 101: rotulo ampl deve aparecer no Resultado_geral e ser indeterminado.
    assert out.loc[0, "Resultado_geral"] == RESULTADO_INDETERMINADO_AMPL
    # Sugestao de repeticao SIM (regra de indeterminado).
    rep_col = [c for c in out.columns if c.lower().startswith("sugest")][0]
    assert str(out.loc[0, rep_col]).upper() == "SIM"
    # Amostra 102 segue Detectavel normal.
    assert str(out.loc[1, "Resultado_geral"]).startswith("Detectável")


def test_vectorized_sem_ampl_inalterado():
    df = pd.DataFrame(
        [
            {
                "Selecionado": True,
                "Amostra": "201",
                "Res_RP_1": "Válido",
                "Res_RP_2": "Válido",
                "Res_SC2": "Não Detectável",
            }
        ]
    )
    out = _apply_resultado_geral_vectorized(df, ["Res_SC2"])
    assert out.loc[0, "Resultado_geral"] == RESULTADO_NAO_DETECTAVEL


# ---------------------------------------------------------------------------
# Mapa de placa: rotulo "(ampl)"
# ---------------------------------------------------------------------------

def test_bloco_amostra_texto_ampl():
    from domain.mapa_placa_layout import (
        BlocoAmostra,
        CLASSIF_INDETERMINADO,
        classificar_amostra,
    )

    bloco = BlocoAmostra(
        codigo="101",
        alvos=(),
        classificacao=CLASSIF_INDETERMINADO,
        detectaveis=(),
        ampl=True,
    )
    assert bloco.texto_resultado == "INDETERMINADO (AMPL)."

    # Indeterminado sem ampl mantem o texto padrao.
    bloco_padrao = BlocoAmostra(
        codigo="102",
        alvos=(),
        classificacao=CLASSIF_INDETERMINADO,
        detectaveis=(),
    )
    assert bloco_padrao.texto_resultado == "INDETERMINADO."


def test_classificar_amostra_reconhece_ampl():
    from domain.mapa_placa_layout import CLASSIF_INDETERMINADO, classificar_amostra

    classif, _ = classificar_amostra({"SC2": RESULTADO_INDETERMINADO_AMPL}, rp_valido=True)
    assert classif == CLASSIF_INDETERMINADO


# ---------------------------------------------------------------------------
# Extrator: captura da coluna "Amp Status" por cabecalho
# ---------------------------------------------------------------------------

def test_extrator_localiza_amp_status_por_cabecalho():
    from services.equipment.equipment_extractors import _localizar_indice_amp_status

    assert _localizar_indice_amp_status(["Well", "Sample", "Target", "Cq", "Amp Status"]) == 4
    assert _localizar_indice_amp_status(["Well", "amp_status", "Ct"]) == 1
    assert _localizar_indice_amp_status(["Well", "Sample", "Ct"]) is None
