"""Repositorio SQLite-first para consultas do modulo de relatorios."""

from __future__ import annotations

import json
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

from application.reports_contracts import (
    ReportsFilterDTO,
    ReportsGroupDTO,
    ReportsPaginationDTO,
    ReportsResultDTO,
)
from services.analysis.exam_runs_row_mapper import slugify
from services.persistence.exam_runs_sqlite import default_exam_runs_db_path


def _normalize_text(value: Any) -> str:
    raw = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    ascii_only = "".join(ch for ch in raw if not unicodedata.combining(ch))
    return ascii_only.replace("_", " ").replace("-", " ")


def _classify_positivity(resultado_geral: Any) -> str:
    text = _normalize_text(resultado_geral)
    compact = " ".join(text.split())
    if "invalido" in compact or "invalid" in compact:
        return "invalido"
    if "indeterminado" in compact or "inconclusivo" in compact:
        return "inconclusivo"
    if "nao detectavel" in compact or "nao detectado" in compact or "negativo" in compact:
        return "negativo"
    if "detectavel" in compact or "detectado" in compact or "positivo" in compact:
        return "positivo"
    return "indeterminado"


def _canonical_positivity_filter(value: str) -> str:
    aliases = {
        "detectavel": "positivo",
        "positivo": "positivo",
        "nao_detectavel": "negativo",
        "negativo": "negativo",
        "indeterminado": "inconclusivo",
        "inconclusivo": "inconclusivo",
        "invalido": "invalido",
    }
    return aliases.get(value, value)


def _summary_template() -> dict[str, int]:
    return {
        "total": 0,
        "positivos": 0,
        "negativos": 0,
        "inconclusivos": 0,
        "invalidos": 0,
    }


def _increment_summary(summary: dict[str, int], positivity: str) -> None:
    summary["total"] += 1
    if positivity == "positivo":
        summary["positivos"] += 1
    elif positivity == "negativo":
        summary["negativos"] += 1
    elif positivity == "invalido":
        summary["invalidos"] += 1
    else:
        summary["inconclusivos"] += 1


class ReportsSQLiteRepository:
    """Consulta agregados de relatorios a partir da tabela SQLite `exam_runs`."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else default_exam_runs_db_path()

    def get_filtered_rows(self, filters: ReportsFilterDTO) -> list[dict[str, Any]]:
        """Retorna linhas filtradas enriquecidas com targets e _exam_name."""
        exam_slug_to_name = {slugify(name): name for name in filters.exames}
        raw_rows = self._fetch_rows(filters, tuple(exam_slug_to_name))
        filtered = self._post_filter_rows(raw_rows, filters)

        result: list[dict[str, Any]] = []
        for row in filtered:
            targets = json.loads(row.get("targets_json") or "{}")
            enriched: dict[str, Any] = dict(row)
            for k, v in targets.items():
                if k not in enriched:
                    enriched[k] = v
            enriched["_exam_name"] = exam_slug_to_name.get(
                row["exame_slug"], row["exame_slug"]
            )
            result.append(enriched)
        return result

    def query_exam_run_totals(self, filters: ReportsFilterDTO) -> ReportsResultDTO:
        """Retorna totais por periodo, exame, positividade, analista, kit e lote."""
        rows = self.get_filtered_rows(filters)

        summary = _summary_template()
        groups: dict[tuple[tuple[str, str], ...], dict[str, Any]] = {}
        allowed_positivity = {
            _canonical_positivity_filter(value) for value in filters.positividade
        }

        for row in rows:
            positivity = _classify_positivity(row["resultado_geral"])
            if allowed_positivity and positivity not in allowed_positivity:
                continue

            _increment_summary(summary, positivity)
            group_key = self._build_group_key(
                filters.agrupar_por,
                row=row,
                exam_name=row["_exam_name"],
                positivity=positivity,
            )
            if group_key not in groups:
                groups[group_key] = {
                    "chaves": dict(group_key),
                    "summary": _summary_template(),
                }
            _increment_summary(groups[group_key]["summary"], positivity)

        agrupamentos = tuple(
            ReportsGroupDTO(
                chaves=payload["chaves"],
                total=payload["summary"]["total"],
                positivos=payload["summary"]["positivos"],
                negativos=payload["summary"]["negativos"],
            )
            for _, payload in sorted(groups.items())
        )

        return ReportsResultDTO(
            resumo=summary,
            agrupamentos=agrupamentos,
            detalhes=(),
            paginacao=ReportsPaginationDTO(
                limit=filters.limit,
                offset=filters.offset,
                total_estimado=summary["total"],
            ),
        )

    def _fetch_rows(
        self,
        filters: ReportsFilterDTO,
        exame_slugs: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        if not exame_slugs:
            return []

        placeholders = ", ".join("?" for _ in exame_slugs)
        params: list[Any] = [
            filters.data_inicio.isoformat(),
            filters.data_fim.isoformat(),
            *exame_slugs,
        ]

        lote_clause = ""
        if filters.lotes:
            lote_placeholders = ", ".join("?" for _ in filters.lotes)
            lote_clause = f"AND lower(trim(lote)) IN ({lote_placeholders})"
            params.extend(v.casefold() for v in filters.lotes)

        query = f"""
            SELECT corrida_id, data_exame, exame_slug, resultado_geral,
                   lote, amostra_codigo, targets_json
            FROM exam_runs
            WHERE data_exame >= ?
              AND data_exame <= ?
              AND exame_slug IN ({placeholders})
              {lote_clause}
            ORDER BY data_exame, exame_slug, amostra_codigo
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _post_filter_rows(
        rows: list[dict[str, Any]],
        filters: ReportsFilterDTO,
    ) -> list[dict[str, Any]]:
        """Filtra kit e analista em Python a partir de targets_json."""
        if not filters.kits and not filters.analistas:
            return rows

        kits_lower = {v.casefold() for v in filters.kits}
        analistas_lower = {v.casefold() for v in filters.analistas}

        result = []
        for row in rows:
            targets = json.loads(row.get("targets_json") or "{}")
            if kits_lower:
                kit = str(targets.get("kit") or "").casefold()
                if kit not in kits_lower:
                    continue
            if analistas_lower:
                analista = str(
                    targets.get("analista") or targets.get("usuario") or ""
                ).casefold()
                if analista not in analistas_lower:
                    continue
            result.append(row)
        return result

    @staticmethod
    def _build_group_key(
        group_by: tuple[str, ...],
        *,
        row: dict[str, Any],
        exam_name: str,
        positivity: str,
    ) -> tuple[tuple[str, str], ...]:
        values = {
            "periodo": str(row.get("data_exame") or ""),
            "exame": exam_name,
            "positividade": positivity,
            "lote": str(row.get("lote") or ""),
            "kit": str(row.get("kit") or ""),
            "analista": str(row.get("analista") or row.get("usuario") or ""),
        }
        return tuple((field, values[field]) for field in group_by if field in values)
