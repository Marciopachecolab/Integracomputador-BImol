"""Helpers para retorno padronizado de erros em servicos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class ServiceError:
    """Representa erro funcional/operacional em formato contratual."""

    code: str
    message: str
    source: str

    def to_dict(self, **extra: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "sucesso": False,
            "erro": self.message,
            "erro_codigo": self.code,
            "erro_origem": self.source,
        }
        payload.update(extra)
        return payload


def build_error_result(
    *,
    code: str,
    message: str,
    source: str,
    **extra: Any,
) -> Dict[str, Any]:
    """Atalho para montar payload de erro padronizado."""
    return ServiceError(code=code, message=message, source=source).to_dict(**extra)
