# -*- coding: utf-8 -*-
"""Sincronizacao de status pos-envio GAL entre artefatos da corrida."""

from __future__ import annotations

import csv
import os
import re
import threading
import uuid
import json
import time
import hashlib
import hmac
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import pandas as pd

from services.core.config_service import config_service
from services.persistence.csv_io import read_csv_strict, write_csv_atomic
from services.dedupe_keys import DEDUPE_FIELDS, build_dedupe_key
from services.analysis.exam_runs_row_mapper import slugify
from services.persistence.exam_runs_sqlite import ExamRunsSQLiteRepository
from services.analysis.full_run_contract import (
    STATUS_SELECIONADA_DUPLICADA,
    STATUS_SELECIONADA_ENVIADA,
    STATUS_SELECIONADA_FALHA,
)
from services.shared_io import flush_and_fsync as _shared_flush_and_fsync
from services.shared_text import safe_str_pandas_strip as _shared_safe_str_pandas_strip
from utils.csv_lock import CSVFileLock
from utils.csv_safety import sanitize_csv_value
from utils.logger import registrar_log
from utils.network_io import RetryPolicy, call_with_retry, open_with_retry, path_exists_with_retry


def _safe_str(value: object) -> str:
    return _shared_safe_str_pandas_strip(value)


def _normalize_date(value: object) -> str:
    raw = _safe_str(value)
    if not raw:
        return ""
    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
    ):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def _sanitize_filename(value: object) -> str:
    raw = _safe_str(value).lower()
    safe = re.sub(r"[^a-z0-9._-]+", "_", raw).strip("_")
    return safe or "corrida"


def _status_from_send(row: Mapping[str, Any]) -> Tuple[str, str]:
    status = _safe_str(row.get("status", "")).lower()
    if status == "sucesso":
        return STATUS_SELECIONADA_ENVIADA, "enviado"
    if status == "duplicado":
        return STATUS_SELECIONADA_DUPLICADA, "duplicado"
    return STATUS_SELECIONADA_FALHA, "falha"


def _build_error_text(value: object) -> str:
    if isinstance(value, list):
        return "; ".join(_safe_str(v) for v in value if _safe_str(v))
    return _safe_str(value)


def _build_updates(
    *,
    relatorio_local: Iterable[Mapping[str, Any]],
    context: Mapping[str, Any],
) -> Dict[tuple[str, str, str, str], Dict[str, str]]:
    updates: Dict[tuple[str, str, str, str], Dict[str, str]] = {}
    usuario_envio = _safe_str(context.get("usuario_execucao", ""))

    for row in relatorio_local:
        codigo = _safe_str(row.get("codigoAmostra") or row.get("registroInterno"))
        corrida_id = _safe_str(row.get("corrida_id") or context.get("corrida_id"))
        lote = _safe_str(row.get("lote") or context.get("lote") or row.get("loteKit"))
        data_exame = _normalize_date(
            row.get("data_exame") or context.get("data_exame") or row.get("dataProcessamentoFim")
        )
        key = build_dedupe_key(
            {
                "corrida_id": corrida_id,
                "amostra_codigo": codigo,
                "lote": lote,
                "data_exame": data_exame,
            },
            fields=DEDUPE_FIELDS,
        )
        if key is None:
            continue

        status_amostra, status_gal = _status_from_send(row)
        erro = _build_error_text(row.get("erro", ""))
        detalhes = _safe_str(row.get("detalhes", ""))
        detalhes_envio = "; ".join(part for part in (erro, detalhes) if part)
        sucesso_envio = "True" if status_amostra in {
            STATUS_SELECIONADA_ENVIADA,
            STATUS_SELECIONADA_DUPLICADA,
        } else "False"
        payload = {
            "status_amostra_corrida": status_amostra,
            "status_gal": status_gal,
            "sucesso_envio": sucesso_envio,
            "usuario_envio": usuario_envio,
            "detalhes_envio": detalhes_envio,
        }
        ts_event = _safe_str(row.get("ts_status_final") or row.get("ts_sucesso"))
        if ts_event:
            payload["data_hora_envio"] = ts_event
        updates[key] = payload
    return updates


def _row_key(row: Mapping[str, Any]) -> Optional[tuple[str, str, str, str]]:
    key = build_dedupe_key(
        {
            "corrida_id": _safe_str(row.get("corrida_id", "")),
            "amostra_codigo": _safe_str(
                row.get("amostra_codigo")
                or row.get("codigo")
                or row.get("SRC_AMOSTRA_CODIGO")
                or row.get("SRC_CODIGO")
            ),
            "lote": _safe_str(row.get("lote", "")),
            "data_exame": _normalize_date(row.get("data_exame", "")),
        },
        fields=DEDUPE_FIELDS,
    )
    return key


def contract_key_from_row(row: Mapping[str, Any]) -> Optional[tuple[str, str, str, str]]:
    """Resolve chave contratual de uma linha oriunda de qualquer artefato."""
    return _row_key(row)


_LEGACY_FALLBACK_ALLOWED_KINDS = {"erro_contratual", "erro_encoding_ou_parse"}
_TRANSIENT_ERRNO_CODES = {11, 16, 32, 110, 111}
_TRANSIENT_WINERROR_CODES = {32, 33, 64, 121}
_TRANSIENT_MESSAGE_TOKENS = (
    "temporarily unavailable",
    "resource busy",
    "sharing violation",
    "share locked",
)
_SQLITE_ASYNC_AUDIT_HEADERS = [
    "timestamp",
    "job_id",
    "status",
    "attempt",
    "rows_updated",
    "error",
    "db_path",
    "updates_count",
]
_SQLITE_ASYNC_QUEUE_HEADERS = [
    "timestamp",
    "job_id",
    "status",
    "attempt",
    "next_retry_epoch",
    "db_path",
    "updates_json",
    "last_error",
]
_SQLITE_ASYNC_QUEUE_PENDING = {"queued", "retry_scheduled"}
_SQLITE_ASYNC_QUEUE_TERMINAL = {"success", "failed"}


def _iter_exception_chain(exc: Exception, max_depth: int = 5) -> Iterable[BaseException]:
    current: BaseException | None = exc
    seen_ids: set[int] = set()
    depth = 0
    while current is not None and depth < max_depth:
        marker = id(current)
        if marker in seen_ids:
            break
        seen_ids.add(marker)
        yield current
        depth += 1
        current = current.__cause__ or current.__context__


