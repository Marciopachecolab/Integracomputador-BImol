# -*- coding: utf-8 -*-
"""
Admin panel - Initial Setup (Instalacao Inicial).

UI-only wrapper that validates and prepares shared storage paths.
Access is restricted to ADMIN users.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

import customtkinter as ctk
from tkinter import filedialog, messagebox

from services.core.config_service import config_service
from services.installation_checks import build_setup_report
from services.installation_checks import export_setup_report
from services.installation_checks import summarize_checks
from utils.logger import registrar_log


class InitialSetupPanel:
    """Initial setup UI for admin users."""

    def __init__(self, parent, main_window, usuario_logado: str, nivel_acesso: str):
        self.parent = parent
        self.main_window = main_window
        self.usuario_logado = usuario_logado or "Desconhecido"
        self.nivel_acesso = str(nivel_acesso or "").upper()
        self.config_service = config_service

        if not self._is_admin():
            self._render_blocked()
            return

        self._build()

    def _is_admin(self) -> bool:
        return self.nivel_acesso in ("ADMIN", "MASTER")

    def _render_blocked(self) -> None:
        registrar_log(
            "AdminPanel",
            f"Instalacao Inicial bloqueada para {self.usuario_logado} (nivel: {self.nivel_acesso})",
            "WARNING",
        )
        messagebox.showerror(
            "Acesso Negado",
            "Funcionalidade restrita a usuarios ADMIN.",
            parent=self.main_window,
        )

    def _build(self) -> None:
        frame = ctk.CTkFrame(self.parent)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            frame,
            text="Instalacao Inicial",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            frame,
            text=f"Usuario: {self.usuario_logado} | Nivel: {self.nivel_acesso}",
            font=ctk.CTkFont(size=12),
        ).pack(pady=(0, 12))

        actions = ctk.CTkFrame(frame)
        actions.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            actions,
            text="Revalidar Checklist",
            command=self._render_status,
            width=180,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            actions,
            text="Preparar Pastas",
            command=self._prepare_dirs,
            width=180,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            actions,
            text="Abrir Wizard",
            command=self._open_wizard,
            width=160,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            actions,
            text="Exportar Relatorio",
            command=self._export_report,
            width=160,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            actions,
            text="Restaurar Backup",
            command=self._restore_backup,
            width=160,
            fg_color="#D32F2F",
            hover_color="#B71C1C",
        ).pack(side="left", padx=6)

        shared_frame = ctk.CTkFrame(frame)
        shared_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            shared_frame,
            text="Compartilhamento padrão (UNC ou pasta local do servidor):",
        ).pack(anchor="w", padx=6, pady=(8, 4))

        entry_line = ctk.CTkFrame(shared_frame)
        entry_line.pack(fill="x", padx=6, pady=(0, 8))

        self.entry_shared_root = ctk.CTkEntry(
            entry_line,
            placeholder_text=r"Ex: \\SERVIDOR\Integragal ou D:\IntegragalShare",
        )
        self.entry_shared_root.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            entry_line,
            text="Selecionar Pasta",
            width=140,
            command=self._select_shared_root,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            entry_line,
            text="Padronizar Compartilhamento",
            width=220,
            command=self._apply_shared_storage_standardization,
        ).pack(side="left", padx=4)

        current_root = str(self.config_service.get("data_root", "") or "").strip()
        if current_root:
            self.entry_shared_root.insert(0, current_root)

        self.status_text = ctk.CTkTextbox(frame, height=420)
        self.status_text.pack(fill="both", expand=True, pady=8)
        self.report = None
        self._render_status()

    def _render_status(self) -> None:
        self.report = build_setup_report(self.usuario_logado)
        self._set_status_lines(self._collect_status_lines())

    def _prepare_dirs(self) -> None:
        try:
            paths = self.config_service.get_paths()
            
            to_create = []
            for raw in paths.values():
                if not raw:
                    continue
                p = Path(raw)
                target_dir = p if p.suffix == "" else p.parent
                if target_dir and not target_dir.exists() and str(target_dir) not in to_create:
                    to_create.append(str(target_dir))
            
            if not to_create:
                messagebox.showinfo(
                    "Dry-Run",
                    "Nenhuma pasta nova precisa ser criada. Todas já existem.",
                    parent=self.main_window,
                )
                return
            
            preview_msg = "Dry-Run: As seguintes pastas serão criadas:\n\n" + "\n".join(to_create) + "\n\nDeseja prosseguir com a criação?"
            if not messagebox.askyesno("Confirmar Criação", preview_msg, parent=self.main_window):
                return
                
            created = self._ensure_dirs(paths.values())
            self.report = build_setup_report(self.usuario_logado)
            self._set_status_lines(
                self._collect_status_lines(
                    extra_lines=created, title="Preparacao de Pastas"
                )
            )
            messagebox.showinfo(
                "Preparacao Concluida",
                f"Pastas preparadas: {len(created)}",
                parent=self.main_window,
            )
        except Exception as exc:
            registrar_log("AdminPanel", f"Falha ao preparar pastas: {exc}", "ERROR")
            messagebox.showerror(
                "Erro",
                f"Falha ao preparar pastas: {exc}",
                parent=self.main_window,
            )

    def _collect_status_lines(
        self, extra_lines: Iterable[str] | None = None, title: str = "Checklist"
    ) -> Tuple[str, ...]:
        report = self.report or build_setup_report(self.usuario_logado)
        lines = [f"[{title}]", ""]

        lines.append(f"Data/Hora: {report.timestamp}")
        lines.append(f"Usuario (App): {report.app_user}")
        lines.append(f"Usuario (OS): {report.os_user}")
        lines.append(f"data_root: {report.data_root or '(vazio)'}")
        lines.append(
            f"allowed_roots: {report.allowed_roots if report.allowed_roots else '(vazio)'}"
        )
        shared_status = self.config_service.get_shared_storage_status()
        lines.append(f"shared_storage.required: {shared_status.get('required', False)}")
        lines.append(f"shared_storage.ready: {shared_status.get('ready', False)}")
        lines.append(f"shared_storage.same_root_policy: {shared_status.get('same_root_policy', False)}")
        lines.append(f"shared_storage.read_write_ok: {shared_status.get('read_write_ok', False)}")
        lines.append("")

        ok, warn, fail = summarize_checks(
            report.path_checks + report.csv_checks + report.acl_checks
        )
        lines.append(f"Resumo: OK={ok} | WARN={warn} | FAIL={fail}")
        lines.append("")

        lines.append("[Paths]")
        lines.extend(self._format_checks(report.path_checks))
        lines.append("")
        lines.append("[CSV Integridade]")
        lines.extend(self._format_checks(report.csv_checks))
        lines.append("")
        lines.append("[ACL Share]")
        lines.extend(self._format_checks(report.acl_checks))

        if extra_lines:
            lines.append("")
            lines.append("[Pastas criadas/garantidas]")
            lines.extend(extra_lines)

        return tuple(lines)

    def _format_checks(self, checks):
        return [f"- [{c.status}] {c.name}: {c.message}" for c in checks]

    def _open_wizard(self) -> None:
        from ui.admin_initial_setup_wizard import InitialSetupWizard

        # Criar backup baseline antes de abrir o wizard para garantir rollback de alterações do assistente
        ok, msg = self.config_service.create_installation_backup()
        if not ok:
            if not messagebox.askyesno(
                "Aviso de Backup",
                f"Não foi possível criar backup baseline ({msg}).\n\nDeseja abrir o assistente mesmo assim?",
                parent=self.main_window,
            ):
                return

        report = self.report or build_setup_report(self.usuario_logado)
        InitialSetupWizard(self.main_window, report)

    def _export_report(self) -> None:
        report = self.report or build_setup_report(self.usuario_logado)
        try:
            output_path = export_setup_report(report)
            messagebox.showinfo(
                "Relatorio Exportado",
                f"Relatorio salvo em:\n{output_path}",
                parent=self.main_window,
            )
        except Exception as exc:
            registrar_log("AdminPanel", f"Falha ao exportar relatorio: {exc}", "ERROR")
            messagebox.showerror(
                "Erro",
                f"Falha ao exportar relatorio: {exc}",
                parent=self.main_window,
            )

    def _restore_backup(self) -> None:
        if not messagebox.askyesno(
            "Restaurar Backup Baseline",
            "Deseja restaurar a configuração a partir do backup baseline de instalação (config.json.baseline.bak)?\nIsso desfará TODAS as alterações feitas desde a última criação de baseline.",
            parent=self.main_window,
        ):
            return

        ok, msg = self.config_service.restore_installation_backup()
        if ok:
            self._render_status()
            messagebox.showinfo("Backup Restaurado", msg, parent=self.main_window)
        else:
            messagebox.showerror("Erro", msg, parent=self.main_window)

    def _ensure_dirs(self, paths: Iterable[str]) -> Tuple[str, ...]:
        created = []
        for raw in paths:
            if not raw:
                continue
            p = Path(raw)
            target_dir = p if p.suffix == "" else p.parent
            if not target_dir:
                continue
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
                created.append(str(target_dir))
        return tuple(created)

    def _select_shared_root(self) -> None:
        selected = filedialog.askdirectory(parent=self.main_window, title="Selecionar compartilhamento")
        if not selected:
            return
        self.entry_shared_root.delete(0, "end")
        self.entry_shared_root.insert(0, selected)

    def _apply_shared_storage_standardization(self) -> None:
        shared_root = self.entry_shared_root.get().strip()
        if not shared_root:
            messagebox.showwarning(
                "Compartilhamento obrigatório",
                "Informe o caminho do compartilhamento antes de padronizar.",
                parent=self.main_window,
            )
            return

        preview_msg = (
            f"Dry-Run (Resumo da Configuração):\n\n"
            f"Você está prestes a padronizar o armazenamento usando a raiz:\n"
            f"-> {shared_root}\n\n"
            f"Alterações previstas no config.json:\n"
            f"- 'data_root' e 'allowed_roots' serão atualizados para a nova raiz.\n"
            f"- 'shared_storage.required' será ativado (True).\n"
            f"- Todos os caminhos de dados (banco, logs, CSVs, etc.) serão convertidos para relativos baseados na nova raiz.\n\n"
            f"Tem certeza que deseja gravar essas alterações?"
        )
        if not messagebox.askyesno(
            "Confirmação de Padronização",
            preview_msg,
            parent=self.main_window,
        ):
            return

        ok, msg = self.config_service.configure_shared_storage(shared_root)
        if not ok:
            messagebox.showerror("Erro", msg, parent=self.main_window)
            return

        self._render_status()
        messagebox.showinfo(
            "Compartilhamento padronizado",
            (
                "Configuração aplicada com sucesso.\n"
                "Todos os terminais devem usar o mesmo config.json e este mesmo compartilhamento."
            ),
            parent=self.main_window,
        )

    def _set_status_lines(self, lines: Iterable[str]) -> None:
        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", "end")
        for line in lines:
            self.status_text.insert("end", f"{line}\n")
        self.status_text.configure(state="disabled")
