"""
Card de Resumo - Componente Reutilizável
Fase 3.1 - Dashboard
"""

import customtkinter as ctk
from ui.theme import Theme

class CardResumo(ctk.CTkFrame):
    """
    Card de resumo com título, valor e indicativo
    Usado no dashboard para estatísticas
    """
    
    def __init__(
        self,
        master,
        titulo: str,
        valor: str,
        cor_destaque: str = Theme.PRIMARY_BLUE,
        indicativo_texto: str = "",
        indicativo_cor: str = Theme.COLOR_SUCCESS,
        **kwargs
    ):
        super().__init__(
            master,
            fg_color=Theme.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=Theme.BORDER_DEFAULT,
            **kwargs
        )
        
        self.titulo = titulo
        self.valor = valor
        self.cor_destaque = cor_destaque
        self.indicativo_texto = indicativo_texto
        self.indicativo_cor = indicativo_cor
        
        self._criar_widgets()
    
    def _criar_widgets(self):
        # Título (pequeno e secundário)
        self.label_titulo = ctk.CTkLabel(
            self,
            text=self.titulo,
            font=Theme.get_font_primary(size=13, weight="bold"),
            text_color=Theme.TEXT_MUTED
        )
        self.label_titulo.pack(anchor="w", padx=20, pady=(20, 5))
        
        # Valor (grande e destacado)
        self.label_valor = ctk.CTkLabel(
            self,
            text=self.valor,
            font=Theme.get_font_primary(size=28, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        self.label_valor.pack(anchor="w", padx=20, pady=0)

        # Indicativo / Subtexto
        if self.indicativo_texto:
            self.label_indicativo = ctk.CTkLabel(
                self,
                text=self.indicativo_texto,
                font=Theme.get_font_primary(size=11, weight="bold"),
                text_color=self.indicativo_cor
            )
            self.label_indicativo.pack(anchor="w", padx=20, pady=(5, 20))
        else:
            spacer = ctk.CTkFrame(self, height=20, fg_color="transparent")
            spacer.pack(pady=(5, 20))
    
    def atualizar_valor(self, novo_valor: str):
        self.valor = novo_valor
        self.label_valor.configure(text=novo_valor)


# Função auxiliar para criar cards rapidamente
def criar_card_estatistica(
    master,
    titulo: str,
    valor: str,
    tipo: str = "info",
    indicativo_texto: str = ""
) -> CardResumo:
    
    cores_indicativo = {
        'info': Theme.TEXT_MUTED,
        'sucesso': Theme.COLOR_SUCCESS,
        'erro': Theme.COLOR_DANGER,
        'aviso': Theme.COLOR_WARNING,
    }
    
    cor_ind = cores_indicativo.get(tipo, Theme.TEXT_MUTED)
    
    return CardResumo(
        master,
        titulo=titulo,
        valor=valor,
        cor_destaque=Theme.PRIMARY_BLUE,
        indicativo_texto=indicativo_texto,
        indicativo_cor=cor_ind
    )