def _classify_contract_read_error(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        return "erro_contratual"
    if isinstance(exc, PermissionError):
        return "permissao_negada"
    if isinstance(exc, (UnicodeDecodeError, pd.errors.ParserError)):
        return "erro_encoding_ou_parse"
    if isinstance(exc, FileNotFoundError):
        return "arquivo_ausente"
    return "erro_nao_mapeado"


def _is_legacy_fallback_allowed(error_kind: str) -> bool:
    return error_kind in _LEGACY_FALLBACK_ALLOWED_KINDS


def _transient_critical_error_code(exc: Exception) -> str:
    for candidate in _iter_exception_chain(exc):
        errno_code = getattr(candidate, "errno", None)
        if isinstance(errno_code, int) and errno_code in _TRANSIENT_ERRNO_CODES:
            return f"os_errno_{errno_code}"
        winerror_code = getattr(candidate, "winerror", None)
        if isinstance(winerror_code, int) and winerror_code in _TRANSIENT_WINERROR_CODES:
            return f"os_winerror_{winerror_code}"
        if isinstance(candidate, PermissionError):
            return "permission_error"
        if isinstance(candidate, TimeoutError):
            return "timeout_error"
        if isinstance(candidate, ConnectionError):
            return "connection_error"
    if str(os.getenv("INTEGRAGAL_TRANSIENT_MESSAGE_HEURISTIC", "0")).strip().lower() in {
        "1",
        "true",
        "on",
        "yes",
    }:
        text = str(exc).strip().lower()
        for token in _TRANSIENT_MESSAGE_TOKENS:
            if token in text:
                return f"message_token_{token.replace(' ', '_')}"
    return ""


def _strict_retry_attempts() -> int:
    raw = str(os.getenv("INTEGRAGAL_STRICT_READ_RETRY_ATTEMPTS", "2")).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 2


def _is_transient_critical_error(exc: Exception) -> bool:
    return bool(_transient_critical_error_code(exc))


def _read_csv_with_fallback(
    path: Path,
    *,
    delimiter: str,
    encoding: str,
    contract_name: Optional[str] = None,
) -> pd.DataFrame:
    policy = RetryPolicy.from_env()
    attempts = _strict_retry_attempts()
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return read_csv_strict(path, contract_name=contract_name, policy=policy)
        except Exception as exc:
            last_exc = exc
            error_kind = _classify_contract_read_error(exc)
            can_retry = (
                _is_transient_critical_error(exc)
                and (not _is_legacy_fallback_allowed(error_kind))
                and attempt < attempts
            )
            if can_retry:
                retry_code = _transient_critical_error_code(exc)
                registrar_log(
                    "FullRunStatusSync",
                    (
                        f"Retry leitura contratual para '{path.name}' "
                        f"(tentativa={attempt}/{attempts}, erro={error_kind}, "
                        f"criterio_transitorio={retry_code}): {exc}"
                    ),
                    "WARNING",
                )
                continue
            if not _is_legacy_fallback_allowed(error_kind):
                registrar_log(
                    "FullRunStatusSync",
                    (
                        f"Fallback legado CSV bloqueado para '{path.name}' "
                        f"({error_kind}): {exc}"
                    ),
                    "ERROR",
                )
                raise
            registrar_log(
                "FullRunStatusSync",
                (
                    f"Fallback legado CSV acionado para '{path.name}' "
                    f"({error_kind}): {exc}"
                ),
                "WARNING",
            )
            return call_with_retry(
                lambda: pd.read_csv(path, sep=delimiter, encoding=encoding),
                op_name="read_csv_legacy_fallback",
                path=path,
                policy=policy,
            )
    raise RuntimeError(f"Leitura contratual sem resultado para '{path.name}': {last_exc}")


def _flush_and_fsync(handle) -> None:
    _shared_flush_and_fsync(handle)


def _artifact_warn_threshold_bytes() -> int:
    raw = str(os.getenv("INTEGRAGAL_FULL_RUN_ARTIFACT_WARN_MB", "25")).strip()
    try:
        threshold_mb = max(0, int(raw))
    except ValueError:
        threshold_mb = 25
    return threshold_mb * 1024 * 1024


def _validate_full_run_artifact_size(path: Path) -> None:
    try:
        size_bytes = int(path.stat().st_size)
    except OSError:
        return
    threshold = _artifact_warn_threshold_bytes()
    if threshold >= 0 and size_bytes > threshold:
        registrar_log(
            "FullRunStatusSync",
            (
                f"Artefato full-run acima do limiar: file={path.name} "
                f"size_bytes={size_bytes} threshold_bytes={threshold}"
            ),
            "WARNING",
        )


def _artifact_incremental_threshold_bytes() -> int:
    raw = str(os.getenv("INTEGRAGAL_FULL_RUN_ARTIFACT_INCREMENTAL_MB", "25")).strip()
    try:
        threshold_mb = max(0, int(raw))
    except ValueError:
        threshold_mb = 25
    return threshold_mb * 1024 * 1024


def _artifact_incremental_threshold_rows() -> int:
    raw = str(os.getenv("INTEGRAGAL_FULL_RUN_ARTIFACT_INCREMENTAL_ROWS", "50000")).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 50000


def _artifact_incremental_threshold_cells() -> int:
    raw = str(os.getenv("INTEGRAGAL_FULL_RUN_ARTIFACT_INCREMENTAL_CELLS", "2000000")).strip()
    try:
        return max(1000, int(raw))
    except ValueError:
        return 2000000


def _artifact_logical_volume(path: Path) -> tuple[int, int]:
    policy = RetryPolicy.from_env()
    row_count = 0
    col_count = 0
    try:
        with open_with_retry(path, "r", encoding="utf-8", newline="", policy=policy) as handle:
            reader = csv.reader(handle, delimiter=",")
            header = next(reader, [])
            col_count = len(header)
            for _ in reader:
                row_count += 1
    except Exception:
        return 0, 0
    return row_count, col_count


def _artifact_logical_volume_limited(
    path: Path,
    *,
    row_threshold: int,
    cell_threshold: int,
) -> tuple[int, int, bool]:
    policy = RetryPolicy.from_env()
    row_count = 0
    col_count = 0
    try:
        with open_with_retry(path, "r", encoding="utf-8", newline="", policy=policy) as handle:
            reader = csv.reader(handle, delimiter=",")
            header = next(reader, [])
            col_count = len(header)
            for _ in reader:
                row_count += 1
                logical_cells = int(row_count) * max(int(col_count), 1)
                if int(row_count) > int(row_threshold) or logical_cells > int(cell_threshold):
                    return row_count, col_count, True
    except Exception:
        return 0, 0, False
    return row_count, col_count, False


def _should_use_incremental_full_run_update(path: Path) -> bool:
    try:
        size_bytes = int(path.stat().st_size)
    except OSError:
        return False
    if size_bytes > _artifact_incremental_threshold_bytes():
        return True
    row_threshold = _artifact_incremental_threshold_rows()
    cell_threshold = _artifact_incremental_threshold_cells()
    row_count, col_count, exceeded = _artifact_logical_volume_limited(
        path,
        row_threshold=row_threshold,
        cell_threshold=cell_threshold,
    )
    if exceeded:
        return True
    logical_cells = int(row_count) * max(int(col_count), 1)
    return (
        int(row_count) > row_threshold
        or logical_cells > cell_threshold
    )


def _update_full_run_artifact_incremental(
    *,
    path: Path,
    updates: Mapping[tuple[str, str, str, str], Dict[str, str]],
    policy: RetryPolicy,
) -> int:
    changed = 0
    tmp = path.with_name(f"{path.name}.tmp")
    with CSVFileLock(path):
        try:
            with open_with_retry(path, "r", encoding="utf-8", newline="", policy=policy) as src:
                reader = csv.DictReader(src, delimiter=",")
                base_fields = [str(col).strip() for col in (reader.fieldnames or [])]
                extra_fields = [
                    col
                    for col in (
                        "status_amostra_corrida",
                        "status_gal",
                        "sucesso_envio",
                        "data_hora_envio",
                        "usuario_envio",
                        "detalhes_envio",
                    )
                    if col not in base_fields
                ]
                fieldnames = base_fields + extra_fields
                with open_with_retry(
                    tmp, "w", encoding="utf-8", newline="", policy=policy
                ) as dst:
                    writer = csv.DictWriter(dst, fieldnames=fieldnames, delimiter=",")
                    writer.writeheader()
                    for row in reader:
                        normalized = {name: row.get(name, "") for name in fieldnames}
                        key = _row_key(normalized)
                        if key is not None and key in updates:
                            payload = updates[key]
                            row_changed = False
                            for col, value in payload.items():
                                current = _safe_str(normalized.get(col, ""))
                                desired = _safe_str(value)
                                if current != desired:
                                    normalized[col] = desired
                                    row_changed = True
                            if row_changed:
                                changed += 1
                        writer.writerow(
                            {col: sanitize_csv_value(normalized.get(col, "")) for col in fieldnames}
                        )
                    _flush_and_fsync(dst)
            os.replace(tmp, path)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
    return changed


def _sqlite_async_audit_path(logs_dir: Path) -> Path:
    return logs_dir / "sqlite_reconcile_async_audit.csv"


def _sqlite_async_queue_path(logs_dir: Path) -> Path:
    return logs_dir / "sqlite_reconcile_async_queue.csv"


def _sqlite_async_queue_archive_path(logs_dir: Path) -> Path:
    return logs_dir / "sqlite_reconcile_async_queue_archive.csv"


def _sqlite_async_payloads_dir(logs_dir: Path) -> Path:
    return logs_dir / "sqlite_reconcile_payloads"


def _sqlite_async_claims_dir(logs_dir: Path) -> Path:
    return logs_dir / "sqlite_reconcile_claims"


def _ensure_sqlite_async_audit(path: Path, policy: RetryPolicy) -> None:
    if path_exists_with_retry(path, policy=policy):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with CSVFileLock(path):
        if path_exists_with_retry(path, policy=policy):
            return
        with open_with_retry(path, "w", newline="", encoding="utf-8", policy=policy) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=_SQLITE_ASYNC_AUDIT_HEADERS,
                delimiter=";",
            )
            writer.writeheader()


