# -*- coding: utf-8 -*-
"""
config/ui_theme.py

Definições de cores e estilos visuais para interface do IntegRAGal.

FASE 3: Cores de fundo para resultados na TreeView.

Criado em: 2025-12-XX
Parte da refatoração UI - feature/ui-analise-placa-2025_12
"""

from typing import Dict
from config.enums import ResultStatus
from utils.text_result_classifier import classify_result_text
from ui.theme.design_tokens import SemanticColors

# Cores de fundo para resultados — alinhadas com tag_configure e plate_viewer
UI_COLORS: Dict[str, str] = {
    "detectado": SemanticColors.DETECTADO,
    "inconclusivo": SemanticColors.INCONCLUSIVO,
    "invalido": SemanticColors.INVALIDO,
    "nao_detectavel": SemanticColors.NAO_DETECTAVEL,
    "nao_detectado": "",
    "padrao": "",
}

_TOKEN_TO_COLOR = {
    "DET": UI_COLORS["detectado"],
    "INC": UI_COLORS["inconclusivo"],
    "INV": UI_COLORS["invalido"],
    "ND": UI_COLORS["nao_detectavel"],
}


def obter_cor_resultado(resultado) -> str:
    """Retorna cor de fundo canônica para um resultado.

    Delega classificação para classify_result_text (ordem INV>INC>ND>DET),
    evitando a colisão 'DET' em 'INDETERMINADO' e 'NAO DETECTAVEL'.
    """
    token = classify_result_text(resultado)
    return _TOKEN_TO_COLOR.get(token, UI_COLORS["padrao"])
