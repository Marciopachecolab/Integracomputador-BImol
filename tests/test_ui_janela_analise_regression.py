import pytest
import pandas as pd
from ui.janela_analise_completa import _determinar_tag_resultado, _is_controle_operacional

def test_is_controle_operacional():
    """
    Testes de regressão (Golden Master) para a heurística de controles.
    Garante que a lógica atual de identificação de CN/CP funcione perfeitamente
    antes de refatorarmos para ViewModels.
    """
    # Cenários Positivos (Devem ser controles)
    assert _is_controle_operacional(pd.Series({"Amostra": "CN", "Codigo": "123"})) is True
    assert _is_controle_operacional(pd.Series({"Amostra": "Amostra1", "Codigo": "CP"})) is True
    assert _is_controle_operacional(pd.Series({"Amostra": "cn_algo", "Codigo": "algo"})) is True
    assert _is_controle_operacional(pd.Series({"Amostra": "controle_negativo", "Codigo": "123"})) is True
    assert _is_controle_operacional(pd.Series({"Amostra": "123", "Codigo": "ControlePositivo"})) is True
    assert _is_controle_operacional(pd.Series({"Amostra": "CN", "Codigo": "CN"})) is True

    # Cenários Negativos (Não devem ser controles)
    assert _is_controle_operacional(pd.Series({"Amostra": "Paciente1", "Codigo": "PAC01"})) is False
    assert _is_controle_operacional(pd.Series({"Amostra": "C", "Codigo": "P"})) is False
    assert _is_controle_operacional(pd.Series({"Amostra": "", "Codigo": ""})) is False
    assert _is_controle_operacional(pd.Series({"OutraColuna": "CN"})) is False


def test_determinar_tag_resultado():
    """
    Testes de regressão (Golden Master) para a classificação visual de resultados.
    Garante que a UI continue aplicando a cor correta baseada no DataFrame legado.
    """
    # 1. Baseado na coluna primária "Resultado_geral" (Regra forte do Domínio)
    assert _determinar_tag_resultado(pd.Series({"Resultado_geral": "Detectável"})) == "detectado"
    assert _determinar_tag_resultado(pd.Series({"Resultado_geral": "Não Detectável"})) == "nao_detectavel"
    assert _determinar_tag_resultado(pd.Series({"Resultado_geral": "Inconclusivo"})) == "indeterminado"
    assert _determinar_tag_resultado(pd.Series({"Resultado_geral": "Inválido"})) == "invalido"

    # 2. Testando a hierarquia de prioridade (Fallback individual das colunas Res_)
    # Ordem de prioridade legada: INV > INC > DET > ND
    
    # Se houver um Inválido perdido, o status final visual vira inválido
    row_inv = pd.Series({
        "Res_Alvo1": "Detectável",
        "Resultado_Alvo2": "Inválido",
        "Res_Alvo3": "Não Detectável"
    })
    assert _determinar_tag_resultado(row_inv) == "invalido"

    # Se houver um Inconclusivo (sem Invalido)
    row_inc = pd.Series({
        "Res_Alvo1": "Detectável",
        "Resultado_Alvo2": "Inconclusivo",
        "Res_Alvo3": "Não Detectável"
    })
    assert _determinar_tag_resultado(row_inc) == "indeterminado"

    # Se houver um Detectável (sem Invalido e sem Inconclusivo)
    row_det = pd.Series({
        "Res_Alvo1": "Não Detectável",
        "Resultado_Alvo2": "Detectável",
        "Res_Alvo3": "Não Detectável"
    })
    assert _determinar_tag_resultado(row_det) == "detectado"

    # Apenas ND
    row_nd = pd.Series({
        "Res_Alvo1": "Não Detectável",
        "Resultado_Alvo2": "Não Detectável",
    })
    assert _determinar_tag_resultado(row_nd) == "nao_detectavel"

    # Testando com Mojibakes de acentuação se aplicável no classifier
    assert _determinar_tag_resultado(pd.Series({"Resultado_geral": "DetectÃ¡vel"})) == "detectado"

    # Se nenhuma regra casar, o fallback da UI é nao_detectavel
    assert _determinar_tag_resultado(pd.Series({"Coluna_Aleatoria": "Lixo"})) == "nao_detectavel"
