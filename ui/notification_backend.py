# -*- coding: utf-8 -*-
"""Backend de notificacao da camada UI para ErrorHandler."""

from __future__ import annotations

from tkinter import messagebox
from typing import Any, Callable, Optional

from utils.error_handler import ErrorHandler


class UINotificationBackend:
    """Backend com parent opcional para dialogs da UI."""

    def __init__(self, parent_getter: Optional[Callable[[], Any]] = None) -> None:
        self._parent_getter = parent_getter

    def _resolve_parent(self) -> Any:
        if self._parent_getter is None:
            return None
        try:
            parent = self._parent_getter()
            if parent is None:
                return None
            if hasattr(parent, "winfo_exists") and bool(parent.winfo_exists()):
                return parent
        except Exception:
            return None
        return None

    def show_error(self, title: str, message: str) -> None:
        parent = self._resolve_parent()
        if parent is not None:
            messagebox.showerror(title, message, parent=parent)
            return
        messagebox.showerror(title, message)

    def show_warning(self, title: str, message: str) -> None:
        parent = self._resolve_parent()
        if parent is not None:
            messagebox.showwarning(title, message, parent=parent)
            return
        messagebox.showwarning(title, message)

    def show_info(self, title: str, message: str) -> None:
        parent = self._resolve_parent()
        if parent is not None:
            messagebox.showinfo(title, message, parent=parent)
            return
        messagebox.showinfo(title, message)


def configure_error_handler_for_ui(parent_getter: Callable[[], Any]) -> None:
    """Vincula ErrorHandler a backend de UI."""

    ErrorHandler.set_notification_backend(UINotificationBackend(parent_getter))


def reset_error_handler_backend() -> None:
    """Restaura backend padrao apos fechamento de janela principal."""

    ErrorHandler.reset_notification_backend()