def _ensure_sqlite_async_queue(path: Path, policy: RetryPolicy) -> None:
    if path_exists_with_retry(path, policy=policy):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with CSVFileLock(path):
        if path_exists_with_retry(path, policy=policy):
            return
        with open_with_retry(path, "w", newline="", encoding="utf-8", policy=policy) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=_SQLITE_ASYNC_QUEUE_HEADERS,
                delimiter=";",
            )
            writer.writeheader()


def _ensure_sqlite_async_queue_archive(path: Path, policy: RetryPolicy) -> None:
    if path_exists_with_retry(path, policy=policy):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with CSVFileLock(path):
        if path_exists_with_retry(path, policy=policy):
            return
        with open_with_retry(path, "w", newline="", encoding="utf-8", policy=policy) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=_SQLITE_ASYNC_QUEUE_HEADERS,
                delimiter=";",
            )
            writer.writeheader()


def _sqlite_async_max_attempts() -> int:
    raw = str(os.getenv("INTEGRAGAL_SQLITE_ASYNC_MAX_ATTEMPTS", "3")).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 3


def _sqlite_async_backoff_seconds() -> int:
    raw = str(os.getenv("INTEGRAGAL_SQLITE_ASYNC_BACKOFF_SECONDS", "30")).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 30


def _sqlite_async_claim_ttl_seconds() -> int:
    raw = str(os.getenv("INTEGRAGAL_SQLITE_ASYNC_CLAIM_TTL_SECONDS", "120")).strip()
    try:
        return max(10, int(raw))
    except ValueError:
        return 120


def _sqlite_async_reprocess_burst_limit() -> int:
    raw = str(os.getenv("INTEGRAGAL_SQLITE_ASYNC_REPROCESS_BURST", "5")).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 5


def _sqlite_async_max_concurrent_workers() -> int:
    raw = str(os.getenv("INTEGRAGAL_SQLITE_ASYNC_MAX_CONCURRENT", "3")).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 3


def _sqlite_async_queue_retain_rows() -> int:
    raw = str(os.getenv("INTEGRAGAL_SQLITE_ASYNC_QUEUE_RETAIN_ROWS", "5000")).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 5000


def _sqlite_async_archive_retain_rows() -> int:
    raw = str(os.getenv("INTEGRAGAL_SQLITE_ASYNC_ARCHIVE_RETAIN_ROWS", "20000")).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 20000


def _sqlite_async_claim_heartbeat_seconds() -> int:
    raw = str(os.getenv("INTEGRAGAL_SQLITE_ASYNC_CLAIM_HEARTBEAT_SECONDS", "30")).strip()
    try:
        return max(5, int(raw))
    except ValueError:
        return 30


def _sqlite_async_claim_expiry_grace_seconds() -> int:
    raw = str(os.getenv("INTEGRAGAL_SQLITE_ASYNC_CLAIM_EXPIRY_GRACE_SECONDS", "15")).strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 15


def _sqlite_async_archive_max_age_days() -> int:
    raw = str(os.getenv("INTEGRAGAL_SQLITE_ASYNC_ARCHIVE_MAX_AGE_DAYS", "30")).strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 30


def _sqlite_async_archive_max_bytes() -> int:
    raw = str(os.getenv("INTEGRAGAL_SQLITE_ASYNC_ARCHIVE_MAX_MB", "25")).strip()
    try:
        mb = max(0, int(raw))
    except ValueError:
        mb = 25
    return mb * 1024 * 1024


def _sqlite_async_payload_rollout_mode() -> str:
    mode = str(os.getenv("INTEGRAGAL_SQLITE_ASYNC_PAYLOAD_MODE", "inline")).strip().lower()
    if mode not in {"inline", "external", "auto"}:
        return "inline"
    return mode


def _sqlite_async_payload_auto_min_bytes() -> int:
    raw = str(os.getenv("INTEGRAGAL_SQLITE_ASYNC_PAYLOAD_AUTO_MIN_BYTES", "512")).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 512


def _sqlite_async_payload_hmac_key() -> str:
    return str(os.getenv("INTEGRAGAL_SQLITE_ASYNC_PAYLOAD_HMAC_KEY", "")).strip()


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def _sqlite_async_next_retry_epoch(attempt: int) -> int:
    exponent = max(0, int(attempt) - 1)
    delay = _sqlite_async_backoff_seconds() * (2 ** exponent)
    return int(time.time()) + int(delay)


def _claim_is_expired(*, lease_until_epoch: int, now_epoch: int) -> bool:
    grace = _sqlite_async_claim_expiry_grace_seconds()
    return int(now_epoch) > (int(lease_until_epoch) + int(grace))


def _read_claim_payload(claim_path: Path) -> Dict[str, Any]:
    try:
        parsed = json.loads(claim_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _claim_sqlite_async_job(*, logs_dir: Path, job_id: str) -> bool:
    claims_dir = _sqlite_async_claims_dir(logs_dir)
    claims_dir.mkdir(parents=True, exist_ok=True)
    claim_path = claims_dir / f"{_safe_str(job_id)}.claim"
    now_epoch = int(time.time())

    if claim_path.exists():
        payload = _read_claim_payload(claim_path)
        lease_until = _safe_int(payload.get("lease_until_epoch", 0), default=0)
        if not _claim_is_expired(lease_until_epoch=lease_until, now_epoch=now_epoch):
            return False
        try:
            claim_path.unlink()
        except OSError:
            return False

    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(claim_path), flags)
    except FileExistsError:
        return False
    except OSError:
        return False

    lease_until = now_epoch + _sqlite_async_claim_ttl_seconds()
    payload = {
        "job_id": _safe_str(job_id),
        "owner_pid": int(os.getpid()),
        "lease_until_epoch": int(lease_until),
    }
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False))
        _flush_and_fsync(handle)
    return True


