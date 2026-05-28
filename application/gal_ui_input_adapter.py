# -*- coding: utf-8 -*-
"""Adapter de montagem/validacao de entrada da UI para envio GAL (U3)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Optional

from application.gal_send_use_case import GalSendRequest

_DEFAULT_TRANSITION_UNTIL = date(2026, 5, 4)  # minimo de 2 meses a partir de 2026-03-04
_ENV_TRANSITION_UNTIL = "GAL_UI_INPUT_ADAPTER_LEGACY_UNTIL"


@dataclass(frozen=True)
class GalUIInputState:
    """Estado bruto coletado da UI para iniciar o envio GAL."""

    processing: bool
    csv_path: str
    usuario: str
    senha: str
    usuario_logado: str
    usuario_nivel: str
    observacao: str
    relatorio_filename: str
    corrida_id: str = ""
    exame_id: str = ""
    lote: str = ""
    data_exame: str = ""
    arquivo_corrida: str = ""
    arquivo_extracao: str = ""
    parte_placa: int = 0
    numero_extracao: str = ""
    nome_corrida: str = ""
    quem_fez_extracao: str = ""
    quem_preparou_placa: str = ""
    observacoes_corrida: str = ""


@dataclass(frozen=True)
class GalUIValidationIssue:
    """Problema de validacao da entrada da UI."""

    severity: str
    title: str
    message: str


class GalUIInputAdapter:
    """Centraliza validacao e montagem de request da UI para o use case."""

    def __init__(self, logger_callback: Optional[Callable[[str, str], None]] = None) -> None:
        self._logger_callback = logger_callback
        self._transition_until = self._load_transition_until()

    def validate_for_start(self, state: GalUIInputState) -> Optional[GalUIValidationIssue]:
        if state.processing:
            return GalUIValidationIssue(
                severity="info",
                title="Processamento em Andamento",
                message="Ja existe um envio em andamento. Aguarde a conclusao.",
            )

        if not state.csv_path or not os.path.isfile(state.csv_path):
            return GalUIValidationIssue(
                severity="warning",
                title="Arquivo CSV",
                message="Selecione um arquivo CSV valido antes de iniciar.",
            )

        if not state.usuario or not state.senha:
            return GalUIValidationIssue(
                severity="warning",
                title="Credenciais",
                message="Informe usuario e senha do GAL para iniciar o processamento.",
            )

        return None

    def build_request(self, state: GalUIInputState) -> GalSendRequest:
        relatorio_filename = state.relatorio_filename.strip()
        if not relatorio_filename:
            relatorio_filename = f"relatorio_envio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        elif not relatorio_filename.lower().endswith(".txt"):
            relatorio_filename = f"{relatorio_filename}.txt"

        observacao = state.observacao.strip() or "Nenhuma observacao."

        return GalSendRequest(
            csv_path=state.csv_path.strip(),
            usuario=state.usuario.strip(),
            senha=state.senha.strip(),
            usuario_logado=state.usuario_logado.strip(),
            observacao=observacao,
            relatorio_filename=relatorio_filename,
            usuario_nivel=state.usuario_nivel.strip(),
            corrida_id=state.corrida_id.strip(),
            exame_id=state.exame_id.strip(),
            lote=state.lote.strip(),
            data_exame=state.data_exame.strip(),
            arquivo_corrida=state.arquivo_corrida.strip(),
            arquivo_extracao=state.arquivo_extracao.strip(),
            parte_placa=int(state.parte_placa or 0),
            numero_extracao=state.numero_extracao.strip(),
            nome_corrida=state.nome_corrida.strip(),
            quem_fez_extracao=state.quem_fez_extracao.strip(),
            quem_preparou_placa=state.quem_preparou_placa.strip(),
            observacoes_corrida=state.observacoes_corrida.strip(),
        )

    def is_legacy_transition_active(self, today: Optional[date] = None) -> bool:
        now = today or date.today()
        return now <= self._transition_until

    def log_transition_fallback(self, reason: str) -> None:
        if self._logger_callback is None:
            return
        self._logger_callback(
            f"Fallback legado de entrada GAL acionado durante janela de transicao ({self._transition_until.isoformat()}): {reason}",
            "warning",
        )

    @staticmethod
    def _load_transition_until() -> date:
        raw = (os.getenv(_ENV_TRANSITION_UNTIL) or "").strip()
        if not raw:
            return _DEFAULT_TRANSITION_UNTIL
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            return _DEFAULT_TRANSITION_UNTIL
