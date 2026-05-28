"""
Gerenciador de navegacao para a aplicacao IntegraGAL.

Fase 2 (single-window):
- suporta registro de modulos;
- renderiza paginas no ModuleHost da janela principal.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from utils.logger import registrar_log


class NavigationManager:
    """Gerenciador de navegacao entre modulos."""

    def __init__(self, main_window):
        self.main_window = main_window
        self.current_module: Optional[str] = None
        self.navigation_history: list[dict[str, Optional[str]]] = []
        self.module_states: dict[str, dict[str, object]] = {}
        self.module_factories: dict[str, Callable] = {}

    def register_module(self, module_name: str, factory: Callable) -> None:
        """Registra uma factory de modulo para renderizacao no ModuleHost."""
        self.module_factories[module_name] = factory

    def unregister_module(self, module_name: str) -> None:
        """Remove uma factory de modulo registrada."""
        self.module_factories.pop(module_name, None)

    def navigate_to(self, module_name: str, callback: Optional[Callable] = None):
        """
        Navega para um modulo especifico.

        Prioridade de execucao:
        1. callback explicito;
        2. modulo registrado no host.
        """
        try:
            self.navigation_history.append(
                {
                    "from": self.current_module,
                    "to": module_name,
                    "timestamp": self._get_current_timestamp(),
                }
            )

            old_module = self.current_module
            self.current_module = module_name
            if old_module:
                self._save_module_state(old_module)

            registrar_log(
                "Navegação", f"Navegação de '{old_module}' para '{module_name}'", "INFO"
            )

            if callback is not None:
                callback()
            elif module_name in self.module_factories:
                self._render_registered_module(module_name)

            self._update_ui_for_module(module_name)
        except Exception as exc:
            registrar_log(
                "Navegação", f"Erro na navegação para '{module_name}': {exc}", "ERROR"
            )

    def _render_registered_module(self, module_name: str) -> None:
        module_host = getattr(self.main_window, "module_host", None)
        factory = self.module_factories.get(module_name)
        if module_host is None or factory is None:
            return
        module_host.show_module(module_name, factory)

    def _get_current_timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _save_module_state(self, module_name: str):
        if hasattr(self.main_window, "app_state"):
            self.module_states[module_name] = {
                "app_state": self.main_window.app_state,
                "timestamp": self._get_current_timestamp(),
            }

    def _update_ui_for_module(self, module_name: str):
        module_configs = {
            "main": {"title": "IntegraGAL - Menu Principal", "actions": []},
            "main_menu": {"title": "IntegraGAL - Menu Principal", "actions": []},
            "dashboard": {"title": "IntegraGAL - Dashboard", "actions": []},
            "graficos_qualidade": {"title": "IntegraGAL - Graficos de Qualidade", "actions": []},
            "historico_analises": {"title": "IntegraGAL - Historico de Analises", "actions": []},
            "analise_completa": {"title": "IntegraGAL - Analise Completa", "actions": []},
            "extracao": {"title": "IntegraGAL - Mapeamento da Placa", "actions": []},
            "analise": {"title": "IntegraGAL - Análise", "actions": []},
            "resultados": {"title": "IntegraGAL - Resultados", "actions": []},
            "gal": {"title": "IntegraGAL - Envio GAL", "actions": []},
            "admin": {"title": "IntegraGAL - Administração", "actions": []},
            "admin_panel": {"title": "IntegraGAL - Administração", "actions": []},
            "usuarios": {"title": "IntegraGAL - Gerenciar Usuários", "actions": []},
            "exam_creator_wizard": {"title": "IntegraGAL - Novo Exame", "actions": []},
            "tela_configuracoes": {"title": "IntegraGAL - Configurações", "actions": []},
        }
        config = module_configs.get(module_name, module_configs["main"])

        if hasattr(self.main_window, "title"):
            self.main_window.title(config["title"])

        for action in config["actions"]:
            try:
                action()
            except Exception as exc:
                registrar_log(
                    "Navegação",
                    f"Erro ao executar ação do módulo '{module_name}': {exc}",
                    "ERROR",
                )

    def go_back(self) -> bool:
        try:
            if len(self.navigation_history) > 1:
                self.navigation_history.pop()
                previous_nav = self.navigation_history[-1]
                target_module = previous_nav["from"]
                if target_module:
                    self.navigate_to(target_module)
                    return True
        except Exception as exc:
            registrar_log("Navegação", f"Erro ao voltar no histórico: {exc}", "ERROR")
        return False

    def get_current_module(self) -> Optional[str]:
        return self.current_module

    def get_navigation_history(self) -> list:
        return self.navigation_history.copy()

    def clear_history(self):
        self.navigation_history.clear()
        registrar_log("Navegação", "Histórico de navegações limpo", "INFO")

    def get_module_info(self, module_name: str) -> dict:
        info = {
            "name": module_name,
            "current": self.current_module == module_name,
            "has_saved_state": module_name in self.module_states,
            "navigation_count": len(
                [item for item in self.navigation_history if item["to"] == module_name]
            ),
        }
        if module_name in self.module_states:
            info["last_access"] = self.module_states[module_name]["timestamp"]
        return info
