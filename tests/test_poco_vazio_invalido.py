"""Regra de dominio: poco vazio e sempre Invalido (todos os exames).

Poco vazio = codigo/anotacao da amostra em branco, apenas "X" ou iniciando com
"Vazio" (rotulo "Vazio_<poco>"). Ver domain.resultado_geral.is_amostra_vazia e
services.analysis.analysis_service._apply_resultado_geral_vectorized.
"""

import pytest

from domain.resultado_geral import (
    RESULTADO_INVALIDO,
    calcular_resultado_geral,
    is_amostra_vazia,
)


@pytest.mark.parametrize(
    "valor",
    ["", "   ", "X", "x", "Vazio_A1", "VAZIO", "vazio_h12", None, "NAN", "None"],
)
def test_is_amostra_vazia_detecta_vazios(valor):
    assert is_amostra_vazia(valor) is True


@pytest.mark.parametrize("valor", ["101", "422600698", "CN", "CP", "AX12", "1X"])
def test_is_amostra_vazia_ignora_validos(valor):
    assert is_amostra_vazia(valor) is False


def test_calcular_resultado_geral_vazio_sobrepoe_tudo():
    # Mesmo com RP valido e alvo detectavel, poco vazio -> Invalido.
    res = calcular_resultado_geral(
        rp_valido=True,
        alvos={"SC2": "Detectável"},
        amostra_vazia=True,
    )
    assert res == RESULTADO_INVALIDO


def test_vectorized_poco_vazio_vira_invalido_e_desmarcado():
    pd = pytest.importorskip("pandas")
    from services.analysis.analysis_service import _apply_resultado_geral_vectorized

    df = pd.DataFrame(
        [
            {"Selecionado": True, "Amostra": "101", "Res_RP_1": "Válido", "Res_RP_2": "Válido", "Res_SC2": "Detectável"},
            {"Selecionado": True, "Amostra": "Vazio_B1", "Res_RP_1": "Válido", "Res_RP_2": "Válido", "Res_SC2": "Detectável"},
            {"Selecionado": True, "Amostra": "X", "Res_RP_1": "Válido", "Res_RP_2": "Válido", "Res_SC2": ""},
        ]
    )

    out = _apply_resultado_geral_vectorized(df, ["Res_SC2"])

    # Amostra valida segue o fluxo normal.
    assert out.loc[0, "Resultado_geral"].startswith("Detectável")
    assert bool(out.loc[0, "Selecionado"]) is True

    # Pocos vazios -> Invalido e desmarcados, mesmo com RP valido e alvo detectavel.
    assert out.loc[1, "Resultado_geral"] == RESULTADO_INVALIDO
    assert bool(out.loc[1, "Selecionado"]) is False
    assert out.loc[2, "Resultado_geral"] == RESULTADO_INVALIDO
    assert bool(out.loc[2, "Selecionado"]) is False
