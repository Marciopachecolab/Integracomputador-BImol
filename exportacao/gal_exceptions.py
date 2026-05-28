# -*- coding: utf-8 -*-
"""Excecoes tipadas para integracao GAL."""

from __future__ import annotations

from domain.error_codes import ErrorCode


class GalIntegrationError(RuntimeError):
    """Erro base de integracao GAL."""

    error_code = ErrorCode.GAL_INTEGRATION_ERROR

    def __init__(self, message: str = "") -> None:
        super().__init__(message)


class GalLoginError(GalIntegrationError):
    """Falha durante autenticacao no GAL."""

    error_code = ErrorCode.GAL_LOGIN_ERROR


class GalLoginElementNotFound(GalLoginError):
    """Elemento critico da tela de login nao encontrado."""

    error_code = ErrorCode.GAL_LOGIN_ELEMENT_NOT_FOUND


class GalLoginNotConfirmed(GalLoginError):
    """Login executado, mas sem confirmacao de sessao autenticada."""

    error_code = ErrorCode.GAL_LOGIN_NOT_CONFIRMED


class GalPayloadValidationError(GalIntegrationError):
    """Payload de envio GAL invalido para o contrato operacional."""

    error_code = ErrorCode.GAL_PAYLOAD_INVALID
