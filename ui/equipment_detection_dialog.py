# -*- coding: utf-8 -*-
"""
Dialog de Detecção de Tipo de Placa PCR
Exibe resultado da detecção automática e permite escolha manual
"""
from typing import Optional, Dict, List
import customtkinter as ctk

from utils.gui_utils import close_modal_toplevel, register_modal_toplevel_usage


class EquipmentDetectionDialog(ctk.CTkToplevel):
    """
    Dialog para confirmação/seleção de tipo de placa PCR detectado.
    
    Exibe:
    - Melhor match detectado com nível de confiança
    - Top 3 alternativas
    - Opção de escolha manual via dropdown
    - Botões Confirmar/Cancelar
    """
    
    def __init__(
        self,
        master,
        deteccao_resultado: Dict,
        equipamentos_disponiveis: List[str],
        arquivo_nome: str
    ):
        super().__init__(master)
        
        self.title("Detecção de Tipo de Placa PCR")
        self.geometry("550x450")
        
        self._resultado = deteccao_resultado
        self._equipamentos = sorted(equipamentos_disponiveis)
        self._arquivo = arquivo_nome
        self._selecao: Optional[str] = None
        self._confirmado: bool = False
        register_modal_toplevel_usage(self.__class__.__name__, context="equipment_detection")
        
        # Dialog modal
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancelar)
        
        self._criar_widgets()
        
        # Centralizar na tela
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _criar_widgets(self):
        """Cria interface do dialog"""
        
        # Container principal
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Título
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            title_frame,
            text="🔬 Detecção Automática de Tipo de Placa",
            font=("", 16, "bold")
        ).pack()
        
        # Nome do arquivo
        ctk.CTkLabel(
            title_frame,
            text=f"Arquivo: {self._arquivo}",
            font=("", 11),
            text_color="gray"
        ).pack(pady=(5, 0))
        
        # Resultado da detecção
        detection_frame = ctk.CTkFrame(main_frame)
        detection_frame.pack(fill="x", pady=(0, 15))
        
        equipamento = self._resultado.get('equipamento', 'Desconhecido')
        confianca = self._resultado.get('confianca', 0.0)
        
        # Cor do badge de confiança
        if confianca >= 0.95:
            cor_badge = "#28a745"  # Verde
            texto_confianca = "Alta Confiança"
        elif confianca >= 0.80:
            cor_badge = "#ffc107"  # Amarelo
            texto_confianca = "Média Confiança"
        else:
            cor_badge = "#dc3545"  # Vermelho
            texto_confianca = "Baixa Confiança"
        
        # Frame do melhor match
        match_frame = ctk.CTkFrame(detection_frame)
        match_frame.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(
            match_frame,
            text="✅ Tipo de Placa Detectado:",
            font=("", 13, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            match_frame,
            text=equipamento,
            font=("", 14, "bold"),
            text_color="#2196F3"
        ).pack(anchor="w", padx=10)
        
        # Badge de confiança
        badge_frame = ctk.CTkFrame(match_frame, fg_color=cor_badge, corner_radius=8)
        badge_frame.pack(anchor="w", padx=10, pady=(5, 10))
        
        ctk.CTkLabel(
            badge_frame,
            text=f"{texto_confianca}: {confianca*100:.1f}%",
            font=("", 11, "bold"),
            text_color="white"
        ).pack(padx=10, pady=5)
        
        # Alternativas (se houver)
        alternativas = self._resultado.get('alternativas', [])
        if alternativas and len(alternativas) > 0:
            alt_frame = ctk.CTkFrame(main_frame)
            alt_frame.pack(fill="x", pady=(0, 15))
            
            ctk.CTkLabel(
                alt_frame,
                text="📋 Outras Opções Detectadas:",
                font=("", 12, "bold")
            ).pack(anchor="w", padx=15, pady=(10, 5))
            
            for i, alt in enumerate(alternativas[:3], 1):
                alt_nome = alt.get('equipamento', 'N/A')
                alt_conf = alt.get('confianca', 0.0)
                
                alt_label = ctk.CTkLabel(
                    alt_frame,
                    text=f"  {i}. {alt_nome} ({alt_conf*100:.1f}%)",
                    font=("", 11),
                    text_color="gray"
                )
                alt_label.pack(anchor="w", padx=20, pady=2)
        
        # Seleção manual
        manual_frame = ctk.CTkFrame(main_frame)
        manual_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            manual_frame,
            text="🔧 Ou escolha manualmente:",
            font=("", 12, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        self.combo_equipamento = ctk.CTkComboBox(
            manual_frame,
            values=self._equipamentos,
            width=400,
            state="readonly"
        )
        self.combo_equipamento.pack(padx=15, pady=(0, 10))
        self.combo_equipamento.set(equipamento)  # Pré-selecionar detecção
        
        # Botões
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")
        button_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.btn_confirmar = ctk.CTkButton(
            button_frame,
            text="✅ Confirmar",
            command=self._on_confirmar,
            fg_color="#28a745",
            hover_color="#218838"
        )
        self.btn_confirmar.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        self.btn_cancelar = ctk.CTkButton(
            button_frame,
            text="❌ Cancelar",
            command=self._on_cancelar,
            fg_color="gray",
            hover_color="#5a6268"
        )
        self.btn_cancelar.grid(row=0, column=1, padx=(5, 0), sticky="ew")
    
    def _on_confirmar(self):
        """Confirma seleção (detectada ou manual)"""
        self._selecao = self.combo_equipamento.get()
        self._confirmado = True
        close_modal_toplevel(self)
    
    def _on_cancelar(self):
        """Cancela operação"""
        self._selecao = None
        self._confirmado = False
        close_modal_toplevel(self)
    
    def get_selecao(self) -> Optional[str]:
        """
        Aguarda fechamento do dialog e retorna equipamento selecionado.
        
        Returns:
            Nome do equipamento selecionado ou None se cancelado
        """
        self.wait_window()
        return self._selecao if self._confirmado else None
