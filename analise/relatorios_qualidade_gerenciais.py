


"""


Módulo de relatórios de Qualidade (CQI/CQE) e Relatórios Gerenciais/Produtividade.





Este módulo consolida funções de relatório que operam exclusivamente sobre


pandas.DataFrame e podem ser chamadas a partir de serviços da aplicação


(ex.: QualityService, ReportingService, AnalysisService).





Grupos de relatórios:





3. Relatórios de Qualidade (CQI / CQE / indicadores técnicos)


   - gerar_relatorio_controles_internos_corrida


   - gerar_relatorio_indicadores_qualidade_periodo


   - gerar_relatorio_nc_relacionadas_corrida





4. Relatórios gerenciais e de produtividade


   - gerar_relatorio_producao_periodo


   - gerar_relatorio_positividade_exame_periodo


   - gerar_relatorio_produtividade_equipamento


   - gerar_relatorio_tempo_processamento


"""





from __future__ import annotations





from dataclasses import dataclass


from typing import Dict, List, Optional, Tuple





import pandas as pd








# ============================================================================


# 3. RELATÓRIOS DE QUALIDADE (CQI / CQE / INDICADORES TÉCNICOS)


# ============================================================================








@dataclass


class QualidadeColumnConfig:


    """Colunas necessárias para relatórios de qualidade.





    Parâmetros


    ----------


    run_id       : identificador da corrida


    exam         : exame realizado


    equipment    : equipamento utilizado


    sample_type  : tipo de amostra (amostra/controle/branco)


    control_type : tipo de controle (ex.: 'controle positivo',


                   'controle negativo', 'controle interno', etc.)


    result       : resultado interpretado


    ct           : Ct principal


    retest_flag  : flag indicando se é um reteste (opcional)


    """





    run_id: str


    exam: str


    equipment: str


    sample_type: str


    control_type: Optional[str]


    result: str


    ct: str


    retest_flag: Optional[str] = None








