# -*- coding: utf-8 -*-
"""
Servi Service Container - Dependency Injection Container

Solução para Problema Arquitetural P1 (Acoplamento Forte UI→Services).

Este container centraliza a criação e gestão de instâncias de services,
permitindo injeção de dependência em controllers e views.

Benefícios:
- Desacoplamento: UI não conhece implementação concreta de services
- Testabilidade: Fácil mockar services para testes unitários
- Centralization: Um único ponto de configuração de dependências
"""

from typing import Optional

from models import AppState
from services.analysis.analysis_service import AnalysisService
from services.core.config_service import ConfigService
from services.reports.history_report import HistoryReportService
from services.core.event_bus import EventBus
from domain.persistence_contracts import PersistenceProvider


class ServiceContainer:
    """
    Container de services para injeção de dependência.
    
    Uso:
        # Em main.py:
        container = ServiceContainer()
        menu_handler = MenuHandler(app, container)
        
        # Em MenuHandler:
        def executar_analise(self):
            self.services.analysis.executar_analise(...)
    """
    
    def __init__(self, app_state: Optional[AppState] = None):
        # Singleton instances
        self._config_service: Optional[ConfigService] = None
        self._analysis_service: Optional[AnalysisService] = None
        self._history_service: Optional[HistoryReportService] = None
        self._event_bus = EventBus  # Já é singleton
        self._persistence_provider: Optional[PersistenceProvider] = None
        self._app_state: Optional[AppState] = app_state
        
        # P4 FIX: Repositories para SQLite
        self._user_repo = None
        self._history_repo = None

    def bind_app_state(self, app_state: AppState) -> None:
        """Vincula o estado atual da aplicacao ao container."""
        if app_state is self._app_state:
            return
        self._app_state = app_state
        self._analysis_service = None
    
    @property
    def config(self) -> ConfigService:
        """Retorna instância singleton de ConfigService."""
        if self._config_service is None:
            from services.core.config_service import config_service
            self._config_service = config_service
        return self._config_service
    
    @property
    def analysis(self) -> AnalysisService:
        """Retorna instancia singleton de AnalysisService."""
        if self._app_state is None:
            self._app_state = AppState()
        if self._analysis_service is None:
            self._analysis_service = AnalysisService(self._app_state)
        elif self._analysis_service.app_state is not self._app_state:
            self._analysis_service = AnalysisService(self._app_state)
        return self._analysis_service

    @property
    def history(self) -> HistoryReportService:
        """Retorna instância de HistoryReportService."""
        if self._history_service is None:
            from services.reports.history_report import HistoryReportService
            self._history_service = HistoryReportService()
        return self._history_service
    
    @property
    def events(self) -> EventBus:
        """Retorna Event Bus."""
        return self._event_bus

    @property
    def persistence(self) -> PersistenceProvider:
        """Retorna provider de persistencia (CSV/SQLite)."""
        if self._persistence_provider is None:
            from services.persistence.persistence_provider import get_persistence_provider
            self._persistence_provider = get_persistence_provider()
        return self._persistence_provider
    
    # P4 FIX: Repositories
    @property
    def users(self):
        """Retorna UserRepository via provider."""
        if self._user_repo is None:
            self._user_repo = self.persistence.users()
        return self._user_repo
    
    @property
    def history_repo(self):
        """Retorna HistoryRepository via provider."""
        if self._history_repo is None:
            self._history_repo = self.persistence.history()
        return self._history_repo


# Global container instance (para compatibilidade com código legado)
_global_container: Optional[ServiceContainer] = None


def get_service_container(app_state: Optional[AppState] = None) -> ServiceContainer:
    """Retorna container global de services (Singleton)."""
    global _global_container
    if _global_container is None:
        _global_container = ServiceContainer(app_state=app_state)
    elif app_state is not None:
        _global_container.bind_app_state(app_state)
    return _global_container


def reset_service_container_for_tests() -> None:
    """Reseta container global (uso em testes)."""
    global _global_container
    _global_container = None
