# -*- coding: utf-8 -*-
"""Contrato para seleção de arquivo pelo usuário (sem dependência de UI)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class FileChooserPort(Protocol):
    """Porta para abrir diálogo de seleção de arquivo."""

    def escolher_arquivo(
        self,
        filtros: list[tuple[str, str]],
        titulo: str = "",
    ) -> Optional[Path]:
        """Solicita ao usuário a escolha de um arquivo.

        Args:
            filtros: Lista de (descrição, padrão), ex. [("Excel", "*.xlsx")].
            titulo: Título opcional do diálogo.

        Returns:
            Path do arquivo escolhido ou None se cancelado.
        """
