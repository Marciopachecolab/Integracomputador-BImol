# -*- coding: utf-8 -*-
"""Tela de consulta operacional tabular (F6/F7) com fallback legado."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import customtkinter as ctk
from tkinter import simpledialog, ttk, messagebox

from services.core.config_service import config_service
from services.legacy_audit.operational_tabular_viewer import (
    MAX_PAGE_SIZE,
    QueryResult,
    OperationalTabularViewer,
    QueryOptions,
    VIEW_CORRIDAS,
    VIEW_MAPEAMENTOS,
    VIEW_METADADOS_ADICIONAIS,
    VIEW_TESTES_CORRIDA,
)
from services.operational_viewer_quick_filters import build_quick_filter_state
from services.operational_viewer_profiles import OperationalViewerProfileStore
from utils.logger import registrar_log


class HistoricoOperacionalPage(ctk.CTkFrame):
    """Pagina operacional de consulta tabular para historico de corridas."""

    def __init__(
        self,
        *,
        host_frame: ctk.CTkFrame,
        main_window,
        on_close_callback: Optional[Callable[[], None]] = None,
        on_fallback_legacy: Optional[Callable[[str, Exception], None]] = None,
    ) -> None:
        super().__init__(host_frame)
        self.pack(expand=True, fill="both")
        self._main_window = main_window
        self._on_close_callback = on_close_callback
        self._on_fallback_legacy = on_fallback_legacy
        self._fallback_activated = False

        self._user_id = str(
            getattr(getattr(main_window, "app_state", None), "usuario_logado", "") or ""
        ).strip() or "anonimo"
        self._viewer = OperationalTabularViewer()
        self._profile_store = OperationalViewerProfileStore(logs_dir=self._viewer.logs_dir)
        self._quick_filter_chip = ctk.StringVar(value="nenhum")
        self._last_result = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_filters()
        self._build_table()
        self._build_footer()

        self._load_user_state()
        self._run_query()

    def _build_header(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            frame,
            text="Consulta Operacional de Corridas",
            font=("Segoe UI", 18, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=12)



    def _build_filters(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=1, column=0, sticky="ew", padx=16, pady=8)
        for idx in range(10):
            frame.grid_columnconfigure(idx, weight=1)

        ctk.CTkLabel(frame, text="Visao").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        self.combo_view = ctk.CTkComboBox(
            frame,
            values=[
                VIEW_CORRIDAS,
                VIEW_MAPEAMENTOS,
                VIEW_TESTES_CORRIDA,
                VIEW_METADADOS_ADICIONAIS,
            ],
            width=180,
        )
        self.combo_view.set(VIEW_CORRIDAS)
        self.combo_view.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))

        ctk.CTkLabel(frame, text="Periodo inicio").grid(
            row=0, column=1, sticky="w", padx=8, pady=(8, 2)
        )
        self.entry_periodo_inicio = ctk.CTkEntry(frame, placeholder_text="YYYY-MM-DD")
        self.entry_periodo_inicio.grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 8))

        ctk.CTkLabel(frame, text="Periodo fim").grid(row=0, column=2, sticky="w", padx=8, pady=(8, 2))
        self.entry_periodo_fim = ctk.CTkEntry(frame, placeholder_text="YYYY-MM-DD")
        self.entry_periodo_fim.grid(row=1, column=2, sticky="ew", padx=8, pady=(0, 8))

        ctk.CTkLabel(frame, text="Exame").grid(row=0, column=3, sticky="w", padx=8, pady=(8, 2))
        self.entry_exame = ctk.CTkEntry(frame)
        self.entry_exame.grid(row=1, column=3, sticky="ew", padx=8, pady=(0, 8))

        ctk.CTkLabel(frame, text="Status").grid(row=0, column=4, sticky="w", padx=8, pady=(8, 2))
        self.entry_status = ctk.CTkEntry(frame)
        self.entry_status.grid(row=1, column=4, sticky="ew", padx=8, pady=(0, 8))

        ctk.CTkLabel(frame, text="Operador").grid(row=0, column=5, sticky="w", padx=8, pady=(8, 2))
        self.entry_operador = ctk.CTkEntry(frame)
        self.entry_operador.grid(row=1, column=5, sticky="ew", padx=8, pady=(0, 8))

        ctk.CTkLabel(frame, text="Busca").grid(row=0, column=6, sticky="w", padx=8, pady=(8, 2))
        self.entry_busca = ctk.CTkEntry(frame)
        self.entry_busca.grid(row=1, column=6, sticky="ew", padx=8, pady=(0, 8))

        ctk.CTkLabel(frame, text="Ordenar por").grid(row=0, column=7, sticky="w", padx=8, pady=(8, 2))
        self.entry_sort_by = ctk.CTkEntry(frame, placeholder_text="ex: data_hora")
        self.entry_sort_by.grid(row=1, column=7, sticky="w", padx=8, pady=(0, 8))
        
        ctk.CTkLabel(frame, text="Direção").grid(row=0, column=8, sticky="w", padx=8, pady=(8, 2))
        self.combo_sort_direction = ctk.CTkComboBox(frame, values=["desc", "asc"], width=100)
        self.combo_sort_direction.set("desc")
        self.combo_sort_direction.grid(row=1, column=8, sticky="ew", padx=8, pady=(0, 8))

        page_frame = ctk.CTkFrame(frame, fg_color="transparent")
        page_frame.grid(row=1, column=9, sticky="e", padx=8, pady=(0, 8))
        ctk.CTkLabel(page_frame, text="Pag").pack(side="left", padx=(0, 4))
        self.entry_page = ctk.CTkEntry(page_frame, width=50)
        self.entry_page.insert(0, "1")
        self.entry_page.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(page_frame, text="Tam").pack(side="left", padx=(0, 4))
        self.entry_page_size = ctk.CTkEntry(page_frame, width=60)
        self.entry_page_size.insert(0, "100")
        self.entry_page_size.pack(side="left")

        button_bar = ctk.CTkFrame(frame, fg_color="transparent")
        button_bar.grid(row=2, column=0, columnspan=10, sticky="ew", padx=8, pady=(0, 4))
        ctk.CTkButton(button_bar, text="Consultar", command=self._run_query).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(button_bar, text="Limpar", command=self._clear_filters).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(
            button_bar,
            text="Exportar CSV",
            command=lambda: self._export_result("csv"),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            button_bar,
            text="Exportar XLSX",
            command=lambda: self._export_result("xlsx"),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            button_bar,
            text="Usar modo legado",
            fg_color="#6b7280",
            hover_color="#4b5563",
            command=lambda: self._activate_legacy_fallback("manual", RuntimeError("manual")),
        ).pack(side="right")

        chips = ctk.CTkFrame(frame, fg_color="transparent")
        chips.grid(row=3, column=0, columnspan=10, sticky="ew", padx=8, pady=(0, 4))
        ctk.CTkLabel(chips, text="Filtros rapidos:").pack(side="left", padx=(0, 8))
        ctk.CTkButton(chips, text="Hoje", width=80, command=lambda: self._apply_quick_filter("hoje")).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(
            chips,
            text="Ultimos 7d",
            width=100,
            command=lambda: self._apply_quick_filter("ultimos_7_dias"),
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            chips,
            text="Status: Valida",
            width=120,
            command=lambda: self._apply_quick_filter("status_valida"),
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            chips,
            text="Limpar chip",
            width=100,
            command=lambda: self._apply_quick_filter("nenhum"),
        ).pack(side="left", padx=(0, 6))

        presets = ctk.CTkFrame(frame, fg_color="transparent")
        presets.grid(row=4, column=0, columnspan=10, sticky="ew", padx=8, pady=(0, 8))
        ctk.CTkLabel(presets, text="Presets:").pack(side="left", padx=(0, 8))
        self.combo_presets = ctk.CTkComboBox(presets, values=["(sem presets)"], width=240)
        self.combo_presets.set("(sem presets)")
        self.combo_presets.pack(side="left", padx=(0, 6))
        ctk.CTkButton(presets, text="Aplicar", width=80, command=self._apply_selected_preset).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(presets, text="Salvar", width=80, command=self._save_preset_dialog).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(presets, text="Excluir", width=80, command=self._delete_selected_preset).pack(
            side="left", padx=(0, 6)
        )

    def _build_table(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=2, column=0, sticky="nsew", padx=16, pady=8)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.scroll_y = ttk.Scrollbar(frame, orient="vertical")
        self.scroll_x = ttk.Scrollbar(frame, orient="horizontal")
        self.tree = ttk.Treeview(
            frame,
            columns=(),
            show="headings",
            yscrollcommand=self.scroll_y.set,
            xscrollcommand=self.scroll_x.set,
        )
        self.scroll_y.configure(command=self.tree.yview)
        self.scroll_x.configure(command=self.tree.xview)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.scroll_y.grid(row=0, column=1, sticky="ns")
        self.scroll_x.grid(row=1, column=0, sticky="ew")

    def _build_footer(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(8, 16))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=0)
        frame.grid_columnconfigure(3, weight=0)
        self.label_status = ctk.CTkLabel(
            frame,
            text="Pronto",
            anchor="w",
        )
        self.label_status.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.label_metrics = ctk.CTkLabel(
            frame,
            text="Analytics: aguardando consultas",
            anchor="e",
        )
        self.label_metrics.grid(row=0, column=1, sticky="ew", padx=10, pady=10)
        self.label_health = ctk.CTkLabel(
            frame,
            text="Saude: aguardando avaliacao",
            anchor="e",
        )
        self.label_health.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 8))
        self.label_slo = ctk.CTkLabel(
            frame,
            text="SLO: aguardando avaliacao",
            anchor="e",
        )
        self.label_slo.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 8))
        self.label_handover = ctk.CTkLabel(
            frame,
            text="Handover: aguardando avaliacao",
            anchor="e",
        )
        self.label_handover.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 8))
        ctk.CTkButton(
            frame,
            text="Atualizar Saude",
            width=130,
            command=self._refresh_health_summary,
        ).grid(row=0, column=2, padx=(8, 6), pady=8)
        ctk.CTkButton(
            frame,
            text="Executar Automacao",
            width=150,
            command=self._run_slo_automation,
        ).grid(row=1, column=2, padx=(8, 6), pady=8)
        ctk.CTkButton(
            frame,
            text="Executar Readiness",
            width=150,
            command=self._run_operational_readiness,
        ).grid(row=2, column=2, padx=(8, 6), pady=8)
        ctk.CTkButton(
            frame,
            text="Atualizar Handover",
            width=150,
            command=self._refresh_handover_summary,
        ).grid(row=3, column=2, padx=(8, 6), pady=8)
        ctk.CTkButton(
            frame,
            text="Decisao Go/No-Go",
            width=150,
            command=self._apply_handover_decision_dialog,
        ).grid(row=3, column=3, padx=(6, 10), pady=8)
        ctk.CTkButton(
            frame,
            text="Rollback Flag",
            width=120,
            fg_color="#b45309",
            hover_color="#92400e",
            command=self._rollback_operational_viewer_flag,
        ).grid(row=0, column=3, padx=(6, 10), pady=8)

    def _run_query(self) -> None:
        if self._fallback_activated:
            return
        try:
            options = self._build_query_options()
            result = self._viewer.query(options)
            self._last_result = result
            self._render_result(result.rows)
            self._persist_user_state(result)
            self._refresh_metrics_label()
            self._refresh_health_summary()
            self._refresh_handover_summary()
            detail = ""
            if result.is_degraded and result.degradation_message:
                detail = f" | Modo resiliente: {result.degradation_message}"
            self.label_status.configure(
                text=(
                    f"Visao={result.view} | Linhas={result.total_rows} | "
                    f"Pagina={result.page}/{max(result.total_pages, 1)} | "
                    f"Ordenacao={result.applied_sort_by or 'auto'}:{result.applied_sort_direction}"
                    f"{detail}"
                )
            )
        except Exception as exc:
            self._activate_legacy_fallback("query_error", exc)

    def _clear_filters(self) -> None:
        for widget in (
            self.entry_periodo_inicio,
            self.entry_periodo_fim,
            self.entry_exame,
            self.entry_status,
            self.entry_operador,
            self.entry_busca,
            self.entry_sort_by,
        ):
            widget.delete(0, "end")
        self.combo_sort_direction.set("desc")
        self.entry_page.delete(0, "end")
        self.entry_page.insert(0, "1")
        self.entry_page_size.delete(0, "end")
        self.entry_page_size.insert(0, "100")
        self.combo_view.set(VIEW_CORRIDAS)
        self._quick_filter_chip.set("nenhum")
        self._run_query()

    def _export_result(self, fmt: str) -> None:
        if self._fallback_activated:
            return
        try:
            if self._last_result is None:
                self._run_query()
            if self._last_result is None:
                raise RuntimeError("resultado de consulta indisponivel para exportacao")

            output_dir = self._resolve_output_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"consulta_operacional_{self._last_result.view}_{timestamp}"
            output_path = output_dir / base_name
            exported = self._viewer.export_dataframe(
                dataframe=self._last_result.rows,
                output_path=output_path,
                file_format=fmt,
                operator=self._user_id,
                view=self._last_result.view,
            )
            messagebox.showinfo(
                "Exportacao",
                f"Arquivo exportado com sucesso:\n{exported}",
                parent=self,
            )
        except Exception as exc:
            self._activate_legacy_fallback("export_error", exc)

    def _resolve_output_dir(self) -> Path:
        try:
            paths = config_service.get_paths()
        except Exception:
            paths = {}
        target = paths.get("reports_dir") or "reports"
        out = Path(target)
        out.mkdir(parents=True, exist_ok=True)
        return out

    def _build_query_options(self) -> QueryOptions:
        return QueryOptions(
            view=self.combo_view.get(),
            periodo_inicio=self._safe_text(self.entry_periodo_inicio.get()),
            periodo_fim=self._safe_text(self.entry_periodo_fim.get()),
            exame=self._safe_text(self.entry_exame.get()),
            status=self._safe_text(self.entry_status.get()),
            operador=self._safe_text(self.entry_operador.get()),
            busca_textual=self._safe_text(self.entry_busca.get()),
            sort_by=self._safe_text(self.entry_sort_by.get()),
            sort_direction=self.combo_sort_direction.get(),
            page=self._safe_int(self.entry_page.get(), default=1),
            page_size=self._safe_int(self.entry_page_size.get(), default=100),
            user_id=self._user_id,
        )

    def _capture_state(self) -> dict:
        return {
            "view": self.combo_view.get(),
            "periodo_inicio": self.entry_periodo_inicio.get().strip(),
            "periodo_fim": self.entry_periodo_fim.get().strip(),
            "exame": self.entry_exame.get().strip(),
            "status": self.entry_status.get().strip(),
            "operador": self.entry_operador.get().strip(),
            "busca_textual": self.entry_busca.get().strip(),
            "sort_by": self.entry_sort_by.get().strip(),
            "sort_direction": self.combo_sort_direction.get().strip() or "desc",
            "page": self._safe_int(self.entry_page.get(), default=1),
            "page_size": self._safe_int(self.entry_page_size.get(), default=100),
        }

    def _persist_user_state(self, result: QueryResult) -> None:
        state = self._capture_state()
        state["page"] = int(result.page)
        state["page_size"] = int(result.page_size)
        state["sort_by"] = str(result.applied_sort_by or "")
        state["sort_direction"] = str(result.applied_sort_direction or "desc")
        try:
            self._profile_store.save_user_state(self._user_id, state)
        except Exception as exc:
            registrar_log("HistoricoOperacional", f"Falha ao persistir estado: {exc}", "WARNING")

    def _load_user_state(self) -> None:
        try:
            state = self._profile_store.get_user_state(self._user_id)
        except Exception as exc:
            registrar_log("HistoricoOperacional", f"Falha ao carregar estado: {exc}", "WARNING")
            state = {}

        self.combo_view.set(str(state.get("view", VIEW_CORRIDAS) or VIEW_CORRIDAS))
        self._set_entry(self.entry_periodo_inicio, str(state.get("periodo_inicio", "") or ""))
        self._set_entry(self.entry_periodo_fim, str(state.get("periodo_fim", "") or ""))
        self._set_entry(self.entry_exame, str(state.get("exame", "") or ""))
        self._set_entry(self.entry_status, str(state.get("status", "") or ""))
        self._set_entry(self.entry_operador, str(state.get("operador", "") or ""))
        self._set_entry(self.entry_busca, str(state.get("busca_textual", "") or ""))
        self._set_entry(self.entry_sort_by, str(state.get("sort_by", "") or ""))
        self.combo_sort_direction.set(str(state.get("sort_direction", "desc") or "desc"))
        self._set_entry(self.entry_page, str(state.get("page", 1) or 1))
        page_size = self._safe_int(state.get("page_size", 100), default=100)
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))
        self._set_entry(self.entry_page_size, str(page_size))
        self._refresh_presets()

    def _refresh_presets(self) -> None:
        try:
            presets = self._profile_store.list_presets(self._user_id)
        except Exception:
            presets = {}
        self._presets_cache = presets
        names = sorted(presets.keys())
        if not names:
            self.combo_presets.configure(values=["(sem presets)"])
            self.combo_presets.set("(sem presets)")
            return
        self.combo_presets.configure(values=names)
        self.combo_presets.set(names[0])

    def _save_preset_dialog(self) -> None:
        name = simpledialog.askstring("Salvar preset", "Nome do preset:", parent=self)
        if name is None:
            return
        preset_name = str(name).strip()
        if not preset_name:
            messagebox.showwarning("Preset", "Nome do preset invalido.", parent=self)
            return
        try:
            self._profile_store.save_preset(self._user_id, preset_name, self._capture_state())
            self._refresh_presets()
            self.combo_presets.set(preset_name)
        except Exception as exc:
            messagebox.showerror("Preset", f"Falha ao salvar preset:\n{exc}", parent=self)

    def _apply_selected_preset(self) -> None:
        selected = str(self.combo_presets.get() or "").strip()
        if not selected or selected == "(sem presets)":
            return
        preset = getattr(self, "_presets_cache", {}).get(selected)
        if not isinstance(preset, dict):
            return
        self.combo_view.set(str(preset.get("view", VIEW_CORRIDAS) or VIEW_CORRIDAS))
        self._set_entry(self.entry_periodo_inicio, str(preset.get("periodo_inicio", "") or ""))
        self._set_entry(self.entry_periodo_fim, str(preset.get("periodo_fim", "") or ""))
        self._set_entry(self.entry_exame, str(preset.get("exame", "") or ""))
        self._set_entry(self.entry_status, str(preset.get("status", "") or ""))
        self._set_entry(self.entry_operador, str(preset.get("operador", "") or ""))
        self._set_entry(self.entry_busca, str(preset.get("busca_textual", "") or ""))
        self._set_entry(self.entry_sort_by, str(preset.get("sort_by", "") or ""))
        self.combo_sort_direction.set(str(preset.get("sort_direction", "desc") or "desc"))
        self._set_entry(self.entry_page, str(preset.get("page", 1) or 1))
        self._set_entry(self.entry_page_size, str(preset.get("page_size", 100) or 100))
        self._run_query()

    def _delete_selected_preset(self) -> None:
        selected = str(self.combo_presets.get() or "").strip()
        if not selected or selected == "(sem presets)":
            return
        try:
            self._profile_store.delete_preset(self._user_id, selected)
            self._refresh_presets()
        except Exception as exc:
            messagebox.showerror("Preset", f"Falha ao excluir preset:\n{exc}", parent=self)

    def _apply_quick_filter(self, chip: str) -> None:
        token = str(chip or "").strip().lower() or "nenhum"
        self._quick_filter_chip.set(token)
        updates = build_quick_filter_state(token)
        if "periodo_inicio" in updates:
            self._set_entry(self.entry_periodo_inicio, updates.get("periodo_inicio", ""))
        if "periodo_fim" in updates:
            self._set_entry(self.entry_periodo_fim, updates.get("periodo_fim", ""))
        if "status" in updates:
            self._set_entry(self.entry_status, updates.get("status", ""))
        self._set_entry(self.entry_page, "1")
        self._run_query()

    def _refresh_metrics_label(self) -> None:
        try:
            metrics = self._viewer.get_operational_metrics(last_n=5000)
            query_stats = metrics.get("by_operation", {}).get("operational_viewer.query", {})
            export_stats = metrics.get("by_operation", {}).get("operational_viewer.export", {})
            self.label_metrics.configure(
                text=(
                    "Analytics: "
                    f"Q={metrics.get('query_volume', 0)} "
                    f"(p50={query_stats.get('p50_ms', 0)}ms p95={query_stats.get('p95_ms', 0)}ms err={query_stats.get('error_rate', 0)}) | "
                    f"E={metrics.get('export_volume', 0)} "
                    f"(p95={export_stats.get('p95_ms', 0)}ms err={export_stats.get('error_rate', 0)})"
                )
            )
        except Exception as exc:
            registrar_log("HistoricoOperacional", f"Falha ao atualizar analytics: {exc}", "WARNING")

    def _refresh_health_summary(self) -> None:
        try:
            health = self._viewer.get_operational_health(last_n=5000)
            status = str(health.get("status", "unknown")).lower()
            alert_count = int(health.get("alert_count", 0) or 0)
            critical_count = int(health.get("critical_count", 0) or 0)
            recommendations = health.get("recommendations", [])
            top_recommendation = ""
            if isinstance(recommendations, list) and recommendations:
                top_recommendation = str(recommendations[0])
            self.label_health.configure(
                text=(
                    f"Saude={status} | alertas={alert_count} | criticos={critical_count}"
                    + (f" | recomendacao={top_recommendation}" if top_recommendation else "")
                )
            )

            panel = self._viewer.get_operational_slo_panel(last_n=10000)
            compliance = panel.get("compliance", {}) if isinstance(panel, dict) else {}
            summary = panel.get("summary", {}) if isinstance(panel, dict) else {}
            severity = str(compliance.get("severity", "info"))
            violations = int(compliance.get("violation_count", 0) or 0)
            window = summary.get("window", {}) if isinstance(summary, dict) else {}
            requests = int(window.get("requests", 0) or 0)
            self.label_slo.configure(
                text=f"SLO={severity} | violacoes={violations} | req_janela={requests}"
            )
        except Exception as exc:
            registrar_log("HistoricoOperacional", f"Falha ao avaliar saude operacional: {exc}", "WARNING")

    def _run_slo_automation(self) -> None:
        if self._fallback_activated:
            return
        try:
            result = self._viewer.run_operational_slo_automation(
                actor=self._user_id,
                dry_run=False,
                last_n=10000,
            )
            severity = str(result.get("severity", "info"))
            action = str(result.get("action", "monitorar"))
            message = str(result.get("message", "Automacao executada."))
            self._refresh_health_summary()
            messagebox.showinfo(
                "Automacao SLO",
                f"Severidade={severity}\nAcao={action}\n{message}",
                parent=self,
            )
            if severity == "critical" and bool(result.get("rollback_applied", False)):
                self._activate_legacy_fallback("slo_rollback", RuntimeError("rollback aplicado via automacao"))
        except Exception as exc:
            registrar_log("HistoricoOperacional", f"Falha na automacao SLO: {exc}", "WARNING")
            messagebox.showerror("Automacao SLO", f"Falha ao executar automacao:\n{exc}", parent=self)

    def _run_operational_readiness(self) -> None:
        if self._fallback_activated:
            return
        try:
            result = self._viewer.run_operational_readiness(
                actor=self._user_id,
                dry_run=None,
                last_n=10000,
            )
            automation = result.get("automation", {}) if isinstance(result, dict) else {}
            runbook = result.get("runbook", {}) if isinstance(result, dict) else {}
            severity = str(automation.get("severity", "info"))
            action = str(automation.get("action", "monitorar"))
            message = str(result.get("message", "Readiness executado."))
            first_step = ""
            steps = runbook.get("steps", []) if isinstance(runbook, dict) else []
            if isinstance(steps, list) and steps:
                first = steps[0] if isinstance(steps[0], dict) else {}
                first_step = str(first.get("instruction", ""))
            self._refresh_health_summary()
            messagebox.showinfo(
                "Readiness Operacional",
                (
                    f"Severidade={severity}\n"
                    f"Acao={action}\n"
                    f"{message}\n"
                    + (f"Primeiro passo: {first_step}" if first_step else "")
                ),
                parent=self,
            )
            if severity == "critical" and bool(automation.get("rollback_applied", False)):
                self._activate_legacy_fallback(
                    "readiness_rollback",
                    RuntimeError("rollback aplicado via readiness"),
                )
        except Exception as exc:
            registrar_log("HistoricoOperacional", f"Falha no readiness operacional: {exc}", "WARNING")
            messagebox.showerror("Readiness Operacional", f"Falha ao executar readiness:\n{exc}", parent=self)

    def _refresh_handover_summary(self) -> None:
        try:
            panel = self._viewer.get_operational_handover_panel(
                environments=("dev", "hml", "prod"),
                last_n=10000,
            )
            overall = panel.get("overall", {}) if isinstance(panel, dict) else {}
            envs = panel.get("environments", []) if isinstance(panel, dict) else []
            avg_score = int(overall.get("average_score", 0) or 0)
            ready = bool(overall.get("ready_for_go", False))
            pending_total = int(overall.get("pending_total", 0) or 0)

            env_parts = []
            if isinstance(envs, list):
                for item in envs:
                    if not isinstance(item, dict):
                        continue
                    env_name = str(item.get("environment", "")).strip() or "env"
                    score = int(item.get("score", 0) or 0)
                    decision = str(item.get("recommended_decision", "no-go"))
                    env_parts.append(f"{env_name}:{score}/{decision}")
            env_text = " | ".join(env_parts[:3])

            self.label_handover.configure(
                text=(
                    f"Handover=({'GO' if ready else 'NO-GO'}) "
                    f"| score_medio={avg_score} | pendencias={pending_total}"
                    + (f" | {env_text}" if env_text else "")
                )
            )
        except Exception as exc:
            registrar_log("HistoricoOperacional", f"Falha ao atualizar handover: {exc}", "WARNING")

    def _apply_handover_decision_dialog(self) -> None:
        if self._fallback_activated:
            return
        try:
            readiness = self._viewer.get_operational_handover_readiness(
                environment="prod",
                last_n=10000,
            )
            recommended = str(readiness.get("recommended_decision", "no-go"))
            score = int(readiness.get("score", 0) or 0)
            severity = str((readiness.get("slo_status", {}) or {}).get("severity", "info"))

            choice = messagebox.askyesnocancel(
                "Decisao Go/No-Go",
                (
                    "Aplicar decisao de handover para PROD?\n\n"
                    f"Recomendado: {recommended.upper()}\n"
                    f"Score: {score}\n"
                    f"Severidade SLO: {severity}\n\n"
                    "Sim = GO | Nao = NO-GO | Cancelar = abortar"
                ),
                parent=self,
            )
            if choice is None:
                return
            decision = "go" if bool(choice) else "no-go"

            result = self._viewer.apply_operational_handover_decision(
                environment="prod",
                actor=self._user_id,
                decision=decision,
                reason="manual_ui_f12",
                dry_run=False,
                last_n=10000,
            )
            self._refresh_handover_summary()
            self._refresh_health_summary()

            messagebox.showinfo(
                "Decisao Handover",
                (
                    f"Decisao aplicada: {str(result.get('decision', ''))}\n"
                    f"Recomendado: {str(result.get('recommended_decision', ''))}\n"
                    f"Score: {int(result.get('score', 0) or 0)}\n"
                    f"Acao flag: {str(result.get('feature_flag_action', 'none'))}"
                ),
                parent=self,
            )
            if str(result.get("decision", "")).lower() == "no-go" and bool(
                result.get("rollback_applied", False)
            ):
                self._activate_legacy_fallback(
                    "handover_no_go",
                    RuntimeError("rollback aplicado via decisao de handover"),
                )
        except Exception as exc:
            registrar_log("HistoricoOperacional", f"Falha ao aplicar decisao de handover: {exc}", "WARNING")
            messagebox.showerror("Decisao Handover", f"Falha ao aplicar decisao:\n{exc}", parent=self)

    def _rollback_operational_viewer_flag(self) -> None:
        if self._fallback_activated:
            return
        confirm = messagebox.askyesno(
            "Rollback",
            (
                "Deseja aplicar rollback da feature flag "
                "`USE_OPERATIONAL_TABULAR_VIEWER` agora?\n\n"
                "A tela sera redirecionada para o modo legado."
            ),
            parent=self,
        )
        if not confirm:
            return
        result = self._viewer.apply_operational_rollback(
            reason="manual_ui_f9",
            actor=self._user_id,
            dry_run=False,
        )
        if bool(result.get("ok")):
            messagebox.showinfo("Rollback", str(result.get("message", "Rollback aplicado.")), parent=self)
            self._activate_legacy_fallback("rollback_flag", RuntimeError("rollback aplicado"))
            return
        messagebox.showerror("Rollback", str(result.get("message", "Falha ao aplicar rollback.")), parent=self)

    def _render_result(self, dataframe) -> None:
        self.tree.delete(*self.tree.get_children())
        columns = [str(col) for col in list(dataframe.columns)]
        self.tree.configure(columns=columns)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor="w")
        for row in dataframe.fillna("").itertuples(index=False):
            self.tree.insert("", "end", values=tuple(row))

    def _activate_legacy_fallback(self, reason: str, error: Exception) -> None:
        if self._fallback_activated:
            return
        self._fallback_activated = True
        registrar_log(
            "HistoricoOperacional",
            f"Fallback para historico legado (reason={reason}): {error}",
            "WARNING",
        )
        if self._on_fallback_legacy is not None:
            self._on_fallback_legacy(reason, error)

    def _close_page(self) -> None:
        if self._on_close_callback is not None:
            self._on_close_callback()
            return
        self.destroy()

    @staticmethod
    def _safe_text(value: object) -> Optional[str]:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _set_entry(widget: ctk.CTkEntry, value: str) -> None:
        widget.delete(0, "end")
        widget.insert(0, str(value or ""))

    @staticmethod
    def _safe_int(value: object, *, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default)


def create_operational_historico_page(
    *,
    parent: ctk.CTkFrame,
    main_window,
    on_close_callback: Optional[Callable[[], None]] = None,
    on_fallback_legacy: Optional[Callable[[str, Exception], None]] = None,
) -> ctk.CTkFrame:
    """Factory da pagina operacional de historico."""
    return HistoricoOperacionalPage(
        host_frame=parent,
        main_window=main_window,
        on_close_callback=on_close_callback,
        on_fallback_legacy=on_fallback_legacy,
    )


__all__ = ["HistoricoOperacionalPage", "create_operational_historico_page"]
