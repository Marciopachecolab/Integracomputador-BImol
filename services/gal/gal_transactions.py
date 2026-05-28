# -*- coding: utf-8 -*-
"""Persistencia de transacoes GAL (sucesso + trilha unificada + idempotencia)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from services.core.config_service import config_service
from services.persistence.csv_contracts import get_csv_contract
from utils.csv_lock import CSVFileLock
from utils.csv_safety import sanitize_csv_value
from utils.network_io import RetryPolicy, open_with_retry, path_exists_with_retry

TRANSACTION_HEADERS: List[str] = [
    "run_id",
    "codigo_amostra",
    "transaction_id",
    "ts_sucesso",
    "status",
]

TRANSACTION_JOURNAL_HEADERS: List[str] = [
    "idempotencia_chave",
    "run_id",
    "codigo_amostra",
    "kit",
    "lote_kit",
    "data_exame",
    "status",
    "transaction_id",
    "ts_evento",
    "erro",
    "detalhes",
]

_GAL_TX_SUCCESS_CONTRACT = get_csv_contract("gal_transacoes_sucesso.csv")
_GAL_TX_SUCCESS_DELIMITER = (
    _GAL_TX_SUCCESS_CONTRACT.delimiter if _GAL_TX_SUCCESS_CONTRACT else ";"
)
_GAL_TX_SUCCESS_ENCODING = (
    _GAL_TX_SUCCESS_CONTRACT.encoding if _GAL_TX_SUCCESS_CONTRACT else "utf-8"
)

_GAL_TX_JOURNAL_CONTRACT = get_csv_contract("gal_transacoes.csv")
_GAL_TX_JOURNAL_DELIMITER = (
    _GAL_TX_JOURNAL_CONTRACT.delimiter if _GAL_TX_JOURNAL_CONTRACT else ";"
)
_GAL_TX_JOURNAL_ENCODING = (
    _GAL_TX_JOURNAL_CONTRACT.encoding if _GAL_TX_JOURNAL_CONTRACT else "utf-8"
)


def normalize_idempotency_value(value: object) -> str:
    """Normaliza componente de chave de idempotencia."""
    return str(value or "").strip().lower()


def build_idempotency_key(
    *,
    codigo_amostra: object,
    kit: object,
    lote_kit: object,
    data_exame: object,
    corrida_id: object = "",
    nome_corrida: object = "",
    arquivo_corrida: object = "",
    placa: object = "",
    parte_placa: object = "",
) -> str:
    """
    Monta chave de idempotencia do envio GAL.

    Formato base: codigo_amostra|kit|lote_kit|data_exame (normalizado).
    Quando disponiveis, dados estaveis da corrida/placa entram como escopo
    adicional. Timestamp de envio nao entra porque mudaria a cada retentativa.
    """
    parts = [
        normalize_idempotency_value(codigo_amostra),
        normalize_idempotency_value(kit),
        normalize_idempotency_value(lote_kit),
        normalize_idempotency_value(data_exame),
    ]
    scoped_parts = []
    for label, value in (
        ("corrida", corrida_id),
        ("nome_corrida", nome_corrida),
        ("arquivo_corrida", arquivo_corrida),
        ("placa", placa),
        ("parte_placa", parte_placa),
    ):
        normalized = normalize_idempotency_value(value)
        if normalized:
            scoped_parts.append(f"{label}={normalized}")
    parts.extend(scoped_parts)
    return "|".join(parts)


def default_transaction_journal_path(log_dir: Optional[str | Path] = None) -> Path:
    """Resolve caminho padrao do journal de transacoes GAL."""
    if log_dir:
        return Path(log_dir) / "gal_transacoes.csv"
    paths = config_service.get_paths()
    base_log = Path(paths.get("log_file", "logs/sistema.log")).parent
    return base_log / "gal_transacoes.csv"


def load_successful_idempotency_keys(path: Path) -> Set[str]:
    """Le o journal e retorna chaves de idempotencia com status de sucesso."""
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(path, policy=policy):
        return set()

    keys: Set[str] = set()
    with CSVFileLock(path):
        with open_with_retry(
            path,
            "r",
            encoding=_GAL_TX_JOURNAL_ENCODING,
            newline="",
            policy=policy,
        ) as handle:
            reader = csv.DictReader(handle, delimiter=_GAL_TX_JOURNAL_DELIMITER)
            for row in reader:
                status = normalize_idempotency_value(row.get("status", ""))
                if status != "sucesso":
                    continue
                key = normalize_idempotency_value(row.get("idempotencia_chave", ""))
                if key:
                    keys.add(key)
    return keys


def build_success_transaction_rows(
    relatorio_local: Iterable[Dict[str, Any]],
    run_id: str,
) -> List[Dict[str, str]]:
    """Filtra apenas sucessos e prepara linhas para CSV legado de sucesso."""
    rows: List[Dict[str, str]] = []
    for item in relatorio_local:
        status = str(item.get("status") or "")
        if status != "sucesso":
            continue
        codigo = item.get("codigoAmostra") or item.get("registroInterno") or ""
        rows.append(
            {
                "run_id": str(run_id),
                "codigo_amostra": str(codigo),
                "transaction_id": str(item.get("transaction_id") or ""),
                "ts_sucesso": str(item.get("ts_sucesso") or ""),
                "status": status,
            }
        )
    return rows


def build_transaction_journal_rows(
    relatorio_local: Iterable[Dict[str, Any]],
    *,
    run_id: str,
    kit_default: str,
) -> List[Dict[str, str]]:
    """Monta trilha unificada de transacoes (sucesso/falha/duplicado)."""
    rows: List[Dict[str, str]] = []
    for item in relatorio_local:
        codigo = item.get("codigoAmostra") or item.get("registroInterno") or ""
        kit = str(item.get("kit") or kit_default or "")
        lote_kit = str(item.get("loteKit") or "")
        data_exame = str(item.get("dataProcessamentoFim") or item.get("data_exame") or "")
        key = str(item.get("idempotencia_chave") or "")
        if not key:
            key = build_idempotency_key(
                codigo_amostra=codigo,
                kit=kit,
                lote_kit=lote_kit,
                data_exame=data_exame,
                corrida_id=item.get("corrida_id", ""),
                nome_corrida=item.get("nome_corrida", ""),
                arquivo_corrida=item.get("arquivo_corrida", ""),
                placa=item.get("num_placa", "") or item.get("placa", ""),
                parte_placa=item.get("parte_placa", ""),
            )
        erros = item.get("erro") or []
        if isinstance(erros, list):
            erro_texto = "; ".join(str(v) for v in erros if v is not None)
        else:
            erro_texto = str(erros or "")

        rows.append(
            {
                "idempotencia_chave": key,
                "run_id": str(run_id),
                "codigo_amostra": str(codigo),
                "kit": kit,
                "lote_kit": lote_kit,
                "data_exame": data_exame,
                "status": str(item.get("status") or ""),
                "transaction_id": str(item.get("transaction_id") or ""),
                "ts_evento": str(
                    item.get("ts_status_final")
                    or item.get("ts_sucesso")
                    or item.get("timestamp")
                    or ""
                ),
                "erro": erro_texto,
                "detalhes": str(item.get("detalhes") or ""),
            }
        )
    return rows


def append_success_transactions(path: Path, rows: Iterable[Dict[str, str]]) -> None:
    """Escreve linhas no CSV legado de transacoes de sucesso (append-only)."""
    rows_list = list(rows)
    if not rows_list:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    policy = RetryPolicy.from_env()

    with CSVFileLock(path):
        file_exists = path_exists_with_retry(path, policy=policy) and path.stat().st_size > 0
        with open_with_retry(
            path, "a", encoding=_GAL_TX_SUCCESS_ENCODING, newline="", policy=policy
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=TRANSACTION_HEADERS,
                delimiter=_GAL_TX_SUCCESS_DELIMITER,
            )
            if not file_exists:
                writer.writeheader()
            for row in rows_list:
                writer.writerow(
                    {h: sanitize_csv_value(row.get(h, "")) for h in TRANSACTION_HEADERS}
                )


def append_transaction_journal(path: Path, rows: Iterable[Dict[str, str]]) -> None:
    """Escreve trilha unificada de transacoes GAL (append-only)."""
    rows_list = list(rows)
    if not rows_list:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    policy = RetryPolicy.from_env()

    with CSVFileLock(path):
        file_exists = path_exists_with_retry(path, policy=policy) and path.stat().st_size > 0
        with open_with_retry(
            path, "a", encoding=_GAL_TX_JOURNAL_ENCODING, newline="", policy=policy
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=TRANSACTION_JOURNAL_HEADERS,
                delimiter=_GAL_TX_JOURNAL_DELIMITER,
            )
            if not file_exists:
                writer.writeheader()
            for row in rows_list:
                writer.writerow(
                    {
                        h: sanitize_csv_value(row.get(h, ""))
                        for h in TRANSACTION_JOURNAL_HEADERS
                    }
                )


def append_transaction_journal_unique(path: Path, rows: Iterable[Dict[str, str]]) -> Dict[str, int]:
    """Escreve eventos no journal sem duplicar identidades ja registradas."""
    rows_list = list(rows)
    if not rows_list:
        return {"input_rows": 0, "appended_rows": 0, "skipped_duplicates": 0}

    existing = _load_journal_identity_keys(path)
    to_append: List[Dict[str, str]] = []
    skipped = 0
    for row in rows_list:
        identity = _build_journal_identity(row)
        if identity != "|||" and identity in existing:
            skipped += 1
            continue
        to_append.append(row)
        if identity != "|||":
            existing.add(identity)

    append_transaction_journal(path, to_append)
    return {
        "input_rows": len(rows_list),
        "appended_rows": len(to_append),
        "skipped_duplicates": skipped,
    }


def default_success_transactions_path(log_dir: Optional[str | Path] = None) -> Path:
    """Resolve caminho padrao do ledger legado de sucesso GAL."""
    if log_dir:
        return Path(log_dir) / "gal_transacoes_sucesso.csv"
    paths = config_service.get_paths()
    base_log = Path(paths.get("log_file", "logs/sistema.log")).parent
    return base_log / "gal_transacoes_sucesso.csv"


def _build_legacy_identity(
    *,
    run_id: object,
    codigo_amostra: object,
    transaction_id: object,
    ts_sucesso: object,
) -> str:
    """Monta chave de identidade do ledger legado para reconciliacao."""
    return "|".join(
        [
            normalize_idempotency_value(run_id),
            normalize_idempotency_value(codigo_amostra),
            normalize_idempotency_value(transaction_id),
            normalize_idempotency_value(ts_sucesso),
        ]
    )


def _build_journal_identity(row: Dict[str, object]) -> str:
    """Monta chave de identidade do journal para reconciliacao com trilha legada."""
    ts_evento = row.get("ts_evento") or row.get("ts_sucesso") or ""
    return _build_legacy_identity(
        run_id=row.get("run_id", ""),
        codigo_amostra=row.get("codigo_amostra", ""),
        transaction_id=row.get("transaction_id", ""),
        ts_sucesso=ts_evento,
    )


def _read_legacy_success_rows(path: Path) -> List[Dict[str, str]]:
    """Le linhas do ledger legado de sucesso GAL."""
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(path, policy=policy):
        return []

    rows: List[Dict[str, str]] = []
    with CSVFileLock(path):
        with open_with_retry(
            path,
            "r",
            encoding=_GAL_TX_SUCCESS_ENCODING,
            newline="",
            policy=policy,
        ) as handle:
            reader = csv.DictReader(handle, delimiter=_GAL_TX_SUCCESS_DELIMITER)
            for row in reader:
                rows.append({h: str(row.get(h, "")) for h in TRANSACTION_HEADERS})
    return rows


def _load_journal_identity_keys(path: Path) -> Set[str]:
    """Le o journal unificado e retorna identidades ja registradas."""
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(path, policy=policy):
        return set()

    keys: Set[str] = set()
    with CSVFileLock(path):
        with open_with_retry(
            path,
            "r",
            encoding=_GAL_TX_JOURNAL_ENCODING,
            newline="",
            policy=policy,
        ) as handle:
            reader = csv.DictReader(handle, delimiter=_GAL_TX_JOURNAL_DELIMITER)
            for row in reader:
                identity = _build_journal_identity(row)
                if identity != "|||":
                    keys.add(identity)
    return keys


def reconcile_legacy_success_into_journal(
    *,
    journal_path: Path,
    legacy_success_path: Path,
    kit_default: str = "",
) -> Dict[str, int]:
    """
    Reconcilia o ledger legado de sucesso no journal oficial.

    Regras:
    - nao altera linhas existentes;
    - inclui apenas ausencias do legacy no journal;
    - preserva status `sucesso_legacy` para nao interferir na idempotencia atual.
    """
    legacy_rows = _read_legacy_success_rows(legacy_success_path)
    if not legacy_rows:
        return {
            "legacy_total": 0,
            "already_in_journal": 0,
            "appended_to_journal": 0,
        }

    journal_identities = _load_journal_identity_keys(journal_path)
    already_count = 0
    rows_to_append: List[Dict[str, str]] = []

    for row in legacy_rows:
        if normalize_idempotency_value(row.get("status", "")) != "sucesso":
            continue
        identity = _build_legacy_identity(
            run_id=row.get("run_id", ""),
            codigo_amostra=row.get("codigo_amostra", ""),
            transaction_id=row.get("transaction_id", ""),
            ts_sucesso=row.get("ts_sucesso", ""),
        )
        if identity in journal_identities:
            already_count += 1
            continue

        rows_to_append.append(
            {
                "idempotencia_chave": f"legacy::{identity}",
                "run_id": str(row.get("run_id", "")),
                "codigo_amostra": str(row.get("codigo_amostra", "")),
                "kit": str(kit_default or ""),
                "lote_kit": "",
                "data_exame": "",
                "status": "sucesso_legacy",
                "transaction_id": str(row.get("transaction_id", "")),
                "ts_evento": str(row.get("ts_sucesso", "")),
                "erro": "",
                "detalhes": "reconciliado_de=gal_transacoes_sucesso.csv",
            }
        )
        journal_identities.add(identity)

    if rows_to_append:
        append_transaction_journal(journal_path, rows_to_append)

    return {
        "legacy_total": len(legacy_rows),
        "already_in_journal": already_count,
        "appended_to_journal": len(rows_to_append),
    }
