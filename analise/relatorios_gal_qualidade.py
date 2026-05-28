


"""


Módulo de relatórios para integração GAL e qualidade analítica (CQI/CQE).





Este módulo complementa os relatórios operacionais, focando em:





2. Relatórios para integração GAL


   - Relatório de Pré-Envio ao GAL


   - Relatório de Exportação GAL


   - Relatório de Envio ao GAL





3. Relatórios de qualidade (CQI / CQE / indicadores técnicos)


   - Relatório de Controles Internos por Corrida


   - Relatório de Indicadores de Qualidade por Período


   - Relatório de Não Conformidades Relacionadas à Corrida





As funções aqui definidas trabalham exclusivamente com pandas.DataFrame


e são pensadas para serem chamadas a partir dos serviços da aplicação


(ex.: AnalysisService, GalIntegrationService, QualityService).


"""





from __future__ import annotations





from dataclasses import dataclass


from typing import Dict, Iterable, List, Optional, Tuple





import pandas as pd





# Reaproveitamos o ColumnConfig do módulo de relatórios operacionais


try:


    # Import mantido apenas para compatibilidade; marcado com noqa para evitar F401 (import não utilizado).


    from .relatorios_operacionais import ColumnConfig  # noqa: F401


except ImportError:  # fallback se import relativo não funcionar


    from analise.relatorios_operacionais import ColumnConfig  # type: ignore  # noqa: F401








# ============================================================================


# 2. RELATÓRIOS PARA INTEGRAÇÃO GAL


# ============================================================================








@dataclass


class GalPreEnvioColumnConfig:


    """Mapeia as colunas do df_final necessárias para o pré-envio ao GAL.





    A ideia é gerar uma 'prévia' do que será enviado, verificando se todos os


    campos obrigatórios estão preenchidos.





    Campos típicos:


      - sample_id      : identificador da amostra


      - exam_code      : código do exame (interno ou GAL)


      - result         : resultado interpretado


      - patient_id     : identificador do paciente (opcional)


      - run_id         : identificador da corrida (opcional)


    """





    sample_id: str


    exam_code: str


    result: str


    patient_id: Optional[str] = None


    run_id: Optional[str] = None








def gerar_relatorio_pre_envio_gal(


    df_final: pd.DataFrame,


    cols: GalPreEnvioColumnConfig,


    campos_obrigatorios: Optional[Iterable[str]] = None,


) -> pd.DataFrame:


    """Gera o Relatório de Pré-Envio ao GAL.





    Para cada amostra, mostra os principais dados que irão para o payload/CSV


    de envio ao GAL e marca situações de alerta, como:





      - campos obrigatórios ausentes;


      - resultado vazio ou não interpretado.





    Parâmetros


    ----------


    df_final:


        DataFrame de resultados consolidados (df_final) da corrida/corridas.


    cols:


        Mapeamento das colunas relevantes (GalPreEnvioColumnConfig).


    campos_obrigatorios:


        Lista de nomes lógicos (entre 'sample_id', 'exam_code', 'result',


        'patient_id', 'run_id') que devem ser validados como obrigatórios.





    Retorno


    -------


    DataFrame com colunas:


      - id_amostra


      - codigo_exame


      - resultado


      - id_paciente


      - id_corrida


      - pronto_para_envio (bool)


      - alertas (texto)


    """


    if df_final.empty:


        return pd.DataFrame(


            columns=[


                "id_amostra",


                "codigo_exame",


                "resultado",


                "id_paciente",


                "id_corrida",


                "pronto_para_envio",


                "alertas",


            ]


        )





    if campos_obrigatorios is None:


        campos_obrigatorios = ["sample_id", "exam_code", "result"]





    df = df_final.copy()





    # Construção das colunas básicas


    rel = pd.DataFrame(


        {


            "id_amostra": df[cols.sample_id],


            "codigo_exame": df[cols.exam_code],


            "resultado": df[cols.result],


        }


    )





    # Campos opcionais


    if cols.patient_id and cols.patient_id in df.columns:


        rel["id_paciente"] = df[cols.patient_id]


    else:


        rel["id_paciente"] = None





    if cols.run_id and cols.run_id in df.columns:


        rel["id_corrida"] = df[cols.run_id]


    else:


        rel["id_corrida"] = None





    # Avalia obrigatoriedade e alerta por linha


    alertas: List[str] = []


    pronto_flags: List[bool] = []





    for idx, row in rel.iterrows():


        problemas = []





        # Checagem de campos obrigatórios


        for campo_logico in campos_obrigatorios:


            if campo_logico == "sample_id":


                valor = row["id_amostra"]


                rotulo = "ID da amostra"


            elif campo_logico == "exam_code":


                valor = row["codigo_exame"]


                rotulo = "Código do exame"


            elif campo_logico == "result":


                valor = row["resultado"]


                rotulo = "Resultado"


            elif campo_logico == "patient_id":


                valor = row["id_paciente"]


                rotulo = "ID do paciente"


            elif campo_logico == "run_id":


                valor = row["id_corrida"]


                rotulo = "ID da corrida"


            else:


                # campo lógico desconhecido, ignora


                continue





            if pd.isna(valor) or str(valor).strip() == "":


                problemas.append(f"Campo obrigatório ausente: {rotulo}.")





        # Checagem simples de resultado incompleto


        if not pd.isna(row["resultado"]):


            if str(row["resultado"]).strip() == "":


                problemas.append("Resultado vazio ou não interpretado.")


        else:


            problemas.append("Resultado ausente.")





        pronto = len(problemas) == 0


        pronto_flags.append(pronto)


        alertas.append(" ".join(problemas) if problemas else "")





    rel["pronto_para_envio"] = pronto_flags


    rel["alertas"] = alertas





    # Ordena por id_amostra/codigo_exame para manter previsibilidade


    rel = rel.sort_values(


        by=["id_corrida", "codigo_exame", "id_amostra"],


        kind="stable",


        na_position="last",


    )





    return rel.reset_index(drop=True)