def gerar_relatorio_controles_internos_corrida(


    df_final: pd.DataFrame,


    cols: QualidadeColumnConfig,


    faixas_aceitabilidade: Optional[


        Dict[str, Tuple[Optional[float], Optional[float]]]


    ] = None,


) -> pd.DataFrame:


    """Relatório de Controles Internos por Corrida.





    Para uma corrida (df_final de uma corrida), calcula, por tipo de controle:





      - n_pocos            : número de poços


      - ct_medio           : Ct médio


      - ct_min             : Ct mínimo


      - ct_max             : Ct máximo


      - ct_desvio_padrao   : desvio padrão de Ct


      - faixa_aceitabilidade (texto)


      - situacao           : 'Dentro da faixa', 'Fora da faixa' ou 'Sem faixa definida'





    faixas_aceitabilidade:


      dict opcional: tipo_controle -> (ct_min, ct_max)


      Ex.: {"controle positivo": (25.0, 30.0)}


    """


    if df_final.empty:


        return pd.DataFrame(


            columns=[


                "id_corrida",


                "tipo_controle",


                "n_pocos",


                "ct_medio",


                "ct_min",


                "ct_max",


                "ct_desvio_padrao",


                "faixa_aceitabilidade",


                "situacao",


            ]


        )





    df = df_final.copy()





    # Filtra apenas controles (tipo_amostra == 'controle')


    tipo_amostra = df[cols.sample_type].astype(str).str.strip().str.lower()


    df_controles = df.loc[tipo_amostra == "controle"].copy()





    if df_controles.empty:


        return pd.DataFrame(


            columns=[


                "id_corrida",


                "tipo_controle",


                "n_pocos",


                "ct_medio",


                "ct_min",


                "ct_max",


                "ct_desvio_padrao",


                "faixa_aceitabilidade",


                "situacao",


            ]


        )





    # ID da corrida (assume-se único na corrida)


    run_id_val = None


    if cols.run_id in df_controles.columns:


        serie_run = df_controles[cols.run_id].dropna().astype(str).str.strip()


        run_id_val = serie_run.iloc[0] if not serie_run.empty else None





    # Tipo de controle


    if cols.control_type and cols.control_type in df_controles.columns:


        tipo_controle_series = (


            df_controles[cols.control_type].astype(str).str.strip().str.lower()


        )


    else:


        # Fallback genérico


        tipo_controle_series = pd.Series(


            ["controle"] * len(df_controles), index=df_controles.index


        )





    df_controles = df_controles.assign(_tipo_controle=tipo_controle_series)





    agrupado = df_controles.groupby("_tipo_controle", dropna=False)





    linhas: List[Dict[str, object]] = []





    for tipo_controle, grupo in agrupado:


        ct_grupo = pd.to_numeric(grupo[cols.ct], errors="coerce").dropna()





        if ct_grupo.empty:


            n_pocos = int(len(grupo))


            ct_medio = None


            ct_min = None


            ct_max = None


            ct_desvio = None


        else:


            n_pocos = int(len(ct_grupo))


            ct_medio = float(ct_grupo.mean())


            ct_min = float(ct_grupo.min())


            ct_max = float(ct_grupo.max())


            ct_desvio = float(ct_grupo.std(ddof=0))





        faixa_txt = ""


        situacao = "Sem faixa definida"


        if faixas_aceitabilidade and tipo_controle in faixas_aceitabilidade:


            faixa_min, faixa_max = faixas_aceitabilidade[tipo_controle]


            if faixa_min is not None and faixa_max is not None:


                faixa_txt = f"{faixa_min} <= Ct <= {faixa_max}"


            elif faixa_min is not None:


                faixa_txt = f"Ct >= {faixa_min}"


            elif faixa_max is not None:


                faixa_txt = f"Ct <= {faixa_max}"





            if ct_medio is not None:


                dentro_min = True if faixa_min is None else ct_medio >= faixa_min


                dentro_max = True if faixa_max is None else ct_medio <= faixa_max


                situacao = "Dentro da faixa" if (dentro_min and dentro_max) else "Fora da faixa"





        linhas.append(


            {


                "id_corrida": run_id_val,


                "tipo_controle": tipo_controle,


                "n_pocos": n_pocos,


                "ct_medio": ct_medio,


                "ct_min": ct_min,


                "ct_max": ct_max,


                "ct_desvio_padrao": ct_desvio,


                "faixa_aceitabilidade": faixa_txt,


                "situacao": situacao,


            }


        )





    rel = pd.DataFrame(linhas)


    rel = rel.sort_values(by=["id_corrida", "tipo_controle"], kind="stable")





    return rel.reset_index(drop=True)