def _renew_sqlite_async_job_claim(*, logs_dir: Path, job_id: str) -> bool:
    claim_path = _sqlite_async_claims_dir(logs_dir) / f"{_safe_str(job_id)}.claim"
    if not claim_path.exists():
        return False
    now_epoch = int(time.time())
    lease_until = now_epoch + _sqlite_async_claim_ttl_seconds()
    payload = _read_claim_payload(claim_path)
    payload["job_id"] = _safe_str(job_id)
    payload["owner_pid"] = int(os.getpid())
    payload["lease_until_epoch"] = int(lease_until)
    tmp = claim_path.with_suffix(".claim.tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False))
            _flush_and_fsync(handle)
        os.replace(tmp, claim_path)
    except OSError:
        return False
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    return True


def _release_sqlite_async_job_claim(*, logs_dir: Path, job_id: str) -> None:
    claim_path = _sqlite_async_claims_dir(logs_dir) / f"{_safe_str(job_id)}.claim"
    try:
        claim_path.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def _active_sqlite_async_claims(logs_dir: Path) -> int:
    claims_dir = _sqlite_async_claims_dir(logs_dir)
    if not claims_dir.exists():
        return 0
    now_epoch = int(time.time())
    active = 0
    for claim_path in claims_dir.glob("*.claim"):
        payload = _read_claim_payload(claim_path)
        lease_until = _safe_int(payload.get("lease_until_epoch", 0), default=0)
        if _claim_is_expired(lease_until_epoch=lease_until, now_epoch=now_epoch):
            try:
                claim_path.unlink()
            except OSError:
                pass
            continue
        active += 1
    return active


def _start_sqlite_async_claim_heartbeat(
    *,
    logs_dir: Path,
    job_id: str,
) -> tuple[threading.Event, threading.Thread]:
    stop_event = threading.Event()
    base_interval = _sqlite_async_claim_heartbeat_seconds()

    def _next_wait_seconds() -> int:
        claim_path = _sqlite_async_claims_dir(logs_dir) / f"{_safe_str(job_id)}.claim"
        payload = _read_claim_payload(claim_path)
        lease_until = _safe_int(payload.get("lease_until_epoch", 0), default=0)
        now_epoch = int(time.time())
        remaining = max(1, int(lease_until) - int(now_epoch))
        adaptive = max(1, min(int(base_interval), max(1, remaining // 2)))
        return adaptive

    def _runner() -> None:
        while True:
            wait_seconds = _next_wait_seconds()
            if stop_event.wait(wait_seconds):
                break
            _renew_sqlite_async_job_claim(logs_dir=logs_dir, job_id=job_id)

    worker = threading.Thread(
        target=_runner,
        daemon=True,
        name=f"sqlite-claim-heartbeat-{_safe_str(job_id)[:8]}",
    )
    worker.start()
    return stop_event, worker


def _serialize_updates_for_queue(
    updates: Mapping[tuple[str, str, str, str], Dict[str, str]]
) -> str:
    items: list[dict[str, Any]] = []
    for key, payload in updates.items():
        if len(key) != 4:
            continue
        serialized_payload = {str(k): _safe_str(v) for k, v in payload.items()}
        items.append(
            {
                "key": [_safe_str(part) for part in key],
                "payload": serialized_payload,
            }
        )
    return json.dumps(items, ensure_ascii=False, separators=(",", ":"))


def _payload_hmac_signature(payload_text: str, key: str) -> str:
    digest = hmac.new(
        key.encode("utf-8"),
        payload_text.encode("utf-8"),
        hashlib.sha256,
    )
    return digest.hexdigest()


def _persist_external_payload_reference(
    *,
    logs_dir: Path,
    job_id: str,
    payload_text: str,
) -> str:
    policy = RetryPolicy.from_env()
    payloads_dir = _sqlite_async_payloads_dir(logs_dir)
    payloads_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{_safe_str(job_id)}.json"
    target = payloads_dir / filename
    tmp = payloads_dir / f"{filename}.tmp"
    checksum_target = target.with_suffix(target.suffix + ".sha256")
    checksum_tmp = checksum_target.with_suffix(".sha256.tmp")
    hmac_target = target.with_suffix(target.suffix + ".hmac")
    hmac_tmp = hmac_target.with_suffix(".hmac.tmp")
    checksum = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
    hmac_key = _sqlite_async_payload_hmac_key()
    hmac_signature = _payload_hmac_signature(payload_text, hmac_key) if hmac_key else ""
    try:
        with open_with_retry(tmp, "w", encoding="utf-8", newline="", policy=policy) as handle:
            handle.write(payload_text)
            _flush_and_fsync(handle)
        with open_with_retry(
            checksum_tmp, "w", encoding="utf-8", newline="", policy=policy
        ) as handle:
            handle.write(checksum)
            _flush_and_fsync(handle)
        if hmac_signature:
            with open_with_retry(hmac_tmp, "w", encoding="utf-8", newline="", policy=policy) as handle:
                handle.write(hmac_signature)
                _flush_and_fsync(handle)
        os.replace(tmp, target)
        os.replace(checksum_tmp, checksum_target)
        if hmac_signature:
            os.replace(hmac_tmp, hmac_target)
        return f"@file:{filename}"
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        if checksum_tmp.exists():
            try:
                checksum_tmp.unlink()
            except OSError:
                pass
        if hmac_tmp.exists():
            try:
                hmac_tmp.unlink()
            except OSError:
                pass


def _store_queue_payload_reference(*, logs_dir: Path, job_id: str, payload_json: str) -> str:
    payload_text = str(payload_json or "[]")
    mode = _sqlite_async_payload_rollout_mode()
    use_external = False
    if mode == "external":
        use_external = True
    elif mode == "auto":
        use_external = len(payload_text.encode("utf-8")) >= _sqlite_async_payload_auto_min_bytes()

    if not use_external:
        if mode == "auto":
            registrar_log(
                "FullRunStatusSync",
                "payload_rollout=inline_auto",
                "INFO",
            )
        return payload_text
    try:
        ref = _persist_external_payload_reference(
            logs_dir=logs_dir,
            job_id=job_id,
            payload_text=payload_text,
        )
        if mode == "auto":
            registrar_log(
                "FullRunStatusSync",
                "payload_rollout=external_auto",
                "INFO",
            )
        return ref
    except Exception as exc:
        registrar_log(
            "FullRunStatusSync",
            f"payload_rollout=fallback_inline erro={exc}",
            "WARNING",
        )
        return payload_text


def _resolve_queue_payload_reference(*, logs_dir: Path, payload: str) -> str:
    raw = _safe_str(payload)
    if not raw.startswith("@file:"):
        return raw
    filename = raw.replace("@file:", "", 1).strip()
    if not filename:
        return "[]"
    policy = RetryPolicy.from_env()
    target = _sqlite_async_payloads_dir(logs_dir) / filename
    if not path_exists_with_retry(target, policy=policy):
        return "[]"
    try:
        with open_with_retry(target, "r", encoding="utf-8", newline="", policy=policy) as handle:
            payload_text = str(handle.read() or "[]")
    except Exception:
        return "[]"
    checksum_path = target.with_suffix(target.suffix + ".sha256")
    hmac_path = target.with_suffix(target.suffix + ".hmac")
    hmac_key = _sqlite_async_payload_hmac_key()
    if path_exists_with_retry(hmac_path, policy=policy):
        if not hmac_key:
            return "[]"
        try:
            with open_with_retry(
                hmac_path, "r", encoding="utf-8", newline="", policy=policy
            ) as handle:
                expected_hmac = _safe_str(handle.read())
        except Exception:
            return "[]"
        current_hmac = _payload_hmac_signature(payload_text, hmac_key)
        if expected_hmac and current_hmac != expected_hmac:
            return "[]"
    if path_exists_with_retry(checksum_path, policy=policy):
        try:
            with open_with_retry(
                checksum_path, "r", encoding="utf-8", newline="", policy=policy
            ) as handle:
                expected = _safe_str(handle.read())
        except Exception:
            return "[]"
        current = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
        if expected and current != expected:
            return "[]"
    return payload_text


def _deserialize_updates_from_queue(
    payload: str,
    *,
    logs_dir: Optional[Path] = None,
) -> Dict[tuple[str, str, str, str], Dict[str, str]]:
    updates: Dict[tuple[str, str, str, str], Dict[str, str]] = {}
    raw_payload = payload
    if logs_dir is not None:
        raw_payload = _resolve_queue_payload_reference(logs_dir=logs_dir, payload=payload)
    try:
        parsed = json.loads(raw_payload)
    except json.JSONDecodeError:
        return updates
    if not isinstance(parsed, list):
        return updates
    for item in parsed:
        if not isinstance(item, dict):
            continue
        key_parts = item.get("key")
        row_payload = item.get("payload", {})
        if not isinstance(key_parts, list) or len(key_parts) != 4:
            continue
        if not isinstance(row_payload, dict):
            continue
        key = tuple(_safe_str(part) for part in key_parts)
        normalized_payload = {str(k): _safe_str(v) for k, v in row_payload.items()}
        updates[key] = normalized_payload
    return updates


def _append_sqlite_async_queue_archive(
    *,
    logs_dir: Path,
    rows: List[Dict[str, str]],
    policy: RetryPolicy,
) -> None:
    if not rows:
        return
    archive_path = _sqlite_async_queue_archive_path(logs_dir)
    _ensure_sqlite_async_queue_archive(archive_path, policy)
    with CSVFileLock(archive_path):
        with open_with_retry(
            archive_path, "a", newline="", encoding="utf-8", policy=policy
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=_SQLITE_ASYNC_QUEUE_HEADERS,
                delimiter=";",
            )
            for row in rows:
                writer.writerow({name: _safe_str(row.get(name, "")) for name in _SQLITE_ASYNC_QUEUE_HEADERS})
    _rotate_sqlite_async_queue_archive_if_needed(logs_dir=logs_dir)


def _queue_row_timestamp_epoch(row: Mapping[str, str]) -> int:
    raw = _safe_str(row.get("timestamp", ""))
    if not raw:
        return 0
    try:
        return int(datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").timestamp())
    except ValueError:
        return 0


def _queue_row_approx_bytes(row: Mapping[str, str]) -> int:
    total = 0
    for name in _SQLITE_ASYNC_QUEUE_HEADERS:
        total += len(_safe_str(row.get(name, "")).encode("utf-8")) + 1
    return total


def _rotate_sqlite_async_queue_archive_if_needed(*, logs_dir: Path) -> int:
    policy = RetryPolicy.from_env()
    path = _sqlite_async_queue_archive_path(logs_dir)
    if not path_exists_with_retry(path, policy=policy):
        return 0
    retain_rows = _sqlite_async_archive_retain_rows()
    max_age_days = _sqlite_async_archive_max_age_days()
    max_bytes = _sqlite_async_archive_max_bytes()
    now_epoch = int(time.time())
    min_epoch = now_epoch - int(max_age_days * 86400) if max_age_days > 0 else 0
    candidates: deque[Dict[str, str]] = deque(maxlen=retain_rows)
    total_rows = 0
    with CSVFileLock(path):
        with open_with_retry(path, "r", newline="", encoding="utf-8", policy=policy) as handle:
            reader = csv.DictReader(handle, delimiter=";")
            for row in reader:
                normalized = {name: _safe_str(row.get(name, "")) for name in _SQLITE_ASYNC_QUEUE_HEADERS}
                total_rows += 1
                row_epoch = _queue_row_timestamp_epoch(normalized)
                if min_epoch > 0 and row_epoch > 0 and row_epoch < min_epoch:
                    continue
                candidates.append(normalized)
        if total_rows <= retain_rows and len(candidates) == total_rows:
            return 0

        kept_rows: deque[Dict[str, str]] = deque()
        used_bytes = 0
        for row in reversed(candidates):
            row_size = _queue_row_approx_bytes(row)
            if max_bytes > 0 and (used_bytes + row_size) > max_bytes:
                continue
            kept_rows.appendleft(row)
            used_bytes += row_size

        tmp = path.with_name(f"{path.name}.tmp")
        try:
            with open_with_retry(tmp, "w", newline="", encoding="utf-8", policy=policy) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=_SQLITE_ASYNC_QUEUE_HEADERS,
                    delimiter=";",
                )
                writer.writeheader()
                for row in kept_rows:
                    writer.writerow(row)
                _flush_and_fsync(handle)
            os.replace(tmp, path)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
    return max(0, total_rows - len(kept_rows))


def _compact_sqlite_async_queue_if_needed(*, logs_dir: Path) -> int:
    policy = RetryPolicy.from_env()
    path = _sqlite_async_queue_path(logs_dir)
    if not path_exists_with_retry(path, policy=policy):
        return 0

    retain_rows = _sqlite_async_queue_retain_rows()
    with CSVFileLock(path):
        latest_seq_by_job: Dict[str, int] = {}
        tail_rows: deque[tuple[int, Dict[str, str]]] = deque(maxlen=retain_rows)
        total_rows = 0
        with open_with_retry(path, "r", newline="", encoding="utf-8", policy=policy) as handle:
            reader = csv.DictReader(handle, delimiter=";")
            for row in reader:
                total_rows += 1
                normalized = {name: _safe_str(row.get(name, "")) for name in _SQLITE_ASYNC_QUEUE_HEADERS}
                tail_rows.append((total_rows, normalized))
                job_id = _safe_str(normalized.get("job_id", ""))
                if job_id:
                    latest_seq_by_job[job_id] = total_rows
        if total_rows <= retain_rows:
            return 0

        keep_seqs = set(latest_seq_by_job.values())
        for seq, _row in tail_rows:
            keep_seqs.add(seq)
        if len(keep_seqs) > retain_rows:
            keep_seqs = set(sorted(keep_seqs)[-retain_rows:])
        elif len(keep_seqs) < retain_rows:
            for seq, _row in reversed(tail_rows):
                keep_seqs.add(seq)
                if len(keep_seqs) >= retain_rows:
                    break

        archive_path = _sqlite_async_queue_archive_path(logs_dir)
        _ensure_sqlite_async_queue_archive(archive_path, policy)

        tmp = path.with_name(f"{path.name}.tmp")
        moved = 0
        try:
            with open_with_retry(path, "r", newline="", encoding="utf-8", policy=policy) as src, open_with_retry(
                tmp, "w", newline="", encoding="utf-8", policy=policy
            ) as dst, open_with_retry(
                archive_path, "a", newline="", encoding="utf-8", policy=policy
            ) as archive:
                reader = csv.DictReader(src, delimiter=";")
                queue_writer = csv.DictWriter(
                    dst,
                    fieldnames=_SQLITE_ASYNC_QUEUE_HEADERS,
                    delimiter=";",
                )
                archive_writer = csv.DictWriter(
                    archive,
                    fieldnames=_SQLITE_ASYNC_QUEUE_HEADERS,
                    delimiter=";",
                )
                queue_writer.writeheader()
                seq = 0
                for row in reader:
                    seq += 1
                    normalized = {name: _safe_str(row.get(name, "")) for name in _SQLITE_ASYNC_QUEUE_HEADERS}
                    if seq in keep_seqs:
                        queue_writer.writerow(normalized)
                    else:
                        archive_writer.writerow(normalized)
                        moved += 1
                _flush_and_fsync(dst)
                _flush_and_fsync(archive)
            os.replace(tmp, path)
            _rotate_sqlite_async_queue_archive_if_needed(logs_dir=logs_dir)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
    return moved


def _append_sqlite_async_queue_event(
    *,
    logs_dir: Path,
    job_id: str,
    status: str,
    attempt: int,
    next_retry_epoch: int,
    db_path: str,
    updates_json: str,
    last_error: str,
) -> None:
    policy = RetryPolicy.from_env()
    path = _sqlite_async_queue_path(logs_dir)
    _ensure_sqlite_async_queue(path, policy)
    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "job_id": str(job_id),
        "status": str(status),
        "attempt": str(int(attempt)),
        "next_retry_epoch": str(int(next_retry_epoch)),
        "db_path": str(db_path or ""),
        "updates_json": str(updates_json or "[]"),
        "last_error": str(last_error or ""),
    }
    with CSVFileLock(path):
        with open_with_retry(path, "a", newline="", encoding="utf-8", policy=policy) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=_SQLITE_ASYNC_QUEUE_HEADERS,
                delimiter=";",
            )
            writer.writerow(payload)
    if str(status) in _SQLITE_ASYNC_QUEUE_TERMINAL:
        _compact_sqlite_async_queue_if_needed(logs_dir=logs_dir)


def _latest_sqlite_async_queue_state(logs_dir: Path) -> Dict[str, Dict[str, str]]:
    _compact_sqlite_async_queue_if_needed(logs_dir=logs_dir)
    policy = RetryPolicy.from_env()
    path = _sqlite_async_queue_path(logs_dir)
    if not path_exists_with_retry(path, policy=policy):
        return {}
    latest: Dict[str, Dict[str, str]] = {}
    with CSVFileLock(path):
        with open_with_retry(path, "r", newline="", encoding="utf-8", policy=policy) as handle:
            reader = csv.DictReader(handle, delimiter=";")
            for row in reader:
                job_id = _safe_str(row.get("job_id", ""))
                if not job_id:
                    continue
                latest[job_id] = {str(k): _safe_str(v) for k, v in row.items()}
    return latest


def _append_sqlite_async_audit(
    *,
    logs_dir: Path,
    job_id: str,
    status: str,
    attempt: int,
    rows_updated: int,
    error: str,
    db_path: str,
    updates_count: int,
) -> None:
    policy = RetryPolicy.from_env()
    path = _sqlite_async_audit_path(logs_dir)
    _ensure_sqlite_async_audit(path, policy)
    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "job_id": str(job_id),
        "status": str(status),
        "attempt": str(int(attempt)),
        "rows_updated": str(int(rows_updated)),
        "error": str(error or ""),
        "db_path": str(db_path or ""),
        "updates_count": str(int(updates_count)),
    }
    with CSVFileLock(path):
        with open_with_retry(path, "a", newline="", encoding="utf-8", policy=policy) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=_SQLITE_ASYNC_AUDIT_HEADERS,
                delimiter=";",
            )
            writer.writerow(payload)


