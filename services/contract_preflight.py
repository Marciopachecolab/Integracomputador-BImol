"""Preflight de contratos de runtime (fase 1 - B1-T03).

Politica padrao:
- dev: audit (nao bloqueante)
- hml/prod: enforce (bloqueante)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from services.core.config_service import config_service
from services.contract_catalog import ContractCatalog, get_contract_catalog
from utils.logger import registrar_log

_DEFAULT_PREFLIGHT_MODE_BY_ENV = {
    "dev": "audit",
    "hml": "enforce",
    "prod": "enforce",
}

_ENV_ALIASES = {
    "dev": "dev",
    "development": "dev",
    "local": "dev",
    "hml": "hml",
    "homolog": "hml",
    "homologacao": "hml",
    "staging": "hml",
    "stg": "hml",
    "qa": "hml",
    "test": "hml",
    "prod": "prod",
    "prd": "prod",
    "production": "prod",
}

_MODE_ALIASES = {
    "audit": "audit",
    "warn": "audit",
    "warning": "audit",
    "enforce": "enforce",
    "block": "enforce",
    "strict": "enforce",
}


@dataclass(frozen=True)
class ContractPreflightResult:
    environment: str
    mode: str
    issue_count: int


def _normalize_environment(value: Any) -> str:
    token = str(value or "").strip().lower()
    if not token:
        return "dev"
    return _ENV_ALIASES.get(token, "dev")


def _normalize_mode(value: Any) -> str:
    token = str(value or "").strip().lower()
    if not token:
        return "audit"
    return _MODE_ALIASES.get(token, "audit")


def resolve_runtime_environment(*, explicit_env: Any = None) -> str:
    """Resolve ambiente de runtime com fallback seguro para dev."""
    if explicit_env is not None:
        return _normalize_environment(explicit_env)

    raw_env = (
        os.getenv("INTEGRAGAL_ENV")
        or os.getenv("APP_ENV")
        or config_service.get("environment")
        or (config_service.get("contracts", {}) or {}).get("environment")
        or "dev"
    )
    return _normalize_environment(raw_env)


def resolve_preflight_mode(
    *,
    environment: str,
    explicit_mode: Any = None,
) -> str:
    """Resolve modo de preflight para o ambiente informado."""
    if explicit_mode is not None:
        return _normalize_mode(explicit_mode)

    mode_from_env = os.getenv("INTEGRAGAL_CONTRACT_PREFLIGHT_MODE")
    if mode_from_env:
        return _normalize_mode(mode_from_env)

    contracts_cfg = config_service.get("contracts", {}) or {}
    raw_mode_map = contracts_cfg.get("preflight_mode_by_env", {})
    mode_map: Dict[str, str] = {}
    if isinstance(raw_mode_map, dict):
        for key, value in raw_mode_map.items():
            mode_map[_normalize_environment(key)] = _normalize_mode(value)

    for env_name, default_mode in _DEFAULT_PREFLIGHT_MODE_BY_ENV.items():
        mode_map.setdefault(env_name, default_mode)

    return mode_map.get(environment, "audit")


def run_contract_preflight(
    *,
    catalog: Optional[ContractCatalog] = None,
    environment: Any = None,
    mode: Any = None,
) -> ContractPreflightResult:
    """Executa preflight dos contratos e aplica politica por ambiente."""
    resolved_env = resolve_runtime_environment(explicit_env=environment)
    resolved_mode = resolve_preflight_mode(environment=resolved_env, explicit_mode=mode)
    runtime_catalog = catalog or get_contract_catalog(reload=True)

    issues = runtime_catalog.validate_contract_files()
    issue_count = len(issues)

    if issue_count == 0:
        registrar_log(
            "ContractPreflight",
            f"Preflight de contratos aprovado (env={resolved_env}, mode={resolved_mode}).",
            "INFO",
        )
        return ContractPreflightResult(
            environment=resolved_env,
            mode=resolved_mode,
            issue_count=0,
        )

    summary = f"{issue_count} inconformidade(s) contratual(is)"
    preview = issues[0] if issues else {}
    registrar_log(
        "ContractPreflight",
        (
            f"Preflight detectou {summary} (env={resolved_env}, mode={resolved_mode}). "
            f"Primeiro problema: {preview}"
        ),
        "WARNING",
    )

    if resolved_mode == "enforce":
        raise RuntimeError(
            f"Preflight de contratos bloqueado em {resolved_env}: {summary}."
        )

    return ContractPreflightResult(
        environment=resolved_env,
        mode=resolved_mode,
        issue_count=issue_count,
    )
