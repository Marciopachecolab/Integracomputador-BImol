


"""


Módulo de Relatórios de Auditoria, Rastreabilidade e Suporte/Depuração.





Nome do módulo: relatorios_auditoria_dep.py





Grupo 5 – Relatórios de auditoria e rastreabilidade


  - gerar_relatorio_log_uso_sistema


  - gerar_relatorio_versao_regras_motor


  - gerar_relatorio_arquivos_processados





Grupo 6 – Relatórios de suporte / depuração (desenvolvimento)


  - gerar_relatorio_diferencas_motor


  - gerar_relatorio_validacao_csv





Todas as funções operam exclusivamente sobre pandas.DataFrame e estruturas


simples de configuração (dataclasses), sem depender de UI, AppState ou


componentes específicos do IntegraGAL.


"""





from __future__ import annotations





from dataclasses import dataclass


from typing import Dict, Iterable, List, Optional





import pandas as pd








# ============================================================================


# 5. RELATÓRIOS DE AUDITORIA E RASTREABILIDADE


# ============================================================================








@dataclass


class UsoSistemaLogConfig:


    """Colunas para Relatório de Log de Uso do Sistema.





    user_id      : identificador do usuário (login, nome, etc.)


    timestamp    : data/hora da ação


    action       : tipo de ação (ex.: 'IMPORTACAO_ARQUIVO', 'EXECUCAO_ANALISE', 'ENVIO_GAL')


    run_id       : identificador da corrida afetada (opcional)


    details      : texto livre com detalhes da ação (opcional)


    """





    user_id: Optional[str]


    timestamp: str


    action: str


    run_id: Optional[str] = None


    details: Optional[str] = None








def gerar_relatorio_log_uso_sistema(


    df_log: pd.DataFrame,


    cols: UsoSistemaLogConfig,


    periodo_inicio: Optional[pd.Timestamp] = None,


    periodo_fim: Optional[pd.Timestamp] = None,


    acoes_filtrar: Optional[Iterable[str]] = None,


) -> pd.DataFrame:


    """Relatório de Log de Uso do Sistema.





    Filtra e organiza o log de uso, retornando:





      - data_hora


      - usuario


      - acao


      - id_corrida


      - detalhes





    Parâmetros


    ----------


    df_log:


        DataFrame com as ações registradas no sistema.


    cols:


        Configuração de colunas (UsoSistemaLogConfig).


    periodo_inicio / periodo_fim:


        Limites opcionais de período (pandas.Timestamp).


    acoes_filtrar:


        Lista opcional de tipos de ação a incluir


        (ex.: ['IMPORTACAO_ARQUIVO', 'EXECUCAO_ANALISE']).


    """


    if df_log.empty:


        return pd.DataFrame(


            columns=["data_hora", "usuario", "acao", "id_corrida", "detalhes"]


        )





    df = df_log.copy()





    ts = pd.to_datetime(df[cols.timestamp], errors="coerce")





    mask = pd.Series(True, index=df.index)


    if periodo_inicio is not None:


        mask &= ts >= periodo_inicio


    if periodo_fim is not None:


        mask &= ts <= periodo_fim





    df = df.loc[mask].copy()


    ts = ts.loc[mask]





    if df.empty:


        return pd.DataFrame(


            columns=["data_hora", "usuario", "acao", "id_corrida", "detalhes"]


        )





    if acoes_filtrar is not None:


        acoes_norm = {str(a).strip().upper() for a in acoes_filtrar}


        acoes_df = df[cols.action].astype(str).str.strip().str.upper()


        df = df.loc[acoes_df.isin(acoes_norm)].copy()


        ts = ts.loc[df.index]





    if df.empty:


        return pd.DataFrame(


            columns=["data_hora", "usuario", "acao", "id_corrida", "detalhes"]


        )





    usuario = (


        df[cols.user_id] if (cols.user_id and cols.user_id in df.columns) else None


    )


    run_col = df[cols.run_id] if (cols.run_id and cols.run_id in df.columns) else None


    details_col = (


        df[cols.details] if (cols.details and cols.details in df.columns) else None


    )





    rel = pd.DataFrame(


        {


            "data_hora": ts,


            "usuario": usuario,


            "acao": df[cols.action],


            "id_corrida": run_col,


            "detalhes": details_col,


        }


    )





    rel = rel.sort_values(by="data_hora", kind="stable", na_position="last")





    return rel.reset_index(drop=True)








