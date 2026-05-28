"""Governanca de rollout do runtime canonico da analise (F3.7)."""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from services.analysis.analysis_runtime_observability import GATE_PREFIX
from services.core.runtime_flags import (
    is_analysis_runtime_promotion_gate_enforcement_enabled,
    is_analysis_runtime_staged_rollout_enabled,
)


AUDIT_PREFIX = "0260325_analysis_runtime_rollout_audit"
STAGE_AUDIT_PREFIX = "0260325_analysis_runtime_rollout_stage"
CUTOVER_AUDIT_PREFIX = "0260325_analysis_runtime_cutover"
STABILIZATION_CLOSURE_AUDIT_PREFIX = "0260325_analysis_runtime_stabilization_closure"
STAGE_SEQUENCE = (10, 25, 50, 100)


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _normalize_exam_key(value: Any) -> str:
    text = str(value or "").strip().lower().replace("_", " ")
    return " ".join(text.split())


def _exam_key_variants(value: Any) -> set[str]:
    normalized = _normalize_exam_key(value)
    if not normalized:
        return set()
    compact = normalized.replace(" ", "")
    alnum = "".join(ch for ch in normalized if ch.isalnum())
    return {normalized, compact, alnum}


def _resolve_exam_scope(exam_name: str | None) -> Dict[str, Any]:
    raw_targets = str(os.getenv("INTEGRAGAL_ANALYSIS_RUNTIME_TARGET_EXAMS", "") or "").strip()
    if not raw_targets:
        return {
            "target_exams": [],
            "configured": False,
            "exam_name": str(exam_name or ""),
            "in_scope": True,
            "scope_mode": "global",
        }

    tokens = [token for token in (item.strip() for item in raw_targets.split(",")) if token]
    target_variants: set[str] = set()
    for token in tokens:
        target_variants.update(_exam_key_variants(token))
    exam_variants = _exam_key_variants(exam_name)
    in_scope = bool(exam_variants and exam_variants.intersection(target_variants))
    return {
        "target_exams": tokens,
        "configured": True,
        "exam_name": str(exam_name or ""),
        "in_scope": bool(in_scope),
        "scope_mode": "targeted",
    }


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_reports_dir(reports_dir: Path | None = None) -> Path:
    root = reports_dir or Path("reports")
    root.mkdir(parents=True, exist_ok=True)
    return root


def load_latest_runtime_gate(*, reports_dir: Path | None = None) -> Dict[str, Any] | None:
    root = _resolve_reports_dir(reports_dir)
    latest = root / f"{GATE_PREFIX}_latest.json"
    if latest.exists():
        payload = _read_json(latest)
        if payload:
            return payload
    return None


def load_latest_rollout_audit(*, reports_dir: Path | None = None) -> Dict[str, Any] | None:
    root = _resolve_reports_dir(reports_dir)
    latest = root / f"{AUDIT_PREFIX}_latest.json"
    if latest.exists():
        payload = _read_json(latest)
        if payload:
            return payload
    return None


def load_latest_stage_audit(*, reports_dir: Path | None = None) -> Dict[str, Any] | None:
    root = _resolve_reports_dir(reports_dir)
    latest = root / f"{STAGE_AUDIT_PREFIX}_latest.json"
    if latest.exists():
        payload = _read_json(latest)
        if payload:
            return payload
    return None


def load_latest_cutover_audit(*, reports_dir: Path | None = None) -> Dict[str, Any] | None:
    root = _resolve_reports_dir(reports_dir)
    latest = root / f"{CUTOVER_AUDIT_PREFIX}_latest.json"
    if latest.exists():
        payload = _read_json(latest)
        if payload:
            return payload
    return None


def load_latest_stabilization_closure_audit(*, reports_dir: Path | None = None) -> Dict[str, Any] | None:
    root = _resolve_reports_dir(reports_dir)
    latest = root / f"{STABILIZATION_CLOSURE_AUDIT_PREFIX}_latest.json"
    if latest.exists():
        payload = _read_json(latest)
        if payload:
            return payload
    return None


