# -*- coding: utf-8 -*-
"""
ui/theme/design_tokens.py

Fonte única de verdade para estética e espaçamentos do IntegRAGal.
Baseado nas diretrizes de UI Premium e Design Moderno (Blueprint Institucional).
"""

class Colors:
    bg = "#F4F6FA"
    bgWhite = "#FFFFFF"
    bgPanel = "#F8FAFC"
    sidebar = "#FFFFFF"
    sidebarActive = "#1A56DB"
    sidebarActiveBg = "#EBF0FF"
    border = "#E2E8F0"
    borderLight = "#EEF2F7"
    textPrimary = "#1A202C"
    textSecondary = "#4A5568"
    textMuted = "#718096"
    textDisabled = "#A0AEC0"
    blue = "#1A56DB"
    blueHover = "#1641B8"
    blueSoft = "#EBF0FF"
    blueLight = "#DBEAFE"
    success = "#16A34A"
    successSoft = "#DCFCE7"
    successBorder = "#86EFAC"
    warning = "#CA8A04"
    warningSoft = "#FEF9C3"
    warningBorder = "#FDE047"
    danger = "#DC2626"
    dangerSoft = "#FEE2E2"
    dangerBorder = "#FCA5A5"
    orange = "#EA580C"
    orangeSoft = "#FFF7ED"
    purple = "#7C3AED"
    purpleSoft = "#EDE9FE"
    gray = "#64748B"
    graySoft = "#F1F5F9"
    red = "#DC2626"
    yellow = "#D97706"
    green = "#16A34A"

# =============================================================================
# CORES SEMÂNTICAS (Resultados)
# Integradas ao novo design blueprint
# =============================================================================
class SemanticColors:
    # Vermelho premium - Alerta/Detectado
    DETECTADO = Colors.dangerSoft

    # Amarelo/Âmbar premium - Atenção/Inconclusivo
    INCONCLUSIVO = Colors.warningSoft

    # Verde claro - Não Detectável (decisão 2026-05-22)
    NAO_DETECTAVEL = "#C8E6C9"  # Verde claro meio, legível e distinto do branco

    # Cinza médio - Inválido/Sem sinal (decisão 2026-05-22)
    INVALIDO = "#BDBDBD"  # Cinza médio — distingue claramente de branco e de ND verde

    # Cores de controle
    CONTROLE_CN = Colors.dangerSoft  # CN em vermelho suave (baseado na referência WellDot)
    CONTROLE_CP = Colors.successSoft # CP em verde suave
    EMPTY = Colors.bgWhite        # Branco

# =============================================================================
# CORES DE GRUPOS (Mapeamento de Placa)
# =============================================================================
class GroupColors:
    PAIR = Colors.blueLight
    TRIO = Colors.purpleSoft
    QUARTET = Colors.warningSoft

# =============================================================================
# TIPOGRAFIA
# =============================================================================
class Typography:
    FONT_FAMILY = "Inter"  # ou Segoe UI/Arial como fallback
    
    # Títulos e Cabeçalhos
    H1 = (FONT_FAMILY, 24, "bold")
    H2 = (FONT_FAMILY, 20, "bold")
    H3 = (FONT_FAMILY, 16, "bold")
    
    # Textos de Corpo e Dados
    BODY_LARGE = (FONT_FAMILY, 14, "normal")
    BODY_DEFAULT = (FONT_FAMILY, 12, "normal")
    BODY_SMALL = (FONT_FAMILY, 11, "normal")
    
    # Destaques em Tabelas
    TABLE_HEADER = (FONT_FAMILY, 11, "bold")
    TABLE_DATA_HIGHLIGHT = (FONT_FAMILY, 12, "bold")

# =============================================================================
# ESPAÇAMENTOS (Grid System de 4pt/8pt)
# =============================================================================
class Spacing:
    XS = 4
    SM = 8
    MD = 16
    LG = 24
    XL = 32
    XXL = 48

# =============================================================================
# BORDAS E ELEVAÇÕES
# =============================================================================
class Radii:
    NONE = 0
    SM = 4
    MD = 8      # Padrão para Cards modernos
    LG = 12
    FULL = 9999 # Para botões redondos ou badges