def gerar_relatorio_indicadores_qualidade_periodo(


    df_historico: pd.DataFrame,


    cols: QualidadeColumnConfig,


    periodo_inicio: Optional[pd.Timestamp] = None,


    periodo_fim: Optional[pd.Timestamp] = None,


    frequencia: str = "M",


) -> pd.DataFrame:


    """Relatório de Indicadores de Qualidade por Período.





    Consolida indicadores por exame e equipamento, em um período opcional,


    agrupando por 'frequencia' (ex.: 'D' = dia, 'W' = semana, 'M' = mês).





    Indicadores por (período, exame, equipamento):





      - total_amostras


      - total_retestes


      - taxa_reteste


      - total_invalidos


      - total_inconclusivos


      - perc_invalidos


      - perc_inconclusivos


      - ct_pos_controle_medio     (controles positivos)


      - ct_pos_controle_min


      - ct_pos_controle_max


      - ct_pos_controle_desvio


    """


    if df_historico.empty:


        return pd.DataFrame(


            columns=[


                "periodo",


                "exame",


                "equipamento",


                "total_amostras",


                "total_retestes",


                "taxa_reteste",


                "total_invalidos",


                "total_inconclusivos",


                "perc_invalidos",


                "perc_inconclusivos",


                "ct_pos_controle_medio",


                "ct_pos_controle_min",


                "ct_pos_controle_max",


                "ct_pos_controle_desvio",


            ]


        )





    df = df_historico.copy()





    # Identifica coluna de data/hora da corrida, se existir


    ts_series = None


    for candidate_col in ["data_hora_corrida", "run_datetime", "data_hora"]:


        if candidate_col in df.columns:


            ts_series = pd.to_datetime(df[candidate_col], errors="coerce")


            break





    if ts_series is None:


        # Sem data, período único


        df["__periodo__"] = "NA"


    else:


        mask = pd.Series(True, index=df.index)


        if periodo_inicio is not None:


            mask &= ts_series >= periodo_inicio


        if periodo_fim is not None:


            mask &= ts_series <= periodo_fim


        df = df.loc[mask].copy()


        ts_series = ts_series.loc[mask]





        periodo_series = ts_series.dt.to_period(frequencia).astype(str)


        df["__periodo__"] = periodo_series





    if df.empty:


        return pd.DataFrame(


            columns=[


                "periodo",


                "exame",


                "equipamento",


                "total_amostras",


                "total_retestes",


                "taxa_reteste",


                "total_invalidos",


                "total_inconclusivos",


                "perc_invalidos",


                "perc_inconclusivos",


                "ct_pos_controle_medio",


                "ct_pos_controle_min",


                "ct_pos_controle_max",


                "ct_pos_controle_desvio",


            ]


        )





    # Tipo de amostra / resultado


    tipo_amostra = df[cols.sample_type].astype(str).str.strip().str.lower()





    # Amostras (não-controles) para indicadores


    df_amostras = df.loc[tipo_amostra == "amostra"].copy()





    if df_amostras.empty:


        return pd.DataFrame(


            columns=[


                "periodo",


                "exame",


                "equipamento",


                "total_amostras",


                "total_retestes",


                "taxa_reteste",


                "total_invalidos",


                "total_inconclusivos",


                "perc_invalidos",


                "perc_inconclusivos",


                "ct_pos_controle_medio",


                "ct_pos_controle_min",


                "ct_pos_controle_max",


                "ct_pos_controle_desvio",


            ]


        )





    # Flag de reteste


    if cols.retest_flag and cols.retest_flag in df_amostras.columns:


        reteste_series = df_amostras[cols.retest_flag].fillna(False)


        reteste_bool = reteste_series.astype(str).str.strip().str.lower().isin(


            ["1", "true", "sim", "yes", "y", "t"]


        )


    else:


        reteste_bool = pd.Series(False, index=df_amostras.index)





    resultado_amostra = (


        df_amostras[cols.result].astype(str).str.strip().str.lower()


    )





    # Controles positivos para distribuição de Ct


    df_controles = df.loc[tipo_amostra == "controle"].copy()


    df_controles_pos = pd.DataFrame()


    if not df_controles.empty and cols.control_type and cols.control_type in df_controles.columns:


        tipo_controle = (


            df_controles[cols.control_type].astype(str).str.strip().str.lower()


        )


        mask_pos = tipo_controle.str.contains("positivo", na=False)


        df_controles_pos = df_controles.loc[mask_pos].copy()





    # Garante que controles positivos também tenham período


    if not df_controles_pos.empty:


        df_controles_pos["__periodo__"] = df["__periodo__"].loc[


            df_controles_pos.index


        ]





    def indicadores_para_grupo(


        periodo: str, exame: str, equipamento: str, idxs: pd.Index


    ) -> Dict[str, object]:


        total = int(len(idxs))


        if total == 0:


            return {


                "periodo": periodo,


                "exame": exame,


                "equipamento": equipamento,


                "total_amostras": 0,


                "total_retestes": 0,


                "taxa_reteste": 0.0,


                "total_invalidos": 0,


                "total_inconclusivos": 0,


                "perc_invalidos": 0.0,


                "perc_inconclusivos": 0.0,


                "ct_pos_controle_medio": None,


                "ct_pos_controle_min": None,


                "ct_pos_controle_max": None,


                "ct_pos_controle_desvio": None,


            }





        # Amostras


        retestes = int(reteste_bool.loc[idxs].sum())


        res_grupo = resultado_amostra.loc[idxs]


        invalidos = int(


            (res_grupo == "inválido").sum() + (res_grupo == "invalido").sum()


        )


        inconclusivos = int((res_grupo == "inconclusivo").sum())





        taxa_reteste = float(retestes / total)


        perc_invalidos = float(invalidos / total)


        perc_inconclusivos = float(inconclusivos / total)





        # Controles positivos para o mesmo período/exame/equipamento


        ct_pos_medio = None


        ct_pos_min = None


        ct_pos_max = None


        ct_pos_desvio = None





        if not df_controles_pos.empty:


            df_pos_local = df_controles_pos.copy()


            mask_local = (


                (df_pos_local[cols.exam] == exame)


                & (df_pos_local[cols.equipment] == equipamento)


                & (df_pos_local["__periodo__"] == periodo)


            )


            ct_local = pd.to_numeric(


                df_pos_local.loc[mask_local, cols.ct], errors="coerce"


            ).dropna()


            if not ct_local.empty:


                ct_pos_medio = float(ct_local.mean())


                ct_pos_min = float(ct_local.min())


                ct_pos_max = float(ct_local.max())


                ct_pos_desvio = float(ct_local.std(ddof=0))





        return {


            "periodo": periodo,


            "exame": exame,


            "equipamento": equipamento,


            "total_amostras": total,


            "total_retestes": retestes,


            "taxa_reteste": taxa_reteste,


            "total_invalidos": invalidos,


            "total_inconclusivos": inconclusivos,


            "perc_invalidos": perc_invalidos,


            "perc_inconclusivos": perc_inconclusivos,


            "ct_pos_controle_medio": ct_pos_medio,


            "ct_pos_controle_min": ct_pos_min,


            "ct_pos_controle_max": ct_pos_max,


            "ct_pos_controle_desvio": ct_pos_desvio,


        }





    df_amostras["__periodo__"] = df["__periodo__"].loc[df_amostras.index]





    grupo = df_amostras.groupby(


        ["__periodo__", cols.exam, cols.equipment], dropna=False


    )





    linhas: List[Dict[str, object]] = []


    for (periodo, exame, equipamento), g in grupo:


        idxs = g.index


        linha = indicadores_para_grupo(periodo, exame, equipamento, idxs)


        linhas.append(linha)





    rel = pd.DataFrame(linhas)


    rel = rel.sort_values(


        by=["periodo", "exame", "equipamento"],


        kind="stable",


        na_position="last",


    )





    return rel.reset_index(drop=True)








