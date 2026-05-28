# -*- coding: utf-8 -*-
"""Checklist executavel de rollout/hardening do visualizador operacional (F7)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from services.legacy_audit.operational_tabular_viewer import (
    OperationalTabularViewer,
    QueryOptions,
    SUPPORTED_VIEWS,
)
from services.core.runtime_flags import is_operational_tabular_viewer_enabled


@dataclass(frozen=True)
class RolloutCheckItem:
    """Item de checklist executavel."""

    id: str
    ok: bool
    details: str


def run_operational_viewer_rollout_check(
    *,
    viewer: Optional[OperationalTabularViewer] = None,
    output_dir: Optional[str | Path] = None,
    user_id: Optional[str] = None,
    legacy_fallback_checker: Optional[Callable[[], bool]] = None,
) -> Dict[str, object]:
    """Executa checklist operacional de readiness para rollout da F7."""
    run_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    active_viewer = viewer or OperationalTabularViewer()
    checks: List[RolloutCheckItem] = []

    flag_enabled = is_operational_tabular_viewer_enabled(user_id=user_id)
    checks.append(
        RolloutCheckItem(
            id="flag_operational_viewer_resolvida",
            ok=True,
            details=f"flag_resolvida={flag_enabled}",
        )
    )

    for view in SUPPORTED_VIEWS:
        try:
            result = active_viewer.query(QueryOptions(view=view, page_size=20))
            checks.append(
                RolloutCheckItem(
                    id=f"consulta_view_{view}",
                    ok=True,
                    details=f"rows={result.total_rows} columns={len(result.available_columns)}",
                )
            )
        except Exception as exc:
            checks.append(
                RolloutCheckItem(
                    id=f"consulta_view_{view}",
                    ok=False,
                    details=f"erro={exc}",
                )
            )

    try:
        empty_case = active_viewer.query(
            QueryOptions(view="corridas", busca_textual="__sem_resultado_f7__", page_size=20)
        )
        checks.append(
            RolloutCheckItem(
                id="consulta_sem_resultado_controlada",
                ok=(empty_case.total_rows == 0),
                details=f"rows={empty_case.total_rows}",
            )
        )
    except Exception as exc:
        checks.append(
            RolloutCheckItem(
                id="consulta_sem_resultado_controlada",
                ok=False,
                details=f"erro={exc}",
            )
        )

    export_base = Path(output_dir) if output_dir else (Path("reports") / "rollout_f7")
    export_base.mkdir(parents=True, exist_ok=True)
    try:
        corridas = active_viewer.query(QueryOptions(view="corridas", page_size=50))
        csv_path = active_viewer.export_dataframe(
            dataframe=corridas.rows,
            output_path=export_base / "rollout_check_corridas",
            file_format="csv",
        )
        xlsx_path = active_viewer.export_dataframe(
            dataframe=corridas.rows,
            output_path=export_base / "rollout_check_corridas",
            file_format="xlsx",
        )
        checks.append(
            RolloutCheckItem(
                id="exportacao_csv_xlsx",
                ok=csv_path.exists() and xlsx_path.exists(),
                details=f"csv={csv_path.name};xlsx={xlsx_path.name}",
            )
        )
    except Exception as exc:
        checks.append(
            RolloutCheckItem(
                id="exportacao_csv_xlsx",
                ok=False,
                details=f"erro={exc}",
            )
        )

    try:
        if legacy_fallback_checker is None:
            checks.append(
                RolloutCheckItem(
                    id="fallback_legado_disponivel",
                    ok=True,
                    details="nao_avaliado_sem_adapter_injetado",
                )
            )
        else:
            checks.append(
                RolloutCheckItem(
                    id="fallback_legado_disponivel",
                    ok=bool(legacy_fallback_checker()),
                    details="validado_por_adapter_injetado",
                )
            )
    except Exception as exc:
        checks.append(
            RolloutCheckItem(
                id="fallback_legado_disponivel",
                ok=False,
                details=f"erro={exc}",
            )
        )

    all_ok = all(item.ok for item in checks)
    return {
        "executado_em": run_at,
        "ok": all_ok,
        "total_itens": len(checks),
        "itens_ok": sum(1 for item in checks if item.ok),
        "itens_falhos": sum(1 for item in checks if not item.ok),
        "itens": [
            {"id": item.id, "ok": item.ok, "details": item.details}
            for item in checks
        ],
    }


__all__ = ["RolloutCheckItem", "run_operational_viewer_rollout_check"]
