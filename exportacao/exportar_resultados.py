# FileName: /Integragal/exportacao/exportar_resultados.py


import os

from dataclasses import dataclass
from typing import Any, Dict, Optional

from datetime import datetime


from tkinter import filedialog, messagebox





import matplotlib.pyplot as plt


import pandas as pd





from services.exam_registry import get_exam_cfg
from services.core.config_service import config_service
from domain.error_codes import ErrorCode


from utils.logger import registrar_log  # Importa o logger centralizado
from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, open_with_retry
from utils.selecionado_normalizer import _normalizar_selecionado


@dataclass(frozen=True)
class GalExportCoreResult:
    dataframe: pd.DataFrame
    detectable_counts: Dict[str, int]
    log_file_path: str


def _resolve_exam_cfg(exam_cfg: Any = None, exame: Optional[str] = None):
    if exam_cfg is not None:
        return exam_cfg
    if exame:
        try:
            return get_exam_cfg(exame)
        except Exception:
            return None
    return None


def _is_control_sample(sample: str, codigo: str, controles_cn_cp: list[str]) -> bool:
    for cc in controles_cn_cp:
        if cc and (cc in sample or cc in codigo):
            return True
    return (
        "CN" in sample
        or "CN" in codigo
        or "CP" in sample
        or "CP" in codigo
        or "NEGATIVO" in sample
        or "POSITIVO" in codigo
    )


def exportar_resultados_core(
    df_processado: pd.DataFrame,
    lote_kit: str,
    mapeamento_alvo: dict,
    mapeamento_saida: dict,
    colunas_modelo: list,
    *,
    exam_cfg: Any = None,
    exame: Optional[str] = None,
) -> GalExportCoreResult:
    """Core puro da exportacao GAL sem acoplamento com UI/dialogs."""
    if df_processado is None or not isinstance(df_processado, pd.DataFrame):
        raise ValueError("DataFrame de resultados invalido ou nao fornecido.")
    if mapeamento_alvo is None or not isinstance(mapeamento_alvo, dict):
        raise ValueError("Mapeamento de alvo invalido ou nao fornecido.")
    if mapeamento_saida is None or not isinstance(mapeamento_saida, dict):
        raise ValueError("Mapeamento de saida invalido ou nao fornecido.")
    if colunas_modelo is None or not isinstance(colunas_modelo, (list, tuple)):
        raise ValueError("Modelo de colunas invalido ou nao fornecido.")
    if "Selecionado" not in df_processado.columns:
        raise ValueError("Coluna 'Selecionado' nao encontrada no DataFrame.")
    if "Sample" not in df_processado.columns:
        raise ValueError("Coluna 'Sample' nao encontrada no DataFrame.")

    cfg = _resolve_exam_cfg(exam_cfg=exam_cfg, exame=exame)
    controles_cn_cp: list[str] = []
    if cfg is not None:
        try:
            controles = cfg.controles or {}
            controles_cn_cp = [str(c).upper() for c in controles.keys()]
        except Exception:
            controles_cn_cp = []

    processing_end_date = datetime.now().strftime("%d/%m/%Y")
    try:
        paths = config_service.get_paths()
    except Exception:
        paths = {}
    log_dir = paths.get("logs_dir")
    if not log_dir:
        log_file = paths.get("log_file")
        if log_file:
            log_dir = os.path.dirname(log_file)
    if not log_dir:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "resultados_por_amostra.txt")

    detectable_counts_for_plot = {col_csv: 0 for col_csv in mapeamento_alvo.values()}
    lines_to_export: list[dict[str, Any]] = []

    policy = RetryPolicy.from_env()
    with CSVFileLock(log_file_path), open_with_retry(
        log_file_path, "w", encoding="utf-8", policy=policy
    ) as log_file:
        for _, row in df_processado.iterrows():
            is_selected = row.get("Selecionado", False)
            is_selected = _normalizar_selecionado(is_selected)
            if not is_selected:
                continue

            sample = str(row.get("Sample", "")).upper()
            codigo = str(row.get("Codigo", "")).upper() if "Codigo" in row else ""
            if _is_control_sample(sample, codigo, controles_cn_cp):
                log_file.write(f"Skipped control: {sample} ({codigo})\n")
                continue

            csv_line = {col_name: "" for col_name in colunas_modelo}
            if "codigoAmostra" in colunas_modelo:
                csv_line["codigoAmostra"] = row["Sample"]
            if "registroInterno" in colunas_modelo:
                csv_line["registroInterno"] = row["Sample"]
            if "loteKit" in colunas_modelo:
                csv_line["loteKit"] = lote_kit
            if "dataProcessamentoFim" in colunas_modelo:
                csv_line["dataProcessamentoFim"] = processing_end_date

            for internal_col, csv_col in mapeamento_alvo.items():
                if csv_col not in colunas_modelo:
                    continue
                internal_result = row.get(internal_col, "")
                mapped_value = mapeamento_saida.get(internal_result, "")
                csv_line[csv_col] = mapped_value
                if mapped_value == "1":
                    detectable_counts_for_plot[csv_col] = (
                        detectable_counts_for_plot.get(csv_col, 0) + 1
                    )

            for key, value in {
                "paciente": "",
                "exame": str(getattr(cfg, "gal_exame_codigo", "VRSRT")) if cfg else "VRSRT",
                "metodo": "RTTR",
                "kit": str(getattr(cfg, "kit_codigo", "1175")) if cfg else "1175",
                "painel": str(getattr(cfg, "panel_tests_id", "12")) if cfg else "12",
                "resultado": "",
            }.items():
                if key in colunas_modelo and not csv_line.get(key):
                    csv_line[key] = value

            lines_to_export.append(csv_line)
            log_file.write(f"Amostra {csv_line.get('codigoAmostra', '')}:\n")
            for key in colunas_modelo:
                log_file.write(f"  {key}: {csv_line.get(key, '')}\n")
            log_file.write("\n")

    if not lines_to_export:
        raise ValueError("Nenhuma amostra valida selecionada para exportacao.")

    df_final_csv = pd.DataFrame(lines_to_export, columns=colunas_modelo)
    return GalExportCoreResult(
        dataframe=df_final_csv,
        detectable_counts=detectable_counts_for_plot,
        log_file_path=log_file_path,
    )


