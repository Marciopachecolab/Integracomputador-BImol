# models.py
from typing import Optional

import pandas as pd


class AppState:
    """
    Armazena e gere o estado partilhado da aplicação.
    Este modelo de dados é importado por qualquer módulo que precise
    de aceder ou modificar o estado da aplicação.
    """

    def __init__(self):
        self.usuario_logado: Optional[str] = None
        self.nivel_acesso: Optional[str] = None  # NOVO: Nível de acesso do usuário
        self.dados_extracao: Optional[pd.DataFrame] = None
        self.parte_placa: Optional[int] = None
        self.resultados_analise: Optional[pd.DataFrame] = None
        self.lote_kit: Optional[str] = None
        self.exame_selecionado: Optional[str] = None
        # FASE 4: Metadados da extração
        self.numero_extracao: Optional[str] = None
        self.caminho_arquivo_extracao: Optional[str] = None
        # Metadados opcionais da corrida (Fase 5 - contrato sem bloqueio)
        self.nome_corrida: Optional[str] = None
        self.quem_fez_extracao: Optional[str] = None
        self.quem_preparou_placa: Optional[str] = None
        self.observacoes_corrida: Optional[str] = None
        # Optional overrides for control wells (lists of well names)
        self.control_cn_wells: Optional[list[str]] = None
        self.control_cp_wells: Optional[list[str]] = None
        # Equipment/Plate type detection (Fase 1.4)
        self.tipo_de_placa_detectado: Optional[str] = None  # Nome detectado automaticamente
        self.tipo_de_placa_config: Optional[object] = None  # EquipmentConfig object
        self.tipo_de_placa_selecionado: Optional[str] = None  # Nome confirmado pelo usuário
        # Runtime contratual (fase 3)
        self.exam_id: Optional[str] = None
        self.equipment_id: Optional[str] = None
        self.analysis_rules_profile_id: Optional[str] = None
        self.gal_profile_id: Optional[str] = None
        self.storage_profile_id: Optional[str] = None
        self.contract_versions: Optional[dict[str, str]] = None

    def reset_analise_state(self):
        """Reseta o estado relacionado a uma análise específica."""
        self.resultados_analise = None
        self.lote_kit = None
        self.exame_selecionado = None
        self.exam_id = None
        self.nome_corrida = None
        self.quem_fez_extracao = None
        self.quem_preparou_placa = None
        self.observacoes_corrida = None

    def reset_extracao_state(self):
        """Reseta o estado da extração e da análise."""
        self.dados_extracao = None
        self.parte_placa = None
        self.numero_extracao = None  # FASE 4
        self.caminho_arquivo_extracao = None  # FASE 4
        self.reset_analise_state()
        self.control_cn_wells = None
        self.control_cp_wells = None
