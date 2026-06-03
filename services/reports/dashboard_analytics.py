# -*- coding: utf-8 -*-
"""
Dashboard Analytics Service - gera estatisticas para paineis operacionais e gerenciais.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List
import re

from services.persistence.exam_runs_sqlite import ExamRunsSQLiteRepository
from services.reports.relatorio_estatistico import _classificar_resultado, _is_control

def parse_date(date_str: str) -> datetime | None:
    """Tenta extrair datetime a partir de strings de data variadas."""
    if not date_str:
        return None
    date_str = str(date_str).strip()
    try:
        # DD/MM/YYYY
        if "/" in date_str:
            parts = date_str.split(" ")[0].split("/")
            if len(parts) == 3:
                return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
        # YYYY-MM-DD
        elif "-" in date_str:
            parts = date_str.split(" ")[0].split("-")
            if len(parts) == 3:
                return datetime(int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        pass
    return None


def limpar_nome_alvo(name: str) -> str:
    """Remove prefixos de coluna (RES_/SRC_RES_/RESULTADO_) e normaliza o rotulo."""
    for prefixo in ("SRC_RES_", "RESULTADO_", "RES_", "CT_"):
        if name.upper().startswith(prefixo):
            return name[len(prefixo):].replace("_", " ").strip()
    return name.replace("_", " ").strip()


def parse_ct(value) -> "float | None":
    """Converte valor de Ct (string ex. '19.34', vazio = nao detectado) em float > 0."""
    if value is None:
        return None
    s = str(value).strip().replace(",", ".")
    if not s:
        return None
    try:
        f = float(s)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


class DashboardAnalyticsService:
    """Servico de analiticas para o Dashboard."""

    def __init__(self, repository: ExamRunsSQLiteRepository | None = None):
        self.repository = repository or ExamRunsSQLiteRepository()

    def obter_estatisticas_gestao(
        self,
        period_days: int,
        exame_filtro: str = "Todos",
        data_inicio: "datetime | None" = None,
        data_fim: "datetime | None" = None,
    ) -> dict:
        """Retorna estatisticas gerenciais para o periodo ou intervalo de datas.

        Quando data_inicio e data_fim sao fornecidas, ignoram period_days e nao
        calculam periodo anterior (deltas ficam zerados).
        """
        rows = self.repository.list_rows()
        now = datetime.now()
        now_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        if data_inicio and data_fim:
            current_start = data_inicio.replace(hour=0, minute=0, second=0, microsecond=0)
            current_end = data_fim.replace(hour=23, minute=59, second=59, microsecond=999999)
            previous_start = None
        else:
            current_start = now_end - timedelta(days=period_days)
            current_end = now_end
            previous_start = current_start - timedelta(days=period_days)

        current_volume = 0
        previous_volume = 0
        
        unique_exams = set()
        
        current_det = 0
        current_total = 0
        previous_det = 0
        previous_total = 0
        
        # Estrutura para Top Doencas: alvo -> count
        disease_counts: Dict[str, int] = {}
        
        ignore_pattern = re.compile(r"RP|CN|CP|GERAL", re.IGNORECASE)

        core_fields = {
            "corrida_id", "exame_slug", "equipamento_id", "equipamento_modelo", 
            "data_exame", "hora_exame", "lote", "amostra_codigo", "pocos", 
            "resultado_geral", "status_placa", "id"
        }

        for row in rows:
            exame_nome = row.get("exame_slug") or row.get("exame") or ""
            if exame_nome:
                unique_exams.add(exame_nome)
                
            if exame_filtro != "Todos" and exame_filtro.lower() not in exame_nome.lower():
                continue

            dt = parse_date(row.get("data_exame") or "")
            if not dt:
                continue

            is_current = current_start <= dt <= current_end
            is_previous = (
                previous_start <= dt < current_start
                if previous_start is not None
                else False
            )

            if not is_current and not is_previous:
                continue
                
            if _is_control(row.get("amostra_codigo")):
                continue

            if is_current:
                current_volume += 1
            if is_previous:
                previous_volume += 1

            for key, val in row.items():
                if key in core_fields:
                    continue

                # Conta apenas colunas canonicas de resultado (RES_*). Isso elimina
                # duplicatas de snapshot de origem (SRC_RES_*) e colunas auxiliares
                # (CT_*, SRC_MANUAL_*, SRC_RESULTADO_GERAL, etc.) que inflavam as
                # contagens e geravam itens redundantes (ex.: "RES HRV" + "SRC RES HRV").
                if not str(key).upper().startswith("RES_"):
                    continue

                if ignore_pattern.search(key):
                    continue
                    
                # Classificar (ex: Det, ND, Ind)
                cls = _classificar_resultado(val)
                if cls in ("det", "nd", "ind"):
                    if is_current:
                        current_total += 1
                        if cls == "det":
                            current_det += 1
                            disease_counts[key] = disease_counts.get(key, 0) + 1
                    if is_previous:
                        previous_total += 1
                        if cls == "det":
                            previous_det += 1

        # Variacao volume
        delta_volume = 0.0
        if previous_volume > 0:
            delta_volume = ((current_volume - previous_volume) / previous_volume) * 100.0
        elif current_volume > 0:
            delta_volume = 100.0

        # Variacao positividade global
        current_positivity = (current_det / current_total * 100.0) if current_total > 0 else 0.0
        previous_positivity = (previous_det / previous_total * 100.0) if previous_total > 0 else 0.0
        
        delta_positivity = current_positivity - previous_positivity

        # Top Positive Diseases
        clean_target_name = limpar_nome_alvo

        top_diseases = sorted(disease_counts.items(), key=lambda x: x[1], reverse=True)[:12]
        top_diseases_formatted = [
            {"alvo": clean_target_name(k), "count": v} for k, v in top_diseases
        ]

        return {
            "period_days": period_days,
            "current_volume": current_volume,
            "previous_volume": previous_volume,
            "delta_volume": delta_volume,
            "current_positivity": current_positivity,
            "previous_positivity": previous_positivity,
            "delta_positivity": delta_positivity,
            "top_positive_diseases": top_diseases_formatted,
            "unique_exams": sorted(list(unique_exams))
        }

    def obter_estatisticas_operacionais(self) -> dict:
        """
        Retorna estatisticas operacionais globais ou do dia de hoje.
        """
        rows = self.repository.list_rows()
        now = datetime.now()
        hoje = now.date()

        volume_hoje = 0
        volume_total = len(rows)
        equipamentos_ativos = set()

        for row in rows:
            dt = parse_date(row.get("data_exame") or "")
            if dt and dt.date() == hoje:
                volume_hoje += 1
            
            eq_id = row.get("equipamento_id") or row.get("equipamento_modelo")
            if eq_id:
                equipamentos_ativos.add(eq_id)

        return {
            "volume_hoje": volume_hoje,
            "volume_total": volume_total,
            "equipamentos_ativos_count": len(equipamentos_ativos)
        }

    def obter_painel_analitico(self, exame_filtro: str = "Todos") -> dict:
        """Agrega KPIs, heatmap dia x doenca e tabela de Ct (15/7/3 dias).

        Janela analitica fixa de 15 dias a partir de hoje, com sub-janelas de
        7 e 3 dias. Considera apenas colunas canonicas RES_*/CT_* (ignora SRC_*
        e controles RP/CN/CP/GERAL). Retorna estrutura consumida pela aba
        "Visao Analitica" do dashboard.
        """
        rows = self.repository.list_rows()
        now = datetime.now()
        hoje = now.date()
        ini15 = hoje - timedelta(days=14)   # 15 dias incluindo hoje
        ini7 = hoje - timedelta(days=6)
        ini3 = hoje - timedelta(days=2)
        dias15 = [(ini15 + timedelta(days=i)).isoformat() for i in range(15)]
        dia_idx = {d: i for i, d in enumerate(dias15)}

        ignore_pattern = re.compile(r"RP|CN|CP|GERAL", re.IGNORECASE)

        unique_exams = set()
        for row in rows:
            en = row.get("exame_slug") or row.get("exame") or ""
            if en:
                unique_exams.add(en)

        def _match_exame(nome: str) -> bool:
            return exame_filtro == "Todos" or exame_filtro.lower() in nome.lower()

        # Acumuladores
        volume_total = 0
        det_total = 0
        clf_total = 0
        # heatmap[alvo][dia_iso] = positivos
        heat: Dict[str, Dict[str, int]] = {}
        # ct_acc[alvo] = {"15": [vals], "7": [...], "3": [...]}
        ct_acc: Dict[str, Dict[str, List[float]]] = {}
        # positividade por alvo (15d): det / classificados
        alvo_det: Dict[str, int] = {}
        alvo_clf: Dict[str, int] = {}

        for row in rows:
            exame_nome = row.get("exame_slug") or row.get("exame") or ""
            if not _match_exame(exame_nome):
                continue
            if _is_control(row.get("amostra_codigo")):
                continue
            dt = parse_date(row.get("data_exame") or "")
            if not dt:
                continue
            d = dt.date()
            if d < ini15 or d > hoje:
                continue
            d_iso = d.isoformat()

            volume_total += 1
            in7 = d >= ini7
            in3 = d >= ini3

            for key, val in row.items():
                ku = str(key).upper()
                if not ku.startswith("RES_"):
                    continue
                if ignore_pattern.search(key):
                    continue
                cls = _classificar_resultado(val)
                if cls not in ("det", "nd", "ind"):
                    continue
                alvo = limpar_nome_alvo(key)
                clf_total += 1
                alvo_clf[alvo] = alvo_clf.get(alvo, 0) + 1
                if cls == "det":
                    alvo_det[alvo] = alvo_det.get(alvo, 0) + 1
                    det_total += 1
                    heat.setdefault(alvo, {})
                    heat[alvo][d_iso] = heat[alvo].get(d_iso, 0) + 1
                    # Ct correspondente (CT_<alvo bruto>), so quando detectavel
                    ct_key = "CT_" + key[len("RES_"):]
                    ctv = parse_ct(row.get(ct_key))
                    if ctv is not None:
                        acc = ct_acc.setdefault(alvo, {"15": [], "7": [], "3": []})
                        acc["15"].append(ctv)
                        if in7:
                            acc["7"].append(ctv)
                        if in3:
                            acc["3"].append(ctv)

        # KPIs
        positividade = (det_total / clf_total * 100.0) if clf_total > 0 else 0.0
        kpis = {
            "volume_total": volume_total,
            "volume_dia_media": volume_total / 15.0,
            "positividade": positividade,
            "pendentes_gal": self._contar_pendentes_gal(rows, exame_filtro, ignore_pattern),
        }

        # Ordena alvos por total de positivos (desc) para heatmap/tabela
        totais = {a: sum(v.values()) for a, v in heat.items()}
        alvos = sorted(totais, key=lambda a: totais[a], reverse=True)

        matriz = [[heat.get(a, {}).get(d, 0) for d in dias15] for a in alvos]

        def _media(vals: List[float]) -> "float | None":
            return (sum(vals) / len(vals)) if vals else None

        def _delta(novo: "float | None", base: "float | None") -> "float | None":
            if novo is None or base is None or base == 0:
                return None
            return (novo - base) / base * 100.0

        ct_table = []
        for a in alvos:
            acc = ct_acc.get(a, {"15": [], "7": [], "3": []})
            ct15 = _media(acc["15"])
            ct7 = _media(acc["7"])
            ct3 = _media(acc["3"])
            ct_table.append({
                "alvo": a,
                "ct15": ct15,
                "ct7": ct7,
                "ct3": ct3,
                "delta7": _delta(ct7, ct15),
                "delta3": _delta(ct3, ct7),
            })

        positividade_por_alvo = {
            a: (alvo_det.get(a, 0) / alvo_clf[a] * 100.0)
            for a in alvo_clf if alvo_clf[a] > 0
        }

        return {
            "kpis": kpis,
            "heatmap": {"dias": dias15, "alvos": alvos, "matriz": matriz},
            "ct_table": ct_table,
            "alvos": alvos,
            "positividade_por_alvo": positividade_por_alvo,
            "unique_exams": sorted(unique_exams),
        }

    def _contar_pendentes_gal(self, rows, exame_filtro, ignore_pattern) -> int:
        """Conta amostras nao-controle cujo status GAL reconciliado != enviado/duplicado."""
        try:
            from services.gal.gal_transactions import default_transaction_journal_path
            from services.gal.gal_status_reconciler import reconcile_gal_status

            considerar = [
                r for r in rows
                if not _is_control(r.get("amostra_codigo"))
                and (exame_filtro == "Todos"
                     or exame_filtro.lower() in str(r.get("exame_slug") or "").lower())
            ]
            if not considerar:
                return 0
            statuses = reconcile_gal_status(considerar, default_transaction_journal_path())
            pendentes = 0
            for r in considerar:
                codigo = str(r.get("amostra_codigo") or "")
                st = statuses.get(codigo, "nao_enviado")
                if st not in ("enviado", "duplicado"):
                    pendentes += 1
            return pendentes
        except Exception:
            return 0
