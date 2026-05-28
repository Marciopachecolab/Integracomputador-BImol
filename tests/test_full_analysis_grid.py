# -*- coding: utf-8 -*-
"""
tests/test_full_analysis_grid.py

Testes unitários do FullAnalysisGrid.
Valida: construção de colunas dinâmicas, identificação de controles,
formatação de CT, determinação de tags de cor e estado de seleção.
NÃO abre janela gráfica — testa apenas a lógica pura do componente.
"""

import math
import pytest
import pandas as pd


# Importa apenas os helpers puros (sem instanciar widget Tk)
from ui.components.full_analysis_grid import (
    _is_control,
    _result_tag,
    _fmt_ct,
    _fmt_cell,
    _FIXED_BEFORE,
    _FIXED_AFTER,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _row(**kwargs) -> pd.Series:
    defaults = {
        "Selecionado": True,
        "Amostra": "420000089",
        "Poco": "A1",
        "Resultado_geral": "Nao Detectavel",
        "Status_Placa": "Valida",
        "Codigo": "420000089",
    }
    defaults.update(kwargs)
    return pd.Series(defaults)


# ---------------------------------------------------------------------------
# _is_control
# ---------------------------------------------------------------------------

class TestIsControl:
    def test_cn_detectado_como_controle(self):
        row = _row(Amostra="CN")
        assert _is_control(row) is True

    def test_cp_detectado_como_controle(self):
        row = _row(Amostra="CP")
        assert _is_control(row) is True

    def test_amostra_normal_nao_e_controle(self):
        row = _row(Amostra="420000089")
        assert _is_control(row) is False

    def test_neg_e_pos_sao_controles(self):
        assert _is_control(_row(Amostra="NEG")) is True
        assert _is_control(_row(Amostra="POS")) is True

    def test_case_insensitive(self):
        assert _is_control(_row(Amostra="cn")) is True
        assert _is_control(_row(Amostra="Cp")) is True


# ---------------------------------------------------------------------------
# _result_tag
# ---------------------------------------------------------------------------

class TestResultTag:
    def test_controle_tem_tag_controle(self):
        row = _row(Amostra="CN", Resultado_geral="Detectavel")
        assert _result_tag(row) == "controle"

    def test_detectavel(self):
        row = _row(Resultado_geral="Detectavel")
        assert _result_tag(row) == "detectavel"

    def test_nao_detectavel(self):
        row = _row(Resultado_geral="Nao Detectavel")
        assert _result_tag(row) == "nao_detectavel"

    def test_indeterminado(self):
        row = _row(Resultado_geral="Indeterminado")
        assert _result_tag(row) == "indeterminado"

    def test_invalido(self):
        row = _row(Resultado_geral="Invalido")
        assert _result_tag(row) == "invalido"

    def test_inconclusivo_e_indeterminado(self):
        row = _row(Resultado_geral="Inconclusivo")
        assert _result_tag(row) == "indeterminado"


# ---------------------------------------------------------------------------
# _fmt_ct
# ---------------------------------------------------------------------------

class TestFmtCt:
    def test_float_arredondado(self):
        assert _fmt_ct(24.376) == "24.38"

    def test_nan_retorna_vazio(self):
        assert _fmt_ct(float("nan")) == ""

    def test_none_retorna_vazio(self):
        assert _fmt_ct(None) == ""

    def test_string_numerica(self):
        assert _fmt_ct("35.5") == "35.50"

    def test_string_nao_numerica(self):
        assert _fmt_ct("Nao detect.") == "Nao detect."


# ---------------------------------------------------------------------------
# _fmt_cell
# ---------------------------------------------------------------------------

class TestFmtCell:
    def test_ct_col_formata_float(self):
        assert _fmt_cell("CT_SC2", 25.47) == "25.47"

    def test_res_col_retorna_string(self):
        assert _fmt_cell("Res_SC2", "Nao Detectavel") == "Nao Detectavel"

    def test_nan_retorna_vazio(self):
        assert _fmt_cell("Res_ADV", float("nan")) == ""

    def test_none_retorna_vazio(self):
        assert _fmt_cell("Resultado_geral", None) == ""

    def test_string_longa_truncada(self):
        longa = "A" * 30
        resultado = _fmt_cell("Resultado_geral", longa)
        assert len(resultado) <= 23  # 21 chars + "…"
        assert resultado.endswith("…")


# ---------------------------------------------------------------------------
# Constantes de ordem
# ---------------------------------------------------------------------------

class TestColumnConstants:
    def test_fixed_before_tem_selecionado_primeiro(self):
        assert _FIXED_BEFORE[0] == "Selecionado"

    def test_fixed_after_tem_resultado_geral(self):
        assert "Resultado_geral" in _FIXED_AFTER

    def test_fixed_after_tem_codigo(self):
        assert "Codigo" in _FIXED_AFTER
