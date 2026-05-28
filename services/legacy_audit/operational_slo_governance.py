# -*- coding: utf-8 -*-
"""Governanca SLO/SLI e automacao de resposta operacional (F10)."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

from services.contract_preflight import resolve_runtime_environment
from services.operational_viewer_health import resolve_operational_thresholds
from services.operational_viewer_health import apply_operational_viewer_rollback
from services.shared_paths import resolve_logs_dir as _shared_resolve_logs_dir
from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, open_with_retry, path_exists_with_retry
from utils.logger import registrar_log

_AUDIT_HEADERS = [
    "timestamp",
    "environment",
    "severity",
    "action",
    "dry_run",
    "rollback_applied",
    "violations",
    "message",
    "snapshot_json",
    "actor",
]

_READINESS_AUDIT_HEADERS = [
    "timestamp",
    "environment",
    "event_type",
    "severity",
    "action",
    "dry_run",
    "rollback_applied",
    "validation_ok",
    "message",
    "actor",
    "policy_json",
    "details_json",
]


@dataclass(frozen=True)
class SLOTargets:
    """Metas SLO/SLI por ambiente."""

    environment: str
    availability_min: float
    p95_max_ms: float
    p99_max_ms: float
    error_rate_max: float
    min_samples: int
    rolling_window_minutes: int
    baseline_lookback_minutes: int


@dataclass(frozen=True)
class OperationalPolicy:
    """Politica operacional unificada por ambiente (F11)."""

    environment: str
    auto_apply_enabled: bool
    dry_run_default: bool
    rollback_automatic_enabled: bool
    rollback_min_critical_violations: int
    warning_apply_mitigation: bool
    warning_page_size_cap: int
    rolling_window_minutes: int
    baseline_lookback_minutes: int
    min_samples: int
    availability_min: float
    p95_max_ms: float
    p99_max_ms: float
    error_rate_max: float
    error_rate_warn: float
    error_rate_critical: float
    p95_warn_ms: float
    p95_critical_ms: float
    query_volume_warn: int
    query_volume_critical: int
    export_volume_warn: int
    export_volume_critical: int


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return float(default)
    try:
        return float(raw)
    except Exception:
        return float(default)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return int(default)
    try:
        return int(raw)
    except Exception:
        return int(default)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return bool(default)
    return str(raw).strip().lower() in {"1", "true", "on", "yes"}


def _resolve_logs_dir(logs_dir: Optional[str | Path]) -> Path:
    return _shared_resolve_logs_dir(logs_dir)


def get_contingency_audit_path(*, logs_dir: Optional[str | Path] = None) -> Path:
    """Retorna caminho canonico da auditoria de contingencia."""
    return _resolve_logs_dir(logs_dir) / "operational_contingency_audit.csv"


def get_mitigation_state_path(*, logs_dir: Optional[str | Path] = None) -> Path:
    """Retorna caminho canonico do estado de mitigacao local."""
    return _resolve_logs_dir(logs_dir) / "operational_mitigation_state.json"


def get_readiness_audit_path(*, logs_dir: Optional[str | Path] = None) -> Path:
    """Retorna caminho canonico da auditoria consolidada de readiness."""
    return _resolve_logs_dir(logs_dir) / "operational_readiness_audit.csv"


def resolve_slo_targets(*, environment: Optional[str] = None) -> SLOTargets:
    """Resolve metas SLO com fallback seguro por ambiente."""
    env = resolve_runtime_environment(explicit_env=environment)
    defaults = {
        "dev": {
            "availability_min": 0.80,
            "p95_max_ms": 3000.0,
            "p99_max_ms": 5000.0,
            "error_rate_max": 0.20,
            "min_samples": 10,
            "rolling_window_minutes": 60,
            "baseline_lookback_minutes": 24 * 60,
        },
        "hml": {
            "availability_min": 0.90,
            "p95_max_ms": 2200.0,
            "p99_max_ms": 3500.0,
            "error_rate_max": 0.10,
            "min_samples": 15,
            "rolling_window_minutes": 60,
            "baseline_lookback_minutes": 24 * 60,
        },
        "prod": {
            "availability_min": 0.95,
            "p95_max_ms": 1500.0,
            "p99_max_ms": 2500.0,
            "error_rate_max": 0.05,
            "min_samples": 20,
            "rolling_window_minutes": 60,
            "baseline_lookback_minutes": 24 * 60,
        },
    }
    base = defaults.get(env, defaults["dev"])

    rolling_window_minutes = max(
        1,
        _env_int("INTEGRAGAL_OPVIEW_SLO_WINDOW_MINUTES", base["rolling_window_minutes"]),
    )
    baseline_lookback_minutes = max(
        rolling_window_minutes,
        _env_int("INTEGRAGAL_OPVIEW_SLO_BASELINE_MINUTES", base["baseline_lookback_minutes"]),
    )

    return SLOTargets(
        environment=env,
        availability_min=max(0.0, _env_float("INTEGRAGAL_OPVIEW_SLO_AVAILABILITY_MIN", base["availability_min"])),
        p95_max_ms=max(0.0, _env_float("INTEGRAGAL_OPVIEW_SLO_P95_MAX_MS", base["p95_max_ms"])),
        p99_max_ms=max(0.0, _env_float("INTEGRAGAL_OPVIEW_SLO_P99_MAX_MS", base["p99_max_ms"])),
        error_rate_max=max(0.0, _env_float("INTEGRAGAL_OPVIEW_SLO_ERROR_RATE_MAX", base["error_rate_max"])),
        min_samples=max(1, _env_int("INTEGRAGAL_OPVIEW_SLO_MIN_SAMPLES", base["min_samples"])),
        rolling_window_minutes=rolling_window_minutes,
        baseline_lookback_minutes=baseline_lookback_minutes,
    )


def resolve_operational_policy(*, environment: Optional[str] = None) -> OperationalPolicy:
    """Resolve politica operacional consolidada por ambiente."""
    slo = resolve_slo_targets(environment=environment)
    thresholds = resolve_operational_thresholds(environment=slo.environment)

    defaults = {
        "dev": {
            "auto_apply_enabled": False,
            "dry_run_default": True,
            "rollback_automatic_enabled": False,
            "rollback_min_critical_violations": 1,
            "warning_apply_mitigation": True,
            "warning_page_size_cap": 120,
        },
        "hml": {
            "auto_apply_enabled": True,
            "dry_run_default": False,
            "rollback_automatic_enabled": True,
            "rollback_min_critical_violations": 1,
            "warning_apply_mitigation": True,
            "warning_page_size_cap": 100,
        },
        "prod": {
            "auto_apply_enabled": True,
            "dry_run_default": False,
            "rollback_automatic_enabled": True,
            "rollback_min_critical_violations": 1,
            "warning_apply_mitigation": True,
            "warning_page_size_cap": 100,
        },
    }
    base = defaults.get(slo.environment, defaults["dev"])

    return OperationalPolicy(
        environment=slo.environment,
        auto_apply_enabled=_env_bool("INTEGRAGAL_OPVIEW_POLICY_AUTO_APPLY", base["auto_apply_enabled"]),
        dry_run_default=_env_bool("INTEGRAGAL_OPVIEW_POLICY_DRY_RUN_DEFAULT", base["dry_run_default"]),
        rollback_automatic_enabled=_env_bool(
            "INTEGRAGAL_OPVIEW_POLICY_ROLLBACK_AUTO_ENABLED",
            base["rollback_automatic_enabled"],
        ),
        rollback_min_critical_violations=max(
            1,
            _env_int(
                "INTEGRAGAL_OPVIEW_POLICY_ROLLBACK_MIN_CRITICAL",
                base["rollback_min_critical_violations"],
            ),
        ),
        warning_apply_mitigation=_env_bool(
            "INTEGRAGAL_OPVIEW_POLICY_WARNING_APPLY_MITIGATION",
            base["warning_apply_mitigation"],
        ),
        warning_page_size_cap=max(
            50,
            _env_int(
                "INTEGRAGAL_OPVIEW_POLICY_WARNING_PAGE_CAP",
                base["warning_page_size_cap"],
            ),
        ),
        rolling_window_minutes=slo.rolling_window_minutes,
        baseline_lookback_minutes=slo.baseline_lookback_minutes,
        min_samples=slo.min_samples,
        availability_min=slo.availability_min,
        p95_max_ms=slo.p95_max_ms,
        p99_max_ms=slo.p99_max_ms,
        error_rate_max=slo.error_rate_max,
        error_rate_warn=thresholds.error_rate_warn,
        error_rate_critical=thresholds.error_rate_critical,
        p95_warn_ms=thresholds.p95_warn_ms,
        p95_critical_ms=thresholds.p95_critical_ms,
        query_volume_warn=thresholds.query_volume_warn,
        query_volume_critical=thresholds.query_volume_critical,
        export_volume_warn=thresholds.export_volume_warn,
        export_volume_critical=thresholds.export_volume_critical,
    )


def validate_operational_policy(*, policy: OperationalPolicy) -> Dict[str, object]:
    """Valida consistencia da politica operacional por ambiente."""
    errors: List[str] = []
    warnings: List[str] = []

    if policy.auto_apply_enabled and policy.dry_run_default:
        errors.append("auto_apply_enabled=true e dry_run_default=true sao conflitantes.")
    if not policy.auto_apply_enabled and not policy.dry_run_default:
        warnings.append("auto_apply desabilitado com dry_run_default=false; forcar dry_run e recomendado.")

    if not (0.0 <= policy.availability_min <= 1.0):
        errors.append("availability_min deve estar no intervalo [0,1].")
    if policy.p95_max_ms <= 0 or policy.p99_max_ms <= 0:
        errors.append("p95_max_ms e p99_max_ms devem ser > 0.")
    if policy.p95_max_ms > policy.p99_max_ms:
        errors.append("p95_max_ms nao pode ser maior que p99_max_ms.")
    if policy.error_rate_max < 0 or policy.error_rate_max > 1:
        errors.append("error_rate_max deve estar no intervalo [0,1].")

    if policy.error_rate_warn >= policy.error_rate_critical:
        errors.append("error_rate_warn deve ser menor que error_rate_critical.")
    if policy.p95_warn_ms >= policy.p95_critical_ms:
        errors.append("p95_warn_ms deve ser menor que p95_critical_ms.")
    if policy.query_volume_warn >= policy.query_volume_critical:
        errors.append("query_volume_warn deve ser menor que query_volume_critical.")
    if policy.export_volume_warn >= policy.export_volume_critical:
        errors.append("export_volume_warn deve ser menor que export_volume_critical.")

    if policy.baseline_lookback_minutes < policy.rolling_window_minutes:
        errors.append("baseline_lookback_minutes deve ser >= rolling_window_minutes.")
    if policy.min_samples < 1:
        errors.append("min_samples deve ser >= 1.")
    if policy.rollback_min_critical_violations < 1:
        errors.append("rollback_min_critical_violations deve ser >= 1.")
    if policy.warning_page_size_cap < 50:
        errors.append("warning_page_size_cap deve ser >= 50.")

    if (not policy.rollback_automatic_enabled) and policy.auto_apply_enabled:
        warnings.append("rollback automatico desabilitado; contingencia critica dependera de acao manual.")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "policy": asdict(policy),
    }


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    if p <= 0:
        return values[0]
    if p >= 100:
        return values[-1]
    index = max(0, int(round((p / 100) * len(values) + 0.5)) - 1)
    return values[min(index, len(values) - 1)]


def _parse_meta(raw: object) -> Dict[str, object]:
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _calc_sli_entry(df: pd.DataFrame) -> Dict[str, float | int]:
    latencies = sorted(pd.to_numeric(df.get("duration_ms"), errors="coerce").dropna().tolist())
    count = int(len(df))
    errors = int(df.get("is_error", pd.Series(dtype=bool)).sum())
    err_rate = (errors / count) if count > 0 else 0.0
    return {
        "requests": count,
        "errors": errors,
        "error_rate": round(err_rate, 6),
        "availability": round(max(0.0, 1.0 - err_rate), 6),
        "p95_ms": round(_percentile(latencies, 95), 2),
        "p99_ms": round(_percentile(latencies, 99), 2),
    }


def _load_latency_df(*, logs_dir: Optional[str | Path], last_n: int) -> pd.DataFrame:
    path = _resolve_logs_dir(logs_dir) / "query_latency.csv"
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(path, policy=policy):
        return pd.DataFrame()
    try:
        with CSVFileLock(path):
            df = pd.read_csv(path, sep=";", encoding="utf-8")
    except Exception as exc:
        registrar_log("SLOGovernance", f"Falha ao ler query_latency.csv: {exc}", "WARNING")
        return pd.DataFrame()

    if int(last_n or 0) > 0 and len(df) > int(last_n):
        df = df.tail(int(last_n)).reset_index(drop=True)

    df = df[df.get("operation", pd.Series(dtype=str)).astype(str).str.startswith("operational_viewer.")].copy()
    if df.empty:
        return df

    df["timestamp_dt"] = pd.to_datetime(df.get("timestamp"), errors="coerce")
    df = df.dropna(subset=["timestamp_dt"]).reset_index(drop=True)
    df["meta_dict"] = df.get("meta", pd.Series(dtype=str)).map(_parse_meta)
    df["view"] = df["meta_dict"].map(lambda m: str(m.get("view", "") or "").strip() or "unknown")
    df["is_error"] = df["meta_dict"].map(lambda m: bool(str(m.get("error", "")).strip()))
    return df


def summarize_sli_slo(
    *,
    logs_dir: Optional[str | Path] = None,
    environment: Optional[str] = None,
    last_n: int = 10000,
) -> Dict[str, object]:
    """Resume SLI/SLO em janela rolling e baseline historico."""
    targets = resolve_slo_targets(environment=environment)
    df = _load_latency_df(logs_dir=logs_dir, last_n=last_n)
    if df.empty:
        return {
            "environment": targets.environment,
            "targets": asdict(targets),
            "window": {"requests": 0},
            "baseline": {"requests": 0},
            "operations": {},
            "views": {},
            "total_requests": 0,
        }

    now_ref = pd.to_datetime(df["timestamp_dt"]).max()
    window_start = now_ref - pd.Timedelta(minutes=int(targets.rolling_window_minutes))
    baseline_start = window_start - pd.Timedelta(minutes=int(targets.baseline_lookback_minutes))

    current = df[df["timestamp_dt"] >= window_start].copy()
    baseline = df[(df["timestamp_dt"] >= baseline_start) & (df["timestamp_dt"] < window_start)].copy()

    operations: Dict[str, Dict[str, object]] = {}
    for op_name, grp in current.groupby("operation"):
        current_entry = _calc_sli_entry(grp)
        base_grp = baseline[baseline["operation"] == op_name]
        base_entry = _calc_sli_entry(base_grp) if not base_grp.empty else {"requests": 0, "error_rate": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}
        operations[str(op_name)] = {
            "current": current_entry,
            "baseline": base_entry,
        }

    views: Dict[str, Dict[str, object]] = {}
    for view_name, grp in current.groupby("view"):
        current_entry = _calc_sli_entry(grp)
        base_grp = baseline[baseline["view"] == view_name]
        base_entry = _calc_sli_entry(base_grp) if not base_grp.empty else {"requests": 0, "error_rate": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}
        views[str(view_name)] = {
            "current": current_entry,
            "baseline": base_entry,
        }

    return {
        "environment": targets.environment,
        "targets": asdict(targets),
        "window": {
            "start": window_start.strftime("%Y-%m-%d %H:%M:%S"),
            "end": now_ref.strftime("%Y-%m-%d %H:%M:%S"),
            "requests": int(len(current)),
        },
        "baseline": {
            "start": baseline_start.strftime("%Y-%m-%d %H:%M:%S"),
            "end": window_start.strftime("%Y-%m-%d %H:%M:%S"),
            "requests": int(len(baseline)),
        },
        "operations": operations,
        "views": views,
        "total_requests": int(len(current)),
    }


def _build_violation(scope: str, metric: str, value: float, limit: float, severity: str, reason: str) -> Dict[str, object]:
    return {
        "scope": scope,
        "metric": metric,
        "value": value,
        "limit": limit,
        "severity": severity,
        "reason": reason,
    }


def evaluate_slo_compliance(*, summary: Dict[str, object]) -> Dict[str, object]:
    """Avalia conformidade SLO e classifica severidade global."""
    targets = summary.get("targets", {}) if isinstance(summary, dict) else {}
    min_samples = int(targets.get("min_samples", 1) or 1)
    availability_min = float(targets.get("availability_min", 0.0) or 0.0)
    p95_max = float(targets.get("p95_max_ms", 0.0) or 0.0)
    p99_max = float(targets.get("p99_max_ms", 0.0) or 0.0)
    error_rate_max = float(targets.get("error_rate_max", 0.0) or 0.0)

    violations: List[Dict[str, object]] = []

    def _check_scope(scope: str, payload: Dict[str, object]) -> None:
        current = payload.get("current", {}) if isinstance(payload, dict) else {}
        baseline = payload.get("baseline", {}) if isinstance(payload, dict) else {}
        requests = int(current.get("requests", 0) or 0)
        if requests < min_samples:
            return

        availability = float(current.get("availability", 1.0) or 1.0)
        p95 = float(current.get("p95_ms", 0.0) or 0.0)
        p99 = float(current.get("p99_ms", 0.0) or 0.0)
        err_rate = float(current.get("error_rate", 0.0) or 0.0)

        if availability < availability_min:
            severity = "critical" if availability < max(0.0, availability_min - 0.10) else "warning"
            violations.append(_build_violation(scope, "availability", availability, availability_min, severity, "SLO de disponibilidade violado"))

        if p95 > p95_max:
            severity = "critical" if p95 > (p95_max * 1.5) else "warning"
            violations.append(_build_violation(scope, "p95_ms", p95, p95_max, severity, "SLO de latencia p95 violado"))

        if p99 > p99_max:
            severity = "critical" if p99 > (p99_max * 1.5) else "warning"
            violations.append(_build_violation(scope, "p99_ms", p99, p99_max, severity, "SLO de latencia p99 violado"))

        if err_rate > error_rate_max:
            severity = "critical" if err_rate > (error_rate_max * 2) else "warning"
            violations.append(_build_violation(scope, "error_rate", err_rate, error_rate_max, severity, "SLO de taxa de erro violado"))

        base_requests = int(baseline.get("requests", 0) or 0)
        if base_requests >= min_samples:
            base_p95 = float(baseline.get("p95_ms", 0.0) or 0.0)
            base_err = float(baseline.get("error_rate", 0.0) or 0.0)
            if base_p95 > 0 and p95 > (base_p95 * 1.5):
                violations.append(_build_violation(scope, "p95_regression", p95, base_p95 * 1.5, "warning", "Regressao de p95 vs baseline"))
            if base_err >= 0 and err_rate > max(error_rate_max, base_err * 2):
                violations.append(_build_violation(scope, "error_regression", err_rate, max(error_rate_max, base_err * 2), "warning", "Regressao de erro vs baseline"))

    for op_name, payload in (summary.get("operations", {}) or {}).items():
        if isinstance(payload, dict):
            _check_scope(f"operation:{op_name}", payload)

    for view_name, payload in (summary.get("views", {}) or {}).items():
        if isinstance(payload, dict):
            _check_scope(f"view:{view_name}", payload)

    critical_count = sum(1 for item in violations if item.get("severity") == "critical")
    warning_count = sum(1 for item in violations if item.get("severity") == "warning")

    if critical_count > 0:
        severity = "critical"
    elif warning_count > 0:
        severity = "warning"
    else:
        severity = "info"

    return {
        "severity": severity,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "violations": violations,
        "violation_count": len(violations),
        "summary": summary,
    }


def _ensure_audit_file(path: Path, policy: RetryPolicy) -> None:
    if path_exists_with_retry(path, policy=policy):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with CSVFileLock(path):
        if path_exists_with_retry(path, policy=policy):
            return
        with open_with_retry(path, "w", newline="", encoding="utf-8", policy=policy) as handle:
            writer = csv.DictWriter(handle, fieldnames=_AUDIT_HEADERS, delimiter=";")
            writer.writeheader()


def _append_audit_row(
    *,
    logs_dir: Optional[str | Path],
    environment: str,
    severity: str,
    action: str,
    dry_run: bool,
    rollback_applied: bool,
    violations: int,
    message: str,
    snapshot: Dict[str, object],
    actor: str,
) -> None:
    path = get_contingency_audit_path(logs_dir=logs_dir)
    policy = RetryPolicy.from_env()
    _ensure_audit_file(path, policy)
    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "environment": environment,
        "severity": severity,
        "action": action,
        "dry_run": str(bool(dry_run)).lower(),
        "rollback_applied": str(bool(rollback_applied)).lower(),
        "violations": str(int(violations)),
        "message": str(message or ""),
        "snapshot_json": json.dumps(snapshot, ensure_ascii=False),
        "actor": str(actor or ""),
    }
    with CSVFileLock(path):
        with open_with_retry(path, "a", newline="", encoding="utf-8", policy=policy) as handle:
            writer = csv.DictWriter(handle, fieldnames=_AUDIT_HEADERS, delimiter=";")
            writer.writerow(payload)


def _save_local_mitigation_state(*, logs_dir: Optional[str | Path], page_size_cap: int, actor: str, reason: str) -> Dict[str, object]:
    path = get_mitigation_state_path(logs_dir=logs_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "page_size_cap": int(max(50, min(page_size_cap, 1000))),
        "actor": str(actor or ""),
        "reason": str(reason or ""),
    }
    policy = RetryPolicy.from_env()
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    with CSVFileLock(path):
        with open_with_retry(path, "w", encoding="utf-8", policy=policy) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    return payload


def run_slo_automation(
    *,
    logs_dir: Optional[str | Path] = None,
    environment: Optional[str] = None,
    actor: str = "",
    dry_run: Optional[bool] = None,
    last_n: int = 10000,
    auto_apply: Optional[bool] = None,
    auto_rollback_enabled: bool = True,
    auto_rollback_min_violations: int = 1,
    warning_apply_mitigation: bool = True,
    warning_page_size_cap: int = 100,
) -> Dict[str, object]:
    """Executa avaliacao SLO + automacao por severidade, com auditoria."""
    summary = summarize_sli_slo(logs_dir=logs_dir, environment=environment, last_n=last_n)
    compliance = evaluate_slo_compliance(summary=summary)
    severity = str(compliance.get("severity", "info"))
    resolved_env = str(summary.get("environment", resolve_runtime_environment(explicit_env=environment)))

    resolved_auto_apply = (
        str(os.getenv("INTEGRAGAL_OPVIEW_AUTO_RESPONSE_APPLY", "0")).strip().lower() in {"1", "true", "on", "yes"}
        if auto_apply is None
        else bool(auto_apply)
    )
    resolved_dry_run = (not resolved_auto_apply) if dry_run is None else bool(dry_run)

    action = "monitorar"
    message = "Operacao estavel."
    rollback_applied = False
    mitigation_state: Dict[str, object] = {}
    auto_rollback_min_violations = max(1, int(auto_rollback_min_violations or 1))

    if severity == "warning":
        action = "mitigacao_local"
        message = "Warning detectado: mitigacao local aplicada (cap de pagina)."
        if warning_apply_mitigation and not resolved_dry_run:
            mitigation_state = _save_local_mitigation_state(
                logs_dir=logs_dir,
                page_size_cap=warning_page_size_cap,
                actor=actor,
                reason="warning_slo",
            )
        elif not warning_apply_mitigation:
            action = "monitorar"
            message = "Warning detectado: mitigacao local desabilitada por politica."
    elif severity == "critical":
        violations = int(compliance.get("violation_count", 0) or 0)
        allow_auto_rollback = auto_rollback_enabled and (violations >= auto_rollback_min_violations)
        if allow_auto_rollback:
            action = "contingencia"
            message = "Critical detectado: recomendada contingencia e rollback da feature flag."
            rollback_result = apply_operational_viewer_rollback(
                reason="critical_slo_f10",
                actor=actor,
                dry_run=resolved_dry_run,
            )
            rollback_applied = bool(rollback_result.get("ok", False)) and not bool(rollback_result.get("dry_run", True))
            message = str(rollback_result.get("message", message))
        else:
            action = "contingencia_manual"
            message = (
                "Critical detectado: politica exige contingencia manual "
                "(rollback automatico desabilitado ou abaixo do limiar)."
            )

    snapshot = {
        "summary": summary,
        "compliance": {
            "severity": severity,
            "violation_count": int(compliance.get("violation_count", 0) or 0),
            "critical_count": int(compliance.get("critical_count", 0) or 0),
            "warning_count": int(compliance.get("warning_count", 0) or 0),
        },
    }

    try:
        _append_audit_row(
            logs_dir=logs_dir,
            environment=resolved_env,
            severity=severity,
            action=action,
            dry_run=resolved_dry_run,
            rollback_applied=rollback_applied,
            violations=int(compliance.get("violation_count", 0) or 0),
            message=message,
            snapshot=snapshot,
            actor=actor,
        )
    except Exception as exc:
        registrar_log("SLOGovernance", f"Falha ao registrar auditoria de contingencia: {exc}", "WARNING")

    return {
        "environment": resolved_env,
        "severity": severity,
        "action": action,
        "dry_run": resolved_dry_run,
        "rollback_applied": rollback_applied,
        "message": message,
        "summary": summary,
        "compliance": compliance,
        "mitigation_state": mitigation_state,
        "policy_context": {
            "auto_apply": bool(resolved_auto_apply),
            "auto_rollback_enabled": bool(auto_rollback_enabled),
            "auto_rollback_min_violations": int(auto_rollback_min_violations),
            "warning_apply_mitigation": bool(warning_apply_mitigation),
            "warning_page_size_cap": int(max(50, warning_page_size_cap)),
        },
    }


def read_contingency_audit(*, logs_dir: Optional[str | Path] = None, limit: int = 200) -> pd.DataFrame:
    """Le auditoria recente das decisoes de contingencia."""
    path = get_contingency_audit_path(logs_dir=logs_dir)
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(path, policy=policy):
        return pd.DataFrame(columns=_AUDIT_HEADERS)
    try:
        df = pd.read_csv(path, sep=";", encoding="utf-8")
    except Exception as exc:
        registrar_log("SLOGovernance", f"Falha ao ler auditoria de contingencia: {exc}", "WARNING")
        return pd.DataFrame(columns=_AUDIT_HEADERS)
    if int(limit or 0) > 0 and len(df) > int(limit):
        return df.tail(int(limit)).reset_index(drop=True)
    return df


def get_local_mitigation_state(*, logs_dir: Optional[str | Path] = None) -> Dict[str, object]:
    """Retorna estado atual de mitigacao local, se existir."""
    path = get_mitigation_state_path(logs_dir=logs_dir)
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(path, policy=policy):
        return {}
    try:
        with open_with_retry(path, "r", encoding="utf-8", policy=policy) as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _ensure_readiness_audit_file(path: Path, policy: RetryPolicy) -> None:
    if path_exists_with_retry(path, policy=policy):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with CSVFileLock(path):
        if path_exists_with_retry(path, policy=policy):
            return
        with open_with_retry(path, "w", newline="", encoding="utf-8", policy=policy) as handle:
            writer = csv.DictWriter(handle, fieldnames=_READINESS_AUDIT_HEADERS, delimiter=";")
            writer.writeheader()


def _append_readiness_audit_row(
    *,
    logs_dir: Optional[str | Path],
    environment: str,
    event_type: str,
    severity: str,
    action: str,
    dry_run: bool,
    rollback_applied: bool,
    validation_ok: bool,
    message: str,
    actor: str,
    policy_payload: Dict[str, object],
    details_payload: Dict[str, object],
) -> None:
    path = get_readiness_audit_path(logs_dir=logs_dir)
    policy = RetryPolicy.from_env()
    _ensure_readiness_audit_file(path, policy)
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "environment": str(environment or ""),
        "event_type": str(event_type or "").strip() or "readiness",
        "severity": str(severity or "info"),
        "action": str(action or "monitorar"),
        "dry_run": str(bool(dry_run)).lower(),
        "rollback_applied": str(bool(rollback_applied)).lower(),
        "validation_ok": str(bool(validation_ok)).lower(),
        "message": str(message or ""),
        "actor": str(actor or ""),
        "policy_json": json.dumps(policy_payload or {}, ensure_ascii=False),
        "details_json": json.dumps(details_payload or {}, ensure_ascii=False),
    }
    with CSVFileLock(path):
        with open_with_retry(path, "a", newline="", encoding="utf-8", policy=policy) as handle:
            writer = csv.DictWriter(handle, fieldnames=_READINESS_AUDIT_HEADERS, delimiter=";")
            writer.writerow(row)


def read_readiness_audit(*, logs_dir: Optional[str | Path] = None, limit: int = 200) -> pd.DataFrame:
    """Le auditoria de readiness operacional (F11)."""
    path = get_readiness_audit_path(logs_dir=logs_dir)
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(path, policy=policy):
        return pd.DataFrame(columns=_READINESS_AUDIT_HEADERS)
    try:
        df = pd.read_csv(path, sep=";", encoding="utf-8")
    except Exception as exc:
        registrar_log("SLOGovernance", f"Falha ao ler readiness audit: {exc}", "WARNING")
        return pd.DataFrame(columns=_READINESS_AUDIT_HEADERS)
    if int(limit or 0) > 0 and len(df) > int(limit):
        return df.tail(int(limit)).reset_index(drop=True)
    return df


def read_consolidated_operational_audit(*, logs_dir: Optional[str | Path] = None, limit: int = 300) -> pd.DataFrame:
    """Consolida trilha de auditoria SLO + readiness em formato unico."""
    contingency = read_contingency_audit(logs_dir=logs_dir, limit=max(1, int(limit or 300)))
    readiness = read_readiness_audit(logs_dir=logs_dir, limit=max(1, int(limit or 300)))

    rows: List[Dict[str, object]] = []

    for _, row in contingency.fillna("").iterrows():
        rows.append(
            {
                "timestamp": str(row.get("timestamp", "")),
                "environment": str(row.get("environment", "")),
                "source": "contingency",
                "event_type": "slo_automation",
                "severity": str(row.get("severity", "")),
                "action": str(row.get("action", "")),
                "dry_run": str(row.get("dry_run", "")),
                "rollback_applied": str(row.get("rollback_applied", "")),
                "message": str(row.get("message", "")),
                "actor": str(row.get("actor", "")),
                "payload_json": str(row.get("snapshot_json", "")),
            }
        )

    for _, row in readiness.fillna("").iterrows():
        rows.append(
            {
                "timestamp": str(row.get("timestamp", "")),
                "environment": str(row.get("environment", "")),
                "source": "readiness",
                "event_type": str(row.get("event_type", "")),
                "severity": str(row.get("severity", "")),
                "action": str(row.get("action", "")),
                "dry_run": str(row.get("dry_run", "")),
                "rollback_applied": str(row.get("rollback_applied", "")),
                "message": str(row.get("message", "")),
                "actor": str(row.get("actor", "")),
                "payload_json": str(row.get("details_json", "")),
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "timestamp",
                "environment",
                "source",
                "event_type",
                "severity",
                "action",
                "dry_run",
                "rollback_applied",
                "message",
                "actor",
                "payload_json",
            ]
        )

    merged = pd.DataFrame(rows)
    merged["timestamp_dt"] = pd.to_datetime(merged["timestamp"], errors="coerce")
    merged = merged.sort_values(by=["timestamp_dt"], ascending=True, na_position="last").drop(columns=["timestamp_dt"])
    if int(limit or 0) > 0 and len(merged) > int(limit):
        merged = merged.tail(int(limit)).reset_index(drop=True)
    return merged


def build_operational_runbook(
    *,
    severity: str,
    action: str,
    rollback_applied: bool,
    validation_ok: bool,
) -> Dict[str, object]:
    """Gera runbook executavel de resposta a incidentes warning/critical."""
    sev = str(severity or "info").strip().lower()
    act = str(action or "monitorar").strip().lower()
    steps: List[Dict[str, str]] = []

    steps.append({"step": "validar_painel", "instruction": "Conferir status de saude e SLO no painel operacional."})
    steps.append({"step": "confirmar_logs", "instruction": "Confirmar eventos recentes em query_latency.csv e trilhas de auditoria."})

    if not validation_ok:
        steps.append({"step": "corrigir_config", "instruction": "Interromper auto-aplicacao e corrigir inconsistencias de politica."})

    if sev == "warning":
        steps.extend(
            [
                {"step": "mitigacao_local", "instruction": "Aplicar cap de paginacao e reduzir escopo de consulta/exportacao."},
                {"step": "reavaliar_15m", "instruction": "Reavaliar indicadores apos 15 minutos."},
            ]
        )
    elif sev == "critical":
        steps.extend(
            [
                {"step": "contingencia", "instruction": "Ativar contingencia operacional e priorizar fluxo legado."},
                {
                    "step": "rollback_flag",
                    "instruction": (
                        "Aplicar rollback da feature flag se nao aplicado automaticamente."
                        if not rollback_applied
                        else "Rollback da feature flag ja aplicado automaticamente."
                    ),
                },
                {"step": "comunicar_turno", "instruction": "Registrar incidente e comunicar equipe de plantao."},
            ]
        )
    else:
        steps.append({"step": "monitorar", "instruction": "Manter monitoramento com janela rolling ativa."})

    return {
        "severity": sev,
        "action": act,
        "steps": steps,
        "total_steps": len(steps),
    }


def run_operational_readiness(
    *,
    logs_dir: Optional[str | Path] = None,
    environment: Optional[str] = None,
    actor: str = "",
    dry_run: Optional[bool] = None,
    last_n: int = 10000,
) -> Dict[str, object]:
    """Executa readiness operacional F11 (politica + validacao + acao + auditoria)."""
    policy = resolve_operational_policy(environment=environment)
    validation = validate_operational_policy(policy=policy)
    validation_ok = bool(validation.get("ok", False))

    resolved_dry_run = bool(dry_run) if dry_run is not None else (policy.dry_run_default or (not policy.auto_apply_enabled))

    if not validation_ok:
        message = "Politica operacional invalida: auto-aplicacao bloqueada."
        runbook = build_operational_runbook(
            severity="critical",
            action="bloqueio_configuracao",
            rollback_applied=False,
            validation_ok=False,
        )
        result = {
            "ok": False,
            "environment": policy.environment,
            "policy": asdict(policy),
            "validation": validation,
            "dry_run": True,
            "automation": {},
            "runbook": runbook,
            "message": message,
        }
        try:
            _append_readiness_audit_row(
                logs_dir=logs_dir,
                environment=policy.environment,
                event_type="policy_validation_failed",
                severity="critical",
                action="bloqueio_configuracao",
                dry_run=True,
                rollback_applied=False,
                validation_ok=False,
                message=message,
                actor=actor,
                policy_payload=asdict(policy),
                details_payload={"validation": validation, "runbook": runbook},
            )
        except Exception as exc:
            registrar_log("SLOGovernance", f"Falha ao registrar readiness audit: {exc}", "WARNING")
        return result

    automation = run_slo_automation(
        logs_dir=logs_dir,
        environment=policy.environment,
        actor=actor,
        dry_run=resolved_dry_run,
        last_n=last_n,
        auto_apply=policy.auto_apply_enabled,
        auto_rollback_enabled=policy.rollback_automatic_enabled,
        auto_rollback_min_violations=policy.rollback_min_critical_violations,
        warning_apply_mitigation=policy.warning_apply_mitigation,
        warning_page_size_cap=policy.warning_page_size_cap,
    )
    severity = str(automation.get("severity", "info"))
    action = str(automation.get("action", "monitorar"))
    rollback_applied = bool(automation.get("rollback_applied", False))
    runbook = build_operational_runbook(
        severity=severity,
        action=action,
        rollback_applied=rollback_applied,
        validation_ok=True,
    )
    message = str(automation.get("message", "Readiness executado."))

    result = {
        "ok": True,
        "environment": policy.environment,
        "policy": asdict(policy),
        "validation": validation,
        "dry_run": bool(resolved_dry_run),
        "automation": automation,
        "runbook": runbook,
        "message": message,
    }

    try:
        _append_readiness_audit_row(
            logs_dir=logs_dir,
            environment=policy.environment,
            event_type="readiness_run",
            severity=severity,
            action=action,
            dry_run=bool(resolved_dry_run),
            rollback_applied=rollback_applied,
            validation_ok=True,
            message=message,
            actor=actor,
            policy_payload=asdict(policy),
            details_payload={
                "validation": validation,
                "automation": {
                    "severity": severity,
                    "action": action,
                    "violation_count": int((automation.get("compliance", {}) or {}).get("violation_count", 0) or 0),
                },
                "runbook": runbook,
            },
        )
    except Exception as exc:
        registrar_log("SLOGovernance", f"Falha ao registrar readiness audit: {exc}", "WARNING")

    return result


__all__ = [
    "SLOTargets",
    "OperationalPolicy",
    "resolve_slo_targets",
    "resolve_operational_policy",
    "validate_operational_policy",
    "summarize_sli_slo",
    "evaluate_slo_compliance",
    "run_slo_automation",
    "run_operational_readiness",
    "build_operational_runbook",
    "read_contingency_audit",
    "read_readiness_audit",
    "read_consolidated_operational_audit",
    "get_local_mitigation_state",
    "get_contingency_audit_path",
    "get_mitigation_state_path",
    "get_readiness_audit_path",
]
