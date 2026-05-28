"""
Paleta de Cores - IntegaGal
Fase 3.1 - Dashboard
"""

# Cores Principais
CORES = {
    # Primárias
    'primaria': '#1E88E5',          # Azul principal
    'primaria_hover': '#1976D2',    # Azul hover
    'primaria_claro': '#64B5F6',    # Azul claro
    'primaria_escuro': '#0D47A1',   # Azul escuro
    
    # Secundárias
    'secundaria': '#43A047',        # Verde sucesso
    'secundaria_hover': '#388E3C',  # Verde hover
    'secundaria_claro': '#81C784',  # Verde claro
    
    # Status
    'sucesso': '#43A047',           # Verde
    'erro': '#E53935',              # Vermelho
    'aviso': '#FB8C00',             # Laranja
    'info': '#1E88E5',              # Azul
    
    # Cinzas
    'fundo': '#F5F5F5',             # Cinza muito claro
    'fundo_escuro': '#E0E0E0',      # Cinza claro
    'fundo_card': '#FFFFFF',        # Branco
    'borda': '#BDBDBD',             # Cinza médio
    
    # Textos
    'texto': '#212121',             # Preto texto
    'texto_secundario': '#757575',  # Cinza texto
    'texto_claro': '#FFFFFF',       # Branco texto
    
    # Especiais
    'branco': '#FFFFFF',
    'preto': '#000000',
    'transparente': 'transparent',
}

# Cores por Status de Análise
STATUS_CORES = {
    'valida': CORES['sucesso'],
    'invalida': CORES['erro'],
    'aviso': CORES['aviso'],
    'pendente': CORES['texto_secundario'],
    'processando': CORES['info'],
}

# Cores para Gráficos
GRAFICO_CORES = [
    '#1E88E5',  # Azul
    '#43A047',  # Verde
    '#FB8C00',  # Laranja
    '#E53935',  # Vermelho
    '#8E24AA',  # Roxo
    '#00ACC1',  # Ciano
    '#FDD835',  # Amarelo
    '#5E35B1',  # Índigo
]

# Gradientes
GRADIENTE_AZUL = ['#E3F2FD', '#BBDEFB', '#90CAF9', '#64B5F6', '#42A5F5', '#1E88E5']
GRADIENTE_VERDE = ['#E8F5E9', '#C8E6C9', '#A5D6A7', '#81C784', '#66BB6A', '#43A047']
GRADIENTE_VERMELHO = ['#FFEBEE', '#FFCDD2', '#EF9A9A', '#E57373', '#EF5350', '#E53935']

# Sombras
SOMBRA_LEVE = 'gray10'
SOMBRA_MEDIA = 'gray20'
SOMBRA_FORTE = 'gray30'

def hex_to_rgb(hex_color: str) -> tuple:
    """Converte cor hexadecimal para RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Converte RGB para hexadecimal"""
    return f'#{r:02x}{g:02x}{b:02x}'

def ajustar_luminosidade(hex_color: str, fator: float) -> str:
    """
    Ajusta luminosidade da cor
    fator > 1: mais claro
    fator < 1: mais escuro
    """
    r, g, b = hex_to_rgb(hex_color)
    r = min(255, int(r * fator))
    g = min(255, int(g * fator))
    b = min(255, int(b * fator))
    return rgb_to_hex(r, g, b)