def _executar_exportacao_gal_ui(
    df_processado: pd.DataFrame,
    lote_kit: str,
    mapeamento_alvo: dict,
    mapeamento_saida: dict,
    colunas_modelo: list,
    colunas_humanas: dict = None,
    exam_cfg: Any = None,
    exame: str = None,
) -> None:
    """Adapter UI do core de exportacao GAL."""
    _log_runtime_usage("adapter_invoked")

    def _safe_messagebox(method: str, title: str, message: str) -> None:
        try:
            getattr(messagebox, method)(title, message)
        except Exception:
            registrar_log(
                "Exportacao GAL UI",
                f"Dialogo '{method}' indisponivel em modo headless: {title} - {message}",
                level="WARNING",
            )

    try:
        core = exportar_resultados_core(
            df_processado=df_processado,
            lote_kit=lote_kit,
            mapeamento_alvo=mapeamento_alvo,
            mapeamento_saida=mapeamento_saida,
            colunas_modelo=colunas_modelo,
            exam_cfg=exam_cfg,
            exame=exame,
        )
    except ValueError as exc:
        _safe_messagebox("showwarning", "Exportacao GAL", str(exc))
        registrar_log(
            "Exportacao GAL",
            str(exc),
            level="WARNING",
            error_code=ErrorCode.GAL_PAYLOAD_INVALID,
        )
        _log_runtime_usage("core_validation_error", error_code=ErrorCode.GAL_PAYLOAD_INVALID)
        return
    except Exception as exc:
        _safe_messagebox("showerror", "Erro de Exportacao", f"Falha no core de exportacao: {exc}")
        registrar_log(
            "Erro de Exportacao",
            str(exc),
            level="ERROR",
            error_code=ErrorCode.GAL_INTEGRATION_ERROR,
        )
        _log_runtime_usage("core_error", error_code=ErrorCode.GAL_INTEGRATION_ERROR)
        return

    output_filepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        title="Salvar CSV no Formato GAL",
    )

    if not output_filepath:
        registrar_log("Exportacao GAL", "Exportacao cancelada pelo usuario.", level="INFO")
        _log_runtime_usage("cancelled")
        return

    try:
        policy = RetryPolicy.from_env()
        with CSVFileLock(output_filepath), open_with_retry(
            output_filepath,
            "w",
            newline="",
            encoding="utf-8",
            policy=policy,
        ) as handle:
            core.dataframe.to_csv(handle, sep=";", index=False)

        msg_to_user = (
            f"Arquivo salvo em: {output_filepath}\n"
            f"Log salvo em: {core.log_file_path}\n\n"
            "Contagem de Detectaveis (apenas amostras validas):\n"
        )
        sorted_targets = sorted(
            core.detectable_counts.keys(),
            key=lambda k: colunas_humanas.get(k, k) if colunas_humanas else k,
        )
        for csv_col_name in sorted_targets:
            human_name = (
                colunas_humanas.get(csv_col_name, csv_col_name)
                if colunas_humanas
                else csv_col_name
            )
            count_val = core.detectable_counts.get(csv_col_name, 0)
            msg_to_user += f"{human_name}: {count_val} detectaveis\n"

        _safe_messagebox("showinfo", "Exportacao Concluida", msg_to_user)
        _gerar_grafico_detectaveis(core.detectable_counts, colunas_humanas)
        _log_runtime_usage(
            "success",
            rows=len(core.dataframe),
            output_path=output_filepath,
        )
    except Exception as exc:
        registrar_log(
            "Erro na Exportacao CSV",
            str(exc),
            level="ERROR",
            error_code=ErrorCode.GAL_INTEGRATION_ERROR,
        )
        _log_runtime_usage("save_error", error_code=ErrorCode.GAL_INTEGRATION_ERROR)
        _safe_messagebox(
            "showerror",
            "Erro de Exportacao",
            f"Ocorreu um erro ao salvar o arquivo CSV: {exc}",
        )


