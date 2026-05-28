"""
Bootstrap utilitario para modo single-window.

Fase 0:
- Introduz feature flag `UI_SINGLE_WINDOW`;
- Mantem rollback simples para bootstrap legado.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Mapping, Optional, Tuple, TypeVar

T = TypeVar("T")


def _coerce_bool(value: Any) -> Optional[bool]:
    """
    Converte valores comuns para bool.

    Returns:
        bool quando a conversao e suportada, ou None quando o valor e invalido.
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    return None


def resolve_single_window_enabled(
    config_get: Callable[[str, Any], Any],
    environ: Optional[Mapping[str, str]] = None,
) -> bool:
    """
    Resolve ativacao do modo single-window com precedencia previsivel.

    Ordem de precedencia:
    1. Variavel de ambiente `UI_SINGLE_WINDOW`
    2. `feature_flags.ui_single_window` no config
    3. chave legada `ui_single_window` no config
    4. default global `True` (fase 8)
    """
    env_map = dict(environ or os.environ)
    env_override = _coerce_bool(env_map.get("UI_SINGLE_WINDOW"))
    if env_override is not None:
        return env_override

    feature_flags = config_get("feature_flags", {})
    if isinstance(feature_flags, dict):
        from_feature_flags = _coerce_bool(feature_flags.get("ui_single_window"))
        if from_feature_flags is not None:
            return from_feature_flags

    from_legacy_key = _coerce_bool(config_get("ui_single_window", None))
    if from_legacy_key is not None:
        return bool(from_legacy_key)

    # Fase 8: single-window ativo por padrao para rollout global.
    # Rollback rapido continua disponivel via:
    # - env UI_SINGLE_WINDOW=0
    # - feature_flags.ui_single_window=false
    # - ui_single_window=false
    return True


def create_app_with_rollback(
    single_window_enabled: bool,
    create_single: Callable[[], T],
    create_legacy: Callable[[], T],
    on_rollback: Optional[Callable[[BaseException], None]] = None,
) -> Tuple[T, str]:
    """
    Cria app no modo selecionado com rollback para legado.

    Returns:
        Tupla (app, modo_resolvido), onde modo_resolvido e:
        - "single_window"
        - "legacy"
        - "legacy_rollback"
    """
    if not single_window_enabled:
        return create_legacy(), "legacy"

    try:
        return create_single(), "single_window"
    except Exception as exc:  # pragma: no cover - protegido por testes
        if on_rollback:
            on_rollback(exc)
        return create_legacy(), "legacy_rollback"