def _gate_has_critical_violation(gate_report: Dict[str, Any]) -> bool:
    inputs = gate_report.get("inputs", {}) if isinstance(gate_report, dict) else {}
    critical = _safe_int(inputs.get("critical_divergences"), 0)
    errors = _safe_int(inputs.get("errors"), 0)
    p95_latency = float(inputs.get("p95_latency_ms", 0.0) or 0.0)
    p95_target = float(inputs.get("p95_target_ms", 0.0) or 0.0)
    p95_violation = p95_target > 0.0 and p95_latency > p95_target
    return critical > 0 or errors > 0 or p95_violation


def _resolve_operational_gate(gate_report: Dict[str, Any]) -> Dict[str, Any]:
    inputs = gate_report.get("inputs", {}) if isinstance(gate_report, dict) else {}
    thresholds = gate_report.get("thresholds", {}) if isinstance(gate_report, dict) else {}
    compared = max(1, _safe_int(inputs.get("samples_compared"), 0))
    critical = _safe_int(inputs.get("critical_divergences"), 0)
    errors = _safe_int(inputs.get("errors"), 0)
    default_error_rate = float(errors) / float(compared)
    error_rate = float(inputs.get("error_rate", default_error_rate) or default_error_rate)
    p95_latency = float(inputs.get("p95_latency_ms", 0.0) or 0.0)
    p95_target = float(inputs.get("p95_target_ms", 0.0) or 0.0)

    max_critical = _safe_int(thresholds.get("max_critical_divergences"), 0)
    max_error_rate = float(thresholds.get("max_error_rate", 0.0) or 0.0)
    require_p95 = bool(thresholds.get("require_p95_within_target", True))

    parity_ok = critical <= max_critical
    error_ok = error_rate <= max_error_rate
    latency_ok = (not require_p95) or (p95_target <= 0.0) or (p95_latency <= p95_target)
    go_no_go = "GO" if (parity_ok and error_ok and latency_ok) else "NO_GO"
    return {
        "go_no_go": go_no_go,
        "criteria": {
            "parity_ok": bool(parity_ok),
            "error_ok": bool(error_ok),
            "latency_ok": bool(latency_ok),
        },
        "inputs": {
            "critical_divergences": int(critical),
            "errors": int(errors),
            "error_rate": float(error_rate),
            "p95_latency_ms": float(p95_latency),
            "p95_target_ms": float(p95_target),
            "samples_compared": int(compared),
        },
        "thresholds": {
            "max_critical_divergences": int(max_critical),
            "max_error_rate": float(max_error_rate),
            "require_p95_within_target": bool(require_p95),
        },
    }


def _resolve_rollback_state(
    *,
    requested_enabled_by_flag: bool,
    requested_enabled_effective: bool,
    promotion_status: str,
    effective_runtime_enabled: bool,
    reports_dir: Path | None,
) -> Dict[str, Any]:
    prev_audit = load_latest_rollout_audit(reports_dir=reports_dir) or {}
    prev_effective = bool(prev_audit.get("effective_runtime_enabled", False))
    triggered = bool(prev_effective and (not bool(effective_runtime_enabled)))

    reason = ""
    if triggered:
        if not requested_enabled_by_flag:
            reason = "runtime_flag_off"
        elif not requested_enabled_effective:
            reason = "exam_out_of_scope"
        elif str(promotion_status).upper() == "BLOCKED":
            reason = "gate_blocked_or_critical_violation"
        else:
            reason = "runtime_disabled"

    return {
        "triggered": bool(triggered),
        "from_mode": "registry_runtime" if prev_effective else "legacy_builtin_rules",
        "to_mode": "legacy_builtin_rules" if triggered else "",
        "reason": reason,
    }


def _next_stage(previous_stage: int) -> int:
    for step in STAGE_SEQUENCE:
        if step > int(previous_stage):
            return int(step)
    return int(STAGE_SEQUENCE[-1])


def compute_rollout_bucket(user_id: str | None) -> int:
    """Retorna bucket deterministico [0..99] para canario por usuario."""
    key = str(user_id or "").strip().lower()
    if not key:
        return 100
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def _is_canary_allowed(*, user_id: str | None, stage_percent: int) -> bool:
    stage = max(0, min(100, int(stage_percent or 0)))
    if stage >= 100:
        return True
    return compute_rollout_bucket(user_id) < stage