def _log_runtime_usage(event: str, **payload: Any) -> None:
    """Registra telemetria de uso runtime para funcoes monitoradas."""
    parts = [f"feature=exportar_resultados_gal", f"event={event}"]
    for key, value in payload.items():
        parts.append(f"{key}={value}")
    registrar_log("RuntimeUsage", " ".join(parts), level="INFO")







def exportar_resultados_gal(


    df_processado: pd.DataFrame,


    lote_kit: str,


    mapeamento_alvo: dict,


    mapeamento_saida: dict,


    colunas_modelo: list,


    colunas_humanas: dict = None,


    exam_cfg: any = None,


    exame: str = None,


) -> None:


    """


    Exporta os resultados processados para um arquivo CSV no formato GAL.


    Parâmetros:


        df_processado: DataFrame com os resultados processados.


        lote_kit: Código do lote do kit utilizado.


        mapeamento_alvo: Dicionário mapeando nomes de colunas de resultado internos para colunas do CSV.


        mapeamento_saida: Dicionário mapeando valores de resultado (e.g. 'Detectável', 'ND') para códigos CSV ('1','2','3').


        colunas_modelo: Lista contendo o modelo de colunas do CSV de saída (formato GAL).


        colunas_humanas: (Opcional) Dicionário para mapear nomes de colunas CSV para nomes legíveis (usado no gráfico).


        exam_cfg: (Opcional) Config do exame (ExamConfig) para validações de controles


        exame: (Opcional) Nome do exame (para buscar config se exam_cfg não fornecido)


    """


    _log_runtime_usage("function_invoked", source="exportacao.exportar_resultados")
    try:
        from services.suspected_orphan_telemetry import log_suspected_orphan_usage

        log_suspected_orphan_usage(
            "exportacao.exportar_resultados.exportar_resultados_gal",
            rows=int(len(df_processado)) if hasattr(df_processado, "__len__") else 0,
        )
    except Exception:
        pass

    # Fluxo novo (Fase 1 AN-01): UI adapter -> core desacoplado.
    # Mantemos o corpo legado abaixo apenas como fallback de rollback tecnico.
    return _executar_exportacao_gal_ui(
        df_processado=df_processado,
        lote_kit=lote_kit,
        mapeamento_alvo=mapeamento_alvo,
        mapeamento_saida=mapeamento_saida,
        colunas_modelo=colunas_modelo,
        colunas_humanas=colunas_humanas,
        exam_cfg=exam_cfg,
        exame=exame,
    )

    # Carrega config do exame se não fornecida


    if not exam_cfg and exame:


        try:


            exam_cfg = get_exam_cfg(exame)


        except Exception:


            exam_cfg = None


    


    # Extrai controles do registry se disponível


    controles_cn_cp = []


    if exam_cfg:


        try:


            controles = exam_cfg.controles or {}


            controles_cn_cp = [str(c).upper() for c in controles.keys()]


        except Exception:


            controles_cn_cp = []


    


    # Verificações iniciais de validade dos parâmetros


    if df_processado is None or not isinstance(df_processado, pd.DataFrame):


        registrar_log(


            "Erro de Exportação",


            "DataFrame de resultados inválido ou não fornecido.",


            level="ERROR",


        )


        messagebox.showerror(


            "Erro de Exportação",


            "DataFrame de resultados inválido ou não fornecido.",


        )


        return


    if mapeamento_alvo is None or not isinstance(mapeamento_alvo, dict):


        registrar_log(


            "Erro de Exportação",


            "Mapeamento de alvo inválido ou não fornecido.",


            level="ERROR",


        )


        messagebox.showerror(


            "Erro de Exportação", "Mapeamento de alvo inválido ou não fornecido."


        )


        return


    if mapeamento_saida is None or not isinstance(mapeamento_saida, dict):


        registrar_log(


            "Erro de Exportação",


            "Mapeamento de saída inválido ou não fornecido.",


            level="ERROR",


        )


        messagebox.showerror(


            "Erro de Exportação", "Mapeamento de saída inválido ou não fornecido."


        )


        return


    if colunas_modelo is None or not isinstance(colunas_modelo, (list, tuple)):


        registrar_log(


            "Erro de Exportação",


            "Modelo de colunas inválido ou não fornecido.",


            level="ERROR",


        )


        messagebox.showerror(


            "Erro de Exportação", "Modelo de colunas inválido ou não fornecido."


        )


        return





    # Verificar se há coluna 'Selecionado' e coluna 'Sample' no DataFrame


    if "Selecionado" not in df_processado.columns:


        registrar_log(


            "Erro de Exportação",


            "Coluna 'Selecionado' não encontrada no DataFrame. Nenhuma amostra será exportada.",


            level="WARNING",


        )


        messagebox.showwarning(


            "Coluna Ausente",


            "A coluna 'Selecionado' não foi encontrada nos resultados. Nenhuma amostra será exportada.",


        )


        return


    if "Sample" not in df_processado.columns:


        registrar_log(


            "Erro de Exportação",


            "Coluna 'Sample' não encontrada no DataFrame.",


            level="ERROR",


        )


        messagebox.showerror(


            "Erro de Exportação",


            "Não foi possível encontrar a coluna 'Sample' no DataFrame de resultados.",


        )


        return





    # Preparação de variáveis para exportação


    processing_end_date = datetime.now().strftime("%d/%m/%Y")


    # O log de resultados por amostra pode ser salvo em um subdiretório de logs


    try:
        paths = config_service.get_paths()
    except Exception:
        paths = {}
    log_dir = paths.get("logs_dir")
    if not log_dir:
        log_file = paths.get("log_file")
        if log_file:
            log_dir = os.path.dirname(log_file)
    if not log_dir:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")


    os.makedirs(log_dir, exist_ok=True)  # Garante que o diretório de logs exista


    log_file_path = os.path.join(log_dir, "resultados_por_amostra.txt")





    # Inicializa contagem de detectáveis para cada coluna de destino do CSV


    detectable_counts_for_plot = {col_csv: 0 for col_csv in mapeamento_alvo.values()}





    lines_to_export = []


    try:


        policy = RetryPolicy.from_env()
        with CSVFileLock(log_file_path), open_with_retry(
            log_file_path, "w", encoding="utf-8", policy=policy
        ) as log_file:


            # Itera sobre cada linha do DataFrame processado


            for _, row in df_processado.iterrows():


                try:


                    # Verifica se a amostra está selecionada (marca '✓' na coluna 'Selecionado')


                    # ou se a coluna 'Selecionado' é booleana e True


                    is_selected = row.get("Selecionado", False)


                    is_selected = _normalizar_selecionado(is_selected)





                    if not is_selected:


                        continue


                    


                    # Filtra CN/CP (controles) automaticamente baseado em registry ou hardcoded


                    sample = str(row.get("Sample", "")).upper()


                    codigo = str(row.get("Codigo", "")).upper() if "Codigo" in row else ""


                    


                    # Detecta controles (CN/CP) automaticamente


                    is_control = False


                    for cc in controles_cn_cp:


                        if cc in sample or cc in codigo:


                            is_control = True


                            break


                    


                    # Se não houver config de controles no registry, usa heurística padrão


                    if not is_control:


                        if ("CN" in sample or "CN" in codigo or 


                            "CP" in sample or "CP" in codigo or


                            "NEGATIVO" in sample or "POSITIVO" in codigo):


                            is_control = True


                    


                    # Pula controles (não exporta)


                    if is_control:


                        log_file.write(f"Skipped control: {sample} ({codigo})\n")


                        continue





                    # Prepara dicionário para a linha de CSV, iniciando com colunas modelo em branco


                    csv_line = {col_name: "" for col_name in colunas_modelo}





                    # Preencher dados básicos, se estas colunas estiverem presentes no modelo


                    if "codigoAmostra" in colunas_modelo:


                        csv_line["codigoAmostra"] = row["Sample"]


                    if "registroInterno" in colunas_modelo:


                        csv_line["registroInterno"] = row["Sample"]


                    if "loteKit" in colunas_modelo:


                        csv_line["loteKit"] = lote_kit


                    if "dataProcessamentoFim" in colunas_modelo:


                        csv_line["dataProcessamentoFim"] = processing_end_date





                    # Mapear resultados para colunas do CSV conforme o mapeamento fornecido


                    for internal_col, csv_col in mapeamento_alvo.items():


                        if csv_col not in colunas_modelo:


                            continue


                        internal_result = row.get(internal_col, "")


                        mapped_value = mapeamento_saida.get(internal_result, "")


                        csv_line[csv_col] = mapped_value


                        if mapped_value == "1":


                            detectable_counts_for_plot[csv_col] = (


                                detectable_counts_for_plot.get(csv_col, 0) + 1


                            )





                    # Adicionar valores padrão se as colunas existirem no modelo e não foram preenchidas


                    for key, value in {
                        "paciente": "",
                        "exame": str(getattr(exam_cfg, "gal_exame_codigo", "VRSRT")) if exam_cfg else "VRSRT",
                        "metodo": "RTTR",
                        "kit": str(getattr(exam_cfg, "kit_codigo", "1175")) if exam_cfg else "1175",
                        "painel": str(getattr(exam_cfg, "panel_tests_id", "12")) if exam_cfg else "12",
                        "resultado": "",
                    }.items():
                        if key in colunas_modelo and not csv_line.get(key):
                            csv_line[key] = value





                    # Adicionar a linha pronta na lista de exportação


                    lines_to_export.append(csv_line)





                    # Registrar detalhes da linha no log


                    log_file.write(f"Amostra {csv_line.get('codigoAmostra','')}:\n")


                    for key in colunas_modelo:


                        log_file.write(f"  {key}: {csv_line.get(key, '')}\n")


                    log_file.write("\n")





                except Exception as e_row:


                    # Se ocorrer erro em alguma linha, registra no log e continua


                    amostra_id = row.get("Sample", "")


                    registrar_log(


                        "Erro na Exportação",


                        f"Amostra {amostra_id} não exportada: {e_row}",


                        level="ERROR",


                    )


                    continue





    except Exception as e_file:


        registrar_log(


            "Erro na Exportação", f"Falha ao criar log: {e_file}", level="ERROR"


        )


        messagebox.showerror(


            "Erro de Exportação",


            f"Ocorreu um erro ao criar o log de exportação: {e_file}",


        )


        return





    # Verifica se há alguma amostra válida para exportar


    if not lines_to_export:


        messagebox.showwarning(


            "Nenhuma Amostra",


            "Nenhuma amostra válida ('Selecionado' com '✓') para exportação.",


        )


        return





    # Criar DataFrame final com as linhas exportadas


    df_final_csv = pd.DataFrame(lines_to_export, columns=colunas_modelo)





    # Solicita local para salvar o arquivo CSV


    output_filepath = filedialog.asksaveasfilename(


        defaultextension=".csv",


        filetypes=[("CSV files", "*.csv")],


        title="Salvar CSV no Formato GAL",


    )





    if output_filepath:


        try:


            # Salvar CSV com codificação UTF-8 e separador ponto-e-vírgula


            policy = RetryPolicy.from_env()
            with CSVFileLock(output_filepath):
                with open_with_retry(
                    output_filepath,
                    "w",
                    newline="",
                    encoding="utf-8",
                    policy=policy,
                ) as handle:
                    df_final_csv.to_csv(handle, sep=";", index=False)


            registrar_log(


                "Exportação CSV Concluída", f"Arquivo salvo em: {output_filepath}"


            )





            # Construir mensagem de resumo com contagem de detectáveis por agravo


            msg_to_user = (


                f"Arquivo salvo em: {output_filepath}\n"


                f"Log salvo em: {log_file_path}\n\n"


                "Contagem de Detectáveis (apenas amostras VÁLIDAS):\n"


            )


            # Ordena alvos para apresentação (pelo nome humano, se disponível)


            sorted_targets = sorted(


                detectable_counts_for_plot.keys(),


                key=lambda k: colunas_humanas.get(k, k) if colunas_humanas else k,


            )


            for csv_col_name in sorted_targets:


                human_name = (


                    colunas_humanas.get(csv_col_name, csv_col_name)


                    if colunas_humanas


                    else csv_col_name


                )


                count_val = detectable_counts_for_plot.get(csv_col_name, 0)


                msg_to_user += f"{human_name}: {count_val} detectáveis\n"





            messagebox.showinfo("Exportação Concluída", msg_to_user)


            # Gerar gráfico de barras para detectáveis


            _gerar_grafico_detectaveis(detectable_counts_for_plot, colunas_humanas)





        except Exception as e_save:


            registrar_log("Erro na Exportação CSV", str(e_save), level="ERROR")


            messagebox.showerror(


                "Erro de Exportação",


                f"Ocorreu um erro ao salvar o arquivo CSV: {e_save}",


            )


    else:


        # Usuário cancelou a operação de salvar


        messagebox.showwarning("Cancelado", "Exportação cancelada pelo usuário.")








