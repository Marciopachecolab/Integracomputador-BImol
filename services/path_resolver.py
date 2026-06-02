# services/path_resolver.py
"""Helpers para resolver paths sensiveis via config_service com fallback seguro.

Este modulo centraliza a resolucao de caminhos para arquivos compartilhados
(banco/usuarios.csv, catalogos, etc.) respeitando data_root/allowed_roots.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from services.core.config_service import config_service
from services.system_paths import BASE_DIR


def _safe_get_paths() -> dict:
    """Retorna paths do config_service com fallback para dict vazio."""
    try:
        return config_service.get_paths()
    except Exception:
        return {}


def resolve_banco_dir() -> Path:
    """Resolve o diretorio base de CSVs de cadastro (banco/)."""
    paths = _safe_get_paths()
    exams_catalog = paths.get("exams_catalog_csv")
    if exams_catalog:
        try:
            return Path(exams_catalog).parent
        except Exception:
            pass
    return Path(BASE_DIR) / "banco_runtime"


def resolve_users_csv_path() -> Path:
    """Resolve o caminho canonico de usuarios.csv."""
    paths = _safe_get_paths()
    for key in ("users_csv", "credentials_csv"):
        value = paths.get(key)
        if value:
            return Path(value)
    return resolve_banco_dir() / "usuarios.csv"


def resolve_credentials_csv_path(*, allow_same: bool = False) -> Optional[Path]:
    """Resolve o caminho do legado credenciais.csv quando diferente de usuarios.csv.

    Args:
        allow_same: Quando True, permite retornar o mesmo arquivo de users_csv.

    Returns:
        Path do credenciais.csv legado ou None quando nao aplicavel.
    """
    paths = _safe_get_paths()
    users_path = Path(paths.get("users_csv")) if paths.get("users_csv") else None

    cred_cfg = paths.get("credentials_csv")
    if cred_cfg:
        cred_path = Path(cred_cfg)
        if users_path is not None and cred_path.resolve() == users_path.resolve():
            return cred_path if allow_same else None
        if allow_same or users_path is None:
            return cred_path
        if cred_path.resolve() != users_path.resolve():
            return cred_path

    legacy = resolve_banco_dir() / "credenciais.csv"
    if legacy.exists():
        if allow_same:
            return legacy
        if users_path is None:
            return legacy
        if legacy.resolve() != users_path.resolve():
            return legacy

    return None
