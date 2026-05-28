# -*- coding: utf-8 -*-
"""Adapter tkinter para FileChooserPort — isola filedialog da lógica pura."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog
from typing import Optional


class TkFileChooser:
    """Implementa FileChooserPort usando tkinter.filedialog."""

    def escolher_arquivo(
        self,
        filtros: list[tuple[str, str]],
        titulo: str = "",
    ) -> Optional[Path]:
        raw = filedialog.askopenfilename(
            title=titulo,
            filetypes=filtros,
        )
        if not raw:
            return None
        return Path(raw)
