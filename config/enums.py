# -*- coding: utf-8 -*-
from enum import Enum

class ResultStatus(str, Enum):
    """
    Enum para padronizar os status de resultado.
    Herda de str para manter compatibilidade com código legado que espera strings.
    """
    DETECTAVEL = "Detectável"
    NAO_DETECTAVEL = "Não Detectável"
    INDETERMINADO = "Indeterminado"
    
    # Para Controles Internos (RP)
    VALIDO = "Válido"
    INVALIDO = "Inválido"
    
    def __str__(self):
        return self.value
