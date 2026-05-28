"""
Dashboard Principal - IntegaGal
Fase 3.1 - Interface Gráfica
"""

import customtkinter as ctk
from tkinter import ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional
import os

from .estilos import CORES, FONTES, STATUS_CORES, GRAFICO_CORES
from .componentes import criar_card_estatistica
from services.reports.history_report import HistoryReportService
from services.reports.dashboard_analytics import DashboardAnalyticsService
from utils.gui_utils import safe_destroy_ctk_toplevel
from utils.logger import registrar_log

# Importar sistema de alertas
try:
    from .sistema_alertas import (
        GerenciadorAlertas, CentroNotificacoes, gerar_alertas_exemplo,
        TipoAlerta, CategoriaAlerta,
    )
except ImportError:
    GerenciadorAlertas = None
    CentroNotificacoes = None
    gerar_alertas_exemplo = None
    TipoAlerta = None
    CategoriaAlerta = None

# Compatibilidade: expor classes usadas por testes legados
try:
    from .visualizador_exame import VisualizadorExame
    from .graficos_qualidade import GraficosQualidade
    from .historico_analises import HistoricoAnalises
except Exception:
    VisualizadorExame = None
    GraficosQualidade = None
    HistoricoAnalises = None


class Dashboard(ctk.CTkFrame):
    """
    Dashboard principal em modo legado (Toplevel) ou página (single-window).
    """

    def __init__(
        self,
        master=None,
        *,
        host_frame: Optional[ctk.CTkFrame] = None,
        on_navigate: Optional[Callable[[str], None]] = None,
        on_close_callback: Optional[Callable[[], None]] = None,
    ):
        self._is_page_mode = host_frame is not None
        self._window: Optional[ctk.CTkToplevel] = None
        self._navigate_callback = on_navigate
        self._on_close_callback = on_close_callback

        if self._is_page_mode:
            super().__init__(master=host_frame)
            self.pack(expand=True, fill="both")
        else:
            self._window = ctk.CTkToplevel(master=master)
            super().__init__(master=self._window)
            self.pack(expand=True, fill="both")

        self._parent = master
        self._graficos_window = None
        self._historico_window = None
        self._criando_graficos_window = False
        self._criando_historico_window = False
        self._closing = False

        if self._window is not None:
            self._window.title("IntegaGal - Dashboard de Analises")
            self._window.geometry("1400x900")
            if master is not None:
                self._window.transient(master)

        self.df_historico = None
        self.cards = {}
        self.cards_gestao = {}
        self.analytics_service = DashboardAnalyticsService()
        self.periodo_gestao = 30

        if GerenciadorAlertas:
            self.gerenciador_alertas = GerenciadorAlertas()
        else:
            self.gerenciador_alertas = None
        self.badge_alertas = None
        self.btn_alertas = None

        self._criar_interface()

        if self.gerenciador_alertas:
            self.gerenciador_alertas.registrar_callback(self._atualizar_badge_alertas)

        self.carregar_dados()

        if self._window is not None:
            self._window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _navigate_route(self, route_name: str) -> bool:
        """Navega no modo pagina quando callback de navegacao estiver disponivel."""
        if not getattr(self, "_is_page_mode", False):
            return False
        callback = getattr(self, "_navigate_callback", None)
        if callback is None:
            return False
        callback(route_name)
        return True

    def _criar_interface(self):
        """Cria toda a interface do dashboard"""
        # Configurar grid principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Container principal com scroll (criado antes do header que o usa como pai)
        self.main_container = ctk.CTkScrollableFrame(
            self,
            fg_color=CORES['fundo'],
            corner_radius=0
        )
        self.main_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # Header
        self._criar_header()
        
        # Abas
        self.tabview = ctk.CTkTabview(self.main_container, fg_color="transparent")
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        
        self.tab_operacional = self.tabview.add("Operacional")
        self.tab_gestao = self.tabview.add("Gestão Clínica")
        
        self.tab_operacional.grid_columnconfigure(0, weight=1)
        self.tab_gestao.grid_columnconfigure(0, weight=1)
        
        # Setup Operacional
        self._criar_secao_cards(self.tab_operacional)
        self._criar_secao_grafico(self.tab_operacional)
        self._criar_secao_tabela(self.tab_operacional)
        
        # Setup Gestao
        self._criar_filtro_gestao(self.tab_gestao)
        self._criar_secao_cards_gestao(self.tab_gestao)
        self._criar_secao_grafico_gestao(self.tab_gestao)
    
    def _criar_header(self):
        """Cria header moderno com saudação e data"""
        from ui.theme import Theme
        
        header = ctk.CTkFrame(
            self.main_container,
            fg_color="transparent"
        )
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 0))
        
        # Título Saudação
        usuario = "Usuário"
        
        # Tentar buscar do app_state se existir na hierarquia
        try:
            parent = self
            while parent:
                if hasattr(parent, 'app_state') and getattr(parent, 'app_state', None):
                    usuario = getattr(parent.app_state, "usuario_logado", "Usuário") or "Usuário"
                    break
                parent = parent.master
        except Exception:
            pass

        label_titulo = ctk.CTkLabel(
            header,
            text=f"Bem-vindo de volta, {usuario} 👋",
            font=Theme.get_font_primary(size=24, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        label_titulo.pack(anchor="w")
        
        self.banner_dados = None
    
    def _criar_secao_cards(self, parent):
        """Cria seção de cards de resumo"""
        frame_cards = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )
        frame_cards.grid(row=1, column=0, sticky="ew", padx=20, pady=20)
        frame_cards.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        self.cards['total'] = criar_card_estatistica(
            frame_cards,
            titulo="Total de Análises",
            valor="0",
            tipo="info",
            indicativo_texto="+12% esta semana"
        )
        self.cards['total'].grid(row=0, column=0, sticky="ew", padx=10)
        
        self.cards['validas'] = criar_card_estatistica(
            frame_cards,
            titulo="Taxa de Sucesso",
            valor="0%",
            tipo="sucesso",
            indicativo_texto="+0.4% esta semana"
        )
        self.cards['validas'].grid(row=0, column=1, sticky="ew", padx=10)
        
        self.cards['alertas'] = criar_card_estatistica(
            frame_cards,
            titulo="Alertas Críticos",
            valor="0",
            tipo="erro",
            indicativo_texto="-2 de ontem"
        )
        self.cards['alertas'].grid(row=0, column=2, sticky="ew", padx=10)
        
        self.cards['ultima'] = criar_card_estatistica(
            frame_cards,
            titulo="Revisão Pendente",
            valor="0",
            tipo="aviso",
            indicativo_texto="4 alta prioridade"
        )
        self.cards['ultima'].grid(row=0, column=3, sticky="ew", padx=10)
    
    def _criar_secao_grafico(self, parent):
        """Cria seção com gráfico de tendências"""
        from ui.theme import Theme
        
        # Container do gráfico
        frame_grafico = ctk.CTkFrame(
            parent,
            fg_color=Theme.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=Theme.BORDER_DEFAULT
        )
        frame_grafico.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        frame_grafico.grid_columnconfigure(0, weight=1)
        
        # Título
        label_titulo = ctk.CTkLabel(
            frame_grafico,
            text="📊 Análises por Dia (Últimos 30 dias)",
            font=Theme.get_font_primary(size=14, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        label_titulo.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 10))
        
        # Frame para o gráfico matplotlib
        self.frame_canvas_grafico = ctk.CTkFrame(
            frame_grafico,
            fg_color=Theme.BG_CARD
        )
        self.frame_canvas_grafico.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15))
        
        # Placeholder - será preenchido em carregar_dados()
        self.canvas_grafico = None
    
    def _criar_secao_tabela(self, parent):
        """Cria seção com tabela de análises recentes"""
        from ui.theme import Theme
        
        # Container da tabela
        frame_tabela = ctk.CTkFrame(
            parent,
            fg_color=Theme.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=Theme.BORDER_DEFAULT
        )
        frame_tabela.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        frame_tabela.grid_columnconfigure(0, weight=1)
        
        # Título
        label_titulo = ctk.CTkLabel(
            frame_tabela,
            text="📋 Corridas Recentes",
            font=Theme.get_font_primary(size=14, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        label_titulo.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 10))
        
        self.entry_busca = ctk.CTkEntry(
            frame_tabela,
            placeholder_text="🔎 Buscar corrida (exame, data, equipamento)...",
            width=300
        )
        self.entry_busca.grid(row=0, column=1, sticky="e", padx=20, pady=(15, 10))
        self.entry_busca.bind("<KeyRelease>", self._atualizar_tabela)
        
        # Frame para a tabela
        frame_tree = ctk.CTkFrame(
            frame_tabela,
            fg_color=Theme.BG_CARD
        )
        frame_tree.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15))
        frame_tree.grid_columnconfigure(0, weight=1)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical")
        
        # Treeview (tabela)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=Theme.BG_CARD,
            foreground=Theme.TEXT_SECONDARY,
            rowheight=35,
            fieldbackground=Theme.BG_CARD,
            font=("Segoe UI", 11)
        )
        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 11, "bold"),
            background=Theme.BG_ROOT,
            foreground=Theme.TEXT_MUTED,
            borderwidth=0
        )
        style.map('Treeview', background=[('selected', Theme.PRIMARY_BLUE_LIGHT)], foreground=[('selected', Theme.PRIMARY_BLUE_HOVER)])
        
        self.tree = ttk.Treeview(
            frame_tabela,
            columns=("data_hora", "exame", "equipamento", "status", "corrida_id"),
            displaycolumns=("data_hora", "exame", "equipamento", "status"),
            show="headings",
            yscrollcommand=scrollbar.set,
            style="Historico.Treeview"
        )
        
        # Configurar colunas
        self.tree.heading("data_hora", text="Data/Hora")
        self.tree.heading("exame", text="Exame")
        self.tree.heading("equipamento", text="Equipamento")
        self.tree.heading("status", text="Status")
        
        self.tree.column("data_hora", width=150, anchor="w")
        self.tree.column("exame", width=250, anchor="w")
        self.tree.column("equipamento", width=200, anchor="w")
        self.tree.column("status", width=120, anchor="center")
        
        scrollbar.config(command=self.tree.yview)
        
        self.tree.grid(row=0, column=0, sticky="ew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Bind para duplo clique (futura navegação para detalhes)
        self.tree.bind("<Double-1>", self._on_item_double_click)
    

    def _criar_filtro_gestao(self, parent):
        from ui.theme import Theme
        frame_filtro = ctk.CTkFrame(parent, fg_color="transparent")
        frame_filtro.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        
        label_filtro = ctk.CTkLabel(frame_filtro, text="Período:", font=Theme.get_font_primary(size=14, weight="bold"))
        label_filtro.pack(side="left", padx=(0, 10))
        
        def on_filter_change(choice):
            if choice == "Últimos 7 dias": self.periodo_gestao = 7
            elif choice == "Últimos 30 dias": self.periodo_gestao = 30
            elif choice == "Últimos 6 meses": self.periodo_gestao = 180
            self._atualizar_dados_gestao()

        self.filtro_periodo = ctk.CTkOptionMenu(
            frame_filtro,
            values=["Últimos 7 dias", "Últimos 30 dias", "Últimos 6 meses"],
            command=on_filter_change
        )
        self.filtro_periodo.set("Últimos 30 dias")
        self.filtro_periodo.pack(side="left")
        
        label_exame = ctk.CTkLabel(frame_filtro, text="Exame:", font=Theme.get_font_primary(size=14, weight="bold"))
        label_exame.pack(side="left", padx=(20, 10))
        
        def on_exame_change(choice):
            self.exame_gestao = choice
            self._atualizar_dados_gestao()

        self.exame_gestao = "Todos"
        self.filtro_exame = ctk.CTkOptionMenu(
            frame_filtro,
            values=["Todos"],
            command=on_exame_change
        )
        self.filtro_exame.set("Todos")
        self.filtro_exame.pack(side="left")

    def _criar_secao_cards_gestao(self, parent):
        frame_cards = ctk.CTkFrame(parent, fg_color="transparent")
        frame_cards.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        frame_cards.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.cards_gestao['volume'] = criar_card_estatistica(
            frame_cards, titulo="Volume de Exames", valor="0", tipo="info", indicativo_texto="0%"
        )
        self.cards_gestao['volume'].grid(row=0, column=0, sticky="ew", padx=10)
        
        self.cards_gestao['positividade'] = criar_card_estatistica(
            frame_cards, titulo="Positividade Global", valor="0%", tipo="sucesso", indicativo_texto="0%"
        )
        self.cards_gestao['positividade'].grid(row=0, column=1, sticky="ew", padx=10)
        
        self.cards_gestao['tat'] = criar_card_estatistica(
            frame_cards, titulo="TAT Médio (Dias)", valor="N/D", tipo="aviso", indicativo_texto="-"
        )
        self.cards_gestao['tat'].grid(row=0, column=2, sticky="ew", padx=10)

    def _criar_secao_grafico_gestao(self, parent):
        from ui.theme import Theme
        frame_grafico = ctk.CTkFrame(parent, fg_color=Theme.BG_CARD, corner_radius=8)
        frame_grafico.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        parent.grid_rowconfigure(2, weight=1)
        frame_grafico.grid_columnconfigure(0, weight=1)
        frame_grafico.grid_rowconfigure(1, weight=1)
        
        label_titulo = ctk.CTkLabel(
            frame_grafico, text="📊 Doenças Mais Positivas", font=Theme.get_font_primary(size=14, weight="bold")
        )
        label_titulo.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 10))
        
        self.frame_canvas_gestao = ctk.CTkFrame(frame_grafico, fg_color=Theme.BG_CARD)
        self.frame_canvas_gestao.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 15))
        self.canvas_gestao = None

    def _atualizar_dados_gestao(self):
        try:
            exame_atual = getattr(self, "exame_gestao", "Todos")
            stats = self.analytics_service.obter_estatisticas_gestao(self.periodo_gestao, exame_filtro=exame_atual)
            
            unique_exams = stats.get("unique_exams", [])
            if unique_exams and hasattr(self, "filtro_exame"):
                valores_exames = ["Todos"] + unique_exams
                current_val = self.filtro_exame.get()
                self.filtro_exame.configure(values=valores_exames)
                if current_val in valores_exames:
                    self.filtro_exame.set(current_val)
                else:
                    self.filtro_exame.set("Todos")
                    self.exame_gestao = "Todos"
            
            # Atualiza Volume
            vol = stats.get("current_volume", 0)
            d_vol = stats.get("delta_volume", 0.0)
            s_vol = "+" if d_vol >= 0 else ""
            if "volume" in self.cards_gestao:
                self.cards_gestao["volume"].set_valor(str(vol))
                self.cards_gestao["volume"].set_indicativo(f"{s_vol}{d_vol:.1f}% vs ant.")
            
            # Atualiza Positividade
            pos = stats.get("current_positivity", 0.0)
            d_pos = stats.get("delta_positivity", 0.0)
            s_pos = "+" if d_pos >= 0 else ""
            if "positividade" in self.cards_gestao:
                self.cards_gestao["positividade"].set_valor(f"{pos:.1f}%")
                self.cards_gestao["positividade"].set_indicativo(f"{s_pos}{d_pos:.1f} pp vs ant.")
                
            # Atualiza Grafico de Barras
            top_diseases = stats.get("top_positive_diseases", [])
            self._atualizar_grafico_gestao(top_diseases)
            
        except Exception as e:
            registrar_log(f"Erro ao carregar dados de gestao: {str(e)}", level="error")

    def _atualizar_grafico_gestao(self, top_diseases):
        if hasattr(self, 'canvas_gestao') and self.canvas_gestao:
            self.canvas_gestao.get_tk_widget().destroy()
            
        fig = Figure(figsize=(8, 4), dpi=100)
        fig.patch.set_facecolor(CORES['fundo_card'])
        ax = fig.add_subplot(111)
        ax.set_facecolor(CORES['fundo_card'])
        
        if top_diseases:
            labels = [d["alvo"] for d in top_diseases]
            values = [d["count"] for d in top_diseases]
            y_pos = range(len(labels))
            ax.barh(y_pos, values, color=GRAFICO_CORES[0])
            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, color=CORES['texto_secundario'])
            ax.invert_yaxis()
            ax.tick_params(colors=CORES['texto_secundario'])
            for spine in ax.spines.values():
                spine.set_color(CORES['borda'])
        else:
            ax.text(0.5, 0.5, "Sem dados suficientes", ha="center", va="center", color=CORES['texto_secundario'])
            ax.set_axis_off()
            
        fig.tight_layout()
        self.canvas_gestao = FigureCanvasTkAgg(fig, master=self.frame_canvas_gestao)
        self.canvas_gestao.draw()
        self.canvas_gestao.get_tk_widget().pack(fill="both", expand=True)

    def carregar_dados(self):
        """
        Carrega dados do histórico de análises DE FORMA ASSÍNCRONA.
        
        OTIMIZAÇÃO CRÍTICA (2026-01-08):
        - Implementado threading para não bloquear UI durante leitura de CSV pesado
        - Polling via .after() mantém Tkinter responsivo
        - Tela de loading exibida enquanto dados são processados
        """
        # Mostrar indicador de loading
        self._mostrar_loading()
        
        # Iniciar carregamento em background
        from threading import Thread
        from queue import Queue
        
        self._data_queue = Queue()
        worker = Thread(target=self._carregar_dados_worker, args=(self._data_queue,), daemon=True)
        worker.start()
        
        # Polling para verificar quando dados estiverem prontos
        self._verificar_dados_carregados()
    
    def _mostrar_loading(self):
        """Exibe tela de carregamento enquanto dados são processados."""
        # Limpar conteúdo anterior
        for widget in self.main_container.winfo_children():
            widget.destroy()
        
        # Frame de loading
        loading_frame = ctk.CTkFrame(self.main_container)
        loading_frame.pack(expand=True)
        
        ctk.CTkLabel(
            loading_frame,
            text="⏳ Carregando Dashboard...",
            font=("Arial", 18, "bold")
        ).pack(pady=20)
        
        self.loading_label = ctk.CTkLabel(
            loading_frame,
            text="Lendo histórico de análises...",
            font=("Arial", 12)
        )
        self.loading_label.pack(pady=10)
    
    def _carregar_dados_worker(self, result_queue):
        """
        Worker thread que carrega dados em background.
        NÃO PODE TOCAR NA UI - apenas processa dados.
        """
        try:
            dados = {"df": None, "origem": None, "erro": None}

            # 1. Fonte canônica via service (provider + fallback contratual)
            try:
                df_hist = HistoryReportService().ler_historico(limit=1000)
                if df_hist is not None and not df_hist.empty:
                    df = df_hist.copy()
                    if 'status' in df.columns and 'status_corrida' not in df.columns:
                        df['status_corrida'] = df['status']
                    if 'equipamento' not in df.columns:
                        df['equipamento'] = df.get('exame', 'N/A')
                    if 'data_hora' not in df.columns and 'data_hora_analise' in df.columns:
                        df['data_hora'] = df['data_hora_analise']
                    df = self._normalizar_dataframe_historico(df)

                    dados["df"] = df
                    dados["origem"] = "HistoryReportService"
                    result_queue.put(dados)
                    return
            except Exception:
                pass

            # 2. Fallback legado via db_utils
            try:
                from db.db_utils import obter_historico_analises
                df_db = obter_historico_analises(limit=1000)

                if df_db is not None and not df_db.empty:
                    df = df_db.copy()
                    if 'status' in df.columns:
                        df['status_corrida'] = df['status']
                    if 'equipamento' not in df.columns:
                        df['equipamento'] = df.get('exame', 'N/A')
                    if 'data_hora' not in df.columns and 'data_hora_analise' in df.columns:
                        df['data_hora'] = df['data_hora_analise']
                    df = self._normalizar_dataframe_historico(df)

                    dados["df"] = df
                    dados["origem"] = "Banco de Dados"
                    result_queue.put(dados)
                    return
            except Exception as e:
                dados["erro"] = f"Erro ao carregar histórico: {e}"

            # 3. Nenhuma fonte disponível - usar dados de exemplo
            dados["df"] = None
            dados["origem"] = "Exemplo"
            result_queue.put(dados)

        except Exception as e:
            result_queue.put({"df": None, "origem": None, "erro": str(e)})

    def _verificar_dados_carregados(self):
        """
        Polling - verifica se worker thread terminou.
        Chama a si mesmo via .after() até dados estarem prontos.
        """
        if not self._data_queue.empty():
            # Dados prontos!
            resultado = self._data_queue.get()
            
            if resultado.get("erro"):
                print(f"[ERRO] Erro ao carregar dados: {resultado['erro']}")
                self._criar_dados_exemplo()
                self._finalizar_carregamento(exemplo=True)
            elif resultado["df"] is not None:
                self.df_historico = resultado["df"]
                print(f"[OK] Dashboard carregado com {len(self.df_historico)} registros de {resultado['origem']}")
                self._finalizar_carregamento(origem=resultado["origem"])
            else:
                # Sem dados - usar exemplo
                self._criar_dados_exemplo()
                self._finalizar_carregamento(exemplo=True)
        else:
            # Ainda processando - verificar novamente em 100ms
            self.after(100, self._verificar_dados_carregados)
    
    def _finalizar_carregamento(self, origem=None, exemplo=False):
        """Atualiza UI após dados carregados - THREAD-SAFE."""
        # Limpar loading screen
        for widget in self.main_container.winfo_children():
            widget.destroy()
        
        # Recriar interface
        self._criar_interface()

        # Gerar alertas reais a partir dos dados carregados
        if self.gerenciador_alertas and self.df_historico is not None and not exemplo:
            self._gerar_alertas_reais()

        # Atualizar com dados
        self._atualizar_interface_com_dados()
    
    def _on_item_double_click(self, event):
        """Handler para duplo clique na tabela - abre visualizador"""
        item = self.tree.selection()
        if not item:
            return
        
        valores = self.tree.item(item[0])['values']
        data_hora = valores[0]
        exame = valores[1]
        equipamento = valores[2]
        status = valores[3]
        
        try:
            # Importar visualizador
            from .visualizador_exame import VisualizadorExame, criar_dados_exame_exemplo
    
        except Exception as e:
            registrar_log("Dashboard", f"Erro ao carregar dados: {e}", "WARNING")
            # Continuar sem dados se falhar
    
    def _mostrar_banner_dados_reais(self, origem="Dados Reais"):
        """Mostra banner indicando que está usando dados reais"""
        if self.banner_dados:
            self.banner_dados.destroy()
        
        self.banner_dados = ctk.CTkFrame(
            self.main_container,
            fg_color="#28a745",  # Verde
            corner_radius=8,
            height=40
        )
        self.banner_dados.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 10))
        
        ctk.CTkLabel(
            self.banner_dados,
            text=f"✅ Dashboard com {origem} ({len(self.df_historico)} registros)",
            font=("", 12, "bold"),
            text_color="white"
        ).pack(pady=10)
    
    def _mostrar_banner_dados_exemplo(self):
        """Mostra banner indicando que está usando dados de exemplo"""
        if self.banner_dados:
            self.banner_dados.destroy()
        
        self.banner_dados = ctk.CTkFrame(
            self.main_container,
            fg_color="#ff9800",  # Laranja
            corner_radius=8,
            height=40
        )
        self.banner_dados.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 10))
        
        ctk.CTkLabel(
            self.banner_dados,
            text="⚠️ DADOS DE EXEMPLO - Execute análises para ver dados reais",
            font=("", 12, "bold"),
            text_color="white"
        ).pack(pady=10)
    
    def _criar_dados_exemplo(self):
        """Cria dados de exemplo para demonstração"""
        # Dados fictícios para demonstração
        dados = []
        equipamentos = ["ABI 7500", "Biomanguinhos", "QuantStudio"]
        exames = ["VR1e2 Biomanguinhos", "Dengue PCR", "Zika RT-PCR", "Chikungunya"]
        status = ["Valida", "Valida", "Invalida", "Aviso"]
        
        for i in range(30):
            data = datetime.now() - timedelta(days=29-i)
            dados.append({
                'data_hora': data.strftime("%Y-%m-%d %H:%M:%S"),
                'exame': exames[i % len(exames)],
                'equipamento': equipamentos[i % len(equipamentos)],
                'status_corrida': status[i % len(status)],
                'analista': 'Usuario Teste'
            })
        
        self.df_historico = self._normalizar_dataframe_historico(pd.DataFrame(dados))

    @staticmethod
    def _parse_data_hora_series(values: pd.Series) -> pd.Series:
        """Converte datas em formatos mistos para datetime de forma tolerante."""
        raw = values.astype(str).str.strip()
        parsed = pd.to_datetime(raw, format="%Y-%m-%d %H:%M:%S", errors="coerce")
        for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d", "%d/%m/%Y"):
            missing = parsed.isna()
            if not missing.any():
                break
            parsed.loc[missing] = pd.to_datetime(raw.loc[missing], format=fmt, errors="coerce")
        return parsed

    def _normalizar_dataframe_historico(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza DataFrame de historico para renderizacao segura no dashboard."""
        normalized = df.copy()
        if 'status' in normalized.columns and 'status_corrida' not in normalized.columns:
            normalized['status_corrida'] = normalized['status']
        if 'equipamento' not in normalized.columns:
            normalized['equipamento'] = normalized.get('exame', 'N/A')
        if 'data_hora' not in normalized.columns and 'data_hora_analise' in normalized.columns:
            normalized['data_hora'] = normalized['data_hora_analise']
        if 'data_hora' not in normalized.columns:
            normalized['data_hora'] = ""

        normalized['data_hora_dt'] = self._parse_data_hora_series(normalized['data_hora'])
        invalid_dates = int(normalized['data_hora_dt'].isna().sum())
        if invalid_dates > 0:
            registrar_log(
                "Dashboard",
                (
                    "Normalizacao de data_hora com valores invalidos "
                    f"(total={len(normalized)}, invalidos={invalid_dates})."
                ),
                "WARNING",
            )
        return normalized
    
    def _atualizar_interface_com_dados(self):
        """Atualiza toda a interface com os dados carregados"""
        if self.df_historico is None or len(self.df_historico) == 0:
            return
        
        # Atualizar cards
        self._atualizar_cards()
        
        # Atualizar gráfico
        self._atualizar_grafico()
        
        # Atualizar tabela
        self._atualizar_tabela()
    
    def _gerar_alertas_reais(self):
        """Gera alertas baseados nos dados reais carregados."""
        if not self.gerenciador_alertas or not TipoAlerta or not CategoriaAlerta:
            return
        df = self.df_historico
        if df is None or df.empty:
            return

        # 1. Verificar placas invalidas recentes
        status_col = df.get('status_corrida', df.get('status', pd.Series(dtype=str)))
        status_norm = status_col.fillna('').str.strip().str.lower()
        invalidas = int((status_norm == 'invalida').sum())
        if invalidas > 0:
            self.gerenciador_alertas.criar_alerta(
                TipoAlerta.ALTO,
                CategoriaAlerta.QUALIDADE,
                f"{invalidas} analise(s) com status Invalida no historico",
                detalhes=f"Total de analises invalidas encontradas nos dados carregados: {invalidas}.",
            )

        # 2. GAL - envios nao realizados
        if 'status_gal' in df.columns:
            gal_falhas = df['status_gal'].fillna('').str.strip()
            nao_enviados = int((gal_falhas.isin(['não enviável', 'nao enviavel', 'erro', ''])).sum())
            if nao_enviados > 0:
                self.gerenciador_alertas.criar_alerta(
                    TipoAlerta.MEDIO,
                    CategoriaAlerta.SISTEMA,
                    f"{nao_enviados} registro(s) sem envio ao GAL",
                    detalhes="Registros com status GAL vazio, nao enviavel ou com erro.",
                )

        # 3. Quantidade total como info
        self.gerenciador_alertas.criar_alerta(
            TipoAlerta.INFO,
            CategoriaAlerta.SISTEMA,
            f"Historico carregado com {len(df)} registros reais",
            detalhes="Dados carregados com sucesso do HistoryReportService.",
        )

    def _atualizar_cards(self):
        """Atualiza valores dos cards de resumo"""
        if self.df_historico is None:
            return
        
        # Total
        total = len(self.df_historico)
        self.cards['total'].atualizar_valor(str(total))
        
        # Válidas
        validas = len(self.df_historico[self.df_historico['status_corrida'] == 'Valida'])
        self.cards['validas'].atualizar_valor(str(validas))
        
        # Alertas (avisos + inválidas)
        alertas = len(self.df_historico[self.df_historico['status_corrida'].isin(['Aviso', 'Invalida'])])
        self.cards['alertas'].atualizar_valor(str(alertas))
        
        # Última análise
        if len(self.df_historico) > 0:
            data_series = (
                self.df_historico['data_hora_dt']
                if 'data_hora_dt' in self.df_historico.columns
                else self._parse_data_hora_series(self.df_historico['data_hora'])
            )
            ultima = data_series.max()
            if pd.isna(ultima):
                self.cards['ultima'].atualizar_valor("--:--")
            else:
                self.cards['ultima'].atualizar_valor(ultima.strftime("%H:%M"))
    
    def _atualizar_grafico(self):
        """Atualiza gráfico de tendências"""
        if self.df_historico is None or len(self.df_historico) == 0:
            return
        
        # Limpar gráfico anterior
        if self.canvas_grafico:
            self.canvas_grafico.get_tk_widget().destroy()
        
        # Preparar dados
        df = self.df_historico.copy()
        if 'data_hora_dt' not in df.columns:
            df['data_hora_dt'] = self._parse_data_hora_series(df['data_hora'])
        df = df[df['data_hora_dt'].notna()].copy()
        if df.empty:
            return
        df['data'] = df['data_hora_dt'].dt.date
        
        # Agrupar por data
        df_agrupado = df.groupby('data').size().reset_index(name='count')
        
        # Criar figura matplotlib
        fig = Figure(figsize=(12, 4), dpi=100, facecolor=CORES['branco'])
        ax = fig.add_subplot(111)
        
        # Plotar linha
        ax.plot(
            df_agrupado['data'],
            df_agrupado['count'],
            color=CORES['primaria'],
            linewidth=2,
            marker='o',
            markersize=6,
            markerfacecolor=CORES['primaria'],
            markeredgecolor=CORES['branco'],
            markeredgewidth=2
        )
        
        # Estilo
        ax.set_xlabel('Data', fontsize=10)
        ax.set_ylabel('Quantidade', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_facecolor(CORES['branco'])
        
        # Rotacionar labels do eixo x
        fig.autofmt_xdate()
        
        # Ajustar layout
        fig.tight_layout()
        
        # Criar canvas tkinter
        self.canvas_grafico = FigureCanvasTkAgg(fig, master=self.frame_canvas_grafico)
        self.canvas_grafico.draw()
        self.canvas_grafico.get_tk_widget().pack(fill="both", expand=True)
    
    def _atualizar_tabela(self, event=None):
        """Atualiza tabela de análises recentes com suporte a busca"""
        if not hasattr(self, "df_historico") or self.df_historico is None:
            return
            
        termo = ""
        if hasattr(self, "entry_busca"):
            termo = self.entry_busca.get().lower().strip()
        
        # Limpar tabela
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        df_recentes = self.df_historico.copy()
        if 'data_hora_dt' not in df_recentes.columns:
            df_recentes['data_hora_dt'] = self._parse_data_hora_series(df_recentes['data_hora'])
            
        # Filtrar se houver termo
        if termo:
            mask = df_recentes.astype(str).apply(lambda x: x.str.lower().str.contains(termo, na=False)).any(axis=1)
            df_recentes = df_recentes[mask]
            
        df_recentes = df_recentes.sort_values('data_hora_dt', ascending=False).head(100 if termo else 20)
        
        # Adicionar linhas
        for _, row in df_recentes.iterrows():
            # Formatar data/hora
            dt = row.get('data_hora_dt')
            if pd.isna(dt):
                data_hora_fmt = str(row.get('data_hora', 'N/A'))
            else:
                data_hora_fmt = dt.strftime("%d/%m/%Y %H:%M")
            
            # Formatar status
            status_map = {
                'Valida': '✅ Válida',
                'Invalida': '❌ Inválida',
                'Aviso': '⚠️ Aviso'
            }
            status_fmt = status_map.get(row['status_corrida'], row.get('status_corrida', 'N/A'))
            
            # Inserir na tabela
            self.tree.insert(
                "",
                "end",
                values=(
                    data_hora_fmt,
                    row['exame'],
                    row['equipamento'],
                    status_fmt,
                    str(row.get('corrida_id', ''))
                )
            )
    
    def _on_item_double_click(self, event):
        """Handler para duplo clique na tabela - abre visualizador em tabela"""
        item = self.tree.selection()
        if not item:
            return
        
        valores = self.tree.item(item[0])['values']
        data_hora = valores[0]
        exame = valores[1]
        equipamento = valores[2]
        status = valores[3]
        corrida_id = valores[4] if len(valores) > 4 else ""
        
        try:
            self._abrir_detalhes_corrida(corrida_id, data_hora, exame, equipamento, status)
        except Exception as e:
            print(f"Erro ao abrir detalhes da corrida: {e}")

    def _abrir_detalhes_corrida(self, corrida_id, data_hora, exame, equipamento, status):
        # 1. Fetch data for this run
        from services.persistence.exam_runs_sqlite import ExamRunsSQLiteRepository
        repo = ExamRunsSQLiteRepository()
        rows = repo.list_rows()
        # Filter
        if corrida_id:
            run_rows = [r for r in rows if r.get('corrida_id') == corrida_id]
        else:
            # Fallback filter
            run_rows = [r for r in rows if (r.get('data_exame', '') in data_hora or data_hora in r.get('data_exame', '')) and r.get('equipamento_modelo') == equipamento]

        if not run_rows:
            import tkinter.messagebox as messagebox
            messagebox.showinfo("Detalhes da Corrida", "Nenhum dado detalhado encontrado para esta corrida no banco de dados local.")
            return

        import pandas as pd
        df = pd.DataFrame(run_rows)
        rename_map = {
            'amostra_codigo': 'Amostra',
            'pocos': 'Poço',
            'resultado_geral': 'Resultado_Geral',
            'status_placa': 'Status_Placa'
        }
        df = df.rename(columns=rename_map)

        cols_to_drop = ['id', 'corrida_id', 'exame_slug', 'equipamento_id', 'equipamento_modelo', 'data_exame', 'hora_exame', 'lote', 'criado_em', 'targets_json']
        df = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors='ignore')

        import customtkinter as ctk
        from ui.theme.design_tokens import CORES, FONTES
        
        janela = ctk.CTkToplevel(self)
        janela.title(f"Detalhes da Corrida - {exame}")
        janela.geometry("1100x650")
        janela.grab_set()

        header = ctk.CTkFrame(janela, fg_color=CORES['primaria'], corner_radius=0, height=80)
        header.pack(fill="x")
        
        lbl_title = ctk.CTkLabel(header, text=f"Resultados: {exame}", font=FONTES['titulo_grande'], text_color=CORES['branco'])
        lbl_title.pack(side="left", padx=20, pady=20)
        
        lbl_info = ctk.CTkLabel(header, text=f"{data_hora} | {equipamento} | {status}", font=FONTES['corpo'], text_color=CORES['branco'])
        lbl_info.pack(side="right", padx=20, pady=20)

        frame_tabela = ctk.CTkFrame(janela, fg_color="transparent")
        frame_tabela.pack(fill="both", expand=True, padx=20, pady=20)

        from tkinter import ttk
        columns = list(df.columns)
        
        # Use style defined in the system
        tree = ttk.Treeview(frame_tabela, columns=columns, show="headings", style="Historico.Treeview")
        
        scroll_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=tree.yview)
        scroll_x = ttk.Scrollbar(frame_tabela, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        
        for col in columns:
            tree.heading(col, text=col)
            width = 100
            if "Amostra" in col: width = 180
            elif "Resultado" in col: width = 120
            elif "Poço" in col: width = 60
            tree.column(col, width=width, anchor="center")

        for _, row_data in df.iterrows():
            # Apply some basic formatting
            values = [str(row_data.get(c, '')) for c in columns]
            tree.insert("", "end", values=values)
        
        tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")
        
        # Add a close button
        btn_fechar = ctk.CTkButton(janela, text="Fechar", command=janela.destroy, width=120, height=35)
        btn_fechar.pack(pady=10)
    
    def _abrir_graficos(self):
        """Abre tela de graficos no modo pagina ou janela legado."""
        try:
            if self.df_historico is None or len(self.df_historico) == 0:
                print("Dashboard sem dados para graficos")
                return
            if self._navigate_route("graficos_qualidade"):
                return
            if GraficosQualidade is None:
                print("GraficosQualidade indisponivel")
                return
            if getattr(self, "_criando_graficos_window", False):
                return
            existing = getattr(self, "_graficos_window", None)
            if existing is not None:
                try:
                    if existing.winfo_exists():
                        existing.focus()
                        existing.lift()
                        return
                except Exception:
                    pass
            self._criando_graficos_window = True
            self._graficos_window = GraficosQualidade(self, self.df_historico)
        except Exception as e:
            print(f"Erro ao abrir graficos: {e}")
        finally:
            self._criando_graficos_window = False

    def _abrir_historico(self):
        """Abre tela de historico no modo pagina ou janela legado."""
        try:
            if self.df_historico is None or len(self.df_historico) == 0:
                print("Dashboard sem dados para historico")
                return
            if self._navigate_route("historico_analises"):
                return
            if HistoricoAnalises is None:
                print("HistoricoAnalises indisponivel")
                return
            if getattr(self, "_criando_historico_window", False):
                return
            existing = getattr(self, "_historico_window", None)
            if existing is not None:
                try:
                    if existing.winfo_exists():
                        existing.focus()
                        existing.lift()
                        return
                except Exception:
                    pass
            self._criando_historico_window = True
            self._historico_window = HistoricoAnalises(self, self.df_historico)
        except Exception as e:
            print(f"Erro ao abrir historico: {e}")
        finally:
            self._criando_historico_window = False

    def _abrir_alertas(self):
        """Abre centro de notificacoes."""
        try:
            if not self.gerenciador_alertas or not CentroNotificacoes:
                print("Sistema de alertas nao disponivel")
                return
            CentroNotificacoes(self, self.gerenciador_alertas)
        except Exception as e:
            print(f"Erro ao abrir alertas: {e}")

    def _atualizar_badge_alertas(self):
        """Atualiza badge de alertas nao lidos."""
        try:
            if not self.gerenciador_alertas:
                return

            stats = self.gerenciador_alertas.get_estatisticas()
            nao_lidos = stats['nao_lidos']

            if nao_lidos > 0:
                texto = str(nao_lidos) if nao_lidos < 100 else "99+"
                if self.badge_alertas:
                    self.badge_alertas.configure(text=texto)
                elif hasattr(self, 'btn_alertas') and self.btn_alertas:
                    frame_alertas = self.btn_alertas.master
                    self.badge_alertas = ctk.CTkLabel(
                        frame_alertas,
                        text=texto,
                        fg_color=CORES['erro'],
                        text_color=CORES['branco'],
                        corner_radius=10,
                        width=24,
                        height=24,
                        font=('Segoe UI', 10, 'bold')
                    )
                    self.badge_alertas.place(x=95, y=5)
            else:
                if self.badge_alertas:
                    self.badge_alertas.destroy()
                    self.badge_alertas = None
        except Exception as e:
            print(f"Erro ao atualizar badge: {e}")

    def _on_close(self):
        if self._closing:
            return
        self._closing = True

        if getattr(self, "_is_page_mode", False):
            callback = getattr(self, "_on_close_callback", None)
            if callback is not None:
                callback()
            else:
                self.destroy()
            return

        try:
            if self._graficos_window is not None and self._graficos_window.winfo_exists():
                safe_destroy_ctk_toplevel(self._graficos_window)
        except Exception:
            pass
        try:
            if self._historico_window is not None and self._historico_window.winfo_exists():
                safe_destroy_ctk_toplevel(self._historico_window)
        except Exception:
            pass
        try:
            if self._parent is not None and hasattr(self._parent, 'menu_handler'):
                handler = self._parent.menu_handler
                if getattr(handler, '_dashboard_window', None) is self:
                    handler._dashboard_window = None
        except Exception:
            pass

        window = getattr(self, "_window", None)
        if window is not None:
            safe_destroy_ctk_toplevel(window)
        else:
            try:
                safe_destroy_ctk_toplevel(self)
            except Exception:
                # Em testes de unidade, o objeto pode ser criado via __new__
                # sem inicializacao completa do Tk.
                if hasattr(self, "_w") and hasattr(self, "children"):
                    self.destroy()

    def _voltar_menu(self) -> None:
        """Retorna ao menu principal em modo pagina ou fecha janela no modo legado."""
        if self._navigate_route("main_menu"):
            return
        self._on_close()

    def atualizar_dados(self):
        """Recarrega dados e atualiza interface."""
        self.carregar_dados()


def create_dashboard_page(parent: ctk.CTkFrame, main_window) -> ctk.CTkFrame:
    """Cria dashboard como pagina para o ModuleHost."""

    def _navigate(route_name: str) -> None:
        nav = getattr(main_window, "navigation_manager", None)
        if nav and hasattr(nav, "navigate_to"):
            nav.navigate_to(route_name)

    def _close() -> None:
        _navigate("main_menu")

    page = Dashboard(
        master=main_window,
        host_frame=parent,
        on_navigate=_navigate,
        on_close_callback=_close,
    )
    return page

def main():
    """Função principal para executar o dashboard"""
    app = Dashboard()
    app.mainloop()


if __name__ == '__main__':
    main()