def _run_async_sqlite_reconciliation(
    *,
    updates: Mapping[tuple[str, str, str, str], Dict[str, str]],
    sqlite_db_path: Optional[Path | str],
    logs_dir: Path,
    job_id: str,
    attempt: int = 1,
    updates_json: Optional[str] = None,
) -> None:
    serialized_updates = updates_json or _store_queue_payload_reference(
        logs_dir=logs_dir,
        job_id=job_id,
        payload_json=_serialize_updates_for_queue(updates),
    )
    heartbeat_stop: threading.Event | None = None
    heartbeat_worker: threading.Thread | None = None
    try:
        heartbeat_stop, heartbeat_worker = _start_sqlite_async_claim_heartbeat(
            logs_dir=logs_dir,
            job_id=job_id,
        )
        try:
            repo = ExamRunsSQLiteRepository(db_path=sqlite_db_path)
            rows = int(repo.update_status_fields_by_contract_key(updates))
            _append_sqlite_async_queue_event(
                logs_dir=logs_dir,
                job_id=job_id,
                status="success",
                attempt=attempt,
                next_retry_epoch=0,
                db_path=str(sqlite_db_path or ""),
                updates_json=serialized_updates,
                last_error="",
            )
            _append_sqlite_async_audit(
                logs_dir=logs_dir,
                job_id=job_id,
                status="success",
                attempt=attempt,
                rows_updated=rows,
                error="",
                db_path=str(sqlite_db_path or ""),
                updates_count=len(updates),
            )
        except Exception as exc:
            should_retry = _is_transient_critical_error(exc) and attempt < _sqlite_async_max_attempts()
            if should_retry:
                _append_sqlite_async_queue_event(
                    logs_dir=logs_dir,
                    job_id=job_id,
                    status="retry_scheduled",
                    attempt=attempt,
                    next_retry_epoch=_sqlite_async_next_retry_epoch(attempt),
                    db_path=str(sqlite_db_path or ""),
                    updates_json=serialized_updates,
                    last_error=str(exc),
                )
                _append_sqlite_async_audit(
                    logs_dir=logs_dir,
                    job_id=job_id,
                    status="retry_scheduled",
                    attempt=attempt,
                    rows_updated=0,
                    error=str(exc),
                    db_path=str(sqlite_db_path or ""),
                    updates_count=len(updates),
                )
                return
            _append_sqlite_async_queue_event(
                logs_dir=logs_dir,
                job_id=job_id,
                status="failed",
                attempt=attempt,
                next_retry_epoch=0,
                db_path=str(sqlite_db_path or ""),
                updates_json=serialized_updates,
                last_error=str(exc),
            )
            _append_sqlite_async_audit(
                logs_dir=logs_dir,
                job_id=job_id,
                status="failed",
                attempt=attempt,
                rows_updated=0,
                error=str(exc),
                db_path=str(sqlite_db_path or ""),
                updates_count=len(updates),
            )
    finally:
        if heartbeat_stop is not None:
            heartbeat_stop.set()
        if heartbeat_worker is not None:
            heartbeat_worker.join(timeout=0.2)
        _release_sqlite_async_job_claim(logs_dir=logs_dir, job_id=job_id)


