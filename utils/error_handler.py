"""Centralized error handling with pluggable notification backend."""

from __future__ import annotations

import functools
import traceback
from dataclasses import dataclass
from tkinter import messagebox
from typing import Any, Callable, Optional, Protocol

from utils.text_normalizer import repair_mojibake_text


class NotificationBackend(Protocol):
    """Backend contract for user-facing notifications."""

    def show_error(self, title: str, message: str) -> None: ...

    def show_warning(self, title: str, message: str) -> None: ...

    def show_info(self, title: str, message: str) -> None: ...


@dataclass
class MessageBoxNotificationBackend:
    """Tkinter messagebox backend."""

    def show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message)

    def show_warning(self, title: str, message: str) -> None:
        messagebox.showwarning(title, message)

    def show_info(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message)


@dataclass
class ConsoleNotificationBackend:
    """Console fallback backend."""

    def show_error(self, title: str, message: str) -> None:
        print(f"[ERRO] {title}: {message}")

    def show_warning(self, title: str, message: str) -> None:
        print(f"[AVISO] {title}: {message}")

    def show_info(self, title: str, message: str) -> None:
        print(f"[INFO] {title}: {message}")


class ErrorHandler:
    """Classe centralizada para tratamento de erros."""

    GUI_ENABLED = True

    _gui_backend: NotificationBackend = MessageBoxNotificationBackend()
    _console_backend: NotificationBackend = ConsoleNotificationBackend()
    _notification_backend: NotificationBackend = _gui_backend
    _custom_backend_enabled: bool = False

    ERROR_MESSAGES = {
        FileNotFoundError: {
            "title": "Arquivo Nao Encontrado",
            "message": "O arquivo especificado nao foi encontrado.",
            "suggestion": "Verifique se o arquivo existe e se o caminho esta correto.",
        },
        PermissionError: {
            "title": "Sem Permissao",
            "message": "Voce nao tem permissao para acessar este recurso.",
            "suggestion": "Verifique as permissoes ou execute como administrador.",
        },
        IOError: {
            "title": "Erro de Entrada/Saida",
            "message": "Erro ao ler ou escrever arquivo.",
            "suggestion": "Verifique espaco em disco e se o arquivo nao esta em uso.",
        },
        ValueError: {
            "title": "Valor Invalido",
            "message": "Um valor invalido foi fornecido.",
            "suggestion": "Verifique os dados inseridos e tente novamente.",
        },
        KeyError: {
            "title": "Chave Nao Encontrada",
            "message": "Um campo esperado nao foi encontrado nos dados.",
            "suggestion": "Verifique se o arquivo possui todos os campos necessarios.",
        },
        AttributeError: {
            "title": "Atributo Nao Encontrado",
            "message": "Um atributo necessario nao existe.",
            "suggestion": "Pode ser problema de compatibilidade. Reporte ao suporte.",
        },
        TypeError: {
            "title": "Tipo Invalido",
            "message": "Um dado possui tipo incorreto.",
            "suggestion": "Verifique o formato dos dados fornecidos.",
        },
        Exception: {
            "title": "Erro Inesperado",
            "message": "Ocorreu um erro inesperado.",
            "suggestion": "Tente novamente. Se persistir, reporte ao suporte.",
        },
    }

    @staticmethod
    def set_gui_mode(enabled: bool) -> None:
        """Habilita/desabilita dialogs graficos (modo legado)."""

        ErrorHandler.GUI_ENABLED = enabled
        if not ErrorHandler._custom_backend_enabled:
            ErrorHandler._notification_backend = (
                ErrorHandler._gui_backend if enabled else ErrorHandler._console_backend
            )

    @staticmethod
    def set_notification_backend(backend: NotificationBackend) -> None:
        """Permite injetar backend por camada (U5)."""

        ErrorHandler._notification_backend = backend
        ErrorHandler._custom_backend_enabled = True

    @staticmethod
    def reset_notification_backend() -> None:
        """Restaura backend padrao respeitando GUI_ENABLED."""

        ErrorHandler._custom_backend_enabled = False
        ErrorHandler._notification_backend = (
            ErrorHandler._gui_backend if ErrorHandler.GUI_ENABLED else ErrorHandler._console_backend
        )

    @staticmethod
    def get_friendly_message(exception: Exception) -> dict:
        """Converte excecao em mensagem amigavel."""

        for error_type, msg_data in ErrorHandler.ERROR_MESSAGES.items():
            if isinstance(exception, error_type):
                return msg_data.copy()
        return ErrorHandler.ERROR_MESSAGES[Exception].copy()

    @staticmethod
    def _notify(kind: str, title: str, message: str) -> None:
        title_clean = repair_mojibake_text(title or "")
        message_clean = repair_mojibake_text(message or "")
        backend = ErrorHandler._notification_backend
        try:
            if kind == "error":
                backend.show_error(title_clean, message_clean)
            elif kind == "warning":
                backend.show_warning(title_clean, message_clean)
            else:
                backend.show_info(title_clean, message_clean)
        except Exception:
            # Fallback duro para console em caso de falha no backend atual.
            if kind == "error":
                ErrorHandler._console_backend.show_error(title_clean, message_clean)
            elif kind == "warning":
                ErrorHandler._console_backend.show_warning(title_clean, message_clean)
            else:
                ErrorHandler._console_backend.show_info(title_clean, message_clean)

    @staticmethod
    def show_error(
        title: str = None,
        message: str = None,
        details: str = None,
        suggestion: str = None,
        exception: Exception = None,
    ) -> None:
        if exception and (not title or not message):
            friendly = ErrorHandler.get_friendly_message(exception)
            title = title or friendly["title"]
            message = message or friendly["message"]
            suggestion = suggestion or friendly["suggestion"]
            if not details and getattr(exception, "args", None):
                details = str(exception.args[0])

        full_message = message or "Erro inesperado."
        if suggestion:
            full_message += f"\n\nSugestao:\n{suggestion}"
        if details:
            full_message += f"\n\nDetalhes:\n{details}"

        ErrorHandler._notify("error", title or "Erro", full_message)

    @staticmethod
    def show_warning(title: str, message: str, suggestion: str = None) -> None:
        full_message = message
        if suggestion:
            full_message += f"\n\nSugestao:\n{suggestion}"
        ErrorHandler._notify("warning", title, full_message)

    @staticmethod
    def show_info(title: str, message: str) -> None:
        ErrorHandler._notify("info", title, message)

    @staticmethod
    def log_exception(exception: Exception, context: str = "") -> None:
        error_msg = f"ERRO{' em ' + context if context else ''}: {type(exception).__name__}: {exception}"
        print(error_msg)
        print("Traceback:")
        traceback.print_exc()

    @staticmethod
    def handle_exception(
        exception: Exception,
        context: str = "",
        show_dialog: bool = True,
        re_raise: bool = False,
    ) -> None:
        ErrorHandler.log_exception(exception, context)
        if show_dialog:
            ErrorHandler.show_error(exception=exception)
        if re_raise:
            raise exception


