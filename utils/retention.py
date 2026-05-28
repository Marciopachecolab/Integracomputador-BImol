"""
Rotinas de retencao e rotacao de arquivos de logs e relatorios.

Politica padrao:
- Logs e historicos: 180 dias
- Relatorios (reports/relatorios): 365 dias
- Rotacao do log principal por tamanho (default 50 MB)

Os valores podem ser ajustados em config.json (chave "retencao").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from services.core.config_service import config_service
from services.system_paths import BASE_DIR
from utils.logger import registrar_log


MB_BYTES = 1024 * 1024


@dataclass
class RetentionPolicy:
    """Configuracao de retencao/rotacao."""

    enabled: bool
    logs_days: int
    reports_days: int
    relatorios_days: int
    logs_max_total_mb: int
    reports_max_total_mb: int
    relatorios_max_total_mb: int
    log_file_max_mb: int


@dataclass
class RetentionResult:
    """Resumo de execucao de retencao."""

    removed: List[Path]
    kept: int
    total_before_mb: float
    total_after_mb: float
    rotated_logs: List[Path]
    errors: List[str]


def _parse_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_policy() -> RetentionPolicy:
    cfg = config_service.get("retencao", {}) or {}
    return RetentionPolicy(
        enabled=bool(cfg.get("ativada", True)),
        logs_days=_parse_int(cfg.get("logs_dias", 180), 180),
        reports_days=_parse_int(cfg.get("reports_dias", 365), 365),
        relatorios_days=_parse_int(cfg.get("relatorios_dias", 365), 365),
        logs_max_total_mb=_parse_int(cfg.get("logs_max_total_mb", 512), 512),
        reports_max_total_mb=_parse_int(cfg.get("reports_max_total_mb", 2048), 2048),
        relatorios_max_total_mb=_parse_int(cfg.get("relatorios_max_total_mb", 2048), 2048),
        log_file_max_mb=_parse_int(cfg.get("log_file_max_mb", 50), 50),
    )


def _to_abs(path_value: Optional[str]) -> Optional[Path]:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_absolute():
        return Path(BASE_DIR) / path
    return path


def _unique_paths(items: Iterable[Optional[Path]]) -> List[Path]:
    seen = set()
    result = []
    for item in items:
        if not item:
            continue
        try:
            resolved = item.resolve()
        except Exception:
            resolved = item
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _collect_dirs() -> Dict[str, List[Path]]:
    paths = config_service.get_paths()
    export_cfg = config_service.get("exportacao", {}) or {}

    log_file = _to_abs(paths.get("log_file"))
    logs_dir = _to_abs(paths.get("logs_dir")) or (
        log_file.parent if log_file else Path(BASE_DIR) / "logs"
    )
    historicos_dir = _to_abs(paths.get("historicos_dir"))

    reports_dir = _to_abs(paths.get("reports_dir"))
    default_results = _to_abs(paths.get("default_results_folder"))
    export_dir = _to_abs(export_cfg.get("diretorio_padrao"))
    fallback_reports = Path(BASE_DIR) / "reports"

    relatorios_dir = Path(BASE_DIR) / "relatorios"

    logs_dirs = _unique_paths([logs_dir, historicos_dir])
    reports_dirs = _unique_paths([reports_dir, default_results, export_dir, fallback_reports])

    return {
        "logs": logs_dirs,
        "reports": reports_dirs,
        "relatorios": _unique_paths([relatorios_dir]),
        "log_file": [log_file] if log_file else [],
    }


def _iter_files(directory: Path) -> List[Path]:
    if not directory.exists():
        return []
    return [p for p in directory.rglob("*") if p.is_file()]


def _total_size_mb(files: Iterable[Path]) -> float:
    total = 0
    for file_path in files:
        try:
            total += file_path.stat().st_size
        except OSError:
            continue
    return total / MB_BYTES


def _remove_files(files: Iterable[Path], removed: List[Path], errors: List[str]) -> None:
    for file_path in files:
        try:
            file_path.unlink(missing_ok=True)
            removed.append(file_path)
        except OSError as exc:
            errors.append(f"Falha ao remover {file_path}: {exc}")


def _rotate_log_file(log_file: Path, max_mb: int, rotated: List[Path], errors: List[str]) -> None:
    if max_mb <= 0 or not log_file.exists():
        return
    try:
        size_mb = log_file.stat().st_size / MB_BYTES
        if size_mb < max_mb:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_path = log_file.with_name(f"{log_file.stem}_{timestamp}{log_file.suffix}")
        log_file.rename(rotated_path)
        rotated.append(rotated_path)
    except OSError as exc:
        errors.append(f"Falha ao rotacionar {log_file}: {exc}")


def _apply_retention(
    directory: Path,
    retention_days: int,
    max_total_mb: int,
    removed: List[Path],
    errors: List[str],
) -> Tuple[int, float, float]:
    files = _iter_files(directory)
    total_before_mb = _total_size_mb(files)

    if retention_days > 0:
        cutoff = datetime.now() - timedelta(days=retention_days)
        to_remove_by_age = [f for f in files if datetime.fromtimestamp(f.stat().st_mtime) < cutoff]
        _remove_files(to_remove_by_age, removed, errors)

    files = _iter_files(directory)
    if max_total_mb > 0:
        total_mb = _total_size_mb(files)
        if total_mb > max_total_mb:
            files_sorted = sorted(files, key=lambda p: p.stat().st_mtime)
            while files_sorted and total_mb > max_total_mb:
                target = files_sorted.pop(0)
                _remove_files([target], removed, errors)
                total_mb = _total_size_mb(files_sorted)

    total_after_mb = _total_size_mb(_iter_files(directory))
    return len(_iter_files(directory)), total_before_mb, total_after_mb


def executar_retencao() -> RetentionResult:
    """Executa retencao/rotacao conforme politica configurada."""
    policy = _get_policy()
    removed: List[Path] = []
    rotated: List[Path] = []
    errors: List[str] = []

    if not policy.enabled:
        registrar_log("Retencao", "Retencao desativada em config.json.", "INFO")
        return RetentionResult([], 0, 0.0, 0.0, [], [])

    dirs = _collect_dirs()

    for log_file in dirs["log_file"]:
        _rotate_log_file(log_file, policy.log_file_max_mb, rotated, errors)

    kept_total = 0
    total_before = 0.0
    total_after = 0.0

    for directory in dirs["logs"]:
        kept, before_mb, after_mb = _apply_retention(
            directory,
            policy.logs_days,
            policy.logs_max_total_mb,
            removed,
            errors,
        )
        kept_total += kept
        total_before += before_mb
        total_after += after_mb

    for directory in dirs["reports"]:
        kept, before_mb, after_mb = _apply_retention(
            directory,
            policy.reports_days,
            policy.reports_max_total_mb,
            removed,
            errors,
        )
        kept_total += kept
        total_before += before_mb
        total_after += after_mb

    for directory in dirs["relatorios"]:
        kept, before_mb, after_mb = _apply_retention(
            directory,
            policy.relatorios_days,
            policy.relatorios_max_total_mb,
            removed,
            errors,
        )
        kept_total += kept
        total_before += before_mb
        total_after += after_mb

    registrar_log(
        "Retencao",
        f"Retencao executada. Removidos={len(removed)}, Rotacionados={len(rotated)}.",
        "INFO",
    )
    return RetentionResult(removed, kept_total, total_before, total_after, rotated, errors)


def format_retention_summary(result: RetentionResult) -> str:
    """Gera resumo legivel da execucao de retencao."""
    lines = [
        f"Arquivos removidos: {len(result.removed)}",
        f"Arquivos rotacionados: {len(result.rotated_logs)}",
        f"Tamanho total antes: {result.total_before_mb:.2f} MB",
        f"Tamanho total depois: {result.total_after_mb:.2f} MB",
        f"Arquivos mantidos: {result.kept}",
    ]
    if result.errors:
        lines.append("Erros: " + "; ".join(result.errors[:5]))
    return "\n".join(lines)
