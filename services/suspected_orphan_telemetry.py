"""Telemetria de uso para funcoes suspeitas de orfandade."""

from __future__ import annotations

import time
from threading import Lock
from typing import Any

from utils.logger import registrar_log

_LOCK = Lock()
_LAST_EMIT_BY_FUNCTION: dict[str, float] = {}


def log_suspected_orphan_usage(
    function_name: str,
    *,
    event: str = "invoked",
    throttle_seconds: float = 300.0,
    **payload: Any,
) -> None:
    """Registra evento de uso runtime para funcao suspeita.

    O throttle evita ruido excessivo em funcoes potencialmente chamadas em lote.
    """
    now = time.monotonic()
    with _LOCK:
        last_emit = _LAST_EMIT_BY_FUNCTION.get(function_name, 0.0)
        if now - last_emit < float(throttle_seconds):
            return
        _LAST_EMIT_BY_FUNCTION[function_name] = now

    parts = [
        "feature=suspected_orphan",
        f"function={function_name}",
        f"event={event}",
    ]
    for key, value in payload.items():
        parts.append(f"{key}={value}")
    registrar_log("RuntimeUsage", " ".join(parts), "INFO")