# ---------------------------------------------------------------------------








@dataclass


class VersaoRegrasMotorConfig:


    """Colunas para Relatório de Versão de Regras e Motores por corrida.





    run_id                 : identificador da corrida


    run_datetime           : data/hora da corrida


    analysis_script_version: versão do script/motor de análise


    rules_version          : versão do conjunto de regras configuradas


    cutoff_profile         : identificador do perfil de cutoffs (opcional)


    algorithm_profile      : identificador de perfil de algoritmo/perfil de interpretação (opcional)


    """





    run_id: str


    run_datetime: str


    analysis_script_version: str


    rules_version: str


    cutoff_profile: Optional[str] = None


    algorithm_profile: Optional[str] = None








def gerar_relatorio_versao_regras_motor(


    df_corridas: pd.DataFrame,


    cols: VersaoRegrasMotorConfig,


) -> pd.DataFrame:


    """Relatório de Versão de Regras e Motores.





    Para cada corrida, lista:





      - id_corrida


      - data_hora_corrida


      - versao_motor_analise


      - versao_regras


      - perfil_cutoff


      - perfil_algoritmo





    Útil para rastrear quais versões estavam ativas em cada corrida.


    """


    if df_corridas.empty:


        return pd.DataFrame(


            columns=[


                "id_corrida",


                "data_hora_corrida",


                "versao_motor_analise",


                "versao_regras",


                "perfil_cutoff",


                "perfil_algoritmo",


            ]


        )





    df = df_corridas.copy()





    ts = pd.to_datetime(df[cols.run_datetime], errors="coerce")





    rel = pd.DataFrame(


        {


            "id_corrida": df[cols.run_id],


            "data_hora_corrida": ts,


            "versao_motor_analise": df[cols.analysis_script_version],


            "versao_regras": df[cols.rules_version],


            "perfil_cutoff": df[cols.cutoff_profile]


            if cols.cutoff_profile and cols.cutoff_profile in df.columns


            else None,


            "perfil_algoritmo": df[cols.algorithm_profile]


            if cols.algorithm_profile and cols.algorithm_profile in df.columns


            else None,


        }


    )





    rel = rel.sort_values(


        by=["data_hora_corrida", "id_corrida"], kind="stable", na_position="last"


    )





    return rel.reset_index(drop=True)








# ---------------------------------------------------------------------------








@dataclass


class ArquivosProcessadosConfig:


    """Colunas para Relatório de Arquivos Processados.





    run_id                  : identificador da corrida (opcional, mas recomendável)


    extraction_file_name    : nome do arquivo de extração


    extraction_file_hash    : hash do arquivo de extração (MD5/SHA, etc.) (opcional)


    extraction_file_datetime: data/hora de criação ou importação do arquivo de extração


    result_file_name        : nome do arquivo de resultados


    result_file_hash        : hash do arquivo de resultados (opcional)


    result_file_datetime    : data/hora de criação ou importação do arquivo de resultados


    processing_status       : status de processamento (ex.: 'OK', 'ERRO', 'PARCIAL')


    error_message           : mensagem de erro (quando houver)


    """





    run_id: Optional[str]


    extraction_file_name: str


    extraction_file_hash: Optional[str]


    extraction_file_datetime: str


    result_file_name: str


    result_file_hash: Optional[str]


    result_file_datetime: str


    processing_status: str


    error_message: Optional[str] = None