def _resolve_stage_rollout(
    *,
    requested_enabled: bool,
    promotion_status: str,
    gate_has_critical_violation: bool,
    fallback_reduction: Dict[str, Any],
    user_id: str | None,
    reports_dir: Path | None,
) -> Dict[str, Any]:
    stage_enabled = is_analysis_runtime_staged_rollout_enabled(user_id=user_id)
    latest_stage = load_latest_stage_audit(reports_dir=reports_dir) or {}
    previous_stage_percent = _safe_int(latest_stage.get("current_stage_percent"), 0)
    previous_stage_percent = max(0, min(100, previous_stage_percent))

    fallback_eligible = bool((fallback_reduction or {}).get("eligible", False))
    stage_percent = previous_stage_percent
    stage_status = "DISABLED"
    advanced = False
    blocked = False
    reason = ""

    if not requested_enabled:
        stage_percent = 0
        stage_status = "FLAG_DISABLED"
        reason = "runtime_flag_off"
    elif not stage_enabled:
        stage_percent = 100
        stage_status = "DISABLED"
        reason = "staged_rollout_flag_off"
    elif str(promotion_status).upper() != "APPROVED":
        stage_status = "BLOCKED"
        blocked = True
        reason = "promotion_not_approved"
    elif gate_has_critical_violation:
        stage_status = "BLOCKED"
        blocked = True
        reason = "gate_critical_violation"
    elif not fallback_eligible:
        stage_status = "WAIT_ELIGIBILITY"
        reason = "fallback_reduction_not_eligible"
    else:
        target_stage = _next_stage(previous_stage_percent)
        advanced = target_stage > previous_stage_percent
        stage_percent = target_stage
        stage_status = "ADVANCED" if advanced else "STABLE"
        reason = "advanced_by_gate_approval" if advanced else "already_max_stage"

    canary_allowed = _is_canary_allowed(user_id=user_id, stage_percent=stage_percent)
    return {
        "stage_enabled": bool(stage_enabled),
        "stage_sequence": list(STAGE_SEQUENCE),
        "previous_stage_percent": int(previous_stage_percent),
        "current_stage_percent": int(stage_percent),
        "advanced": bool(advanced),
        "blocked": bool(blocked),
        "status": stage_status,
        "reason": reason,
        "canary_allowed": bool(canary_allowed),
        "fallback_reduction_eligible": bool(fallback_eligible),
    }


def _resolve_cutover_state(
    *,
    requested_enabled: bool,
    promotion_status: str,
    gate_decision: str,
    gate_has_critical_violation: bool,
    stage_rollout: Dict[str, Any],
    reports_dir: Path | None,
) -> Dict[str, Any]:
    min_stable_runs = max(
        1,
        _safe_int(os.getenv("INTEGRAGAL_ANALYSIS_RUNTIME_CUTOVER_MIN_STABLE_RUNS"), 3),
    )
    previous = load_latest_cutover_audit(reports_dir=reports_dir) or {}
    prev_cutover = previous.get("cutover", {}) if isinstance(previous, dict) else {}
    prev_stable_count = _safe_int(
        prev_cutover.get(
            "stable_window_count",
            previous.get("stable_window_count", 0) if isinstance(previous, dict) else 0,
        ),
        0,
    )

    stage_percent = _safe_int(stage_rollout.get("current_stage_percent"), 0)
    stage_ready = stage_percent >= 100
    gate_ready = (
        str(promotion_status).upper() == "APPROVED"
        and str(gate_decision).upper() == "APPROVED"
        and (not bool(gate_has_critical_violation))
    )
    cutover_gate_ok = bool(requested_enabled) and gate_ready and stage_ready
    stable_window_count = (prev_stable_count + 1) if cutover_gate_ok else 0
    readiness_met = cutover_gate_ok and stable_window_count >= min_stable_runs
    go_no_go = "GO" if readiness_met else "NO_GO"

    if not bool(requested_enabled):
        transition_state = "LEGACY_ACTIVE"
    elif not gate_ready:
        transition_state = "LEGACY_GATED"
    elif not stage_ready:
        transition_state = "CANARY_TRANSITION"
    elif not readiness_met:
        transition_state = "CANONICAL_STABILIZING"
    else:
        transition_state = "CANONICAL_CUTOVER_READY"

    return {
        "transition_state": transition_state,
        "stage_ready": bool(stage_ready),
        "gate_ready": bool(gate_ready),
        "cutover_gate_ok": bool(cutover_gate_ok),
        "stable_window_count": int(stable_window_count),
        "min_stable_runs": int(min_stable_runs),
        "readiness_met": bool(readiness_met),
        "go_no_go": go_no_go,
        "legacy_fallback_deactivation_start_allowed": bool(readiness_met),
        "legacy_fallback_deactivation_recommendation": (
            "start_controlled_deactivation"
            if readiness_met
            else "keep_legacy_fallback_active"
        ),
    }


