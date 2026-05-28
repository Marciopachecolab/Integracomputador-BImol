# -*- coding: utf-8 -*-
"""Saude operacional e contingencia do visualizador tabular (F9)."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional

from config.feature_flags import feature_flags
from services.contract_preflight import resolve_runtime_environment
from utils.logger import registrar_log


@dataclass(frozen=True)
class AlertThresholds:
    """Limiares de alerta operacional por ambiente."""

    environment: str
    min_samples: int
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


def resolve_operational_thresholds(*, environment: Optional[str] = None) -> AlertThresholds:
    """Resolve limiares por ambiente com fallback seguro."""
    env = resolve_runtime_environment(explicit_env=environment)

    defaults = {
        "dev": {
            "min_samples": 10,
            "error_rate_warn": 0.35,
            "error_rate_critical": 0.50,
            "p95_warn_ms": 3000.0,
            "p95_critical_ms": 5000.0,
            "query_volume_warn": 3000,
            "query_volume_critical": 8000,
            "export_volume_warn": 800,
            "export_volume_critical": 2000,
        },
        "hml": {
            "min_samples": 15,
            "error_rate_warn": 0.20,
            "error_rate_critical": 0.35,
            "p95_warn_ms": 2200.0,
            "p95_critical_ms": 3500.0,
            "query_volume_warn": 2000,
            "query_volume_critical": 5000,
            "export_volume_warn": 500,
            "export_volume_critical": 1200,
        },
        "prod": {
            "min_samples": 20,
            "error_rate_warn": 0.10,
            "error_rate_critical": 0.20,
            "p95_warn_ms": 1500.0,
            "p95_critical_ms": 2500.0,
            "query_volume_warn": 1500,
            "query_volume_critical": 4000,
            "export_volume_warn": 300,
            "export_volume_critical": 900,
        },
    }
    base = defaults.get(env, defaults["dev"])

    return AlertThresholds(
        environment=env,
        min_samples=max(1, _env_int("INTEGRAGAL_OPVIEW_MIN_SAMPLES", base["min_samples"])),
        error_rate_warn=max(0.0, _env_float("INTEGRAGAL_OPVIEW_ERROR_RATE_WARN", base["error_rate_warn"])),
        error_rate_critical=max(0.0, _env_float("INTEGRAGAL_OPVIEW_ERROR_RATE_CRITICAL", base["error_rate_critical"])),
        p95_warn_ms=max(0.0, _env_float("INTEGRAGAL_OPVIEW_P95_WARN_MS", base["p95_warn_ms"])),
        p95_critical_ms=max(0.0, _env_float("INTEGRAGAL_OPVIEW_P95_CRITICAL_MS", base["p95_critical_ms"])),
        query_volume_warn=max(1, _env_int("INTEGRAGAL_OPVIEW_QUERY_VOLUME_WARN", base["query_volume_warn"])),
        query_volume_critical=max(1, _env_int("INTEGRAGAL_OPVIEW_QUERY_VOLUME_CRITICAL", base["query_volume_critical"])),
        export_volume_warn=max(1, _env_int("INTEGRAGAL_OPVIEW_EXPORT_VOLUME_WARN", base["export_volume_warn"])),
        export_volume_critical=max(1, _env_int("INTEGRAGAL_OPVIEW_EXPORT_VOLUME_CRITICAL", base["export_volume_critical"])),
    )


def _build_alert(*, severity: str, scope: str, metric: str, value: float, threshold: float, message: str) -> Dict[str, object]:
    return {
        "severity": severity,
        "scope": scope,
        "metric": metric,
        "value": value,
        "threshold": threshold,
        "message": message,
    }


def evaluate_operational_health(
    *,
    metrics: Dict[str, object],
    thresholds: Optional[AlertThresholds] = None,
    environment: Optional[str] = None,
) -> Dict[str, object]:
    """Avalia saude operacional e recomenda contingencia."""
    cfg = thresholds or resolve_operational_thresholds(environment=environment)
    alerts: List[Dict[str, object]] = []

    by_operation = metrics.get("by_operation", {}) if isinstance(metrics, dict) else {}
    by_view = metrics.get("by_view", {}) if isinstance(metrics, dict) else {}

    for op_name, payload in (by_operation.items() if isinstance(by_operation, dict) else []):
        if not isinstance(payload, dict):
            continue
        volume = int(payload.get("volume", 0) or 0)
        p95 = float(payload.get("p95_ms", 0.0) or 0.0)
        err = float(payload.get("error_rate", 0.0) or 0.0)

        if volume >= cfg.min_samples:
            if err >= cfg.error_rate_critical:
                alerts.append(
                    _build_alert(
                        severity="critical",
                        scope=f"operation:{op_name}",
                        metric="error_rate",
                        value=err,
                        threshold=cfg.error_rate_critical,
                        message=f"Taxa de erro critica em {op_name}.",
                    )
                )
            elif err >= cfg.error_rate_warn:
                alerts.append(
                    _build_alert(
                        severity="warning",
                        scope=f"operation:{op_name}",
                        metric="error_rate",
                        value=err,
                        threshold=cfg.error_rate_warn,
                        message=f"Taxa de erro elevada em {op_name}.",
                    )
                )

            if p95 >= cfg.p95_critical_ms:
                alerts.append(
                    _build_alert(
                        severity="critical",
                        scope=f"operation:{op_name}",
                        metric="p95_ms",
                        value=p95,
                        threshold=cfg.p95_critical_ms,
                        message=f"Latencia p95 critica em {op_name}.",
                    )
                )
            elif p95 >= cfg.p95_warn_ms:
                alerts.append(
                    _build_alert(
                        severity="warning",
                        scope=f"operation:{op_name}",
                        metric="p95_ms",
                        value=p95,
                        threshold=cfg.p95_warn_ms,
                        message=f"Latencia p95 elevada em {op_name}.",
                    )
                )

        if op_name == "operational_viewer.query":
            if volume >= cfg.query_volume_critical:
                alerts.append(
                    _build_alert(
                        severity="critical",
                        scope=f"operation:{op_name}",
                        metric="volume",
                        value=float(volume),
                        threshold=float(cfg.query_volume_critical),
                        message="Volume critico de consultas detectado.",
                    )
                )
            elif volume >= cfg.query_volume_warn:
                alerts.append(
                    _build_alert(
                        severity="warning",
                        scope=f"operation:{op_name}",
                        metric="volume",
                        value=float(volume),
                        threshold=float(cfg.query_volume_warn),
                        message="Volume elevado de consultas detectado.",
                    )
                )

        if op_name == "operational_viewer.export":
            if volume >= cfg.export_volume_critical:
                alerts.append(
                    _build_alert(
                        severity="critical",
                        scope=f"operation:{op_name}",
                        metric="volume",
                        value=float(volume),
                        threshold=float(cfg.export_volume_critical),
                        message="Volume critico de exportacoes detectado.",
                    )
                )
            elif volume >= cfg.export_volume_warn:
                alerts.append(
                    _build_alert(
                        severity="warning",
                        scope=f"operation:{op_name}",
                        metric="volume",
                        value=float(volume),
                        threshold=float(cfg.export_volume_warn),
                        message="Volume elevado de exportacoes detectado.",
                    )
                )

    for view_name, payload in (by_view.items() if isinstance(by_view, dict) else []):
        if not isinstance(payload, dict):
            continue
        volume = int(payload.get("volume", 0) or 0)
        if volume < cfg.min_samples:
            continue
        p95 = float(payload.get("p95_ms", 0.0) or 0.0)
        err = float(payload.get("error_rate", 0.0) or 0.0)
        if err >= cfg.error_rate_critical:
            alerts.append(
                _build_alert(
                    severity="critical",
                    scope=f"view:{view_name}",
                    metric="error_rate",
                    value=err,
                    threshold=cfg.error_rate_critical,
                    message=f"Taxa de erro critica na visao {view_name}.",
                )
            )
        elif err >= cfg.error_rate_warn:
            alerts.append(
                _build_alert(
                    severity="warning",
                    scope=f"view:{view_name}",
                    metric="error_rate",
                    value=err,
                    threshold=cfg.error_rate_warn,
                    message=f"Taxa de erro elevada na visao {view_name}.",
                )
            )

        if p95 >= cfg.p95_critical_ms:
            alerts.append(
                _build_alert(
                    severity="critical",
                    scope=f"view:{view_name}",
                    metric="p95_ms",
                    value=p95,
                    threshold=cfg.p95_critical_ms,
                    message=f"Latencia p95 critica na visao {view_name}.",
                )
            )

    critical_count = sum(1 for item in alerts if item.get("severity") == "critical")
    warning_count = sum(1 for item in alerts if item.get("severity") == "warning")

    if critical_count > 0:
        status = "critical"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "healthy"

    recommendations: List[str] = []
    if critical_count > 0:
        recommendations.append("Recomendar fallback imediato para modulo legado na consulta operacional.")
    if critical_count >= 2:
        recommendations.append("Recomendar rollback da feature flag USE_OPERATIONAL_TABULAR_VIEWER.")
    if status == "healthy":
        recommendations.append("Operacao estavel. Manter rollout gradual com monitoramento.")

    return {
        "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "environment": cfg.environment,
        "status": status,
        "alerts": alerts,
        "alert_count": len(alerts),
        "warning_count": warning_count,
        "critical_count": critical_count,
        "recommendations": recommendations,
        "can_recommend_fallback": critical_count > 0,
        "can_recommend_rollback": critical_count >= 2,
        "thresholds": asdict(cfg),
    }


def apply_operational_viewer_rollback(*, reason: str, actor: str = "", dry_run: bool = False) -> Dict[str, object]:
    """Aplica rollback da feature flag do visualizador operacional."""
    payload = {
        "performed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "flag": "USE_OPERATIONAL_TABULAR_VIEWER",
        "dry_run": bool(dry_run),
        "reason": str(reason or "").strip() or "rollback_f9",
        "actor": str(actor or "").strip(),
        "ok": True,
        "message": "",
    }

    if dry_run:
        payload["message"] = "Dry-run: rollback nao aplicado."
        return payload

    try:
        feature_flags.disable_flag("USE_OPERATIONAL_TABULAR_VIEWER")
        payload["message"] = "Rollback aplicado: flag desabilitada."
        registrar_log(
            "OperationalHealth",
            (
                "Rollback aplicado para visualizador operacional "
                f"actor={payload['actor']} reason={payload['reason']}"
            ),
            "WARNING",
        )
        return payload
    except Exception as exc:
        payload["ok"] = False
        payload["message"] = f"Falha ao aplicar rollback: {exc}"
        registrar_log("OperationalHealth", payload["message"], "ERROR")
        return payload


__all__ = [
    "AlertThresholds",
    "resolve_operational_thresholds",
    "evaluate_operational_health",
    "apply_operational_viewer_rollback",
]
