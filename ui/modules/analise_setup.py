import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
import customtkinter as ctk
from ui.theme import Theme
from utils.logger import registrar_log

from ui.components.base_components import IGTextField, IGSelect
class AnaliseSetupPage(ctk.CTkFrame):
    """Tela de preparação para a análise (Etapa 1). Substitui os antigos popups modais."""
    def __init__(self, parent, main_window):
        super().__init__(parent, fg_color="transparent")
        self.main_window = main_window
        self.app_state = main_window.app_state
        self.menu_handler = main_window.menu_handler
        
        self.arquivo_selecionado = None
        
        # Validar mapeamento antes de desenhar a tela
        if not self.menu_handler._tem_mapeamento_extracao_valido():
            self._mostrar_aviso_mapeamento()
            return
            
        self._criar_interface()
        
    def _mostrar_aviso_mapeamento(self):
        lbl = ctk.CTkLabel(
            self, 
            text="⚠️ É necessário realizar o Mapeamento da Placa primeiro.",
            font=Theme.get_font_primary(size=16, weight="bold"),
            text_color=Theme.COLOR_DANGER
        )
        lbl.pack(pady=50)
        
        btn = ctk.CTkButton(
            self,
            text="Ir para Mapeamento",
            command=lambda: self.main_window.navigation_manager.navigate_to("extracao"),
            fg_color=Theme.PRIMARY_BLUE,
            hover_color=Theme.PRIMARY_BLUE_HOVER
        )
        btn.pack(pady=10)

    def _criar_interface(self):
        # Título
        lbl_titulo = ctk.CTkLabel(
            self,
            text="1. Configuração da Corrida e Exame",
            font=Theme.get_font_primary(size=20, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        lbl_titulo.pack(pady=(20, 10), padx=20, anchor="w")
        
        # Scrollable container
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Frame de Exame
        frame_exame = ctk.CTkFrame(scroll, fg_color=Theme.BG_CARD, border_width=1, border_color=Theme.BORDER_DEFAULT)
        frame_exame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(frame_exame, text="Selecione o Exame", font=Theme.get_font_primary(size=14, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(pady=(10, 5), padx=15, anchor="w")
        
        lista_exames = self.menu_handler._carregar_exames_para_ui()
        self.combo_exame = IGSelect(frame_exame, values=lista_exames if lista_exames else ["Nenhum exame cadastrado"], width=300)
        self.combo_exame.pack(pady=(0, 15), padx=15, anchor="w")
        
        # Dados da Corrida (Obrigatórios)
        frame_dados = ctk.CTkFrame(scroll, fg_color=Theme.BG_CARD, border_width=1, border_color=Theme.BORDER_DEFAULT)
        frame_dados.pack(fill="x", pady=10)
        
        ctk.CTkLabel(frame_dados, text="Dados Obrigatórios", font=Theme.get_font_primary(size=14, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(pady=(10, 5), padx=15, anchor="w")
        
        row1 = ctk.CTkFrame(frame_dados, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(row1, text="Lote / Kit:", text_color=Theme.TEXT_PRIMARY).pack(side="left", padx=(0, 10))
        self.entry_lote = IGTextField(row1, width=200)
        self.entry_lote.pack(side="left", padx=(0, 20))
        self.entry_lote.insert(0, getattr(self.app_state, "lote", ""))
        
        from datetime import datetime
        
        ctk.CTkLabel(row1, text="Data da Realização:", text_color=Theme.TEXT_PRIMARY).pack(side="left", padx=(0, 10))
        self.entry_data = IGTextField(row1, width=150)
        self.entry_data.pack(side="left")
        
        data_salva = getattr(self.app_state, "data_exame", "")
        if not data_salva:
            data_salva = datetime.now().strftime("%d/%m/%Y")
            
        self.entry_data.insert(0, data_salva)
        
        # Arquivo de Resultados
        frame_arq = ctk.CTkFrame(scroll, fg_color=Theme.BG_CARD, border_width=1, border_color=Theme.BORDER_DEFAULT)
        frame_arq.pack(fill="x", pady=10)
        
        ctk.CTkLabel(frame_arq, text="Arquivo de Resultados do Equipamento", font=Theme.get_font_primary(size=14, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(pady=(10, 5), padx=15, anchor="w")
        
        self.lbl_arquivo = ctk.CTkLabel(frame_arq, text="Nenhum arquivo selecionado", text_color=Theme.TEXT_PRIMARY)
        self.lbl_arquivo.pack(pady=5, padx=15, anchor="w")
        
        btn_selecionar = ctk.CTkButton(frame_arq, text="Selecionar Arquivo", command=self._selecionar_arquivo, fg_color=Theme.PRIMARY_BLUE)
        btn_selecionar.pack(pady=(0, 15), padx=15, anchor="w")
        
        # Opcionais
        frame_opcionais = ctk.CTkFrame(scroll, fg_color=Theme.BG_CARD, border_width=1, border_color=Theme.BORDER_DEFAULT)
        frame_opcionais.pack(fill="x", pady=10)
        
        ctk.CTkLabel(frame_opcionais, text="Dados Opcionais", font=Theme.get_font_primary(size=14, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(pady=(10, 5), padx=15, anchor="w")
        
        self.entry_nome_corrida = self._criar_campo_opcional(frame_opcionais, "Nome da Corrida:", getattr(self.app_state, "nome_corrida", ""))
        self.entry_quem_extracao = self._criar_campo_opcional(frame_opcionais, "Quem fez a extração:", getattr(self.app_state, "quem_fez_extracao", ""))
        self.entry_quem_placa = self._criar_campo_opcional(frame_opcionais, "Quem preparou a placa:", getattr(self.app_state, "quem_preparou_placa", ""))
        self.entry_quem_analise = self._criar_campo_opcional(frame_opcionais, "Quem analisou a placa:", getattr(self.app_state, "quem_analisou_placa", ""))
        self.entry_obs = self._criar_campo_opcional(frame_opcionais, "Observações:", getattr(self.app_state, "observacoes_corrida", ""))
        
        # Botões
        frame_botoes = ctk.CTkFrame(self, fg_color="transparent")
        frame_botoes.pack(fill="x", pady=20, padx=20)
        
        btn_avancar = ctk.CTkButton(
            frame_botoes,
            text="Avançar para Análise >",
            command=self._iniciar_analise,
            fg_color=Theme.COLOR_SUCCESS,
            hover_color="#059669",
            height=40,
            font=Theme.get_font_primary(size=14, weight="bold")
        )
        btn_avancar.pack(side="right")
        
    def _criar_campo_opcional(self, parent, label_text, default_value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row, text=label_text, width=150, anchor="w", text_color=Theme.TEXT_PRIMARY).pack(side="left")
        entry = IGTextField(row, width=300)
        entry.pack(side="left")
        if default_value:
            entry.insert(0, str(default_value))
        return entry
        
    def _selecionar_arquivo(self):
        caminho = filedialog.askopenfilename(
            parent=self.main_window,
            title="Selecione o arquivo de resultados do equipamento",
            filetypes=[("Arquivos de planilha", "*.csv;*.xlsx;*.xls"), ("Todos os arquivos", "*.*")],
        )
        if caminho:
            self.arquivo_selecionado = Path(caminho)
            self.lbl_arquivo.configure(text=str(self.arquivo_selecionado))
            self.app_state.caminho_arquivo_corrida = str(self.arquivo_selecionado)
            
    def _iniciar_analise(self):
        exame = self.combo_exame.get()
        lote = self.entry_lote.get().strip()
        data_exame = self.entry_data.get().strip()
        
        if not exame or exame == "Nenhum exame cadastrado":
            messagebox.showwarning("Aviso", "Selecione um exame válido.")
            return
            
        if not lote or not data_exame:
            messagebox.showwarning("Aviso", "Lote e Data são obrigatórios.")
            return
            
        if not self.arquivo_selecionado:
            messagebox.showwarning("Aviso", "Selecione o arquivo de resultados.")
            return
            
        # Salvar estado
        self.app_state.exame_selecionado = exame
        self.app_state.lote = lote
        self.app_state.data_exame = data_exame
        self.app_state.nome_corrida = self.entry_nome_corrida.get().strip()
        self.app_state.quem_fez_extracao = self.entry_quem_extracao.get().strip()
        self.app_state.quem_preparou_placa = self.entry_quem_placa.get().strip()
        self.app_state.quem_analisou_placa = self.entry_quem_analise.get().strip()
        self.app_state.observacoes_corrida = self.entry_obs.get().strip()
        
        self.main_window.update_status(f"A executar análise para '{exame}'...")
        
        # Disparar a análise no background através do handler existente
        self.menu_handler._iniciar_execucao_analise_assincrona(
            exame,
            lote,
            self.arquivo_selecionado
        )

def create_analise_setup_page(parent, main_window):
    return AnaliseSetupPage(parent, main_window)
