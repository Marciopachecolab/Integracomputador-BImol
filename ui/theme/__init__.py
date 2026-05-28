# ui/theme.py
# Modulo responsavel por armazenar e fornecer os Design Tokens e cores canonicas do sistema.
# Regra SDD (AGENTS.md): As cores clinicas (Verde/Amarelo/Vermelho) sao padroes absolutos e nao devem 
# carregar ou substituir regra de negocio da aplicacao, devendo mapear 1:1 o Output da Camada de Dominio.

import customtkinter as ctk

class Theme:
    # --- Backgrounds e Superfícies ---
    BG_ROOT = "#F4F7FA"         # Fundo principal off-white (visto fora dos cards no mockup)
    BG_PANEL = "#FFFFFF"        # Fundo do Sidebar
    BG_CARD = "#FFFFFF"         # Fundo dos cards brancos
    
    # --- Bordas ---
    BORDER_DEFAULT = "#E2E8F0"  # Bordas dos cards
    BORDER_LIGHT = "#F1F5F9"
    
    # --- Cores Primárias de Ação ---
    PRIMARY_BLUE = "#2563EB"    # Azul vibrante (Start New Plate)
    PRIMARY_BLUE_HOVER = "#1D4ED8"
    PRIMARY_BLUE_SOFT = "#EFF6FF" # Hover do menu
    PRIMARY_BLUE_LIGHT = "#DBEAFE"
    
    # --- Tipografia / Cores de Texto ---
    TEXT_PRIMARY = "#000000"    # Textos principais (títulos)
    TEXT_SECONDARY = "#000000"  # Textos secundários (ex: labels nos cards)
    TEXT_MUTED = "#000000"
    TEXT_DISABLED = "#94A3B8"
    
    # --- Cores Clínicas / Estados Canônicos (INTOCÁVEIS) ---
    # Nao Detectavel / Sucesso
    COLOR_SUCCESS = "#10B981"
    COLOR_SUCCESS_SOFT = "#D1FAE5"
    COLOR_SUCCESS_BORDER = "#6EE7B7"
    
    # Indeterminado / Aviso
    COLOR_WARNING = "#F59E0B"
    COLOR_WARNING_SOFT = "#FEF3C7"
    COLOR_WARNING_BORDER = "#FCD34D"
    
    # Detectavel / Falha / Invalido
    COLOR_DANGER = "#EF4444"
    COLOR_DANGER_SOFT = "#FEE2E2"
    COLOR_DANGER_BORDER = "#FCA5A5"

    # --- Outros Elementos ---
    COLOR_GRAY = "#94A3B8"
    COLOR_GRAY_SOFT = "#F8FAFC"
    
    @classmethod
    def get_font_primary(cls, size: int = 12, weight: str = "normal"):
        """
        Retorna a definicao de fonte padrao da UI institucional (Segoe UI / Inter fallback)
        Para uso com CTkFont.
        """
        return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)

ctk.set_appearance_mode("Light")
