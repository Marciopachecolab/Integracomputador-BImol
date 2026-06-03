"""Gera/valida baseline funcional da Fase 0 (parser, analise, GAL e historico)."""

from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

warnings.filterwarnings(
    "ignore",
    message="Workbook contains no default style, apply openpyxl's default",
)

from exportacao.gal_formatter import formatar_para_gal
from models import AppState
from services.analysis.analysis_service import AnalysisService
from services.core.config_service import config_service
from services.equipment.equipment_detector import detectar_equipamento
from services.reports.history_report import HistoryReportService
from services.core.runtime_flags import (
    is_contract_analysis_runtime_enabled,
    is_contract_parser_enabled,
    is_legacy_panel_csv_enabled,
)

import os

DEFAULT_FIXTURE_7500 = Path(
    os.environ.get("PHASE0_FIXTURE_7500", "tests/fixtures/fixture_7500.xlsx")
)
DEFAULT_FIXTURE_QUANTI = Path(
    os.environ.get("PHASE0_FIXTURE_QUANTI", "tests/fixtures/fixture_quanti.xlsx")
)
DEFAULT_EXAME = "VR1e2 Biomanguinhos 7500"
DEFAULT_OUTPUT = Path("snapshots/phase0_runtime_baseline.json")


def _df_hash(df: pd.DataFrame) -> str:
    safe_df = df.astype(str)
    csv_text = safe_df.to_csv(index=False, sep=";")
    return hashlib.sha256(csv_text.encode("utf-8")).hexdigest()


def _analysis_summary(df: pd.DataFrame) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "rows": int(len(df)),
        "columns": [str(col) for col in df.columns.tolist()],
        "frame_hash_sha256": _df_hash(df),
    }

    if "Resultado_geral" in df.columns:
        resultado = df["Resultado_geral"].astype(str).replace({"nan": "", "NaT": ""})
        summary["resultado_geral_counts"] = resultado.value_counts().to_dict()
    else:
        summary["resultado_geral_counts"] = {}

    preview_cols = [col for col in ["Amostra", "Poço(s)", "PoÃ§o(s)", "Resultado_geral"] if col in df.columns]
    if preview_cols:
        summary["preview"] = df[preview_cols].head(5).astype(str).to_dict(orient="records")
    else:
        summary["preview"] = df.head(3).astype(str).to_dict(orient="records")
    return summary


def _collect_detection(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"status": "fixture_missing", "path": str(path)}
    try:
        detection = detectar_equipamento(str(path))
        return {
            "status": "ok",
            "path": str(path),
            "equipamento": detection.get("equipamento"),
            "confianca": detection.get("confianca"),
            "alternativas_top3": detection.get("alternativas", [])[:3],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "path": str(path),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }


def _collect_analysis(path: Path, exame: str) -> tuple[Dict[str, Any], Optional[pd.DataFrame]]:
    if not path.exists():
        return {"status": "fixture_missing", "path": str(path)}, None
    service = AnalysisService(AppState())
    try:
        result = service.analisar_corrida(
            exame=exame,
            arquivo_resultados=path,
            arquivo_extracao=None,
            lote="PHASE0-BASELINE",
        )
        df = result.df_processado.copy()
        return {
            "status": "ok",
            "path": str(path),
            "summary": _analysis_summary(df),
        }, df
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "path": str(path),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }, None


def _collect_gal(analysis_df: Optional[pd.DataFrame], exame: str) -> Dict[str, Any]:
    if analysis_df is None or analysis_df.empty:
        return {"status": "skipped", "reason": "analysis_not_available"}

    df_gal = formatar_para_gal(analysis_df, exame=exame)
    return {
        "status": "ok",
        "rows": int(len(df_gal)),
        "columns": [str(col) for col in df_gal.columns.tolist()],
        "frame_hash_sha256": _df_hash(df_gal),
    }


