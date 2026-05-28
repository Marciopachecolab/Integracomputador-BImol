"""
Janela única com abas: Análise + Mapa da Placa
Solução para eliminar problemas com múltiplos CTkToplevel e travamentos.
Baseado na recomendação do especialista em Tkinter/CustomTkinter.
"""

from __future__ import annotations
import customtkinter as ctk
import pandas as pd
from tkinter import messagebox, ttk
from ui.theme import Theme
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
import math
import time

from ui.modules.plate_viewer import PlateModel, PlateView
from utils.logger import registrar_log
from utils.after_mixin import AfterManagerMixin
from ui.components.scientific_data_grid import ScientificDataGrid
from ui.components.full_analysis_grid import FullAnalysisGrid
from application.contracts.ui_view_models import DataGridRowViewModel
from utils.ct_formatter import formatar_ct_display  # FASE 2: Formatação CT
from utils.gui_utils import center_window, safe_destroy_ctk_toplevel
from utils.text_normalizer import _normalize_col_key, repair_mojibake_text
from utils.text_result_classifier import classify_result_text
from config.ui_theme import obter_cor_resultado  # FASE 3: Cores resultados
from config.ui_theme import obter_cor_resultado  # FASE 3: Cores resultados
# from config.business_rules import ... (REMOVED - Logic Centralized)
from services.analysis.logic_engine import classificar_ct
from services.core.query_latency import record_query_latency, summarize_query_latency
from services.core.runtime_flags import is_plate_sync_use_case_enabled
from application.sync_plate_to_analysis import sync_plate_to_analysis
from domain.error_codes import ErrorCode
from config.column_constants import listar_colunas_alvo

if TYPE_CHECKING:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def _build_exam_runtime_profile(nome_exame: str) -> Dict:
    """Carrega o perfil de limiares de CT por alvo para o exame informado.

    Retorna dict vazio se o exame não for encontrado (fallback para regra global).
    """
    try:
        from services.exam_registry import get_exam_cfg
        from services.analysis.analysis_runtime_contract import build_runtime_rule_profile_from_cfg
        cfg = get_exam_cfg(nome_exame)
        faixas = cfg.faixas_ct or {}
        return build_runtime_rule_profile_from_cfg(
            cfg,
            exam_name=nome_exame,
            rp_min_fallback=float(faixas.get("rp_min", 15.0)),
            rp_max_fallback=float(faixas.get("rp_max", 35.0)),
        )
    except Exception:
        return {}


_ALVOS_CT = {
    "SC2", "FLUA", "FLUB", "RSV", "ADENO", "METAP", "RINO",
    "PARAINFLUENZA", "PARECHOVIRUS", "ENTEROVIRUS", "BOCAVIRUS",
    "MYCOPLASMA", "RP", "RP_1", "RP_2",
}

_LARGURAS = {
    "poco": 55,
    "amostra": 140,
    "codigo": 100,
    "resultado": 90,
    "ct": 70,
    "geral": 105,
    "default": 100,
}


def _largura_coluna(col: str) -> int:
    c = col.lower()
    if "poco" in c or "poço" in c:
        return _LARGURAS["poco"]
    if "amostra" in c:
        return _LARGURAS["amostra"]
    if "codigo" in c or "código" in c:
        return _LARGURAS["codigo"]
    if c == "resultado_geral":
        return _LARGURAS["geral"]
    if c.startswith("resultado_"):
        return _LARGURAS["resultado"]
    if c.startswith("ct_") or col.upper() in _ALVOS_CT:
        return _LARGURAS["ct"]
    return _LARGURAS["default"]


def _abreviar_cabecalho(col: str) -> str:
    c = col.lower()
    if c == "resultado_geral":
        return "Geral"
    if c.startswith("resultado_"):
        return "Res. " + col[len("resultado_"):].upper()
    if c.startswith("ct_"):
        return "CT " + col[3:].upper()
    return repair_mojibake_text(col)


def _norm_res_label(val: str) -> str:
    """Normaliza rotulos de resultado para comparacao."""
    token = classify_result_text(val)
    if token == "INV":
        return "invalido"
    if token == "INC":
        return "inconclusivo"
    if token == "DET":
        return "positivo"
    if token == "ND":
        return "negativo"
    return str(val).strip().upper()


def _normalizar_token_operacional(value: Any) -> str:
    """Normaliza valores operacionais para comparações de seleção."""
    return _normalize_col_key(repair_mojibake_text(value))


def _find_column_by_normalized_key(df: pd.DataFrame, accepted_keys: set[str]) -> Optional[str]:
    """Retorna a coluna cujo nome normalizado está entre as chaves aceitas."""
    for column in df.columns:
        if _normalize_col_key(column) in accepted_keys:
            return str(column)
    return None


def _is_controle_operacional(row: pd.Series) -> bool:
    """Identifica linhas de controle por Amostra ou Codigo."""
    tokens = [
        _normalizar_token_operacional(row.get("Amostra", "")),
        _normalizar_token_operacional(row.get("Codigo", "")),
    ]
    return any(
        token in {"cn", "cp"}
        or token.startswith("cn")
        or token.startswith("cp")
        or "controleneg" in token
        or "controlepos" in token
        for token in tokens
        if token
    )


def _rp_operacional_valido(value: Any) -> bool:
    return _normalizar_token_operacional(value) in {"valido", "valida"}


def _status_placa_operacional_valido(value: Any) -> bool:
    return _normalizar_token_operacional(value) in {"valido", "valida"}


def _sugestao_repeticao_negativa(value: Any) -> bool:
    return _normalizar_token_operacional(value) in {"nao", "n"}


def _formatar_valor_celula(col_name: str, value: Any) -> str:
    """
    Formata valor de célula para exibição.
    
    FASE 2: Formata CTs usando ct_formatter para converter "Undetermined" → "Und"
    
    Args:
        col_name: Nome da coluna
        value: Valor a formatar
        
    Returns:
        String formatada para exibição
    """
    # Colunas que contêm valores CT
    colunas_ct = [
        "SC2", "FLUA", "FLUB", "RSV", "ADENO", "METAP", "RINO", 
        "PARAINFLUENZA", "PARECHOVIRUS", "ENTEROVIRUS", "BOCAVIRUS", 
        "MYCOPLASMA", "RP", "RP_1", "RP_2"
    ]
    
    # Se é coluna CT, aplicar formatação especializada
    if col_name.upper() in colunas_ct:
        return repair_mojibake_text(formatar_ct_display(value))
    
    # Outros valores: conversão padrão
    return repair_mojibake_text(str(value))


_TOKEN_TO_TAG = {"INV": "invalido", "INC": "indeterminado", "DET": "detectado", "ND": "nao_detectavel"}


def _determinar_tag_resultado(row: pd.Series) -> str:
    """Determina tag de cor para uma linha delegando a classify_result_text (INV>INC>ND>DET)."""
    from utils.text_result_classifier import classify_result_text

    # Usar Resultado_geral como fonte primária (calculado pelo domínio, sempre correto)
    if "Resultado_geral" in row.index:
        token = classify_result_text(row["Resultado_geral"])
        if token is not None:
            return _TOKEN_TO_TAG.get(token, "nao_detectavel")

    # Fallback: varrer colunas individuais na ordem de prioridade INV>INC>DET>ND
    colunas_resultado = [col for col in row.index
                         if (col.startswith("Resultado_") or col.startswith("Res_"))
                         and "GERAL" not in col.upper()]

    pioridade: dict[str, str] = {}
    _ordem = ["INV", "INC", "DET", "ND"]
    for col in colunas_resultado:
        token = classify_result_text(row[col])
        if token and token not in pioridade:
            pioridade[token] = _TOKEN_TO_TAG.get(token, "nao_detectavel")

    for t in _ordem:
        if t in pioridade:
            return pioridade[t]

    return "nao_detectavel"