def _resolve_stabilization_closure_state(
    *,
    requested_enabled: bool,
    promotion_status: str,
    gate_has_critical_violation: bool,
    cutover: Dict[str, Any],
    effective_runtime_enabled: bool,
    reports_dir: Path | None,
) -> Dict[str, Any]:
    min_windows = max(
        1,
        _safe_int(os.getenv("INTEGRAGAL_ANALYSIS_RUNTIME_STABILIZATION_MIN_WINDOWS"), 3),
    )
    max_incidents = max(
        0,
        _safe_int(os.getenv("INTEGRAGAL_ANALYSIS_RUNTIME_STABILIZATION_MAX_INCIDENTS"), 0),
    )
    rollback_cooldown = max(
        1,
        _safe_int(os.getenv("INTEGRAGAL_ANALYSIS_RUNTIME_STABILIZATION_ROLLBACK_COOLDOWN_WINDOWS"), 3),
    )

    previous = load_latest_stabilization_closure_audit(reports_dir=reports_dir) or {}
    prev_state = previous.get("stabilization_closure", {}) if isinstance(previous, dict) else {}
    prev_window = _safe_int(
        prev_state.get(
            "stable_windows_count",
            previous.get("stable_windows_count", 0) if isinstance(previous, dict) else 0,
        ),
        0,
    )
    prev_incidents = _safe_int(
        prev_state.get(
            "incidents_in_window",
            previous.get("incidents_in_window", 0) if isinstance(previous, dict) else 0,
        ),
        0,
    )
    prev_since_rollback = _safe_int(
        prev_state.get(
            "windows_since_last_rollback",
            previous.get("windows_since_last_rollback", rollback_cooldown),
        ),
        rollback_cooldown,
    )
    prev_final_state = str(
        prev_state.get(
            "final_operational_state",
            previous.get("final_operational_state", ""),
        )
    ).strip()
    prev_cutover_ready = bool(
        prev_state.get(
            "cutover_ready_once",
            previous.get("cutover_ready_once", False),
        )
    )

    cutover_ready = bool(cutover.get("readiness_met", False))
    cutover_ready_once = bool(prev_cutover_ready or cutover_ready)

    incident_event = bool(
        gate_has_critical_violation
        or (
            cutover_ready_once
            and str(promotion_status).upper() != "APPROVED"
        )
    )

    rollback_event = bool(
        cutover_ready_once
        and (
            (not bool(requested_enabled))
            or (not bool(effective_runtime_enabled))
        )
    )

    incidents_in_window = prev_incidents + (1 if incident_event else 0)
    windows_since_last_rollback = 0 if rollback_event else (prev_since_rollback + 1)
    rollback_recent = windows_since_last_rollback < rollback_cooldown

    stable_window_ok = bool(
        cutover_ready_once
        and str(promotion_status).upper() == "APPROVED"
        and (not gate_has_critical_violation)
        and (not rollback_recent)
    )
    stable_windows_count = (prev_window + 1) if stable_window_ok else 0

    closure_ready = bool(
        cutover_ready_once
        and stable_windows_count >= min_windows
        and incidents_in_window <= max_incidents
        and (not rollback_recent)
        and str(promotion_status).upper() == "APPROVED"
        and (not gate_has_critical_violation)
    )
    closure_go_no_go = "GO" if closure_ready else "NO_GO"

    if closure_ready:
        final_state = "CANONICAL_PRIMARY_WITH_CONTINGENCY_FALLBACK"
    elif cutover_ready_once:
        final_state = "CANONICAL_STABILIZING_WITH_CONTINGENCY_FALLBACK"
    elif prev_final_state:
        final_state = prev_final_state
    else:
        final_state = "LEGACY_PRIMARY_WITH_CANONICAL_SHADOW"

    return {
        "final_operational_state": final_state,
        "cutover_ready_once": bool(cutover_ready_once),
        "stable_windows_count": int(stable_windows_count),
        "min_stable_windows": int(min_windows),
        "incidents_in_window": int(incidents_in_window),
        "max_incidents_allowed": int(max_incidents),
        "windows_since_last_rollback": int(windows_since_last_rollback),
        "rollback_cooldown_windows": int(rollback_cooldown),
        "rollback_recent": bool(rollback_recent),
        "incident_event": bool(incident_event),
        "rollback_event": bool(rollback_event),
        "closure_readiness_met": bool(closure_ready),
        "closure_go_no_go": closure_go_no_go,
        "legacy_fallback_mode": (
            "contingency_controlled" if cutover_ready_once else "full_fallback_allowed"
        ),
    }


