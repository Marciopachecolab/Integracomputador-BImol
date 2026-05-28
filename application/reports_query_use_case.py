# -*- coding: utf-8 -*-
"""Use case de consulta do modulo de relatorios."""

from __future__ import annotations

import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

from application.reports_contracts import (
    ReportsDetailDTO,
    ReportsFilterDTO,
    ReportsGroupDTO,
    ReportsPaginationDTO,
    ReportsResultDTO,
)
from services.gal.gal_status_reconciler import reconcile_gal_status
from services.reports.reports_repository import ReportsSQLiteRepository


def _classify_positivity(resultado_geral: Any) -> str:
    raw = unicodedata.normalize("NFKD", str(resultado_geral or "").strip().lower())
    text = " ".join(
        "".join(c for c in raw if not unicodedata.combining(c))
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )
    if "invalido" in text or "invalid" in text:
        return "invalido"
    if "indeterminado" in text or "inconclusivo" in text:
        return "inconclusivo"
    if "nao detectavel" in text or "nao detectado" in text or "negativo" in text:
        return "negativo"
    if "detectavel" in text or "detectado" in text or "positivo" in text:
        return "positivo"
    return "indeterminado"


def _canonical_positivity_filter(value: str) -> str:
    return {
        "detectavel": "positivo",
        "positivo": "positivo",
        "nao_detectavel": "negativo",
        "negativo": "negativo",
        "indeterminado": "inconclusivo",
        "inconclusivo": "inconclusivo",
        "invalido": "invalido",
    }.get(value, value)


def _summary_template() -> dict[str, int]:
    return {"total": 0, "positivos": 0, "negativos": 0, "inconclusivos": 0, "invalidos": 0}


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


def _build_group_key(
    group_by: tuple[str, ...],
    *,
    row: dict[str, Any],
    positivity: str,
) -> tuple[tuple[str, str], ...]:
    values: dict[str, str] = {
        "periodo": str(row.get("data_exame") or ""),
        "exame": str(row.get("_exam_name") or ""),
        "positividade": positivity,
        "lote": str(row.get("lote") or ""),
        "kit": str(row.get("kit") or ""),
        "analista": str(row.get("analista") or row.get("usuario") or ""),
        "status_gal": str(row.get("_status_gal") or "nao_enviado"),
    }
    return tuple((field, values[field]) for field in group_by if field in values)


class ReportsQueryUseCase:
    """Orquestra filtros, repositorio, reconciliacao GAL e regras de escopo."""

    def __init__(
        self,
        repository: ReportsSQLiteRepository,
        journal_path: Path,
    ) -> None:
        self._repo = repository
        self._journal_path = journal_path

    def execute(self, filters: ReportsFilterDTO) -> ReportsResultDTO:
        rows = self._repo.get_filtered_rows(filters)

        # Reconcilia status GAL para cada amostra
        gal_statuses = reconcile_gal_status(rows, self._journal_path)
        for row in rows:
            codigo = str(row.get("amostra_codigo") or row.get("codigo_amostra") or "")
            row["_status_gal"] = gal_statuses.get(codigo, "nao_enviado")

        # Filtro por status_gal
        if filters.status_gal:
            allowed_gal = set(filters.status_gal)
            rows = [r for r in rows if r.get("_status_gal") in allowed_gal]

        allowed_positivity = {_canonical_positivity_filter(v) for v in filters.positividade}

        summary = _summary_template()
        groups: dict[tuple[tuple[str, str], ...], dict[str, Any]] = {}

        for row in rows:
            positivity = _classify_positivity(row.get("resultado_geral", ""))
            if allowed_positivity and positivity not in allowed_positivity:
                continue

            _increment_summary(summary, positivity)
            group_key = _build_group_key(filters.agrupar_por, row=row, positivity=positivity)
            if group_key not in groups:
                groups[group_key] = {"chaves": dict(group_key), "summary": _summary_template()}
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

        all_details = self._build_details(rows, allowed_positivity)
        paged_details = tuple(all_details[filters.offset: filters.offset + filters.limit])

        return ReportsResultDTO(
            resumo=summary,
            agrupamentos=agrupamentos,
            detalhes=paged_details,
            paginacao=ReportsPaginationDTO(
                limit=filters.limit,
                offset=filters.offset,
                total_estimado=summary["total"],
            ),
        )

    @staticmethod
    def _build_details(
        rows: list[dict[str, Any]],
        allowed_positivity: set[str],
    ) -> list[ReportsDetailDTO]:
        result = []
        for row in rows:
            positivity = _classify_positivity(row.get("resultado_geral", ""))
            if allowed_positivity and positivity not in allowed_positivity:
                continue

            data_str = str(row.get("data_exame") or "")
            try:
                data_exame = date.fromisoformat(data_str)
            except ValueError:
                continue

            result.append(
                ReportsDetailDTO(
                    corrida_id=str(row.get("corrida_id") or ""),
                    amostra_codigo=str(row.get("amostra_codigo") or ""),
                    exame=str(row.get("_exam_name") or ""),
                    data_exame=data_exame,
                    analista=str(row.get("analista") or row.get("usuario") or ""),
                    kit=str(row.get("kit") or ""),
                    lote=str(row.get("lote") or ""),
                    resultado_geral=str(row.get("resultado_geral") or ""),
                    status_gal=str(row.get("_status_gal") or "nao_enviado"),
                )
            )
        return result