def _schedule_async_sqlite_reconciliation(
    *,
    updates: Mapping[tuple[str, str, str, str], Dict[str, str]],
    sqlite_db_path: Optional[Path | str],
    logs_dir: Path,
) -> str:
    job_id = uuid.uuid4().hex
    serialized_updates = _store_queue_payload_reference(
        logs_dir=logs_dir,
        job_id=job_id,
        payload_json=_serialize_updates_for_queue(dict(updates)),
    )
    _append_sqlite_async_queue_event(
        logs_dir=logs_dir,
        job_id=job_id,
        status="queued",
        attempt=0,
        next_retry_epoch=int(time.time()),
        db_path=str(sqlite_db_path or ""),
        updates_json=serialized_updates,
        last_error="",
    )
    _claim_sqlite_async_job(logs_dir=logs_dir, job_id=job_id)
    _append_sqlite_async_audit(
        logs_dir=logs_dir,
        job_id=job_id,
        status="queued",
        attempt=0,
        rows_updated=0,
        error="",
        db_path=str(sqlite_db_path or ""),
        updates_count=len(updates),
    )
    worker = threading.Thread(
        target=_run_async_sqlite_reconciliation,
        kwargs={
            "updates": dict(updates),
            "sqlite_db_path": sqlite_db_path,
            "logs_dir": logs_dir,
            "job_id": job_id,
            "attempt": 1,
            "updates_json": serialized_updates,
        },
        daemon=True,
        name=f"sqlite-reconcile-{job_id[:8]}",
    )
    worker.start()
    return job_id