def resolve_runtime_rollout_decision(
    *,
    requested_enabled: bool,
    exam_name: str | None = None,
    user_id: str | None = None,
    reports_dir: Path | None = None,
) -> Dict[str, Any]:
    """Resolve decisao efetiva de rollout do runtime canonico."""
    requested_enabled_by_flag = bool(requested_enabled)
    exam_scope = _resolve_exam_scope(exam_name)
    requested_enabled_effective = bool(requested_enabled_by_flag and exam_scope.get("in_scope", True))
    enforcement_enabled = is_analysis_runtime_promotion_gate_enforcement_enabled(user_id=user_id)
    gate_report = load_latest_runtime_gate(reports_dir=reports_dir)
    gate_found = bool(gate_report)
    gate_decision = str((gate_report or {}).get("decision", "")).strip().upper()
    gate_allowed = bool((gate_report or {}).get("is_promotion_allowed", gate_decision == "APPROVED"))
    gate_has_violation = _gate_has_critical_violation(gate_report or {})
    operational_gate = _resolve_operational_gate(gate_report or {})

    block_reason = ""
    promotion_status = "FLAG_DISABLED"

    if not requested_enabled_by_flag:
        promotion_status = "FLAG_DISABLED"
    elif not requested_enabled_effective:
        promotion_status = "OUT_OF_SCOPE"
        block_reason = "exam_out_of_scope"
    elif not enforcement_enabled:
        promotion_status = "APPROVED"
    elif not gate_found:
        promotion_status = "BLOCKED"
        block_reason = "gate_ausente"
    elif (not gate_allowed) or gate_has_violation or gate_decision != "APPROVED":
        promotion_status = "BLOCKED"
        block_reason = "gate_blocked_or_critical_violation"
    else:
        promotion_status = "APPROVED"

    prev_audit = load_latest_rollout_audit(reports_dir=reports_dir) or {}
    prev_fallback = prev_audit.get("fallback_reduction", {}) if isinstance(prev_audit, dict) else {}
    prev_streak = _safe_int(prev_fallback.get("approved_streak"), 0)
    approved_streak = (prev_streak + 1) if promotion_status == "APPROVED" else 0

    min_streak = max(
        1,
        _safe_int(os.getenv("INTEGRAGAL_ANALYSIS_RUNTIME_FALLBACK_MIN_APPROVED_STREAK"), 5),
    )
    min_samples = max(
        1,
        _safe_int(os.getenv("INTEGRAGAL_ANALYSIS_RUNTIME_FALLBACK_MIN_GATE_SAMPLES"), 200),
    )
    samples_compared = _safe_int(((gate_report or {}).get("inputs", {}) or {}).get("samples_compared"), 0)
    eligible = approved_streak >= min_streak and samples_compared >= min_samples

    fallback_reduction = {
        "approved_streak": approved_streak,
        "min_approved_streak": min_streak,
        "samples_compared": samples_compared,
        "min_samples_required": min_samples,
        "eligible": bool(eligible),
        "recommendation": (
            "eligible_reduce_legacy_fallback_by_step"
            if eligible
            else "keep_legacy_fallback_until_thresholds"
        ),
    }

    stage_rollout = _resolve_stage_rollout(
        requested_enabled=bool(requested_enabled_effective),
        promotion_status=promotion_status,
        gate_has_critical_violation=gate_has_violation,
        fallback_reduction=fallback_reduction,
        user_id=user_id,
        reports_dir=reports_dir,
    )
    cutover = _resolve_cutover_state(
        requested_enabled=bool(requested_enabled_effective),
        promotion_status=promotion_status,
        gate_decision=gate_decision or "UNAVAILABLE",
        gate_has_critical_violation=gate_has_violation,
        stage_rollout=stage_rollout,
        reports_dir=reports_dir,
    )

    if not bool(requested_enabled_effective):
        effective_runtime_enabled = False
        shadow_compare_enabled = False
    elif str(promotion_status).upper() != "APPROVED":
        effective_runtime_enabled = False
        shadow_compare_enabled = True
    elif bool(stage_rollout.get("stage_enabled", False)):
        effective_runtime_enabled = bool(stage_rollout.get("canary_allowed", False))
        shadow_compare_enabled = not effective_runtime_enabled
    else:
        effective_runtime_enabled = True
        shadow_compare_enabled = False

    stabilization_closure = _resolve_stabilization_closure_state(
        requested_enabled=bool(requested_enabled_effective),
        promotion_status=promotion_status,
        gate_has_critical_violation=gate_has_violation,
        cutover=cutover,
        effective_runtime_enabled=bool(effective_runtime_enabled),
        reports_dir=reports_dir,
    )
    rollback = _resolve_rollback_state(
        requested_enabled_by_flag=bool(requested_enabled_by_flag),
        requested_enabled_effective=bool(requested_enabled_effective),
        promotion_status=promotion_status,
        effective_runtime_enabled=bool(effective_runtime_enabled),
        reports_dir=reports_dir,
    )

    return {
        "requested_enabled": bool(requested_enabled_effective),
        "requested_enabled_by_flag": bool(requested_enabled_by_flag),
        "scope": exam_scope,
        "gate_enforcement_enabled": bool(enforcement_enabled),
        "gate_report_found": gate_found,
        "gate_decision": gate_decision or "UNAVAILABLE",
        "gate_is_promotion_allowed": gate_allowed,
        "gate_has_critical_violation": gate_has_violation,
        "operational_gate": operational_gate,
        "promotion_status": promotion_status,
        "effective_runtime_enabled": bool(effective_runtime_enabled),
        "shadow_compare_enabled": bool(shadow_compare_enabled),
        "block_reason": block_reason,
        "rollback": rollback,
        "fallback_reduction": fallback_reduction,
        "stage_rollout": stage_rollout,
        "cutover": cutover,
        "stabilization_closure": stabilization_closure,
        "gate_snapshot": gate_report or {},
    }