@dataclass


class NcRelacionadaColumnConfig:


    """Colunas de um DataFrame de não conformidades relacionadas à corrida.





    Parâmetros


    ----------


    run_id          : identificador da corrida


    nc_id           : identificador da NC


    nc_tipo         : tipo da NC (ex.: 'controle', 'arquivo', 'procedimento')


    nc_descricao    : descrição resumida


    nc_classificacao: classificação (ex.: crítica, maior, menor) (opcional)


    """





    run_id: str


    nc_id: str


    nc_tipo: str


    nc_descricao: str


    nc_classificacao: Optional[str] = None








def gerar_relatorio_nc_relacionadas_corrida(


    df_nc: pd.DataFrame,


    cols: NcRelacionadaColumnConfig,


) -> pd.DataFrame:


    """Relatório de Não Conformidades Relacionadas à Corrida.





    Lista, por corrida, as NCs registradas:





      - id_corrida


      - nc_id


      - nc_tipo


      - nc_classificacao


      - nc_descricao





    df_nc deve ser previamente filtrado para o período/corridas de interesse.


    """


    if df_nc.empty:


        return pd.DataFrame(


            columns=[


                "id_corrida",


                "nc_id",


                "nc_tipo",


                "nc_classificacao",


                "nc_descricao",


            ]


        )





    df = df_nc.copy()





    rel = pd.DataFrame(


        {


            "id_corrida": df[cols.run_id],


            "nc_id": df[cols.nc_id],


            "nc_tipo": df[cols.nc_tipo],


            "nc_classificacao": df[cols.nc_classificacao]


            if cols.nc_classificacao and cols.nc_classificacao in df.columns


            else None,


            "nc_descricao": df[cols.nc_descricao],


        }


    )





    rel = rel.sort_values(


        by=["id_corrida", "nc_tipo", "nc_id"], kind="stable", na_position="last"


    )





    return rel.reset_index(drop=True)








