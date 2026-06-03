import re

filepath = r"c:\Integragal\Integragal - Backup - 20260128_151811\ui\modules\dashboard.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Imports
if "DashboardAnalyticsService" not in content:
    content = content.replace("from services.reports.history_report import HistoryReportService", 
                              "from services.reports.history_report import HistoryReportService\nfrom services.reports.dashboard_analytics import DashboardAnalyticsService")

# 2. Init variables
if "self.analytics_service" not in content:
    content = content.replace("self.df_historico = None\n        self.cards = {}",
                              "self.df_historico = None\n        self.cards = {}\n        self.cards_gestao = {}\n        self.analytics_service = DashboardAnalyticsService()\n        self.periodo_gestao = 30")

# 3. _criar_interface
old_criar_interface = """        # Seções do dashboard
        self._criar_secao_cards()  # row 1
        self._criar_secao_grafico()  # row 2
        self._criar_secao_tabela()  # row 3"""

new_criar_interface = """        # Abas
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
        self._criar_secao_grafico_gestao(self.tab_gestao)"""
content = content.replace(old_criar_interface, new_criar_interface)

# 4. Signatures of Operational UI sections
content = content.replace("def _criar_secao_cards(self):", "def _criar_secao_cards(self, parent):")
content = re.sub(r'frame_cards = ctk\.CTkFrame\(\s*self\.main_container,', r'frame_cards = ctk.CTkFrame(\n            parent,', content)

content = content.replace("def _criar_secao_grafico(self):", "def _criar_secao_grafico(self, parent):")
content = re.sub(r'frame_grafico = ctk\.CTkFrame\(\s*self\.main_container,', r'frame_grafico = ctk.CTkFrame(\n            parent,', content)

content = content.replace("def _criar_secao_tabela(self):", "def _criar_secao_tabela(self, parent):")
content = re.sub(r'frame_tabela = ctk\.CTkFrame\(\s*self\.main_container,', r'frame_tabela = ctk.CTkFrame(\n            parent,', content)


# 5. Add new UI sections for Gestao
gestao_methods = """
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
            frame_grafico, text="🦠 Doenças Mais Positivas", font=Theme.get_font_primary(size=14, weight="bold")
        )
        label_titulo.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 10))
        
        self.frame_canvas_gestao = ctk.CTkFrame(frame_grafico, fg_color=Theme.BG_CARD)
        self.frame_canvas_gestao.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 15))
        self.canvas_gestao = None
"""
# inject before carregar_dados
if "_criar_filtro_gestao" not in content:
    content = content.replace("    def carregar_dados(", gestao_methods + "\n    def carregar_dados(")

# 6. Update carregar_dados
# Currently carregar_dados does: threading.Thread(target=self._carregar_dados_worker)
# We will intercept `_atualizar_interface` to also update Gestao
# But wait, we can just load Gestao synchronously or in a thread.
# Let's add `_atualizar_dados_gestao`
gestao_logic = """
    def _atualizar_dados_gestao(self):
        try:
            stats = self.analytics_service.obter_estatisticas_gestao(self.periodo_gestao)
            
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
"""
if "_atualizar_dados_gestao" not in content:
    content = content.replace("    def carregar_dados(", gestao_logic + "\n    def carregar_dados(")

# Hook Gestao into _atualizar_interface
old_atualizar = """        if hasattr(self, 'cards') and 'total' in self.cards:
            self.cards['total'].set_valor(str(len(self.df_historico)))
            self.cards['total'].set_indicativo("Dados do histórico local")
            
            sucesso_taxa = 0
            if len(self.df_historico) > 0:"""
new_atualizar = """        # Update Gestao
        self._atualizar_dados_gestao()
        
        if hasattr(self, 'cards') and 'total' in self.cards:
            self.cards['total'].set_valor(str(len(self.df_historico)))
            self.cards['total'].set_indicativo("Dados do histórico local")
            
            sucesso_taxa = 0
            if len(self.df_historico) > 0:"""
if "self._atualizar_dados_gestao()" not in content:
    content = content.replace(old_atualizar, new_atualizar)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Dashboard UI refatorada com sucesso.")