def build_runtime_rollout_audit(
    *,
    decision: Dict[str, Any],
    current_gate_report: Dict[str, Any],
    component: str,
    route_mode: str,
) -> Dict[str, Any]:
    inputs = current_gate_report.get("inputs", {}) if isinstance(current_gate_report, dict) else {}
    operational_gate = decision.get("operational_gate", {}) if isinstance(decision, dict) else {}
    rollback = decision.get("rollback", {}) if isinstance(decision, dict) else {}
    return {
        "report_id": AUDIT_PREFIX,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "component": str(component or "").strip() or "AnalysisService",
        "route_mode": str(route_mode or ""),
        "requested_enabled_by_flag": bool(decision.get("requested_enabled_by_flag", False)),
        "scope": decision.get("scope", {}),
        "scope_in_scope": bool((decision.get("scope", {}) or {}).get("in_scope", True)),
        "promotion_status": str(decision.get("promotion_status", "")),
        "block_reason": str(decision.get("block_reason", "")),
        "effective_runtime_enabled": bool(decision.get("effective_runtime_enabled", False)),
        "shadow_compare_enabled": bool(decision.get("shadow_compare_enabled", False)),
        "operational_gate_go_no_go": str((operational_gate or {}).get("go_no_go", "NO_GO")),
        "operational_gate_criteria": (operational_gate or {}).get("criteria", {}),
        "operational_gate_inputs": (operational_gate or {}).get("inputs", {}),
        "operational_gate_thresholds": (operational_gate or {}).get("thresholds", {}),
        "rollback_triggered": bool((rollback or {}).get("triggered", False)),
        "rollback_reason": str((rollback or {}).get("reason", "")),
        "rollback_from_mode": str((rollback or {}).get("from_mode", "")),
        "rollback_to_mode": str((rollback or {}).get("to_mode", "")),
        "consumed_gate_decision": str(decision.get("gate_decision", "")),
        "current_gate_report_id": str(current_gate_report.get("report_id", "")),
        "source_parity_report_id": str(current_gate_report.get("source_parity_report_id", "")),
        "current_gate_decision": str(current_gate_report.get("decision", "")),
        "current_gate_critical_divergences": _safe_int(inputs.get("critical_divergences"), 0),
        "current_gate_errors": _safe_int(inputs.get("errors"), 0),
        "fallback_reduction": decision.get("fallback_reduction", {}),
        "stage_rollout": decision.get("stage_rollout", {}),
    }