# ============================================================================


# 4. RELATÓRIOS GERENCIAIS E DE PRODUTIVIDADE


# ============================================================================








@dataclass


class ProducaoColumnConfig:


    """Colunas para Relatório de Produção por Período.





    run_id       : identificador da corrida


    run_datetime : data/hora da corrida


    exam         : exame realizado


    equipment    : equipamento utilizado


    sample_type  : tipo de amostra (amostra/controle/branco)


    """





    run_id: str


    run_datetime: str


    exam: str


    equipment: str


    sample_type: str








def gerar_relatorio_producao_periodo(


    df_historico: pd.DataFrame,


    cols: ProducaoColumnConfig,


    periodo_inicio: Optional[pd.Timestamp] = None,


    periodo_fim: Optional[pd.Timestamp] = None,


    frequencia: str = "D",


) -> pd.DataFrame:


    """Relatório de Produção por Período.





    Para cada (período, exame, equipamento) calcula:





      - n_corridas  : número de corridas distintas


      - n_exames    : número de amostras (sample_type == 'amostra')





    frequencia: 'D' (dia), 'W' (semana), 'M' (mês), etc.


    """


    if df_historico.empty:


        return pd.DataFrame(


            columns=["periodo", "exame", "equipamento", "n_corridas", "n_exames"]


        )





    df = df_historico.copy()





    ts = pd.to_datetime(df[cols.run_datetime], errors="coerce")





    mask = pd.Series(True, index=df.index)


    if periodo_inicio is not None:


        mask &= ts >= periodo_inicio


    if periodo_fim is not None:


        mask &= ts <= periodo_fim





    df = df.loc[mask].copy()


    ts = ts.loc[mask]





    if df.empty:


        return pd.DataFrame(


            columns=["periodo", "exame", "equipamento", "n_corridas", "n_exames"]


        )





    df["__periodo__"] = ts.dt.to_period(frequencia).astype(str)





    tipo_amostra = df[cols.sample_type].astype(str).str.strip().str.lower()


    df_amostras = df.loc[tipo_amostra == "amostra"].copy()





    if df_amostras.empty:


        return pd.DataFrame(


            columns=["periodo", "exame", "equipamento", "n_corridas", "n_exames"]


        )





    grupo = df_amostras.groupby(


        ["__periodo__", cols.exam, cols.equipment], dropna=False


    )





    linhas: List[Dict[str, object]] = []


    for (periodo, exame, equipamento), g in grupo:


        n_exames = int(len(g))


        n_corridas = int(g[cols.run_id].dropna().astype(str).nunique())


        linhas.append(


            {


                "periodo": periodo,


                "exame": exame,


                "equipamento": equipamento,


                "n_corridas": n_corridas,


                "n_exames": n_exames,


            }


        )





    rel = pd.DataFrame(linhas)


    rel = rel.sort_values(


        by=["periodo", "exame", "equipamento"],


        kind="stable",


        na_position="last",


    )





    return rel.reset_index(drop=True)








