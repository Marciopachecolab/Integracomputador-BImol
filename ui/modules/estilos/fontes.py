"""
Configuração de Fontes - IntegaGal
Fase 3.1 - Dashboard
"""

# Famílias de Fontes
FONTE_PRINCIPAL = "Arial"
FONTE_SECUNDARIA = "Segoe UI"
FONTE_MONOSPACE = "Consolas"

# Tamanhos de Fonte
TAMANHOS = {
    'titulo_grande': 24,
    'titulo': 18,
    'subtitulo': 16,
    'subtitulo_pequeno': 14,
    'corpo': 12,
    'corpo_pequeno': 11,
    'caption': 10,
    'mini': 9,
}

# Pesos de Fonte
PESO = {
    'normal': 'normal',
    'bold': 'bold',
}

# Configurações Completas
FONTES = {
    # Títulos
    'titulo_grande': (FONTE_PRINCIPAL, TAMANHOS['titulo_grande'], PESO['bold']),
    'titulo': (FONTE_PRINCIPAL, TAMANHOS['titulo'], PESO['bold']),
    'subtitulo': (FONTE_PRINCIPAL, TAMANHOS['subtitulo'], PESO['bold']),
    'subtitulo_normal': (FONTE_PRINCIPAL, TAMANHOS['subtitulo'], PESO['normal']),
    'subtitulo_pequeno': (FONTE_PRINCIPAL, TAMANHOS['subtitulo_pequeno'], PESO['bold']),
    
    # Corpo
    'corpo': (FONTE_PRINCIPAL, TAMANHOS['corpo'], PESO['normal']),
    'corpo_bold': (FONTE_PRINCIPAL, TAMANHOS['corpo'], PESO['bold']),
    'corpo_pequeno': (FONTE_PRINCIPAL, TAMANHOS['corpo_pequeno'], PESO['normal']),
    
    # Especiais
    'caption': (FONTE_SECUNDARIA, TAMANHOS['caption'], PESO['normal']),
    'monospace': (FONTE_MONOSPACE, TAMANHOS['corpo'], PESO['normal']),
    'monospace_pequeno': (FONTE_MONOSPACE, TAMANHOS['corpo_pequeno'], PESO['normal']),
}

def obter_fonte(tipo: str) -> tuple:
    """
    Retorna configuração de fonte por tipo
    
    Args:
        tipo: Nome do tipo de fonte (ex: 'titulo', 'corpo')
        
    Returns:
        Tupla (família, tamanho, peso)
    """
    return FONTES.get(tipo, FONTES['corpo'])
