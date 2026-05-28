# -*- coding: utf-8 -*-
"""Use case puro de extração de planilha — sem dependência de tkinter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from application.file_chooser_port import FileChooserPort
from utils.extraction_helpers import _extrair_numero_extracao

_FILTROS_XLSX = [("Excel files", "*.xlsx")]
_TITULO_DIALOGO = "Selecione a planilha de extração"


@dataclass
class ExtractionFileResult:
    """DTO com o arquivo escolhido e o parse inicial da planilha."""

    caminho_arquivo: Path
    numero_extracao: Optional[str]
    df_bloco: pd.DataFrame


class ExtractionUseCase:
    """Orquestra escolha de arquivo e parse inicial sem dependência de UI."""

    def __init__(self, file_chooser: FileChooserPort) -> None:
        self._chooser = file_chooser

    def executar(self) -> Optional[ExtractionFileResult]:
        path = self._chooser.escolher_arquivo(
            filtros=_FILTROS_XLSX,
            titulo=_TITULO_DIALOGO,
        )
        if path is None:
            return None
        return self._parse_arquivo(path)

    def _parse_arquivo(self, path: Path) -> ExtractionFileResult:
        numero_extracao = _extrair_numero_extracao(str(path))
        df_bloco = pd.read_excel(
            path,
            sheet_name="PLANILHA EXTRAÇÃO",
            usecols="B:M",
            skiprows=9,
            nrows=8,
            header=None,
        )
        return ExtractionFileResult(
            caminho_arquivo=path,
            numero_extracao=numero_extracao,
            df_bloco=df_bloco,
        )
