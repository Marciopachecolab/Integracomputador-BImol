"""Contrato operacional canonico para regras runtime de analise."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from services.analysis.analysis_helpers import canonicalizar_alvo_pcr
from services.exam_domain_contracts import normalize_target_filter, normalize_target_type


def safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _normalize_target(value: Any) -> str:
    return canonicalizar_alvo_pcr(value)


def _is_blank_ct(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    if not text:
        return True
    return text.upper() in {"NA", "N/A", "NAN", "NONE", "UNDETERMINED", "UND", "N/D"}


def _resolve_default_rule(cfg: Any) -> Dict[str, float]:
    base = {
        "ct_minimo": 10.0,
        "ct_detectavel_limite": 35.0,
        "ct_inconclusivo_min": 35.01,
        "ct_inconclusivo_limite": 40.0,
    }
    faixas = getattr(cfg, "faixas_ct", {}) or {}
    detect_lim = safe_float(faixas.get("detect_max"), base["ct_detectavel_limite"])
    inconc_min = safe_float(faixas.get("inconc_min"), detect_lim + 0.01)
    return {
        "ct_minimo": safe_float(faixas.get("rp_min"), base["ct_minimo"]),
        "ct_detectavel_limite": detect_lim,
        "ct_inconclusivo_min": inconc_min,
        "ct_inconclusivo_limite": safe_float(faixas.get("inconc_max"), base["ct_inconclusivo_limite"]),
    }


def _resolve_targets(cfg: Any) -> Dict[str, Dict[str, str]]:
    targets_configuration: Dict[str, Dict[str, str]] = {}

    for item in list(getattr(cfg, "targets_por_poco", []) or []):
        if not isinstance(item, dict):
            continue
        alvo = str(item.get("alvo", "")).strip()
        if not alvo:
            continue
        canonical = _normalize_target(alvo)
        if not canonical:
            continue
        if canonical in targets_configuration:
            continue
        targets_configuration[canonical] = {
            "filter": normalize_target_filter(item.get("filtro", "NONE")),
            "type": normalize_target_type(item.get("tipo", "VIRAL")),
        }

    if targets_configuration:
        return targets_configuration

    for alvo in list(getattr(cfg, "alvos", []) or []):
        canonical = _normalize_target(alvo)
        if not canonical:
            continue
        if canonical in targets_configuration:
            continue
        targets_configuration[canonical] = {"filter": "NONE", "type": "VIRAL"}

    return targets_configuration


def build_runtime_rule_profile_from_cfg(
    cfg: Any,
    *,
    exam_name: str,
    rp_min_fallback: float,
    rp_max_fallback: float,
) -> Dict[str, Any]:
    default_rule = _resolve_default_rule(cfg)
    by_target: Dict[str, Dict[str, float]] = {}
    limiares = list(getattr(cfg, "limiares_ct_por_alvo_poco", []) or [])

    if limiares:
        grouped: Dict[str, Dict[str, List[float]]] = {}
        for item in limiares:
            if not isinstance(item, dict):
                continue
            alvo = _normalize_target(item.get("alvo"))
            if not alvo:
                continue
            bucket = grouped.setdefault(alvo, {"mins": [], "dets": [], "inc_starts": [], "incs": []})
            detect_lim = safe_float(item.get("ct_detectavel_limite"), default_rule["ct_detectavel_limite"])
            bucket["mins"].append(safe_float(item.get("ct_minimo"), default_rule["ct_minimo"]))
            bucket["dets"].append(detect_lim)
            bucket["inc_starts"].append(
                safe_float(item.get("ct_inconclusivo_min"), detect_lim + 0.01)
            )
            bucket["incs"].append(
                safe_float(item.get("ct_inconclusivo_limite"), default_rule["ct_inconclusivo_limite"])
            )

        for alvo, bucket in grouped.items():
            by_target[alvo] = {
                "ct_minimo": min(bucket["mins"]) if bucket["mins"] else default_rule["ct_minimo"],
                "ct_detectavel_limite": max(bucket["dets"]) if bucket["dets"] else default_rule["ct_detectavel_limite"],
                "ct_inconclusivo_min": min(bucket["inc_starts"])
                if bucket["inc_starts"]
                else default_rule["ct_inconclusivo_min"],
                "ct_inconclusivo_limite": max(bucket["incs"]) if bucket["incs"] else default_rule["ct_inconclusivo_limite"],
            }

    for target_name in _resolve_targets(cfg).keys():
        if target_name not in by_target:
            by_target[target_name] = dict(default_rule)

    faixas = getattr(cfg, "faixas_ct", {}) or {}
    rp_min = safe_float(faixas.get("rp_min"), rp_min_fallback)
    rp_max = safe_float(faixas.get("rp_max"), rp_max_fallback)

    return {
        "exame": str(getattr(cfg, "nome_exame", exam_name) or exam_name),
        "default_rule": default_rule,
        "by_target": by_target,
        "rp_min": rp_min,
        "rp_max": rp_max,
        "has_v2": bool(limiares),
    }


def _resolve_effective_rule(
    *,
    default_rule: Dict[str, Any],
    target_rule: Dict[str, Any],
) -> Dict[str, float]:
    rule: Dict[str, float] = dict(default_rule or {})
    rule.update(target_rule or {})

    detect_lim = safe_float(rule.get("ct_detectavel_limite"), 35.0)
    rule["ct_inconclusivo_min"] = safe_float(
        rule.get("ct_inconclusivo_min"),
        detect_lim + 0.01,
    )

    if default_rule and target_rule:
        default_inconc_min = safe_float(
            default_rule.get("ct_inconclusivo_min"),
            safe_float(default_rule.get("ct_detectavel_limite"), 35.0) + 0.01,
        )
        # A faixa global de inconclusivo é autoridade para início.
        rule["ct_inconclusivo_min"] = default_inconc_min
        rule["ct_inconclusivo_limite"] = min(
            safe_float(target_rule.get("ct_inconclusivo_limite"), rule.get("ct_inconclusivo_limite", 40.0)),
            safe_float(default_rule.get("ct_inconclusivo_limite"), rule.get("ct_inconclusivo_limite", 40.0)),
        )

    return rule


def classify_ct_with_runtime_profile(
    ct_val: Any,
    *,
    target_name: str,
    profile: Dict[str, Any],
) -> str:
    target_key = _normalize_target(target_name)
    default_rule = dict(profile.get("default_rule", {}) or {})
    target_rule = dict(profile.get("by_target", {}).get(target_key) or {})
    rule = _resolve_effective_rule(default_rule=default_rule, target_rule=target_rule)

    if _is_blank_ct(ct_val):
        return "Nao Detectavel"

    try:
        ct = float(str(ct_val).replace(",", "."))
    except Exception:
        return "Nao Detectavel"

    ct_min = safe_float(rule.get("ct_minimo"), 10.0)
    detect_lim = safe_float(rule.get("ct_detectavel_limite"), 35.0)
    inconc_min = safe_float(rule.get("ct_inconclusivo_min"), detect_lim + 0.01)
    inconc_lim = safe_float(rule.get("ct_inconclusivo_limite"), 40.0)

    if ct < ct_min:
        return "Nao Detectavel"
    if inconc_min <= ct <= inconc_lim:
        return "Indeterminado"
    if ct <= detect_lim and ct < inconc_min:
        return "Detectavel"
    if ct <= inconc_lim:
        return "Indeterminado"
    return "Nao Detectavel"


def build_protocol_and_rules_from_cfg(
    cfg: Any,
    *,
    protocol_id: str,
) -> Tuple[Dict[str, Any] | None, Dict[str, Any] | None]:
    if not cfg:
        return None, None

    targets_configuration = _resolve_targets(cfg)
    if not targets_configuration:
        return None, None

    profile = build_runtime_rule_profile_from_cfg(
        cfg,
        exam_name=protocol_id,
        rp_min_fallback=10.0,
        rp_max_fallback=35.0,
    )
    by_target = profile.get("by_target", {}) or {}
    default_rule = profile.get("default_rule", {}) or {}

    rules: List[Dict[str, Any]] = []
    for target_name in targets_configuration.keys():
        lim = _resolve_effective_rule(
            default_rule=default_rule,
            target_rule=dict(by_target.get(target_name) or {}),
        )
        ct_min = safe_float(lim.get("ct_minimo"), 10.0)
        ct_detect = safe_float(lim.get("ct_detectavel_limite"), 35.0)
        ct_inconc_min = safe_float(lim.get("ct_inconclusivo_min"), ct_detect + 0.01)
        ct_inconc = safe_float(lim.get("ct_inconclusivo_limite"), 40.0)
        rules.append(
            {
                "target": target_name,
                "default_result": "Nao Detectavel",
                "conditions": [
                    {
                        "range": [ct_min, max(ct_min, min(ct_detect, ct_inconc_min) - 0.0001)],
                        "result": "Detectavel",
                    },
                    {
                        "range": [ct_inconc_min, ct_inconc],
                        "result": "Indeterminado",
                    },
                ],
            }
        )

    protocol = {
        "id": protocol_id,
        "display_name": str(getattr(cfg, "nome_exame", protocol_id)),
        "targets_configuration": targets_configuration,
        "validation_rules": {
            "run_validation": [
                {
                    "rule": "CONTROL_EXISTS",
                    "target": "CN",
                    "severity": "FATAL",
                    "error_msg": "Controle Negativo NAO encontrado na placa!",
                },
                {
                    "rule": "CONTROL_EXISTS",
                    "target": "CP",
                    "severity": "WARNING",
                    "error_msg": "Controle Positivo ausente.",
                },
            ]
        },
    }
    rules_cfg = {"protocol_id": protocol_id, "rules": rules}
    return protocol, rules_cfg
