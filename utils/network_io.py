# -*- coding: utf-8 -*-
"""
Network I/O Retry Utilities

Centraliza retry + backoff para operacoes de I/O em arquivos, com timeout total.
Evita falhas abruptas quando a rede oscila (ex.: compartilhamentos SMB).
"""

from __future__ import annotations

import os
import random
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, Optional, TypeVar, Union

T = TypeVar("T")

_logging_in_progress = False


def _log(msg: str, level: str = "INFO") -> None:
    global _logging_in_progress
    if _logging_in_progress:
        try:
            print(f"[NetworkIO][{level}] {msg}")
        except Exception:
            pass
        return

    try:
        _logging_in_progress = True
        from utils.logger import registrar_log

        registrar_log("NetworkIO", msg, level)
    except Exception:
        try:
            print(f"[NetworkIO][{level}] {msg}")
        except Exception:
            pass
    finally:
        _logging_in_progress = False


@dataclass(frozen=True)
class RetryPolicy:
    timeout_seconds: float = 6.0
    max_attempts: int = 4
    base_delay: float = 0.3
    max_delay: float = 1.5
    jitter: float = 0.1
    retry_on_missing: bool = True

    @staticmethod
    def from_env(prefix: str = "INTEGRAGAL_IO") -> "RetryPolicy":
        def _get_float(name: str, default: float) -> float:
            raw = os.getenv(f"{prefix}_{name}")
            if not raw:
                return default
            try:
                return float(raw)
            except Exception:
                return default

        def _get_int(name: str, default: int) -> int:
            raw = os.getenv(f"{prefix}_{name}")
            if not raw:
                return default
            try:
                return int(raw)
            except Exception:
                return default

        def _get_bool(name: str, default: bool) -> bool:
            raw = os.getenv(f"{prefix}_{name}")
            if raw is None:
                return default
            return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}

        return RetryPolicy(
            timeout_seconds=_get_float("TIMEOUT_SECONDS", 6.0),
            max_attempts=max(1, _get_int("MAX_ATTEMPTS", 4)),
            base_delay=max(0.0, _get_float("BASE_DELAY", 0.3)),
            max_delay=max(0.0, _get_float("MAX_DELAY", 1.5)),
            jitter=max(0.0, _get_float("JITTER", 0.1)),
            retry_on_missing=_get_bool("RETRY_ON_MISSING", True),
        )


def is_network_path(path: Union[str, Path, None]) -> bool:
    if not path:
        return False
    try:
        p = os.fspath(path)
    except Exception:
        return False
    # Heuristica: UNC path (Windows) ou caminhos iniciando com //
    return str(p).startswith("\\\\") or str(p).startswith("//")


def _should_retry(exc: Exception, path: Optional[Union[str, Path]], policy: RetryPolicy) -> bool:
    if isinstance(exc, FileNotFoundError):
        return policy.retry_on_missing or is_network_path(path)
    if isinstance(exc, (PermissionError, OSError, IOError, TimeoutError)):
        return True
    return False


def _compute_delay(attempt: int, policy: RetryPolicy) -> float:
    if attempt <= 1:
        base = policy.base_delay
    else:
        base = min(policy.base_delay * (2 ** (attempt - 1)), policy.max_delay)
    if policy.jitter > 0:
        base += random.uniform(0, policy.jitter)
    return max(0.0, base)


def call_with_retry(
    func: Callable[[], T],
    *,
    op_name: str,
    path: Optional[Union[str, Path]] = None,
    policy: Optional[RetryPolicy] = None,
) -> T:
    policy = policy or RetryPolicy.from_env()
    start = time.monotonic()
    attempt = 0
    last_exc: Optional[Exception] = None

    while True:
        attempt += 1
        try:
            return func()
        except Exception as exc:
            last_exc = exc
            if not _should_retry(exc, path, policy):
                raise
            elapsed = time.monotonic() - start
            if attempt >= policy.max_attempts or elapsed >= policy.timeout_seconds:
                _log(
                    f"Timeout ao executar '{op_name}' em {path}. "
                    f"Tentativas={attempt}, erro={type(exc).__name__}: {exc}",
                    "ERROR",
                )
                raise
            delay = _compute_delay(attempt, policy)
            _log(
                f"Falha em '{op_name}' (tentativa {attempt}) para {path}: "
                f"{type(exc).__name__}: {exc}. Retentando em {delay:.2f}s.",
                "WARNING",
            )
            time.sleep(delay)


def path_exists_with_retry(
    path: Union[str, Path],
    *,
    policy: Optional[RetryPolicy] = None,
) -> bool:
    policy = policy or RetryPolicy.from_env()
    start = time.monotonic()
    attempt = 0
    last_error: Optional[Exception] = None

    while True:
        attempt += 1
        try:
            if os.path.exists(path):
                return True
        except Exception as exc:
            last_error = exc

        elapsed = time.monotonic() - start
        if attempt >= policy.max_attempts or elapsed >= policy.timeout_seconds:
            if last_error:
                _log(
                    f"Falha ao verificar existencia de {path}: "
                    f"{type(last_error).__name__}: {last_error}",
                    "ERROR",
                )
            return False

        delay = _compute_delay(attempt, policy)
        time.sleep(delay)


@contextmanager
def open_with_retry(
    path: Union[str, Path],
    mode: str = "r",
    *,
    policy: Optional[RetryPolicy] = None,
    **kwargs,
) -> Iterator:
    target = os.fspath(path)

    def _do_open():
        return open(target, mode, **kwargs)

    f = call_with_retry(_do_open, op_name=f"open({mode})", path=target, policy=policy)
    try:
        yield f
    finally:
        try:
            f.close()
        except Exception:
            pass

