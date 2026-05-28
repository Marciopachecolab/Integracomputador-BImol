# -*- coding: utf-8 -*-
"""Adapter dedicado para coleta de dialogs da UI no fluxo GAL."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

import customtkinter as ctk
from tkinter import filedialog, simpledialog

from services.core.config_service import config_service


@dataclass(frozen=True)
class GalUIDialogResult:
    """Resultado consolidado da coleta de dialogs para envio GAL."""

    csv_path: str
    observacao: str
    relatorio_filename: str


class GalMetadataDialog(ctk.CTkToplevel):
    def __init__(self, parent, initial_report_name: str):
        super().__init__(parent)
        self.title("Metadados do Envio GAL")
        self.geometry("600x450")
        
        if hasattr(parent, "winfo_toplevel"):
            self.transient(parent.winfo_toplevel())
        self.attributes("-topmost", True)
        self.resizable(False, False)
        
        self.result = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        
        ctk.CTkLabel(self, text="Nome do Relatório (TXT):", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.entry_relatorio = ctk.CTkEntry(self, width=560, height=40, font=("Segoe UI", 14))
        self.entry_relatorio.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.entry_relatorio.insert(0, initial_report_name)
        
        ctk.CTkLabel(self, text="Observações (opcional):", font=("Segoe UI", 14, "bold")).grid(row=2, column=0, padx=20, pady=(15, 5), sticky="w")
        self.text_obs = ctk.CTkTextbox(self, width=560, height=150, font=("Segoe UI", 14))
        self.text_obs.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, padx=20, pady=20, sticky="e")
        
        ctk.CTkButton(btn_frame, text="Cancelar", command=self.cancelar, width=120, fg_color="gray").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Confirmar", command=self.confirmar, width=120).pack(side="left")
        
    def confirmar(self):
        obs = self.text_obs.get("1.0", "end-1c").strip()
        relatorio = self.entry_relatorio.get().strip()
        self.result = {"observacao": obs, "relatorio": relatorio}
        self.destroy()
        
    def cancelar(self):
        self.destroy()


class GalUIDialogAdapter:
    """Encapsula dialogs de selecao/entrada da UI para envio GAL."""

    def __init__(
        self,
        *,
        select_file_fn: Optional[Callable[[object], Optional[str]]] = None,
        ask_string_fn: Optional[Callable[[str, str, object, Optional[str]], Optional[str]]] = None,
        now_fn: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._select_file_fn = select_file_fn or self._default_select_file
        self._ask_string_fn = ask_string_fn or self._default_ask_string
        self._now_fn = now_fn or datetime.now

    @staticmethod
    def _default_select_file(parent: object) -> Optional[str]:
        # FASE 3: Resolver diretorio reports dinamicamente usando config_service
        initial_dir = None
        try:
            cfg = config_service.get_all()
            data_root = cfg.get("data_root")
            paths = cfg.get("paths", {})
            reports_dir = paths.get("default_results_folder") or paths.get("reports_dir") or "reports"
            
            if data_root:
                if not os.path.isabs(reports_dir):
                    reports_dir = os.path.join(data_root, reports_dir)
                if not os.path.exists(reports_dir):
                    os.makedirs(reports_dir, exist_ok=True)
                initial_dir = os.path.abspath(reports_dir)
            else:
                if os.path.exists(reports_dir):
                    initial_dir = os.path.abspath(reports_dir)
        except Exception:
            pass

        kwargs = {
            "title": "Selecionar CSV de resultados",
            "filetypes": [("CSV files", "*.csv")],
            "parent": parent,
        }
        if initial_dir:
            kwargs["initialdir"] = initial_dir

        return filedialog.askopenfilename(**kwargs)

    @staticmethod
    def _default_ask_string(
        title: str,
        prompt: str,
        parent: object,
        initialvalue: Optional[str] = None,
    ) -> Optional[str]:
        kwargs = {"parent": parent}
        if initialvalue is not None:
            kwargs["initialvalue"] = initialvalue
        return simpledialog.askstring(title, prompt, **kwargs)

    def collect(self, parent: object) -> Optional[GalUIDialogResult]:
        """Coleta arquivo, observacao e nome de relatorio; retorna None se cancelado."""
        csv_path = (self._select_file_fn(parent) or "").strip()
        if not csv_path:
            return None

        # FASE 3: Novo fluxo visual com campos agrupados e redimensionados
        initial_name = f"relatorio_envio_{self._now_fn().strftime('%Y%m%d_%H%M')}"
        
        dialog = GalMetadataDialog(parent, initial_name)
        dialog.grab_set()
        
        # Esperar fechar
        if hasattr(parent, "wait_window"):
            parent.wait_window(dialog)
        else:
            dialog.wait_window(dialog)
            
        if not dialog.result:
            return None
            
        observacao_raw = dialog.result["observacao"]
        observacao = observacao_raw.strip() or "Nenhuma observacao."

        report_name = dialog.result["relatorio"]
        if not report_name:
            report_name = f"relatorio_envio_{self._now_fn().strftime('%Y%m%d_%H%M%S')}.txt"
        elif not report_name.lower().endswith(".txt"):
            report_name = f"{report_name}.txt"

        return GalUIDialogResult(
            csv_path=csv_path,
            observacao=observacao,
            relatorio_filename=report_name,
        )