@dataclass


class GalExportLogConfig:


    """Mapeia as colunas de um DataFrame de log de exportação GAL.





    Este DataFrame é esperado ser preenchido pela camada de integração,


    por exemplo, cada vez que um arquivo para GAL é gerado.





    Campos típicos:


      - timestamp      : data/hora da exportação


      - run_id         : identificador da corrida/lote


      - exams_count    : quantidade de exames enviados


      - file_name      : nome do arquivo gerado


      - file_path      : caminho completo do arquivo gerado


    """





    timestamp: str


    run_id: str


    exams_count: str


    file_name: str


    file_path: str








def gerar_relatorio_exportacao_gal(


    df_exportacoes: pd.DataFrame,


    cols: GalExportLogConfig,


    periodo_inicio: Optional[pd.Timestamp] = None,


    periodo_fim: Optional[pd.Timestamp] = None,


) -> pd.DataFrame:


    """Gera o Relatório de Exportação GAL (por corrida ou por período).





    Este relatório consolida o log de exportação de arquivos para o GAL.


    Pode ser filtrado por período (timestamp entre periodo_inicio e periodo_fim).





    Retorno


    -------


    DataFrame com colunas:


      - data_hora_exportacao


      - id_corrida


      - quantidade_exames


      - nome_arquivo


      - caminho_arquivo


    """


    if df_exportacoes.empty:


        return pd.DataFrame(


            columns=[


                "data_hora_exportacao",


                "id_corrida",


                "quantidade_exames",


                "nome_arquivo",


                "caminho_arquivo",


            ]


        )





    df = df_exportacoes.copy()





    # Converte timestamp para datetime (quando possível) para permitir filtragem


    ts_series = pd.to_datetime(df[cols.timestamp], errors="coerce")





    mask = pd.Series(True, index=df.index)


    if periodo_inicio is not None:


        mask &= ts_series >= periodo_inicio


    if periodo_fim is not None:


        mask &= ts_series <= periodo_fim





    df = df.loc[mask].copy()





    rel = pd.DataFrame(


        {


            "data_hora_exportacao": ts_series[mask],


            "id_corrida": df[cols.run_id],


            "quantidade_exames": pd.to_numeric(


                df[cols.exams_count], errors="coerce"


            ),


            "nome_arquivo": df[cols.file_name],


            "caminho_arquivo": df[cols.file_path],


        }


    )





    # Ordena por data/hora de exportação


    rel = rel.sort_values(


        by=["data_hora_exportacao", "id_corrida"],


        kind="stable",


        na_position="last",


    )





    return rel.reset_index(drop=True)








