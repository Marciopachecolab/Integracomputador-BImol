from __future__ import annotations

from pathlib import Path
from typing import Optional

from services.core.config_service import config_service


def resolve_logs_dir(
    logs_dir: Optional[str | Path],
    *,
    fallback_file_key: str = "gal_history_csv",
    default_dir: str | Path = "logs",
    use_config: bool = True,
) -> Path:
    """Resolve logs directory using explicit path, config, and deterministic fallback."""
    if logs_dir:
        return Path(logs_dir)
    if not use_config:
        return Path(default_dir)
    try:
        paths = config_service.get_paths()
    except Exception:
        paths = {}
    target = paths.get("logs_dir")
    if target:
        return Path(target)
    fallback_ref = paths.get(fallback_file_key, str(Path(default_dir) / "historico_analises.csv"))
    return Path(fallback_ref).parent


__all__ = ["resolve_logs_dir"]
