# -*- coding: utf-8 -*-
"""Contrato base para artefato de corrida completa (Fase 0)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping

from services.shared_text import safe_str as _shared_safe_str

SCHEMA_VERSION_FULL_RUN = "1.0.0"

STATUS_CONTROLE = "controle"
STATUS_NAO_SELECIONADA = "nao_selecionada"
STATUS_SELECIONADA_PARA_ENVIO = "selecionada_para_envio"
STATUS_SELECIONADA_ENVIADA = "selecionada_enviada"
STATUS_SELECIONADA_FALHA = "selecionada_falha"
STATUS_SELECIONADA_DUPLICADA = "selecionada_duplicada"


def _safe_str(value: object) -> str:
    return _shared_safe_str(value)


def _to_ascii_token(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    token = re.sub(r"[^A-Za-z0-9]+", "_", ascii_only).strip("_")
    return token.upper() or "COLUNA"


def normalize_source_column_name(column: object) -> str:
    """Normaliza nome de coluna da UI para formato estavel de persistencia."""
    return _to_ascii_token(_safe_str(column))


def is_control_code(codigo: object) -> bool:
    """Detecta controles operacionais por codigo da linha."""
    code = _safe_str(codigo).lower()
    if not code:
        return False
    return ("cp" in code) or ("cn" in code)


def classify_sample_status(
    *,
    codigo: object,
    selecionado: bool,
    envio_status: object = "",
) -> str:
    """
    Classifica status operacional da linha da corrida.

    Prioridade:
    1) controle
    2) status de envio informado
    3) selecao de envio
    """
    if is_control_code(codigo):
        return STATUS_CONTROLE

    send = _safe_str(envio_status).lower()
    if send in {"sucesso", "enviado", "ok"}:
        return STATUS_SELECIONADA_ENVIADA
    if send in {"falha", "erro", "error"}:
        return STATUS_SELECIONADA_FALHA
    if send in {"duplicado", "duplicate"}:
        return STATUS_SELECIONADA_DUPLICADA
    if bool(selecionado):
        return STATUS_SELECIONADA_PARA_ENVIO
    return STATUS_NAO_SELECIONADA


@dataclass(frozen=True)
class FullRunMetadata:
    corrida_id: str
    exame: str
    lote: str
    data_exame: str
    usuario: str
    timestamp_execucao: str
    arquivo_corrida: str
    nome_corrida: str = ""
    quem_fez_extracao: str = ""
    quem_preparou_placa: str = ""
    observacoes: str = ""
    schema_version: str = SCHEMA_VERSION_FULL_RUN


def build_full_run_metadata(
    *,
    exame: object,
    lote: object,
    data_exame: object,
    usuario: object,
    arquivo_corrida: object,
    corrida_id: object = "",
    nome_corrida: object = "",
    quem_fez_extracao: object = "",
    quem_preparou_placa: object = "",
    observacoes: object = "",
    timestamp_execucao: object = "",
) -> FullRunMetadata:
    """Monta metadados canonicos da corrida completa."""
    exame_txt = _safe_str(exame)
    lote_txt = _safe_str(lote)
    data_txt = _safe_str(data_exame)
    user_txt = _safe_str(usuario)
    file_name = Path(_safe_str(arquivo_corrida)).name

    corrida_txt = _safe_str(corrida_id)
    if not corrida_txt:
        corrida_txt = f"{exame_txt}|{lote_txt}|{data_txt}|{file_name}".strip("|")

    ts = _safe_str(timestamp_execucao) or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return FullRunMetadata(
        corrida_id=corrida_txt,
        exame=exame_txt,
        lote=lote_txt,
        data_exame=data_txt,
        usuario=user_txt,
        timestamp_execucao=ts,
        arquivo_corrida=file_name,
        nome_corrida=_safe_str(nome_corrida),
        quem_fez_extracao=_safe_str(quem_fez_extracao),
        quem_preparou_placa=_safe_str(quem_preparou_placa),
        observacoes=_safe_str(observacoes),
    )


def build_full_run_row(
    *,
    source_row: Mapping[str, Any],
    metadata: FullRunMetadata,
    status_amostra_corrida: str,
    source_prefix: str = "SRC_",
) -> Dict[str, str]:
    """Monta linha normalizada da corrida completa para persistencia."""
    payload: Dict[str, str] = {
        "schema_version": metadata.schema_version,
        "corrida_id": metadata.corrida_id,
        "exame": metadata.exame,
        "lote": metadata.lote,
        "data_exame": metadata.data_exame,
        "usuario": metadata.usuario,
        "timestamp_execucao": metadata.timestamp_execucao,
        "arquivo_corrida": metadata.arquivo_corrida,
        "nome_corrida": metadata.nome_corrida,
        "quem_fez_extracao": metadata.quem_fez_extracao,
        "quem_preparou_placa": metadata.quem_preparou_placa,
        "observacoes": metadata.observacoes,
        "status_amostra_corrida": _safe_str(status_amostra_corrida),
    }

    seen: Dict[str, int] = {}
    for raw_key, raw_value in source_row.items():
        src_col = f"{source_prefix}{normalize_source_column_name(raw_key)}"
        if src_col in seen:
            seen[src_col] += 1
            src_col = f"{src_col}_{seen[src_col]}"
        else:
            seen[src_col] = 1
        payload[src_col] = _safe_str(raw_value)
    return payload
