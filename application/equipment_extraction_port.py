# -*- coding: utf-8 -*-
"""Contratos para deteccao e extracao de equipamentos (Fase B)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol, runtime_checkable

import pandas as pd


class EquipmentExtractionError(RuntimeError):
    """Erro base da porta de extracao de equipamentos."""


class EquipmentDetectionError(EquipmentExtractionError):
    """Falha ao detectar equipamento."""


class EquipmentConfigError(EquipmentExtractionError):
    """Falha ao resolver configuracao de equipamento."""


class EquipmentExtractionFailure(EquipmentExtractionError):
    """Falha ao extrair dados do equipamento."""


@dataclass(frozen=True)
class EquipmentDetectionResult:
    """Resultado tipado da deteccao de equipamento."""

    equipamento: str
    confianca: float
    alternativas: list[dict[str, Any]] = field(default_factory=list)
    estrutura_detectada: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Compatibilidade com o dialogo legado (dict)."""
        return {
            "equipamento": self.equipamento,
            "confianca": self.confianca,
            "alternativas": list(self.alternativas or []),
            "estrutura_detectada": dict(self.estrutura_detectada or {}),
        }


@runtime_checkable
class EquipmentExtractionPort(Protocol):
    """Porta para deteccao e extracao de dados por equipamento."""

    def detect_equipment(self, arquivo_resultados: Path) -> EquipmentDetectionResult:
        """Detecta equipamento a partir do arquivo."""

    def list_equipamentos(self) -> list[str]:
        """Lista equipamentos cadastrados/disponiveis."""

    def resolve_config(self, equipamento: str):
        """Resolve a configuracao do equipamento."""

    def extract_results(self, arquivo_resultados: Path, config) -> pd.DataFrame:
        """Extrai e normaliza dados do arquivo para o formato canonico."""
