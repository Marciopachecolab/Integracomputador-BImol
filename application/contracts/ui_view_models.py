# -*- coding: utf-8 -*-
"""
application/contracts/ui_view_models.py

Contratos estritos para a camada de visualização (UI).
Estes ViewModels garantem que a UI (CustomTkinter) não receba, não processe,
nem tenha conhecimento da existência de `pandas.DataFrame`.
Todo processamento complexo é resolvido pela camada de serviço/presenter 
antes de instanciar estes DTOs.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List

@dataclass
class DataGridRowViewModel:
    """
    Representa uma linha plana e pré-computada na ScientificDataGrid.
    Nenhuma lógica de decisão de cor ou classificação deve existir na View após consumir isto.
    """
    well: str                   # Poço (ex: "A01")
    sample: str                 # Nome da amostra ou código do paciente
    targets_summary: str        # Resumo legível (ex: "SC2: Det | FLUA: ND")
    result_tag: str             # Tag unificada de resultado (ex: "detectado", "inconclusivo", "invalido", "nao_detectavel")
    is_control: bool            # True se for CN/CP, forçando a cor da placa
    target_details: Dict[str, str] = field(default_factory=dict) # Mapa Alvo -> "CT (formatado)"
    is_selected: bool = False   # Estado da checkbox na interface
    is_disabled: bool = False   # Se True, desabilita interações (ex: poço vazio ou fora do escopo)


@dataclass
class PlateMapViewModel:
    """
    Representa o estado visual de um único poço na malha do PlateInteractiveMap.
    """
    well_pos: str               # Coordenada espacial (ex: "A1" ou "A01")
    sample_id: str              # Identificador curto para tooltip/hover
    result_tag: str             # Usado para resgatar a cor em ui.theme.design_tokens.SemanticColors
    is_control: bool            # Afeta a hierarquia visual do poço
    group_id: Optional[str] = None # Usado para colorir agrupamentos (Mapas de extração)
    group_color: str = ""       # Cor pré-calculada do grupo (se houver)


@dataclass
class RunSummaryViewModel:
    """
    Representa o Header Card de estatísticas.
    """
    total_wells: int
    detected_count: int
    inconclusive_count: int
    invalid_count: int
    control_count: int
    exam_name: str
    plate_id: str
