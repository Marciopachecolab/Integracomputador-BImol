# extracao/mapeamento_placas.py
from typing import Dict, List

from domain.plate_mapping import (
    gerar_mapeamento_24 as _gerar_mapeamento_24,
    gerar_mapeamento_32 as _gerar_mapeamento_32,
    gerar_mapeamento_48 as _gerar_mapeamento_48,
    gerar_mapeamento_96 as _gerar_mapeamento_96,
)
from utils.logger import registrar_log


def gerar_mapeamento_96() -> List[Dict]:
    """Facade para domain.plate_mapping.gerar_mapeamento_96."""
    try:
        mapeamento = _gerar_mapeamento_96()
        registrar_log(
            "Mapeamento Placas",
            "Mapeamento de 96 pocos gerado com sucesso.",
            level="INFO",
        )
        return mapeamento
    except Exception as e:
        registrar_log(
            "Mapeamento Placas",
            f"Erro ao gerar mapeamento de 96 pocos: {e}",
            level="ERROR",
        )
        raise


def gerar_mapeamento_48(parte: int = 1) -> List[Dict]:
    """Facade para domain.plate_mapping.gerar_mapeamento_48."""
    try:
        mapeamento = _gerar_mapeamento_48(parte)
        registrar_log(
            "Mapeamento Placas",
            f"Mapeamento 1-para-2 de 48 pocos (parte {parte}) gerado.",
            "INFO",
        )
        return mapeamento
    except Exception as e:
        registrar_log(
            "Mapeamento Placas",
            f"Erro ao gerar mapeamento de 48 pocos (parte {parte}): {e}",
            level="ERROR",
        )
        raise


def gerar_mapeamento_32(parte: int = 1) -> List[Dict]:
    """Facade para domain.plate_mapping.gerar_mapeamento_32."""
    try:
        mapeamento = _gerar_mapeamento_32(parte)
        registrar_log(
            "Mapeamento Placas",
            f"Mapeamento de 32 pocos (parte {parte}) gerado com sucesso.",
            level="INFO",
        )
        return mapeamento
    except Exception as e:
        registrar_log(
            "Mapeamento Placas",
            f"Erro ao gerar mapeamento de 32 pocos (parte {parte}): {e}",
            level="ERROR",
        )
        raise


def gerar_mapeamento_24(parte: int = 1) -> List[Dict]:
    """Facade para domain.plate_mapping.gerar_mapeamento_24."""
    try:
        mapeamento = _gerar_mapeamento_24(parte)
        registrar_log(
            "Mapeamento Placas",
            f"Mapeamento de 24 pocos (parte {parte}) gerado com sucesso.",
            level="INFO",
        )
        return mapeamento
    except Exception as e:
        registrar_log(
            "Mapeamento Placas",
            f"Erro ao gerar mapeamento de 24 pocos (parte {parte}): {e}",
            level="ERROR",
        )
        raise
