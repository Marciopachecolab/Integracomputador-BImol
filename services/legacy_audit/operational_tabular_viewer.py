# -*- coding: utf-8 -*-
"""Visualizador tabular operacional da corrida (Fase 6).

Implementa consultas tabulares com:
- visoes minimas (corridas, mapeamentos, testes da corrida, metadados adicionais);
- filtros obrigatorios (periodo, exame, status, operador, busca textual);
- ordenacao e paginacao para alto volume;
- exportacao CSV/XLSX com fidelidade de colunas do resultado filtrado.
"""

from __future__ import annotations

import json
import math
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from services.core.config_service import config_service
from services.persistence.csv_io import read_csv_strict
from services.operational_export_audit import record_export_audit
from services.operational_handover import (
    apply_handover_decision,
    evaluate_handover_panel,
    evaluate_handover_readiness,
    read_handover_audit,
)
from services.operational_viewer_analytics import summarize_operational_viewer_metrics
from services.operational_viewer_health import (
    apply_operational_viewer_rollback,
    evaluate_operational_health,
)
from services.legacy_audit.operational_slo_governance import (
    read_consolidated_operational_audit,
    read_readiness_audit,
    resolve_operational_policy,
    run_operational_readiness,
    evaluate_slo_compliance,
    get_local_mitigation_state,
    read_contingency_audit,
    run_slo_automation,
    summarize_sli_slo,
    validate_operational_policy,
)
from services.path_resolver import resolve_banco_dir
from services.core.query_latency import record_query_latency
from utils.csv_lock import CSVFileLock
from utils.logger import registrar_log

VIEW_CORRIDAS = "corridas"
VIEW_MAPEAMENTOS = "mapeamentos"
VIEW_TESTES_CORRIDA = "testes_corrida"
VIEW_METADADOS_ADICIONAIS = "metadados_adicionais"

SUPPORTED_VIEWS: Tuple[str, ...] = (
    VIEW_CORRIDAS,
    VIEW_MAPEAMENTOS,
    VIEW_TESTES_CORRIDA,
    VIEW_METADADOS_ADICIONAIS,
)

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000
HIGH_VOLUME_THRESHOLD = 5000
HIGH_VOLUME_PAGE_SIZE_CAP = 200


@dataclass(frozen=True)
class QueryOptions:
    """Parametros de consulta do visualizador."""

    view: str = VIEW_CORRIDAS
    periodo_inicio: Optional[str] = None
    periodo_fim: Optional[str] = None
    exame: Optional[str] = None
    status: Optional[str] = None
    operador: Optional[str] = None
    busca_textual: Optional[str] = None
    sort_by: Optional[str] = None
    sort_direction: str = "desc"
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    user_id: Optional[str] = None


@dataclass(frozen=True)
class QueryResult:
    """Resultado paginado de uma consulta tabular."""

    view: str
    rows: pd.DataFrame
    total_rows: int
    page: int
    page_size: int
    total_pages: int
    available_columns: Tuple[str, ...]
    applied_sort_by: Optional[str]
    applied_sort_direction: str
    is_degraded: bool = False
    degradation_message: Optional[str] = None


