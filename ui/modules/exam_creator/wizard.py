from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable, Optional

import customtkinter as ctk

from services.exam_domain_contracts import (
    SUPPORTED_FILTERS,
    SUPPORTED_TYPES,
    is_control_internal_type,
    is_supported_target_filter,
    is_supported_target_type,
    normalize_target_filter,
    normalize_target_type,
)
from utils.logger import registrar_log


class ExamCreatorWizardPage(ctk.CTkFrame):
    """Wizard de criacao de exame com contrato V2 (pocos/alvos/ct)."""

    def __init__(
        self,
        parent,
        *,
        on_close: Optional[Callable[[], None]] = None,
        dialog_parent=None,
    ) -> None:
        super().__init__(parent)
        self.on_close = on_close
        self.dialog_parent = dialog_parent or self.winfo_toplevel()
        self.current_step = 1
        self.exam_data: dict[str, object] = {}
        self.temp_targets: list[dict[str, Any]] = []
        self.temp_ct_thresholds: list[dict[str, Any]] = []
        self._registry_exam_rows: list[tuple[str, str]] = []
        self._editing_slug: str = ""

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.lbl_step = ctk.CTkLabel(
            self,
            text="Passo 1: Dados Basicos",
            font=("Arial", 20, "bold"),
        )
        self.lbl_step.grid(row=0, column=0, pady=20)

        ScrollableFrame = getattr(ctk, "CTkScrollableFrame", ctk.CTkFrame)
        self.content_frame = ScrollableFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        self.nav_frame = ctk.CTkFrame(self, height=50)
        self.nav_frame.grid(row=2, column=0, padx=20, pady=20, sticky="ew")

        self.btn_prev = ctk.CTkButton(
            self.nav_frame,
            text="< Voltar",
            state="disabled",
            command=self.prev_step,
        )
        self.btn_prev.pack(side="left", padx=10)

        self.btn_next = ctk.CTkButton(
            self.nav_frame,
            text="Próximo >",
            command=self.next_step,
        )
        self.btn_next.pack(side="right", padx=10)

        self.render_step_1()

    def _close_page(self) -> None:
        if self.on_close is not None:
            self.on_close()
            return
        self.destroy()

    def clear_content(self) -> None:
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def _pocos_values(self) -> list[str]:
        return ["1", "2", "3", "4"]

    def _selected_pocos(self) -> int:
        value = getattr(self, "cmb_pocos", None)
        if value is None:
            return int(self.exam_data.get("pocos_por_amostra", 1) or 1)
        try:
            selected = int(self.cmb_pocos.get())
        except Exception:
            selected = int(self.exam_data.get("pocos_por_amostra", 1) or 1)
        return selected if selected in (1, 2, 3, 4) else 1

    def _pocos_selector_values(self) -> list[str]:
        return [str(i) for i in range(1, self._selected_pocos() + 1)]

    def _ct_target_key(self, alvo: str, poco: int) -> str:
        return f"{alvo}|P{poco}"

    def render_step_1(self) -> None:
        self.clear_content()
        self.lbl_step.configure(text="Passo 1: Identificacao e Pocos")
        self.btn_prev.configure(state="disabled")
        self.btn_next.configure(text="Próximo >")

        ctk.CTkLabel(self.content_frame, text="Nome do Exame (Visivel):").pack(pady=5)
        self.ent_name = ctk.CTkEntry(
            self.content_frame,
            width=400,
            placeholder_text="Ex: Painel Respiratorio 2026",
        )
        self.ent_name.pack(pady=5)
        if self.exam_data.get("display_name"):
            self.ent_name.insert(0, str(self.exam_data["display_name"]))

        ctk.CTkLabel(self.content_frame, text="ID do Protocolo (Sistema):").pack(pady=5)
        self.ent_id = ctk.CTkEntry(
            self.content_frame,
            width=400,
            placeholder_text="Ex: pnl_resp_2026",
        )
        self.ent_id.pack(pady=5)
        if self.exam_data.get("id"):
            self.ent_id.insert(0, str(self.exam_data["id"]))

        ctk.CTkLabel(self.content_frame, text="Versao:").pack(pady=5)
        self.ent_ver = ctk.CTkEntry(self.content_frame, width=100)
        self.ent_ver.pack(pady=5)
        self.ent_ver.insert(0, str(self.exam_data.get("version", "1.0") or "1.0"))

        ctk.CTkLabel(self.content_frame, text="Pocos por amostra (1..4):").pack(pady=5)
        self.cmb_pocos = ctk.CTkComboBox(self.content_frame, values=self._pocos_values(), width=100)
        self.cmb_pocos.pack(pady=5)
        self.cmb_pocos.set(str(self.exam_data.get("pocos_por_amostra", 1) or 1))

        edit_label = (
            f"Editando exame existente: {self._editing_slug}"
            if self._editing_slug
            else "Modo atual: Novo exame"
        )
        ctk.CTkLabel(self.content_frame, text=edit_label).pack(pady=(10, 4))

        registry_frame = ctk.CTkFrame(self.content_frame)
        registry_frame.pack(fill="x", expand=False, padx=10, pady=(4, 8))

        ctk.CTkLabel(
            registry_frame,
            text="Exames já cadastrados (seleção com barra rolante):",
        ).pack(anchor="w", padx=8, pady=(8, 4))

        list_container = ctk.CTkFrame(registry_frame)
        list_container.pack(fill="x", expand=False, padx=8, pady=(0, 8))

        self.listbox_registry = tk.Listbox(
            list_container,
            height=5,
            font=("Consolas", 11),
            exportselection=False,
        )
        self.listbox_registry.pack(side="left", fill="both", expand=True)

        self.scrollbar_registry = ctk.CTkScrollbar(
            list_container, orientation="vertical", command=self.listbox_registry.yview
        )
        self.scrollbar_registry.pack(side="right", fill="y")
        self.listbox_registry.configure(yscrollcommand=self.scrollbar_registry.set)

        actions = ctk.CTkFrame(registry_frame)
        actions.pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkButton(
            actions,
            text="Recarregar Lista",
            width=150,
            command=self._refresh_registry_exam_list,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            actions,
            text="Editar Exame Selecionado",
            width=220,
            command=self._load_selected_exam_for_edit,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            actions,
            text="Ativar Exame",
            width=150,
            command=self._toggle_selected_exam_active,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            actions,
            text="Excluir Exame",
            width=150,
            command=self._delete_selected_exam,
            fg_color="red",
        ).pack(side="left", padx=4)

        self._refresh_registry_exam_list()

    def _refresh_registry_exam_list(self) -> None:
        self._registry_exam_rows = []
        listbox = getattr(self, "listbox_registry", None)
        if listbox is None:
            return

        listbox.delete(0, tk.END)
        try:
            from ui.modules.cadastros_diversos import RegistryExamEditor

            editor = RegistryExamEditor()
            self._registry_exam_rows = list(editor.load_all_exams())
        except Exception as exc:
            registrar_log("ExamCreator", f"Falha ao listar exames do registry: {exc}", "WARNING")
            listbox.insert(tk.END, "<falha ao carregar exames>")
            return

        if not self._registry_exam_rows:
            listbox.insert(tk.END, "<nenhum exame cadastrado>")
            return

        from services.exam_registry import registry
        for nome, slug in self._registry_exam_rows:
            is_active = registry.is_active(nome)
            status = " - EXAME ATIVADO" if is_active else ""
            listbox.insert(tk.END, f"{nome} [{slug}]{status}")

        if self._editing_slug:
            for idx, (_, slug) in enumerate(self._registry_exam_rows):
                if slug == self._editing_slug:
                    listbox.selection_clear(0, tk.END)
                    listbox.selection_set(idx)
                    listbox.see(idx)
                    break

    def _load_selected_exam_for_edit(self) -> None:
        listbox = getattr(self, "listbox_registry", None)
        if listbox is None:
            return

        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning(
                "Seleção obrigatória",
                "Selecione um exame na lista para editar.",
                parent=self.dialog_parent,
            )
            return

        idx = int(selection[0])
        if idx < 0 or idx >= len(self._registry_exam_rows):
            return
        _, slug = self._registry_exam_rows[idx]

        try:
            from ui.modules.cadastros_diversos import RegistryExamEditor

            editor = RegistryExamEditor()
            cfg = editor.load_exam(slug)
        except Exception as exc:
            messagebox.showerror(
                "Erro",
                f"Falha ao carregar exame para edição: {exc}",
                parent=self.dialog_parent,
            )
            return

        if cfg is None:
            messagebox.showerror(
                "Erro",
                "Exame selecionado não foi encontrado no registry.",
                parent=self.dialog_parent,
            )
            return

        self._open_full_exam_editor(cfg, slug=slug)

    def _toggle_selected_exam_active(self) -> None:
        listbox = getattr(self, "listbox_registry", None)
        if listbox is None:
            return

        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning(
                "Seleção obrigatória",
                "Selecione um exame na lista para ativar/desativar.",
                parent=self.dialog_parent,
            )
            return

        idx = int(selection[0])
        if idx < 0 or idx >= len(self._registry_exam_rows):
            return
        nome, slug = self._registry_exam_rows[idx]

        from services.core.config_service import config_service
        from services.exam_registry import _norm_exame, registry

        exams_cfg = config_service.get("exams", {})
        if not isinstance(exams_cfg, dict):
            exams_cfg = {}
        active = exams_cfg.get("active_exams", [])
        if not isinstance(active, list):
            active = []

        norm_target = _norm_exame(nome)

        # Check if already active
        is_active = any(_norm_exame(a) == norm_target for a in active)
        if is_active:
            # Deactivate
            new_active = [a for a in active if _norm_exame(a) != norm_target]
        else:
            # Activate
            new_active = list(active)
            new_active.append(nome)

        exams_cfg["active_exams"] = new_active
        config_service.set("exams", exams_cfg)
        config_service.save()

        # Reload registry cache
        registry.load()

        # Refresh UI
        self._refresh_registry_exam_list()
        
        status_msg = "ativado" if not is_active else "desativado"
        messagebox.showinfo(
            "Sucesso",
            f"O exame '{nome}' foi {status_msg} com sucesso.",
            parent=self.dialog_parent,
        )

    def _delete_selected_exam(self) -> None:
        listbox = getattr(self, "listbox_registry", None)
        if listbox is None:
            return

        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning(
                "Seleção obrigatória",
                "Selecione um exame na lista para excluir.",
                parent=self.dialog_parent,
            )
            return

        idx = int(selection[0])
        if idx < 0 or idx >= len(self._registry_exam_rows):
            return
        nome, slug = self._registry_exam_rows[idx]

        if not messagebox.askyesno(
            "Confirmar Exclusão",
            f"Deseja realmente excluir o exame '{nome}' do config.json?",
            parent=self.dialog_parent,
        ):
            return

        from services.core.config_service import config_service
        from services.exam_registry import _norm_exame, registry

        exams_cfg = config_service.get("exams", {})
        if not isinstance(exams_cfg, dict):
            exams_cfg = {}
            
        # Remover dos ativos se estiver la
        active = exams_cfg.get("active_exams", [])
        if isinstance(active, list):
            norm_target = _norm_exame(nome)
            exams_cfg["active_exams"] = [a for a in active if _norm_exame(a) != norm_target]
            
        # Remover do configs
        configs = exams_cfg.get("configs", {})
        if isinstance(configs, dict) and nome in configs:
            del configs[nome]
            exams_cfg["configs"] = configs
            
        config_service.set("exams", exams_cfg)
        config_service.save()

        # Reload registry cache
        registry.load()

        # Refresh UI
        self._refresh_registry_exam_list()
        
        messagebox.showinfo(
            "Sucesso",
            f"O exame '{nome}' foi excluído com sucesso.",
            parent=self.dialog_parent,
        )

    def _open_full_exam_editor(self, cfg: Any, *, slug: str) -> None:
        try:
            self._apply_registry_exam_to_wizard(cfg, slug=slug)
            self.render_step_1()
            
            # Show a success message
            messagebox.showinfo(
                "Edição",
                f"Você está editando o exame: {self.exam_data.get('display_name', slug)}\nSiga os passos do assistente para editar as informações.",
                parent=self.dialog_parent,
            )
        except Exception as exc:
            messagebox.showerror(
                "Erro",
                f"Erro ao carregar exame para edição: {exc}",
                parent=self.dialog_parent,
            )

    def _apply_registry_exam_to_wizard(self, cfg: Any, *, slug: str) -> None:
        self._editing_slug = str(slug or "").strip()

        display_name = str(getattr(cfg, "nome_exame", "") or "").strip()
        protocol_id = str(getattr(cfg, "slug", "") or "").strip()
        version = str(getattr(cfg, "versao_protocolo", "") or "").strip() or "1.0"
        pocos = int(getattr(cfg, "pocos_por_amostra", 1) or 1)
        if pocos not in (1, 2, 3, 4):
            pocos = 1

        raw_targets = list(getattr(cfg, "targets_por_poco", []) or [])
        mapped_targets: list[dict[str, Any]] = []
        for item in raw_targets:
            if not isinstance(item, dict):
                continue
            alvo = str(item.get("alvo", "")).strip()
            if not alvo:
                continue
            mapped_targets.append(
                {
                    "name": alvo,
                    "type": normalize_target_type(item.get("tipo", "VIRAL")),
                    "filter": normalize_target_filter(item.get("filtro", "FAM")),
                    "poco": int(item.get("poco", 1) or 1),
                }
            )

        if not mapped_targets:
            for alvo in list(getattr(cfg, "alvos", []) or []):
                alvo_nome = str(alvo).strip()
                if not alvo_nome:
                    continue
                mapped_targets.append(
                    {
                        "name": alvo_nome,
                        "type": "VIRAL",
                        "filter": "FAM",
                        "poco": 1,
                    }
                )

        raw_limiares = list(getattr(cfg, "limiares_ct_por_alvo_poco", []) or [])
        mapped_ct: list[dict[str, Any]] = []
        for item in raw_limiares:
            if not isinstance(item, dict):
                continue
            alvo = str(item.get("alvo", "")).strip()
            if not alvo:
                continue
            mapped_ct.append(
                {
                    "alvo": alvo,
                    "poco": int(item.get("poco", 1) or 1),
                    "ct_minimo": float(item.get("ct_minimo", 10.0)),
                    "ct_detectavel_limite": float(item.get("ct_detectavel_limite", 35.0)),
                    "ct_inconclusivo_limite": float(item.get("ct_inconclusivo_limite", 40.0)),
                }
            )

        if not mapped_ct and mapped_targets:
            faixas = dict(getattr(cfg, "faixas_ct", {}) or {})
            ct_min_default = float(faixas.get("rp_min", 10.0))
            ct_det_default = float(faixas.get("detect_max", 35.0))
            ct_inc_default = float(faixas.get("inconc_max", 40.0))
            for target in mapped_targets:
                mapped_ct.append(
                    {
                        "alvo": str(target.get("name", "")).strip(),
                        "poco": int(target.get("poco", 1) or 1),
                        "ct_minimo": ct_min_default,
                        "ct_detectavel_limite": ct_det_default,
                        "ct_inconclusivo_limite": ct_inc_default,
                    }
                )

        self.exam_data = {
            "display_name": display_name,
            "id": protocol_id,
            "version": version,
            "pocos_por_amostra": pocos,
            "targets": list(mapped_targets),
            "ct_thresholds": list(mapped_ct),
        }
        self.temp_targets = list(mapped_targets)
        self.temp_ct_thresholds = list(mapped_ct)

    def render_step_2(self) -> None:
        self.clear_content()
        self.lbl_step.configure(text="Passo 2: Alvos por Filtro e Poco")
        self.btn_prev.configure(state="normal")
        self.btn_next.configure(text="Próximo >")

        add_frame = ctk.CTkFrame(self.content_frame)
        add_frame.pack(fill="x", pady=10)

        self.ent_target = ctk.CTkEntry(add_frame, placeholder_text="Nome do Alvo (ex: SC2)")
        self.ent_target.pack(side="left", padx=5)

        self.cmb_type = ctk.CTkComboBox(
            add_frame,
            values=list(SUPPORTED_TYPES),
            width=170,
        )
        self.cmb_type.pack(side="left", padx=5)
        self.cmb_type.set("VIRAL")

        self.cmb_filter = ctk.CTkComboBox(
            add_frame,
            values=list(SUPPORTED_FILTERS),
            width=100,
        )
        self.cmb_filter.pack(side="left", padx=5)
        self.cmb_filter.set("FAM")

        self.cmb_poco = ctk.CTkComboBox(
            add_frame,
            values=self._pocos_selector_values(),
            width=80,
        )
        self.cmb_poco.pack(side="left", padx=5)
        self.cmb_poco.set("1")

        ctk.CTkButton(
            add_frame,
            text="+ Adicionar",
            width=100,
            command=self.add_target_to_list,
        ).pack(side="left", padx=5)

        self.targets_list = ctk.CTkTextbox(self.content_frame, height=280)
        self.targets_list.pack(fill="both", expand=True, padx=5, pady=5)

        if not self.temp_targets:
            legacy_targets = self.exam_data.get("targets", [])
            if isinstance(legacy_targets, list):
                for item in legacy_targets:
                    if isinstance(item, dict):
                        self.temp_targets.append(
                            {
                                "name": str(item.get("name", "")).strip(),
                                "type": normalize_target_type(item.get("type", "VIRAL")),
                                "filter": normalize_target_filter(item.get("filter", "FAM")),
                                "poco": int(item.get("poco", 1) or 1),
                            }
                        )
        self.update_targets_display()

    def render_step_3(self) -> None:
        self.clear_content()
        self.lbl_step.configure(text="Passo 3: Faixas de CT por Alvo")
        self.btn_prev.configure(state="normal")
        self.btn_next.configure(text="Salvar")

        self._seed_ct_thresholds_for_missing_targets()
        self._ct_entries: list[dict] = []

        # Cabeçalho fixo
        header = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header.pack(fill="x", padx=5, pady=(8, 0))
        header.grid_columnconfigure(0, weight=2)
        header.grid_columnconfigure((1, 2, 3), weight=1)
        ctk.CTkLabel(header, text="Alvo", font=("Arial", 12, "bold"), anchor="w").grid(
            row=0, column=0, padx=10, pady=6, sticky="w"
        )
        for col, label in enumerate(("CT Mínimo", "CT Detectável", "CT Inconclusivo"), 1):
            ctk.CTkLabel(header, text=label, font=("Arial", 12, "bold")).grid(
                row=0, column=col, padx=5, pady=6
            )

        # Linhas editáveis (uma por alvo+poco)
        ScrollableFrame = getattr(ctk, "CTkScrollableFrame", ctk.CTkFrame)
        scroll = ScrollableFrame(self.content_frame, height=300, fg_color="transparent")
        scroll.pack(fill="both", expand=True, pady=10)
        rows_frame = scroll
        rows_frame.grid_columnconfigure(0, weight=2)
        rows_frame.grid_columnconfigure((1, 2, 3), weight=1)

        for i, threshold in enumerate(self.temp_ct_thresholds):
            alvo = str(threshold.get("alvo", "")).strip()
            poco = int(threshold.get("poco", 1) or 1)

            row_bg = "transparent"
            row_frame = ctk.CTkFrame(rows_frame, fg_color=row_bg)
            row_frame.pack(fill="x", pady=1)
            row_frame.grid_columnconfigure(0, weight=2)
            row_frame.grid_columnconfigure((1, 2, 3), weight=1)

            label_text = f"{alvo} (P{poco})" if poco > 1 else alvo
            ctk.CTkLabel(row_frame, text=label_text, anchor="w").grid(
                row=0, column=0, padx=10, pady=5, sticky="w"
            )

            ent_min = ctk.CTkEntry(row_frame, width=110)
            ent_min.insert(0, str(threshold.get("ct_minimo", 10.0)))
            ent_min.grid(row=0, column=1, padx=5, pady=5)

            ent_det = ctk.CTkEntry(row_frame, width=110)
            ent_det.insert(0, str(threshold.get("ct_detectavel_limite", 35.0)))
            ent_det.grid(row=0, column=2, padx=5, pady=5)

            ent_inconc = ctk.CTkEntry(row_frame, width=110)
            ent_inconc.insert(0, str(threshold.get("ct_inconclusivo_limite", 40.0)))
            ent_inconc.grid(row=0, column=3, padx=5, pady=5)

            self._ct_entries.append({
                "alvo": alvo,
                "poco": poco,
                "min": ent_min,
                "det": ent_det,
                "inconc": ent_inconc,
            })

    def _ct_selector_values(self) -> list[str]:
        values: list[str] = []
        for target in self.temp_targets:
            name = str(target.get("name", "")).strip()
            poco = int(target.get("poco", 1) or 1)
            if not name:
                continue
            key = self._ct_target_key(name, poco)
            if key not in values:
                values.append(key)
        return values

    def _seed_ct_thresholds_for_missing_targets(self) -> None:
        existing = {
            (str(item.get("alvo", "")).strip().upper(), int(item.get("poco", 0) or 0))
            for item in self.temp_ct_thresholds
            if isinstance(item, dict)
        }
        for target in self.temp_targets:
            alvo = str(target.get("name", "")).strip()
            poco = int(target.get("poco", 1) or 1)
            key = (alvo.upper(), poco)
            if not alvo or key in existing:
                continue
            self.temp_ct_thresholds.append(
                {
                    "alvo": alvo,
                    "poco": poco,
                    "ct_minimo": 10.0,
                    "ct_detectavel_limite": 35.0,
                    "ct_inconclusivo_limite": 40.0,
                }
            )
            existing.add(key)

    def _collect_ct_from_table(self) -> bool:
        """Lê as Entries da tabela de CT e atualiza temp_ct_thresholds. Retorna False se inválido."""
        if not getattr(self, "_ct_entries", None):
            return True

        new_thresholds = []
        for entry in self._ct_entries:
            alvo = entry["alvo"]
            try:
                ct_min = float(str(entry["min"].get()).replace(",", "."))
                ct_det = float(str(entry["det"].get()).replace(",", "."))
                ct_inconc = float(str(entry["inconc"].get()).replace(",", "."))
            except ValueError:
                messagebox.showerror(
                    "Erro", f"Valores CT inválidos para o alvo '{alvo}'.", parent=self.dialog_parent
                )
                return False

            if not (0 <= ct_min <= 45 and 0 <= ct_det <= 45 and 0 <= ct_inconc <= 45):
                messagebox.showerror(
                    "Erro", f"CTs do alvo '{alvo}' devem estar entre 0 e 45.", parent=self.dialog_parent
                )
                return False

            if not (ct_min <= ct_det <= ct_inconc):
                messagebox.showerror(
                    "Erro",
                    f"Ordem inválida para '{alvo}': CT mínimo ≤ CT detectável ≤ CT inconclusivo.",
                    parent=self.dialog_parent,
                )
                return False

            new_thresholds.append({
                "alvo": alvo,
                "poco": entry["poco"],
                "ct_minimo": ct_min,
                "ct_detectavel_limite": ct_det,
                "ct_inconclusivo_limite": ct_inconc,
            })

        self.temp_ct_thresholds = new_thresholds
        return True

    def add_target_to_list(self) -> None:
        target_name = self.ent_target.get().strip()
        if not target_name:
            messagebox.showerror("Erro", "Informe o nome do alvo.", parent=self.dialog_parent)
            return

        try:
            poco = int(self.cmb_poco.get())
        except Exception:
            messagebox.showerror("Erro", "Poco invalido.", parent=self.dialog_parent)
            return

        pocos = self._selected_pocos()
        if poco < 1 or poco > pocos:
            messagebox.showerror("Erro", f"Poco deve estar entre 1 e {pocos}.", parent=self.dialog_parent)
            return

        key = (target_name.upper(), poco)
        for item in self.temp_targets:
            if (str(item.get("name", "")).strip().upper(), int(item.get("poco", 0) or 0)) == key:
                messagebox.showerror("Erro", "Duplicidade de alvo+poco.", parent=self.dialog_parent)
                return

        self.temp_targets.append(
            {
                "name": target_name,
                "type": normalize_target_type(self.cmb_type.get()),
                "filter": normalize_target_filter(self.cmb_filter.get()),
                "poco": poco,
            }
        )
        self.update_targets_display()
        self.ent_target.delete(0, "end")

    def add_ct_threshold_to_list(self) -> None:
        selector = self.cmb_ct_target.get().strip()
        if "|P" not in selector:
            messagebox.showerror("Erro", "Selecione um alvo+poco valido.", parent=self.dialog_parent)
            return
        alvo, poco_str = selector.split("|P", 1)

        try:
            poco = int(poco_str)
            ct_min = float(str(self.ent_ct_min.get()).replace(",", "."))
            ct_detect = float(str(self.ent_ct_detect.get()).replace(",", "."))
            ct_inconc = float(str(self.ent_ct_inconc.get()).replace(",", "."))
        except Exception:
            messagebox.showerror("Erro", "CTs devem ser numericos.", parent=self.dialog_parent)
            return

        if not (0 <= ct_min <= 45 and 0 <= ct_detect <= 45 and 0 <= ct_inconc <= 45):
            messagebox.showerror("Erro", "CTs devem estar entre 0 e 45.", parent=self.dialog_parent)
            return
        if not (ct_min <= ct_detect <= ct_inconc):
            messagebox.showerror(
                "Erro",
                "Ordem invalida de CT: minimo <= detectavel <= inconclusivo.",
                parent=self.dialog_parent,
            )
            return

        key = (alvo.strip().upper(), poco)
        updated = False
        for row in self.temp_ct_thresholds:
            row_key = (str(row.get("alvo", "")).strip().upper(), int(row.get("poco", 0) or 0))
            if row_key == key:
                row["ct_minimo"] = ct_min
                row["ct_detectavel_limite"] = ct_detect
                row["ct_inconclusivo_limite"] = ct_inconc
                updated = True
                break

        if not updated:
            self.temp_ct_thresholds.append(
                {
                    "alvo": alvo.strip(),
                    "poco": poco,
                    "ct_minimo": ct_min,
                    "ct_detectavel_limite": ct_detect,
                    "ct_inconclusivo_limite": ct_inconc,
                }
            )
        self.update_ct_display()

    def update_targets_display(self) -> None:
        text = ""
        for item in self.temp_targets:
            text += (
                f"[{item.get('type', '')}] {item.get('name', '')} "
                f"(Filtro: {item.get('filter', '')}, Poco: {item.get('poco', 1)})\n"
            )
        self.targets_list.delete("1.0", "end")
        self.targets_list.insert("1.0", text)

    def update_ct_display(self) -> None:
        text = ""
        for row in self.temp_ct_thresholds:
            text += (
                f"{row.get('alvo', '')}|P{row.get('poco', 0)} -> "
                f"min={row.get('ct_minimo', '')}, "
                f"det={row.get('ct_detectavel_limite', '')}, "
                f"incon={row.get('ct_inconclusivo_limite', '')}\n"
            )
        self.ct_list.delete("1.0", "end")
        self.ct_list.insert("1.0", text)

    def _build_v2_payload(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        raw_targets = getattr(self, "temp_targets", [])
        if not raw_targets and isinstance(self.exam_data.get("targets"), list):
            raw_targets = self.exam_data.get("targets", [])
        raw_limiares = getattr(self, "temp_ct_thresholds", [])
        if not raw_limiares and isinstance(self.exam_data.get("ct_thresholds"), list):
            raw_limiares = self.exam_data.get("ct_thresholds", [])

        targets = [
            {
                "alvo": str(item.get("name", "")).strip(),
                "filtro": normalize_target_filter(item.get("filter", "")),
                "poco": int(item.get("poco", 1) or 1),
                "tipo": normalize_target_type(item.get("type", "")),
            }
            for item in raw_targets
            if str(item.get("name", "")).strip()
        ]
        limiares = [
            {
                "alvo": str(item.get("alvo", "")).strip(),
                "poco": int(item.get("poco", 1) or 1),
                "ct_minimo": float(item.get("ct_minimo", 0.0)),
                "ct_detectavel_limite": float(item.get("ct_detectavel_limite", 0.0)),
                "ct_inconclusivo_limite": float(item.get("ct_inconclusivo_limite", 0.0)),
            }
            for item in raw_limiares
            if str(item.get("alvo", "")).strip()
        ]
        return targets, limiares

    def _validate_v2_payload(self) -> tuple[bool, str]:
        pocos = int(self.exam_data.get("pocos_por_amostra", 1) or 1)
        if pocos not in (1, 2, 3, 4):
            return False, "pocos_por_amostra deve ser 1, 2, 3 ou 4."

        targets, limiares = self._build_v2_payload()
        if not targets:
            return False, "Cadastre ao menos um alvo por poco."

        seen_targets: set[tuple[str, int]] = set()
        for item in targets:
            alvo = item["alvo"]
            filtro = item["filtro"]
            tipo = item["tipo"]
            poco = item["poco"]
            if not alvo or not filtro or not tipo:
                return False, "Alvo, filtro e tipo sao obrigatorios."
            if not is_supported_target_filter(filtro):
                return False, f"Filtro nao suportado: {filtro}."
            if not is_supported_target_type(tipo):
                return False, f"Tipo nao suportado: {tipo}."
            if poco < 1 or poco > pocos:
                return False, f"Poco fora do intervalo 1..{pocos}."
            key = (alvo.upper(), poco)
            if key in seen_targets:
                return False, "Duplicidade de alvo+poco."
            seen_targets.add(key)

        seen_limiares: set[tuple[str, int]] = set()
        for item in limiares:
            key = (item["alvo"].upper(), item["poco"])
            if key in seen_limiares:
                return False, "Duplicidade de limiar para alvo+poco."
            seen_limiares.add(key)
            ct_min = item["ct_minimo"]
            ct_det = item["ct_detectavel_limite"]
            ct_inc = item["ct_inconclusivo_limite"]
            if not (0 <= ct_min <= 45 and 0 <= ct_det <= 45 and 0 <= ct_inc <= 45):
                return False, "Limiar CT fora do intervalo 0..45."
            if not (ct_min <= ct_det <= ct_inc):
                return False, "Ordem invalida de limiares CT."

        if seen_targets != seen_limiares:
            return False, "Cada alvo+poco deve possuir limiares CT correspondentes."
        return True, "OK"

    def _derive_legacy_from_v2(
        self,
        targets_por_poco: list[dict[str, Any]],
        limiares: list[dict[str, Any]],
    ) -> dict[str, Any]:
        alvos: list[str] = []
        controls_cn: list[str] = []
        controls_cp: list[str] = []
        for item in targets_por_poco:
            alvo = str(item.get("alvo", "")).strip()
            tipo = normalize_target_type(item.get("tipo", ""))
            if alvo and alvo not in alvos:
                alvos.append(alvo)
            if tipo == "CONTROL_EXTERNAL" and alvo and alvo not in controls_cn:
                controls_cn.append(alvo)
            if is_control_internal_type(tipo) and alvo and alvo not in controls_cp:
                controls_cp.append(alvo)

        detect_values = [float(item["ct_detectavel_limite"]) for item in limiares]
        inconc_values = [float(item["ct_inconclusivo_limite"]) for item in limiares]
        min_values = [float(item["ct_minimo"]) for item in limiares]
        detect_min = min(detect_values) if detect_values else 35.0
        detect_max = max(detect_values) if detect_values else 35.0
        inconc_max = max(inconc_values) if inconc_values else 40.0
        rp_min = min(min_values) if min_values else 10.0

        return {
            "alvos": alvos,
            "mapa_alvos": {alvo: alvo for alvo in alvos},
            "faixas_ct": {
                "detect_max": detect_max,
                "inconc_min": min(45.0, detect_min + 0.01),
                "inconc_max": inconc_max,
                "rp_min": rp_min,
                "rp_max": detect_max,
            },
            "rps": controls_cp[:],
            "controles": {"cn": controls_cn, "cp": controls_cp},
        }

    def next_step(self) -> None:
        if self.current_step == 1:
            if not self.ent_name.get().strip() or not self.ent_id.get().strip():
                messagebox.showerror(
                    "Erro",
                    "Preencha nome e ID do exame.",
                    parent=self.dialog_parent,
                )
                return
            try:
                pocos = int(self.cmb_pocos.get())
            except Exception:
                pocos = 0
            if pocos not in (1, 2, 3, 4):
                messagebox.showerror("Erro", "Pocos por amostra deve ser 1..4.", parent=self.dialog_parent)
                return

            self.exam_data["display_name"] = self.ent_name.get().strip()
            self.exam_data["id"] = self.ent_id.get().strip()
            self.exam_data["version"] = self.ent_ver.get().strip() or "1.0"
            self.exam_data["pocos_por_amostra"] = pocos

            self.current_step = 2
            self.render_step_2()
            return

        if self.current_step == 2:
            if not self.temp_targets:
                messagebox.showerror("Erro", "Cadastre ao menos um alvo.", parent=self.dialog_parent)
                return
            self.exam_data["targets"] = list(self.temp_targets)
            self.current_step = 3
            self.render_step_3()
            return

        if self.current_step == 3:
            if not self._collect_ct_from_table():
                return
            ok, msg = self._validate_v2_payload()
            if not ok:
                messagebox.showerror("Erro", msg, parent=self.dialog_parent)
                return
            self.exam_data["ct_thresholds"] = list(self.temp_ct_thresholds)
            self.save_exam()

    def prev_step(self) -> None:
        if self.current_step == 2:
            self.current_step = 1
            self.render_step_1()
            return
        if self.current_step == 3:
            self._collect_ct_from_table()
            self.current_step = 2
            self.render_step_2()
            return

    def _save_exam_legacy(self) -> None:
        targets_configuration: dict[str, dict[str, str]] = {}
        for target in self.exam_data.get("targets", []):  # type: ignore[union-attr]
            if not isinstance(target, dict):
                continue
            name = str(target.get("name", "")).strip()
            if not name:
                continue
            poco = target.get("poco")
            key = f"{name}_P{poco}" if isinstance(poco, int) else name
            targets_configuration[key] = {
                "filter": str(target.get("filter", "")).strip(),
                "type": str(target.get("type", "")).strip(),
            }

        protocol_json = {
            "id": self.exam_data["id"],
            "display_name": self.exam_data["display_name"],
            "version": self.exam_data["version"],
            "targets_configuration": targets_configuration,
        }

        path = Path("banco_runtime/protocols/analysis_protocols.json")
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if path.exists():
                with path.open("r", encoding="utf-8") as handler:
                    data = json.load(handler)
            else:
                data = []

            data.append(protocol_json)
            with path.open("w", encoding="utf-8") as handler:
                json.dump(data, handler, indent=2, ensure_ascii=False)

            registrar_log(
                "ExamCreator",
                f"Exame criado com sucesso (legado): {self.exam_data['display_name']}",
                "INFO",
            )
            messagebox.showinfo(
                "Sucesso",
                f"Exame '{self.exam_data['display_name']}' criado com sucesso!",
                parent=self.dialog_parent,
            )
            self._close_page()
        except (OSError, json.JSONDecodeError) as exc:
            registrar_log("ExamCreator", f"Falha ao salvar exame: {exc}", "ERROR")
            messagebox.showerror(
                "Erro",
                f"Falha ao salvar: {exc}",
                parent=self.dialog_parent,
            )

    def _resolve_actor_context(self) -> tuple[str, str]:
        app_state = getattr(self.dialog_parent, "app_state", None)
        if app_state is None:
            app_state = getattr(getattr(self, "master", None), "app_state", None)
        actor_username = str(getattr(app_state, "usuario_logado", "") or "").strip()
        actor_access_level = str(getattr(app_state, "nivel_acesso", "") or "").strip()
        return actor_username, actor_access_level

    def _build_registry_exam_config(self) -> Any:
        from services.exam_registry import ExamConfig

        targets_por_poco, limiares = self._build_v2_payload()
        legacy = self._derive_legacy_from_v2(targets_por_poco, limiares)

        protocol_id = str(self.exam_data.get("id", "") or "").strip()
        display_name = str(self.exam_data.get("display_name", "") or "").strip()
        version = str(self.exam_data.get("version", "") or "").strip()
        pocos_por_amostra = int(self.exam_data.get("pocos_por_amostra", 1) or 1)

        return ExamConfig(
            nome_exame=display_name,
            slug=protocol_id,
            equipamento="7500",
            tipo_placa_analitica="96",
            esquema_agrupamento={1: "96->96", 2: "96->48", 3: "96->32", 4: "96->24"}.get(
                pocos_por_amostra, "96->96"
            ),
            kit_codigo="",
            alvos=legacy["alvos"],
            mapa_alvos=legacy["mapa_alvos"],
            faixas_ct=legacy["faixas_ct"],
            rps=legacy["rps"],
            export_fields=[],
            panel_tests_id=protocol_id,
            controles=legacy["controles"],
            comentarios="Cadastro via wizard V2 compat mode",
            versao_protocolo=version,
            pocos_por_amostra=pocos_por_amostra,
            targets_por_poco=targets_por_poco,
            limiares_ct_por_alvo_poco=limiares,
        )

    def _save_exam_via_registry(self) -> tuple[bool, str]:
        actor_username, actor_access_level = self._resolve_actor_context()
        try:
            from ui.modules.cadastros_diversos import RegistryExamEditor
            from services.core.config_loader import limpar_caches
        except Exception as exc:  # pragma: no cover
            msg = f"Registry indisponivel: {exc}"
            registrar_log("ExamCreator", msg, "ERROR")
            return False, msg

        try:
            cfg = self._build_registry_exam_config()
            editor = RegistryExamEditor(
                actor_username=actor_username,
                actor_access_level=actor_access_level,
            )
            ok, msg = editor.save_exam(cfg)
            if not ok:
                registrar_log("ExamCreator", f"Falha no save via registry: {msg}", "WARNING")
                return False, str(msg)
            editor.reload_registry()
            limpar_caches()
            registrar_log(
                "ExamCreator",
                f"Exame criado via registry: {self.exam_data.get('display_name', '')}",
                "INFO",
            )
            messagebox.showinfo(
                "Sucesso",
                f"Exame '{self.exam_data.get('display_name', '')}' criado com sucesso!",
                parent=self.dialog_parent,
            )
            self._close_page()
            return True, "OK"
        except Exception as exc:  # noqa: BLE001
            msg = f"Erro no save via registry: {exc}"
            registrar_log("ExamCreator", msg, "ERROR")
            return False, msg

    def save_exam(self) -> None:
        ok, msg = self._save_exam_via_registry()
        if ok:
            return
        messagebox.showerror(
            "Erro",
            (
                "Falha ao salvar exame via registry. "
                "O exame nao foi salvo. Detalhe: "
                f"{msg}"
            ),
            parent=self.dialog_parent,
        )


class ExamCreatorWizard(ctk.CTkToplevel):
    """Facade legacy para compatibilidade."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Criador de Novos Exames - IntegraGAL")
        try:
            self.state("zoomed")
        except Exception:
            self.geometry("1280x900")
        try:
            self.minsize(1100, 760)
        except Exception:
            pass
        if hasattr(self, "transient"):
            self.transient(parent)
        if hasattr(self, "grab_set"):
            self.grab_set()

        page = ExamCreatorWizardPage(self, on_close=self.destroy, dialog_parent=self)
        page.pack(expand=True, fill="both", padx=10, pady=10)
        self.page = page


def create_exam_creator_wizard_page(parent: ctk.CTkFrame, main_window) -> ctk.CTkFrame:
    """Cria o wizard de exames em modo pagina no ModuleHost."""

    def _go_back() -> None:
        nav = getattr(main_window, "navigation_manager", None)
        if nav and hasattr(nav, "navigate_to"):
            nav.navigate_to("main_menu")

    page = ExamCreatorWizardPage(parent, on_close=_go_back, dialog_parent=main_window)
    page.pack(expand=True, fill="both")
    return page
