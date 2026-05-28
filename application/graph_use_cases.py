# -*- coding: utf-8 -*-
"""
Use cases for graph data generation (UI-independent).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from services.reports.relatorio_estatistico import calcular_estatisticas_relatorio


@dataclass(frozen=True)
class DetectionGraphData:
    labels: List[str]
    detectaveis: List[int]
    indeterminados: List[int]
    total_sem_controles: int


def build_detection_graph_data(
    df_analise: pd.DataFrame,
    *,
    sort_labels: bool = True,
) -> DetectionGraphData:
    """
    Build graph data using the statistical report results.

    Only 'Detectaveis' and 'Indeterminados' counts are returned, as required by UI.
    """
    table_data, total_sem_controles = calcular_estatisticas_relatorio(df_analise)
    if not table_data:
        return DetectionGraphData([], [], [], total_sem_controles)

    rows = [
        row
        for row in table_data
        if str(row.get("Alvo", "")).strip()
    ]
    if sort_labels:
        rows = sorted(rows, key=lambda r: str(r.get("Alvo", "")).upper())

    labels = [str(row.get("Alvo", "")).strip() for row in rows]
    detectaveis = [int(row.get("Det", 0)) for row in rows]
    indeterminados = [int(row.get("Ind", 0)) for row in rows]

    return DetectionGraphData(labels, detectaveis, indeterminados, total_sem_controles)


def build_detection_graph_figure(graph_data: DetectionGraphData) -> Figure:
    """
    Build a matplotlib Figure for the detection graph.

    Args:
        graph_data: DetectionGraphData with labels and counts.

    Returns:
        Matplotlib Figure ready to be rendered by a canvas.
    """
    labels = graph_data.labels
    det_vals = graph_data.detectaveis
    inc_vals = graph_data.indeterminados

    fig = Figure(figsize=(max(10, len(labels) * 1.2), 6))
    ax = fig.add_subplot(111)

    x = np.arange(len(labels))
    width = 0.35

    rects1 = ax.bar(
        x - width / 2,
        det_vals,
        width,
        label="Detectavel",
        color="#e74c3c",
        edgecolor="black",
        linewidth=0.8,
    )
    rects2 = ax.bar(
        x + width / 2,
        inc_vals,
        width,
        label="Indeterminado",
        color="#f39c12",
        edgecolor="black",
        linewidth=0.8,
    )

    ax.set_title(
        "Amostras por Alvo (Detectaveis e Indeterminados)",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    ax.set_xlabel("Alvos", fontsize=12, fontweight="bold")
    ax.set_ylabel("Quantidade", fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)

    ymax = max(det_vals + inc_vals) if (det_vals or inc_vals) else 10
    ax.set_ylim(0, ymax * 1.25)
    ax.grid(axis="y", alpha=0.3, linestyle="--")

    if len(labels) > 6:
        for tick in ax.get_xticklabels():
            tick.set_rotation(45)
            tick.set_ha("right")

    def _autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            if height > 0:
                ax.annotate(
                    f"{int(height)}",
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontweight="bold",
                    fontsize=9,
                )

    _autolabel(rects1)
    _autolabel(rects2)

    ax.legend(loc="upper right", fontsize=10)
    fig.tight_layout()
    return fig
