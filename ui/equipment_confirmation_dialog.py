"""
Dialog para confirmação de equipamento detectado.
Permite ao usuário confirmar a detecção automática ou escolher manualmente.
"""
import customtkinter as ctk
from typing import Optional, Dict, List

from utils.gui_utils import close_modal_toplevel, register_modal_toplevel_usage


class EquipmentConfirmationDialog(ctk.CTkToplevel):
    """Dialog para usuário confirmar ou alterar equipamento detectado."""
    
    def __init__(self, parent, resultado_deteccao: Dict, equipamentos_disponiveis: List[str]):
        """
        Args:
            parent: Janela pai
            resultado_deteccao: Dict com 'equipamento', 'confianca', 'alternativas'
            equipamentos_disponiveis: Lista de todos os equipamentos cadastrados
        """
        super().__init__(parent)
        
        self.resultado_deteccao = resultado_deteccao
        self.equipamentos_disponiveis = equipamentos_disponiveis
        self.escolha_final: Optional[str] = None
        register_modal_toplevel_usage(self.__class__.__name__, context="equipment_confirmation")
        
        self.title("Confirmação de Equipamento")
        self.geometry("550x450")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancelar)
        
        self._build_ui()
        
        # Centralizar
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _build_ui(self):
        """Constrói interface do dialog."""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Título
        ctk.CTkLabel(
            main_frame,
            text="🔍 Equipamento Detectado",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(0, 15))
        
        # Equipamento detectado
        equip_detectado = self.resultado_deteccao['equipamento']
        confianca = self.resultado_deteccao['confianca']
        
        info_frame = ctk.CTkFrame(main_frame, fg_color=("gray90", "gray20"))
        info_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            info_frame,
            text=f"Equipamento: {equip_detectado}",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        cor_confianca = "green" if confianca >= 80 else "orange" if confianca >= 60 else "red"
        ctk.CTkLabel(
            info_frame,
            text=f"Confiança: {confianca:.1f}%",
            font=ctk.CTkFont(size=12),
            text_color=cor_confianca
        ).pack(anchor="w", padx=15, pady=(0, 10))
        
        # Alternativas (se houver)
        alternativas = self.resultado_deteccao.get('alternativas', [])
        if alternativas and len(alternativas) > 1:  # Mais de 1 alternativa (primeira é a detectada)
            ctk.CTkLabel(
                main_frame,
                text="Alternativas encontradas:",
                font=ctk.CTkFont(size=12, weight="bold")
            ).pack(anchor="w", pady=(10, 5))
            
            alt_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            alt_frame.pack(fill="x", padx=10)
            
            for i, alt in enumerate(alternativas[1:4], 1):  # Top 3 alternativas (exceto primeira)
                txt = f"{i}. {alt['equipamento']} ({alt['confianca']:.1f}%)"
                ctk.CTkLabel(
                    alt_frame,
                    text=txt,
                    font=ctk.CTkFont(size=11)
                ).pack(anchor="w", pady=2)
        
        # Dropdown para escolher manualmente
        ctk.CTkLabel(
            main_frame,
            text="Ou escolher manualmente:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", pady=(20, 5))
        
        self.combo_equipamentos = ctk.CTkComboBox(
            main_frame,
            values=self.equipamentos_disponiveis,
            width=400
        )
        self.combo_equipamentos.set(equip_detectado)
        self.combo_equipamentos.pack(anchor="w", padx=10, pady=(0, 20))
        
        # Botões
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=(10, 0))
        
        ctk.CTkButton(
            btn_frame,
            text="✅ Confirmar",
            fg_color="green",
            hover_color="darkgreen",
            width=150,
            height=40,
            command=self._confirmar
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="❌ Cancelar",
            fg_color="red",
            hover_color="darkred",
            width=150,
            height=40,
            command=self._cancelar
        ).pack(side="left", padx=5)
    
    def _confirmar(self):
        """Confirma escolha do equipamento."""
        self.escolha_final = self.combo_equipamentos.get()
        close_modal_toplevel(self)
    
    def _cancelar(self):
        """Cancela operação."""
        self.escolha_final = None
        close_modal_toplevel(self)
    
    def obter_escolha(self) -> Optional[str]:
        """
        Retorna equipamento escolhido pelo usuário.
        
        Returns:
            Nome do equipamento ou None se cancelado
        """
        self.wait_window()
        return self.escolha_final