def _gerar_grafico_detectaveis(


    detectable_counts: dict, colunas_humanas: dict = None


) -> None:


    """


    Gera um gráfico de barras simples mostrando a quantidade de amostras detectáveis por agravo.


    Parâmetros:


        detectable_counts: Dicionário de contagem de amostras detectáveis por coluna do CSV.


        colunas_humanas: (Opcional) Mapeamento de nomes de coluna para nomes legíveis.


    """


    if not detectable_counts or all(v == 0 for v in detectable_counts.values()):


        registrar_log(


            "Gráfico de Detecção",


            "Nenhum alvo detectável para gerar o gráfico.",


            level="INFO",


        )


        messagebox.showinfo(


            "Gráfico de Detecção", "Nenhum alvo detectável para gerar o gráfico."


        )


        return





    # Filtra apenas alvos com contagem maior que zero


    plot_data = {k: v for k, v in detectable_counts.items() if v > 0}


    plot_labels = [


        colunas_humanas.get(k, k) if colunas_humanas else k for k in plot_data.keys()


    ]


    plot_values = list(plot_data.values())





    plt.figure(figsize=(10, 5))


    plt.bar(plot_labels, plot_values, color="skyblue")


    plt.title("Número de Amostras Detectáveis por Agravo")


    plt.xlabel("Agravo")


    plt.ylabel("Quantidade")


    plt.xticks(rotation=0)


    plt.tight_layout()


    plt.show()


    registrar_log(


        "Gráfico de Detecção", "Gráfico de detectáveis gerado.", level="INFO"


    )