def gerar_relatorio_arquivos_processados(


    df_arquivos: pd.DataFrame,


    cols: ArquivosProcessadosConfig,


    periodo_inicio: Optional[pd.Timestamp] = None,


    periodo_fim: Optional[pd.Timestamp] = None,


) -> pd.DataFrame:


    """Relatório de Arquivos Processados.





    Retorna tabela com:





      - id_corrida


      - arquivo_extracao


      - hash_extracao


      - data_hora_extracao


      - arquivo_resultados


      - hash_resultados


      - data_hora_resultados


      - status_processamento


      - mensagem_erro


    """


    if df_arquivos.empty:


        return pd.DataFrame(


            columns=[


                "id_corrida",


                "arquivo_extracao",


                "hash_extracao",


                "data_hora_extracao",


                "arquivo_resultados",


                "hash_resultados",


                "data_hora_resultados",


                "status_processamento",


                "mensagem_erro",


            ]


        )





    df = df_arquivos.copy()





    # Considera a data/hora do arquivo de resultados como referência para filtragem


    ts = pd.to_datetime(df[cols.result_file_datetime], errors="coerce")





    mask = pd.Series(True, index=df.index)


    if periodo_inicio is not None:


        mask &= ts >= periodo_inicio


    if periodo_fim is not None:


        mask &= ts <= periodo_fim





    df = df.loc[mask].copy()


    ts = ts.loc[mask]





    if df.empty:


        return pd.DataFrame(


            columns=[


                "id_corrida",


                "arquivo_extracao",


                "hash_extracao",


                "data_hora_extracao",


                "arquivo_resultados",


                "hash_resultados",


                "data_hora_resultados",


                "status_processamento",


                "mensagem_erro",


            ]


        )





    rel = pd.DataFrame(


        {


            "id_corrida": df[cols.run_id]


            if cols.run_id and cols.run_id in df.columns


            else None,


            "arquivo_extracao": df[cols.extraction_file_name],


            "hash_extracao": df[cols.extraction_file_hash]


            if cols.extraction_file_hash


            and cols.extraction_file_hash in df.columns


            else None,


            "data_hora_extracao": pd.to_datetime(


                df[cols.extraction_file_datetime], errors="coerce"


            ),


            "arquivo_resultados": df[cols.result_file_name],


            "hash_resultados": df[cols.result_file_hash]


            if cols.result_file_hash and cols.result_file_hash in df.columns


            else None,


            "data_hora_resultados": ts,


            "status_processamento": df[cols.processing_status],


            "mensagem_erro": df[cols.error_message]


            if cols.error_message and cols.error_message in df.columns


            else None,


        }


    )





    rel = rel.sort_values(


        by=["data_hora_resultados", "id_corrida"],


        kind="stable",


        na_position="last",


    )





    return rel.reset_index(drop=True)








# ============================================================================


# 6. RELATÓRIOS DE SUPORTE / DEPURAÇÃO (DESENVOLVIMENTO)


# ============================================================================








@dataclass


class DiffMotorConfig:


    """Colunas para Relatório de Diferenças entre Motor Específico e Motor Universal.





    sample_id    : ID da amostra (chave principal de comparação)


    result       : coluna de resultado interpretado


    ct           : coluna de Ct principal


    run_id       : ID da corrida (opcional, mas recomendável)


    well         : poço (opcional, se quiser granularidade por poço)


    flags        : coluna com flags ou observações (opcional)


    """





    sample_id: str


    result: str


    ct: str


    run_id: Optional[str] = None


    well: Optional[str] = None


    flags: Optional[str] = None