@dataclass


class GalEnvioLogConfig:


    """Mapeia as colunas de um DataFrame de log de envio ao GAL.





    Este DataFrame é esperado ser preenchido pelo módulo de integração


    sempre que uma requisição de envio ao GAL for realizada.





    Campos típicos:


      - timestamp         : data/hora do envio


      - run_id            : identificador da corrida/lote


      - exams_count       : quantidade de exames na requisição


      - status            : status textual (ex.: 'SUCESSO', 'FALHA')


      - http_status       : código HTTP retornado (quando houver)


      - gal_response_code : código de retorno específico do GAL (quando houver)


      - error_message     : mensagem de erro (quando houver)


    """





    timestamp: str


    run_id: str


    exams_count: str


    status: str


    http_status: Optional[str] = None


    gal_response_code: Optional[str] = None


    error_message: Optional[str] = None








def gerar_relatorio_envio_gal(


    df_envios: pd.DataFrame,


    cols: GalEnvioLogConfig,


    periodo_inicio: Optional[pd.Timestamp] = None,


    periodo_fim: Optional[pd.Timestamp] = None,


) -> pd.DataFrame:


    """Gera o Relatório de Envio ao GAL (log de integração).





    Para cada envio realizado, lista:


      - data/hora do envio


      - id_corrida


      - quantidade de exames na requisição


      - status (sucesso/falha)


      - códigos retornados (HTTP/GAL)


      - mensagem de erro (quando existir)





    Este relatório é essencial para auditoria e resolução de divergências


    entre GAL e laboratório.


    """


    if df_envios.empty:


        return pd.DataFrame(


            columns=[


                "data_hora_envio",


                "id_corrida",


                "quantidade_exames",


                "status",


                "http_status",


                "codigo_resposta_gal",


                "mensagem_erro",


            ]


        )





    df = df_envios.copy()





    ts_series = pd.to_datetime(df[cols.timestamp], errors="coerce")





    mask = pd.Series(True, index=df.index)


    if periodo_inicio is not None:


        mask &= ts_series >= periodo_inicio


    if periodo_fim is not None:


        mask &= ts_series <= periodo_fim





    df = df.loc[mask].copy()





    rel = pd.DataFrame(


        {


            "data_hora_envio": ts_series[mask],


            "id_corrida": df[cols.run_id],


            "quantidade_exames": pd.to_numeric(


                df[cols.exams_count], errors="coerce"


            ),


            "status": df[cols.status],


            "http_status": df[cols.http_status]


            if cols.http_status and cols.http_status in df.columns


            else None,


            "codigo_resposta_gal": df[cols.gal_response_code]


            if cols.gal_response_code and cols.gal_response_code in df.columns


            else None,


            "mensagem_erro": df[cols.error_message]


            if cols.error_message and cols.error_message in df.columns


            else None,


        }


    )





    rel = rel.sort_values(


        by=["data_hora_envio", "id_corrida"],


        kind="stable",


        na_position="last",


    )





    return rel.reset_index(drop=True)








# ============================================================================


# 3. RELATÓRIOS DE QUALIDADE (CQI / CQE / INDICADORES TÉCNICOS)


# ============================================================================








@dataclass


