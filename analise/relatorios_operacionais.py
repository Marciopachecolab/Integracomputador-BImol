
"""
Módulo de relatórios operacionais de corrida / rotina.

Este módulo gera quatro tipos de relatórios a partir de um DataFrame
de resultados consolidados (por exemplo, o df_final do motor de análise):

1) Relatório de Corrida Analítica (Run Summary)
2) Relatório de Mapa de Placa
3) Relatório de Amostras da Corrida
4) Relatório de Erros e Inconsistências

O módulo NÃO faz suposições rígidas sobre os nomes das colunas.
Em vez disso, utiliza uma configuração explícita de colunas (ColumnConfig),
que deve ser preenchida de acordo com a estrutura do df_final.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class ColumnConfig:
    """Mapeia as colunas do df_final usadas pelos relatórios.

    Todos os campos devem apontar para colunas existentes no DataFrame
    de resultados consolidados produzido pelos motores de análise.
    """

    # Obrigatórios para todos os relatórios
    run_id: str
    plate_id: str
    equipment: str
    kit: str
    run_datetime: str
    sample_type: str
    result: str
    sample_id: str
    ct: str
    well: str

    # Opcionais (usados quando existirem no df)
    patient: Optional[str] = None
    exam: Optional[str] = None
    observations: Optional[str] = None


def _get_unique_value(df: pd.DataFrame, column: str) -> Optional[str]:
    """Retorna um único valor não nulo de uma coluna, se existir.

    Caso a coluna não exista no DataFrame ou não haja valores não nulos,
    retorna None.
    """
    if column not in df.columns:
        return None
    serie = df[column].dropna().astype(str).str.strip()
    if serie.empty:
        return None
    # Usa o primeiro valor não vazio
    return serie.iloc[0]


def gerar_relatorio_corrida_analitica(
    df_final: pd.DataFrame,
    cols: ColumnConfig,
) -> pd.DataFrame:
    """Gera o Relatório de Corrida Analítica (Run Summary).

    Uma linha por corrida (assumindo que df_final contenha apenas uma corrida).

    Campos gerados:
      - id_corrida
      - id_placa
      - equipamento
      - kit
      - data_hora_processamento
      - total_amostras
      - total_controles
      - total_brancos
      - total_positivos
      - total_negativos
      - total_inconclusivos
      - total_invalidos
    """
    if df_final.empty:
        # Retorna DataFrame com uma linha vazia e contagens zeradas,
        # para simplificar tratamento na UI.
        return pd.DataFrame(
            [
                {
                    "id_corrida": None,
                    "id_placa": None,
                    "equipamento": None,
                    "kit": None,
                    "data_hora_processamento": None,
                    "total_amostras": 0,
                    "total_controles": 0,
                    "total_brancos": 0,
                    "total_positivos": 0,
                    "total_negativos": 0,
                    "total_inconclusivos": 0,
                    "total_invalidos": 0,
                }
            ]
        )

    # Metadados da corrida
    id_corrida = _get_unique_value(df_final, cols.run_id)
    id_placa = _get_unique_value(df_final, cols.plate_id)
    equipamento = _get_unique_value(df_final, cols.equipment)
    kit = _get_unique_value(df_final, cols.kit)
    data_hora = _get_unique_value(df_final, cols.run_datetime)

    # Cópia de trabalho
    df = df_final.copy()

    # Tipo de poço: amostra / controle / branco
    tipo = df[cols.sample_type].astype(str).str.strip().str.lower()

    total_amostras = (tipo == "amostra").sum()
    total_controles = (tipo == "controle").sum()
    total_brancos = (tipo == "branco").sum()

    # Resultado interpretado
    resultado = df[cols.result].astype(str).str.strip().str.lower()

    total_positivos = (resultado == "positivo").sum()
    total_negativos = (resultado == "negativo").sum()
    total_inconclusivos = (resultado == "inconclusivo").sum()
    total_invalidos = (resultado == "inválido").sum() + (resultado == "invalido").sum()

    resumo = {
        "id_corrida": id_corrida,
        "id_placa": id_placa,
        "equipamento": equipamento,
        "kit": kit,
        "data_hora_processamento": data_hora,
        "total_amostras": int(total_amostras),
        "total_controles": int(total_controles),
        "total_brancos": int(total_brancos),
        "total_positivos": int(total_positivos),
        "total_negativos": int(total_negativos),
        "total_inconclusivos": int(total_inconclusivos),
        "total_invalidos": int(total_invalidos),
    }

    return pd.DataFrame([resumo])


def gerar_relatorio_mapa_placa(
    df_final: pd.DataFrame,
    cols: ColumnConfig,
) -> pd.DataFrame:
    """Gera o Relatório de Mapa de Placa.

    Uma linha por poço, com as informações:
      - poço
      - id_amostra
      - tipo_amostra (amostra/controle/branco)
      - resultado_interpretado
      - ct_principal

    O DataFrame retornado pode ser usado diretamente para:
      - visualização em grade na UI
      - exportação para Excel
      - geração de PDF/PNG (em outro módulo)
    """
    if df_final.empty:
        return pd.DataFrame(
            columns=[
                "poço",
                "id_amostra",
                "tipo_amostra",
                "resultado_interpretado",
                "ct_principal",
            ]
        )

    df = df_final.copy()

    df_mapa = pd.DataFrame(
        {
            "poço": df[cols.well],
            "id_amostra": df[cols.sample_id],
            "tipo_amostra": df[cols.sample_type],
            "resultado_interpretado": df[cols.result],
            "ct_principal": df[cols.ct],
        }
    )

    # Ordena pelo poço para facilitar visualização (A1, A2, B1, ...)
    df_mapa = df_mapa.sort_values(by="poço", kind="stable")

    return df_mapa.reset_index(drop=True)


def gerar_relatorio_amostras_corrida(
    df_final: pd.DataFrame,
    cols: ColumnConfig,
) -> pd.DataFrame:
    """Gera o Relatório de Amostras da Corrida (lista linear).

    Uma linha por amostra (ou por poço, dependendo do df_final),
    com as colunas:

      - id_amostra
      - paciente (quando houver, se mapeado em cols.patient)
      - exame (quando houver, se mapeado em cols.exam)
      - ct_principal
      - resultado_interpretado
      - observacoes (quando houver, se mapeado em cols.observations)

    Este relatório é útil para:
      - conferência manual
      - exportação para planilhas
      - conferência com dados do GAL
    """
    if df_final.empty:
        return pd.DataFrame(
            columns=[
                "id_amostra",
                "paciente",
                "exame",
                "ct_principal",
                "resultado_interpretado",
                "observacoes",
            ]
        )

    df = df_final.copy()

    rel_cols = {
        "id_amostra": df[cols.sample_id],
        "ct_principal": df[cols.ct],
        "resultado_interpretado": df[cols.result],
    }

    # Campos opcionais
    if cols.patient and cols.patient in df.columns:
        rel_cols["paciente"] = df[cols.patient]
    else:
        rel_cols["paciente"] = None

    if cols.exam and cols.exam in df.columns:
        rel_cols["exame"] = df[cols.exam]
    else:
        rel_cols["exame"] = None

    if cols.observations and cols.observations in df.columns:
        rel_cols["observacoes"] = df[cols.observations]
    else:
        rel_cols["observacoes"] = None

    rel = pd.DataFrame(rel_cols)

    # Ordenação simples por id_amostra (quando possível)
    if rel["id_amostra"].notna().any():
        rel = rel.sort_values(by="id_amostra", kind="stable")

    return rel.reset_index(drop=True)


def gerar_relatorio_erros_inconsistencias(
    df_final: pd.DataFrame,
    cols: ColumnConfig,
    ct_min: Optional[float] = None,
    ct_max: Optional[float] = None,
) -> pd.DataFrame:
    """Gera o Relatório de Erros e Inconsistências da corrida.

    Lista problemas detectados na corrida, com foco em:

      - Amostra sem resultado.
      - Poço com Ct fora de faixa esperada (quando ct_min/ct_max forem fornecidos).
      - Controles com comportamento potencialmente inadequado
        (controle sem resultado OU com Ct fora de faixa, quando definida).

    Colunas do relatório:

      - poço
      - id_amostra
      - tipo_amostra
      - ct_principal
      - resultado_interpretado
      - motivos_erro  (texto descrevendo os problemas encontrados)
    """
    if df_final.empty:
        return pd.DataFrame(
            columns=[
                "poço",
                "id_amostra",
                "tipo_amostra",
                "ct_principal",
                "resultado_interpretado",
                "motivos_erro",
            ]
        )

    df = df_final.copy()

    # Normalizações básicas
    tipo = df[cols.sample_type].astype(str).str.strip().str.lower()
    resultado = df[cols.result].astype(str).str.strip()
    ct_series = pd.to_numeric(df[cols.ct], errors="coerce")

    # 1) Amostra/poço sem resultado (vazio ou NaN)
    sem_resultado_mask = resultado.eq("") | resultado.isna()

    # 2) Ct fora de faixa (apenas se limites forem fornecidos)
    ct_fora_faixa_mask = pd.Series(False, index=df.index)
    if ct_min is not None:
        ct_fora_faixa_mask |= ct_series < ct_min
    if ct_max is not None:
        ct_fora_faixa_mask |= ct_series > ct_max

    # 3) Controles inadequados:
    #    aqui consideramos "controle" qualquer linha com tipo_amostra == "controle".
    #    Consideramos inadequado se:
    #      - não tem resultado, OU
    #      - Ct está fora de faixa (quando faixa foi definida).
    controle_mask = tipo == "controle"
    controle_inadequado_mask = controle_mask & (sem_resultado_mask | ct_fora_faixa_mask)

    # Combina todas as condições para identificar linhas problemáticas
    problemas_mask = sem_resultado_mask | ct_fora_faixa_mask | controle_inadequado_mask

    if not problemas_mask.any():
        return pd.DataFrame(
            columns=[
                "poço",
                "id_amostra",
                "tipo_amostra",
                "ct_principal",
                "resultado_interpretado",
                "motivos_erro",
            ]
        )

    problemas = df.loc[problemas_mask].copy()

    motivos = []
    for idx, _row in problemas.iterrows():
        motivo_list = []

        if sem_resultado_mask.loc[idx]:
            motivo_list.append("Amostra/poço sem resultado interpretado.")

        if (ct_min is not None or ct_max is not None) and ct_fora_faixa_mask.loc[idx]:
            if ct_series.loc[idx] is not None and not pd.isna(ct_series.loc[idx]):
                motivo_list.append(
                    f"Ct fora da faixa definida (valor atual: {ct_series.loc[idx]!r})."
                )
            else:
                motivo_list.append("Ct ausente ou inválido em contexto com faixa definida.")

        if controle_inadequado_mask.loc[idx]:
            motivo_list.append("Controle com comportamento potencialmente inadequado.")

        motivos.append(" ".join(motivo_list))

    problemas_rel = pd.DataFrame(
        {
            "poço": problemas[cols.well],
            "id_amostra": problemas[cols.sample_id],
            "tipo_amostra": problemas[cols.sample_type],
            "ct_principal": problemas[cols.ct],
            "resultado_interpretado": problemas[cols.result],
            "motivos_erro": motivos,
        }
    )

    # Ordena por poço para facilitar conferência
    problemas_rel = problemas_rel.sort_values(by="poço", kind="stable")

    return problemas_rel.reset_index(drop=True)