def gerar_relatorio_diferencas_motor(


    df_especifico: pd.DataFrame,


    df_universal: pd.DataFrame,


    cols: DiffMotorConfig,


    colunas_extra_comparar: Optional[Iterable[str]] = None,


) -> pd.DataFrame:


    """Relatório de Diferenças entre Motor Universal e Motor Específico.





    Faz um merge entre os dois DataFrames a partir das chaves


    (sample_id, run_id, well), quando existirem, e compara:





      - resultado


      - Ct


      - flags


      - colunas adicionais especificadas em `colunas_extra_comparar`





    Saída: uma linha por combinação com alguma divergência, contendo:





      - sample_id


      - id_corrida


      - poco


      - campo


      - valor_especifico


      - valor_universal


      - tipo_diferenca


    """


    if df_especifico.empty and df_universal.empty:


        return pd.DataFrame(


            columns=[


                "sample_id",


                "id_corrida",


                "poco",


                "campo",


                "valor_especifico",


                "valor_universal",


                "tipo_diferenca",


            ]


        )





    # Define chaves de merge


    merge_keys = [cols.sample_id]


    if cols.run_id:


        merge_keys.append(cols.run_id)


    if cols.well:


        merge_keys.append(cols.well)





    left = df_especifico.copy()


    right = df_universal.copy()





    # Adiciona sufixos para distinguir colunas


    merged = pd.merge(


        left,


        right,


        on=merge_keys,


        how="outer",


        suffixes=("_esp", "_uni"),


        indicator=True,


    )





    linhas: List[Dict[str, object]] = []





    # Conjunto de campos "base" a comparar


    campos_comparar = [cols.result, cols.ct]


    if cols.flags:


        campos_comparar.append(cols.flags)


    if colunas_extra_comparar:


        campos_comparar.extend(list(colunas_extra_comparar))





    # Remove duplicados preservando ordem


    campos_comparar = list(dict.fromkeys(campos_comparar))





    for _, row in merged.iterrows():


        # Registros que só existem em um dos lados


        if row["_merge"] == "left_only":


            tipo_diff = "presente_apenas_motor_especifico"


            for campo in campos_comparar:


                col_esp = (


                    f"{campo}_esp" if f"{campo}_esp" in merged.columns else campo


                )


                valor_esp = row.get(col_esp, None)


                if pd.isna(valor_esp):


                    continue


                linhas.append(


                    {


                        "sample_id": row.get(cols.sample_id),


                        "id_corrida": row.get(cols.run_id)


                        if cols.run_id


                        else None,


                        "poco": row.get(cols.well) if cols.well else None,


                        "campo": campo,


                        "valor_especifico": valor_esp,


                        "valor_universal": None,


                        "tipo_diferenca": tipo_diff,


                    }


                )


            continue





        if row["_merge"] == "right_only":


            tipo_diff = "presente_apenas_motor_universal"


            for campo in campos_comparar:


                col_uni = (


                    f"{campo}_uni" if f"{campo}_uni" in merged.columns else campo


                )


                valor_uni = row.get(col_uni, None)


                if pd.isna(valor_uni):


                    continue


                linhas.append(


                    {


                        "sample_id": row.get(cols.sample_id),


                        "id_corrida": row.get(cols.run_id)


                        if cols.run_id


                        else None,


                        "poco": row.get(cols.well) if cols.well else None,


                        "campo": campo,


                        "valor_especifico": None,


                        "valor_universal": valor_uni,


                        "tipo_diferenca": tipo_diff,


                    }


                )


            continue





        # _merge == 'both' -> comparar campo a campo


        for campo in campos_comparar:


            col_esp = (


                f"{campo}_esp" if f"{campo}_esp" in merged.columns else campo


            )


            col_uni = (


                f"{campo}_uni" if f"{campo}_uni" in merged.columns else campo


            )





            valor_esp = row.get(col_esp, None)


            valor_uni = row.get(col_uni, None)





            # Considera NaN ~ None


            if pd.isna(valor_esp):


                valor_esp = None


            if pd.isna(valor_uni):


                valor_uni = None





            if valor_esp == valor_uni:


                continue





            # Determina tipo simples de diferença


            if valor_esp is None and valor_uni is not None:


                tipo_diff = "valor_ausente_motor_especifico"


            elif valor_esp is not None and valor_uni is None:


                tipo_diff = "valor_ausente_motor_universal"


            else:


                tipo_diff = "valores_diferentes"





            linhas.append(


                {


                    "sample_id": row.get(cols.sample_id),


                    "id_corrida": row.get(cols.run_id) if cols.run_id else None,


                    "poco": row.get(cols.well) if cols.well else None,


                    "campo": campo,


                    "valor_especifico": valor_esp,


                    "valor_universal": valor_uni,


                    "tipo_diferenca": tipo_diff,


                }


            )





    if not linhas:


        return pd.DataFrame(


            columns=[


                "sample_id",


                "id_corrida",


                "poco",


                "campo",


                "valor_especifico",


                "valor_universal",


                "tipo_diferenca",


            ]


        )





    rel = pd.DataFrame(linhas)





    rel = rel.sort_values(


        by=["id_corrida", "sample_id", "poco", "campo"],


        kind="stable",


        na_position="last",


    )





    return rel.reset_index(drop=True)