class JanelaAnaliseCompleta(AfterManagerMixin, ctk.CTkFrame):
    """
    Janela única com abas: Análise + Mapa da Placa.
    Elimina necessidade de CTkToplevel aninhados e resolve travamentos.
    """

    def __init__(
        self,
        root,
        dataframe: pd.DataFrame,
        status_corrida: str,
        num_placa: str,
        data_placa_formatada: str,
        agravos: List[str],
        usuario_logado: str = "Desconhecido",
        exame: str = "",
        lote: str = "",
        arquivo_corrida: str = "",
        bloco_tamanho: int = 1,
        numero_extracao: str = "",  # FASE 4: Numero da extracao (C8)
        host_frame: Optional[ctk.CTkFrame] = None,
        on_close_callback: Optional[Callable[[], None]] = None,
    ):
        self._is_page_mode = host_frame is not None
        self._window: Optional[ctk.CTkToplevel] = None
        self._on_close_callback = on_close_callback
        self._plate_saved_subscribed = False
        self.main_window = root

        if self._is_page_mode:
            super().__init__(master=host_frame)
            self.pack(fill="both", expand=True)
        else:
            self._window = ctk.CTkToplevel(master=root)
            super().__init__(master=self._window)
            self.pack(fill="both", expand=True)

        # Estado compartilhado entre abas
        self.df_analise = dataframe.copy()
        self.plate_model: Optional[PlateModel] = None
        self._grafico_window: Optional[ctk.CTkToplevel] = None
        self._grafico_canvas: Optional["FigureCanvasTkAgg"] = None

        # Metadados
        self.status_corrida = status_corrida
        self.num_placa = num_placa
        self.data_placa_formatada = data_placa_formatada
        self.agravos = agravos
        self.usuario_logado = usuario_logado
        self.exame = exame
        self.lote = lote
        self.arquivo_corrida = arquivo_corrida
        self.bloco_tamanho = bloco_tamanho
        self.numero_extracao = numero_extracao  # FASE 4

        # Perfil de limiares CT por alvo carregado do JSON do exame
        self._runtime_profile: Dict = _build_exam_runtime_profile(self.exame)

        # ? REGRESSAO #1: Normalizar colunas com busca parcial (suporta 'Poco(s)', etc.)
        self._normalizar_colunas_df(self.df_analise)

        # ? Criar coluna Codigo se nao existir (usar Amostra como fallback)
        if 'Codigo' not in self.df_analise.columns:
            if 'Amostra' in self.df_analise.columns:
                self.df_analise['Codigo'] = self.df_analise['Amostra']
                registrar_log("Normalizacao", "Coluna 'Codigo' criada a partir de 'Amostra'", "INFO")
            else:
                # Ultimo recurso: criar coluna vazia
                self.df_analise['Codigo'] = ''
                registrar_log("Normalizacao", "AVISO: Coluna 'Codigo' criada vazia (Amostra ausente)", "WARNING")

        # Adicionar coluna de selecao se nao existir
        if "Selecionado" not in self.df_analise.columns:
            # ? ETAPA 2: Pre-selecionar TODOS (Opcao A escolhida pelo usuario)
            # Todas amostras ficam pre-selecionadas, incluindo invalidos
            selecoes = [True] * len(self.df_analise)
            self.df_analise.insert(0, "Selecionado", selecoes)
            registrar_log("Selecao", f"{len(selecoes)} amostras pre-selecionadas (TODAS)", "DEBUG")

        if self._window is not None:
            self._set_window_title("RT-PCR - Analise Completa")
            self._window.transient(root)
            self._window.grab_set()
            self._window.resizable(True, True)

            # Definir tamanho (85% da tela)
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            window_width = int(screen_width * 0.85)
            window_height = int(screen_height * 0.85)
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            self._window.geometry(f"{window_width}x{window_height}+{x}+{y}")
            self._window.state('zoomed')
        else:
            if hasattr(self.main_window, "state"):
                self.after(100, lambda: self.main_window.state('zoomed'))

        # ? CORRECAO #2: Subscrever ao Event Bus para receber evento de salvamento do mapa
        self._subscribe_plate_saved_event()

        # Criar interface
        self._criar_header()
        self._criar_tabview()

        if self._window is not None:
            self._window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_window_title(self, value: str) -> None:
        """Atualiza o titulo de forma segura em modo pagina/legado."""
        target = self._window
        if target is None:
            try:
                target = self.winfo_toplevel()
            except Exception:
                target = None
        if target is not None and hasattr(target, "title"):
            try:
                target.title(value)
            except Exception:
                pass

    def _subscribe_plate_saved_event(self, event_bus=None) -> None:
        """Inscreve handler de sincronizacao do mapa apenas uma vez."""
        if self._plate_saved_subscribed:
            return
        if event_bus is None:
            from services.core.event_bus import EventBus

            event_bus = EventBus
        from services.core.event_bus import SystemEvents

        event_bus.subscribe(SystemEvents.PLATE_SAVED, self._on_mapa_salvo_event)
        self._plate_saved_subscribed = True
        registrar_log("EventBus", "Subscrito ao evento PLATE_SAVED", "DEBUG")

    def _unsubscribe_plate_saved_event(self, event_bus=None) -> None:
        """Remove handler de sincronizacao para evitar leaks entre janelas."""
        if not self._plate_saved_subscribed:
            return
        if event_bus is None:
            from services.core.event_bus import EventBus

            event_bus = EventBus
        from services.core.event_bus import SystemEvents

        event_bus.unsubscribe(SystemEvents.PLATE_SAVED, self._on_mapa_salvo_event)
        self._plate_saved_subscribed = False
        registrar_log("EventBus", "Unsubscribed do evento PLATE_SAVED", "DEBUG")

    def _normalizar_colunas_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza nomes de colunas do DataFrame.
        
        - Poço(s)/Poço/Poco → Poco
        - Código/Codigo/CODE → Codigo
        
        Args:
            df: DataFrame a normalizar
            
        Returns:
            DataFrame com colunas normalizadas (in-place)
        """
        rename_map: Dict[str, str] = {}
        normalized_map = {col: _normalize_col_key(col) for col in df.columns}

        if "Poco" not in df.columns:
            for col, normalized in normalized_map.items():
                if normalized in {"poco", "pocos", "well", "wells"}:
                    rename_map[col] = "Poco"
                    break

        if "Codigo" not in df.columns:
            for col, normalized in normalized_map.items():
                if "codigo" in normalized or normalized in {"code", "codes"}:
                    rename_map[col] = "Codigo"
                    break
        
        if rename_map:
            df.rename(columns=rename_map, inplace=True)
            registrar_log("Normalização", f"Colunas renomeadas: {rename_map}", "DEBUG")

        # Canonicalizar coluna de sugestao para repeticao, mantendo a mais a direita.
        repeticao_key = _normalize_col_key("Sugestão_de_repetição")
        repeticao_cols = [
            col for col in df.columns if _normalize_col_key(col) == repeticao_key
        ]
        if repeticao_cols:
            rightmost_col = repeticao_cols[-1]
            rightmost_series = df[rightmost_col].copy()

            original_cols = list(df.columns)
            rightmost_idx = original_cols.index(rightmost_col)
            removed_before = sum(
                1 for col in repeticao_cols if original_cols.index(col) < rightmost_idx
            )
            insert_idx = max(0, rightmost_idx - removed_before)

            df.drop(columns=repeticao_cols, inplace=True)
            df.insert(
                min(insert_idx, len(df.columns)),
                "Sugestão_de_repetição",
                rightmost_series,
            )

            if len(repeticao_cols) > 1 or rightmost_col != "Sugestão_de_repetição":
                registrar_log(
                    "Normalização",
                    (
                        "Coluna de repeticao canonicalizada: "
                        f"removidas={repeticao_cols} mantida='Sugestão_de_repetição' "
                        "(origem=coluna mais a direita)"
                    ),
                    "INFO",
                )

        return df
    
    def _rebuild_plate_model(self, df_source: Optional[pd.DataFrame] = None) -> Optional['PlateModel']:
        """
        Reconstrói PlateModel a partir do DataFrame atual.
        
        Consolida a lógica duplicada de criação de PlateModel em 3 locais diferentes.
        
        Args:
            df_source: DataFrame a ser usado para construir o PlateModel.
            
        Returns:
            PlateModel atualizado com dados normalizados, ou None se 'Poco' estiver ausente.
        """
        if df_source is None:
            df_source = self.df_analise
        if df_source is None:
            registrar_log("PlateModel", "DataFrame de origem ausente para rebuild", "WARNING")
            return None

        # Normalizar colunas
        df_normalizado = self._normalizar_colunas_df(df_source.copy())
        
        # Validar que Poco existe
        if 'Poco' not in df_normalizado.columns:
            registrar_log("PlateModel", "Coluna 'Poco' ausente, retornando modelo vazio", "WARNING")
            return None
        
        # Criar PlateModel
        return PlateModel.from_df(
            df_normalizado,
            group_size=self.bloco_tamanho,
            exame=self.exame
        )
    
    def _carregar_mapa_inicial(self):
        """
        Carrega o mapa da placa na aba 'Mapa da Placa'.
        Chamado uma vez ao iniciar a janela, após um pequeno delay.
        """
        from views.plate_view import PlateView
        from models.plate_model import PlateModel
        
        # Usar uma cópia do df_analise para o mapa, para evitar modificações diretas
        df_para_mapa = self.df_analise.copy()
        
        # Normalização consolidada
        self._normalizar_colunas_df(df_para_mapa)
        
        # Validar que Poco existe (evita mapa vazio)
        if 'Poco' not in df_para_mapa.columns:
            registrar_log("Mapa", "Coluna 'Poco' ausente no DataFrame, impossível criar mapa", "ERROR")
            return
        
        # Usar método consolidado para criar PlateModel
        self.plate_model = self._rebuild_plate_model(df_para_mapa)
        
        if self.plate_model:
            self._mapa_frame = PlateView(
                self.tab_mapa,
                self.plate_model,
                self.num_placa,
                self.data_placa_formatada,
                self.status_corrida,
                self.usuario_logado,
                self.exame,
                self.lote,
                self.arquivo_corrida,
                self.numero_extracao,
                self.agravos
            )
            self._mapa_frame.pack(fill="both", expand=True)
        else:
            # Exibir placeholder se o modelo não puder ser criado
            self._mapa_placeholder = ctk.CTkLabel(
                self.tab_mapa,
                text="Não foi possível carregar o mapa da placa.\nColuna 'Poco' ausente ou inválida.",
                font=Theme.get_font_primary(size=14, weight="bold"),
                text_color="red"
            )
            self._mapa_placeholder.pack(expand=True)
    
    def _criar_header(self):
        """Cria header com informações da corrida."""
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        header_frame.grid_columnconfigure(4, weight=1)  # FASE 4: Expandido para 5 colunas
        
        # FASE 4: Extração (C8) - prioridade visual à esquerda
        if self.numero_extracao:
            ctk.CTkLabel(
                header_frame,
                text=f"Extração: {self.numero_extracao}",
                font=Theme.get_font_primary(size=9, weight="bold"),
                text_color="#e74c3c"  # Vermelho para destaque
            ).grid(row=0, column=0, padx=10, sticky="w")
            col_offset = 1  # Deslocar outras colunas
        else:
            col_offset = 0  # Sem extração, layout original
        
        ctk.CTkLabel(
            header_frame, 
            text=f"Placa: {self.num_placa}", 
            font=Theme.get_font_primary(size=9, weight="bold")  # FASE 1.2: 12pt → 9pt
        ).grid(row=0, column=col_offset, padx=10, sticky="w")
        
        ctk.CTkLabel(
            header_frame,
            text=f"Data: {self.data_placa_formatada}",
            font=Theme.get_font_primary(size=9, weight="bold")  # FASE 1.2: 12pt → 9pt
        ).grid(row=0, column=col_offset+1, padx=10, sticky="w")
        
        ctk.CTkLabel(
            header_frame,
            text=f"Status: {self.status_corrida}",
            font=Theme.get_font_primary(size=9, weight="bold")  # FASE 1.2: 12pt → 9pt
        ).grid(row=0, column=col_offset+2, padx=10, sticky="w")
        
        ctk.CTkLabel(
            header_frame,
            text=f"Exame: {self.exame}",
            font=Theme.get_font_primary(size=9, weight="bold")  # FASE 1.2: 12pt → 9pt
        ).grid(row=0, column=col_offset+3, padx=10, sticky="e")
    
    def _criar_tabview(self):
        """Cria TabView com abas de Análise e Mapa."""
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # Aba 1: Análise
        self.tab_analise = self.tabview.add("Analise")
        self._construir_aba_analise()
        
        # Aba 2: Mapa da Placa
        self.tab_mapa = self.tabview.add("Mapa da Placa")
        self._mapa_frame: Optional[PlateView] = None
        self._mapa_placeholder = None
        
        # Callback ao trocar aba
        self.tabview.configure(command=self._on_tab_change)
        
        # NOVO: Carregar mapa automaticamente após pequeno delay
        # (permite janela renderizar completamente antes)
        self.after(100, self._carregar_mapa_inicial)
    
    def _ordenar_df_por_coluna(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ordena DataFrame por coluna Poco usando padrão (coluna primeiro, depois linha).
        
        Ordem esperada: A1+A2, B1+B2, ..., H1+H2, A3+A4, B3+B4, ..., H11+H12
        
        Args:
            df: DataFrame com coluna 'Poco' ou 'Poço'
            
        Returns:
            DataFrame ordenado (novo objeto com índice resetado)
        """
        # Identificar coluna de poços
        poco_col = None
        if 'Poco' in df.columns:
            poco_col = 'Poco'
        elif 'Poço' in df.columns:
            poco_col = 'Poço'
        else:
            # Sem coluna de poços, retornar sem ordenar
            registrar_log("Ordenacao", "Coluna Poco/Poço não encontrada, sem ordenação", "WARNING")
            return df
        
        return self._sort_dataframe_by_well(df, poco_col)
    
    def _sort_dataframe_by_well(self, df: pd.DataFrame, poco_col: str) -> pd.DataFrame:
        """
        Ordena DataFrame pela coluna de poços usando ordenação por coluna.
        
        Args:
            df: DataFrame a ordenar
            poco_col: Nome da coluna com IDs de poços ('Poco' ou 'Poço')
            
        Returns:
            DataFrame ordenado com índice resetado
        """
        from utils.well_sorter import well_sort_key_by_column
        
        try:
            # Criar mapa de ordem baseado na chave de ordenação por coluna
            df_copy = df.copy()
            df_copy['_sort_key'] = df_copy[poco_col].apply(well_sort_key_by_column)
            df_sorted = df_copy.sort_values('_sort_key').drop(columns=['_sort_key'])
            return df_sorted.reset_index(drop=True)
        except Exception as e:
            registrar_log("Ordenacao", f"Erro ao ordenar DataFrame: {e}", "ERROR")
            return df
    
    def _construir_aba_analise(self):
        """Constrói conteúdo da aba de análise."""
        # Frame principal
        main_frame = ctk.CTkFrame(self.tab_analise)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # Barra de botões
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        btn_frame.grid_columnconfigure(7, weight=1)
        
        ctk.CTkButton(
            btn_frame,
            text="[X] Selecionar Todos",
            command=self._selecionar_todos,
            fg_color="#3498DB",
            hover_color="#2980B9"
        ).grid(row=0, column=0, padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Relatório Estatístico",
            command=self._mostrar_relatorio
        ).grid(row=0, column=1, padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Gráfico de Detecção",
            command=self._gerar_grafico
        ).grid(row=0, column=2, padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Reaplicar Seleção",
            command=self._reaplicar_selecao,
            fg_color="#F39C12",
            hover_color="#D68910"
        ).grid(row=0, column=3, padx=5)
        
        # Botão 'Ir para Mapa' REMOVIDO - mapa já está na aba ao lado
        
        ctk.CTkButton(
            btn_frame,
            text="[SALVAR] Selecionados",
            command=self._salvar_selecionados,
            fg_color="#27AE60",
            hover_color="#229954"
        ).grid(row=0, column=4, padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Gerar Mapa da Placa definitivo para arquivar",
            command=self._gerar_mapa_placa_definitivo,
            fg_color="#34495E",
            hover_color="#2C3E50"
        ).grid(row=0, column=5, padx=5)

        self.btn_abrir_mapa = ctk.CTkButton(
            btn_frame,
            text="Abrir Mapa da Placa",
            command=self._abrir_mapa_definitivo,
            fg_color="#27AE60",
            hover_color="#229954"
        )
        self.btn_abrir_mapa.grid(row=0, column=6, padx=5)

        # Frame da tabela
        self.table_frame = ctk.CTkFrame(main_frame)
        self.table_frame.grid(row=1, column=0, sticky="nsew")
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(0, weight=1)
        
        # Criar ScientificDataGrid inicial
        self._criar_scientific_grid()
        
        # Popular tabela
        self._popular_tabela()
    
    def _criar_scientific_grid(self):
        """Instancia o FullAnalysisGrid (tabela completa com todas as colunas)."""
        if hasattr(self, 'full_grid') and self.full_grid:
            self.full_grid.destroy()

        self.full_grid = FullAnalysisGrid(
            self.table_frame,
            on_toggle_select=self._on_grid_toggle_select,
        )
        self.full_grid.pack(fill="both", expand=True)

        # Mantém alias para não quebrar código legado que referencie scientific_grid
        self.scientific_grid = self.full_grid
        
    def _on_grid_toggle_select(self, well: str, new_state: bool):
        """Callback invocado pelo FullAnalysisGrid quando o usuário clica no checkbox."""
        # O FullAnalysisGrid já atualizou sua cópia interna (_df é referência viva);
        # aqui garantimos que df_analise (source of truth da janela) também reflete.
        poco_col = "Poco" if "Poco" in self.df_analise.columns else "Poço"
        mask = self.df_analise[poco_col] == well
        self.df_analise.loc[mask, "Selecionado"] = new_state
        
        # Sincronizar imediatamente com o app_state (source of truth global)
        # Evita que a recriação do módulo reverta a edição.
        if hasattr(self.main_window, "app_state"):
            self.main_window.app_state.resultados_analise = self.df_analise.copy()
            from utils.logger import registrar_log
            registrar_log("Sync", f"Seleção de {well} alterada para {new_state} e sincronizada no app_state.", "DEBUG")
        
    def _popular_tabela(self):
        """Popula o DataGrid e atualiza estatísticas se for modo legacy."""
        try:
            # Sincronizar com o estado global para o Módulo Resultados
            if hasattr(self.main_window, "app_state"):
                self.main_window.app_state.resultados_analise = self.df_analise.copy()

            if not hasattr(self, 'full_grid') or not self.full_grid:
                return
            self.full_grid.load_dataframe(self.df_analise)
        except Exception as e:
            registrar_log("PopularTabela", f"Erro: {e}", "ERROR")

    def _selecionar_todos(self):
        """Seleciona todas as amostras válidas (não inválidas, não controles)."""
        try:
            # Detectar colunas
            result_cols = listar_colunas_alvo(self.df_analise.columns)
            
            selecionadas = 0
            for index, row in self.df_analise.iterrows():
                # Pular controles
                amostra = str(row.get("Amostra", "")).upper()
                if any(ctrl in amostra for ctrl in ["CN", "CP", "NEG", "POS"]):
                    self.df_analise.loc[index, "Selecionado"] = False
                    continue
                
                # Pular inválidos
                if any(_norm_res_label(row.get(c, "")) == "invalido" for c in result_cols):
                    self.df_analise.loc[index, "Selecionado"] = False
                    continue
                
                # Selecionar
                self.df_analise.loc[index, "Selecionado"] = True
                selecionadas += 1
            
            # Atualizar tabela
            self._popular_tabela()

            messagebox.showinfo(
                "Selecao Completa",
                f"OK! {selecionadas} amostras validas selecionadas!",
                parent=self
            )
            
        except Exception as e:
            registrar_log("Selecionar Todos", f"Erro: {e}", "ERROR")
            messagebox.showerror("Erro", f"Falha ao selecionar:\n{e}", parent=self)

    def _reaplicar_selecao(self):
        """
        Reaplica regras de seleção com base na aptidão operacional atual.
        Preserva seleção manual somente até o usuário acionar este comando,
        limpando apenas os Inválidos, Indeterminados, CN e CP. As demais escolhas persistem.
        """
        try:
            if "Selecionado" not in self.df_analise.columns:
                self.df_analise.insert(0, "Selecionado", False)

            result_cols = listar_colunas_alvo(self.df_analise.columns)

            selecionadas = 0
            for index, row in self.df_analise.iterrows():
                # Controles não são selecionáveis
                amostra = str(row.get("Amostra", "")).upper()
                is_controle = _is_controle_operacional(row) or any(ctrl in amostra for ctrl in ["CN", "CP", "NEG", "POS"])

                # Amostras inválidas ou indeterminadas não podem ser selecionadas.
                rg = str(row.get("Resultado_geral", "")).lower()
                is_indeterminado = "indeterm" in rg or "inconclus" in rg
                is_invalido = any(_norm_res_label(row.get(c, "")) == "invalido" for c in result_cols)

                if is_controle or is_indeterminado or is_invalido:
                    self.df_analise.loc[index, "Selecionado"] = False
                
                if self.df_analise.loc[index, "Selecionado"]:
                    selecionadas += 1

            self._popular_tabela()
            messagebox.showinfo(
                "Seleção Reaplicada",
                f"OK! Seleção reavaliada (Controles/Indeterminados/Inválidos desmarcados). Restaram {selecionadas} amostras.",
                parent=self,
            )

        except Exception as e:
            registrar_log("Seleção", f"Erro ao reaplicar seleção: {e}", "ERROR")
            messagebox.showerror("Erro", f"Falha ao reaplicar seleção:\n{e}", parent=self)
    
    def _carregar_mapa_inicial(self):
        """Carrega mapa automaticamente ao abrir janela (chamado via after)."""
        try:
            self._carregar_mapa()
            registrar_log("Mapa", "Mapa carregado automaticamente", "INFO")
            
            # Informar usuário sobre sincronização automática
            messagebox.showinfo(
                "Mapa Carregado",
                "OK! Mapa da placa carregado!\n\n"
                "IMPORTANTE:\n"
                "- Ao clicar 'Aplicar' no mapa, as mudancas sao\n"
                "  automaticamente recalculadas em toda a placa\n"
                "- Clique 'Salvar e Voltar' para sincronizar\n"
                "  com a aba de analise",
                parent=self
            )
            
        except Exception as e:
            registrar_log("Mapa", f"Erro ao carregar mapa inicial: {e}", "ERROR")
            # Mostrar placeholder de erro
            self._mapa_placeholder = ctk.CTkLabel(
                self.tab_mapa,
                text=f"Erro ao carregar mapa:\n{str(e)}",
                font=Theme.get_font_primary(size=9),  # FASE 1.2: 12pt → 9pt
                text_color="#e74c3c"
            )
            self._mapa_placeholder.pack(expand=True)
    
    def _carregar_mapa(self):
        """Cria PlateView pela primeira vez."""
        # Remover placeholder
        if self._mapa_placeholder:
            self._mapa_placeholder.destroy()
            self._mapa_placeholder = None
        
        # ✅ REGRESSÃO #2: Normalização ROBUSTA antes de criar PlateModel
        df_para_mapa = self.df_analise.copy()
        
        # Normalização consolidada
        self._normalizar_colunas_df(df_para_mapa)
        
        # ✅ Validar que Poco existe (evita mapa vazio)
        if 'Poco' not in df_para_mapa.columns:
            colunas_disp = ', '.join(df_para_mapa.columns[:10])
            messagebox.showerror(
                "Erro", 
                f"Coluna 'Poco' não encontrada após normalização.\n\nColunas disponíveis: {colunas_disp}...", 
                parent=self
            )
            registrar_log("Mapa", f"ERRO: Poco ausente. Colunas: {df_para_mapa.columns.tolist()}", "ERROR")
            return
        
        # Criar PlateModel
        self.plate_model = PlateModel.from_df(
            df_para_mapa,
            group_size=self.bloco_tamanho,
            exame=self.exame
        )
        
        # Criar PlateView como Frame DENTRO da aba
        meta = {
            "data": self.data_placa_formatada,
            "extracao": self.arquivo_corrida or self.lote,
            "exame": self.exame,
            "usuario": self.usuario_logado,
        }
        
        # ✅ CORREÇÃO #2: Remover callback inválido - PlateView usará Event Bus
        # O método _on_mapa_salvo não existe. O correto é _on_mapa_salvo_event
        # que já está subscrito ao Event Bus via SystemEvents.PLATE_SAVED
        self._mapa_frame = PlateView(
            self.tab_mapa,
            self.plate_model,
            meta=meta
            # ❌ REMOVIDO: on_save_callback=self._on_mapa_salvo (método não existe)
        )
        self._mapa_frame.pack(fill="both", expand=True)
        
        registrar_log("Mapa", "PlateView criado com sucesso (Event Bus ativo, normalização robusta)", "INFO")
    
    def _criar_tab_mapa(self):
        """
        Cria aba do mapa da placa.
        
        OTIMIZAÇÃO (P2 - Resolve Janelas Modais Aninhadas):
        Usa Event Bus para comunicação desacoplada em vez de callback direto.
        """
        try:
            # Garantir subscricao unica ao evento de salvamento.
            self._subscribe_plate_saved_event()
            
            from ui.modules.plate_viewer import PlateView, PlateModel
            
            # Converter df para modelo
            self.plate_model = PlateModel.from_df(
                self.df_analise,
                group_size=self.bloco_tamanho,
                exame=self.exame
            )
            
            # Criar visualizador SEM callback
            # PlateView publicará evento quando salvar
            self.plate_view = PlateView(
                self.tab_mapa,
                self.plate_model,
                title=f"Mapa da Placa - {self.exame}",
                metadata={
                    "num_placa": self.num_placa,
                    "data_placa": self.data_placa_formatada,
                    "exame": self.exame
                }
            )
            
            self.plate_view.pack(fill="both", expand=True)
            self._mapa_frame = self.plate_view # Manter compatibilidade com _atualizar_mapa
            
            registrar_log("Mapa", "PlateView criado com sucesso (via _criar_tab_mapa)", "INFO")
            
        except Exception as e:
            registrar_log("Mapa", f"Erro ao criar aba do mapa: {e}", "ERROR")
            messagebox.showerror("Erro", f"Falha ao criar aba do mapa:\n{e}", parent=self)
    
    def _atualizar_mapa(self):
        """Atualiza PlateView quando DataFrame muda."""
        if not hasattr(self, 'plate_view') or self.plate_view is None:
            registrar_log("Mapa", "PlateView não existe, criando novo", "DEBUG")
            self._carregar_mapa()
            return
        
        # Rebuilding usando método consolidado
        self.plate_model = self._rebuild_plate_model()
        
        # Atualizar view
        self.plate_view.set_model(self.plate_model)
        registrar_log("Mapa", "Mapa atualizado com novos dados", "INFO")
    
    def _on_mapa_salvo_event(self, event_data: dict):
        """
        Callback para o evento PLATE_SAVED do Event Bus.
        RECALCULA TODA A PLACA e sincroniza IMEDIATAMENTE com aba de análise.
        """
        try:
            # O PlateModel atualizado vem no event_data
            plate_model: PlateModel = event_data.get("plate_model")
            if not plate_model:
                messagebox.showwarning("Aviso", "Evento de mapa salvo sem PlateModel.", parent=self)
                return
            
            # PASSO 1: Converter PlateModel de volta para DataFrame
            df_updated = plate_model.to_dataframe()
            
            if df_updated is None or df_updated.empty:
                messagebox.showwarning("Aviso", "Mapa retornou dados vazios", parent=self)
                return
            
            # FASE 2.1: Normalização defensiva (segunda camada de proteção)
            from ui.modules.plate_viewer import normalize_well_id
            if "Poco" in df_updated.columns:
                df_updated["Poco"] = df_updated["Poco"].apply(normalize_well_id)
            elif "Poço" in df_updated.columns:
                df_updated["Poço"] = df_updated["Poço"].apply(normalize_well_id)
            
            # DEBUG: Log de estrutura ANTES do merge
            cols_resultado_antes = [c for c in self.df_analise.columns if c.startswith("Resultado_")]
            registrar_log("Sync", f"ANTES - df_analise: {len(self.df_analise)} linhas, {len(self.df_analise.columns)} colunas", "DEBUG")
            registrar_log("Sync", f"ANTES - Colunas Resultado_*: {cols_resultado_antes}", "DEBUG")
            if cols_resultado_antes:
                amostra = self.df_analise[cols_resultado_antes].head(2).to_dict('records')
                registrar_log("Sync", f"ANTES - Amostra resultados: {amostra}", "DEBUG")
            
            registrar_log("Sync", f"df_updated: {len(df_updated)} linhas, {len(df_updated.columns)} colunas", "DEBUG")
            cols_resultado_updated = [c for c in df_updated.columns if c.startswith("Resultado_")]
            if cols_resultado_updated:
                amostra_updated = df_updated[cols_resultado_updated].head(2).to_dict('records')
                registrar_log("Sync", f"df_updated - Amostra resultados: {amostra_updated}", "DEBUG")
            
            # DEBUG 2026-02-09: Log para diagnosticar problema de CT não sendo atualizado
            ct_cols_updated = [c for c in df_updated.columns if c.startswith("CT_")]
            registrar_log("Sync", f"df_updated - Colunas CT_*: {ct_cols_updated}", "DEBUG")
            if ct_cols_updated:
                ct_sample = df_updated[ct_cols_updated].head(3).to_dict('records')
                registrar_log("Sync", f"df_updated - Amostra CT: {ct_sample}", "DEBUG")
            
            # Formato do Poco
            if "Poco" in df_updated.columns:
                poco_sample = df_updated["Poco"].head(5).tolist()
                registrar_log("Sync", f"df_updated - Poco format: {poco_sample}", "DEBUG")
            if "Poco" in self.df_analise.columns:
                poco_analise_sample = self.df_analise["Poco"].head(5).tolist()
                registrar_log("Sync", f"df_analise - Poco format: {poco_analise_sample}", "DEBUG")
            
            # AUDIT LOG: Registrar modificação de resultados
            try:
                from utils.audit_logger import get_audit_logger
                audit_logger = get_audit_logger()
                
                audit_logger.log_data_modification(
                    usuario=self.usuario_logado or "UNKNOWN",
                    entity_type="resultado_analise",
                    entity_id=f"placa_{self.num_placa}",
                    operation="UPDATE",
                    before={"total_linhas": len(self.df_analise) if hasattr(self, 'df_analise') else 0},
                    after={"total_linhas": len(df_updated)}
                )
            except Exception as e:
                registrar_log("JanelaAnalise", f"Erro ao registrar audit log: {e}", "WARNING")
            
            # PASSO 2: Merge PRESERVANDO colunas que não vieram do mapa
            if is_plate_sync_use_case_enabled(user_id=self.usuario_logado):
                merge_t0 = time.perf_counter()
                sync_result = sync_plate_to_analysis(self.df_analise, df_updated)
                merge_duration_ms = (time.perf_counter() - merge_t0) * 1000
                self.df_analise = sync_result.dataframe
                registrar_log(
                    "Sync",
                    "sync_plate_to_analysis aplicado "
                    f"(merge_key={sync_result.merge_key}, updated_cells={sync_result.updated_cells}, "
                    f"fallback={sync_result.fallback_used})",
                    "INFO",
                )
                try:
                    record_query_latency(
                        operation="plate.sync.merge",
                        backend="use_case",
                        duration_ms=merge_duration_ms,
                        result_count=int(sync_result.updated_cells),
                        meta={
                            "fallback_used": bool(sync_result.fallback_used),
                            "merge_key": str(sync_result.merge_key or ""),
                            "rows_analysis": int(len(self.df_analise)),
                            "rows_updated": int(len(df_updated)),
                        },
                    )
                    summary = summarize_query_latency(
                        operation="plate.sync.merge",
                        backend="use_case",
                        last_n=5000,
                    )
                    registrar_log(
                        "SyncTelemetry",
                        (
                            f"plate.sync.merge[use_case] count={summary['count']} "
                            f"p50={summary['p50_ms']}ms p95={summary['p95_ms']}ms "
                            f"last={merge_duration_ms:.2f}ms"
                        ),
                        "INFO",
                    )
                except Exception as telemetry_exc:
                    registrar_log(
                        "SyncTelemetry",
                        f"Falha ao registrar telemetria de merge use_case: {telemetry_exc}",
                        "WARNING",
                        error_code=ErrorCode.PLATE_SYNC_MERGE_FAILED,
                    )

                if "Selecionado" in self.df_analise.columns:
                    cols = ["Selecionado"] + [c for c in self.df_analise.columns if c != "Selecionado"]
                    self.df_analise = self.df_analise[cols]

                try:
                    self._reanalise_completa_pos_mapa()
                except Exception as _exc_reanalise:
                    registrar_log("Sync", f"Aviso na re-análise (continuando): {_exc_reanalise}", "WARNING")

                if hasattr(self.main_window, "app_state"):
                    self.main_window.app_state.resultados_analise = self.df_analise.copy()
                    registrar_log(
                        "Sincronização",
                        "Global app_state.resultados_analise atualizado após mapa salvo.",
                        "INFO",
                    )

                self.tabview.set("Analise")
                from datetime import datetime

                timestamp = datetime.now().strftime("%H:%M:%S")
                self._set_window_title(f"RT-PCR - Analise Completa (OK - Sincronizado: {timestamp})")
                registrar_log("Sincronização", "Dados do mapa sincronizados com sucesso", "INFO")
                return

            # PASSO 2: Merge PRESERVANDO colunas que não vieram do mapa (legado)
            colunas_originais = list(self.df_analise.columns)
            
            # Identificar chave de merge (Poco ou Poço)
            chave_merge = None
            if "Poco" in df_updated.columns and "Poco" in self.df_analise.columns:
                chave_merge = "Poco"
            elif "Poço" in df_updated.columns and "Poço" in self.df_analise.columns:
                chave_merge = "Poço"
            
            # CORREÇÃO BUG 2026-02-09: A lógica de merge estava DENTRO do elif "Poço"
            # Isso fazia com que quando df_updated tinha coluna "Poco", o merge era PULADO!
            if chave_merge:
                # CORRECAO CRITICA: Identificar colunas que VIERAM do mapa vs. colunas CALCULADAS
                # Padronização Phase 6: Agora plate_viewer gera Res_ tal qual analysis_service.
                # Portanto, podemos aceitar todas as colunas do mapa.
                colunas_do_mapa = set(df_updated.columns)
                colunas_preservar = [c for c in self.df_analise.columns if c not in colunas_do_mapa]
                
                # Normalizar chaves
                df_updated[chave_merge] = df_updated[chave_merge].astype(str).str.strip()
                self.df_analise[chave_merge] = self.df_analise[chave_merge].astype(str).str.strip()
                
                # BACKUP de colunas que NÃO vieram do mapa
                if colunas_preservar:
                    df_backup = self.df_analise[[chave_merge] + colunas_preservar].copy()
                
                # Atualizar APENAS as colunas que vieram do mapa
                for col in colunas_do_mapa:
                    if col == chave_merge:
                        continue
                    
                    # Atualizar célula por célula
                    for idx, row_updated in df_updated.iterrows():
                        poco_id = str(row_updated[chave_merge]).strip()
                        
                        # CORREÇÃO BUG 2026-02-09: Usar normalize_well_id para matching exato
                        # Antes: 'A1' in ['A10', 'A11'] retornava False (ok), mas 'A01' não fazia match com 'A1'
                        from ui.modules.plate_viewer import normalize_well_id
                        
                        def well_in_group(group_id: str) -> bool:
                            """Verifica se poco_id está contido em group_id com normalização."""
                            wells = [w.strip() for w in str(group_id).split('+')]
                            poco_normalized = normalize_well_id(poco_id)
                            wells_normalized = [normalize_well_id(w) for w in wells]
                            return poco_normalized in wells_normalized
                        
                        mask = self.df_analise[chave_merge].apply(well_in_group)
                        
                        if mask.any():
                            self.df_analise.loc[mask, col] = row_updated[col]
                        else:
                            # Poço realmente não encontrado (pode ser controle ou vazio)
                            pass  # Silenciado para reduzir logs
                
                # DEBUG 2026-02-09: Log CT values AFTER merge to see if they were copied
                ct_cols_in_df = [c for c in self.df_analise.columns if c.startswith('CT_')]
                if ct_cols_in_df:
                    ct_after_sample = self.df_analise[ct_cols_in_df].head(3).to_dict('records')
                    registrar_log("Sync", f"APÓS MERGE - CT values: {ct_after_sample}", "DEBUG")
                
                registrar_log("Sync", f"Preservadas {len(colunas_preservar)} colunas não-editadas: {colunas_preservar[:5]}...", "INFO")
                
                # VALIDAÇÃO: Verificar integridade do merge
                colunas_resultado = [c for c in self.df_analise.columns if c.startswith("Resultado_")]
                total_nan = 0
                for col in colunas_resultado:
                    nan_count = self.df_analise[col].isna().sum()
                    total_nan += nan_count
                    if nan_count > 0:
                        registrar_log("Sync", f"AVISO: {nan_count} NaN detectados em {col}", "WARNING")
                
                if total_nan > 0:
                    registrar_log("Sync", f"ERRO CRÍTICO: {total_nan} valores NaN no total - MERGE CORROMPIDO", "ERROR")
                
                # Log detalhado DEPOIS do merge
                registrar_log("Sync", f"DEPOIS - Merge concluído: {len(self.df_analise)} linhas, {len(self.df_analise.columns)} colunas", "DEBUG")
                if colunas_resultado:
                    dtypes = {c: str(self.df_analise[c].dtype) for c in colunas_resultado}
                    registrar_log("Sync", f"DEPOIS - Tipos de dados: {dtypes}", "DEBUG")
                    amostra_depois = self.df_analise[colunas_resultado].head(2).to_dict('records')
                    registrar_log("Sync", f"DEPOIS - Amostra resultados: {amostra_depois}", "DEBUG")
                
                # CORREÇÃO: Ordenar DataFrame por (coluna, linha) após merge
                self.df_analise = self._ordenar_df_por_coluna(self.df_analise)
                registrar_log("Sync", "DataFrame ordenado por (coluna, linha): A1+A2, B1+B2, ..., H11+H12", "INFO")
                
            else:
                # FALLBACK: Substituição direta se não houver chave
                self.df_analise = df_updated.copy()
                if "Selecionado" not in self.df_analise.columns:
                    self.df_analise.insert(0, "Selecionado", False)
            
            # PASSO 3: Garantir ordem das colunas (Selecionado primeiro)
            if "Selecionado" in self.df_analise.columns:
                cols = ["Selecionado"] + [c for c in self.df_analise.columns if c != "Selecionado"]
                self.df_analise = self.df_analise[cols]
            
            # PASSO 3.5 + 4: Re-análise completa (Res_* canonicalizados + Resultado_geral + cores)
            try:
                self._reanalise_completa_pos_mapa()
            except Exception as _exc_reanalise:
                registrar_log("Sync", f"Aviso na re-análise (continuando): {_exc_reanalise}", "WARNING")

            # PASSO 4.5: Sincronizar com o estado global da aplicação
            # Garante que o menu "Visualizar Resultados" mostre os dados atualizados
            if hasattr(self.main_window, "app_state"):
                self.main_window.app_state.resultados_analise = self.df_analise.copy()
                registrar_log("Sincronização", "Global app_state.resultados_analise atualizado após mapa salvo.", "INFO")

            # PASSO 5: Voltar para aba de análise — garantido mesmo se recalc falhou
            self.tabview.set("Analise")
            
            # PASSO 6: Feedback visual
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._set_window_title(f"RT-PCR - Analise Completa (OK - Sincronizado: {timestamp})")
            
            registrar_log("Sincronização", "Dados do mapa sincronizados com sucesso", "INFO")
            
        except Exception as e:
            import traceback
            erro_completo = traceback.format_exc()
            registrar_log(
                "Sincronizacao",
                f"Erro: {erro_completo}",
                "ERROR",
                error_code=ErrorCode.PLATE_SYNC_MERGE_FAILED,
            )
            messagebox.showerror("Erro de Sincronização", f"Falha ao sincronizar:\n{e}\n\nVeja logs para detalhes.", parent=self)
    
    def _on_tab_change(self):
        """Callback ao trocar de aba."""
        aba_atual = self.tabview.get()
        registrar_log("TabView", f"Aba alterada para: {aba_atual}", "DEBUG")
        
        if aba_atual == "Analise":
            target = self._window if self._window is not None else self.winfo_toplevel()
            try:
                target.state('zoomed')
            except Exception as e:
                registrar_log("TabView", f"Não foi possível maximizar a janela: {e}", "WARNING")
    
    def _recalcular_resultados_por_ct(self):
        """
        Recalcula colunas Res_* baseadas nos valores de CT após edição no Mapa da Placa.
        
        REGRAS DE CT (Biomanguinhos VR1e2):
        - CT vazio/None/<8/>42: Não Detectável
        - CT 8-35: Detectável
        - CT 35-40: Indeterminado
        - CT >40: Não Detectável
        
        Também recalcula Resultado_geral com prioridade correta.
        """
        # Constantes de threshold AGORA em services.logic_engine
        
        # Função classificar_ct agora é importada de services.logic_engine
        # Eliminando duplicação de regra de negócio.
        
        # Identificar pares de colunas CT_* e Res_*
        ct_cols = [c for c in self.df_analise.columns if c.startswith('CT_') and c != 'CT_Raw']
        
        for ct_col in ct_cols:
            # Extrair nome do alvo (CT_ADV -> ADV)
            alvo = ct_col.replace('CT_', '')
            
            # Encontrar coluna de resultado correspondente
            res_col = f'Res_{alvo}'
            if res_col not in self.df_analise.columns:
                # Tentar formato alternativo Resultado_*
                res_col = f'Resultado_{alvo}'
                if res_col not in self.df_analise.columns:
                    continue  # Alvo sem coluna de resultado, pular
            
            # Canonicalizar nome do alvo para bater com o runtime_profile (ex: "FLUA" -> "INF A")
            from services.analysis.analysis_helpers import canonicalizar_alvo_pcr
            alvo_canonico = canonicalizar_alvo_pcr(alvo) or alvo

            # Recalcular resultado usando limiares por alvo do exame
            if self._runtime_profile:
                from domain.ct_rules_runtime import classificar_ct_por_exame

                def _classificar_ct_alvo(ct_raw, _alvo=alvo_canonico):
                    if pd.isna(ct_raw) or str(ct_raw).strip().lower() in (
                        "", "undetermined", "und", "—",
                    ):
                        ct_float = None
                    else:
                        try:
                            ct_float = float(str(ct_raw).replace(",", "."))
                        except (ValueError, TypeError):
                            ct_float = None
                    return classificar_ct_por_exame(ct_float, _alvo, "A1", self._runtime_profile).value
            else:
                def _classificar_ct_alvo(ct_raw, _alvo=alvo_canonico):
                    return classificar_ct(ct_raw)

            # Aplicar recalculo apenas em linhas sem override manual
            manual_col = f"Manual_{alvo}"
            if manual_col in self.df_analise.columns and self.df_analise[manual_col].astype(bool).any():
                mask_auto = ~self.df_analise[manual_col].astype(bool)
                self.df_analise.loc[mask_auto, res_col] = (
                    self.df_analise.loc[mask_auto, ct_col].apply(_classificar_ct_alvo)
                )
                n_manual = int(self.df_analise[manual_col].astype(bool).sum())
                registrar_log("Recalc", f"{res_col}: {n_manual} linha(s) com override manual preservadas", "INFO")
            else:
                self.df_analise[res_col] = self.df_analise[ct_col].apply(_classificar_ct_alvo)

            registrar_log("Recalc", f"Recalculado {res_col} baseado em {ct_col} (perfil: {bool(self._runtime_profile)})", "DEBUG")
        
        # Agora recalcular Resultado_geral
        self._recalcular_resultado_geral()
    
    def _recalcular_resultado_geral(self):
        """Recalcula Resultado_geral delegando a domain.resultado_geral.calcular_resultado_geral."""
        from domain.resultado_geral import calcular_resultado_geral, RESULTADO_INDETERMINADO

        if 'Resultado_geral' not in self.df_analise.columns:
            self.df_analise['Resultado_geral'] = ""

        res_cols = [c for c in self.df_analise.columns
                    if (c.startswith('Res_') or c.startswith('Resultado_'))
                    and not any(rp in c.upper() for rp in ['RP_', 'RP-', '_RP', 'GERAL'])]

        _RP_VALIDOS = {'detectável', 'detectavel', 'detectado', 'válido', 'valido', ''}
        for idx, row in self.df_analise.iterrows():
            # RP válido = CT dentro do range (resultado "Detectável") ou legado "Válido".
            # Colunas podem ser Res_RP, Res_RP_1..4 dependendo do exame.
            rp_valido = True
            for rp_col in ['Res_RP', 'Res_RP_1', 'Res_RP_2', 'Res_RP_3', 'Res_RP_4']:
                if rp_col in row.index:
                    rp_val = str(row.get(rp_col, '')).strip().casefold()
                    if rp_val not in _RP_VALIDOS:
                        rp_valido = False
                        break

            alvos = {
                col.replace('Res_', '').replace('Resultado_', ''): str(row.get(col, ''))
                for col in res_cols
            }

            resultado = calcular_resultado_geral(rp_valido, alvos)
            self.df_analise.at[idx, 'Resultado_geral'] = resultado

            if 'Sugestão_de_repetição' in self.df_analise.columns:
                self.df_analise.at[idx, 'Sugestão_de_repetição'] = (
                    "Sim" if resultado == RESULTADO_INDETERMINADO else "Não"
                )

        registrar_log("Recalc", "Resultado_geral recalculado para todas as amostras", "INFO")

    def _reanalise_completa_pos_mapa(self) -> None:
        """Pipeline completo de re-análise após edição no Mapa da Placa.

        Garante que Resultado_geral existe, recalcula Res_<alvo> com nomes
        canônicos, recalcula Resultado_geral e repopula a tabela com cores.
        """
        if "Resultado_geral" not in self.df_analise.columns:
            self.df_analise["Resultado_geral"] = ""
        self._recalcular_resultados_por_ct()
        self._recalcular_resultado_geral()
        self._popular_tabela()
        registrar_log("Sync", "Re-analise completa pos-mapa concluida", "INFO")

    def _calcular_geral_fallback(self, row, result_cols):
        """
        Fallback: Calcula Resultado_geral para uma row quando coluna não existe.
        Replica lógica de PlateModel._calcular_resultado_geral.
        """
        try:
            from services.suspected_orphan_telemetry import log_suspected_orphan_usage
            log_suspected_orphan_usage(
                "ui.janela_analise_completa._calcular_geral_fallback",
                throttle_seconds=3600,
            )
        except Exception:
            pass

        has_pos = False
        has_inc = False
        has_inv = False
        has_nd = False
        
        for col in result_cols:
            # Filtrar RPs
            alvo = col.replace("Resultado_", "").replace("Res_", "")
            alvo_upper = alvo.upper()
            if alvo_upper.startswith("RP") or "RP_" in alvo_upper or "RP-" in alvo_upper:
                continue
            
            token = classify_result_text(row.get(col, ""))
            if token == "DET":
                has_pos = True
            elif token == "INC":
                has_inc = True
            elif token == "INV":
                has_inv = True
            elif token == "ND":
                has_nd = True
        
        # Prioridades
        if has_pos:
            return "Detectável"
        elif has_inc:
            return "Indeterminado"
        elif has_inv:
            return "Inválido"
        elif has_nd:
            return "Não detectável"
        else:
            return ""
    
    def _mostrar_relatorio(self):
        """Exibe relatório estatístico em tabela profissional."""
        try:
            import customtkinter as ctk
            from tkinter import ttk
            from services.reports.relatorio_estatistico import calcular_estatisticas_relatorio

            table_data, total_sem_controles = calcular_estatisticas_relatorio(self.df_analise)
            if not table_data:
                messagebox.showerror("Erro", "Nenhuma coluna de resultado encontrada.", parent=self)
                return
            
            # Criar janela Toplevel com tabela
            janela_stats = ctk.CTkToplevel(self)
            janela_stats.title(f"Estatísticas - {self.exame}")
            janela_stats.geometry("720x560")
            center_window(janela_stats, width=720, height=560)
            janela_stats.transient(self)

            # Header com info
            header_frame = ctk.CTkFrame(janela_stats)
            header_frame.pack(fill="x", padx=10, pady=10)

            ctk.CTkLabel(
                header_frame,
                text="Relatório Estatístico",
                font=Theme.get_font_primary(size=16, weight="bold"),
            ).pack(anchor="w")

            ctk.CTkLabel(
                header_frame,
                text=(
                    f"Exame: {self.exame} | Data: {self.data_placa_formatada} | "
                    f"Total (sem CN/CP): {total_sem_controles} amostras"
                ),
                font=Theme.get_font_primary(size=11),
            ).pack(anchor="w", pady=(5, 0))

            # Legenda de cores
            legenda_frame = ctk.CTkFrame(janela_stats, fg_color="transparent")
            legenda_frame.pack(fill="x", padx=10, pady=(0, 4))
            for cor, label in (
                ("#ffb3b3", "  Detectável presente  "),
                ("#ffe0b2", "  Indeterminado  "),
                ("#d4f4d4", "  Todos Não detect.  "),
            ):
                ctk.CTkLabel(
                    legenda_frame,
                    text=label,
                    fg_color=cor,
                    text_color="#333333",
                    corner_radius=4,
                    font=Theme.get_font_primary(size=9),
                ).pack(side="left", padx=4)

            # Frame para Treeview
            tree_frame = ctk.CTkFrame(janela_stats)
            tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

            # Treeview com scrollbar
            columns = ("nd", "det", "inc", "total", "pct_det")
            tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings", height=15)

            # Configurar colunas
            tree.column("#0", width=190, anchor="w")
            tree.heading("#0", text="Alvo")

            tree.column("nd", width=110, anchor="center")
            tree.heading("nd", text="Não detect.")

            tree.column("det", width=110, anchor="center")
            tree.heading("det", text="Detectável")

            tree.column("inc", width=110, anchor="center")
            tree.heading("inc", text="Indeterminado")

            tree.column("total", width=90, anchor="center")
            tree.heading("total", text="Total")

            tree.column("pct_det", width=100, anchor="center")
            tree.heading("pct_det", text="% Det")

            # Scrollbar
            scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)

            # Pack
            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # Preencher dados com cor por linha
            tree.tag_configure("det_presente", background="#ffb3b3")
            tree.tag_configure("ind_presente", background="#ffe0b2")
            tree.tag_configure("tudo_nd", background="#d4f4d4")

            for row_data in table_data:
                nd_val = int(row_data.get("ND", 0) or 0)
                det_val = int(row_data.get("Det", 0) or 0)
                ind_val = int(row_data.get("Ind", 0) or 0)
                total_val = int(row_data.get("Total", 0) or 0)
                pct = f"{det_val * 100 // total_val}%" if total_val > 0 else "—"
                pct_str = f"{det_val} ({pct})"

                if det_val > 0:
                    tag = "det_presente"
                elif ind_val > 0:
                    tag = "ind_presente"
                else:
                    tag = "tudo_nd"

                tree.insert(
                    "",
                    "end",
                    text=row_data["Alvo"],
                    values=(nd_val, det_val, ind_val, total_val, pct_str),
                    tags=(tag,),
                )
            
            # Botão fechar
            ctk.CTkButton(
                janela_stats,
                text="Fechar",
                command=janela_stats.destroy,
                width=100
            ).pack(pady=(0, 10))
            
            janela_stats.focus_force()
            registrar_log(
                "Relatorio",
                f"Tabela exibida com {len(table_data)} linhas (sem CN/CP: {total_sem_controles})",
                "INFO",
            )
            
        except Exception as e:
            import traceback
            erro = traceback.format_exc()
            registrar_log("Relatorio", f"Erro: {erro}", "ERROR")
            messagebox.showerror("Erro", f"Falha ao gerar relatório:\n{e}", parent=self)

    def _fechar_janela_grafico(self) -> None:
        """Fecha a janela de gráfico se estiver aberta."""
        if self._grafico_window and self._grafico_window.winfo_exists():
            safe_destroy_ctk_toplevel(self._grafico_window)
        self._grafico_window = None
        self._grafico_canvas = None

    def _obter_janela_grafico(self) -> ctk.CTkToplevel:
        """Obtém ou cria a janela de gráfico de detecção."""
        if self._grafico_window and self._grafico_window.winfo_exists():
            self._grafico_window.lift()
            self._grafico_window.focus_force()
            return self._grafico_window

        janela = ctk.CTkToplevel(self)
        janela.title("Gráfico de Detecção")
        janela.geometry("1100x700")
        center_window(janela, width=1100, height=700)
        janela.transient(self)
        janela.protocol("WM_DELETE_WINDOW", self._fechar_janela_grafico)
        self._grafico_window = janela
        return janela

    def _gerar_grafico(self) -> None:
        """Gera gráfico de detecção (Detectáveis e Indeterminados por Alvo)."""
        try:
            from tkinter import TclError
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from application.graph_use_cases import (
                build_detection_graph_data,
                build_detection_graph_figure,
            )

            # Preparar colunas de resultado apenas para validação de entrada
            result_cols = [
                c
                for c in self.df_analise.columns
                if str(c).startswith("Resultado_") or str(c).startswith("Res_")
            ]
            if not result_cols:
                messagebox.showerror(
                    "Erro", "Nenhuma coluna de resultado encontrada.", parent=self
                )
                return

            graph_data = build_detection_graph_data(self.df_analise, sort_labels=True)
            if not graph_data.labels:
                messagebox.showwarning(
                    "Aviso",
                    "Nenhum alvo relevante para exibir no gráfico.",
                    parent=self,
                )
                return

            janela = self._obter_janela_grafico()
            if self._grafico_canvas:
                self._grafico_canvas.get_tk_widget().destroy()
                self._grafico_canvas = None

            fig = build_detection_graph_figure(graph_data)
            canvas = FigureCanvasTkAgg(fig, master=janela)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
            self._grafico_canvas = canvas
            janela.focus_force()

            registrar_log(
                "Grafico",
                f"Gráfico agrupado gerado com {len(graph_data.labels)} alvos (relatório estatístico).",
                "INFO",
            )
        except (ImportError, TclError, RuntimeError) as exc:
            registrar_log("Grafico", f"Erro ao abrir gráfico: {exc}", "ERROR")
            messagebox.showerror(
                "Erro",
                "Falha ao gerar gráfico. Verifique a instalação do Tk/Tcl no Python.",
                parent=self,
            )
        except Exception as exc:
            import traceback
            erro = traceback.format_exc()
            registrar_log("Grafico", f"Erro: {erro}", "ERROR")
            messagebox.showerror("Erro", f"Falha ao gerar gráfico:\n{exc}", parent=self)

    def _salvar_selecionados(self):
        """Salva TODAS as amostras no histórico e pergunta sobre envio ao GAL."""
        try:
            from services.reports.history_report import gerar_historico_csv
            from db.db_utils import salvar_historico_processamento
            from exportacao.gal_formatter import formatar_para_gal
            from datetime import datetime, timezone
            
            # ✅ CORREÇÃO #1: Detecção robusta de coluna de código com fallback
            col_codigo = None
            for nome_possivel in ["Codigo", "Código", "CÓDIGO", "CODE", "Code"]:
                if nome_possivel in self.df_analise.columns:
                    col_codigo = nome_possivel
                    break
            
            if col_codigo is None:
                colunas_disponiveis = ", ".join(self.df_analise.columns[:10])
                messagebox.showerror(
                    "Erro",
                    f"Nenhuma coluna de código encontrada no DataFrame.\n\n"
                    f"Colunas disponíveis: {colunas_disponiveis}...",
                    parent=self
                )
                registrar_log("Salvar", f"Coluna de código não encontrada. Tentativas: Codigo, Código, CODE", "ERROR")
                return
            
            # Preparar TODAS as amostras (não apenas selecionadas)
            df_todas = self.df_analise[self.df_analise[col_codigo].notna() & (self.df_analise[col_codigo] != "")]
            selecionados = self.df_analise[self.df_analise["Selecionado"] == True]
            
            if len(df_todas) == 0:
                messagebox.showinfo("Informação", "Nenhuma amostra para salvar.", parent=self)
                return
            
            # PASSO 1: Salvar TODAS no histórico CSV
            from services.core.config_service import config_service
            paths = config_service.get_paths()
            caminho_csv = paths.get("gal_history_csv", "logs/historico_analises.csv")
            app_state = getattr(self.main_window, "app_state", None)
            
            gerar_historico_csv(
                df_todas,
                exame=self.exame,
                usuario=self.usuario_logado,
                lote=self.lote,
                data_exame=self.data_placa_formatada,
                arquivo_corrida=self.arquivo_corrida,
                nome_corrida=str(getattr(app_state, "nome_corrida", "") or ""),
                quem_fez_extracao=str(getattr(app_state, "quem_fez_extracao", "") or ""),
                quem_preparou_placa=str(getattr(app_state, "quem_preparou_placa", "") or ""),
                observacoes=str(getattr(app_state, "observacoes_corrida", "") or ""),
                arquivo_extracao=str(getattr(app_state, "caminho_arquivo_extracao", "") or ""),
                parte_placa=getattr(app_state, "parte_placa", None),
                numero_extracao=str(getattr(app_state, "numero_extracao", "") or ""),
                caminho_csv=caminho_csv,
            )
            
            # Salvar também no PostgreSQL
            detalhes = f"Placa: {self.num_placa}; {len(df_todas)} amostras salvas."
            salvar_historico_processamento(
                self.usuario_logado, self.exame, "Concluído", detalhes
            )
            
            registrar_log("Histórico", f"{len(df_todas)} amostras salvas no histórico", "INFO")
            
            # PASSO 2: Verificar se há selecionadas para envio ao GAL
            if len(selecionados) == 0:
                messagebox.showinfo(
                    "Historico Salvo",
                    f"OK! {len(df_todas)} amostras salvas no historico.\n\nAVISO: Nenhuma selecionada para envio ao GAL.",
                    parent=self
                )
                return
            
            # PASSO 3: Perguntar sobre envio ao GAL
            resposta = messagebox.askyesno(
                "Enviar para GAL?",
                f"OK! {len(df_todas)} amostras salvas no historico!\n\n{len(selecionados)} amostras selecionadas.\n\nDeseja enviar as selecionadas para o GAL?",
                parent=self
            )
            
            if resposta:
                self._enviar_para_gal(selecionados)
            else:
                messagebox.showinfo("Concluído", "Histórico salvo. Envio ao GAL cancelado.", parent=self)
            
        except Exception as e:
            registrar_log("Salvar", f"Erro: {e}", "ERROR")
            messagebox.showerror("Erro", f"Falha ao salvar:\n{e}", parent=self)
    
    def _enviar_para_gal(self, df_selecionadas):
        """Processa envio das amostras selecionadas para o GAL."""
        try:
            from exportacao.gal_formatter import exportar_csv_gal_oficial
            from services.core.config_service import config_service
            from services.analysis.final_run_report import (
                resolve_corrida_id,
                upsert_final_report_with_export_refs,
            )
            import os

            export_result = exportar_csv_gal_oficial(
                df_selecionadas,
                exam_cfg=None,
                exame=self.exame,
            )
            df_gal = export_result.dataframe
            gal_path = export_result.gal_path
            
            registrar_log("GAL Export", f"CSV GAL gerado: {gal_path}", "INFO")
            
            # Notificar usuário
            messagebox.showinfo(
                "CSV GAL Gerado",
                f"OK! CSV do GAL salvo com sucesso!\n\nArquivo: {os.path.basename(gal_path)}\n{len(df_gal)} amostras",
                parent=self
            )
            try:
                app_state = getattr(self.main_window, "app_state", None)
                corrida_id = resolve_corrida_id(
                    corrida_id=getattr(app_state, "corrida_id", ""),
                    exame_id=self.exame,
                    lote=self.lote,
                    data_exame=self.data_placa_formatada,
                    arquivo_corrida=self.arquivo_corrida,
                )
                paths = config_service.get_paths()
                historico_csv = paths.get("gal_history_csv", "logs/historico_analises.csv")
                logs_dir = os.path.dirname(str(historico_csv)) or "logs"
                upsert_final_report_with_export_refs(
                    logs_dir=logs_dir,
                    corrida_id=corrida_id,
                    export_refs=[export_result.gal_path, export_result.gal_last_path],
                    context={
                        "exame_id": str(self.exame or ""),
                        "lote": str(self.lote or ""),
                        "data_exame": str(self.data_placa_formatada or ""),
                        "arquivo_corrida": str(self.arquivo_corrida or ""),
                        "arquivo_extracao": str(
                            getattr(app_state, "caminho_arquivo_extracao", "") or ""
                        ),
                        "parte_placa": getattr(app_state, "parte_placa", None),
                        "numero_extracao": str(
                            getattr(app_state, "numero_extracao", "") or ""
                        ),
                        "usuario_execucao": str(self.usuario_logado or ""),
                        "observacoes": str(
                            getattr(app_state, "observacoes_corrida", "") or ""
                        ),
                    },
                )
            except Exception as exc:
                registrar_log(
                    "GAL Export",
                    f"Falha ao atualizar relatorio final canonico com trilha de exportacao: {exc}",
                    "WARNING",
                )
            
        except Exception as e:
            registrar_log("GAL", f"Erro ao enviar para GAL: {e}", "ERROR")
            messagebox.showerror("Erro GAL", f"Falha ao processar GAL:\n{e}", parent=self)
            messagebox.showerror("Erro", f"Falha ao enviar para GAL:\n{e}", parent=self)
    
    def _abrir_mapa_definitivo(self):
        """Abre o Mapa da Placa definitivo em .xlsx gerado mais recente."""
        if hasattr(self, '_ultimo_mapa_gerado') and self._ultimo_mapa_gerado:
            import os
            try:
                os.startfile(self._ultimo_mapa_gerado)
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao abrir arquivo:\n{e}", parent=self)
        else:
            messagebox.showinfo("Aviso", "Gere o Mapa da Placa definitivo primeiro para poder abri-lo.", parent=self)
    
    def _gerar_mapa_placa_definitivo(self):
        """Gera o Mapa da Placa definitivo em .xlsx para arquivamento.

        Lê o df_analise atual, ExamConfig (pocos_por_amostra, ordem de alvos)
        e delega para exportacao.mapa_placa_exporter.gerar_mapa_placa_xlsx.
        """
        try:
            from exportacao.mapa_placa_exporter import gerar_mapa_placa_xlsx
            from services.exam_registry import get_exam_cfg
            import os

            if self.df_analise is None or len(self.df_analise) == 0:
                messagebox.showinfo(
                    "Mapa da Placa",
                    "Nenhum dado de analise disponivel para gerar o mapa.",
                    parent=self,
                )
                return

            try:
                cfg = get_exam_cfg(self.exame)
            except Exception:
                cfg = None
            pocos_por_amostra = int(getattr(cfg, "pocos_por_amostra", 1) or 1)
            ordem_alvos = list(getattr(cfg, "alvos", []) or [])

            nome_placa = "placa"
            if self.arquivo_corrida:
                nome_placa = os.path.splitext(os.path.basename(self.arquivo_corrida))[0]

            from services.core.config_service import config_service
            data_root = config_service.get("data_root", os.getcwd())
            diretorio_saida = os.path.join(data_root, "mapas")
            os.makedirs(diretorio_saida, exist_ok=True)

            app_state = getattr(self.main_window, "app_state", None)
            nome_op = getattr(app_state, "quem_analisou_placa", "") or getattr(app_state, "quem_preparou_placa", "") or "Usuário Desconhecido"

            caminho = gerar_mapa_placa_xlsx(
                df_analise=self.df_analise,
                nome_exame=str(self.exame or "Exame"),
                nome_placa=nome_placa,
                pocos_por_amostra=pocos_por_amostra,
                diretorio_saida=diretorio_saida,
                ordem_alvos=ordem_alvos or None,
                nome_operador=str(nome_op),
            )
            
            self._ultimo_mapa_gerado = caminho

            registrar_log(
                "Mapa Placa",
                f"Mapa definitivo gerado em: {caminho}",
                "INFO",
            )
            messagebox.showinfo(
                "Mapa da Placa gerado",
                f"Arquivo salvo em:\n{caminho}",
                parent=self,
            )
        except Exception as e:
            registrar_log(
                "Mapa Placa",
                f"Falha ao gerar mapa da placa definitivo: {e}",
                "ERROR",
            )
            messagebox.showerror(
                "Erro",
                f"Falha ao gerar Mapa da Placa:\n{e}",
                parent=self,
            )

    def _on_close(self):
        """Fecha janela/pagina com limpeza adequada."""
        try:
            self._unsubscribe_plate_saved_event()
            if self._is_page_mode:
                if self._on_close_callback is not None:
                    self._on_close_callback()
                else:
                    super().destroy()
                return

            if self._window is not None:
                safe_destroy_ctk_toplevel(self._window)
            else:
                safe_destroy_ctk_toplevel(self)
        except Exception as e:
            registrar_log("Fechar", f"Erro: {e}", "ERROR")

    def destroy(self):
        """Compatibilidade: garante fechamento da Toplevel no modo legado."""
        self._unsubscribe_plate_saved_event()
        if self._is_page_mode:
            return super().destroy()
        try:
            if self._window is not None:
                safe_destroy_ctk_toplevel(self._window)
            else:
                super().destroy()
        except Exception:
            super().destroy()

    def focus(self):
        if self._window is not None:
            return self._window.focus()
        return super().focus()

    def lift(self, aboveThis=None):
        if self._window is not None:
            return self._window.lift(aboveThis)
        return super().lift(aboveThis)