def safe_operation(
    fallback_value: Any = None,
    fallback_msg: str = None,
    show_error: bool = True,
    context: str = None,
):
    """Decorator para operacoes seguras com tratamento de erro automatico."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                op_context = context or func.__name__
                ErrorHandler.log_exception(exc, op_context)
                if show_error:
                    if fallback_msg:
                        ErrorHandler.show_error(title="Erro", message=fallback_msg, exception=exc)
                    else:
                        ErrorHandler.show_error(exception=exc)
                return fallback_value

        return wrapper

    return decorator


class ErrorContext:
    """Context manager para tratamento de erros."""

    def __init__(
        self,
        context: str,
        show_error: bool = True,
        re_raise: bool = False,
    ) -> None:
        self.context = context
        self.show_error = show_error
        self.re_raise = re_raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is not None:
            ErrorHandler.handle_exception(
                exc_value,
                context=self.context,
                show_dialog=self.show_error,
                re_raise=self.re_raise,
            )
            return not self.re_raise
        return True


def show_error(message: str, title: str = "Erro", suggestion: str = None):
    """Atalho para mostrar erro simples."""
    ErrorHandler.show_error(title=title, message=message, suggestion=suggestion)


def show_warning(message: str, title: str = "Aviso", suggestion: str = None):
    """Atalho para mostrar aviso."""
    ErrorHandler.show_warning(title=title, message=message, suggestion=suggestion)


def show_info(message: str, title: str = "Informacao"):
    """Atalho para mostrar informacao."""
    ErrorHandler.show_info(title=title, message=message)