def gerar_relatorio_positividade_exame_periodo(


    df_historico: pd.DataFrame,


    cols: QualidadeColumnConfig,


    periodo_inicio: Optional[pd.Timestamp] = None,


    periodo_fim: Optional[pd.Timestamp] = None,


    frequencia: str = "M",


) -> pd.DataFrame:


    """Relatório de Positividade por Exame / Período.





    Para cada (período, exame) calcula:





      - n_amostras


      - n_positivas


      - n_negativas


      - perc_positivas


      - perc_negativas


    """


    if df_historico.empty:


        return pd.DataFrame(


            columns=[


                "periodo",


                "exame",


                "n_amostras",


                "n_positivas",


                "n_negativas",


                "perc_positivas",


                "perc_negativas",


            ]


        )





    df = df_historico.copy()





    ts = None


    for candidate_col in ["data_hora_corrida", "run_datetime", "data_hora"]:


        if candidate_col in df.columns:


            ts = pd.to_datetime(df[candidate_col], errors="coerce")


            break





    if ts is None:


        df["__periodo__"] = "NA"


    else:


        mask = pd.Series(True, index=df.index)


        if periodo_inicio is not None:


            mask &= ts >= periodo_inicio


        if periodo_fim is not None:


            mask &= ts <= periodo_fim


        df = df.loc[mask].copy()


        ts = ts.loc[mask]


        df["__periodo__"] = ts.dt.to_period(frequencia).astype(str)





    if df.empty:


        return pd.DataFrame(


            columns=[


                "periodo",


                "exame",


                "n_amostras",


                "n_positivas",


                "n_negativas",


                "perc_positivas",


                "perc_negativas",


            ]


        )





    tipo_amostra = df[cols.sample_type].astype(str).str.strip().str.lower()


    df_amostras = df.loc[tipo_amostra == "amostra"].copy()





    if df_amostras.empty:


        return pd.DataFrame(


            columns=[


                "periodo",


                "exame",


                "n_amostras",


                "n_positivas",


                "n_negativas",


                "perc_positivas",


                "perc_negativas",


            ]


        )





    resultado = df_amostras[cols.result].astype(str).str.strip().str.lower()





    grupo = df_amostras.groupby(["__periodo__", cols.exam], dropna=False)





    linhas: List[Dict[str, object]] = []


    for (periodo, exame), g in grupo:


        idxs = g.index


        total = int(len(idxs))


        if total == 0:


            continue


        res_g = resultado.loc[idxs]


        n_pos = int((res_g == "positivo").sum())


        n_neg = int((res_g == "negativo").sum())


        perc_pos = float(n_pos / total)


        perc_neg = float(n_neg / total)


        linhas.append(


            {


                "periodo": periodo,


                "exame": exame,


                "n_amostras": total,


                "n_positivas": n_pos,


                "n_negativas": n_neg,


                "perc_positivas": perc_pos,


                "perc_negativas": perc_neg,


            }


        )





    rel = pd.DataFrame(linhas)


    rel = rel.sort_values(


        by=["periodo", "exame"], kind="stable", na_position="last"


    )





    return rel.reset_index(drop=True)








def gerar_relatorio_produtividade_equipamento(


    df_historico: pd.DataFrame,


    cols: ProducaoColumnConfig,


    periodo_inicio: Optional[pd.Timestamp] = None,


    periodo_fim: Optional[pd.Timestamp] = None,


    frequencia: str = "M",


) -> pd.DataFrame:


    """Relatório de Produtividade por Equipamento.





    Para cada (período, equipamento) calcula:





      - n_corridas  : número de corridas distintas


      - n_amostras  : número de amostras (sample_type == 'amostra')


    """


    if df_historico.empty:


        return pd.DataFrame(


            columns=["periodo", "equipamento", "n_corridas", "n_amostras"]


        )





    df = df_historico.copy()





    ts = pd.to_datetime(df[cols.run_datetime], errors="coerce")





    mask = pd.Series(True, index=df.index)


    if periodo_inicio is not None:


        mask &= ts >= periodo_inicio


    if periodo_fim is not None:


        mask &= ts <= periodo_fim





    df = df.loc[mask].copy()


    ts = ts.loc[mask]





    if df.empty:


        return pd.DataFrame(


            columns=["periodo", "equipamento", "n_corridas", "n_amostras"]


        )





    df["__periodo__"] = ts.dt.to_period(frequencia).astype(str)





    tipo_amostra = df[cols.sample_type].astype(str).str.strip().str.lower()


    df_amostras = df.loc[tipo_amostra == "amostra"].copy()





    if df_amostras.empty:


        return pd.DataFrame(


            columns=["periodo", "equipamento", "n_corridas", "n_amostras"]


        )





    grupo = df_amostras.groupby(["__periodo__", cols.equipment], dropna=False)





    linhas: List[Dict[str, object]] = []


    for (periodo, equipamento), g in grupo:


        n_amostras = int(len(g))


        n_corridas = int(g[cols.run_id].dropna().astype(str).nunique())


        linhas.append(


            {


                "periodo": periodo,


                "equipamento": equipamento,


                "n_corridas": n_corridas,


                "n_amostras": n_amostras,


            }


        )





    rel = pd.DataFrame(linhas)


    rel = rel.sort_values(


        by=["periodo", "equipamento"], kind="stable", na_position="last"


    )





    return rel.reset_index(drop=True)








