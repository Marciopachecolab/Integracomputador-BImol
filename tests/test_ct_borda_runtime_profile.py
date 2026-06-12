# -*- coding: utf-8 -*-
"""Bordas de CT pelo PERFIL DE RUNTIME canonico (FINDING-011 / CA-02).

O fluxo real de analise escreve o resultado por alvo usando
`classify_ct_with_runtime_profile` (perfil por exame via `faixas_ct`) — fonte
CANONICA. O classificador base (`config.business_rules` /
`domain.ct_rules.classificar_ct` / `logic_engine`) e legado/shadow (calculado
apenas como `legacy_status` de paridade) e diverge nas bordas 8.0/35.0.

Este teste carrega os `faixas_ct` REAIS dos exames canonicos e valida que o
classificador runtime produz exatamente as bordas de `requirements.md §5`.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.analysis.analysis_runtime_contract import (
    _resolve_default_rule,
    classify_ct_with_runtime_profile,
)

_ROOT = Path(__file__).resolve().parents[1]


def _profile_for(exam_file: str) -> dict:
    cfg = json.loads((_ROOT / "config" / "exams" / exam_file).read_text(encoding="utf-8"))
    ns = SimpleNamespace(faixas_ct=cfg.get("faixas_ct", {}) or {})
    return {"default_rule": _resolve_default_rule(ns), "by_target": {}}


# requirements.md §5.1 — VR1e2: Detectavel 8.01<=CT<=35.0; Indeterminado 35.01<=CT<=40.0
@pytest.mark.parametrize(
    "ct,esperado",
    [
        ("8.0", "Nao Detectavel"),
        ("8.01", "Detectavel"),
        ("20.0", "Detectavel"),
        ("35.0", "Detectavel"),
        ("35.01", "Indeterminado"),
        ("40.0", "Indeterminado"),
        ("40.01", "Nao Detectavel"),
    ],
)
def test_borda_vr1e2(ct, esperado):
    prof = _profile_for("vr1e2_biomanguinhos_7500.json")
    assert classify_ct_with_runtime_profile(ct, target_name="SC2", profile=prof) == esperado


# requirements.md §5.2 — ZDC: Detectavel 8.1<=CT<38.1; Indeterminado 38.1<=CT<=40.0
@pytest.mark.parametrize(
    "ct,esperado",
    [
        ("8.0", "Nao Detectavel"),
        ("8.1", "Detectavel"),
        ("20.0", "Detectavel"),
        ("38.0", "Detectavel"),
        ("38.1", "Indeterminado"),
        ("40.0", "Indeterminado"),
        ("40.01", "Nao Detectavel"),
    ],
)
def test_borda_zdc(ct, esperado):
    prof = _profile_for("zdcbm.json")
    assert classify_ct_with_runtime_profile(ct, target_name="ZK", profile=prof) == esperado
