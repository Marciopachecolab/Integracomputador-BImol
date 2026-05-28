import customtkinter as ctk
from ui.theme import Theme

class ClinicalBadge(ctk.CTkFrame):
    def __init__(self, master, status: str, **kwargs):
        status_upper = status.upper()
        
        if status_upper in ["NÃO DETECTÁVEL", "NAO DETECTAVEL", "SUCESSO"]:
            bg_color = Theme.COLOR_SUCCESS_SOFT
            text_color = Theme.COLOR_SUCCESS
            border_color = Theme.COLOR_SUCCESS_BORDER
        elif status_upper in ["INDETERMINADO", "AVISO"]:
            bg_color = Theme.COLOR_WARNING_SOFT
            text_color = Theme.COLOR_WARNING
            border_color = Theme.COLOR_WARNING_BORDER
        elif status_upper in ["DETECTÁVEL", "DETECTAVEL", "FALHA", "INVÁLIDO", "INVALIDO"]:
            bg_color = Theme.COLOR_DANGER_SOFT
            text_color = Theme.COLOR_DANGER
            border_color = Theme.COLOR_DANGER_BORDER
        else:
            bg_color = Theme.COLOR_GRAY_SOFT
            text_color = Theme.COLOR_GRAY
            border_color = Theme.BORDER_DEFAULT
            
        super().__init__(
            master,
            fg_color=bg_color,
            border_width=1,
            border_color=border_color,
            corner_radius=12,
            height=24,
            **kwargs
        )
        self.pack_propagate(False)
        
        self.label = ctk.CTkLabel(
            self,
            text=status.upper(),
            text_color=text_color,
            font=Theme.get_font_primary(size=10, weight="bold")
        )
        self.label.pack(expand=True, padx=10, pady=2)
