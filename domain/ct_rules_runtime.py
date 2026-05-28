# -*- coding: utf-8 -*-
"""
domain/ct_rules_runtime.py

Classificação de Ct com perfis de regras dinâmicos por exame (RuntimeRuleProfile).

Complemento puro de domain/ct_rules.py: quando has_v2=False, delega para
classificar_ct() (thresholds VR1E2 fixos); quando has_v2=True, usa as faixas
por alvo/poço vindas de build_runtime_rule_profile_from_cfg.

Sem I/O, sem pandas, sem tkinter, sem selenium.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from domain.ct_rules import ResultadoCt, classificar_ct


def _lookup_rule(alvo: str, runtime_profile: Dict[str, Any]) -> Dict[str, float]:
    """Retorna a regra de Ct para o alvo, com fallback para default_rule."""
    by_target: Dict[str, Any] = runtime_profile.get("by_target", {}) or {}
    default_rule: Dict[str, Any] = runtime_profile.get("default_rule", {}) or {}
    
    def _normalize(s: str) -> str:
        return str(s).strip().upper().replace("_", " ").replace("  ", " ")

    alvo_key = _normalize(alvo)
    target_rule: Dict[str, Any] = {}
    
    for k, v in by_target.items():
        if _normalize(k) == alvo_key:
            target_rule = dict(v)
            break

    rule = {**dict(default_rule), **target_rule}
    if default_rule and target_rule:
        rule["ct_inconclusivo_min"] = float(
            default_rule.get(
                "ct_inconclusivo_min",
                target_rule.get("ct_inconclusivo_min", float(rule.get("ct_detectavel_limite", 35.0)) + 0.01),
            )
        )
        rule["ct_inconclusivo_limite"] = min(
            float(target_rule.get("ct_inconclusivo_limite", rule.get("ct_inconclusivo_limite", 40.0))),
            float(default_rule.get("ct_inconclusivo_limite", rule.get("ct_inconclusivo_limite", 40.0))),
        )
    return rule


def classificar_ct_por_exame(
    valor: Optional[float],
    alvo: str,
    poco: str,
    runtime_profile: Dict[str, Any],
) -> ResultadoCt:
    """Classifica um valor de Ct usando o perfil de runtime do exame.

    Args:
        valor: Valor numérico de Ct (ou None para ausente/inválido).
        alvo: Nome do alvo (ex.: "ZK", "ADV", "SC2").
        poco: Posição do poço (ex.: "A1") — reservado para regras futuras por poço.
        runtime_profile: Dict retornado por build_runtime_rule_profile_from_cfg.
                         Chave "has_v2" indica se há regras por alvo específicas.

    Returns:
        ResultadoCt: DETECTADO, INCONCLUSIVO ou NAO_DETECTADO.
    """
    if not runtime_profile or not (
        runtime_profile.get("default_rule") or runtime_profile.get("by_target")
    ):
        return classificar_ct(valor)

    rule = _lookup_rule(alvo, runtime_profile)

    if valor is None:
        return ResultadoCt.NAO_DETECTADO
    try:
        ct = float(valor)
    except (ValueError, TypeError):
        return ResultadoCt.NAO_DETECTADO

    ct_min = float(rule.get("ct_minimo", 10.0))
    detect_lim = float(rule.get("ct_detectavel_limite", 35.0))
    inconc_min = float(rule.get("ct_inconclusivo_min", detect_lim + 0.01))
    inconc_lim = float(rule.get("ct_inconclusivo_limite", 40.0))

    if ct < ct_min:
        return ResultadoCt.NAO_DETECTADO
    if inconc_min <= ct <= inconc_lim:
        return ResultadoCt.INCONCLUSIVO
    if ct <= detect_lim and ct < inconc_min:
        return ResultadoCt.DETECTADO
    return ResultadoCt.NAO_DETECTADO
