"""
Host de módulos para navegação single-window.

Permite renderizar páginas por chave, mantendo cache opcional
e isolando a lógica de troca de conteúdo da janela principal.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

import customtkinter as ctk


ModuleFactory = Callable[[ctk.CTkFrame], ctk.CTkFrame]


class ModuleHost:
    """Gerencia o conteúdo central da janela principal."""

    def __init__(self, parent: ctk.CTkFrame, *, keep_cache: bool = True) -> None:
        self.parent = parent
        self.keep_cache = keep_cache
        self._active_key: Optional[str] = None
        self._active_widget: Optional[ctk.CTkFrame] = None
        self._widgets: Dict[str, ctk.CTkFrame] = {}

    @property
    def active_key(self) -> Optional[str]:
        return self._active_key

    def show_module(self, key: str, factory: ModuleFactory) -> ctk.CTkFrame:
        """
        Exibe um módulo no host.

        Args:
            key: Identificador lógico da página.
            factory: Função que constrói o widget quando necessário.
        """
        if self._active_key == key and self._active_widget is not None:
            return self._active_widget

        if self._active_widget is not None:
            self._active_widget.pack_forget()

        widget = self._widgets.get(key)
        if widget is None or not bool(widget.winfo_exists()):
            widget = factory(self.parent)
            if self.keep_cache:
                self._widgets[key] = widget

        widget.pack(expand=True, fill="both")
        self._active_key = key
        self._active_widget = widget
        return widget

    def remove_module(self, key: str) -> None:
        """
        Remove um módulo específico do cache e o destrói.
        Usado para recriar abas purgadas (ex: Nova Análise).
        """
        widget = self._widgets.pop(key, None)
        if widget:
            try:
                if self._active_widget == widget:
                    self._active_widget = None
                    self._active_key = None
                widget.pack_forget()
                widget.destroy()
            except Exception:
                pass

    def clear(self) -> None:
        """Remove widgets ativos e cacheados."""
        if self._active_widget is not None:
            try:
                self._active_widget.pack_forget()
            except Exception:
                pass
        for widget in list(self._widgets.values()):
            try:
                widget.destroy()
            except Exception:
                pass
        self._widgets.clear()
        self._active_widget = None
        self._active_key = None

