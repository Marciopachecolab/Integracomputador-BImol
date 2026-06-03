"""
Interface Gráfica de Configurações do IntegRAGal

Permite ao usuário personalizar todas as configurações do sistema
através de uma interface intuitiva e organizada por categorias.
"""

import customtkinter as ctk
from pathlib import Path
from typing import Dict, Any, Callable
import tkinter.filedialog as fd

from config.settings import configuracao, get_config, set_config, reset_config
from utils.error_handler import ErrorHandler, safe_operation
from utils.logger import registrar_log
from utils.gui_utils import safe_destroy_ctk_toplevel
from ui.theme import Theme

class TelaConfiguracoes(ctk.CTkFrame):
    """Tela de configuracoes em modo legado (janela) ou pagina single-window."""

    def __init__(
        self,
        parent,
        on_apply_callback: Callable = None,
        *,
        host_frame: ctk.CTkFrame | None = None,
        on_close_callback: Callable[[], None] | None = None,
    ):
        """
        Inicializa a tela de configuracoes.

        Args:
            parent: Janela pai.
            on_apply_callback: Funcao chamada ao aplicar configuracoes.
            host_frame: Frame de destino no modo pagina.
            on_close_callback: Callback opcional para fechamento em modo pagina.
        """
        self._is_page_mode = host_frame is not None
        self._on_close_callback = on_close_callback
        self._window: ctk.CTkToplevel | None = None

        if self._is_page_mode:
            super().__init__(host_frame)
            self.pack(expand=True, fill="both")
        else:
            self._window = ctk.CTkToplevel(parent)
            super().__init__(self._window)
            self.pack(expand=True, fill="both")

        self.on_apply_callback = on_apply_callback
        self.mudancas_pendentes = False
        self.valores_pendentes = {}

        if self._window is not None:
            self._window.title("Configuracoes do Sistema")
            self._window.geometry("1000x700")

            self._window.update_idletasks()
            x = (self._window.winfo_screenwidth() // 2) - (1000 // 2)
            y = (self._window.winfo_screenheight() // 2) - (700 // 2)
            self._window.geometry(f"1000x700+{x}+{y}")

            self._window.transient(parent)
            # self._window.grab_set() # Desabilitado para permitir abertura de CTkComboBox (issue do CustomTkinter)
            self._window.protocol("WM_DELETE_WINDOW", self._on_close)

        self._construir_interface()
        self._carregar_valores()

        registrar_log("Configuracoes", "Tela de configuracoes aberta", "INFO")

    def _dialog_parent(self):
        if self._window is not None:
            return self._window
        return self.winfo_toplevel()

    def _construir_interface(self):
        """Constrói a interface da tela de configurações"""
        # Layout principal: menu lateral + conteúdo
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Menu lateral (categorias)
        self._construir_menu_lateral()
        
        # Área de conteúdo (configurações)
        self._construir_area_conteudo()
        
        # Rodapé com botões
        self._construir_rodape()
    
    def _construir_menu_lateral(self):
        """Constrói menu lateral com categorias"""
        menu_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        menu_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        menu_frame.grid_propagate(False)
        
        from ui.components.base_components import IGSidebarMenu, IGLabel
        from ui.theme import Theme
        
        # Título
        titulo = IGLabel(
            menu_frame,
            text="Categorias",
            variant="bold"
        )
        titulo.pack(pady=20, padx=15)
        
        # Categorias
        self.categorias = {
            "aparencia": {"nome": "🎨 Aparência", "icone": "🎨"},
            "alertas": {"nome": "🔔 Alertas", "icone": "🔔"},
            "exportacao": {"nome": "📄 Exportação", "icone": "📄"},
            "extracao": {"nome": "📥 Extração", "icone": "📥"},
            "analise": {"nome": "🔬 Análise", "icone": "🔬"},
            "gal": {"nome": "🌐 GAL", "icone": "🌐"},
            "sessao": {"nome": "💾 Sessão", "icone": "💾"},
            "performance": {"nome": "⚡ Performance", "icone": "⚡"},
            "atalhos": {"nome": "⌨️ Atalhos", "icone": "⌨️"},
            "avancado": {"nome": "🔧 Avançado", "icone": "🔧"}
        }
        
        self.categoria_atual = "aparencia"
        self.cat_keys = list(self.categorias.keys())
        
        items = []
        for cat_id in self.cat_keys:
            items.append({
                "label": self.categorias[cat_id]["nome"],
                "command": lambda c=cat_id: self._mudar_categoria(c)
            })

        self.sidebar_menu = IGSidebarMenu(menu_frame, items=items, active_index=0)
        self.sidebar_menu.pack(fill="both", expand=True)
    
    def _construir_area_conteudo(self):
        """Constrói área de conteúdo com scroll"""
        # Container com scroll
        self.conteudo_frame = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.conteudo_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.conteudo_frame.grid_columnconfigure(0, weight=1)
        
        # Placeholder - será preenchido ao mudar categoria
        self.widgets_config = {}
        
        # Carrega categoria inicial
        self._carregar_categoria(self.categoria_atual)
    
    def _construir_rodape(self):
        """Constrói rodapé com botões de ação"""
        rodape = ctk.CTkFrame(self, height=60, corner_radius=0)
        rodape.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        
        # Botões à direita
        btn_frame = ctk.CTkFrame(rodape, fg_color="transparent")
        btn_frame.pack(side="right", padx=20, pady=10)
        
        # Botão Aplicar
        self.btn_aplicar = ctk.CTkButton(
            btn_frame,
            text="✓ Aplicar",
            command=self._aplicar_configuracoes,
            width=120,
            height=35,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#28a745",
            hover_color="#218838"
        )
        self.btn_aplicar.pack(side="right", padx=5)
        
        # Botão Cancelar — somente no modo janela (popup)
        if not self._is_page_mode:
            btn_cancelar = ctk.CTkButton(
                btn_frame,
                text="✕ Cancelar",
                command=self._on_close,
                width=120,
                height=35,
                font=ctk.CTkFont(size=13),
                fg_color="#dc3545",
                hover_color="#c82333"
            )
            btn_cancelar.pack(side="right", padx=5)
        
        # Botões à esquerda
        btn_frame_esq = ctk.CTkFrame(rodape, fg_color="transparent")
        btn_frame_esq.pack(side="left", padx=20, pady=10)
        
        # Botão Resetar
        btn_reset = ctk.CTkButton(
            btn_frame_esq,
            text="🔄 Resetar Categoria",
            command=self._resetar_categoria_atual,
            width=140,
            height=35,
            font=ctk.CTkFont(size=12)
        )
        btn_reset.pack(side="left", padx=5)
        
        # Botão Exportar
        btn_exportar = ctk.CTkButton(
            btn_frame_esq,
            text="📤 Exportar",
            command=self._exportar_configuracoes,
            width=120,
            height=35,
            font=ctk.CTkFont(size=12)
        )
        btn_exportar.pack(side="left", padx=5)
        
        # Botão Importar
        btn_importar = ctk.CTkButton(
            btn_frame_esq,
            text="📥 Importar",
            command=self._importar_configuracoes,
            width=120,
            height=35,
            font=ctk.CTkFont(size=12)
        )
        btn_importar.pack(side="left", padx=5)
    
    def _mudar_categoria(self, categoria: str):
        """Muda a categoria exibida"""
        if getattr(self, "categoria_atual", None) == categoria:
            return
            
        self._salvar_estado_widgets()
        
        self.categoria_atual = categoria
        idx = self.cat_keys.index(categoria)
        self.sidebar_menu.set_active(idx)
        
        # Limpa conteúdo atual
        for widget in self.conteudo_frame.winfo_children():
            widget.destroy()
            
        self.widgets_config.clear()
        
        # Carrega nova categoria
        self._carregar_categoria(categoria)
    
    def _carregar_categoria(self, categoria: str):
        """Carrega configurações de uma categoria"""
        # Título da categoria
        titulo = ctk.CTkLabel(
            self.conteudo_frame,
            text=self.categorias[categoria]["nome"],
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        titulo.pack(pady=(0, 20), anchor="w")
        
        # Carrega configurações específicas da categoria
        metodo = f"_carregar_config_{categoria}"
        if hasattr(self, metodo):
            getattr(self, metodo)()
        else:
            # Categoria sem implementação específica
            msg = ctk.CTkLabel(
                self.conteudo_frame,
                text=f"Configurações de '{categoria}' em desenvolvimento",
                font=ctk.CTkFont(size=14),
            text_color=Theme.TEXT_PRIMARY
            )
            msg.pack(pady=50)

        # Repopula os widgets recem-criados desta categoria com os valores atuais
        # (config ou pendentes). Sem isso, categorias carregadas sob demanda nascem
        # com switches/combos no default OFF e nao refletem a config salva
        # (ex.: gal_integration.headless=true aparecia desligado).
        self._carregar_valores()

    def _carregar_config_gal(self):
        """Carrega configurações do GAL"""
        self._criar_secao("Integração GAL")

        self._criar_combobox(
            "Ambiente de Envio",
            "gal_integration.base_url",
            ["https://galteste.saude.sc.gov.br", "https://gal.saude.sc.gov.br"],
            "Endereço base do sistema GAL para onde os resultados serão enviados"
        )

        self._criar_secao("Comportamento do Envio")

        self._criar_switch(
            "Ocultar navegador durante envio",
            "gal_integration.headless",
            "Firefox roda em segundo plano (headless). Login e envio aparecem apenas no terminal da janela."
        )

        self._criar_switch(
            "Enviar sem buscar metadados do GAL",
            "gal_integration.envio_sem_metadados",
            "Usa codigoAmostra diretamente como identificador. requisicao e paciente ficam vazios — "
            "o GAL localiza o registro pelo par codigoAmostra + codigo do exame (ex: VRSRT, PEQZDC)."
        )
    
    def _carregar_config_aparencia(self):
        """Carrega configurações de aparência"""
        self._criar_secao("Tema")
        
        # Tema (dark/light/system)
        self._criar_combobox(
            "Modo de Cor",
            "aparencia.tema",
            ["dark", "light", "system"],
            "Modo de cor da interface"
        )
        
        # Cor do tema
        self._criar_combobox(
            "Cor do Tema",
            "aparencia.cor_tema",
            ["blue", "green", "dark-blue"],
            "Cor principal da interface"
        )
        
        # Tamanho da fonte
        self._criar_slider(
            "Tamanho da Fonte",
            "aparencia.tamanho_fonte",
            min_val=8,
            max_val=24,
            formato="{:.0f}",
            unidade="pt"
        )
        
        self._criar_secao("Efeitos Visuais")
        
        # Animações
        self._criar_switch(
            "Animações Habilitadas",
            "aparencia.animacoes_habilitadas",
            "Habilita animações na interface"
        )
        
        # Som de notificações
        self._criar_switch(
            "Som de Notificações",
            "aparencia.som_notificacoes",
            "Reproduz som ao receber notificações"
        )
    
    def _carregar_config_alertas(self):
        """Carrega configurações de alertas"""
        self._criar_secao("Geral")
        
        # Habilitar alertas
        self._criar_switch(
            "Sistema de Alertas Habilitado",
            "alertas.habilitar_alertas",
            "Ativa o sistema de alertas"
        )
        
        self._criar_secao("Limites de CT")
        
        # CT Alto
        self._criar_slider(
            "Limite CT Alto",
            "alertas.limites_ct.ct_alto_limite",
            min_val=25,
            max_val=45,
            formato="{:.1f}",
            unidade=""
        )
        
        # CT Baixo
        self._criar_slider(
            "Limite CT Baixo",
            "alertas.limites_ct.ct_baixo_limite",
            min_val=5,
            max_val=25,
            formato="{:.1f}",
            unidade=""
        )
        
        self._criar_secao("Notificações")
        
        # Mostrar popup
        self._criar_switch(
            "Mostrar Popup de Notificação",
            "alertas.notificacoes.mostrar_popup",
            "Exibe popup ao receber alertas"
        )
        
        # Badge de alertas
        self._criar_switch(
            "Mostrar Badge de Alertas",
            "alertas.badge.mostrar_badge",
            "Exibe contador de alertas não lidos"
        )
    
    def _carregar_config_exportacao(self):
        """Carrega configurações de exportação"""
        self._criar_secao("Formato Padrão")
        
        # Formato
        self._criar_combobox(
            "Formato de Exportação",
            "exportacao.formato_padrao",
            ["pdf", "excel", "csv"],
            "Formato padrão para relatórios"
        )
        
        self._criar_secao("Conteúdo do Relatório")
        
        # Incluir gráficos
        self._criar_switch(
            "Incluir Gráficos",
            "exportacao.incluir_graficos",
            "Adiciona gráficos ao relatório"
        )
        
        # Incluir estatísticas
        self._criar_switch(
            "Incluir Estatísticas",
            "exportacao.incluir_estatisticas",
            "Adiciona estatísticas ao relatório"
        )
        
        # Incluir alertas
        self._criar_switch(
            "Incluir Alertas",
            "exportacao.incluir_alertas",
            "Adiciona lista de alertas ao relatório"
        )
        
        self._criar_secao("Qualidade")
        
        # DPI dos gráficos
        self._criar_slider(
            "DPI dos Gráficos",
            "exportacao.dpi_graficos",
            min_val=150,
            max_val=600,
            formato="{:.0f}",
            unidade="dpi"
        )
    
    def _carregar_config_sessao(self):
        """Carrega configurações de sessão"""
        self._criar_secao("Persistência")
        
        # Salvar automaticamente
        self._criar_switch(
            "Salvar Estado Automaticamente",
            "sessao.salvar_estado_automaticamente",
            "Salva estado do sistema automaticamente"
        )
        
        # Restaurar sessão
        self._criar_switch(
            "Restaurar Sessão Anterior",
            "sessao.restaurar_sessao_anterior",
            "Restaura estado ao iniciar o sistema"
        )
        
        # Intervalo de autosave
        self._criar_slider(
            "Intervalo de Auto-Save",
            "sessao.intervalo_autosave_minutos",
            min_val=1,
            max_val=30,
            formato="{:.0f}",
            unidade="min"
        )
        
        self._criar_secao("Histórico")
        
        # Dias de histórico
        self._criar_slider(
            "Manter Histórico Por",
            "sessao.manter_historico_dias",
            min_val=7,
            max_val=90,
            formato="{:.0f}",
            unidade="dias"
        )
    
    def _carregar_config_avancado(self):
        """Carrega configurações avançadas"""
        self._criar_secao("Debug e Logging")
        
        # Modo debug
        self._criar_switch(
            "Modo Debug",
            "avancado.modo_debug",
            "Ativa modo de depuração (mais logs)"
        )
        
        # Nível de log
        self._criar_combobox(
            "Nível de Log",
            "avancado.nivel_log",
            ["DEBUG", "INFO", "WARNING", "ERROR"],
            "Nível de detalhe dos logs"
        )
        
        self._criar_secao("Performance")
        
        # Cache
        self._criar_switch(
            "Habilitar Cache",
            "avancado.habilitar_cache",
            "Usa cache para melhorar performance"
        )
        
        # Tamanho do cache
        self._criar_slider(
            "Tamanho do Cache",
            "avancado.tamanho_cache_mb",
            min_val=50,
            max_val=500,
            formato="{:.0f}",
            unidade="MB"
        )
        
        # Max threads
        self._criar_slider(
            "Threads Máximas",
            "avancado.max_threads",
            min_val=1,
            max_val=16,
            formato="{:.0f}",
            unidade=""
        )
    
    # ============================================================================
    # Widgets auxiliares
    # ============================================================================
    
    def _criar_secao(self, titulo: str):
        """Cria cabeçalho de seção"""
        frame = ctk.CTkFrame(self.conteudo_frame, fg_color="transparent")
        frame.pack(fill="x", pady=(20, 10))
        
        label = ctk.CTkLabel(
            frame,
            text=titulo,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        )
        label.pack(side="left")
        
        # Linha separadora
        separator = ctk.CTkFrame(frame, height=2, fg_color=("gray80", "gray30"))
        separator.pack(side="left", fill="x", expand=True, padx=10)
    
    def _criar_switch(self, label: str, config_key: str, descricao: str = ""):
        """Cria switch para configuração booleana"""
        frame = ctk.CTkFrame(self.conteudo_frame, fg_color="transparent")
        frame.pack(fill="x", pady=8)
        
        # Label e descrição
        label_frame = ctk.CTkFrame(frame, fg_color="transparent")
        label_frame.pack(side="left", fill="x", expand=True)
        
        lbl = ctk.CTkLabel(
            label_frame,
            text=label,
            font=ctk.CTkFont(size=13),
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        )
        lbl.pack(anchor="w")
        
        if descricao:
            desc = ctk.CTkLabel(
                label_frame,
                text=descricao,
                font=ctk.CTkFont(size=11),
            text_color=Theme.TEXT_PRIMARY,
                anchor="w"
            )
            desc.pack(anchor="w")
        
        switch = ctk.CTkSwitch(
            frame,
            text="",
            text_color=Theme.TEXT_PRIMARY,
            command=self._on_config_change
        )
        switch.pack(side="right", padx=10)
        
        self.widgets_config[config_key] = switch
    
    def _criar_combobox(self, label: str, config_key: str, valores: list, descricao: str = ""):
        """Cria combobox para configuração de escolha"""
        frame = ctk.CTkFrame(self.conteudo_frame, fg_color="transparent")
        frame.pack(fill="x", pady=8)
        
        # Label e descrição
        label_frame = ctk.CTkFrame(frame, fg_color="transparent")
        label_frame.pack(side="left", fill="x", expand=True)
        
        lbl = ctk.CTkLabel(
            label_frame,
            text=label,
            font=ctk.CTkFont(size=13),
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        )
        lbl.pack(anchor="w")
        
        if descricao:
            desc = ctk.CTkLabel(
                label_frame,
                text=descricao,
                font=ctk.CTkFont(size=11),
            text_color=Theme.TEXT_PRIMARY,
                anchor="w"
            )
            desc.pack(anchor="w")
        
        # Combobox
        combo = ctk.CTkComboBox(
            frame,
            values=valores,
            width=200,
            text_color=Theme.TEXT_PRIMARY,
            command=lambda _: self._on_config_change()
        )
        combo.pack(side="right", padx=10)
        
        self.widgets_config[config_key] = combo
    
    def _criar_slider(self, label: str, config_key: str, min_val: float, max_val: float, 
                     formato: str = "{:.1f}", unidade: str = ""):
        """Cria slider para configuração numérica"""
        frame = ctk.CTkFrame(self.conteudo_frame, fg_color="transparent")
        frame.pack(fill="x", pady=8)
        
        # Label
        lbl = ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(size=13),
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        )
        lbl.pack(anchor="w")
        
        # Frame para slider + valor
        slider_frame = ctk.CTkFrame(frame, fg_color="transparent")
        slider_frame.pack(fill="x", pady=5)
        
        # Label do valor
        valor_label = ctk.CTkLabel(
            slider_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=Theme.TEXT_PRIMARY,
            width=80
        )
        valor_label.pack(side="right", padx=10)
        
        # Slider
        slider = ctk.CTkSlider(
            slider_frame,
            from_=min_val,
            to=max_val,
            command=lambda v: self._on_slider_change(v, valor_label, formato, unidade)
        )
        slider.pack(side="left", fill="x", expand=True, padx=10)
        
        self.widgets_config[config_key] = {
            "widget": slider,
            "label": valor_label,
            "formato": formato,
            "unidade": unidade
        }
    
    def _on_slider_change(self, valor, label, formato: str, unidade: str):
        """Callback para mudança em slider"""
        texto = formato.format(valor)
        if unidade:
            texto += f" {unidade}"
        label.configure(text=texto)
        self._on_config_change()
    
    def _on_config_change(self):
        """Marca que há mudanças pendentes"""
        self.mudancas_pendentes = True
        self.btn_aplicar.configure(fg_color="#ffc107", text="⚠ Aplicar Mudanças")
    
    def _carregar_valores(self):
        """Carrega valores atuais das configurações nos widgets"""
        for config_key, widget in self.widgets_config.items():
            if hasattr(self, "valores_pendentes") and config_key in self.valores_pendentes:
                valor = self.valores_pendentes[config_key]
            else:
                valor = get_config(config_key)
            
            if valor is None:
                continue
            
            if isinstance(widget, ctk.CTkSwitch):
                if valor:
                    widget.select()
                else:
                    widget.deselect()
            
            elif isinstance(widget, ctk.CTkComboBox):
                widget.set(str(valor))
            
            elif isinstance(widget, dict):  # Slider
                widget["widget"].set(valor)
                texto = widget["formato"].format(valor)
                if widget["unidade"]:
                    texto += f" {widget['unidade']}"
                widget["label"].configure(text=texto)
    
    def _salvar_estado_widgets(self):
        """Salva o estado dos widgets atualmente visíveis na tela"""
        for config_key, widget in self.widgets_config.items():
            try:
                if isinstance(widget, ctk.CTkSwitch):
                    valor = widget.get() == 1
                elif isinstance(widget, ctk.CTkComboBox):
                    valor = widget.get()
                elif isinstance(widget, dict):  # Slider
                    valor = widget["widget"].get()
                else:
                    continue
                self.valores_pendentes[config_key] = valor
            except Exception:
                pass
                
    @safe_operation(fallback_value=False, context="Aplicando configurações")
    def _aplicar_configuracoes(self) -> bool:
        """Aplica as configurações alteradas"""
        self._salvar_estado_widgets()
        
        # Define configurações na memória
        for config_key, valor in self.valores_pendentes.items():
            configuracao.set(config_key, valor, salvar_agora=False)
        
        # Salva todas de uma vez
        if configuracao.salvar():
            try:
                from services.core.config_service import config_service
                config_service._load_config()
            except Exception:
                pass

            self.mudancas_pendentes = False
            self.btn_aplicar.configure(fg_color="#28a745", text="✓ Aplicar")
            if hasattr(self, "valores_pendentes"):
                self.valores_pendentes.clear()
            
            # Callback
            if self.on_apply_callback:
                self.on_apply_callback(configuracao.config)

            # Atualizar Topbar do app
            try:
                app = self.winfo_toplevel()
                if hasattr(app, "atualizar_topbar_gal"):
                    app.atualizar_topbar_gal()
            except Exception:
                pass
            
            # Utilizar after para dar tempo da CTkComboBox finalizar seu evento antes de exibir o modal
            self.after(200, lambda: ErrorHandler.show_info(
                "Configurações Aplicadas",
                "As configurações foram salvas com sucesso!"
            ))
            
            registrar_log("Configurações", "Configurações aplicadas pelo usuário", "INFO")
            return True
        
        return False
    
    def _resetar_categoria_atual(self):
        """Reseta configurações da categoria atual para valores padrão"""
        # Confirmação
        from tkinter import messagebox
        resposta = messagebox.askyesno(
            "Confirmar Reset",
            f"Deseja resetar todas as configurações de '{self.categorias[self.categoria_atual]['nome']}' para os valores padrão?",
            icon='warning'
        )
        
        if resposta:
            reset_config(self.categoria_atual)
            
            # Recarrega categoria
            self._mudar_categoria(self.categoria_atual)
            
            ErrorHandler.show_info(
                "Configurações Resetadas",
                f"Configurações de '{self.categorias[self.categoria_atual]['nome']}' foram resetadas!"
            )
            
            registrar_log(
                "Configurações",
                f"Categoria '{self.categoria_atual}' resetada para valores padrão",
                "INFO"
            )
    
    def _exportar_configuracoes(self):
        """Exporta configurações para arquivo"""
        caminho = fd.asksaveasfilename(
            title="Exportar Configurações",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")],
            initialfile="integragal_config.json"
        )
        
        if caminho:
            if configuracao.exportar_configuracoes(Path(caminho)):
                ErrorHandler.show_info(
                    "Exportação Concluída",
                    f"Configurações exportadas para:\n{caminho}"
                )
    
    def _importar_configuracoes(self):
        """Importa configurações de arquivo"""
        caminho = fd.askopenfilename(
            title="Importar Configurações",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")]
        )
        
        if caminho:
            if configuracao.importar_configuracoes(Path(caminho)):
                # Recarrega categoria atual
                self._mudar_categoria(self.categoria_atual)
    
    def _on_close(self):
        """Trata fechamento da tela/janela."""
        if self.mudancas_pendentes:
            from tkinter import messagebox
            resposta = messagebox.askyesnocancel(
                "Mudancas Nao Salvas",
                "Voce tem mudancas nao salvas. Deseja salvar antes de fechar?",
                parent=self._dialog_parent(),
                icon='warning'
            )

            if resposta is None:
                return
            elif resposta:
                if not self._aplicar_configuracoes():
                    return

        registrar_log("Configuracoes", "Tela de configuracoes fechada", "INFO")
        if self._is_page_mode:
            if self._on_close_callback is not None:
                self._on_close_callback()
            else:
                self.destroy()
            return

        if self._window is not None:
            safe_destroy_ctk_toplevel(self._window)
            return

        self.destroy()


# Funcao de conveniencia para abrir tela de configuracoes
def abrir_configuracoes(parent=None, callback=None):
    """Abre a tela de configuracoes (modo legado Toplevel)."""
    tela = TelaConfiguracoes(parent, callback)
    return tela._window or tela


def create_configuracoes_page(parent: ctk.CTkFrame, main_window) -> ctk.CTkFrame:
    """Cria a tela de configuracoes como pagina no ModuleHost."""

    def _go_back() -> None:
        nav = getattr(main_window, "navigation_manager", None)
        if nav and hasattr(nav, "navigate_to"):
            nav.navigate_to("main_menu")

    tela = TelaConfiguracoes(
        main_window,
        host_frame=parent,
        on_close_callback=_go_back,
    )
    return tela
