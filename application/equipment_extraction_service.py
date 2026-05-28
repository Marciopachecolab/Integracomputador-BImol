# -*- coding: utf-8 -*-
"""Servico de extracao de equipamentos com adapters dedicados."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Protocol

import pandas as pd

from application.equipment_extraction_port import (
    EquipmentConfigError,
    EquipmentDetectionError,
    EquipmentDetectionResult,
    EquipmentExtractionFailure,
    EquipmentExtractionPort,
)
from services.equipment.equipment_detector import detectar_equipamento
from services.equipment.equipment_registry import EquipmentConfig, EquipmentRegistry
from services.equipment.equipment_extractors import (
    extrair_7500,
    extrair_7500_extended,
    extrair_quantstudio,
    extrair_dados_equipamento,
)
from utils.logger import registrar_log


class EquipmentExtractorAdapter(Protocol):
    """Interface comum para adapters de extracao por equipamento."""

    def extract(self, arquivo_resultados: Path, config: EquipmentConfig) -> pd.DataFrame:
        """Extrai dados do equipamento e retorna DataFrame normalizado."""


@dataclass
class EquipmentExtractor7500Adapter:
    """Adapter dedicado para 7500 (inclui variante extended)."""

    def extract(self, arquivo_resultados: Path, config: EquipmentConfig) -> pd.DataFrame:
        if config.nome == "7500_Extended" or config.extrator_nome == "extrair_7500_extended":
            return extrair_7500_extended(str(arquivo_resultados), config)
        return extrair_7500(str(arquivo_resultados), config)


@dataclass
class EquipmentExtractorQuantiAdapter:
    """Adapter dedicado para QuantStudio/Quanti."""

    def extract(self, arquivo_resultados: Path, config: EquipmentConfig) -> pd.DataFrame:
        return extrair_quantstudio(str(arquivo_resultados), config)


@dataclass
class EquipmentExtractorLegacyAdapter:
    """Adapter fallback usando a resolucao legacy por nome do equipamento."""

    def extract(self, arquivo_resultados: Path, config: EquipmentConfig) -> pd.DataFrame:
        return extrair_dados_equipamento(str(arquivo_resultados), config)


class EquipmentExtractionService(EquipmentExtractionPort):
    """Implementacao da porta para deteccao e extracao de equipamentos."""

    def __init__(
        self,
        *,
        registry: Optional[EquipmentRegistry] = None,
        detector: Optional[Callable[[str], dict]] = None,
        adapters: Optional[Dict[str, EquipmentExtractorAdapter]] = None,
    ) -> None:
        self._registry = registry
        self._detector = detector or detectar_equipamento
        self._adapters = adapters or self._default_adapters()
        self._legacy_adapter = EquipmentExtractorLegacyAdapter()

    def detect_equipment(self, arquivo_resultados: Path) -> EquipmentDetectionResult:
        try:
            resultado = self._detector(str(arquivo_resultados))
        except Exception as exc:  # noqa: BLE001
            raise EquipmentDetectionError(str(exc)) from exc

        equipamento = str((resultado or {}).get("equipamento") or "").strip()
        confianca = float((resultado or {}).get("confianca") or 0.0)
        alternativas = list((resultado or {}).get("alternativas") or [])
        estrutura = dict((resultado or {}).get("estrutura_detectada") or {})

        if not equipamento:
            raise EquipmentDetectionError("equipamento nao detectado")

        return EquipmentDetectionResult(
            equipamento=equipamento,
            confianca=confianca,
            alternativas=alternativas,
            estrutura_detectada=estrutura,
        )

    def list_equipamentos(self) -> list[str]:
        if self._registry is None:
            self._registry = EquipmentRegistry()
        self._registry.load()
        return self._registry.listar_equipamentos()

    def resolve_config(self, equipamento: str) -> EquipmentConfig:
        if self._registry is None:
            self._registry = EquipmentRegistry()
        self._registry.load()
        config = self._registry.get(equipamento)
        if not config:
            raise EquipmentConfigError(f"configuracao nao encontrada: {equipamento}")
        return config

    def extract_results(self, arquivo_resultados: Path, config: EquipmentConfig) -> pd.DataFrame:
        if not Path(arquivo_resultados).exists():
            raise EquipmentExtractionFailure(f"Arquivo de resultados nao encontrado: {arquivo_resultados}")

        adapter = self._select_adapter(config)
        try:
            return adapter.extract(Path(arquivo_resultados), config)
        except Exception as exc:  # noqa: BLE001
            registrar_log(
                "EquipmentExtraction",
                f"Falha no adapter dedicado: {exc}. Usando fallback legacy.",
                "WARNING",
            )
            try:
                return self._legacy_adapter.extract(Path(arquivo_resultados), config)
            except Exception as legacy_exc:  # noqa: BLE001
                raise EquipmentExtractionFailure(str(legacy_exc)) from legacy_exc

    def _select_adapter(self, config: EquipmentConfig) -> EquipmentExtractorAdapter:
        keys = [
            str(config.nome or "").strip(),
            str(config.extrator_nome or "").strip(),
        ]
        for key in keys:
            if key in self._adapters:
                return self._adapters[key]
        return self._legacy_adapter

    @staticmethod
    def _default_adapters() -> Dict[str, EquipmentExtractorAdapter]:
        adapter_7500 = EquipmentExtractor7500Adapter()
        adapter_quanti = EquipmentExtractorQuantiAdapter()
        return {
            "7500": adapter_7500,
            "7500_Extended": adapter_7500,
            "extrair_7500": adapter_7500,
            "extrair_7500_extended": adapter_7500,
            "QuantStudio": adapter_quanti,
            "Quanti": adapter_quanti,
            "extrair_quantstudio": adapter_quanti,
        }
