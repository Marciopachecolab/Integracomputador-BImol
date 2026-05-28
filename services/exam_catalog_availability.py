"""Helpers de disponibilidade/paridade para catalogo de exames na analise."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from services.exam_domain_contracts import is_control_internal_type


REPORT_PREFIX = "0260325_exam_availability_parity"


def _norm(value: str) -> str:
    import unicodedata

    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    return text.encode("ascii", "ignore").decode("ascii")


def _unique_names(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for raw in values:
        name = str(raw or "").strip()
        if not name:
            continue
        key = _norm(name)
        if key in seen:
            continue
        seen.add(key)
        out.append(name)
    return out


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


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


def _derive_legacy_from_v2(cfg: Any) -> Dict[str, Any]:
    targets = list(getattr(cfg, "targets_por_poco", []) or [])
    limiares = list(getattr(cfg, "limiares_ct_por_alvo_poco", []) or [])

    alvos: List[str] = []
    controles_cp: List[str] = []
    for item in targets:
        if not isinstance(item, dict):
            continue
        alvo = str(item.get("alvo", "")).strip()
        tipo = str(item.get("tipo", "")).strip().upper()
        if alvo and alvo not in alvos:
            alvos.append(alvo)
        if is_control_internal_type(tipo) and alvo and alvo not in controles_cp:
            controles_cp.append(alvo)

    detect_values = [_safe_float(item.get("ct_detectavel_limite"), 35.0) for item in limiares if isinstance(item, dict)]
    inconc_values = [_safe_float(item.get("ct_inconclusivo_limite"), 40.0) for item in limiares if isinstance(item, dict)]
    min_values = [_safe_float(item.get("ct_minimo"), 10.0) for item in limiares if isinstance(item, dict)]

    detect_min = min(detect_values) if detect_values else 35.0
    detect_max = max(detect_values) if detect_values else 35.0
    inconc_max = max(inconc_values) if inconc_values else 40.0
    rp_min = min(min_values) if min_values else 10.0

    return {
        "alvos": alvos,
        "controles_cp": controles_cp,
        "faixas_ct": {
            "detect_max": detect_max,
            "inconc_min": min(45.0, detect_min + 0.01),
            "inconc_max": inconc_max,
            "rp_min": rp_min,
            "rp_max": detect_max,
        },
    }


def evaluate_v2_legacy_parity(cfg: Any) -> Dict[str, Any]:
    targets = list(getattr(cfg, "targets_por_poco", []) or [])
    limiares = list(getattr(cfg, "limiares_ct_por_alvo_poco", []) or [])
    has_v2 = bool(targets and limiares)

    result: Dict[str, Any] = {
        "exam_name": str(getattr(cfg, "nome_exame", "") or ""),
        "has_v2": has_v2,
        "critical_divergences": [],
    }
    if not has_v2:
        return result

    derived = _derive_legacy_from_v2(cfg)
    actual_alvos = [str(v).strip() for v in list(getattr(cfg, "alvos", []) or []) if str(v).strip()]
    if {_norm(v) for v in derived["alvos"]} != {_norm(v) for v in actual_alvos}:
        result["critical_divergences"].append(
            {
                "field": "alvos",
                "expected": derived["alvos"],
                "actual": actual_alvos,
            }
        )

    actual_faixas = getattr(cfg, "faixas_ct", {}) or {}
    for field, expected in derived["faixas_ct"].items():
        actual = _safe_float(actual_faixas.get(field), expected)
        if abs(actual - expected) > 0.05:
            result["critical_divergences"].append(
                {
                    "field": f"faixas_ct.{field}",
                    "expected": round(expected, 4),
                    "actual": round(actual, 4),
                }
            )

    controls = getattr(cfg, "controles", {}) or {}
    actual_cp = [str(v).strip() for v in list(controls.get("cp", []) or []) if str(v).strip()]
    if {_norm(v) for v in derived["controles_cp"]} != {_norm(v) for v in actual_cp}:
        result["critical_divergences"].append(
            {
                "field": "controles.cp",
                "expected": derived["controles_cp"],
                "actual": actual_cp,
            }
        )
    return result


def build_availability_report(
    *,
    registry_configs: Iterable[Any],
    legacy_exam_names: Iterable[str],
    selected_exam_names: Iterable[str],
    fetch_latency_ms: float,
    latency_samples_ms: Iterable[float],
    p95_target_ms: float,
    source_mode: str,
) -> Dict[str, Any]:
    registry_list = [cfg for cfg in registry_configs]
    registry_names = _unique_names(getattr(cfg, "nome_exame", "") for cfg in registry_list)
    legacy_names = _unique_names(legacy_exam_names)
    selected_names = _unique_names(selected_exam_names)

    selected_keys = {_norm(name) for name in selected_names}
    missing_registry_in_selected = [name for name in registry_names if _norm(name) not in selected_keys]

    parity = [evaluate_v2_legacy_parity(cfg) for cfg in registry_list]
    parity_critical = [
        {"exam_name": row["exam_name"], "issues": row["critical_divergences"]}
        for row in parity
        if row["critical_divergences"]
    ]

    for name in missing_registry_in_selected:
        parity_critical.append(
            {
                "exam_name": name,
                "issues": [
                    {
                        "field": "availability",
                        "expected": "presente_na_lista_selecionavel",
                        "actual": "ausente",
                    }
                ],
            }
        )

    samples = [float(v) for v in latency_samples_ms]
    p95_latency = _percentile(samples, 95.0)
    p95_ok = p95_latency <= float(p95_target_ms)
    parity_ok = len(parity_critical) == 0

    return {
        "report_id": REPORT_PREFIX,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_mode": source_mode,
        "slo": {
            "p95_target_ms": float(p95_target_ms),
            "p95_latency_ms": round(p95_latency, 3),
            "last_fetch_latency_ms": round(float(fetch_latency_ms), 3),
            "p95_within_target": p95_ok,
        },
        "totals": {
            "registry_exams": len(registry_names),
            "legacy_exams": len(legacy_names),
            "selected_exams": len(selected_names),
            "v2_registry_exams": sum(1 for row in parity if row["has_v2"]),
            "critical_divergences": len(parity_critical),
        },
        "critical_divergences": parity_critical,
        "is_parity_ok": parity_ok,
        "overall_ok": bool(parity_ok and p95_ok),
    }


def persist_availability_report(
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