@dataclass


class TatColumnConfig:


    """Colunas para cálculo de TAT (Tempo de Processamento).





    run_id              : identificador da corrida


    extraction_datetime : data/hora da extração (opcional)


    result_datetime     : data/hora em que o resultado foi obtido


    send_datetime       : data/hora de envio ao GAL (opcional)


    """





    run_id: str


    extraction_datetime: Optional[str]


    result_datetime: str


    send_datetime: Optional[str] = None








def gerar_relatorio_tempo_processamento(


    df_historico: pd.DataFrame,


    cols: TatColumnConfig,


) -> pd.DataFrame:


    """Relatório de Tempo de Processamento (TAT).





    Para cada corrida, calcula:





      - n_amostras


      - tat_extracao_resultado_min   (média em minutos, quando houver extração)


      - tat_resultado_envio_gal_min  (média em minutos, quando houver envio)





    Assume que as colunas de data/hora existam, quando configuradas.


    """


    if df_historico.empty:


        return pd.DataFrame(


            columns=[


                "id_corrida",


                "n_amostras",


                "tat_extracao_resultado_min",


                "tat_resultado_envio_gal_min",


            ]


        )





    df = df_historico.copy()





    # Conversão das colunas de data/hora


    if cols.extraction_datetime and cols.extraction_datetime in df.columns:


        dt_extr = pd.to_datetime(df[cols.extraction_datetime], errors="coerce")


    else:


        dt_extr = None





    dt_res = pd.to_datetime(df[cols.result_datetime], errors="coerce")





    if cols.send_datetime and cols.send_datetime in df.columns:


        dt_envio = pd.to_datetime(df[cols.send_datetime], errors="coerce")


    else:


        dt_envio = None





    grupo = df.groupby(cols.run_id, dropna=False)





    linhas: List[Dict[str, object]] = []





    for run_id_val, g in grupo:


        idxs = g.index


        n_amostras = int(len(g))





        tat_extracao_res = None


        tat_result_envio = None





        # extração -> resultado


        if dt_extr is not None:


            delta_extr_res = (dt_res.loc[idxs] - dt_extr.loc[idxs]).dropna()


            if not delta_extr_res.empty:


                tat_extracao_res = float(


                    delta_extr_res.mean().total_seconds() / 60.0


                )





        # resultado -> envio


        if dt_envio is not None:


            delta_res_envio = (dt_envio.loc[idxs] - dt_res.loc[idxs]).dropna()


            if not delta_res_envio.empty:


                tat_result_envio = float(


                    delta_res_envio.mean().total_seconds() / 60.0


                )





        linhas.append(


            {


                "id_corrida": run_id_val,


                "n_amostras": n_amostras,


                "tat_extracao_resultado_min": tat_extracao_res,


                "tat_resultado_envio_gal_min": tat_result_envio,


            }


        )





    rel = pd.DataFrame(linhas)


    rel = rel.sort_values(by="id_corrida", kind="stable", na_position="last")





    return rel.reset_index(drop=True)


