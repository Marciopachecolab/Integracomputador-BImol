"""Paridade auditavel entre legado (analysis_protocols/rules) e registry canonico."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from services.contract_catalog import get_contract_catalog
from services.analysis.analysis_runtime_contract import build_protocol_and_rules_from_cfg
from services.exam_domain_contracts import uses_default_viral_rule
from services.exam_registry import get_exam_cfg

FALLBACK_CANONICAL = "canonical_registry_rule"
FALLBACK_LEGACY = "legacy_rule_when_canonical_missing"
REPORT_PREFIX = "0260327_legacy_registry_parity"


def _norm_text(value: Any) -> str:
    return str(value or "").strip().upper()


def _normalize_target_name(value: Any) -> str:
    text = _norm_text(value).replace(" ", "").replace("_", "").replace("-", "")
    if not text:
        return ""
    if text in {"ZIKA", "ZYK", "ZK"}:
        return "ZK"
    if text in {"CHIKUNGUNYA", "CHIK"}:
        return "CHIK"
    if text.startswith("DENGUE") and text[-1:].isdigit():
        return f"DEN{text[-1]}"
    if text.startswith("DEN") and text[-1:].isdigit():
        return f"DEN{text[-1]}"
    if text.startswith("D") and len(text) == 2 and text[-1].isdigit():
        return f"DEN{text[-1]}"
    if text.startswith("RP"):
        return "RP"
    return _norm_text(value)


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _load_legacy_protocol(protocol_id: str) -> Dict[str, Any]:
    from services.engine.config_loader import ConfigLoader

    wanted = str(protocol_id or "").strip().lower()
    for row in ConfigLoader.get_protocols():
        if str(row.get("id", "")).strip().lower() == wanted:
            return row
    return {}


def _load_legacy_rules(protocol_id: str) -> Dict[str, Any]:
    from services.engine.config_loader import ConfigLoader

    wanted = str(protocol_id or "").strip().lower()
    for row in ConfigLoader.get_analysis_rules():
        if str(row.get("protocol_id", "")).strip().lower() == wanted:
            return row
    return {}


def _rules_by_target(rules_cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for rule in list(rules_cfg.get("rules", []) or []):
        target = _normalize_target_name(rule.get("target"))
        if not target:
            continue
        out[target] = rule
    return out


def _rule_ranges_signature(rule: Dict[str, Any] | None) -> List[List[float]]:
    return [[item["min"], item["max"]] for item in _rule_conditions_signature(rule)]


def _rule_conditions_signature(rule: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    if not isinstance(rule, dict):
        return []
    out: List[Dict[str, Any]] = []
    for cond in list(rule.get("conditions", []) or []):
        rng = cond.get("range", [])
        if not isinstance(rng, list) or len(rng) != 2:
            continue
        out.append(
            {
                "min": round(_safe_float(rng[0]), 4),
                "max": round(_safe_float(rng[1]), 4),
                "result": _norm_text(cond.get("result")),
            }
        )
    # Comparacao semântica: mesma regra com ordem diferente nao diverge.
    return sorted(out, key=lambda item: (item["min"], item["max"], item["result"]))


def _resolve_legacy_rule_for_target(
    *,
    target: str,
    target_meta: Dict[str, Any],
    legacy_by_target: Dict[str, Dict[str, Any]],
) -> Dict[str, Any] | None:
    exact = legacy_by_target.get(_normalize_target_name(target))
    if exact:
        return exact

    if _normalize_target_name(target).startswith("RP"):
        rp_rule = legacy_by_target.get("RP")
        if rp_rule:
            return rp_rule

    if uses_default_viral_rule(target_meta.get("type")):
        return legacy_by_target.get("DEFAULT_VIRAL")
    return None


def resolve_target_fallback_decision(
    *,
    target: str,
    canonical: Dict[str, Any] | None,
    legacy: Dict[str, Any] | None,
    canonical_rule: Dict[str, Any] | None,
    legacy_rule: Dict[str, Any] | None,
) -> Dict[str, str]:
    target_name = _normalize_target_name(target)
    if canonical and not legacy:
        return {"target": target_name, "fallback": FALLBACK_CANONICAL, "reason": "legacy_missing_target"}
    if legacy and not canonical:
        return {"target": target_name, "fallback": FALLBACK_LEGACY, "reason": "canonical_missing_target"}

    canonical_filter = _norm_text((canonical or {}).get("filter"))
    legacy_filter = _norm_text((legacy or {}).get("filter"))
    canonical_type = _norm_text((canonical or {}).get("type"))
    legacy_type = _norm_text((legacy or {}).get("type"))
    canonical_conditions = _rule_conditions_signature(canonical_rule)
    legacy_conditions = _rule_conditions_signature(legacy_rule)

    diverges = (
        canonical_filter != legacy_filter
        or canonical_type != legacy_type
        or canonical_conditions != legacy_conditions
    )
    if diverges:
        return {
            "target": target_name,
            "fallback": FALLBACK_CANONICAL,
            "reason": "divergent_interpretation_by_target",
        }
    return {"target": target_name, "fallback": "", "reason": "parity_ok"}


def _parse_group_size(esquema_agrupamento: Any, pocos_por_amostra: Any) -> int:
    try:
        explicit = int(pocos_por_amostra or 0)
    except Exception:
        explicit = 0
    if explicit > 0:
        return explicit

    raw = str(esquema_agrupamento or "").strip()
    if "->" not in raw:
        return 1
    left, right = raw.split("->", 1)
    try:
        orig = int(left)
        dest = int(right)
    except Exception:
        return 1
    if orig <= 0 or dest <= 0:
        return 1
    return max(1, orig // dest)


def _normalize_protocol_targets(targets_cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for target, data in dict(targets_cfg or {}).items():
        canonical = _normalize_target_name(target)
        if not canonical:
            continue
        out[canonical] = data if isinstance(data, dict) else {}
    return out


def _normalize_export_target(field: str, protocol_targets: Iterable[str]) -> str:
    value = _normalize_target_name(field)
    targets = set(protocol_targets)
    if value == "ZK" and "ZK" in targets:
        return "ZK"
    return value


def _extract_export_targets_from_profile(profile: Dict[str, Any], protocol_targets: Iterable[str]) -> List[str]:
    targets: set[str] = set()
    pairs = [item for item in list(profile.get("export_field_pairs", []) or []) if isinstance(item, dict)]
    if pairs:
        for pair in pairs:
            canonical_target = _normalize_target_name(pair.get("canonical_target") or pair.get("field"))
            if canonical_target and not canonical_target.startswith("RP"):
                targets.add(canonical_target)
        return sorted(targets)

    for field in list(profile.get("export_fields", []) or []):
        normalized = _normalize_export_target(str(field), protocol_targets)
        if normalized and not normalized.startswith("RP"):
            targets.add(normalized)
    return sorted(targets)


def _build_csv_parity_dimension(
    *,
    exam_name: str,
    cfg: Any,
    protocol_targets: Iterable[str],
) -> Dict[str, Any]:
    catalog = get_contract_catalog()
    bundle = catalog.resolve_runtime_bundle(exam_name=exam_name)
    active_profile = dict(bundle.gal_profile or {})
    active_profile_id = str(active_profile.get("profile_id") or getattr(cfg, "gal_profile_id", "")).strip()
    policy = dict(active_profile.get("csv_schema_policy", {}) or {})
    compatibility = dict(active_profile.get("legacy_compatibility", {}) or {})
    fallback_profile_id = str(
        compatibility.get("fallback_profile_id")
        or compatibility.get("v1_profile_id")
        or policy.get("fallback_profile")
        or active_profile_id
    ).strip() or active_profile_id

    fallback_profile = dict(catalog.get_gal_profile(fallback_profile_id) or active_profile)
    expected_targets = sorted(target for target in set(protocol_targets) if not target.startswith("RP"))
    active_targets = _extract_export_targets_from_profile(active_profile, expected_targets)
    fallback_targets = _extract_export_targets_from_profile(fallback_profile, expected_targets)

    divergences: List[Dict[str, Any]] = []
    if set(active_targets) != set(expected_targets):
        divergences.append(
            {
                "reason": "active_profile_export_targets_mismatch",
                "profile_id": active_profile_id,
                "expected_targets": expected_targets,
                "actual_targets": active_targets,
            }
        )
    if set(fallback_targets) != set(expected_targets):
        divergences.append(
            {
                "reason": "fallback_profile_export_targets_mismatch",
                "profile_id": fallback_profile_id,
                "expected_targets": expected_targets,
                "actual_targets": fallback_targets,
            }
        )
    if not fallback_profile_id:
        divergences.append({"reason": "missing_fallback_profile_id"})

    compatibility_mode = str(policy.get("compatibility_mode", "")).strip().lower()
    if compatibility_mode == "dual_v1_v2" and fallback_profile_id and fallback_profile_id != active_profile_id:
        deterministic_mode = "dual_v1_v2_with_explicit_fallback"
    elif fallback_profile_id and fallback_profile_id != active_profile_id:
        deterministic_mode = "explicit_fallback_profile"
    else:
        deterministic_mode = "single_profile_or_legacy_only"

    return {
        "critical_divergences": len(divergences),
        "is_parity_ok": len(divergences) == 0,
        "expected_targets": expected_targets,
        "active_targets": active_targets,
        "fallback_targets": fallback_targets,
        "active_profile_id": active_profile_id,
        "fallback_profile_id": fallback_profile_id,
        "rollback_flag": str(policy.get("rollback_flag") or ""),
        "deterministic_mode": deterministic_mode,
        "divergences": divergences,
    }


def _build_table_map_parity_dimension(
    *,
    exam_name: str,
    cfg: Any,
    canonical_targets: Dict[str, Dict[str, Any]],
    legacy_targets: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    canonical_keys = set(canonical_targets.keys())
    legacy_keys = set(legacy_targets.keys())

    missing_in_legacy = sorted(canonical_keys - legacy_keys)
    missing_in_canonical = sorted(legacy_keys - canonical_keys)

    group_size_cfg = 0
    try:
        maybe_bloco = getattr(cfg, "bloco_size", None)
        if callable(maybe_bloco):
            group_size_cfg = int(maybe_bloco() or 0)
    except Exception:
        group_size_cfg = 0
    if group_size_cfg <= 0:
        group_size_cfg = _parse_group_size(
            getattr(cfg, "esquema_agrupamento", ""),
            getattr(cfg, "pocos_por_amostra", 1),
        )
    group_size_contract = group_size_cfg
    try:
        decision = get_contract_catalog().resolve_analysis_contract_decision(exam_name=exam_name)
        group_size_contract = int(decision.get("group_size", group_size_cfg) or group_size_cfg)
    except Exception:
        pass

    grouping_divergent = group_size_cfg != group_size_contract
    divergences = []
    if missing_in_legacy:
        divergences.append({"reason": "missing_targets_in_legacy_protocol", "targets": missing_in_legacy})
    if missing_in_canonical:
        divergences.append({"reason": "missing_targets_in_canonical_protocol", "targets": missing_in_canonical})
    if grouping_divergent:
        divergences.append(
            {
                "reason": "group_size_divergence",
                "group_size_cfg": group_size_cfg,
                "group_size_contract": group_size_contract,
            }
        )

    return {
        "critical_divergences": len(divergences),
        "is_parity_ok": len(divergences) == 0,
        "group_size_cfg": group_size_cfg,
        "group_size_contract": group_size_contract,
        "missing_in_legacy": missing_in_legacy,
        "missing_in_canonical": missing_in_canonical,
        "divergences": divergences,
    }


def build_legacy_registry_parity_report(*, exam_name: str, protocol_id: str) -> Dict[str, Any]:
    cfg = get_exam_cfg(exam_name)
    canonical_protocol, canonical_rules = build_protocol_and_rules_from_cfg(cfg, protocol_id=protocol_id)
    legacy_protocol = _load_legacy_protocol(protocol_id)
    legacy_rules = _load_legacy_rules(protocol_id)

    canonical_targets = _normalize_protocol_targets(
        dict((canonical_protocol or {}).get("targets_configuration", {}) or {})
    )
    legacy_targets = _normalize_protocol_targets(dict(legacy_protocol.get("targets_configuration", {}) or {}))
    canonical_rules_by_target = _rules_by_target(canonical_rules or {})
    legacy_rules_by_target = _rules_by_target(legacy_rules)

    all_targets = sorted(set(canonical_targets.keys()) | set(legacy_targets.keys()))
    divergences: List[Dict[str, Any]] = []
    decisions: List[Dict[str, str]] = []

    for target in all_targets:
        canonical_meta = canonical_targets.get(target)
        legacy_meta = legacy_targets.get(target)
        canonical_rule = canonical_rules_by_target.get(target)
        legacy_rule = _resolve_legacy_rule_for_target(
            target=target,
            target_meta=canonical_meta or {},
            legacy_by_target=legacy_rules_by_target,
        )
        decision = resolve_target_fallback_decision(
            target=target,
            canonical=canonical_meta,
            legacy=legacy_meta,
            canonical_rule=canonical_rule,
            legacy_rule=legacy_rule,
        )
        decisions.append(decision)
        if decision["fallback"]:
            divergences.append(
                {
                    "target": target,
                    "reason": decision["reason"],
                    "fallback": decision["fallback"],
                    "canonical": canonical_meta or {},
                    "legacy": legacy_meta or {},
                    "canonical_ranges": _rule_ranges_signature(canonical_rule),
                    "legacy_ranges": _rule_ranges_signature(legacy_rule),
                    "canonical_conditions": _rule_conditions_signature(canonical_rule),
                    "legacy_conditions": _rule_conditions_signature(legacy_rule),
                }
            )

    rules_dimension = {
        "critical_divergences": len(divergences),
        "is_parity_ok": len(divergences) == 0,
        "targets_compared": len(all_targets),
        "divergences": divergences,
    }
    table_map_dimension = _build_table_map_parity_dimension(
        exam_name=exam_name,
        cfg=cfg,
        canonical_targets=canonical_targets,
        legacy_targets=legacy_targets,
    )
    csv_dimension = _build_csv_parity_dimension(
        exam_name=exam_name,
        cfg=cfg,
        protocol_targets=all_targets,
    )

    total_critical = (
        int(table_map_dimension.get("critical_divergences", 0))
        + int(rules_dimension.get("critical_divergences", 0))
        + int(csv_dimension.get("critical_divergences", 0))
    )
    csv_fallback_decision = {
        "active_profile_id": csv_dimension.get("active_profile_id", ""),
        "fallback_profile_id": csv_dimension.get("fallback_profile_id", ""),
        "rollback_flag": csv_dimension.get("rollback_flag", ""),
        "deterministic_mode": csv_dimension.get("deterministic_mode", ""),
    }

    return {
        "report_id": REPORT_PREFIX,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "exam_name": str(exam_name or ""),
        "protocol_id": str(protocol_id or ""),
        "totals": {
            "targets_compared": len(all_targets),
            "critical_divergences": total_critical,
        },
        "fallback_policy": {
            "on_divergence_by_target": FALLBACK_CANONICAL,
            "on_canonical_missing_target": FALLBACK_LEGACY,
            "csv": {
                "on_schema_divergence": "legacy_profile_contract",
                "rollback_flag": csv_dimension.get("rollback_flag", ""),
            },
        },
        "fallback_decisions": decisions,
        "csv_fallback_decision": csv_fallback_decision,
        "dimensions": {
            "table_map": table_map_dimension,
            "rules": rules_dimension,
            "csv": csv_dimension,
        },
        "critical_divergences": divergences,
        "is_parity_ok": total_critical == 0,
    }


def persist_legacy_registry_parity_report(
    report: Dict[str, Any],
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
