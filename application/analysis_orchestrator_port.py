# -*- coding: utf-8 -*-
"""Contratos de orquestracao de analise (Fase B2-T01)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol, runtime_checkable

import pandas as pd


class AnalysisOrchestratorError(RuntimeError):
    """Base para erros tipados da orquestracao de analise."""


class ContractResolutionError(AnalysisOrchestratorError):
    """Falha ao resolver contrato de runtime."""


class EquipmentDetectionError(AnalysisOrchestratorError):
    """Falha ao detectar/confirmar equipamento."""


class InputFileError(AnalysisOrchestratorError):
    """Falha de leitura/acesso aos arquivos de entrada."""


class AnalysisExecutionError(AnalysisOrchestratorError):
    """Falha durante processamento da analise."""


def _require_non_empty(value: str, field_name: str) -> None:
    if not value or not str(value).strip():
        raise ValueError(f"{field_name} nao pode ser vazio.")


@dataclass(frozen=True)
class AnalysisOrchestratorRequestDTO:
    """Entrada canonica para orquestracao de analise."""

    exam_name: str
    lote: str
    data_exame: str
    resultado_path: Path
    extracao_path: Path | None = None
    equipment_hint: str | None = None
    usuario: str = ""

    def __post_init__(self) -> None:
        _require_non_empty(self.exam_name, "exam_name")
        _require_non_empty(self.lote, "lote")
        _require_non_empty(self.data_exame, "data_exame")
        object.__setattr__(self, "resultado_path", Path(self.resultado_path))
        if self.extracao_path is not None:
            object.__setattr__(self, "extracao_path", Path(self.extracao_path))


@dataclass(frozen=True)
class AnalysisOrchestratorResponseDTO:
    """Saida canonica da orquestracao de analise."""

    df_resultado: pd.DataFrame
    status_corrida: str
    metadados: Mapping[str, Any]
    contract_versions: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.df_resultado is None:
            raise ValueError("df_resultado nao pode ser None.")
        _require_non_empty(self.status_corrida, "status_corrida")


@runtime_checkable
class AnalysisOrchestratorPort(Protocol):
    """Porta da camada application para execucao de analise."""

    def execute(
        self,
        request: AnalysisOrchestratorRequestDTO,
    ) -> AnalysisOrchestratorResponseDTO:
        """Executa analise ponta a ponta sem dependencia de UI."""

