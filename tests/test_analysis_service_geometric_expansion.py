import pytest
import pandas as pd
from services.analysis.analysis_service import AnalysisService

def test_expand_gabarito_vr1e2_geometric_anomaly_a2():
    """
    Testa se o poco de extracao A2 expande para A3 e A4 no group_size 2
    ao inves do comportamento incorreto A2 e A3.
    Prova a preservacao de CN (G6 -> G11, G12) e CP (H6 -> H11, H12).
    """
    df_gabarito = pd.DataFrame([
        {"Amostra": "Paciente_1", "Poco": "A1"},
        {"Amostra": "Paciente_2", "Poco": "A2"},
        {"Amostra": "CN", "Poco": "G6"},
        {"Amostra": "CP", "Poco": "H6"}
    ])
    
    # Chama o metodo problematico
    df_expandido = AnalysisService._expand_gabarito_by_group_size(
        gabarito=df_gabarito,
        well_column="Poco",
        group_size=2
    )
    
    # Validar Paciente 2 (A2) -> Analise A3, A4
    paciente_2_pocos = df_expandido[df_expandido["Amostra"] == "Paciente_2"]["Poco"].tolist()
    assert paciente_2_pocos == ["A3", "A4"], f"Falha A2. Encontrado: {paciente_2_pocos}"

    # Validar CN (G6) -> Analise G11, G12
    cn_pocos = df_expandido[df_expandido["Amostra"] == "CN"]["Poco"].tolist()
    assert cn_pocos == ["G11", "G12"], f"Falha CN G6. Encontrado: {cn_pocos}"

    # Validar CP (H6) -> Analise H11, H12
    cp_pocos = df_expandido[df_expandido["Amostra"] == "CP"]["Poco"].tolist()
    assert cp_pocos == ["H11", "H12"], f"Falha CP H6. Encontrado: {cp_pocos}"
    
    assert len(df_expandido) == 8
