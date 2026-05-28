# -*- coding: utf-8 -*-
"""Constantes de CT para classificação de resultados por protocolo."""

from dataclasses import dataclass


@dataclass
class CTThresholdsVR1E2:
    """Thresholds para VR1E2 Biomanguinhos 7500."""
    DETECT_MAX: float = 35.0       # CT <= 35 → Detectado (alinhado com requirements.md §5.1)
    INCONC_MIN: float = 35.01      # Faixa inconclusiva início
    INCONC_MAX: float = 40.0       # Faixa inconclusiva fim
    RP_MIN: float = 15.0           # RP válido mínimo
    RP_MAX: float = 35.0           # RP válido máximo


# Instância padrão para uso direto
VR1E2_THRESHOLDS = CTThresholdsVR1E2()
