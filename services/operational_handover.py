# -*- coding: utf-8 -*-
"""Handover operacional pre-producao (F12)."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import pandas as pd

from config.feature_flags import feature_flags
from services.legacy_audit.operational_slo_governance import (
    evaluate_slo_compliance,
    read_contingency_audit,
    resolve_operational_policy,
    summarize_sli_slo,
    validate_operational_policy,
)
from services.shared_paths import resolve_logs_dir as _shared_resolve_logs_dir
from services.operational_viewer_health import apply_operational_viewer_rollback
from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, open_with_retry, path_exists_with_retry

_HANDOVER_AUDIT_HEADERS = [
    "timestamp",
    "environment",
    "actor",
    "decision",
    "recommended_decision",
    "score",
    "severity",
    "violation_count",
    "dry_run",
    "feature_flag_action",
    "rollback_applied",
    "flag_enabled_after",
    "reason",
    "pending_count",
    "snapshot_json",
]


def _clamp_score(value: float) -> int:
    return int(max(0, min(100, round(value))))


def _resolve_logs_dir(logs_dir: Optional[str | Path]) -> Path:
    return _shared_resolve_logs_dir(logs_dir, use_config=False, default_dir="logs")


def get_handover_audit_path(*, logs_dir: Optional[str | Path] = None) -> Path:
    """Retorna caminho da auditoria de handover."""
    return _resolve_logs_dir(logs_dir) / "operational_handover_audit.csv"


def _latest_contingency_for_environment(*, logs_dir: Optional[str | Path], environment: str) -> Dict[str, object]:
    audit = read_contingency_audit(logs_dir=logs_dir, limit=500)
    if audit.empty:
        return {}
    env_mask = audit.get("environment", pd.Series(dtype=str)).astype(str).str.lower() == str(environment).lower()
    scoped = audit[env_mask].copy()
    if scoped.empty:
        return {}
    scoped["ts"] = pd.to_datetime(scoped.get("timestamp"), errors="coerce")
    scoped = scoped.sort_values(by=["ts"], ascending=True, na_position="last")
    row = scoped.iloc[-1]
    return {
        "timestamp": str(row.get("timestamp", "")),
        "severity": str(row.get("severity", "")),
        "action": str(row.get("action", "")),
        "rollback_applied": str(row.get("rollback_applied", "")).strip().lower() == "true",
        "message": str(row.get("message", "")),
    }


def evaluate_handover_readiness(
    *,
    logs_dir: Optional[str | Path] = None,
    environment: str,
    last_n: int = 10000,
) -> Dict[str, object]:
    """Avalia readiness operacional de um ambiente com score consolidado."""
    policy = resolve_operational_policy(environment=environment)
    validation = validate_operational_policy(policy=policy)
    summary = summarize_sli_slo(logs_dir=logs_dir, environment=policy.environment, last_n=last_n)
    compliance = evaluate_slo_compliance(summary=summary)

    severity = str(compliance.get("severity", "info"))
    violation_count = int(compliance.get("violation_count", 0) or 0)
    window = summary.get("window", {}) if isinstance(summary, dict) else {}
    requests = int(window.get("requests", 0) or 0)
    latest_contingency = _latest_contingency_for_environment(logs_dir=logs_dir, environment=policy.environment)

    pending: List[str] = []
    if requests < int(policy.min_samples):
        pending.append(
            f"Amostragem insuficiente na janela rolling ({requests} < {int(policy.min_samples)})."
        )
    if severity == "warning":
        pending.append("Ambiente em warning: calibrar limiares de latencia/erro antes de GO.")
    elif severity == "critical":
        pending.append("Ambiente em critical: bloquear GO e executar contingencia/rollback.")
    if not bool(validation.get("ok", False)):
        pending.append("Politica operacional inconsistente para auto-aplicacao.")

    for item in validation.get("warnings", []) if isinstance(validation, dict) else []:
        pending.append(f"Aviso de politica: {item}")

    score = 100.0
    if not bool(validation.get("ok", False)):
        score -= 50
    if severity == "critical":
        score -= 35
    elif severity == "warning":
        score -= 15
    score -= min(20, violation_count * 2)
    if requests < int(policy.min_samples):
        score -= 20

    if latest_contingency:
        if str(latest_contingency.get("severity", "")).lower() == "critical" and not bool(
            latest_contingency.get("rollback_applied", False)
        ):
            score -= 10
            pending.append("Ultima contingencia critica sem rollback aplicado.")

    score_int = _clamp_score(score)
    recommended_decision = (
        "go"
        if bool(validation.get("ok", False))
        and severity != "critical"
        and score_int >= 70
        and requests >= int(policy.min_samples)
        else "no-go"
    )

    return {
        "environment": policy.environment,
        "score": score_int,
        "recommended_decision": recommended_decision,
        "policy_state": asdict(policy),
        "validation": validation,
        "slo_status": {
            "severity": severity,
            "violation_count": violation_count,
            "critical_count": int(compliance.get("critical_count", 0) or 0),
            "warning_count": int(compliance.get("warning_count", 0) or 0),
            "window_requests": requests,
        },
        "latest_contingency": latest_contingency,
        "pending_calibrations": pending,
    }


def evaluate_handover_panel(
    *,
    logs_dir: Optional[str | Path] = None,
    environments: Sequence[str] = ("dev", "hml", "prod"),
    last_n: int = 10000,
) -> Dict[str, object]:
    """Gera painel consolidado de handover por ambiente."""
    env_rows: List[Dict[str, object]] = []
    for env in environments:
        row = evaluate_handover_readiness(
            logs_dir=logs_dir,
            environment=str(env),
            last_n=last_n,
        )
        env_rows.append(row)

    total = len(env_rows)
    avg_score = sum(int(item.get("score", 0) or 0) for item in env_rows) / total if total else 0.0
    ready_for_go = bool(total) and all(str(item.get("recommended_decision", "")) == "go" for item in env_rows)
    pending_total = sum(len(item.get("pending_calibrations", []) or []) for item in env_rows)

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "environments": env_rows,
        "overall": {
            "environment_count": total,
            "average_score": _clamp_score(avg_score),
            "ready_for_go": ready_for_go,
            "pending_total": int(pending_total),
        },
    }


def _ensure_handover_audit_file(path: Path, policy: RetryPolicy) -> None:
    if path_exists_with_retry(path, policy=policy):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with CSVFileLock(path):
        if path_exists_with_retry(path, policy=policy):
            return
        with open_with_retry(path, "w", newline="", encoding="utf-8", policy=policy) as handle:
            writer = csv.DictWriter(handle, fieldnames=_HANDOVER_AUDIT_HEADERS, delimiter=";")
            writer.writeheader()


def _append_handover_audit_row(*, logs_dir: Optional[str | Path], payload: Dict[str, object]) -> None:
    path = get_handover_audit_path(logs_dir=logs_dir)
    policy = RetryPolicy.from_env()
    _ensure_handover_audit_file(path, policy)
    with CSVFileLock(path):
        with open_with_retry(path, "a", newline="", encoding="utf-8", policy=policy) as handle:
            writer = csv.DictWriter(handle, fieldnames=_HANDOVER_AUDIT_HEADERS, delimiter=";")
            writer.writerow(payload)


def _is_operational_viewer_enabled() -> bool:
    status = feature_flags.get_flag_status("USE_OPERATIONAL_TABULAR_VIEWER")
    return bool((status or {}).get("enabled", False))


def apply_handover_decision(
    *,
    logs_dir: Optional[str | Path] = None,
    environment: str,
    actor: str,
    decision: Optional[str] = None,
    reason: str = "",
    dry_run: bool = False,
    last_n: int = 10000,
) -> Dict[str, object]:
    """Aplica decisao assistida de handover (go/no-go)."""
    readiness = evaluate_handover_readiness(
        logs_dir=logs_dir,
        environment=environment,
        last_n=last_n,
    )
    recommended = str(readiness.get("recommended_decision", "no-go"))
    normalized = str(decision or recommended).strip().lower()
    final_decision = "go" if normalized == "go" else "no-go"

    rollback_applied = False
    feature_flag_action = "none"

    if final_decision == "no-go":
        feature_flag_action = "rollback"
        rollback = apply_operational_viewer_rollback(
            reason=str(reason or "handover_no_go_f12"),
            actor=str(actor or ""),
            dry_run=bool(dry_run),
        )
        rollback_applied = bool(rollback.get("ok", False)) and not bool(rollback.get("dry_run", True))
    else:
        feature_flag_action = "enable_flag"
        if not bool(dry_run):
            feature_flags.enable_flag("USE_OPERATIONAL_TABULAR_VIEWER")

    flag_after = _is_operational_viewer_enabled()

    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "environment": str(readiness.get("environment", environment)),
        "actor": str(actor or ""),
        "decision": final_decision,
        "recommended_decision": recommended,
        "score": str(int(readiness.get("score", 0) or 0)),
        "severity": str((readiness.get("slo_status", {}) or {}).get("severity", "info")),
        "violation_count": str(int(((readiness.get("slo_status", {}) or {}).get("violation_count", 0) or 0))),
        "dry_run": str(bool(dry_run)).lower(),
        "feature_flag_action": feature_flag_action,
        "rollback_applied": str(bool(rollback_applied)).lower(),
        "flag_enabled_after": str(bool(flag_after)).lower(),
        "reason": str(reason or ""),
        "pending_count": str(len(readiness.get("pending_calibrations", []) or [])),
        "snapshot_json": json.dumps(readiness, ensure_ascii=False),
    }
    _append_handover_audit_row(logs_dir=logs_dir, payload=payload)

    return {
        "environment": str(readiness.get("environment", environment)),
        "decision": final_decision,
        "recommended_decision": recommended,
        "score": int(readiness.get("score", 0) or 0),
        "severity": str((readiness.get("slo_status", {}) or {}).get("severity", "info")),
        "dry_run": bool(dry_run),
        "feature_flag_action": feature_flag_action,
        "rollback_applied": bool(rollback_applied),
        "flag_enabled_after": bool(flag_after),
        "readiness": readiness,
    }


def read_handover_audit(*, logs_dir: Optional[str | Path] = None, limit: int = 200) -> pd.DataFrame:
    """Le trilha de auditoria de handover."""
    path = get_handover_audit_path(logs_dir=logs_dir)
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(path, policy=policy):
        return pd.DataFrame(columns=_HANDOVER_AUDIT_HEADERS)
    df = pd.read_csv(path, sep=";", encoding="utf-8")
    if int(limit or 0) > 0 and len(df) > int(limit):
        df = df.tail(int(limit)).reset_index(drop=True)
    return df


__all__ = [
    "get_handover_audit_path",
    "evaluate_handover_readiness",
    "evaluate_handover_panel",
    "apply_handover_decision",
    "read_handover_audit",
]
