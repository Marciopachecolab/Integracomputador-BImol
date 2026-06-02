# -*- coding: utf-8 -*-
"""Reconcilia status GAL de amostras a partir do journal de transacoes."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from services.persistence.csv_contracts import get_csv_contract
from services.gal.gal_transactions import build_idempotency_key, normalize_idempotency_value
from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, open_with_retry, path_exists_with_retry

_JOURNAL_CONTRACT = get_csv_contract("gal_transacoes.csv")
_DELIMITER = _JOURNAL_CONTRACT.delimiter if _JOURNAL_CONTRACT else ";"
_ENCODING = _JOURNAL_CONTRACT.encoding if _JOURNAL_CONTRACT else "utf-8"

_STATUS_MAP: dict[str, str] = {
    "sucesso": "enviado",
    "sucesso_legacy": "enviado",
    "enviado": "enviado",
    "erro": "erro",
    "duplicado": "duplicado",
    "nao_encontrado": "erro",
}

# Converte DD/MM/YYYY → YYYY-MM-DD dentro de chaves pipe-delimitadas do journal
_DATE_DDMMYYYY = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")


def _normalize_key_dates(key: str) -> str:
    return _DATE_DDMMYYYY.sub(lambda m: f"{m.group(3)}-{m.group(2)}-{m.group(1)}", key)


def _load_journal_status_by_key(journal_path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Carrega journal GAL e retorna dois dicts:
    - key_to_status:    chave_idempotencia → ultimo_status
    - codigo_to_status: codigo_amostra     → ultimo_status (fallback quando kit/lote ausentes)
    """
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(journal_path, policy=policy):
        return {}, {}

    key_to_status: dict[str, str] = {}
    codigo_to_status: dict[str, str] = {}
    with CSVFileLock(journal_path):
        with open_with_retry(
            journal_path,
            "r",
            encoding=_ENCODING,
            newline="",
            policy=policy,
        ) as handle:
            reader = csv.DictReader(handle, delimiter=_DELIMITER)
            for row in reader:
                key = _normalize_key_dates(
                    normalize_idempotency_value(row.get("idempotencia_chave", ""))
                )
                status = normalize_idempotency_value(row.get("status", ""))
                codigo = normalize_idempotency_value(row.get("codigo_amostra", ""))
                if key and status:
                    key_to_status[key] = status
                # Fallback por codigo_amostra — o ultimo registro vence (journal é append-only)
                if codigo and status:
                    codigo_to_status[codigo] = status
    return key_to_status, codigo_to_status


def _build_key_from_row(row: dict[str, Any]) -> str | None:
    """Constroi chave de idempotencia GAL a partir de uma linha de exam_run.

    Retorna None quando kit e lote sao ambos vazios (sem_chave_gal).
    """
    kit = str(row.get("kit") or "")
    lote_kit = str(row.get("lote_kit") or row.get("lote") or "")
    if not kit and not lote_kit:
        return None

    codigo = row.get("codigo_amostra") or row.get("amostra_codigo") or ""
    raw_key = build_idempotency_key(
        codigo_amostra=codigo,
        kit=kit,
        lote_kit=lote_kit,
        data_exame=row.get("data_exame") or "",
    )
    # S23: Aplicar mesma normalização de data que _load_journal_status_by_key
    # usa ao ler o journal (DD/MM/YYYY → YYYY-MM-DD). Sem isso, amostras com
    # data em formato DD/MM não encontram correspondência no journal e voltam
    # como 'nao_enviado' mesmo quando já foram enviadas com sucesso.
    return _normalize_key_dates(raw_key)


def reconcile_gal_status(
    rows: list[dict[str, Any]],
    journal_path: Path,
) -> dict[str, str]:
    """Reconcilia status GAL para cada amostra a partir do journal de transacoes.

    Retorna dict de codigo_amostra -> status_gal.
    Valores possiveis: enviado, nao_enviado, erro, duplicado, sem_chave_gal.

    Quando kit/lote estao ausentes na linha (chave nao construivel), usa fallback
    por codigo_amostra direto no journal — evita 'sem_chave_gal' quando o envio
    foi bem-sucedido mas os metadados de lote nao foram gravados no historico.db.
    """
    journal, codigo_fallback = _load_journal_status_by_key(journal_path)
    result: dict[str, str] = {}

    for row in rows:
        codigo = str(row.get("codigo_amostra") or row.get("amostra_codigo") or "")
        key = _build_key_from_row(row)

        if key is None:
            # kit/lote ausentes: tenta fallback por codigo_amostra
            fb_status = codigo_fallback.get(normalize_idempotency_value(codigo))
            if fb_status:
                result[codigo] = _STATUS_MAP.get(fb_status, "nao_enviado")
            else:
                result[codigo] = "sem_chave_gal"
            continue

        journal_status = journal.get(key)
        if journal_status is None:
            result[codigo] = "nao_enviado"
        else:
            result[codigo] = _STATUS_MAP.get(journal_status, "nao_enviado")

    return result
