# -*- coding: utf-8 -*-
"""Utilitarios de autorizacao para use cases/servicos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Set


PRIVILEGED_LEVELS: Set[str] = {"ADMIN", "MASTER"}
OPERATION_ALLOWED_LEVELS = {
    "gal.send": {"ADMIN", "MASTER", "DIAGNOSTICO"},
    "history.gal.read": {"ADMIN", "MASTER", "DIAGNOSTICO"},
    "history.gal.write": {"ADMIN", "MASTER", "DIAGNOSTICO"},
    "users.mutate": {"ADMIN", "MASTER"},
    "users.sync_legacy": {"ADMIN", "MASTER"},
    "admin.catalog.write": {"ADMIN", "MASTER"},
    "admin.registry.write": {"ADMIN", "MASTER"},
}


@dataclass(frozen=True)
class AuthorizationDeniedError(PermissionError):
    """Erro funcional padronizado para negacao de autorizacao por operacao."""

    operation: str
    access_level: str
    actor_username: str = ""

    def __str__(self) -> str:
        actor_part = f"usuario='{self.actor_username}', " if self.actor_username else ""
        return (
            "Acesso negado para operacao "
            f"'{self.operation}' ({actor_part}nivel='{self.access_level or 'DESCONHECIDO'}')."
        )


def normalize_access_level(value: object) -> str:
    """Normaliza nivel de acesso textual para comparacao."""
    return str(value or "").strip().upper()


def has_required_access(
    access_level: object,
    *,
    allowed_levels: Iterable[str],
) -> bool:
    """Retorna True quando o nivel informado pertence ao conjunto permitido."""
    normalized = normalize_access_level(access_level)
    allowed = {normalize_access_level(level) for level in allowed_levels}
    return bool(normalized) and normalized in allowed


def is_privileged(access_level: object) -> bool:
    """Retorna True para perfis administrativos (ADMIN/MASTER)."""
    return has_required_access(access_level, allowed_levels=PRIVILEGED_LEVELS)


def allowed_levels_for_operation(operation: str) -> Set[str]:
    """Retorna niveis permitidos por operacao, com fallback vazio."""
    return set(OPERATION_ALLOWED_LEVELS.get(str(operation or "").strip(), set()))


def can_execute_operation(operation: str, access_level: object) -> bool:
    """Valida autorizacao por matriz de operacao."""
    allowed = allowed_levels_for_operation(operation)
    if not allowed:
        return False
    return has_required_access(access_level, allowed_levels=allowed)


def ensure_operation_allowed(
    operation: str,
    access_level: object,
    *,
    actor_username: Optional[str] = None,
) -> None:
    """Lanca erro padronizado quando a operacao nao for permitida."""
    level = normalize_access_level(access_level)
    if can_execute_operation(operation, level):
        return
    raise AuthorizationDeniedError(
        operation=str(operation or "").strip(),
        access_level=level,
        actor_username=str(actor_username or "").strip(),
    )
