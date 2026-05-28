"""Observabilidade da execucao de regras da analise (paridade + SLO)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


REPORT_PREFIX = "0260325_analysis_runtime_parity"
GATE_PREFIX = "0260325_analysis_runtime_promotion_gate"


def _norm_text(value: str) -> str:
    import unicodedata

    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    return text.encode("ascii", "ignore").decode("ascii")


def _norm_status(value: str) -> str:
    normalized = _norm_text(value)
    if "detect" in normalized and "nao" not in normalized:
        return "detectavel"
    if "indeterm" in normalized or "inconcl" in normalized:
        return "indeterminado"
    if "nao detect" in normalized:
        return "nao_detectavel"
    return normalized or "vazio"


def _percentile(values: Iterable[float], percentile: float) -> float:
    ordered = sorted(float(v) for v in values if v is not None)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    pos = max(0.0, min(100.0, percentile)) / 100.0 * (len(ordered) - 1)
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return ordered[low]
    weight = pos - low
    return (ordered[low] * (1.0 - weight)) + (ordered[high] * weight)


def build_runtime_parity_report(
    *,
    exame: str,
    route_mode: str,
    elapsed_ms: float,
    latency_samples_ms: Iterable[float],
    p95_target_ms: float,
    comparisons: Iterable[Dict[str, str]],
) -> Dict[str, object]:
    by_target: Dict[str, Dict[str, Dict[str, int]]] = {}
    critical: List[Dict[str, str]] = []
    total = 0

    for row in comparisons:
        target = str(row.get("target", "")).strip() or "UNKNOWN"
        legacy = str(row.get("legacy_status", "")).strip()
        canonical = str(row.get("canonical_status", "")).strip()
        total += 1

        target_bucket = by_target.setdefault(target, {"legacy": {}, "canonical": {}})
        legacy_key = _norm_status(legacy)
        canonical_key = _norm_status(canonical)
        target_bucket["legacy"][legacy_key] = target_bucket["legacy"].get(legacy_key, 0) + 1
        target_bucket["canonical"][canonical_key] = target_bucket["canonical"].get(canonical_key, 0) + 1

        if legacy_key != canonical_key:
            critical.append(
                {
                    "target": target,
                    "legacy_status": legacy,
                    "canonical_status": canonical,
                    "ct": str(row.get("ct", "")),
                }
            )

    samples = [float(v) for v in latency_samples_ms]
    p95_latency = _percentile(samples, 95.0)
    p95_ok = p95_latency <= float(p95_target_ms)
    parity_ok = len(critical) == 0

    return {
        "report_id": REPORT_PREFIX,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "exame": str(exame or ""),
        "route_mode": route_mode,
        "slo": {
            "p95_target_ms": float(p95_target_ms),
            "p95_latency_ms": round(p95_latency, 3),
            "last_execution_ms": round(float(elapsed_ms), 3),
            "p95_within_target": bool(p95_ok),
        },
        "totals": {
            "samples_compared": total,
            "critical_divergences": len(critical),
        },
        "by_target_status": by_target,
        "critical_divergences": critical,
        "is_parity_ok": bool(parity_ok),
        "overall_ok": bool(parity_ok and p95_ok),
    }


def persist_runtime_parity_report(
    report: Dict[str, object],
    *,
    reports_dir: Path | None = None,
) -> Path:
    root = reports_dir or Path("reports")
    root.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    run_file = root / f"{REPORT_PREFIX}_{stamp}.json"
    latest_file = root / f"{REPORT_PREFIX}_latest.json"
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    run_file.write_text(payload, encoding="utf-8")
    latest_file.write_text(payload, encoding="utf-8")
    return run_file


def build_runtime_promotion_gate(
    *,
    parity_report: Dict[str, object],
    error_count: int = 0,
    max_critical_divergences: int = 0,
    max_error_rate: float = 0.0,
) -> Dict[str, object]:
    totals = parity_report.get("totals", {}) if isinstance(parity_report, dict) else {}
    slo = parity_report.get("slo", {}) if isinstance(parity_report, dict) else {}

    compared = int(totals.get("samples_compared", 0) or 0)
    critical_divergences = int(totals.get("critical_divergences", 0) or 0)
    errors = max(0, int(error_count or 0))
    denominator = compared if compared > 0 else (errors if errors > 0 else 1)
    error_rate = float(errors / denominator)
    p95_within_target = bool(slo.get("p95_within_target", False))

    checks = [
        {
            "metric": "critical_divergences",
            "value": critical_divergences,
            "threshold": f"<= {int(max_critical_divergences)}",
            "ok": critical_divergences <= int(max_critical_divergences),
        },
        {
            "metric": "p95_within_target",
            "value": p95_within_target,
            "threshold": "true",
            "ok": p95_within_target,
        },
        {
            "metric": "error_rate",
            "value": round(error_rate, 6),
            "threshold": f"<= {float(max_error_rate):.6f}",
            "ok": error_rate <= float(max_error_rate),
        },
    ]

    block_reasons = [f"{row['metric']} fora do limiar" for row in checks if not bool(row["ok"])]
    decision = "APPROVED" if not block_reasons else "BLOCKED"

    return {
        "report_id": GATE_PREFIX,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "route_mode": str(parity_report.get("route_mode", "")) if isinstance(parity_report, dict) else "",
        "exame": str(parity_report.get("exame", "")) if isinstance(parity_report, dict) else "",
        "source_parity_report_id": str(parity_report.get("report_id", REPORT_PREFIX))
        if isinstance(parity_report, dict)
        else REPORT_PREFIX,
        "inputs": {
            "samples_compared": compared,
            "critical_divergences": critical_divergences,
            "errors": errors,
            "error_rate": round(error_rate, 6),
            "p95_latency_ms": float(slo.get("p95_latency_ms", 0.0) or 0.0),
            "p95_target_ms": float(slo.get("p95_target_ms", 0.0) or 0.0),
        },
        "thresholds": {
            "max_critical_divergences": int(max_critical_divergences),
            "require_p95_within_target": True,
            "max_error_rate": float(max_error_rate),
        },
        "checks": checks,
        "block_reasons": block_reasons,
        "is_promotion_allowed": decision == "APPROVED",
        "decision": decision,
    }


def persist_runtime_promotion_gate(
    gate_report: Dict[str, object],
    *,
    reports_dir: Path | None = None,
) -> Path:
    root = reports_dir or Path("reports")
    root.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    run_file = root / f"{GATE_PREFIX}_{stamp}.json"
    latest_file = root / f"{GATE_PREFIX}_latest.json"
    payload = json.dumps(gate_report, ensure_ascii=False, indent=2)
    run_file.write_text(payload, encoding="utf-8")
    latest_file.write_text(payload, encoding="utf-8")
    return run_file
