"""
Estilos - IntegaGal
Exporta cores e fontes
"""

from .cores import CORES, STATUS_CORES, GRAFICO_CORES, hex_to_rgb, rgb_to_hex, ajustar_luminosidade
from .fontes import FONTES, TAMANHOS, obter_fonte

__all__ = [
    'CORES',
    'STATUS_CORES',
    'GRAFICO_CORES',
    'FONTES',
    'TAMANHOS',
    'obter_fonte',
    'hex_to_rgb',
    'rgb_to_hex',
    'ajustar_luminosidade',
]