def persist_runtime_rollout_audit(
    audit_report: Dict[str, Any],
    *,
    reports_dir: Path | None = None,
) -> Path:
    root = _resolve_reports_dir(reports_dir)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    run_file = root / f"{AUDIT_PREFIX}_{stamp}_{os.getpid()}_{time.time_ns()}.json"
    latest_file = root / f"{AUDIT_PREFIX}_latest.json"
    payload = json.dumps(audit_report, ensure_ascii=False, indent=2)
    run_file.write_text(payload, encoding="utf-8")
    latest_file.write_text(payload, encoding="utf-8")
    return run_file


def build_runtime_rollout_stage_audit(
    *,
    decision: Dict[str, Any],
    component: str,
    route_mode: str,
) -> Dict[str, Any]:
    stage = decision.get("stage_rollout", {}) if isinstance(decision, dict) else {}
    return {
        "report_id": STAGE_AUDIT_PREFIX,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "component": str(component or "").strip() or "AnalysisService",
        "route_mode": str(route_mode or ""),
        "promotion_status": str(decision.get("promotion_status", "")),
        "effective_runtime_enabled": bool(decision.get("effective_runtime_enabled", False)),
        "current_stage_percent": int(_safe_int(stage.get("current_stage_percent"), 0)),
        "previous_stage_percent": int(_safe_int(stage.get("previous_stage_percent"), 0)),
        "advanced": bool(stage.get("advanced", False)),
        "blocked": bool(stage.get("blocked", False)),
        "status": str(stage.get("status", "")),
        "reason": str(stage.get("reason", "")),
        "fallback_reduction_eligible": bool(stage.get("fallback_reduction_eligible", False)),
    }


def persist_runtime_rollout_stage_audit(
    stage_audit: Dict[str, Any],
    *,
    reports_dir: Path | None = None,
) -> Path:
    root = _resolve_reports_dir(reports_dir)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    run_file = root / f"{STAGE_AUDIT_PREFIX}_{stamp}_{os.getpid()}_{time.time_ns()}.json"
    latest_file = root / f"{STAGE_AUDIT_PREFIX}_latest.json"
    payload = json.dumps(stage_audit, ensure_ascii=False, indent=2)
    run_file.write_text(payload, encoding="utf-8")
    latest_file.write_text(payload, encoding="utf-8")
    return run_file