def _collect_history_probe() -> Dict[str, Any]:
    original_config = copy.deepcopy(config_service._config)
    try:
        base_dir = Path("tests/.tmp") / f"phase0_history_{uuid4().hex}"
        csv_path = base_dir / "historicos" / "historico_analises.csv"
        base_dir.mkdir(parents=True, exist_ok=True)
        config_service._config = {
            "storage_backend": "csv",
            "data_root": str(base_dir),
            "paths": {"gal_history_csv": str(csv_path)},
        }
        service = HistoryReportService()
        ok = service.adicionar_registro(
            {
                "exame": "VR1",
                "equipamento": "7500",
                "usuario": "phase0",
                "num_placa": "P0",
                "status_corrida": "OK",
                "total_amostras": 1,
                "total_detectados": 0,
                "total_nao_detectados": 1,
                "total_inconclusivos": 0,
                "total_invalidos": 0,
                "arquivo_corrida": "phase0.xlsx",
                "observacoes": "phase0",
            }
        )
        df = service.ler_historico(limit=100)
        return {
            "status": "ok" if ok else "error",
            "path": str(csv_path),
            "rows": int(len(df)),
            "columns": [str(col) for col in df.columns.tolist()],
            "frame_hash_sha256": _df_hash(df) if not df.empty else None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
    finally:
        config_service._config = original_config


def build_snapshot(*, fixture_7500: Path, fixture_quanti: Path, exame: str) -> Dict[str, Any]:
    if not fixture_7500.exists() and not fixture_quanti.exists():
        raise FileNotFoundError("Nenhum fixture encontrado para baseline da fase 0.")

    analysis_7500, analysis_7500_df = _collect_analysis(fixture_7500, exame)
    analysis_quanti, _ = _collect_analysis(fixture_quanti, exame)
    return {
        "meta": {
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "exame": exame,
            "fixtures": {
                "7500": str(fixture_7500),
                "quanti": str(fixture_quanti),
            },
        },
        "flags": {
            "contract_parser_enabled": is_contract_parser_enabled(),
            "contract_analysis_runtime_enabled": is_contract_analysis_runtime_enabled(),
            "legacy_panel_csv_enabled": is_legacy_panel_csv_enabled(),
        },
        "parser_detection": {
            "7500": _collect_detection(fixture_7500),
            "quanti": _collect_detection(fixture_quanti),
        },
        "analysis": {
            "7500": analysis_7500,
            "quanti": analysis_quanti,
        },
        "gal_export": _collect_gal(analysis_7500_df, exame),
        "history_probe": _collect_history_probe(),
    }


def _normalize_for_compare(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = copy.deepcopy(payload)
    normalized.get("meta", {}).pop("generated_at_utc", None)
    history_probe = normalized.get("history_probe", {})
    if isinstance(history_probe, dict):
        history_probe.pop("path", None)
        history_probe.pop("frame_hash_sha256", None)
    return normalized


def write_snapshot(snapshot: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def check_snapshot(snapshot: Dict[str, Any], output_path: Path) -> int:
    if not output_path.exists():
        print(f"[phase0] baseline nao encontrado: {output_path}")
        return 2

    expected = json.loads(output_path.read_text(encoding="utf-8"))
    left = json.dumps(_normalize_for_compare(expected), indent=2, ensure_ascii=False, sort_keys=True)
    right = json.dumps(_normalize_for_compare(snapshot), indent=2, ensure_ascii=False, sort_keys=True)
    if left == right:
        print("[phase0] baseline confere com o snapshot atual.")
        return 0

    print("[phase0] baseline divergente. Diff:")
    for line in difflib.unified_diff(left.splitlines(), right.splitlines(), lineterm=""):
        print(line)
    return 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Baseline funcional da fase 0.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="Compara com snapshot salvo.")
    parser.add_argument("--exame", default=DEFAULT_EXAME)
    parser.add_argument("--fixture-7500", type=Path, default=DEFAULT_FIXTURE_7500)
    parser.add_argument("--fixture-quanti", type=Path, default=DEFAULT_FIXTURE_QUANTI)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshot = build_snapshot(
        fixture_7500=args.fixture_7500,
        fixture_quanti=args.fixture_quanti,
        exame=args.exame,
    )
    if args.check:
        return check_snapshot(snapshot, args.output)

    write_snapshot(snapshot, args.output)
    print(f"[phase0] baseline atualizado em: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