# ---------------------------------------------------------------------------








def gerar_relatorio_validacao_csv(


    df_raw: pd.DataFrame,


    expected_columns: Iterable[str],


    expected_dtypes: Optional[Dict[str, str]] = None,


    df_descartadas: Optional[pd.DataFrame] = None,


) -> pd.DataFrame:


    """Relatório de Validação de Estrutura de CSVs.





    Gera um resumo de problemas de estrutura e tipos, incluindo:





      - colunas faltantes


      - colunas extras


      - tipos de dados incompatíveis (quando expected_dtypes for fornecido)


      - linhas descartadas (quando df_descartadas for fornecido)





    Saída: uma linha por ocorrência, com:





      - tipo_problema  ('coluna_faltante', 'coluna_extra',


                        'tipo_incompativel', 'linha_descartada')


      - coluna         (quando aplicável)


      - detalhe        (mensagem/resumo)


    """


    problemas: List[Dict[str, object]] = []





    expected_columns = list(expected_columns)


    colunas_real = list(df_raw.columns)





    # Colunas faltantes


    faltantes = [c for c in expected_columns if c not in colunas_real]


    for col in faltantes:


        problemas.append(


            {


                "tipo_problema": "coluna_faltante",


                "coluna": col,


                "detalhe": "Coluna esperada não encontrada no CSV.",


            }


        )





    # Colunas extras


    extras = [c for c in colunas_real if c not in expected_columns]


    for col in extras:


        problemas.append(


            {


                "tipo_problema": "coluna_extra",


                "coluna": col,


                "detalhe": "Coluna presente no CSV, mas não esperada.",


            }


        )





    # Tipos incompatíveis (checagem simples, baseada em expected_dtypes)


    # expected_dtypes pode usar, por ex.: "int", "float", "str", "datetime"


    if expected_dtypes:


        for col, tipo_esp in expected_dtypes.items():


            if col not in df_raw.columns:


                continue


            serie = df_raw[col]





            # Tentativa de conversão; se falhar em muitas linhas, marca como incompatível.


            tipo_esp_norm = str(tipo_esp).lower().strip()


            erros_tipo = 0


            n_total = int(len(serie))


            if n_total == 0:


                continue





            if tipo_esp_norm in ("int", "integer"):


                convertidos = pd.to_numeric(serie, errors="coerce").dropna()


                erros_tipo = n_total - int(len(convertidos))


            elif tipo_esp_norm in ("float", "double", "number"):


                convertidos = pd.to_numeric(serie, errors="coerce").dropna()


                erros_tipo = n_total - int(len(convertidos))


            elif tipo_esp_norm in ("datetime", "date", "timestamp"):


                convertidos = pd.to_datetime(serie, errors="coerce").dropna()


                erros_tipo = n_total - int(len(convertidos))


            else:


                # Para strings, apenas verificamos se existem muitos NaN


                if serie.isna().sum() > 0.3 * n_total:


                    erros_tipo = int(serie.isna().sum())





            if erros_tipo > 0:


                problemas.append(


                    {


                        "tipo_problema": "tipo_incompativel",


                        "coluna": col,


                        "detalhe": (


                            "Possível incompatibilidade: "


                            f"{erros_tipo} valores não coerentes com o tipo esperado '{tipo_esp}'."


                        ),


                    }


                )





    # Linhas descartadas (quando já houver um DataFrame separado com elas)


    if df_descartadas is not None and not df_descartadas.empty:


        n_desc = int(len(df_descartadas))


        problemas.append(


            {


                "tipo_problema": "linha_descartada",


                "coluna": None,


                "detalhe": f"{n_desc} linha(s) descartada(s) durante o pré-processamento.",


            }


        )





    if not problemas:


        return pd.DataFrame(columns=["tipo_problema", "coluna", "detalhe"])





    rel = pd.DataFrame(problemas)





    rel = rel.sort_values(


        by=["tipo_problema", "coluna"], kind="stable", na_position="last"


    )





    return rel.reset_index(drop=True)