def build_runtime_cutover_audit(
    *,
    decision: Dict[str, Any],
    current_gate_report: Dict[str, Any],
    component: str,
    route_mode: str,
) -> Dict[str, Any]:
    cutover = decision.get("cutover", {}) if isinstance(decision, dict) else {}
    inputs = current_gate_report.get("inputs", {}) if isinstance(current_gate_report, dict) else {}
    return {
        "report_id": CUTOVER_AUDIT_PREFIX,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "component": str(component or "").strip() or "AnalysisService",
        "route_mode": str(route_mode or ""),
        "promotion_status": str(decision.get("promotion_status", "")),
        "transition_state": str(cutover.get("transition_state", "")),
        "cutover_go_no_go": str(cutover.get("go_no_go", "NO_GO")),
        "cutover_readiness_met": bool(cutover.get("readiness_met", False)),
        "stable_window_count": int(_safe_int(cutover.get("stable_window_count"), 0)),
        "min_stable_runs": int(_safe_int(cutover.get("min_stable_runs"), 0)),
        "legacy_fallback_deactivation_start_allowed": bool(
            cutover.get("legacy_fallback_deactivation_start_allowed", False)
        ),
        "gate_decision": str(decision.get("gate_decision", "")),
        "gate_critical_divergences": int(_safe_int(inputs.get("critical_divergences"), 0)),
        "gate_errors": int(_safe_int(inputs.get("errors"), 0)),
    }


def persist_runtime_cutover_audit(
    cutover_audit: Dict[str, Any],
    *,
    reports_dir: Path | None = None,
) -> Path:
    root = _resolve_reports_dir(reports_dir)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    run_file = root / f"{CUTOVER_AUDIT_PREFIX}_{stamp}_{os.getpid()}_{time.time_ns()}.json"
    latest_file = root / f"{CUTOVER_AUDIT_PREFIX}_latest.json"
    payload = json.dumps(cutover_audit, ensure_ascii=False, indent=2)
    run_file.write_text(payload, encoding="utf-8")
    latest_file.write_text(payload, encoding="utf-8")
    return run_file


def build_runtime_stabilization_closure_audit(
    *,
    decision: Dict[str, Any],
    current_gate_report: Dict[str, Any],
    component: str,
    route_mode: str,
) -> Dict[str, Any]:
    closure = decision.get("stabilization_closure", {}) if isinstance(decision, dict) else {}
    cutover = decision.get("cutover", {}) if isinstance(decision, dict) else {}
    inputs = current_gate_report.get("inputs", {}) if isinstance(current_gate_report, dict) else {}
    return {
        "report_id": STABILIZATION_CLOSURE_AUDIT_PREFIX,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "component": str(component or "").strip() or "AnalysisService",
        "route_mode": str(route_mode or ""),
        "promotion_status": str(decision.get("promotion_status", "")),
        "cutover_go_no_go": str(cutover.get("go_no_go", "NO_GO")),
        "stabilization_closure_go_no_go": str(closure.get("closure_go_no_go", "NO_GO")),
        "closure_readiness_met": bool(closure.get("closure_readiness_met", False)),
        "cutover_ready_once": bool(closure.get("cutover_ready_once", False)),
        "final_operational_state": str(closure.get("final_operational_state", "")),
        "stable_windows_count": int(_safe_int(closure.get("stable_windows_count"), 0)),
        "min_stable_windows": int(_safe_int(closure.get("min_stable_windows"), 0)),
        "incidents_in_window": int(_safe_int(closure.get("incidents_in_window"), 0)),
        "max_incidents_allowed": int(_safe_int(closure.get("max_incidents_allowed"), 0)),
        "rollback_recent": bool(closure.get("rollback_recent", False)),
        "legacy_fallback_mode": str(closure.get("legacy_fallback_mode", "")),
        "gate_critical_divergences": int(_safe_int(inputs.get("critical_divergences"), 0)),
        "gate_errors": int(_safe_int(inputs.get("errors"), 0)),
    }


def persist_runtime_stabilization_closure_audit(
    closure_audit: Dict[str, Any],
    *,
    reports_dir: Path | None = None,
) -> Path:
    root = _resolve_reports_dir(reports_dir)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    run_file = root / f"{STABILIZATION_CLOSURE_AUDIT_PREFIX}_{stamp}_{os.getpid()}_{time.time_ns()}.json"
    latest_file = root / f"{STABILIZATION_CLOSURE_AUDIT_PREFIX}_latest.json"
    payload = json.dumps(closure_audit, ensure_ascii=False, indent=2)
    run_file.write_text(payload, encoding="utf-8")
    latest_file.write_text(payload, encoding="utf-8")
    return run_file
