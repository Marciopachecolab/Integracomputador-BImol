# -*- coding: utf-8 -*-
"""
Wizard for initial installation checks (admin only).
"""

from __future__ import annotations

from typing import List, Tuple

import customtkinter as ctk
from tkinter import messagebox

from services.installation_checks import SetupReport
from services.installation_checks import export_setup_report
from services.installation_checks import summarize_checks


class InitialSetupWizard:
    def __init__(self, main_window, report: SetupReport):
        self.main_window = main_window
        self.report = report
        self.step_index = 0
        self.steps: List[Tuple[str, List[str]]] = self._build_steps()

        self.window = ctk.CTkToplevel(self.main_window)
        self.window.title("Wizard - Instalacao Inicial")
        self.window.geometry("900x650")
        self.window.transient(self.main_window)
        self.window.grab_set()

        self._build_ui()
        self._render_step()

    def _build_ui(self):
        header = ctk.CTkFrame(self.window)
        header.pack(fill="x", padx=20, pady=(20, 10))

        self.title_label = ctk.CTkLabel(
            header, text="", font=ctk.CTkFont(size=18, weight="bold")
        )
        self.title_label.pack(anchor="w")

        self.text = ctk.CTkTextbox(self.window, height=450)
        self.text.pack(fill="both", expand=True, padx=20, pady=10)

        footer = ctk.CTkFrame(self.window)
        footer.pack(fill="x", padx=20, pady=(0, 20))

        self.btn_prev = ctk.CTkButton(footer, text="Anterior", command=self._prev)
        self.btn_prev.pack(side="left", padx=6)

        self.btn_next = ctk.CTkButton(footer, text="Proximo", command=self._next)
        self.btn_next.pack(side="left", padx=6)

        self.btn_export = ctk.CTkButton(
            footer, text="Exportar Relatorio", command=self._export
        )
        self.btn_export.pack(side="right", padx=6)

        self.btn_close = ctk.CTkButton(
            footer, text="Fechar", command=self.window.destroy
        )
        self.btn_close.pack(side="right", padx=6)

    def _build_steps(self) -> List[Tuple[str, List[str]]]:
        ok, warn, fail = summarize_checks(
            self.report.path_checks + self.report.csv_checks + self.report.acl_checks
        )
        intro = [
            "Este wizard valida pre-requisitos da instalacao inicial.",
            "",
            f"Data/Hora: {self.report.timestamp}",
            f"Usuario (App): {self.report.app_user}",
            f"Usuario (OS): {self.report.os_user}",
            "",
            f"Resumo atual: OK={ok} | WARN={warn} | FAIL={fail}",
            "",
            "Prossiga para ver detalhes por etapa.",
        ]

        path_lines = self._format_checks(self.report.path_checks)
        csv_lines = self._format_checks(self.report.csv_checks)
        acl_lines = self._format_checks(self.report.acl_checks)

        summary = [
            "Resumo final da instalacao:",
            "",
            f"OK={ok} | WARN={warn} | FAIL={fail}",
            "",
            "Use o botao 'Exportar Relatorio' para salvar o resultado.",
        ]

        return [
            ("Introducao", intro),
            ("Checklist de Paths", path_lines),
            ("Integridade de CSVs", csv_lines),
            ("ACL do Share", acl_lines),
            ("Resumo e Exportacao", summary),
        ]

    def _render_step(self):
        title, lines = self.steps[self.step_index]
        self.title_label.configure(text=f"{self.step_index + 1}/{len(self.steps)} - {title}")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        for line in lines:
            self.text.insert("end", f"{line}\n")
        self.text.configure(state="disabled")

        self.btn_prev.configure(state="normal" if self.step_index > 0 else "disabled")
        self.btn_next.configure(
            state="normal" if self.step_index < len(self.steps) - 1 else "disabled"
        )

    def _next(self):
        if self.step_index < len(self.steps) - 1:
            self.step_index += 1
            self._render_step()

    def _prev(self):
        if self.step_index > 0:
            self.step_index -= 1
            self._render_step()

    def _export(self):
        try:
            output_path = export_setup_report(self.report)
            messagebox.showinfo(
                "Relatorio Exportado",
                f"Relatorio salvo em:\n{output_path}",
                parent=self.window,
            )
        except Exception as exc:
            messagebox.showerror(
                "Erro",
                f"Falha ao exportar relatorio: {exc}",
                parent=self.window,
            )

    def _format_checks(self, checks):
        return [f"- [{c.status}] {c.name}: {c.message}" for c in checks]