class OperationalTabularViewer:
    """Consulta operacional unificada para historico de corridas."""

    def __init__(
        self,
        *,
        logs_dir: Optional[str | Path] = None,
        db_path: Optional[str | Path] = None,
        history_csv_path: Optional[str | Path] = None,
        high_volume_threshold: int = HIGH_VOLUME_THRESHOLD,
        high_volume_page_size_cap: int = HIGH_VOLUME_PAGE_SIZE_CAP,
    ) -> None:
        paths = self._safe_get_paths()
        default_history_path = Path(paths.get("gal_history_csv", "logs/historico_analises.csv"))
        default_logs_dir = Path(paths.get("logs_dir", str(default_history_path.parent)))

        self.logs_dir = Path(logs_dir) if logs_dir else default_logs_dir
        self.db_path = Path(db_path) if db_path else (resolve_banco_dir() / "historico.db")
        self.history_csv_path = (
            Path(history_csv_path) if history_csv_path else default_history_path
        )
        self.high_volume_threshold = max(100, int(high_volume_threshold))
        self.high_volume_page_size_cap = max(50, int(high_volume_page_size_cap))

    @staticmethod
    def _safe_get_paths() -> Dict[str, str]:
        try:
            return config_service.get_paths()
        except Exception:
            return {}

    def query(self, options: QueryOptions) -> QueryResult:
        """Executa consulta tabular com filtros, ordenacao e paginacao."""
        t0 = time.perf_counter()
        view = str(options.view or VIEW_CORRIDAS).strip().lower()
        if view not in SUPPORTED_VIEWS:
            raise ValueError(f"view invalida: {view!r}. Suportadas: {SUPPORTED_VIEWS}")

        try:
            if view == VIEW_CORRIDAS:
                df = self._build_corridas_view()
            elif view == VIEW_MAPEAMENTOS:
                df = self._build_mapeamentos_view()
            elif view == VIEW_TESTES_CORRIDA:
                df = self._build_testes_corrida_view()
            else:
                df = self._build_metadados_adicionais_view()

            filtered = self._apply_common_filters(
                df,
                periodo_inicio=options.periodo_inicio,
                periodo_fim=options.periodo_fim,
                exame=options.exame,
                status=options.status,
                operador=options.operador,
                busca_textual=options.busca_textual,
            )

            sorted_df, applied_sort_by, applied_direction = self._apply_sort(
                filtered,
                sort_by=options.sort_by,
                sort_direction=options.sort_direction,
            )

            requested_page_size = self._normalize_page_size(options.page_size)
            page_size = requested_page_size
            is_degraded = False
            degradation_message: Optional[str] = None
            total_filtered = int(len(sorted_df))
            effective_page_cap = self._resolve_effective_page_cap()
            if (
                total_filtered >= self.high_volume_threshold
                and requested_page_size > effective_page_cap
            ):
                page_size = effective_page_cap
                is_degraded = True
                degradation_message = (
                    f"Alto volume detectado ({total_filtered} linhas). "
                    f"page_size limitado para {page_size}."
                )
                registrar_log(
                    "RuntimeUsage",
                    (
                        "feature=operational_tabular_viewer event=high_volume_degradation "
                        f"view={view} total_rows={total_filtered} "
                        f"requested_page_size={requested_page_size} applied_page_size={page_size}"
                    ),
                    "WARNING",
                )

            paged, page, total_pages = self._apply_pagination(
                sorted_df,
                page=options.page,
                page_size=page_size,
            )
            result = QueryResult(
                view=view,
                rows=paged,
                total_rows=int(len(sorted_df)),
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                available_columns=tuple(str(col) for col in sorted_df.columns),
                applied_sort_by=applied_sort_by,
                applied_sort_direction=applied_direction,
                is_degraded=is_degraded,
                degradation_message=degradation_message,
            )
            duration_ms = (time.perf_counter() - t0) * 1000
            record_query_latency(
                operation="operational_viewer.query",
                backend="mixed",
                duration_ms=duration_ms,
                result_count=result.total_rows,
                meta={
                    "view": view,
                    "has_period_filter": bool(options.periodo_inicio or options.periodo_fim),
                    "has_exame_filter": bool(options.exame),
                    "has_status_filter": bool(options.status),
                    "has_operador_filter": bool(options.operador),
                    "has_text_filter": bool(options.busca_textual),
                    "user_id": str(options.user_id or ""),
                    "requested_page_size": int(requested_page_size),
                    "page_size": int(result.page_size),
                    "is_degraded": bool(result.is_degraded),
                },
            )
            registrar_log(
                "RuntimeUsage",
                (
                    "feature=operational_tabular_viewer event=query_success "
                    f"view={view} rows={result.total_rows} page={result.page}/{max(result.total_pages, 1)}"
                ),
                "INFO",
            )
            return result
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000
            record_query_latency(
                operation="operational_viewer.query",
                backend="mixed",
                duration_ms=duration_ms,
                result_count=0,
                meta={"view": view, "error": str(exc)},
            )
            registrar_log(
                "RuntimeUsage",
                f"feature=operational_tabular_viewer event=query_error view={view} error={exc}",
                "WARNING",
            )
            raise

    def export_dataframe(
        self,
        *,
        dataframe: pd.DataFrame,
        output_path: str | Path,
        file_format: str,
        operator: Optional[str] = None,
        view: Optional[str] = None,
    ) -> Path:
        """Exporta DataFrame filtrado para CSV/XLSX preservando colunas."""
        t0 = time.perf_counter()
        fmt = str(file_format or "").strip().lower()
        if fmt not in {"csv", "xlsx"}:
            raise ValueError("file_format deve ser 'csv' ou 'xlsx'")

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            if fmt == "csv":
                if out.suffix.lower() != ".csv":
                    out = out.with_suffix(".csv")
                dataframe.to_csv(out, sep=";", index=False, encoding="utf-8")
            else:
                if out.suffix.lower() != ".xlsx":
                    out = out.with_suffix(".xlsx")
                dataframe.to_excel(out, index=False)

            corrida_ids = self._collect_corrida_ids(dataframe)
            record_export_audit(
                logs_dir=self.logs_dir,
                operator=str(operator or "").strip(),
                view=str(view or "").strip() or VIEW_CORRIDAS,
                file_format=fmt,
                output_file=str(out),
                row_count=int(len(dataframe)),
                corrida_ids=corrida_ids,
                status="success",
                error="",
            )

            duration_ms = (time.perf_counter() - t0) * 1000
            record_query_latency(
                operation="operational_viewer.export",
                backend=fmt,
                duration_ms=duration_ms,
                result_count=int(len(dataframe)),
                meta={
                    "columns": int(len(dataframe.columns)),
                    "operator": str(operator or ""),
                    "view": str(view or ""),
                },
            )
            registrar_log(
                "RuntimeUsage",
                (
                    "feature=operational_tabular_viewer event=export_success "
                    f"format={fmt} rows={len(dataframe)} file={out.name}"
                ),
                "INFO",
            )
            return out
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000
            record_query_latency(
                operation="operational_viewer.export",
                backend=fmt,
                duration_ms=duration_ms,
                result_count=0,
                meta={
                    "error": str(exc),
                    "operator": str(operator or ""),
                    "view": str(view or ""),
                },
            )
            try:
                record_export_audit(
                    logs_dir=self.logs_dir,
                    operator=str(operator or "").strip(),
                    view=str(view or "").strip() or VIEW_CORRIDAS,
                    file_format=fmt,
                    output_file=str(out),
                    row_count=0,
                    corrida_ids=[],
                    status="error",
                    error=str(exc),
                )
            except Exception:
                pass
            registrar_log(
                "RuntimeUsage",
                f"feature=operational_tabular_viewer event=export_error format={fmt} error={exc}",
                "WARNING",
            )
            raise

    def export_query(
        self,
        *,
        options: QueryOptions,
        output_path: str | Path,
        file_format: str,
        operator: Optional[str] = None,
    ) -> Path:
        """Consulta e exporta o resultado paginado atual."""
        result = self.query(options)
        return self.export_dataframe(
            dataframe=result.rows,
            output_path=output_path,
            file_format=file_format,
            operator=operator or options.user_id,
            view=options.view,
        )

    def get_operational_metrics(self, *, last_n: int = 5000) -> Dict[str, object]:
        """Retorna indicadores operacionais agregados para consulta tabular."""
        return summarize_operational_viewer_metrics(
            logs_dir=self.logs_dir,
            last_n=last_n,
        )

    def get_operational_health(
        self,
        *,
        last_n: int = 5000,
        environment: Optional[str] = None,
    ) -> Dict[str, object]:
        """Retorna resumo de saude operacional com alertas e recomendacoes."""
        metrics = self.get_operational_metrics(last_n=last_n)
        return evaluate_operational_health(
            metrics=metrics,
            environment=environment,
        )

    def get_operational_slo_panel(
        self,
        *,
        environment: Optional[str] = None,
        last_n: int = 10000,
    ) -> Dict[str, object]:
        """Retorna resumo consolidado SLI/SLO com classificacao de severidade."""
        summary = summarize_sli_slo(
            logs_dir=self.logs_dir,
            environment=environment,
            last_n=last_n,
        )
        compliance = evaluate_slo_compliance(summary=summary)
        return {
            "summary": summary,
            "compliance": compliance,
        }

    def run_operational_slo_automation(
        self,
        *,
        environment: Optional[str] = None,
        actor: str = "",
        dry_run: Optional[bool] = None,
        last_n: int = 10000,
    ) -> Dict[str, object]:
        """Executa automacao de resposta operacional baseada em SLO/SLI."""
        return run_slo_automation(
            logs_dir=self.logs_dir,
            environment=environment,
            actor=actor,
            dry_run=dry_run,
            last_n=last_n,
        )

    def apply_operational_rollback(
        self,
        *,
        reason: str,
        actor: str = "",
        dry_run: bool = False,
    ) -> Dict[str, object]:
        """Aplica rollback da feature flag do visualizador operacional."""
        return apply_operational_viewer_rollback(
            reason=reason,
            actor=actor,
            dry_run=dry_run,
        )

    def get_operational_contingency_audit(self, *, limit: int = 200) -> pd.DataFrame:
        """Retorna trilha recente das decisoes de contingencia."""
        return read_contingency_audit(logs_dir=self.logs_dir, limit=limit)

    def get_operational_policy(self, *, environment: Optional[str] = None) -> Dict[str, object]:
        """Retorna politica operacional consolidada por ambiente."""
        return {
            "policy": resolve_operational_policy(environment=environment).__dict__,
        }

    def validate_operational_policy(self, *, environment: Optional[str] = None) -> Dict[str, object]:
        """Valida consistencia da politica operacional."""
        policy = resolve_operational_policy(environment=environment)
        return validate_operational_policy(policy=policy)

    def run_operational_readiness(
        self,
        *,
        environment: Optional[str] = None,
        actor: str = "",
        dry_run: Optional[bool] = None,
        last_n: int = 10000,
    ) -> Dict[str, object]:
        """Executa readiness operacional unificado (F11)."""
        return run_operational_readiness(
            logs_dir=self.logs_dir,
            environment=environment,
            actor=actor,
            dry_run=dry_run,
            last_n=last_n,
        )

    def get_operational_readiness_audit(self, *, limit: int = 200) -> pd.DataFrame:
        """Retorna auditoria de readiness operacional."""
        return read_readiness_audit(logs_dir=self.logs_dir, limit=limit)

    def get_operational_audit_consolidated(self, *, limit: int = 300) -> pd.DataFrame:
        """Retorna trilha consolidada de SLO + contingencia + rollback."""
        return read_consolidated_operational_audit(logs_dir=self.logs_dir, limit=limit)

    def get_operational_handover_readiness(
        self,
        *,
        environment: str,
        last_n: int = 10000,
    ) -> Dict[str, object]:
        """Retorna readiness consolidado de um ambiente para handover."""
        return evaluate_handover_readiness(
            logs_dir=self.logs_dir,
            environment=environment,
            last_n=last_n,
        )

    def get_operational_handover_panel(
        self,
        *,
        environments: Sequence[str] = ("dev", "hml", "prod"),
        last_n: int = 10000,
    ) -> Dict[str, object]:
        """Retorna painel consolidado de handover por ambiente."""
        return evaluate_handover_panel(
            logs_dir=self.logs_dir,
            environments=environments,
            last_n=last_n,
        )

    def apply_operational_handover_decision(
        self,
        *,
        environment: str,
        actor: str,
        decision: Optional[str] = None,
        reason: str = "",
        dry_run: bool = False,
        last_n: int = 10000,
    ) -> Dict[str, object]:
        """Aplica decisao assistida de handover (go/no-go)."""
        return apply_handover_decision(
            logs_dir=self.logs_dir,
            environment=environment,
            actor=actor,
            decision=decision,
            reason=reason,
            dry_run=dry_run,
            last_n=last_n,
        )

    def get_operational_handover_audit(self, *, limit: int = 200) -> pd.DataFrame:
        """Retorna trilha de aceite operacional do handover."""
        return read_handover_audit(logs_dir=self.logs_dir, limit=limit)

    def _build_corridas_view(self) -> pd.DataFrame:
        history = self._load_history_rows()
        columns = [
            "corrida_id",
            "data_hora",
            "data_exame",
            "exame",
            "lote",
            "status_corrida",
            "usuario",
            "nome_corrida",
            "quem_fez_extracao",
            "quem_preparou_placa",
            "observacoes",
            "arquivo_corrida",
            "total_amostras",
            "total_detectados",
            "total_nao_detectados",
            "total_inconclusivos",
            "total_invalidos",
            "registros_associados",
        ]
        if history.empty:
            return pd.DataFrame(columns=columns)

        work = history.copy()
        for col in (
            "corrida_id",
            "data_hora",
            "data_exame",
            "exame",
            "lote",
            "status_corrida",
            "usuario",
            "nome_corrida",
            "quem_fez_extracao",
            "quem_preparou_placa",
            "observacoes",
            "arquivo_corrida",
            "total_amostras",
            "total_detectados",
            "total_nao_detectados",
            "total_inconclusivos",
            "total_invalidos",
        ):
            if col not in work.columns:
                work[col] = ""

        work["corrida_id"] = work.apply(self._resolve_corrida_id, axis=1)
        work["arquivo_corrida"] = work["arquivo_corrida"].map(self._basename_only)

        for col in (
            "total_amostras",
            "total_detectados",
            "total_nao_detectados",
            "total_inconclusivos",
            "total_invalidos",
        ):
            work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0).astype(int)

        work = work.sort_values(
            by=["data_hora", "data_exame"],
            ascending=[False, False],
            na_position="last",
        )
        grouped = work.groupby("corrida_id", as_index=False, dropna=False).agg(
            {
                "data_hora": "first",
                "data_exame": "first",
                "exame": "first",
                "lote": "first",
                "status_corrida": "first",
                "usuario": "first",
                "nome_corrida": "first",
                "quem_fez_extracao": "first",
                "quem_preparou_placa": "first",
                "observacoes": "first",
                "arquivo_corrida": "first",
                "total_amostras": "max",
                "total_detectados": "max",
                "total_nao_detectados": "max",
                "total_inconclusivos": "max",
                "total_invalidos": "max",
            }
        )
        sizes = work.groupby("corrida_id", dropna=False).size().rename("registros_associados")
        grouped = grouped.merge(
            sizes.reset_index(),
            on="corrida_id",
            how="left",
        )
        grouped["registros_associados"] = (
            pd.to_numeric(grouped["registros_associados"], errors="coerce")
            .fillna(0)
            .astype(int)
        )
        return grouped[columns]

    def _build_mapeamentos_view(self) -> pd.DataFrame:
        columns = [
            "corrida_id",
            "exame_id",
            "lote",
            "data_exame",
            "arquivo_extracao",
            "parte_placa",
            "numero_extracao",
            "mapeamento_ref",
            "historico_ref",
            "exportacao_ref",
            "envio_ref",
            "status_execucao",
            "usuario_execucao",
            "atualizado_em",
        ]
        rows = self._load_final_run_reports()
        if rows:
            return pd.DataFrame(rows, columns=columns)

        corridas = self._build_corridas_view()
        if corridas.empty:
            return pd.DataFrame(columns=columns)

        fallback = pd.DataFrame(
            {
                "corrida_id": corridas["corrida_id"],
                "exame_id": corridas["exame"],
                "lote": corridas["lote"],
                "data_exame": corridas["data_exame"],
                "arquivo_extracao": "",
                "parte_placa": "",
                "numero_extracao": "",
                "mapeamento_ref": "",
                "historico_ref": corridas["corrida_id"].map(
                    lambda cid: f"historico_analises#corrida_id={cid}"
                ),
                "exportacao_ref": "",
                "envio_ref": "",
                "status_execucao": "",
                "usuario_execucao": corridas["usuario"],
                "atualizado_em": corridas["data_hora"],
            }
        )
        return fallback[columns]

    def _build_testes_corrida_view(self) -> pd.DataFrame:
        rows = self._load_exam_runs_rows()
        if not rows:
            return pd.DataFrame(
                columns=[
                    "corrida_id",
                    "exame_slug",
                    "data_exame",
                    "hora_exame",
                    "lote",
                    "amostra_codigo",
                    "pocos",
                    "resultado_geral",
                    "status_placa",
                    "equipamento_modelo",
                ]
            )
        return pd.DataFrame(rows)

    def _build_metadados_adicionais_view(self) -> pd.DataFrame:
        corridas = self._build_corridas_view()
        columns = [
            "corrida_id",
            "exame",
            "lote",
            "data_exame",
            "data_hora",
            "usuario",
            "status_corrida",
            "nome_corrida",
            "quem_fez_extracao",
            "quem_preparou_placa",
            "observacoes",
            "nivel_preenchimento_opcional",
            "status_execucao",
            "arquivo_extracao",
            "mapeamento_ref",
        ]
        if corridas.empty:
            return pd.DataFrame(columns=columns)

        mapped = self._build_mapeamentos_view()
        merged = corridas.merge(
            mapped[
                [
                    "corrida_id",
                    "status_execucao",
                    "arquivo_extracao",
                    "mapeamento_ref",
                ]
            ],
            on="corrida_id",
            how="left",
        )
        merged["nivel_preenchimento_opcional"] = merged.apply(
            self._classify_optional_fill_level,
            axis=1,
        )
        for col in columns:
            if col not in merged.columns:
                merged[col] = ""
        return merged[columns]

    def _load_history_rows(self) -> pd.DataFrame:
        sqlite_df = self._load_history_rows_from_sqlite()
        if not sqlite_df.empty:
            return sqlite_df
        return self._load_history_rows_from_csv()

    def _load_history_rows_from_sqlite(self) -> pd.DataFrame:
        if not self.db_path.exists():
            return pd.DataFrame()
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='historico_analises' LIMIT 1"
                ).fetchone()
                if not row:
                    return pd.DataFrame()
                return pd.read_sql_query("SELECT * FROM historico_analises", conn)
        except Exception:
            return pd.DataFrame()

    def _load_history_rows_from_csv(self) -> pd.DataFrame:
        if not self.history_csv_path.exists():
            return pd.DataFrame()
        try:
            with CSVFileLock(self.history_csv_path):
                return read_csv_strict(
                    self.history_csv_path,
                    contract_name="historico_analises.csv",
                )
        except Exception:
            try:
                with CSVFileLock(self.history_csv_path):
                    return pd.read_csv(self.history_csv_path, sep=";", encoding="utf-8")
            except Exception:
                return pd.DataFrame()

    def _load_exam_runs_rows(self) -> List[Dict[str, str]]:
        sqlite_rows = self._load_exam_runs_rows_from_sqlite()
        if sqlite_rows:
            return sqlite_rows
        return self._load_exam_runs_rows_from_csv()

    def _load_exam_runs_rows_from_sqlite(self) -> List[Dict[str, str]]:
        if not self.db_path.exists():
            return []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='exam_runs' LIMIT 1"
                ).fetchone()
                if not row:
                    return []
                rows = conn.execute(
                    """
                    SELECT
                        corrida_id, exame_slug, equipamento_id, equipamento_modelo,
                        data_exame, hora_exame, lote, amostra_codigo, pocos,
                        resultado_geral, status_placa, targets_json
                    FROM exam_runs
                    ORDER BY id DESC
                    """
                ).fetchall()
        except Exception:
            return []

        payload: List[Dict[str, str]] = []
        for row in rows:
            item = {str(k): str(v or "") for k, v in dict(row).items() if k != "targets_json"}
            try:
                dynamic = json.loads(str(dict(row).get("targets_json") or "{}"))
                if isinstance(dynamic, dict):
                    for key, value in dynamic.items():
                        item[str(key)] = str(value or "")
            except Exception:
                pass
            payload.append(item)
        return payload

    def _load_exam_runs_rows_from_csv(self) -> List[Dict[str, str]]:
        if not self.logs_dir.exists():
            return []
        rows: List[Dict[str, str]] = []
        for path in sorted(self.logs_dir.glob("corridas_*.csv")):
            try:
                with CSVFileLock(path):
                    df = pd.read_csv(path, sep=",", encoding="utf-8")
            except Exception:
                continue
            if df.empty:
                continue
            if "exame_slug" not in df.columns:
                df["exame_slug"] = path.stem.replace("corridas_", "", 1)
            for record in df.fillna("").to_dict(orient="records"):
                rows.append({str(k): str(v or "") for k, v in record.items()})
        return rows

    def _load_final_run_reports(self) -> List[Dict[str, str]]:
        if not self.logs_dir.exists():
            return []
        rows: List[Dict[str, str]] = []
        for path in sorted(self.logs_dir.glob("relatorio_final_corrida_*.json")):
            if path.name.endswith("_last.json"):
                continue
            try:
                with path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            trilha = payload.get("trilha", {}) if isinstance(payload.get("trilha"), dict) else {}
            rows.append(
                {
                    "corrida_id": str(payload.get("corrida_id", "")),
                    "exame_id": str(payload.get("exame_id", "")),
                    "lote": str(payload.get("lote", "")),
                    "data_exame": str(payload.get("data_exame", "")),
                    "arquivo_extracao": self._basename_only(payload.get("arquivo_extracao", "")),
                    "parte_placa": str(payload.get("parte_placa", "")),
                    "numero_extracao": str(payload.get("numero_extracao", "")),
                    "mapeamento_ref": str(trilha.get("mapeamento_ref", "")),
                    "historico_ref": str(trilha.get("historico_ref", "")),
                    "exportacao_ref": str(trilha.get("exportacao_ref", "")),
                    "envio_ref": str(trilha.get("envio_ref", "")),
                    "status_execucao": str(payload.get("status_execucao", "")),
                    "usuario_execucao": str(payload.get("usuario_execucao", "")),
                    "atualizado_em": str(payload.get("atualizado_em", "")),
                }
            )
        return rows

    @staticmethod
    def _basename_only(value: object) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        return Path(raw).name

    @staticmethod
    def _collect_corrida_ids(df: pd.DataFrame, *, max_ids: int = 50) -> List[str]:
        if df.empty or "corrida_id" not in df.columns:
            return []
        values: List[str] = []
        for item in df["corrida_id"].astype(str).tolist():
            token = str(item or "").strip()
            if not token:
                continue
            if token not in values:
                values.append(token)
            if len(values) >= max_ids:
                break
        return values

    def _resolve_effective_page_cap(self) -> int:
        cap = int(self.high_volume_page_size_cap)
        mitigation = get_local_mitigation_state(logs_dir=self.logs_dir)
        runtime_cap = mitigation.get("page_size_cap") if isinstance(mitigation, dict) else None
        try:
            runtime_cap_int = int(runtime_cap)
        except (TypeError, ValueError):
            runtime_cap_int = cap
        return max(50, min(cap, runtime_cap_int))

    def _resolve_corrida_id(self, row: pd.Series) -> str:
        current = str(row.get("corrida_id", "") or "").strip()
        if current:
            return current
        exame = str(row.get("exame", "") or "").strip()
        lote = str(row.get("lote", "") or "").strip()
        data_exame = str(row.get("data_exame", "") or "").strip()
        arquivo = self._basename_only(row.get("arquivo_corrida", ""))
        composite = "|".join(part for part in [exame, lote, data_exame, arquivo] if part)
        return composite or "corrida_sem_id"

    @staticmethod
    def _classify_optional_fill_level(row: pd.Series) -> str:
        fields = [
            str(row.get("nome_corrida", "") or "").strip(),
            str(row.get("quem_fez_extracao", "") or "").strip(),
            str(row.get("quem_preparou_placa", "") or "").strip(),
            str(row.get("observacoes", "") or "").strip(),
        ]
        filled = sum(1 for value in fields if value)
        if filled <= 0:
            return "vazio"
        if filled >= len(fields):
            return "completo"
        return "parcial"

    def _apply_common_filters(
        self,
        df: pd.DataFrame,
        *,
        periodo_inicio: Optional[str],
        periodo_fim: Optional[str],
        exame: Optional[str],
        status: Optional[str],
        operador: Optional[str],
        busca_textual: Optional[str],
    ) -> pd.DataFrame:
        filtered = df.copy()
        if filtered.empty:
            return filtered

        filtered = self._apply_period_filter(
            filtered,
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
        )
        filtered = self._apply_token_filter(
            filtered,
            token=exame,
            candidate_columns=("exame", "exame_id", "exame_slug"),
        )
        filtered = self._apply_token_filter(
            filtered,
            token=status,
            candidate_columns=("status_corrida", "status_placa", "status_execucao", "status"),
        )
        filtered = self._apply_token_filter(
            filtered,
            token=operador,
            candidate_columns=("usuario", "usuario_execucao", "operador", "quem_fez_extracao"),
        )
        filtered = self._apply_text_search(filtered, busca_textual=busca_textual)
        return filtered.reset_index(drop=True)

    def _apply_period_filter(
        self,
        df: pd.DataFrame,
        *,
        periodo_inicio: Optional[str],
        periodo_fim: Optional[str],
    ) -> pd.DataFrame:
        start = self._parse_datetime(periodo_inicio, end_of_day=False)
        end = self._parse_datetime(periodo_fim, end_of_day=True)
        if start is None and end is None:
            return df

        period_col = self._find_first_existing_column(
            df,
            ("data_hora", "data_exame", "atualizado_em", "hora_exame"),
        )
        if period_col is None:
            return df

        parsed = df[period_col].map(
            lambda value: self._parse_datetime(str(value or "").strip(), end_of_day=False)
        )
        mask = pd.Series(True, index=df.index)
        if start is not None:
            mask = mask & (parsed >= start)
        if end is not None:
            mask = mask & (parsed <= end)
        return df[mask.fillna(False)]

    def _apply_token_filter(
        self,
        df: pd.DataFrame,
        *,
        token: Optional[str],
        candidate_columns: Sequence[str],
    ) -> pd.DataFrame:
        raw = str(token or "").strip().lower()
        if not raw:
            return df
        col = self._find_first_existing_column(df, candidate_columns)
        if col is None:
            return df
        series = df[col].astype(str).str.strip().str.lower()
        return df[series.str.contains(raw, na=False)]

    def _apply_text_search(self, df: pd.DataFrame, *, busca_textual: Optional[str]) -> pd.DataFrame:
        token = str(busca_textual or "").strip().lower()
        if not token:
            return df
        candidate_columns: List[str] = []
        priority = [
            "corrida_id",
            "exame",
            "exame_id",
            "exame_slug",
            "lote",
            "amostra_codigo",
            "arquivo_corrida",
            "arquivo_extracao",
            "mapeamento_ref",
            "usuario",
            "usuario_execucao",
            "status_corrida",
            "status_placa",
            "status_execucao",
            "observacoes",
            "nome_corrida",
            "quem_fez_extracao",
            "quem_preparou_placa",
        ]
        for name in priority:
            if name in df.columns and name not in candidate_columns:
                candidate_columns.append(name)
        if not candidate_columns:
            candidate_columns = [str(col) for col in df.columns]

        mask = pd.Series(False, index=df.index)
        for col in candidate_columns:
            current = df[col].astype(str).str.lower().str.contains(token, na=False)
            mask = mask | current
        return df[mask]

    def _apply_sort(
        self,
        df: pd.DataFrame,
        *,
        sort_by: Optional[str],
        sort_direction: str,
    ) -> Tuple[pd.DataFrame, Optional[str], str]:
        if df.empty:
            direction = "asc" if str(sort_direction).lower() == "asc" else "desc"
            return df, None, direction

        direction = "asc" if str(sort_direction).lower() == "asc" else "desc"
        sort_col = str(sort_by or "").strip()
        if not sort_col or sort_col not in df.columns:
            sort_col = self._find_first_existing_column(
                df,
                ("data_hora", "data_exame", "atualizado_em", "corrida_id", "amostra_codigo"),
            )
        if sort_col is None:
            return df, None, direction

        sorted_df = df.sort_values(
            by=sort_col,
            ascending=(direction == "asc"),
            na_position="last",
            kind="mergesort",
        )
        return sorted_df, sort_col, direction

    @staticmethod
    def _normalize_page_size(value: int) -> int:
        try:
            page_size = int(value)
        except (TypeError, ValueError):
            page_size = DEFAULT_PAGE_SIZE
        page_size = max(1, page_size)
        return min(page_size, MAX_PAGE_SIZE)

    def _apply_pagination(
        self,
        df: pd.DataFrame,
        *,
        page: int,
        page_size: int,
    ) -> Tuple[pd.DataFrame, int, int]:
        total_rows = int(len(df))
        if total_rows <= 0:
            return df.iloc[0:0].copy(), 1, 0

        total_pages = max(math.ceil(total_rows / page_size), 1)
        try:
            current_page = int(page)
        except (TypeError, ValueError):
            current_page = 1
        current_page = max(1, min(current_page, total_pages))
        start = (current_page - 1) * page_size
        end = start + page_size
        return df.iloc[start:end].reset_index(drop=True), current_page, total_pages

    @staticmethod
    def _find_first_existing_column(df: pd.DataFrame, names: Sequence[str]) -> Optional[str]:
        existing = {str(col): str(col) for col in df.columns}
        for name in names:
            if name in existing:
                return existing[name]
        return None

    @staticmethod
    def _parse_datetime(value: Optional[str], *, end_of_day: bool) -> Optional[datetime]:
        raw = str(value or "").strip()
        if not raw:
            return None
        candidates: Sequence[Tuple[str, bool]] = (
            ("%Y-%m-%d %H:%M:%S", False),
            ("%Y-%m-%d %H:%M", False),
            ("%Y-%m-%d", True),
            ("%d/%m/%Y %H:%M:%S", False),
            ("%d/%m/%Y %H:%M", False),
            ("%d/%m/%Y", True),
        )
        for fmt, date_only in candidates:
            try:
                parsed = datetime.strptime(raw, fmt)
                if date_only and end_of_day:
                    return parsed + timedelta(hours=23, minutes=59, seconds=59)
                return parsed
            except ValueError:
                continue
        return None


__all__ = [
    "OperationalTabularViewer",
    "QueryOptions",
    "QueryResult",
    "VIEW_CORRIDAS",
    "VIEW_MAPEAMENTOS",
    "VIEW_TESTES_CORRIDA",
    "VIEW_METADADOS_ADICIONAIS",
    "SUPPORTED_VIEWS",
]