def create_analise_completa_page(parent: ctk.CTkFrame, main_window) -> ctk.CTkFrame:
    """Cria a analise completa como pagina no ModuleHost."""

    app_state = getattr(main_window, "app_state", None)
    df = getattr(app_state, "resultados_analise", None)
    if df is None or getattr(df, "empty", True):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True)
        ctk.CTkLabel(
            frame,
            text="Sem resultados para exibir. Execute a analise primeiro.",
            font=Theme.get_font_primary(size=14, weight="bold"),
        ).pack(expand=True)
        return frame

    def _go_back() -> None:
        nav = getattr(main_window, "navigation_manager", None)
        if nav and hasattr(nav, "navigate_to"):
            nav.navigate_to("dashboard")

    return JanelaAnaliseCompleta(
        main_window,
        dataframe=df,
        status_corrida="N/A",
        num_placa="N/A",
        data_placa_formatada="",
        agravos=["SC2", "HMPV", "INF A", "INF B", "ADV", "RSV", "HRV"],
        usuario_logado=getattr(app_state, "usuario_logado", "Desconhecido"),
        exame=getattr(app_state, "exame_selecionado", ""),
        lote=getattr(app_state, "lote", ""),
        arquivo_corrida=getattr(app_state, "caminho_arquivo_corrida", ""),
        bloco_tamanho=getattr(app_state, "bloco_tamanho", 1),
        numero_extracao=getattr(app_state, "numero_extracao", ""),
        host_frame=parent,
        on_close_callback=_go_back,
    )