def _reprocess_sqlite_async_queue(*, logs_dir: Path) -> int:
    now_epoch = int(time.time())
    scheduled = 0
    burst_limit = _sqlite_async_reprocess_burst_limit()
    max_concurrent = _sqlite_async_max_concurrent_workers()
    active_claims = _active_sqlite_async_claims(logs_dir)
    if active_claims >= max_concurrent:
        return 0
    latest = _latest_sqlite_async_queue_state(logs_dir)
    for job_id, row in latest.items():
        if scheduled >= burst_limit:
            break
        if (active_claims + scheduled) >= max_concurrent:
            break
        status = _safe_str(row.get("status", ""))
        if status not in _SQLITE_ASYNC_QUEUE_PENDING:
            continue
        due_epoch = _safe_int(row.get("next_retry_epoch", "0"), default=0)
        if due_epoch > now_epoch:
            continue
        if not _claim_sqlite_async_job(logs_dir=logs_dir, job_id=job_id):
            continue
        updates_json = _safe_str(row.get("updates_json", ""))
        updates = _deserialize_updates_from_queue(updates_json, logs_dir=logs_dir)
        if not updates:
            _release_sqlite_async_job_claim(logs_dir=logs_dir, job_id=job_id)
            _append_sqlite_async_queue_event(
                logs_dir=logs_dir,
                job_id=job_id,
                status="failed",
                attempt=_safe_int(row.get("attempt", "0"), default=0),
                next_retry_epoch=0,
                db_path=_safe_str(row.get("db_path", "")),
                updates_json=updates_json,
                last_error="payload_ausente_ou_invalido",
            )
            _append_sqlite_async_audit(
                logs_dir=logs_dir,
                job_id=job_id,
                status="failed",
                attempt=_safe_int(row.get("attempt", "0"), default=0),
                rows_updated=0,
                error="payload_ausente_ou_invalido",
                db_path=_safe_str(row.get("db_path", "")),
                updates_count=0,
            )
            continue
        next_attempt = _safe_int(row.get("attempt", "0"), default=0) + 1
        worker = threading.Thread(
            target=_run_async_sqlite_reconciliation,
            kwargs={
                "updates": updates,
                "sqlite_db_path": _safe_str(row.get("db_path", "")) or None,
                "logs_dir": logs_dir,
                "job_id": job_id,
                "attempt": next_attempt,
                "updates_json": updates_json,
            },
            daemon=True,
            name=f"sqlite-reconcile-{job_id[:8]}",
        )
        try:
            worker.start()
            scheduled += 1
        except Exception:
            _release_sqlite_async_job_claim(logs_dir=logs_dir, job_id=job_id)
    return scheduled


def _update_dataframe_in_place(
    df: pd.DataFrame,
    updates: Mapping[tuple[str, str, str, str], Dict[str, str]],
) -> int:
    changed = 0
    if df.empty:
        return changed
    for col in (
        "status_amostra_corrida",
        "status_gal",
        "sucesso_envio",
        "data_hora_envio",
        "usuario_envio",
        "detalhes_envio",
    ):
        if col not in df.columns:
            df[col] = ""
        else:
            df[col] = df[col].astype("object")

    for idx, row in df.iterrows():
        key = _row_key(row.to_dict())
        if key is None or key not in updates:
            continue
        payload = updates[key]
        row_changed = False
        for col, value in payload.items():
            current = _safe_str(df.at[idx, col])
            desired = _safe_str(value)
            if current != desired:
                df.at[idx, col] = desired
                row_changed = True
        if row_changed:
            changed += 1
    return changed


def _update_historico(
    *,
    updates: Mapping[tuple[str, str, str, str], Dict[str, str]],
    history_path: Path,
) -> int:
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(history_path, policy=policy):
        return 0
    df = _read_csv_with_fallback(
        history_path,
        delimiter=";",
        encoding="utf-8",
        contract_name="historico_analises.csv",
    )
    changed = _update_dataframe_in_place(df, updates)
    if changed <= 0:
        return 0
    fieldnames = [str(col).strip() for col in df.columns]
    rows = df.fillna("").to_dict(orient="records")
    write_csv_atomic(
        history_path,
        rows=rows,
        fieldnames=fieldnames,
        contract_name="historico_analises.csv",
        policy=policy,
    )
    return changed


def _update_exam_runs_csv(
    *,
    updates: Mapping[tuple[str, str, str, str], Dict[str, str]],
    logs_dir: Path,
    exame_id: str,
) -> int:
    policy = RetryPolicy.from_env()
    candidates: List[Path]
    if _safe_str(exame_id):
        candidates = [logs_dir / f"corridas_{slugify(exame_id)}.csv"]
    else:
        candidates = sorted(logs_dir.glob("corridas_*.csv"))

    total_changed = 0
    for path in candidates:
        if not path_exists_with_retry(path, policy=policy):
            continue
        df = _read_csv_with_fallback(
            path,
            delimiter=",",
            encoding="utf-8",
            contract_name=str(path.name),
        )
        changed = _update_dataframe_in_place(df, updates)
        if changed <= 0:
            continue
        fieldnames = [str(col).strip() for col in df.columns]
        rows = df.fillna("").to_dict(orient="records")
        write_csv_atomic(
            path,
            rows=rows,
            fieldnames=fieldnames,
            contract_name=str(path.name),
            policy=policy,
        )
        total_changed += changed
    return total_changed


