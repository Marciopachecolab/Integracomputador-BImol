# -*- coding: utf-8 -*-
"""
Persistence Provider

Seleciona e fornece o backend de persistencia (CSV/SQLite) conforme configuracao.
"""

from __future__ import annotations

from typing import Optional

from domain.persistence_contracts import PersistenceProvider, StorageUnavailableError
from services.core.config_service import config_service
from services.persistence.persistence_adapters import CsvPersistenceProvider, SQLitePersistenceProvider
from utils.logger import registrar_log

_provider: Optional[PersistenceProvider] = None


def reset_persistence_provider() -> None:
    """Reseta o provider singleton (uso em testes)."""
    global _provider
    _provider = None


def get_persistence_provider(force_refresh: bool = False) -> PersistenceProvider:
    """
    Retorna provider configurado (singleton).

    Args:
        force_refresh: Recria o provider mesmo que ja exista.
    """
    global _provider
    if _provider is None or force_refresh:
        backend = config_service.get_storage_backend()
        if backend == "sqlite":
            _provider = SQLitePersistenceProvider()
            registrar_log("PersistenceProvider", "Backend sqlite selecionado.", "INFO")
        elif backend == "postgres":
            message = (
                "Backend postgres configurado, mas provider dedicado ainda nao foi implementado. "
                "Backend rejeitado explicitamente para evitar fallback silencioso."
            )
            registrar_log(
                "PersistenceProvider",
                message,
                "ERROR",
            )
            raise StorageUnavailableError(message)
        else:
            _provider = CsvPersistenceProvider()
            registrar_log("PersistenceProvider", "Backend csv selecionado.", "INFO")
    return _provider
