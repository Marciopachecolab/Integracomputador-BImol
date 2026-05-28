# -*- coding: utf-8 -*-
"""
Event Bus - Padrão Pub/Sub para Desacoplamento de Componentes

Solução para Problema Arquitetural P2 (Janelas Modais Aninhadas).

O Event Bus permite que componentes se comuniquem sem conhecer uns aos outros diretamente,
evitando acoplamento e ciclos de dependência.

Uso:
    # No componente emissor:
    from services.core.event_bus import EventBus
    EventBus.publish("plate_saved", {"plate_id": 123, "user": "admin"})
    
    # No componente receptor:
    def on_plate_saved(data):
        print(f"Placa {data['plate_id']} salva por {data['user']}")
    
    EventBus.subscribe("plate_saved", on_plate_saved)
"""

from typing import Callable, Dict, List, Any
import threading
from utils.logger import registrar_log


class EventBus:
    """
    Sistema de eventos centralizado (Singleton) para comunicação entre componentes.
    
    Thread-safe para uso em ambientes multi-thread.
    """
    
    _subscribers: Dict[str, List[Callable]] = {}
    _lock = threading.Lock()
    
    @classmethod
    def subscribe(cls, event_name: str, callback: Callable[[Any], None]) -> None:
        """
        Inscreve um callback para ser notificado quando evento ocorrer.
        
        Args:
            event_name: Nome do evento (ex: "plate_saved", "analysis_complete")
            callback: Função a ser chamada quando evento for publicado.
                     Deve aceitar um argumento (dict com dados do evento).
        
        Example:
            def handle_save(data):
                print(f"Saved: {data}")
            
            EventBus.subscribe("item_saved", handle_save)
        """
        with cls._lock:
            if event_name not in cls._subscribers:
                cls._subscribers[event_name] = []
            
            if callback not in cls._subscribers[event_name]:
                cls._subscribers[event_name].append(callback)
                registrar_log(
                    "EventBus", 
                    f"Subscriber registered for '{event_name}' (total: {len(cls._subscribers[event_name])})",
                    "DEBUG"
                )
    
    @classmethod
    def unsubscribe(cls, event_name: str, callback: Callable[[Any], None]) -> None:
        """
        Remove inscrição de callback para um evento.
        
        Args:
            event_name: Nome do evento
            callback: Função a ser removida
        """
        with cls._lock:
            if event_name in cls._subscribers:
                try:
                    cls._subscribers[event_name].remove(callback)
                    registrar_log(
                        "EventBus",
                        f"Subscriber unregistered from '{event_name}'",
                        "DEBUG"
                    )
                except ValueError:
                    pass  # Callback não estava inscrito
    
    @classmethod
    def publish(cls, event_name: str, data: Any = None) -> None:
        """
        Publica um evento, notificando todos os subscribers.
        
        Args:
            event_name: Nome do evento
            data: Dados a serem passados para os callbacks (geralmente dict)
        
        Example:
            EventBus.publish("user_login", {"user_id": 42, "timestamp": "2026-01-08"})
        """
        with cls._lock:
            subscribers = cls._subscribers.get(event_name, []).copy()
        
        if not subscribers:
            registrar_log(
                "EventBus",
                f"Event '{event_name}' published but no subscribers",
                "DEBUG"
            )
            return
        
        registrar_log(
            "EventBus",
            f"Publishing '{event_name}' to {len(subscribers)} subscriber(s)",
            "DEBUG"
        )
        
        # Executar callbacks (fora do lock para evitar deadlock)
        for callback in subscribers:
            try:
                callback(data)
            except Exception as e:
                registrar_log(
                    "EventBus",
                    f"Error in event handler for '{event_name}': {e}",
                    "ERROR"
                )
    
    @classmethod
    def clear_all_subscribers(cls) -> None:
        """
        Remove todos os subscribers (útil para testes).
        
        ⚠️ USE COM CUIDADO - apenas para debugging/testing.
        """
        with cls._lock:
            cls._subscribers.clear()
            registrar_log("EventBus", "All subscribers cleared", "WARNING")
    
    @classmethod
    def get_subscriber_count(cls, event_name: str) -> int:
        """Retorna quantidade de subscribers para um evento."""
        with cls._lock:
            return len(cls._subscribers.get(event_name, []))


# Eventos Predefinidos do Sistema (Documentação)
class SystemEvents:
    """
    Catálogo de eventos do sistema para documentação.
    
    Use estas constantes em vez de strings hardcoded para evitar typos.
    """
    
    # Eventos de Análise
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_COMPLETED = "analysis.completed"
    ANALYSIS_FAILED = "analysis.failed"
    
    # Eventos de Placa/Mapa
    PLATE_EDITED = "plate.edited"
    PLATE_SAVED = "plate.saved"
    PLATE_VALIDATED = "plate.validated"
    
    # Eventos de Janelas
    WINDOW_OPENED = "window.opened"
    WINDOW_CLOSED = "window.closed"
    
    # Eventos de Dados
    DATA_LOADED = "data.loaded"
    DATA_SAVED = "data.saved"
    
    # Eventos de Usuário
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