def _update_full_run_artifacts(
    *,
    updates: Mapping[tuple[str, str, str, str], Dict[str, str]],
    reports_dir: Path,
    corrida_id: str,
) -> int:
    policy = RetryPolicy.from_env()
    if not reports_dir.exists():
        return 0

    if _safe_str(corrida_id):
        token = _sanitize_filename(corrida_id)
        candidates = sorted(reports_dir.glob(f"corrida_completa_{token}_*.csv"))
    else:
        candidates = sorted(reports_dir.glob("corrida_completa_*.csv"))

    changed_total = 0
    for path in candidates:
        if not path_exists_with_retry(path, policy=policy):
            continue
        _validate_full_run_artifact_size(path)
        if _should_use_incremental_full_run_update(path):
            changed = _update_full_run_artifact_incremental(
                path=path,
                updates=updates,
                policy=policy,
            )
            changed_total += changed
            continue
        with CSVFileLock(path):
            df = call_with_retry(
                lambda: pd.read_csv(path, sep=",", encoding="utf-8"),
                op_name="read_full_run_artifact",
                path=path,
                policy=policy,
            )
            changed = _update_dataframe_in_place(df, updates)
            if changed <= 0:
                continue
            changed_total += changed
            tmp = path.with_name(f"{path.name}.tmp")
            fieldnames = [str(col).strip() for col in df.columns]
            rows = df.fillna("").to_dict(orient="records")
            try:
                with open_with_retry(
                    tmp, "w", encoding="utf-8", newline="", policy=policy
                ) as handle:
                    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=",")
                    writer.writeheader()
                    for row in rows:
                        writer.writerow(
                            {col: sanitize_csv_value(row.get(col, "")) for col in fieldnames}
                        )
                    _flush_and_fsync(handle)
                os.replace(tmp, path)
            finally:
                if tmp.exists():
                    try:
                        tmp.unlink()
                    except OSError:
                        pass
    return changed_total


def reconcile_send_status_across_artifacts(
    *,
    relatorio_local: Iterable[Mapping[str, Any]],
    context: Optional[Mapping[str, Any]] = None,
    logs_dir: Optional[Path | str] = None,
    reports_dir: Optional[Path | str] = None,
    sqlite_db_path: Optional[Path | str] = None,
) -> Dict[str, int]:
    """
    Reconciliacao idempotente de status pos-envio GAL.

    Atualiza:
    - historico_analises.csv
    - corridas_<slug_exame>.csv
    - tabela exam_runs (targets_json)
    - artefato corrida_completa_<corrida>_*.csv
    """
    context_data: Dict[str, Any] = dict(context or {})
    updates = _build_updates(relatorio_local=relatorio_local, context=context_data)
    return apply_status_updates_across_artifacts(
        updates=updates,
        context=context_data,
        logs_dir=logs_dir,
        reports_dir=reports_dir,
        sqlite_db_path=sqlite_db_path,
    )


def apply_status_updates_across_artifacts(
    *,
    updates: Mapping[tuple[str, str, str, str], Dict[str, str]],
    context: Optional[Mapping[str, Any]] = None,
    logs_dir: Optional[Path | str] = None,
    reports_dir: Optional[Path | str] = None,
    sqlite_db_path: Optional[Path | str] = None,
) -> Dict[str, int]:
    """Aplica atualizacoes de status por chave contratual em todos os artefatos suportados."""
    context_data: Dict[str, Any] = dict(context or {})
    if not updates:
        return {
            "input_updates": 0,
            "historico_rows_updated": 0,
            "exam_runs_csv_rows_updated": 0,
            "exam_runs_sqlite_rows_updated": 0,
            "full_run_rows_updated": 0,
        }

    paths = config_service.get_paths()
    resolved_logs = Path(logs_dir) if logs_dir else Path(paths.get("log_file", "logs/sistema.log")).parent
    resolved_reports = (
        Path(reports_dir)
        if reports_dir
        else Path(paths.get("reports_dir") or paths.get("default_results_folder") or "reports")
    )
    history_path = Path(paths.get("gal_history_csv", str(resolved_logs / "historico_analises.csv")))
    requeued_jobs = _reprocess_sqlite_async_queue(logs_dir=resolved_logs)
    if requeued_jobs > 0:
        registrar_log(
            "FullRunStatusSync",
            (
                "Reprocessamento assincrono SQLite acionado; "
                f"jobs_disparados={requeued_jobs}"
            ),
            "INFO",
        )

    historico_rows = _update_historico(updates=updates, history_path=history_path)
    exam_rows = _update_exam_runs_csv(
        updates=updates,
        logs_dir=resolved_logs,
        exame_id=_safe_str(context_data.get("exame_id", "")),
    )

    sqlite_rows = 0
    sqlite_partial_inconsistency = False
    try:
        repo = ExamRunsSQLiteRepository(db_path=sqlite_db_path)
        sqlite_rows = repo.update_status_fields_by_contract_key(updates)
    except Exception as exc:
        sqlite_partial_inconsistency = True
        registrar_log(
            "FullRunStatusSync",
            (
                "Falha ao atualizar exam_runs SQLite; "
                f"inconsistencia_parcial=true; erro={exc}"
            ),
            "WARNING",
        )

    full_rows = _update_full_run_artifacts(
        updates=updates,
        reports_dir=resolved_reports,
        corrida_id=_safe_str(context_data.get("corrida_id", "")),
    )

    sqlite_recovery_rows = 0
    if sqlite_partial_inconsistency and updates:
        try:
            repo_recovery = ExamRunsSQLiteRepository(db_path=sqlite_db_path)
            sqlite_recovery_rows = repo_recovery.update_status_fields_by_contract_key(updates)
            if sqlite_recovery_rows > 0:
                sqlite_rows += int(sqlite_recovery_rows)
                sqlite_partial_inconsistency = False
                registrar_log(
                    "FullRunStatusSync",
                    (
                        "Reconciliacao SQLite pos-falha aplicada; "
                        f"reconciliacao_sqlite_recovery=true; rows={sqlite_recovery_rows}"
                    ),
                    "INFO",
                )
        except Exception as exc:
            registrar_log(
                "FullRunStatusSync",
                (
                    "Reconciliacao SQLite pos-falha nao concluida; "
                    f"inconsistencia_parcial=true; erro={exc}"
                ),
                "WARNING",
            )
            async_job_id = _schedule_async_sqlite_reconciliation(
                updates=updates,
                sqlite_db_path=sqlite_db_path,
                logs_dir=resolved_logs,
            )
            registrar_log(
                "FullRunStatusSync",
                (
                    "Reconciliacao SQLite assincrona agendada; "
                    f"async_sqlite_reconcile_job={async_job_id}"
                ),
                "WARNING",
            )

    summary = {
        "input_updates": len(updates),
        "historico_rows_updated": int(historico_rows),
        "exam_runs_csv_rows_updated": int(exam_rows),
        "exam_runs_sqlite_rows_updated": int(sqlite_rows),
        "full_run_rows_updated": int(full_rows),
    }
    if sqlite_partial_inconsistency:
        registrar_log(
            "FullRunStatusSync",
            f"Resumo reconciliacao com inconsistencia parcial: {summary}",
            "WARNING",
        )
    registrar_log("FullRunStatusSync", f"Reconciliacao pos-envio concluida: {summary}", "INFO")
    return summary
