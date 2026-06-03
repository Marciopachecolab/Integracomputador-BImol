"""
Geração de mapa da placa (Excel) a partir de df_final já interpretado.
- Salva por padrão em reports/placa_{timestamp}.xlsx
- Cada célula mostra amostra/código e todos os alvos com resultado e CT (3 casas decimais).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from services.core.config_service import config_service
from ui.components.plate_viewer import WellResult, exportar_placa_excel
from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, call_with_retry

ROWS = "ABCDEFGH"
COLS = list(range(1, 13))


def _resolve_reports_dir() -> str:
    """Resolve o diretório de saída para relatórios usando config_service."""
    try:
        paths = config_service.get_paths()
        return (
            paths.get("reports_dir")
            or paths.get("default_results_folder")
            or "reports"
        )
    except Exception:
        return "reports"


def _split_well(poco: str) -> Optional[Tuple[int, int]]:
    if not poco:
        return None
    row_part = "".join(ch for ch in poco if ch.isalpha()).upper()
    col_part = "".join(ch for ch in poco if ch.isdigit())
    if not row_part or not col_part:
        return None
    try:
        r = ROWS.index(row_part)
        c = int(col_part) - 1
        if r < 0 or r >= 8 or c < 0 or c >= 12:
            return None
        return r, c
    except Exception:
        return None


def _map_result(val: Any) -> str:
    s = str(val or "").strip().lower()
    if "inval" in s:
        return "Invalido"
    if "inconc" in s:
        return "Inconclusivo"
    if "nao" in s and "detect" in s:
        return "Nao Detectado"
    if "detect" in s:
        return "Detectado"
    return ""


def _collect_targets(row: pd.Series) -> List[Tuple[str, str, Optional[float]]]:
    """Retorna lista de (alvo, resultado, ct) para todas as colunas Resultado_*."""
    targets: List[Tuple[str, str, Optional[float]]] = []
    for col in row.index:
        if str(col).startswith("Resultado_"):
            base = str(col)[len("Resultado_") :].strip()
            res = _map_result(row.get(col))
            ct_val: Optional[float] = None
            for cand in row.index:
                c_up = str(cand).upper().replace(" ", "").replace("_", "")
                b_up = base.upper().replace(" ", "").replace("_", "")
                if c_up == b_up:
                    v = row.get(cand)
                    if v is None or (isinstance(v, float) and pd.isna(v)):
                        ct_val = None
                    else:
                        try:
                            ct_val = round(float(v), 3)
                        except Exception:
                            ct_val = None
                    break
            targets.append((base, res, ct_val))
    # RP médios
    rp_vals = []
    for col in row.index:
        if str(col).upper().startswith("RP"):
            v = row.get(col)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                continue
            try:
                rp_vals.append(round(float(v), 3))
            except Exception:
                continue
    if rp_vals:
        targets.append(("RP", "", sum(rp_vals) / len(rp_vals)))
    return targets


def _build_well_results(df_final: pd.DataFrame) -> List[WellResult]:
    wells: Dict[Tuple[int, int], WellResult] = {}
    for _, r in df_final.iterrows():
        poco_raw_full = str(r.get("Poco", "")).strip()
        poco_list = [p.strip() for p in poco_raw_full.split("+") if p.strip()]
        targets = _collect_targets(r)
        # escolhe principal: detectado se houver, senão primeiro
        res = ""
        ct_t = None
        for base, res_val, ct_val in targets:
            if res == "" or res_val == "Detectado":
                res = res_val
                ct_t = ct_val
        sample = str(r.get("Amostra", "")).strip()
        code = str(r.get("Codigo", "")).strip()
        ct_rp = None
        for t, _, ct in targets:
            if t.upper().startswith("RP") and ct is not None:
                ct_rp = ct
                break
        is_ctrl = any(tag in sample.upper() for tag in ["CN", "CP"])
        ctrl_type = "CN" if "CN" in sample.upper() else ("CP" if "CP" in sample.upper() else None)

        for poco_raw in poco_list:
            parsed = _split_well(poco_raw)
            if not parsed:
                continue
            wells[parsed] = WellResult(
                well=poco_raw,
                sample_code=code or sample,
                ct_target=ct_t,
                ct_rp=ct_rp,
                result=res,
                is_control=is_ctrl,
                control_type=ctrl_type,
            )
            wells[parsed]._targets = targets  # type: ignore

    results: List[WellResult] = []
    for r in range(8):
        for c in range(12):
            res_obj = wells.get((r, c))
            if res_obj:
                results.append(res_obj)
            else:
                well_name = f"{ROWS[r]}{c+1}"
                results.append(
                    WellResult(
                        well=well_name,
                        sample_code="",
                        ct_target=None,
                        ct_rp=None,
                        result="",
                        is_control=False,
                        control_type=None,
                    )
                )
    return results


def gerar_mapa_placa_final(df_final: pd.DataFrame, path_xlsx: Optional[str] = None) -> str:
    """Gera o mapa da placa em Excel e retorna o caminho salvo."""
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    if path_xlsx is None:
        reports_dir = _resolve_reports_dir()
        path_xlsx = os.path.join(reports_dir, f"placa_{ts}.xlsx")
    wells = _build_well_results(df_final)
    output_dir = os.path.dirname(path_xlsx)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    policy = RetryPolicy.from_env()
    with CSVFileLock(path_xlsx):
        call_with_retry(
            lambda: exportar_placa_excel(wells, path_xlsx),
            op_name="export_placa_excel",
            path=path_xlsx,
            policy=policy,
        )
    return path_xlsx


__all__ = ["gerar_mapa_placa_final"]