class QualidadeColumnConfig:


    """Mapeia as colunas necessárias para relatórios de qualidade.





    Em muitos cenários, estas colunas já existirão em df_final ou em um


    DataFrame histórico consolidado.





    Campos típicos:


      - run_id        : identificador da corrida


      - exam          : exame realizado


      - equipment     : equipamento utilizado


      - sample_type   : tipo de amostra (amostra/controle/branco)


      - control_type  : tipo de controle (ex.: 'controle positivo',


                         'controle negativo', 'controle interno', etc.)


      - result        : resultado interpretado


      - ct            : Ct principal


      - retest_flag   : flag indicando se é um reteste (opcional)


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


    """Gera o Relatório de Controles Internos por Corrida.





    Para uma corrida (df_final de uma corrida), calcula, por tipo de controle:





      - N (número de poços)


      - Ct médio


      - Ct mínimo


      - Ct máximo


      - Desvio padrão de Ct


      - Situação em relação à faixa de aceitabilidade (quando fornecida)





    Parâmetros


    ----------


    df_final:


        DataFrame da corrida.


    cols:


        Configuração de colunas relevantes para qualidade.


    faixas_aceitabilidade:


        Dicionário opcional mapeando o tipo de controle para um par


        (ct_min, ct_max). Ex.:


          {


              "controle positivo": (25.0, 30.0),


              "controle interno": (20.0, 35.0),


          }





    Retorno


    -------


    DataFrame com colunas:


      - id_corrida


      - tipo_controle


      - n_pocos


      - ct_medio


      - ct_min


      - ct_max


      - ct_desvio_padrao


      - faixa_aceitabilidade


      - situacao


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





    run_id_val = None


    if cols.run_id in df_controles.columns:


        serie_run = df_controles[cols.run_id].dropna().astype(str).str.strip()


        run_id_val = serie_run.iloc[0] if not serie_run.empty else None





    # Determina o agrupador para tipo de controle


    if cols.control_type and cols.control_type in df_controles.columns:


        tipo_controle_series = (


            df_controles[cols.control_type].astype(str).str.strip().str.lower()


        )


    else:


        # Fallback: considera todos como 'controle' genérico


        tipo_controle_series = pd.Series(


            ["controle"] * len(df_controles), index=df_controles.index


        )





    df_controles = df_controles.assign(_tipo_controle=tipo_controle_series)





    # ct_vals = pd.to_numeric(df_controles[cols.ct], errors="coerce")


    # Comentado: variável auxiliar não utilizada diretamente (Ruff F841).





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


) -> pd.DataFrame:


    """Gera o Relatório de Indicadores de Qualidade por Período.





    Consolida indicadores por exame e equipamento, em um período opcional.





    Indicadores calculados (por exame/equipamento):





      - total_amostras


      - total_retestes             (quando retest_flag fornecido)


      - taxa_reteste               (total_retestes / total_amostras)


      - total_invalidos


      - total_inconclusivos


      - perc_invalidos             (total_invalidos / total_amostras)


      - perc_inconclusivos         (total_inconclusivos / total_amostras)





    df_historico pode conter múltiplas corridas.


    """


    if df_historico.empty:


        return pd.DataFrame(


            columns=[


                "exame",


                "equipamento",


                "total_amostras",


                "total_retestes",


                "taxa_reteste",


                "total_invalidos",


                "total_inconclusivos",


                "perc_invalidos",


                "perc_inconclusivos",


            ]


        )





    df = df_historico.copy()





    # Se existir coluna de data/hora da corrida, a filtragem por período


    # pode ser feita na camada de preparação. Aqui assumimos que o df já


    # está filtrado OU que exista colunas específicas para isso.


    # Para não impor nomes de colunas, este filtro é opcional e externo.





    # Tipo de amostra / resultado


    tipo_amostra = df[cols.sample_type].astype(str).str.strip().str.lower()


    # resultado = df[cols.result].astype(str).str.strip().str.lower()


    # Comentado: variável não utilizada diretamente (Ruff F841).





    # Consideramos apenas linhas do tipo 'amostra' para cálculo de indicadores.


    df_amostras = df.loc[tipo_amostra == "amostra"].copy()





    if df_amostras.empty:


        return pd.DataFrame(


            columns=[


                "exame",


                "equipamento",


                "total_amostras",


                "total_retestes",


                "taxa_reteste",


                "total_invalidos",


                "total_inconclusivos",


                "perc_invalidos",


                "perc_inconclusivos",


            ]


        )





    if periodo_inicio is not None or periodo_fim is not None:


        # Tentativa de usar uma coluna chamada 'data_hora_corrida' se existir.


        # Caso contrário, assume que o DataFrame já foi filtrado fora desta função.


        for candidate_col in ["data_hora_corrida", "run_datetime", "data_hora"]:


            if candidate_col in df_amostras.columns:


                ts_series = pd.to_datetime(


                    df_amostras[candidate_col], errors="coerce"


                )


                mask = pd.Series(True, index=df_amostras.index)


                if periodo_inicio is not None:


                    mask &= ts_series >= periodo_inicio


                if periodo_fim is not None:


                    mask &= ts_series <= periodo_fim


                df_amostras = df_amostras.loc[mask].copy()


                break





    if df_amostras.empty:


        return pd.DataFrame(


            columns=[


                "exame",


                "equipamento",


                "total_amostras",


                "total_retestes",


                "taxa_reteste",


                "total_invalidos",


                "total_inconclusivos",


                "perc_invalidos",


                "perc_inconclusivos",


            ]


        )





    # Marca reteste quando houver coluna indicada


    if cols.retest_flag and cols.retest_flag in df_amostras.columns:


        reteste_series = df_amostras[cols.retest_flag].fillna(False)


        # Aceita booleans ou strings equivalentes


        reteste_bool = reteste_series.astype(str).str.strip().str.lower().isin(


            ["1", "true", "sim", "yes", "y", "t"]


        )


    else:


        reteste_bool = pd.Series(False, index=df_amostras.index)





    resultado_amostra = (


        df_amostras[cols.result].astype(str).str.strip().str.lower()


    )





    def indicador_grupo(grupo: pd.DataFrame) -> Dict[str, object]:


        idxs = grupo.index


        total = int(len(idxs))


        if total == 0:


            return {


                "total_amostras": 0,


                "total_retestes": 0,


                "taxa_reteste": 0.0,


                "total_invalidos": 0,


                "total_inconclusivos": 0,


                "perc_invalidos": 0.0,


                "perc_inconclusivos": 0.0,


            }





        retestes = int(reteste_bool.loc[idxs].sum())





        res_grupo = resultado_amostra.loc[idxs]


        invalidos = int(


            (res_grupo == "inválido").sum() + (res_grupo == "invalido").sum()


        )


        inconclusivos = int((res_grupo == "inconclusivo").sum())





        taxa_reteste = float(retestes / total) if total > 0 else 0.0


        perc_invalidos = float(invalidos / total) if total > 0 else 0.0


        perc_inconclusivos = float(inconclusivos / total) if total > 0 else 0.0





        return {


            "total_amostras": total,


            "total_retestes": retestes,


            "taxa_reteste": taxa_reteste,


            "total_invalidos": invalidos,


            "total_inconclusivos": inconclusivos,


            "perc_invalidos": perc_invalidos,


            "perc_inconclusivos": perc_inconclusivos,


        }





    # Agrupamento por exame/equipamento


    grupo = df_amostras.groupby([cols.exam, cols.equipment], dropna=False)





    linhas: List[Dict[str, object]] = []





    for (exame, equipamento), g in grupo:


        indicadores = indicador_grupo(g)


        linha = {


            "exame": exame,


            "equipamento": equipamento,


            **indicadores,


        }


        linhas.append(linha)





    rel = pd.DataFrame(linhas)





    rel = rel.sort_values(


        by=["exame", "equipamento"], kind="stable", na_position="last"


    )





    return rel.reset_index(drop=True)








@dataclass


class NcRelacionadaColumnConfig:


    """Mapeia colunas de um DataFrame de não conformidades relacionadas à corrida.





    Este DataFrame é pensado como uma camada de integração com um sistema


    de gestão de NCs (como o Analisador de NCs que você está desenvolvendo).





    Campos típicos:


      - run_id        : identificador da corrida


      - nc_id         : identificador da não conformidade


      - nc_tipo       : tipo da NC (ex.: 'controle', 'arquivo', 'procedimento')


      - nc_descricao  : descrição resumida


      - nc_classificacao : classificação (ex.: crítica, maior, menor)


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


    """Gera o Relatório de Não Conformidades Relacionadas à Corrida.





    Este relatório sumariza, por corrida:





      - número total de NCs


      - número de NCs por tipo


      - classificação mais crítica observada na corrida (se houver)





    e lista cada NC com seus dados principais.





    A função assume que df_nc já é um DataFrame filtrado para o período


    ou conjunto de corridas de interesse.


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


