"""

Módulo de Cadastros Diversos para o IntegraGAL.



Este módulo fornece uma janela unificada para manutenção de:

- Exames (banco/exames_config.csv)

- Equipamentos (banco/equipamentos.csv)

- Placas (banco/placas.csv)

- Regras (banco/regras.csv)



O objetivo é permitir inclusão, edição e exclusão de registros

em arquivos CSV simples, mantendo compatibilidade com a

configuração já existente de exames (exames_config.csv).

"""



from __future__ import annotations



import csv

import os

from dataclasses import dataclass

from typing import Dict, List, Optional, Callable



import tkinter as tk

from tkinter import messagebox, ttk



import customtkinter as ctk

from ui.theme import Theme



from services.system_paths import BASE_DIR

from services.cadastros_diversos import get_csv_configs, load_csv, save_csv, CsvConfig
from services.core.config_service import config_service
from services.exam_domain_contracts import (
    is_supported_target_filter,
    is_supported_target_type,
    normalize_target_filter,
    normalize_target_type,
)
from application.access_control import (
    AuthorizationDeniedError,
    ensure_operation_allowed,
    normalize_access_level,
)
from application.equipment_profile_service import EquipmentProfileService

from utils.logger import registrar_log
from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, call_with_retry, open_with_retry, path_exists_with_retry











class CadastrosDiversosWindow:

    """Janela principal para cadastros de exames, equipamentos, placas e regras."""



    def __init__(self, main_window: ctk.CTk | tk.Tk) -> None:

        self.main_window = main_window



        # Configurações de arquivos

        self.csv_configs: Dict[str, CsvConfig] = self._build_csv_configs()



        # Estado de seleção por aba

        self.current_exam_id: Optional[int] = None

        self.current_equipment_id: Optional[int] = None

        self.current_plate_id: Optional[int] = None

        self.current_rule_id: Optional[int] = None

        self.current_exam_slug: Optional[str] = None  # â† Para aba Registry



        # Criação da janela

        self.window = tk.Toplevel(self.main_window)

        self.window.title("Cadastros Diversos")

        self.window.geometry("1100x700")

        self.window.transient(self.main_window)

        self.window.grab_set()



        # Containers principais

        self._build_ui()

    def _resolve_actor_context(self) -> tuple[str, str]:
        """Resolve usuario/nivel correntes a partir do app_state da janela principal."""
        app_state = getattr(self.main_window, "app_state", None)
        username = str(getattr(app_state, "usuario_logado", "") or "").strip()
        level = normalize_access_level(getattr(app_state, "nivel_acesso", ""))
        return username, level

    def _is_operation_allowed(
        self,
        *,
        operation: str,
        action_label: str,
        notify_ui: bool = True,
    ) -> bool:
        """Valida permissao de escrita administrativa na camada de servico/UI."""
        username, level = self._resolve_actor_context()
        try:
            ensure_operation_allowed(operation, level, actor_username=username)
            return True
        except AuthorizationDeniedError as exc:
            registrar_log(
                "CadastrosDiversos",
                f"{exc} acao='{action_label}'.",
                "WARNING",
            )
            if notify_ui:
                messagebox.showwarning(
                    "Acesso negado",
                    "O seu perfil não possui permissão para esta ação.",
                    parent=self.window,
                )
            return False



    # ------------------------------------------------------------------

    # Configuração de arquivos CSV

    # ------------------------------------------------------------------

    def _build_csv_configs(self) -> Dict[str, CsvConfig]:
        return get_csv_configs()

    def _ensure_csv(self, key: str) -> None:
        pass

    def _load_csv(self, key: str) -> List[Dict[str, str]]:
        return load_csv(self.csv_configs[key])

    def _save_csv(self, key: str, rows: List[Dict[str, str]]) -> None:
        if not self._is_operation_allowed(
            operation="admin.catalog.write",
            action_label=f"salvar cadastro '{key}'",
        ):
            return
        save_csv(self.csv_configs[key], rows)

    def _build_ui(self) -> None:

        main_frame = ctk.CTkFrame(self.window)

        main_frame.pack(expand=True, fill="both", padx=10, pady=10)



        title = ctk.CTkLabel(

            main_frame,

            text="Cadastros Diversos",

            font=ctk.CTkFont(size=22, weight="bold"),

        )

        title.pack(pady=(0, 10))



        subtitle = ctk.CTkLabel(

            main_frame,

            text=(

                "Módulo para manutenção de exames, equipamentos, placas e regras.\n"

                "As alterações são persistidas em arquivos CSV na pasta 'banco_runtime/'."

            ),

            font=ctk.CTkFont(size=13),

        )

        subtitle.pack(pady=(0, 15))



        self.tabview = ctk.CTkTabview(main_frame)

        self.tabview.pack(expand=True, fill="both")



        self.tab_exames = self.tabview.add("Exames")

        self.tab_equip = self.tabview.add("Equipamentos")

        self.tab_placas = self.tabview.add("Placas")

        self.tab_regras = self.tabview.add("Regras")

        self.tab_exames_registry = self.tabview.add("Exames (Registry)")  # â† NEW



        self._build_tab_exames_registry()  # â† Criar primeiro para evitar AttributeError

        self._build_tab_exames()

        self._build_tab_equipamentos()

        self._build_tab_placas()

        self._build_tab_regras()



    # ----------------------------- EXAMES -----------------------------

    def _build_tab_exames(self) -> None:

        frame = ctk.CTkFrame(self.tab_exames)

        frame.pack(expand=True, fill="both", padx=10, pady=10)

        frame.grid_rowconfigure(1, weight=1)

        frame.grid_columnconfigure(0, weight=1)

        frame.grid_columnconfigure(1, weight=1)



        # Tabela

        table_frame = ctk.CTkFrame(frame)

        table_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10))



        cols = self.csv_configs["exames"].headers

        self.tree_exames = ttk.Treeview(

            table_frame,

            columns=cols,

            show="headings",

            height=15,

        )

        for c in cols:

            self.tree_exames.heading(c, text=c)

            self.tree_exames.column(c, width=140, anchor="w")

        self.tree_exames.pack(expand=True, fill="both", padx=5, pady=5)

        self.tree_exames.bind("<<TreeviewSelect>>", self._on_select_exam)



        btn_frame = ctk.CTkFrame(table_frame)

        btn_frame.pack(fill="x", padx=5, pady=(0, 5))



        ctk.CTkButton(

            btn_frame,

            text="Novo",

            command=self._novo_exame,

            width=80,

        ).pack(side="left", padx=5)

        ctk.CTkButton(

            btn_frame,

            text="Salvar",

            command=self._salvar_exame,

            width=80,

        ).pack(side="left", padx=5)

        ctk.CTkButton(

            btn_frame,

            text="Excluir",

            command=self._excluir_exame,

            width=80,

        ).pack(side="left", padx=5)

        ctk.CTkButton(

            btn_frame,

            text="Recarregar",

            command=self._carregar_exames,

            width=100,

        ).pack(side="right", padx=5)



        # Formulário

        form_frame = ctk.CTkFrame(frame)

        form_frame.grid(row=0, column=1, sticky="nsew")



        self.entry_exame = ctk.CTkEntry(form_frame, placeholder_text="Nome do exame")

        self.entry_exame.pack(fill="x", padx=5, pady=5)



        self.entry_modulo = ctk.CTkEntry(

            form_frame, placeholder_text="Módulo de análise (ex.: analise.vr1e2_biomanguinhos_7500.analisar_placa...)"

        )

        self.entry_modulo.pack(fill="x", padx=5, pady=5)



        self.entry_tipo_placa = ctk.CTkEntry(

            form_frame, placeholder_text="Tipo de placa (ex.: 48, 96)"

        )

        self.entry_tipo_placa.pack(fill="x", padx=5, pady=5)



        self.entry_numero_kit = ctk.CTkEntry(

            form_frame, placeholder_text="Número/ID do kit"

        )

        self.entry_numero_kit.pack(fill="x", padx=5, pady=5)



        self.entry_equipamento_exame = ctk.CTkEntry(

            form_frame, placeholder_text="Equipamento associado"

        )

        self.entry_equipamento_exame.pack(fill="x", padx=5, pady=5)



        self._carregar_exames()



    def _carregar_exames(self) -> None:

        rows = self._load_csv("exames")

        # limpar

        for item in self.tree_exames.get_children():

            self.tree_exames.delete(item)

        for idx, r in enumerate(rows):

            values = [

                r.get("exame", ""),

                r.get("modulo_analise", ""),

                r.get("tipo_placa", ""),

                r.get("numero_kit", ""),

                r.get("equipamento", ""),

            ]

            self.tree_exames.insert("", "end", iid=str(idx), values=values)



    def _on_select_exam(self, event=None) -> None:

        sel = self.tree_exames.selection()

        if not sel:

            return

        iid = sel[0]

        self.current_exam_id = int(iid)

        vals = self.tree_exames.item(iid, "values")

        if not vals:

            return

        self.entry_exame.delete(0, "end")

        self.entry_exame.insert(0, vals[0])

        self.entry_modulo.delete(0, "end")

        self.entry_modulo.insert(0, vals[1])

        self.entry_tipo_placa.delete(0, "end")

        self.entry_tipo_placa.insert(0, vals[2])

        self.entry_numero_kit.delete(0, "end")

        self.entry_numero_kit.insert(0, vals[3])

        self.entry_equipamento_exame.delete(0, "end")

        self.entry_equipamento_exame.insert(0, vals[4])



    def _novo_exame(self) -> None:

        self.current_exam_id = None

        for entry in [

            self.entry_exame,

            self.entry_modulo,

            self.entry_tipo_placa,

            self.entry_numero_kit,

            self.entry_equipamento_exame,

        ]:

            entry.delete(0, "end")



    def _salvar_exame(self) -> None:

        rows = self._load_csv("exames")

        dados = {

            "exame": self.entry_exame.get().strip(),

            "modulo_analise": self.entry_modulo.get().strip(),

            "tipo_placa": self.entry_tipo_placa.get().strip(),

            "numero_kit": self.entry_numero_kit.get().strip(),

            "equipamento": self.entry_equipamento_exame.get().strip(),

        }

        if not dados["exame"]:

            messagebox.showwarning(

                "Aviso", "O campo 'exame' é obrigatório.", parent=self.window

            )

            return



        if self.current_exam_id is None:

            rows.append(dados)

        else:

            if 0 <= self.current_exam_id < len(rows):

                rows[self.current_exam_id] = dados

            else:

                rows.append(dados)



        self._save_csv("exames", rows)

        self._carregar_exames()



    def _excluir_exame(self) -> None:

        if self.current_exam_id is None:

            messagebox.showinfo(

                "Informação",

                "Selecione um exame para excluir.",

                parent=self.window,

            )

            return



        if not messagebox.askyesno(

            "Confirmação",

            "Deseja realmente excluir o exame selecionado?",

            parent=self.window,

        ):

            return



        rows = self._load_csv("exames")

        if 0 <= self.current_exam_id < len(rows):

            rows.pop(self.current_exam_id)

            self._save_csv("exames", rows)

            self._carregar_exames()

            self._novo_exame()



    # -------------------------- EQUIPAMENTOS --------------------------

    def _build_tab_equipamentos(self) -> None:

        frame = ctk.CTkFrame(self.tab_equip)

        frame.pack(expand=True, fill="both", padx=10, pady=10)

        frame.grid_rowconfigure(1, weight=1)

        frame.grid_columnconfigure(0, weight=1)

        frame.grid_columnconfigure(1, weight=1)



        table_frame = ctk.CTkFrame(frame)

        table_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10))



        cols = self.csv_configs["equipamentos"].headers

        self.tree_equip = ttk.Treeview(

            table_frame,

            columns=cols,

            show="headings",

            height=15,

        )

        for c in cols:

            self.tree_equip.heading(c, text=c)

            self.tree_equip.column(c, width=160, anchor="w")

        self.tree_equip.pack(expand=True, fill="both", padx=5, pady=5)

        self.tree_equip.bind("<<TreeviewSelect>>", self._on_select_equip)



        btn_frame = ctk.CTkFrame(table_frame)

        btn_frame.pack(fill="x", padx=5, pady=(0, 5))



        ctk.CTkButton(

            btn_frame,

            text="Novo",

            command=self._novo_equip,

            width=80,

        ).pack(side="left", padx=5)

        ctk.CTkButton(

            btn_frame,

            text="Salvar",

            command=self._salvar_equip,

            width=80,

        ).pack(side="left", padx=5)

        ctk.CTkButton(

            btn_frame,

            text="Excluir",

            command=self._excluir_equip,

            width=80,

        ).pack(side="left", padx=5)

        ctk.CTkButton(

            btn_frame,

            text="Recarregar",

            command=self._carregar_equip,

            width=100,

        ).pack(side="right", padx=5)



        form_frame = ctk.CTkFrame(frame)
        form_frame.grid(row=0, column=1, sticky="nsew")

        # Botão de teste de detecção (topo, fora do scroll)
        btn_test_frame = ctk.CTkFrame(form_frame)
        btn_test_frame.pack(fill="x", padx=5, pady=(5, 0))
        ctk.CTkButton(
            btn_test_frame,
            text="Testar com arquivo...",
            command=self._testar_deteccao_arquivo,
            width=180,
        ).pack(side="left", padx=5, pady=4)

        # Scrollable para todos os campos
        scroll = ctk.CTkScrollableFrame(form_frame, label_text="Perfil do Equipamento")
        scroll.pack(expand=True, fill="both", padx=5, pady=5)

        def _lbl(parent, text):
            ctk.CTkLabel(parent, text=text, anchor="w").pack(fill="x", padx=5, pady=(6, 0))

        # --- Campos básicos ---
        _lbl(scroll, "Nome (display_name)")
        self.entry_equip_nome = ctk.CTkEntry(scroll, placeholder_text="Nome do equipamento")
        self.entry_equip_nome.pack(fill="x", padx=5, pady=2)

        _lbl(scroll, "Modelo")
        self.entry_equip_modelo = ctk.CTkEntry(scroll, placeholder_text="Modelo")
        self.entry_equip_modelo.pack(fill="x", padx=5, pady=2)

        _lbl(scroll, "Fabricante")
        self.entry_equip_fabricante = ctk.CTkEntry(scroll, placeholder_text="Fabricante")
        self.entry_equip_fabricante.pack(fill="x", padx=5, pady=2)

        _lbl(scroll, "Aliases (separados por vírgula)")
        self.entry_equip_aliases = ctk.CTkEntry(scroll, placeholder_text="Ex: 7500 Real-Time, Applied Biosystems 7500")
        self.entry_equip_aliases.pack(fill="x", padx=5, pady=2)

        _lbl(scroll, "Motivo da alteração")
        self.entry_equip_obs = ctk.CTkEntry(scroll, placeholder_text="Observações / motivo")
        self.entry_equip_obs.pack(fill="x", padx=5, pady=2)

        active_row = ctk.CTkFrame(scroll, fg_color="transparent")
        active_row.pack(fill="x", padx=5, pady=4)
        ctk.CTkLabel(active_row, text="Ativo").pack(side="left")
        self._equip_active_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(active_row, text="", variable=self._equip_active_var, onvalue=True, offvalue=False).pack(side="left", padx=8)

        # --- Assinatura para detecção ---
        ctk.CTkLabel(scroll, text="── Assinatura de Detecção ──", anchor="w", font=("", 11, "bold")).pack(fill="x", padx=5, pady=(10, 0))

        _lbl(scroll, "Colunas obrigatórias (signature.contains_columns — separar por vírgula)")
        self.entry_sig_columns = ctk.CTkEntry(scroll, placeholder_text="Ex: Well, Sample Name, Target Name, Cт")
        self.entry_sig_columns.pack(fill="x", padx=5, pady=2)

        _lbl(scroll, "Tokens identificadores (signature.contains_any_token — separar por vírgula)")
        self.entry_sig_tokens = ctk.CTkEntry(scroll, placeholder_text="Ex: 7500, Applied Biosystems")
        self.entry_sig_tokens.pack(fill="x", padx=5, pady=2)

        _lbl(scroll, "Confiança mínima (confidence_threshold, 0–100)")
        self.entry_confidence = ctk.CTkEntry(scroll, placeholder_text="Ex: 70")
        self.entry_confidence.pack(fill="x", padx=5, pady=2)

        # --- Mapeamento de colunas ---
        ctk.CTkLabel(scroll, text="── Mapeamento de Colunas ──", anchor="w", font=("", 11, "bold")).pack(fill="x", padx=5, pady=(10, 0))

        for attr, label, ph in [
            ("entry_col_well",   "Coluna Well (column_mapping.well)",   "Ex: Well"),
            ("entry_col_sample", "Coluna Sample (column_mapping.sample)", "Ex: Sample Name"),
            ("entry_col_target", "Coluna Target (column_mapping.target)", "Ex: Target Name"),
            ("entry_col_ct",     "Coluna CT (column_mapping.ct)",        "Ex: Cт"),
        ]:
            _lbl(scroll, label)
            entry = ctk.CTkEntry(scroll, placeholder_text=ph)
            entry.pack(fill="x", padx=5, pady=2)
            setattr(self, attr, entry)

        # --- Estratégia de extração ---
        ctk.CTkLabel(scroll, text="── Extração ──", anchor="w", font=("", 11, "bold")).pack(fill="x", padx=5, pady=(10, 0))

        _lbl(scroll, "Estratégia de extração (extractor_strategy)")
        self.combo_extractor = ctk.CTkComboBox(
            scroll,
            values=["indexed_table", "quantstudio_table", "legacy"],
            state="readonly",
        )
        self.combo_extractor.set("indexed_table")
        self.combo_extractor.pack(fill="x", padx=5, pady=2)

        _lbl(scroll, "Mínimo de linhas de dados (validation_rules.min_rows)")
        self.entry_min_rows = ctk.CTkEntry(scroll, placeholder_text="Ex: 8")
        self.entry_min_rows.pack(fill="x", padx=5, pady=2)

        # --- Política de CT ---
        ctk.CTkLabel(scroll, text="── Política de CT ──", anchor="w", font=("", 11, "bold")).pack(fill="x", padx=5, pady=(10, 0))

        _lbl(scroll, "Marcadores nulos (ct_policy.null_markers — separar por vírgula)")
        self.entry_ct_nullmarkers = ctk.CTkEntry(scroll, placeholder_text="Ex: Undetermined, N/A, No Amp, -")
        self.entry_ct_nullmarkers.pack(fill="x", padx=5, pady=2)

        _lbl(scroll, "Aliases de CT (ct_policy.aliases — separar por vírgula)")
        self.entry_ct_aliases = ctk.CTkEntry(scroll, placeholder_text="Ex: Cт, Ct, Cq, C(t)")
        self.entry_ct_aliases.pack(fill="x", padx=5, pady=2)

        _lbl(scroll, "Blocklist CT (ct_policy.blocklist — separar por vírgula)")
        self.entry_ct_blocklist = ctk.CTkEntry(scroll, placeholder_text="Ex: Ct Mean, Cq Mean, Cq SD")
        self.entry_ct_blocklist.pack(fill="x", padx=5, pady=2)

        _lbl(scroll, "Separador decimal (ct_policy.decimal_separator)")
        self.entry_ct_decimal = ctk.CTkEntry(scroll, placeholder_text="Ex: ,")
        self.entry_ct_decimal.pack(fill="x", padx=5, pady=2)

        # --- Política de Well ---
        ctk.CTkLabel(scroll, text="── Política de Well ──", anchor="w", font=("", 11, "bold")).pack(fill="x", padx=5, pady=(10, 0))

        _lbl(scroll, "Formato de entrada (well_policy.input_format)")
        self.entry_well_input = ctk.CTkEntry(scroll, placeholder_text="Ex: A1")
        self.entry_well_input.pack(fill="x", padx=5, pady=2)

        _lbl(scroll, "Formato normalizado (well_policy.normalized_format)")
        self.entry_well_norm = ctk.CTkEntry(scroll, placeholder_text="Ex: A01")
        self.entry_well_norm.pack(fill="x", padx=5, pady=2)

        # --- Política de Planilha e Linhas ---
        ctk.CTkLabel(scroll, text="── Planilha & Linhas ──", anchor="w", font=("", 11, "bold")).pack(fill="x", padx=5, pady=(10, 0))

        _lbl(scroll, "Aba preferida (sheet_policy.preferred_sheet)")
        self.entry_sheet_preferred = ctk.CTkEntry(scroll, placeholder_text="Ex: Results  (vazio = primeira aba)")
        self.entry_sheet_preferred.pack(fill="x", padx=5, pady=2)

        _lbl(scroll, "Abas ignoradas (sheet_policy.skip_keywords — separar por vírgula)")
        self.entry_sheet_skip = ctk.CTkEntry(scroll, placeholder_text="Ex: extracao, extraction")
        self.entry_sheet_skip.pack(fill="x", padx=5, pady=2)

        _lbl(scroll, "Máximo de linhas para buscar header (row_policy.header_search_max_rows)")
        self.entry_row_max_header = ctk.CTkEntry(scroll, placeholder_text="Ex: 30")
        self.entry_row_max_header.pack(fill="x", padx=5, pady=2)

        _lbl(scroll, "Offset início dos dados após header (row_policy.data_start_offset)")
        self.entry_row_offset = ctk.CTkEntry(scroll, placeholder_text="Ex: 1")
        self.entry_row_offset.pack(fill="x", padx=5, pady=2)

        # --- Regras de validação (complemento) ---
        ctk.CTkLabel(scroll, text="── Validação (complemento) ──", anchor="w", font=("", 11, "bold")).pack(fill="x", padx=5, pady=(10, 0))

        _lbl(scroll, "Colunas obrigatórias (validation_rules.required_columns — separar por vírgula)")
        self.entry_required_columns = ctk.CTkEntry(scroll, placeholder_text="Ex: well, sample, target, ct")
        self.entry_required_columns.pack(fill="x", padx=5, pady=2)

        self._carregar_equip()



    def _carregar_equip(self) -> None:
        service = EquipmentProfileService()
        profiles = service.list_profiles()
        self._equip_profile_keys = [str(profile.get("equipment_id", "")).strip() for profile in profiles]

        rows = []
        for profile in profiles:
            rows.append(
                {
                    "nome": str(profile.get("display_name", "")).strip(),
                    "modelo": str(profile.get("modelo", "")).strip(),
                    "fabricante": str(profile.get("fabricante", "")).strip(),
                    "observacoes": str((profile.get("audit") or {}).get("change_reason", "")).strip(),
                }
            )

        for item in self.tree_equip.get_children():
            self.tree_equip.delete(item)

        for idx, r in enumerate(rows):
            self.tree_equip.insert(
                "", "end", iid=str(idx), values=[
                    r.get("nome", ""),
                    r.get("modelo", ""),
                    r.get("fabricante", ""),
                    r.get("observacoes", ""),
                ]
            )



    def _on_select_equip(self, event=None) -> None:
        sel = self.tree_equip.selection()
        if not sel:
            return
        iid = sel[0]
        self.current_equipment_id = int(iid)

        equipment_id = ""
        if hasattr(self, "_equip_profile_keys") and 0 <= self.current_equipment_id < len(self._equip_profile_keys):
            equipment_id = self._equip_profile_keys[self.current_equipment_id]

        profile = {}
        if equipment_id:
            try:
                svc = EquipmentProfileService()
                profile = svc.resolve_profile(equipment_id) or {}
                if not profile:
                    profile = next((p for p in svc.list_profiles() if str(p.get("equipment_id", "")).strip() == equipment_id), {})
            except Exception:
                pass

        def _set(entry, value):
            entry.delete(0, "end")
            entry.insert(0, str(value or ""))

        _set(self.entry_equip_nome, profile.get("display_name", ""))
        _set(self.entry_equip_modelo, profile.get("modelo", ""))
        _set(self.entry_equip_fabricante, profile.get("fabricante", ""))
        _set(self.entry_equip_aliases, ", ".join(profile.get("aliases", [])) if isinstance(profile.get("aliases"), list) else "")
        _set(self.entry_equip_obs, (profile.get("audit") or {}).get("change_reason", ""))

        self._equip_active_var.set(bool(profile.get("active", True)))

        sig = profile.get("signature") or {}
        _set(self.entry_sig_columns, ", ".join(sig.get("contains_columns", [])) if isinstance(sig.get("contains_columns"), list) else "")
        _set(self.entry_sig_tokens, ", ".join(sig.get("contains_any_token", [])) if isinstance(sig.get("contains_any_token"), list) else "")
        _set(self.entry_confidence, str(profile.get("confidence_threshold", 70)))

        cm = profile.get("column_mapping") or {}
        _set(self.entry_col_well, cm.get("well", "Well"))
        _set(self.entry_col_sample, cm.get("sample", "Sample Name"))
        _set(self.entry_col_target, cm.get("target", "Target Name"))
        _set(self.entry_col_ct, cm.get("ct", "Ct"))

        self.combo_extractor.set(str(profile.get("extractor_strategy", "indexed_table")))

        vr = profile.get("validation_rules") or {}
        _set(self.entry_min_rows, str(vr.get("min_rows", 8)))

        ct_pol = profile.get("ct_policy") or {}
        null_markers = ct_pol.get("null_markers", [])
        _set(self.entry_ct_nullmarkers, ", ".join(null_markers) if isinstance(null_markers, list) else str(null_markers))
        ct_aliases = ct_pol.get("aliases", [])
        _set(self.entry_ct_aliases, ", ".join(ct_aliases) if isinstance(ct_aliases, list) else str(ct_aliases))
        ct_blocklist = ct_pol.get("blocklist", [])
        _set(self.entry_ct_blocklist, ", ".join(ct_blocklist) if isinstance(ct_blocklist, list) else str(ct_blocklist))
        _set(self.entry_ct_decimal, str(ct_pol.get("decimal_separator", ",")))

        wp = profile.get("well_policy") or {}
        _set(self.entry_well_input, wp.get("input_format", "A1"))
        _set(self.entry_well_norm, wp.get("normalized_format", "A01"))

        sp = profile.get("sheet_policy") or {}
        _set(self.entry_sheet_preferred, sp.get("preferred_sheet", ""))
        skip_kw = sp.get("skip_keywords", [])
        _set(self.entry_sheet_skip, ", ".join(skip_kw) if isinstance(skip_kw, list) else str(skip_kw))

        rp = profile.get("row_policy") or {}
        _set(self.entry_row_max_header, str(rp.get("header_search_max_rows", 30)))
        _set(self.entry_row_offset, str(rp.get("data_start_offset", 1)))

        req_cols = (profile.get("validation_rules") or {}).get("required_columns", [])
        _set(self.entry_required_columns, ", ".join(req_cols) if isinstance(req_cols, list) else str(req_cols))



    def _novo_equip(self) -> None:
        self.current_equipment_id = None
        for entry in [
            self.entry_equip_nome,
            self.entry_equip_modelo,
            self.entry_equip_fabricante,
            self.entry_equip_aliases,
            self.entry_equip_obs,
            self.entry_sig_columns,
            self.entry_sig_tokens,
            self.entry_confidence,
            self.entry_col_well,
            self.entry_col_sample,
            self.entry_col_target,
            self.entry_col_ct,
            self.entry_min_rows,
            self.entry_ct_nullmarkers,
            self.entry_ct_aliases,
            self.entry_ct_blocklist,
            self.entry_ct_decimal,
            self.entry_well_input,
            self.entry_well_norm,
            self.entry_sheet_preferred,
            self.entry_sheet_skip,
            self.entry_row_max_header,
            self.entry_row_offset,
            self.entry_required_columns,
        ]:
            entry.delete(0, "end")
        self._equip_active_var.set(True)
        self.combo_extractor.set("indexed_table")
        self.entry_confidence.insert(0, "70")
        self.entry_min_rows.insert(0, "8")
        self.entry_well_input.insert(0, "A1")
        self.entry_well_norm.insert(0, "A01")
        self.entry_ct_decimal.insert(0, ",")
        self.entry_row_max_header.insert(0, "30")
        self.entry_row_offset.insert(0, "1")



    def _salvar_equip(self) -> None:
        if not self._is_operation_allowed(
            operation="admin.catalog.write",
            action_label="salvar perfil tecnico de equipamento",
        ):
            return

        def _parse_list(text: str) -> list:
            return [t.strip() for t in text.split(",") if t.strip()]

        display_name = self.entry_equip_nome.get().strip()
        if not display_name:
            messagebox.showwarning("Aviso", "O campo 'Nome' do equipamento é obrigatório.", parent=self.window)
            return

        try:
            confidence = float(self.entry_confidence.get().strip() or "70")
        except ValueError:
            messagebox.showwarning("Aviso", "Confiança mínima deve ser um número (ex: 70).", parent=self.window)
            return

        try:
            min_rows = int(self.entry_min_rows.get().strip() or "8")
        except ValueError:
            messagebox.showwarning("Aviso", "Mínimo de linhas deve ser um número inteiro.", parent=self.window)
            return

        service = EquipmentProfileService()
        actor_username, actor_level = self._resolve_actor_context()

        equipment_id = ""
        if self.current_equipment_id is not None and hasattr(self, "_equip_profile_keys"):
            if 0 <= self.current_equipment_id < len(self._equip_profile_keys):
                equipment_id = self._equip_profile_keys[self.current_equipment_id]
        if not equipment_id:
            equipment_id = display_name.lower().replace(" ", "_").replace("-", "_")

        existing = {}
        try:
            existing = service.resolve_profile(equipment_id) or {}
            if not existing:
                existing = next((p for p in service.list_profiles() if str(p.get("equipment_id", "")).strip() == equipment_id), {})
        except Exception:
            pass

        aliases_raw = self.entry_equip_aliases.get().strip()
        aliases = _parse_list(aliases_raw) if aliases_raw else list(existing.get("aliases", [display_name]))

        sig_columns = _parse_list(self.entry_sig_columns.get())
        sig_tokens = _parse_list(self.entry_sig_tokens.get())
        if not sig_columns:
            sig_columns = (existing.get("signature") or {}).get("contains_columns", [])

        existing_ct = existing.get("ct_policy") or {}

        null_markers_raw = self.entry_ct_nullmarkers.get().strip()
        null_markers = _parse_list(null_markers_raw) if null_markers_raw else existing_ct.get("null_markers", ["Undetermined", "N/A", "No Amp", "-"])

        ct_aliases_raw = self.entry_ct_aliases.get().strip()
        ct_aliases = _parse_list(ct_aliases_raw) if ct_aliases_raw else existing_ct.get("aliases", ["Ct", "Cq", "C(t)"])

        ct_blocklist_raw = self.entry_ct_blocklist.get().strip()
        ct_blocklist = _parse_list(ct_blocklist_raw) if ct_blocklist_raw else existing_ct.get("blocklist", ["Ct Mean", "Cq Mean"])

        ct_decimal = self.entry_ct_decimal.get().strip() or existing_ct.get("decimal_separator", ",")

        existing_sp = existing.get("sheet_policy") or {}
        sheet_preferred = self.entry_sheet_preferred.get().strip()
        sheet_skip_raw = self.entry_sheet_skip.get().strip()
        sheet_skip = _parse_list(sheet_skip_raw) if sheet_skip_raw else existing_sp.get("skip_keywords", ["extracao", "extraction"])

        existing_rp = existing.get("row_policy") or {}
        try:
            row_max_header = int(self.entry_row_max_header.get().strip() or "30")
        except ValueError:
            row_max_header = existing_rp.get("header_search_max_rows", 30)
        try:
            row_offset = int(self.entry_row_offset.get().strip() or "1")
        except ValueError:
            row_offset = existing_rp.get("data_start_offset", 1)

        req_cols_raw = self.entry_required_columns.get().strip()
        req_cols = _parse_list(req_cols_raw) if req_cols_raw else (existing.get("validation_rules") or {}).get("required_columns", ["well", "sample", "target", "ct"])

        profile = {
            "equipment_id": equipment_id,
            "display_name": display_name,
            "aliases": aliases,
            "active": bool(self._equip_active_var.get()),
            "contract_version": str(existing.get("contract_version", "1.0.0")),
            "fabricante": self.entry_equip_fabricante.get().strip(),
            "modelo": self.entry_equip_modelo.get().strip(),
            "file_type": existing.get("file_type", ["xlsx", "xls", "xlsm"]),
            "signature": {
                "contains_columns": sig_columns,
                "contains_any_token": sig_tokens if sig_tokens else (existing.get("signature") or {}).get("contains_any_token", [display_name]),
            },
            "sheet_policy": {
                "preferred_sheet": sheet_preferred,
                "skip_keywords": sheet_skip,
            },
            "row_policy": {
                "header_search_max_rows": row_max_header,
                "data_start_offset": row_offset,
            },
            "column_mapping": {
                "well": self.entry_col_well.get().strip() or "Well",
                "sample": self.entry_col_sample.get().strip() or "Sample Name",
                "target": self.entry_col_target.get().strip() or "Target Name",
                "ct": self.entry_col_ct.get().strip() or "Ct",
            },
            "ct_policy": {
                "aliases": ct_aliases,
                "blocklist": ct_blocklist,
                "null_markers": null_markers,
                "decimal_separator": ct_decimal,
            },
            "well_policy": {
                "input_format": self.entry_well_input.get().strip() or "A1",
                "normalized_format": self.entry_well_norm.get().strip() or "A01",
            },
            "extractor_strategy": self.combo_extractor.get() or "indexed_table",
            "confidence_threshold": confidence,
            "validation_rules": {
                "required_columns": req_cols,
                "min_rows": min_rows,
            },
            "audit": existing.get("audit", {}),
        }

        change_reason = self.entry_equip_obs.get().strip() or "atualizacao via UI"
        try:
            service.save_profile(
                profile=profile,
                actor_username=actor_username,
                actor_access_level=actor_level,
                change_reason=change_reason,
            )
        except AuthorizationDeniedError:
            messagebox.showwarning(
                "Acesso negado",
                "Somente perfis ADMIN ou MASTER podem salvar cadastro técnico de equipamento.",
                parent=self.window,
            )
            return
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao salvar perfil técnico do equipamento:\n{exc}", parent=self.window)
            return

        messagebox.showinfo("Salvo", f"Perfil '{display_name}' salvo com sucesso.", parent=self.window)
        self._carregar_equip()



    def _excluir_equip(self) -> None:

        if self.current_equipment_id is None:

            messagebox.showinfo(

                "Informação",

                "Selecione um equipamento para excluir.",

                parent=self.window,

            )

            return



        if not messagebox.askyesno(

            "Confirmação",

            "Deseja realmente excluir o equipamento selecionado?",

            parent=self.window,

        ):

            return



        if not self._is_operation_allowed(
            operation="admin.catalog.write",
            action_label="inativar perfil tecnico de equipamento",
        ):
            return
        if not hasattr(self, "_equip_profile_keys"):
            return
        if not (0 <= self.current_equipment_id < len(self._equip_profile_keys)):
            return

        service = EquipmentProfileService()
        equipment_id = self._equip_profile_keys[self.current_equipment_id]
        profile = service.resolve_profile(equipment_id)
        if not profile:
            messagebox.showwarning(
                "Aviso",
                f"Perfil tecnico nao encontrado para '{equipment_id}'.",
                parent=self.window,
            )
            return

        actor_username, actor_level = self._resolve_actor_context()
        profile["active"] = False
        try:
            service.save_profile(
                profile=profile,
                actor_username=actor_username,
                actor_access_level=actor_level,
                change_reason="inativado via UI",
            )
        except Exception as exc:
            messagebox.showerror(
                "Erro",
                f"Falha ao inativar perfil tecnico:\n{exc}",
                parent=self.window,
            )
            return

        self._carregar_equip()
        self._novo_equip()

    def _testar_deteccao_arquivo(self) -> None:
        """T25: dry-run de detecção — detecta equipamento a partir de arquivo sem salvar."""
        from pathlib import Path
        from tkinter import filedialog

        filepath = filedialog.askopenfilename(
            title="Selecione arquivo para testar detecção",
            filetypes=[("Arquivos PCR", "*.xlsx *.xls *.xlsm"), ("Todos", "*.*")],
            parent=self.window,
        )
        if not filepath:
            return

        service = EquipmentProfileService()
        try:
            result = service.detect_equipment(Path(filepath))
        except Exception as exc:
            messagebox.showerror(
                "Resultado da Detecção",
                f"Falha na detecção:\n{exc}",
                parent=self.window,
            )
            return

        equip = result.get("equipamento", "—")
        score = result.get("confianca", 0)
        alts = result.get("alternativas", [])
        struct = result.get("estrutura_detectada", {})

        alt_lines = "\n".join(
            f"  • {a.get('equipamento', '?')}  ({a.get('confianca', 0):.1f}%)"
            for a in alts
        ) or "  (nenhuma)"

        struct_lines = (
            f"  Sheet: {struct.get('sheet_name', '—')}\n"
            f"  Linha início: {struct.get('linha_inicio', '—')}\n"
            f"  Total linhas dados: {struct.get('total_linhas', '—')}\n"
            f"  Colunas detectadas: Well={struct.get('coluna_well', '—')}  "
            f"Sample={struct.get('coluna_sample', '—')}  "
            f"Target={struct.get('coluna_target', '—')}  "
            f"CT={struct.get('coluna_ct', '—')}\n"
            f"  Headers: {', '.join(str(h) for h in (struct.get('headers') or [])[:8])}"
        )

        msg = (
            f"Equipamento detectado: {equip}\n"
            f"Confiança: {score:.1f}%\n\n"
            f"Alternativas:\n{alt_lines}\n\n"
            f"Estrutura detectada:\n{struct_lines}"
        )
        messagebox.showinfo("Resultado da Detecção", msg, parent=self.window)

    # ----------------------------- PLACAS -----------------------------

    def _build_tab_placas(self) -> None:

        frame = ctk.CTkFrame(self.tab_placas)

        frame.pack(expand=True, fill="both", padx=10, pady=10)

        frame.grid_rowconfigure(1, weight=1)

        frame.grid_columnconfigure(0, weight=1)

        frame.grid_columnconfigure(1, weight=1)



        table_frame = ctk.CTkFrame(frame)

        table_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10))



        cols = self.csv_configs["placas"].headers

        self.tree_placas = ttk.Treeview(

            table_frame,

            columns=cols,

            show="headings",

            height=15,

        )

        for c in cols:

            self.tree_placas.heading(c, text=c)

            self.tree_placas.column(c, width=140, anchor="w")

        self.tree_placas.pack(expand=True, fill="both", padx=5, pady=5)

        self.tree_placas.bind("<<TreeviewSelect>>", self._on_select_placa)



        btn_frame = ctk.CTkFrame(table_frame)

        btn_frame.pack(fill="x", padx=5, pady=(0, 5))



        ctk.CTkButton(

            btn_frame,

            text="Novo",

            command=self._novo_placa,

            width=80,

        ).pack(side="left", padx=5)

        ctk.CTkButton(

            btn_frame,

            text="Salvar",

            command=self._salvar_placa,

            width=80,

        ).pack(side="left", padx=5)

        ctk.CTkButton(

            btn_frame,

            text="Excluir",

            command=self._excluir_placa,

            width=80,

        ).pack(side="left", padx=5)

        ctk.CTkButton(

            btn_frame,

            text="Recarregar",

            command=self._carregar_placas,

            width=100,

        ).pack(side="right", padx=5)



        form_frame = ctk.CTkFrame(frame)

        form_frame.grid(row=0, column=1, sticky="nsew")



        self.entry_placa_nome = ctk.CTkEntry(

            form_frame, placeholder_text="Nome da placa"

        )

        self.entry_placa_nome.pack(fill="x", padx=5, pady=5)



        self.entry_placa_tipo = ctk.CTkEntry(

            form_frame, placeholder_text="Tipo (ex.: 48, 96)"

        )

        self.entry_placa_tipo.pack(fill="x", padx=5, pady=5)



        self.entry_placa_pocos = ctk.CTkEntry(

            form_frame, placeholder_text="Número de poços"

        )

        self.entry_placa_pocos.pack(fill="x", padx=5, pady=5)



        self.entry_placa_desc = ctk.CTkEntry(

            form_frame, placeholder_text="Descrição/observações"

        )

        self.entry_placa_desc.pack(fill="x", padx=5, pady=5)



        self._carregar_placas()



    def _carregar_placas(self) -> None:

        rows = self._load_csv("placas")

        for item in self.tree_placas.get_children():

            self.tree_placas.delete(item)

        for idx, r in enumerate(rows):

            self.tree_placas.insert(

                "",

                "end",

                iid=str(idx),

                values=[

                    r.get("nome", ""),

                    r.get("tipo", ""),

                    r.get("num_pocos", ""),

                    r.get("descricao", ""),

                ],

            )



    def _on_select_placa(self, event=None) -> None:

        sel = self.tree_placas.selection()

        if not sel:

            return

        iid = sel[0]

        self.current_plate_id = int(iid)

        vals = self.tree_placas.item(iid, "values")

        if not vals:

            return

        self.entry_placa_nome.delete(0, "end")

        self.entry_placa_nome.insert(0, vals[0])

        self.entry_placa_tipo.delete(0, "end")

        self.entry_placa_tipo.insert(0, vals[1])

        self.entry_placa_pocos.delete(0, "end")

        self.entry_placa_pocos.insert(0, vals[2])

        self.entry_placa_desc.delete(0, "end")

        self.entry_placa_desc.insert(0, vals[3])



    def _novo_placa(self) -> None:

        self.current_plate_id = None

        for entry in [

            self.entry_placa_nome,

            self.entry_placa_tipo,

            self.entry_placa_pocos,

            self.entry_placa_desc,

        ]:

            entry.delete(0, "end")



    def _salvar_placa(self) -> None:

        rows = self._load_csv("placas")

        dados = {

            "nome": self.entry_placa_nome.get().strip(),

            "tipo": self.entry_placa_tipo.get().strip(),

            "num_pocos": self.entry_placa_pocos.get().strip(),

            "descricao": self.entry_placa_desc.get().strip(),

        }

        if not dados["nome"]:

            messagebox.showwarning(

                "Aviso",

                "O campo 'nome' da placa é obrigatório.",

                parent=self.window,

            )

            return



        if self.current_plate_id is None:

            rows.append(dados)

        else:

            if 0 <= self.current_plate_id < len(rows):

                rows[self.current_plate_id] = dados

            else:

                rows.append(dados)



        self._save_csv("placas", rows)

        self._carregar_placas()



    def _excluir_placa(self) -> None:

        if self.current_plate_id is None:

            messagebox.showinfo(

                "Informação",

                "Selecione uma placa para excluir.",

                parent=self.window,

            )

            return



        if not messagebox.askyesno(

            "Confirmação",

            "Deseja realmente excluir a placa selecionada?",

            parent=self.window,

        ):

            return



        rows = self._load_csv("placas")

        if 0 <= self.current_plate_id < len(rows):

            rows.pop(self.current_plate_id)

            self._save_csv("placas", rows)

            self._carregar_placas()

            self._novo_placa()



    # ------------------------------ REGRAS -----------------------------

    def _build_tab_regras(self) -> None:

        frame = ctk.CTkFrame(self.tab_regras)

        frame.pack(expand=True, fill="both", padx=10, pady=10)

        frame.grid_rowconfigure(1, weight=1)

        frame.grid_columnconfigure(0, weight=1)

        frame.grid_columnconfigure(1, weight=1)



        table_frame = ctk.CTkFrame(frame)

        table_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10))



        cols = self.csv_configs["regras"].headers

        self.tree_regras = ttk.Treeview(

            table_frame,

            columns=cols,

            show="headings",

            height=15,

        )

        for c in cols:

            self.tree_regras.heading(c, text=c)

            self.tree_regras.column(c, width=160, anchor="w")

        self.tree_regras.pack(expand=True, fill="both", padx=5, pady=5)

        self.tree_regras.bind("<<TreeviewSelect>>", self._on_select_regra)



        btn_frame = ctk.CTkFrame(table_frame)

        btn_frame.pack(fill="x", padx=5, pady=(0, 5))



        ctk.CTkButton(

            btn_frame,

            text="Novo",

            command=self._novo_regra,

            width=80,

        ).pack(side="left", padx=5)

        ctk.CTkButton(

            btn_frame,

            text="Salvar",

            command=self._salvar_regra,

            width=80,

        ).pack(side="left", padx=5)

        ctk.CTkButton(

            btn_frame,

            text="Excluir",

            command=self._excluir_regra,

            width=80,

        ).pack(side="left", padx=5)

        ctk.CTkButton(

            btn_frame,

            text="Recarregar",

            command=self._carregar_regras,

            width=100,

        ).pack(side="right", padx=5)



        form_frame = ctk.CTkFrame(frame)

        form_frame.grid(row=0, column=1, sticky="nsew")



        self.entry_regra_nome = ctk.CTkEntry(

            form_frame, placeholder_text="Nome da regra"

        )

        self.entry_regra_nome.pack(fill="x", padx=5, pady=5)



        self.entry_regra_exame = ctk.CTkEntry(

            form_frame, placeholder_text="Exame associado (opcional)"

        )

        self.entry_regra_exame.pack(fill="x", padx=5, pady=5)



        self.entry_regra_desc = ctk.CTkEntry(

            form_frame, placeholder_text="Descrição da regra"

        )

        self.entry_regra_desc.pack(fill="x", padx=5, pady=5)



        self.entry_regra_param = ctk.CTkEntry(

            form_frame,

            placeholder_text="Parâmetros (livre, ex.: JSON ou key=value;key2=value2)",

        )

        self.entry_regra_param.pack(fill="x", padx=5, pady=5)



        self._carregar_regras()



    def _carregar_regras(self) -> None:

        rows = self._load_csv("regras")

        for item in self.tree_regras.get_children():

            self.tree_regras.delete(item)

        for idx, r in enumerate(rows):

            self.tree_regras.insert(

                "",

                "end",

                iid=str(idx),

                values=[

                    r.get("nome_regra", ""),

                    r.get("exame", ""),

                    r.get("descricao", ""),

                    r.get("parametros", ""),

                ],

            )



    def _on_select_regra(self, event=None) -> None:

        sel = self.tree_regras.selection()

        if not sel:

            return

        iid = sel[0]

        self.current_rule_id = int(iid)

        vals = self.tree_regras.item(iid, "values")

        if not vals:

            return

        self.entry_regra_nome.delete(0, "end")

        self.entry_regra_nome.insert(0, vals[0])

        self.entry_regra_exame.delete(0, "end")

        self.entry_regra_exame.insert(0, vals[1])

        self.entry_regra_desc.delete(0, "end")

        self.entry_regra_desc.insert(0, vals[2])

        self.entry_regra_param.delete(0, "end")

        self.entry_regra_param.insert(0, vals[3])



    def _novo_regra(self) -> None:

        self.current_rule_id = None

        for entry in [

            self.entry_regra_nome,

            self.entry_regra_exame,

            self.entry_regra_desc,

            self.entry_regra_param,

        ]:

            entry.delete(0, "end")



    def _salvar_regra(self) -> None:

        rows = self._load_csv("regras")

        dados = {

            "nome_regra": self.entry_regra_nome.get().strip(),

            "exame": self.entry_regra_exame.get().strip(),

            "descricao": self.entry_regra_desc.get().strip(),

            "parametros": self.entry_regra_param.get().strip(),

        }

        if not dados["nome_regra"]:

            messagebox.showwarning(

                "Aviso",

                "O campo 'nome_regra' é obrigatório.",

                parent=self.window,

            )

            return



        if self.current_rule_id is None:

            rows.append(dados)

        else:

            if 0 <= self.current_rule_id < len(rows):

                rows[self.current_rule_id] = dados

            else:

                rows.append(dados)



        self._save_csv("regras", rows)

        self._carregar_regras()



    def _excluir_regra(self) -> None:

        if self.current_rule_id is None:

            messagebox.showinfo(

                "Informação",

                "Selecione uma regra para excluir.",

                parent=self.window,

            )

            return



        if not messagebox.askyesno(

            "Confirmação",

            "Deseja realmente excluir a regra selecionada?",

            parent=self.window,

        ):

            return



        rows = self._load_csv("regras")

        if 0 <= self.current_rule_id < len(rows):

            rows.pop(self.current_rule_id)

            self._save_csv("regras", rows)

            self._carregar_regras()

            self._novo_regra()





# ============================================================================

# CLASSE: ExamFormDialog

# ============================================================================

# Dialog modal para criar/editar exames com 6 abas (Básico, Alvos, Faixas CT, 

# RP, Export, Controles). Integrado com RegistryExamEditor para validação 

# e persistência em JSON.

# ============================================================================





class ExamFormDialog(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        cfg=None,
        on_save=None,
        actor_username: Optional[str] = None,
        actor_access_level: Optional[str] = None,
        on_cancel: Optional[Callable] = None,
    ) -> None:
        super().__init__(parent)
        self.parent = parent
        self.cfg = cfg  # None = novo, ExamConfig = editar
        self.on_save = on_save
        self.on_cancel = on_cancel
        self.actor_username = str(actor_username or "").strip()
        self.actor_access_level = normalize_access_level(actor_access_level or "")

        self.editor = None  # Sera inicializado apos definir RegistryExamEditor


        # Carregar lista de equipamentos para dropdown

        self._equipamentos = self._load_equipamentos()



        # Configurar window como self para compatibilidade e definir titulo
        self.window = self
        self.title_text = f"Editar: {cfg.nome_exame}" if cfg else "Novo Exame"



        # Widgets de entrada (preenchidos conforme modo)

        self.entry_nome = None

        self.label_slug = None

        self.combo_equip = None

        self.entry_tipo_placa = None

        self.entry_esquema = None

        self.entry_kit = None

        self.text_alvos = None

        self.text_mapa = None

        self.entry_detect_max = None

        self.entry_inconc_min = None

        self.entry_inconc_max = None

        self.entry_rp_min = None

        self.entry_rp_max = None

        self.text_rps = None

        self.text_export = None

        self.entry_panel = None

        self.text_cn = None

        self.text_cp = None

        self.text_comentarios = None

        self.entry_versao = None



        self._build_ui()



    def _load_equipamentos(self) -> List[str]:

        """Carrega lista de equipamentos disponíveis do banco/equipamentos.csv"""
        from pathlib import Path

        try:

            try:
                paths = config_service.get_paths()
                catalog_path = paths.get("exams_catalog_csv")
            except Exception:
                catalog_path = None
            base_dir = Path(catalog_path).parent if catalog_path else Path(BASE_DIR) / "banco_runtime"
            equip_path = base_dir / "equipamentos.csv"

            equipamentos = []

            policy = RetryPolicy.from_env()
            if path_exists_with_retry(equip_path, policy=policy):

                with open_with_retry(equip_path, "r", encoding="utf-8", policy=policy) as f:

                    reader = csv.DictReader(f)

                    for row in reader:

                        if "nome" in row:

                            equipamentos.append(row["nome"].strip())

            return sorted(equipamentos)

        except Exception:

            return ["7500 Real-Time", "QuantStudio"]  # Fallback



    def _build_ui(self) -> None:

        """Constrói interface com TabView + 6 abas + botões"""

        main = ctk.CTkFrame(self.window)

        main.pack(expand=True, fill="both", padx=10, pady=10)



        # Título
        title = ctk.CTkLabel(
            main,
            text=self.title_text,

            font=ctk.CTkFont(size=18, weight="bold"),

        )

        title.pack(pady=(0, 15))



        # TabView com 6 abas

        self.tabview = ctk.CTkTabview(main)

        self.tabview.pack(expand=True, fill="both", pady=(0, 15))



        self.tab_basico = self.tabview.add("Básico")

        self.tab_alvos = self.tabview.add("Alvos")

        self.tab_faixas = self.tabview.add("Faixas CT")

        self.tab_rp = self.tabview.add("RP")

        self.tab_export = self.tabview.add("Export")

        self.tab_controles = self.tabview.add("Controles")



        self._build_tab_basico()

        self._build_tab_alvos()

        self._build_tab_faixas()

        self._build_tab_rp()

        self._build_tab_export()

        self._build_tab_controles()



        # Botões

        btn_frame = ctk.CTkFrame(main)

        btn_frame.pack(pady=(10, 0))



        btn_salvar = ctk.CTkButton(

            btn_frame,

            text="Salvar",

            command=self._salvar,

            fg_color="green",

        )

        btn_salvar.pack(side="left", padx=5)



        btn_cancelar = ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            command=self._cancelar,
            fg_color="red",
        )
        btn_cancelar.pack(side="left", padx=5)

    def _cancelar(self) -> None:
        if self.on_cancel:
            self.on_cancel()
        else:
            self.destroy()



    def _build_tab_basico(self) -> None:

        """Constrói aba BÃSICO com 6 campos"""

        frame = ctk.CTkFrame(self.tab_basico)

        frame.pack(expand=True, fill="both", padx=15, pady=15)



        # Nome Exame

        lbl = ctk.CTkLabel(frame, text="Nome do Exame *", font=ctk.CTkFont(weight="bold"))

        lbl.pack(anchor="w", pady=(0, 5))

        self.entry_nome = ctk.CTkEntry(frame, width=400)

        self.entry_nome.pack(fill="x", pady=(0, 15))

        if self.cfg:

            self.entry_nome.insert(0, self.cfg.nome_exame)



        # Slug (read-only)

        lbl = ctk.CTkLabel(frame, text="Slug (auto-gerado)", font=ctk.CTkFont(weight="bold"))

        lbl.pack(anchor="w", pady=(0, 5))

        self.label_slug = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(family="Consolas", size=12))

        self.label_slug.pack(fill="x", pady=(0, 15))

        if self.cfg:

            self.label_slug.configure(text=self.cfg.slug)

        self.entry_nome.bind("<KeyRelease>", self._update_slug)



        # Equipamento

        lbl = ctk.CTkLabel(frame, text="Equipamento *", font=ctk.CTkFont(weight="bold"))

        lbl.pack(anchor="w", pady=(0, 5))

        self.combo_equip = ctk.CTkComboBox(

            frame, values=self._equipamentos, width=400

        )

        self.combo_equip.pack(fill="x", pady=(0, 15))

        if self.cfg:

            self.combo_equip.set(self.cfg.equipamento)



        # Tipo Placa

        lbl = ctk.CTkLabel(frame, text="Tipo Placa Analítica", font=ctk.CTkFont(weight="bold"))

        lbl.pack(anchor="w", pady=(0, 5))

        self.entry_tipo_placa = ctk.CTkEntry(frame, width=200)

        self.entry_tipo_placa.pack(fill="x", pady=(0, 15))

        if self.cfg:

            self.entry_tipo_placa.insert(0, self.cfg.tipo_placa_analitica)



        # Esquema Agrupamento

        lbl = ctk.CTkLabel(frame, text="Esquema Agrupamento", font=ctk.CTkFont(weight="bold"))

        lbl.pack(anchor="w", pady=(0, 5))

        self.entry_esquema = ctk.CTkEntry(frame, width=200)

        self.entry_esquema.pack(fill="x", pady=(0, 15))

        if self.cfg:

            self.entry_esquema.insert(0, self.cfg.esquema_agrupamento)



        # Kit Código

        lbl = ctk.CTkLabel(frame, text="Kit Código", font=ctk.CTkFont(weight="bold"))

        lbl.pack(anchor="w", pady=(0, 5))

        self.entry_kit = ctk.CTkEntry(frame, width=200)

        self.entry_kit.pack(fill="x")

        if self.cfg:

            self.entry_kit.insert(0, str(self.cfg.kit_codigo))



    def _build_tab_alvos(self) -> None:

        """Constrói aba ALVOS com 2 campos (JSON)"""

        frame = ctk.CTkFrame(self.tab_alvos)

        frame.pack(expand=True, fill="both", padx=15, pady=15)



        # Alvos

        lbl = ctk.CTkLabel(

            frame,

            text="Alvos (JSON list)",

            font=ctk.CTkFont(weight="bold"),

        )

        lbl.pack(anchor="w", pady=(0, 5))

        self.text_alvos = ctk.CTkTextbox(frame, height=150)

        self.text_alvos.pack(expand=True, fill="both", pady=(0, 15))

        if self.cfg and self.cfg.alvos:

            import json

            self.text_alvos.insert("1.0", json.dumps(self.cfg.alvos, indent=2))



        # Mapa Alvos

        lbl = ctk.CTkLabel(

            frame,

            text="Mapa Alvos (JSON dict)",

            font=ctk.CTkFont(weight="bold"),

        )

        lbl.pack(anchor="w", pady=(0, 5))

        self.text_mapa = ctk.CTkTextbox(frame, height=150)

        self.text_mapa.pack(expand=True, fill="both")

        if self.cfg and self.cfg.mapa_alvos:

            import json

            self.text_mapa.insert("1.0", json.dumps(self.cfg.mapa_alvos, indent=2))



    def _build_tab_faixas(self) -> None:
        """Constrói aba FAIXAS CT: tabela por alvo (uma linha por alvo único)."""

        outer = ctk.CTkFrame(self.tab_faixas)
        outer.pack(expand=True, fill="both", padx=15, pady=15)
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(1, weight=1)

        # Refs de compatibilidade (não mais usadas como global entries)
        self.entry_detect_max = None
        self.entry_inconc_min = None
        self.entry_inconc_max = None
        self.entry_rp_min = None
        self.entry_rp_max = None
        self._faixas_entries = {}

        # --- Cabeçalho fixo ---
        header = ctk.CTkFrame(outer, fg_color=Theme.BORDER_DEFAULT)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 0))
        for ci in range(5):
            header.grid_columnconfigure(ci, weight=2 if ci == 0 else 1)

        col_labels = [
            "Alvo",
            "CT Detectável Mínimo",
            "CT Detectável Máximo",
            "CT Inconclusivo Mínimo",
            "CT Inconclusivo Máximo",
        ]
        for ci, lbl in enumerate(col_labels):
            ctk.CTkLabel(
                header,
                text=lbl,
                font=ctk.CTkFont(weight="bold"),
                anchor="w" if ci == 0 else "center",
            ).grid(row=0, column=ci, padx=(10 if ci == 0 else 5), pady=6, sticky="w" if ci == 0 else "")

        # --- Linhas editáveis (uma por alvo único) ---
        ScrollableFrame = getattr(ctk, "CTkScrollableFrame", ctk.CTkFrame)
        rows_frame = ScrollableFrame(outer)
        rows_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 5))
        for ci in range(5):
            rows_frame.grid_columnconfigure(ci, weight=2 if ci == 0 else 1)

        # Alvos únicos preservando ordem de cfg.alvos
        alvos_list: list[str] = []
        if self.cfg:
            if self.cfg.alvos:
                seen_a: set[str] = set()
                for a in self.cfg.alvos:
                    a = str(a).strip()
                    if a and a.upper() not in seen_a:
                        alvos_list.append(a)
                        seen_a.add(a.upper())
            elif getattr(self.cfg, "targets_por_poco", None):
                seen_a = set()
                for t in self.cfg.targets_por_poco:
                    a = str(t.get("alvo", "")).strip()
                    if a and a.upper() not in seen_a:
                        alvos_list.append(a)
                        seen_a.add(a.upper())

        # Índice: primeira ocorrência por alvo (para pré-preencher)
        limiares_idx: dict[str, dict] = {}
        for item in (getattr(self.cfg, "limiares_ct_por_alvo_poco", []) or []):
            if isinstance(item, dict):
                k = str(item.get("alvo", "")).strip().upper()
                if k not in limiares_idx:
                    limiares_idx[k] = item

        # Defaults globais para alvos sem limiar individual
        fct = (self.cfg.faixas_ct if (self.cfg and self.cfg.faixas_ct) else {}) or {}
        def_det_min = str(fct.get("rp_min", 8.1))
        def_det_max = str(fct.get("detect_max", 35.0))
        def_inc_max = str(fct.get("inconc_max", 40.0))

        self._faixas_alvos_entries: list[dict] = []

        if not alvos_list:
            ctk.CTkLabel(
                rows_frame,
                text="Nenhum alvo cadastrado. Adicione alvos na aba 'Alvos' primeiro.",
                text_color="gray60",
            ).pack(pady=20)
        else:
            for i, alvo in enumerate(alvos_list):
                lim = limiares_idx.get(alvo.upper(), {})

                ct_det_min = str(lim.get("ct_minimo", def_det_min))
                ct_det_max = str(lim.get("ct_detectavel_limite", def_det_max))
                # ct_inconclusivo_min pode não estar gravado; deriva de det_max + 0.01
                stored_inc_min = lim.get("ct_inconclusivo_min")
                if stored_inc_min is not None:
                    ct_inc_min = str(stored_inc_min)
                else:
                    try:
                        ct_inc_min = str(round(float(ct_det_max) + 0.01, 4))
                    except Exception:
                        ct_inc_min = def_inc_max
                ct_inc_max = str(lim.get("ct_inconclusivo_limite", def_inc_max))

                row_bg = Theme.COLOR_GRAY_SOFT if i % 2 == 0 else "transparent"
                row_f = ctk.CTkFrame(rows_frame, fg_color=row_bg)
                row_f.pack(fill="x", pady=1)
                for ci in range(5):
                    row_f.grid_columnconfigure(ci, weight=2 if ci == 0 else 1)

                ctk.CTkLabel(row_f, text=alvo, anchor="w").grid(
                    row=0, column=0, padx=10, pady=5, sticky="w"
                )

                ent_det_min = ctk.CTkEntry(row_f, width=120)
                ent_det_min.insert(0, ct_det_min)
                ent_det_min.grid(row=0, column=1, padx=5, pady=5)

                ent_det_max = ctk.CTkEntry(row_f, width=120)
                ent_det_max.insert(0, ct_det_max)
                ent_det_max.grid(row=0, column=2, padx=5, pady=5)

                ent_inc_min = ctk.CTkEntry(row_f, width=120)
                ent_inc_min.insert(0, ct_inc_min)
                ent_inc_min.grid(row=0, column=3, padx=5, pady=5)

                ent_inc_max = ctk.CTkEntry(row_f, width=120)
                ent_inc_max.insert(0, ct_inc_max)
                ent_inc_max.grid(row=0, column=4, padx=5, pady=5)

                self._faixas_alvos_entries.append({
                    "alvo": alvo,
                    "det_min": ent_det_min,
                    "det_max": ent_det_max,
                    "inc_min": ent_inc_min,
                    "inc_max": ent_inc_max,
                })



    def _build_tab_rp(self) -> None:

        """Constrói aba RP com 1 campo (JSON list)"""

        frame = ctk.CTkFrame(self.tab_rp)

        frame.pack(expand=True, fill="both", padx=15, pady=15)



        lbl = ctk.CTkLabel(

            frame,

            text="RPs (JSON list, ex: [\"RP\", \"RP_1\", \"RP_2\"])",

            font=ctk.CTkFont(weight="bold"),

        )

        lbl.pack(anchor="w", pady=(0, 5))

        self.text_rps = ctk.CTkTextbox(frame, height=300)

        self.text_rps.pack(expand=True, fill="both")

        if self.cfg and self.cfg.rps:

            import json

            self.text_rps.insert("1.0", json.dumps(self.cfg.rps, indent=2))



    def _build_tab_export(self) -> None:

        """Constrói aba EXPORT com 2 campos"""

        frame = ctk.CTkFrame(self.tab_export)

        frame.pack(expand=True, fill="both", padx=15, pady=15)



        # Export Fields

        lbl = ctk.CTkLabel(

            frame,

            text="Export Fields (JSON list)",

            font=ctk.CTkFont(weight="bold"),

        )

        lbl.pack(anchor="w", pady=(0, 5))

        self.text_export = ctk.CTkTextbox(frame, height=200)

        self.text_export.pack(expand=True, fill="both", pady=(0, 15))

        if self.cfg and self.cfg.export_fields:

            import json

            self.text_export.insert("1.0", json.dumps(self.cfg.export_fields, indent=2))



        # Panel Tests ID

        lbl = ctk.CTkLabel(

            frame,

            text="Panel Tests ID",

            font=ctk.CTkFont(weight="bold"),

        )

        lbl.pack(anchor="w", pady=(0, 5))

        self.entry_panel = ctk.CTkEntry(frame, width=200)

        self.entry_panel.pack(fill="x")

        if self.cfg:

            self.entry_panel.insert(0, self.cfg.panel_tests_id)



    def _build_tab_controles(self) -> None:

        """Constrói aba CONTROLES com CN/CP/comentarios/versao"""

        frame = ctk.CTkFrame(self.tab_controles)

        frame.pack(expand=True, fill="both", padx=15, pady=15)

        frame.grid_rowconfigure(0, weight=0)

        frame.grid_rowconfigure(1, weight=0)

        frame.grid_rowconfigure(2, weight=1)

        frame.grid_columnconfigure(0, weight=1)

        frame.grid_columnconfigure(1, weight=1)



        # CN (Controle Negativo)

        lbl = ctk.CTkLabel(

            frame,

            text="Controles CN (JSON list)",

            font=ctk.CTkFont(weight="bold"),

        )

        lbl.grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.text_cn = ctk.CTkTextbox(frame, height=100)

        self.text_cn.grid(row=1, column=0, sticky="nsew", padx=(0, 5))

        if self.cfg and self.cfg.controles and self.cfg.controles.get("cn"):

            import json

            self.text_cn.insert("1.0", json.dumps(self.cfg.controles["cn"], indent=2))



        # CP (Controle Positivo)

        lbl = ctk.CTkLabel(

            frame,

            text="Controles CP (JSON list)",

            font=ctk.CTkFont(weight="bold"),

        )

        lbl.grid(row=0, column=1, sticky="w", pady=(0, 5), padx=(5, 0))

        self.text_cp = ctk.CTkTextbox(frame, height=100)

        self.text_cp.grid(row=1, column=1, sticky="nsew", padx=(5, 0))

        if self.cfg and self.cfg.controles and self.cfg.controles.get("cp"):

            import json

            self.text_cp.insert("1.0", json.dumps(self.cfg.controles["cp"], indent=2))



        # Comentarios

        lbl = ctk.CTkLabel(

            frame,

            text="Comentários",

            font=ctk.CTkFont(weight="bold"),

        )

        lbl.grid(row=2, column=0, sticky="nw", pady=(15, 5))

        self.text_comentarios = ctk.CTkTextbox(frame, height=100)

        self.text_comentarios.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, 15))

        if self.cfg:

            self.text_comentarios.insert("1.0", self.cfg.comentarios)



        # Versão Protocolo

        lbl = ctk.CTkLabel(

            frame,

            text="Versão Protocolo",

            font=ctk.CTkFont(weight="bold"),

        )

        lbl.grid(row=4, column=0, sticky="w", pady=(0, 5))

        self.entry_versao = ctk.CTkEntry(frame, width=150)

        self.entry_versao.grid(row=5, column=0, sticky="w")

        if self.cfg:

            self.entry_versao.insert(0, self.cfg.versao_protocolo)



    def _update_slug(self, event=None) -> None:

        """Atualiza label de slug baseado no nome_exame"""

        nome = self.entry_nome.get().strip()

        if nome:

            slug = self._generate_slug_local(nome)

            self.label_slug.configure(text=slug)



    def _generate_slug_local(self, nome_exame: str) -> str:

        """Gera slug localmente (mesmo algoritmo de RegistryExamEditor)

        

        Normaliza nome: lowercase, remove acentos, substitui espaços/hífens por underscores

        """

        import unicodedata

        

        # Lowercase e strip

        normalized = str(nome_exame).strip().lower()

        

        # Remover acentos (NFKD + ASCII)

        normalized = unicodedata.normalize('NFKD', normalized)

        normalized = normalized.encode('ASCII', 'ignore').decode('ASCII')

        

        # Substituir espaços e hífens por underscores

        slug = normalized.replace(" ", "_").replace("-", "_")

        

        return slug



    def _collect_form_data(self):

        """Coleta dados de todas as abas e retorna ExamConfig"""

        import json



        nome = self.entry_nome.get().strip()

        slug = self._generate_slug_local(nome)



        try:

            alvos = json.loads(self.text_alvos.get("1.0", "end"))

        except Exception:

            alvos = []



        try:

            mapa_alvos = json.loads(self.text_mapa.get("1.0", "end"))

        except Exception:

            mapa_alvos = {}



        # faixas_ct: mantém apenas rp_min/rp_max globais (derivados do alvo RP, se existir)
        faixas_ct = {}

        # Mapa de poços por alvo: preserva os poços originais para cada alvo
        from collections import defaultdict
        alvo_pocos: dict[str, list[int]] = defaultdict(list)
        for item in (getattr(self.cfg, "limiares_ct_por_alvo_poco", []) or []) if self.cfg else []:
            if isinstance(item, dict):
                ak = str(item.get("alvo", "")).strip().upper()
                pv = int(item.get("poco", 1) or 1)
                if pv not in alvo_pocos[ak]:
                    alvo_pocos[ak].append(pv)

        limiares = []
        for entry in getattr(self, "_faixas_alvos_entries", []):
            try:
                alvo = entry["alvo"]
                ct_det_min = float(str(entry["det_min"].get()).replace(",", "."))
                ct_det_max = float(str(entry["det_max"].get()).replace(",", "."))
                ct_inc_min = float(str(entry["inc_min"].get()).replace(",", "."))
                ct_inc_max = float(str(entry["inc_max"].get()).replace(",", "."))
            except Exception:
                continue

            # Propaga os mesmos valores para todos os poços originais do alvo
            pocos = alvo_pocos.get(alvo.upper()) or [1]
            for poco in pocos:
                limiares.append({
                    "alvo": alvo,
                    "poco": poco,
                    "ct_minimo": ct_det_min,
                    "ct_detectavel_limite": ct_det_max,
                    "ct_inconclusivo_min": ct_inc_min,
                    "ct_inconclusivo_limite": ct_inc_max,
                })

            # Deriva rp_min/rp_max globais do alvo RP
            if alvo.upper() == "RP":
                faixas_ct["rp_min"] = ct_det_min
                faixas_ct["rp_max"] = ct_det_max



        try:

            rps = json.loads(self.text_rps.get("1.0", "end"))

        except Exception:

            rps = []



        try:

            export_fields = json.loads(self.text_export.get("1.0", "end"))

        except Exception:

            export_fields = []



        try:

            cn = json.loads(self.text_cn.get("1.0", "end"))

        except Exception:

            cn = []



        try:

            cp = json.loads(self.text_cp.get("1.0", "end"))

        except Exception:

            cp = []



        from services.exam_registry import ExamConfig



        return ExamConfig(

            nome_exame=nome,

            slug=slug,

            equipamento=self.combo_equip.get().strip(),

            tipo_placa_analitica=self.entry_tipo_placa.get().strip(),

            esquema_agrupamento=self.entry_esquema.get().strip(),

            kit_codigo=self.entry_kit.get().strip(),

            alvos=alvos,

            mapa_alvos=mapa_alvos,

            faixas_ct=faixas_ct,

            limiares_ct_por_alvo_poco=limiares,

            rps=rps,

            export_fields=export_fields,

            panel_tests_id=self.entry_panel.get().strip(),

            controles={"cn": cn, "cp": cp},

            comentarios=self.text_comentarios.get("1.0", "end").strip(),

            versao_protocolo=self.entry_versao.get().strip(),

        )



    def _salvar(self) -> None:

        """Coleta dados, valida, salva e fecha dialog"""

        try:

            # Inicializar editor aqui para evitar circular import

            if self.editor is None:

                # self.editor = RegistryExamEditor(...)

                self.editor = RegistryExamEditor(

                    actor_username=self.actor_username,

                    actor_access_level=self.actor_access_level,

                )



            cfg = self._collect_form_data()



            # Validar

            is_valid, msg = self.editor.validate_exam(cfg)

            if not is_valid:

                messagebox.showerror(

                    "Erro de Validação",

                    f"Validação falhou:\n{msg}",

                    parent=self.window,

                )

                return



            # Salvar

            success, msg = self.editor.save_exam(cfg)

            if not success:

                messagebox.showerror(

                    "Erro ao Salvar",

                    msg,

                    parent=self.window,

                )

                return



            # Recarregar registry

            self.editor.reload_registry()



            # Callback se existir
            if self.on_save:
                self.on_save(cfg)
            else:
                # Fechar se não houver callback gerenciando o state
                self.window.destroy()

            # Sucesso

            messagebox.showinfo(
                "Sucesso",
                f"Exame '{cfg.nome_exame}' salvo com sucesso!",
                parent=self.window,
            )
            # Ação de fechar agora é controlada pelo callback (on_save)
            # O on_save já deve fechar a janela, mas se não fechar, chamamos _cancelar()
            # self._cancelar() será chamado só se for necessário (mas o on_save do wizard destrói o frame).
            # Para evitar double-destroy, não fazemos nada aqui, o on_save lida com isso.



        except Exception as e:

            messagebox.showerror(

                "Erro Inesperado",

                f"Erro ao salvar:\n{str(e)}",

                parent=self.window,

            )



    # ============================================================================

    # EXAMES (REGISTRY) - Integração com RegistryExamEditor

    # ============================================================================

    def _build_tab_exames_registry(self) -> None:

        """

        Constrói a aba "Exames (Registry)" para CRUD via RegistryExamEditor.

        """


        frame = ctk.CTkFrame(self.tab_exames_registry)

        frame.pack(expand=True, fill="both", padx=10, pady=10)

        frame.grid_rowconfigure(1, weight=1)

        frame.grid_columnconfigure(0, weight=1)

        frame.grid_columnconfigure(1, weight=1)



        # Status label

        self.status_registry = ctk.CTkLabel(frame, text="Carregando exames do registry...", font=ctk.CTkFont(size=14))

        self.status_registry.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,8))



        # Listbox de exames (com barra rolante)
        list_frame = ctk.CTkFrame(frame)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.listbox_registry = tk.Listbox(list_frame, height=18, font=("Consolas", 12))
        self.listbox_registry.grid(row=0, column=0, sticky="nsew")

        self.scrollbar_registry = ctk.CTkScrollbar(
            list_frame, orientation="vertical", command=self.listbox_registry.yview
        )
        self.scrollbar_registry.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        self.listbox_registry.configure(yscrollcommand=self.scrollbar_registry.set)



        # Botões

        btn_frame = ctk.CTkFrame(frame)

        btn_frame.grid(row=1, column=1, sticky="n")

        self.btn_novo_registry = ctk.CTkButton(btn_frame, text="Novo", command=self._novo_exame_registry)

        self.btn_novo_registry.pack(fill="x", pady=2)

        self.btn_editar_registry = ctk.CTkButton(btn_frame, text="Editar", command=self._editar_exame_registry)

        self.btn_editar_registry.pack(fill="x", pady=2)

        self.btn_excluir_registry = ctk.CTkButton(btn_frame, text="Excluir", command=self._excluir_exame_registry)

        self.btn_excluir_registry.pack(fill="x", pady=2)

        self.btn_recarregar_registry = ctk.CTkButton(btn_frame, text="Recarregar", command=self._carregar_exames_registry)

        self.btn_recarregar_registry.pack(fill="x", pady=2)



        # Carregar exames do registry

        self._carregar_exames_registry()



        # Bind seleção

        self.listbox_registry.bind("<<ListboxSelect>>", self._on_select_exam_registry)



    def _carregar_exames_registry(self) -> None:

        """

        Carrega lista de exames do RegistryExamEditor e atualiza listbox.

        """

        # editor = RegistryExamEditor()

        editor = RegistryExamEditor()

        exames = editor.load_all_exams()

        self.listbox_registry.delete(0, tk.END)

        for nome, slug in exames:

            self.listbox_registry.insert(tk.END, f"{nome} [{slug}]")

        self.status_registry.configure(text=f"{len(exames)} exames carregados.")



    def _on_select_exam_registry(self, event=None) -> None:

        """

        Atualiza estado ao selecionar exame na listbox.

        """

        selection = self.listbox_registry.curselection()

        if selection:

            value = self.listbox_registry.get(selection[0])

            # Extrai slug do texto "Nome [slug]"

            if "[" in value and "]" in value:

                slug = value.split("[")[-1].split("]")[0].strip()

                self.current_exam_slug = slug

                self.status_registry.configure(text=f"Selecionado: {value}")

        else:

            self.current_exam_slug = None

            self.status_registry.configure(text="Nenhum exame selecionado.")



    def _novo_exame_registry(self) -> None:

        """

        Abre dialog para criar novo exame com formulário multi-aba.

        Ao salvar, recarrega listbox automaticamente.

        """

        def on_save_callback(cfg):

            """Callback após salvar: recarrega UI"""

            self._carregar_exames_registry()

            self.status_registry.configure(text=f"Exame '{cfg.nome_exame}' criado com sucesso!")



        actor_username, actor_access_level = self._resolve_actor_context()

        dialog = ExamFormDialog(

            parent=self.window,

            cfg=None,  # Modo novo

            on_save=on_save_callback,

            actor_username=actor_username,

            actor_access_level=actor_access_level,

        )



    def _editar_exame_registry(self) -> None:

        """

        Abre dialog para editar exame selecionado.

        Ao salvar, recarrega listbox automaticamente.

        """

        if not self.current_exam_slug:

            self.status_registry.configure(text="Selecione um exame para editar.")

            return



        actor_username, actor_access_level = self._resolve_actor_context()

        editor = RegistryExamEditor(

            actor_username=actor_username,

            actor_access_level=actor_access_level,

        )

        cfg = editor.load_exam(self.current_exam_slug)

        if not cfg:

            self.status_registry.configure(text=f"Erro: Não foi possível carregar {self.current_exam_slug}")

            return



        def on_save_callback(updated_cfg):

            """Callback após salvar: recarrega UI"""

            self._carregar_exames_registry()

            self.status_registry.configure(text=f"Exame '{updated_cfg.nome_exame}' atualizado com sucesso!")



        dialog = ExamFormDialog(

            parent=self.window,

            cfg=cfg,  # Modo editar

            on_save=on_save_callback,

            actor_username=actor_username,

            actor_access_level=actor_access_level,

        )



    def _excluir_exame_registry(self) -> None:

        """

        Exclui exame selecionado do registry.

        """

        if not self.current_exam_slug:

            self.status_registry.configure(text="Selecione um exame para excluir.")

            return

        # from services.cadastros_diversos import RegistryExamEditor

        actor_username, actor_access_level = self._resolve_actor_context()

        editor = RegistryExamEditor(

            actor_username=actor_username,

            actor_access_level=actor_access_level,

        )

        success, msg = editor.delete_exam(self.current_exam_slug)

        self.status_registry.configure(text=msg)

        self._carregar_exames_registry()



    def _recarregar_registry(self) -> None:

        """

        Recarrega registry e atualiza listbox.

        """

        self._carregar_exames_registry()

# Responsável pela edição de exames integrada com o registry híbrido

# (CSV base + JSON override). Fornece métodos para:

#   - Carregar exames do registry

#   - Validar ExamConfig

#   - Salvar em JSON (config/exams/{slug}.json)

#   - Deletar exames

#   - Recarregar registry após modificações

# ============================================================================





class RegistryExamEditor:

    """

    Editor de exames integrado com registry híbrido (CSV+JSON).

    

    Responsabilidades:

    - Carregar lista de exames do registry

    - Validar ExamConfig contra schema esperado

    - Salvar novos/editados exames em JSON

    - Deletar exames (remover arquivo JSON)

    - Recarregar registry após modificações

    - Converter ExamConfig â†” Dict (para JSON I/O)

    

    Attributes:

        registry: Instância global de ExamRegistry (carregada dinamicamente)

    """



    def __init__(
        self,
        *,
        actor_username: Optional[str] = None,
        actor_access_level: Optional[str] = None,
    ) -> None:

        """Inicializa o editor de exames."""

        from services.exam_registry import registry

        self.registry = registry
        self.actor_username = str(actor_username or "").strip()
        self.actor_access_level = normalize_access_level(actor_access_level or "")

    def _is_operation_allowed(self, operation: str) -> bool:
        """Valida permissao de escrita administrativa no registry."""
        try:
            ensure_operation_allowed(
                operation,
                self.actor_access_level,
                actor_username=self.actor_username,
            )
            return True
        except AuthorizationDeniedError as exc:
            registrar_log("RegistryExamEditor", str(exc), "WARNING")
            return False



    def load_all_exams(self) -> List[tuple]:

        """

        Carrega lista de todos os exames do registry.

        

        Returns:

            List[tuple]: Lista de (nome_exame, slug) ordenada por nome.

            

        Example:

            >>> editor = RegistryExamEditor()

            >>> exames = editor.load_all_exams()

            >>> # [("VR1e2 Biomanguinhos 7500", "vr1e2_biomanguinhos_7500"), ...]

        """

        try:
            self.registry.load()
            exames = []

            for slug, cfg in self.registry.exams.items():

                exames.append((cfg.nome_exame, slug))

            # Ordena por nome_exame (primeiro elemento da tupla)

            return sorted(exames, key=lambda x: x[0])

        except Exception as e:

            registrar_log("load_all_exams", f"Erro ao carregar exames: {e}", level="ERROR")

            return []



    def load_exam(self, slug_or_key: str) -> Optional:

        """

        Carrega configuração de um exame específico pelo slug.

        

        Args:

            slug_or_key (str): Pode ser:

                - Slug do arquivo (ex: "vr1e2_biomanguinhos_7500")

                - Chave normalizada (ex: "vr1e2 biomanguinhos 7500")

                - Nome do exame (ex: "VR1e2 Biomanguinhos 7500")

            

        Returns:

            ExamConfig | None: Configuração do exame ou None se não encontrado.

            

        Example:

            >>> cfg = editor.load_exam("vr1e2_biomanguinhos_7500")

            >>> if cfg:

            ...     print(cfg.nome_exame)

        """

        try:

            # Se for slug (contém underscore), converter para chave normalizada

            # slug: "teste_integracao_001" â†’ chave: "teste integracao 001"

            if "_" in slug_or_key and " " not in slug_or_key:

                # Provavelmente é um slug, converter para formato de chave

                search_key = slug_or_key.replace("_", " ")

            else:

                # É um nome ou chave já normalizado

                search_key = slug_or_key

            

            # Tentar como chave normalizada (registry.get faz normalização)

            return self.registry.get(search_key)

        except Exception as e:

            registrar_log("load_exam", f"Erro ao carregar exame {slug_or_key}: {e}", level="ERROR")

            return None



    def validate_exam(self, cfg) -> tuple:

        """

        Valida um ExamConfig contra o schema esperado.

        

        Verificações:

        - Campos obrigatórios preenchidos (nome_exame, slug, equipamento)

        - Tipos corretos (str, list, dict, float, int)

        - Ranges válidos (faixas_ct valores positivos, etc.)

        - Formato de dados (JSON válido em campos dict/list)

        

        Args:

            cfg (ExamConfig): Configuração a validar

            

        Returns:

            Tuple[bool, str]: (is_valid, mensagem_erro_ou_ok)

            

        Example:

            >>> cfg = ExamConfig(nome_exame="VR1", ...)

            >>> is_valid, msg = editor.validate_exam(cfg)

            >>> if not is_valid:

            ...     print(f"Erro: {msg}")

        """

        # Validar nome_exame (obrigatório)

        if not cfg.nome_exame or not isinstance(cfg.nome_exame, str):

            return False, "nome_exame deve ser string não-vazia"



        # Validar slug (obrigatório)

        if not cfg.slug or not isinstance(cfg.slug, str):

            return False, "slug deve ser string não-vazia"



        # Validar equipamento (obrigatório)

        if not cfg.equipamento or not isinstance(cfg.equipamento, str):

            return False, "equipamento deve ser string não-vazia"



        # Validar tipo_placa_analitica (obrigatório)

        if not cfg.tipo_placa_analitica or not isinstance(cfg.tipo_placa_analitica, str):

            return False, "tipo_placa_analitica deve ser string não-vazia"



        # Validar esquema_agrupamento

        if not cfg.esquema_agrupamento or not isinstance(cfg.esquema_agrupamento, str):

            return False, "esquema_agrupamento deve ser string não-vazia"



        # Validar kit_codigo

        if cfg.kit_codigo is None:

            return False, "kit_codigo não pode ser None"



        # Validar alvos (deve ser lista)

        if not isinstance(cfg.alvos, list):

            return False, "alvos deve ser uma lista"



        # Validar mapa_alvos (deve ser dict)

        if not isinstance(cfg.mapa_alvos, dict):

            return False, "mapa_alvos deve ser um dicionário"



        # Validar faixas_ct (deve ser dict com floats)

        if not isinstance(cfg.faixas_ct, dict):

            return False, "faixas_ct deve ser um dicionário"



        # Verificar valores em faixas_ct (devem ser floats positivos)

        for key, value in cfg.faixas_ct.items():

            if not isinstance(value, (int, float)):

                return False, f"faixas_ct[{key}] deve ser numérico, recebido {type(value).__name__}"

            if value < 0:

                return False, f"faixas_ct[{key}] não pode ser negativo (recebido {value})"



        # Validar rps (deve ser lista)

        if not isinstance(cfg.rps, list):

            return False, "rps deve ser uma lista"



        # Validar export_fields (deve ser lista)

        if not isinstance(cfg.export_fields, list):

            return False, "export_fields deve ser uma lista"



        # Validar panel_tests_id (pode ser vazio, mas deve ser string)

        if not isinstance(cfg.panel_tests_id, str):

            return False, "panel_tests_id deve ser string"



        # Validar controles (deve ser dict)

        if not isinstance(cfg.controles, dict):

            return False, "controles deve ser um dicionário"



        # Validar estrutura de controles (cn e cp devem ser listas)

        if "cn" in cfg.controles and not isinstance(cfg.controles["cn"], list):

            return False, "controles['cn'] deve ser uma lista"

        if "cp" in cfg.controles and not isinstance(cfg.controles["cp"], list):

            return False, "controles['cp'] deve ser uma lista"



        # Validar comentarios (pode ser vazio)

        if not isinstance(cfg.comentarios, str):

            return False, "comentarios deve ser string"



        # Validar versao_protocolo (pode ser vazio)

        if not isinstance(cfg.versao_protocolo, str):

            return False, "versao_protocolo deve ser string"



        # Validacao opcional do contrato V2 (retrocompativel).
        pocos_por_amostra = getattr(cfg, "pocos_por_amostra", 1)
        if not isinstance(pocos_por_amostra, int) or pocos_por_amostra not in (1, 2, 3, 4):
            return False, "pocos_por_amostra deve ser inteiro entre 1 e 4"

        targets_por_poco = getattr(cfg, "targets_por_poco", [])
        if not isinstance(targets_por_poco, list):
            return False, "targets_por_poco deve ser uma lista"

        limiares_ct_por_alvo_poco = getattr(cfg, "limiares_ct_por_alvo_poco", [])
        if not isinstance(limiares_ct_por_alvo_poco, list):
            return False, "limiares_ct_por_alvo_poco deve ser uma lista"

        seen_targets: set[tuple[str, int]] = set()
        for item in targets_por_poco:
            if not isinstance(item, dict):
                return False, "targets_por_poco deve conter apenas objetos"
            alvo = str(item.get("alvo", "")).strip()
            filtro = normalize_target_filter(item.get("filtro", ""))
            tipo = normalize_target_type(item.get("tipo", ""))
            poco = item.get("poco")
            if not alvo:
                return False, "targets_por_poco[*].alvo e obrigatorio"
            if not filtro:
                return False, "targets_por_poco[*].filtro e obrigatorio"
            if not tipo:
                return False, "targets_por_poco[*].tipo e obrigatorio"
            if not is_supported_target_filter(filtro):
                return False, f"targets_por_poco[*].filtro nao suportado: {filtro}"
            if not is_supported_target_type(tipo):
                return False, f"targets_por_poco[*].tipo nao suportado: {tipo}"
            if not isinstance(poco, int) or poco < 1 or poco > pocos_por_amostra:
                return False, "targets_por_poco[*].poco fora do intervalo permitido"
            item["filtro"] = filtro
            item["tipo"] = tipo
            item["alvo"] = alvo
            key = (alvo.upper(), poco)
            if key in seen_targets:
                return False, "targets_por_poco contem duplicidade de alvo+poco"
            seen_targets.add(key)

        seen_limiares: set[tuple[str, int]] = set()
        for item in limiares_ct_por_alvo_poco:
            if not isinstance(item, dict):
                return False, "limiares_ct_por_alvo_poco deve conter apenas objetos"
            alvo = str(item.get("alvo", "")).strip()
            poco = item.get("poco")
            ct_min = item.get("ct_minimo")
            ct_detect = item.get("ct_detectavel_limite")
            ct_inconc = item.get("ct_inconclusivo_limite")
            if not alvo:
                return False, "limiares_ct_por_alvo_poco[*].alvo e obrigatorio"
            if not isinstance(poco, int) or poco < 1 or poco > pocos_por_amostra:
                return False, "limiares_ct_por_alvo_poco[*].poco fora do intervalo permitido"
            if not isinstance(ct_min, (int, float)):
                return False, "ct_minimo deve ser numerico"
            if not isinstance(ct_detect, (int, float)):
                return False, "ct_detectavel_limite deve ser numerico"
            if not isinstance(ct_inconc, (int, float)):
                return False, "ct_inconclusivo_limite deve ser numerico"
            if ct_min < 0 or ct_detect < 0 or ct_inconc < 0:
                return False, "limiares CT nao podem ser negativos"
            if not (ct_min <= ct_detect <= ct_inconc):
                return False, "ordem invalida de limiares CT (min <= detectavel <= inconclusivo)"
            seen_limiares.add((alvo.upper(), poco))

        if seen_targets and seen_targets != seen_limiares:
            return False, "cada alvo+poco deve possuir limiares CT correspondentes"

        return True, "Validacao OK"



    def save_exam(self, cfg) -> tuple:

        """

        Salva um ExamConfig em JSON (config/exams/{slug}.json).

        

        Processo:

        1. Valida ExamConfig

        2. Se inválido, retorna (False, mensagem_erro)

        3. Se válido, serializa para dict

        4. Salva em config/exams/{slug}.json

        5. Retorna (True, "Salvo")

        

        Args:

            cfg (ExamConfig): Configuração a salvar

            

        Returns:

            Tuple[bool, str]: (sucesso, mensagem)

            

        Example:

            >>> cfg = ExamConfig(nome_exame="VR1", ...)

            >>> success, msg = editor.save_exam(cfg)

            >>> if success:

            ...     print("Salvo com sucesso!")

        """

        if not self._is_operation_allowed("admin.registry.write"):
            return False, "Acesso negado para salvar exame."

        import json

        from pathlib import Path



        # Validar antes de salvar

        is_valid, validation_msg = self.validate_exam(cfg)

        if not is_valid:

            return False, f"Validação falhou: {validation_msg}"



        try:

            # Converter ExamConfig para dict

            exam_dict = self._exam_to_dict(cfg)



            # Definir caminho de saída

            config_dir = Path(BASE_DIR) / "config" / "exams"

            config_dir.mkdir(parents=True, exist_ok=True)

            json_path = config_dir / f"{cfg.slug}.json"



            # Salvar JSON com indentação para legibilidade

            policy = RetryPolicy.from_env()
            with CSVFileLock(json_path), open_with_retry(
                json_path, "w", encoding="utf-8", policy=policy
            ) as f:

                json.dump(exam_dict, f, indent=2, ensure_ascii=False)



            registrar_log("save_exam", f"Exame salvo: {json_path}", level="INFO")
            
            # NOVO: Sincronizar com arquivos CSV de base
            self._sync_exam_to_csv(cfg)
            
            return True, f"Exame '{cfg.nome_exame}' salvo em {json_path}"



        except Exception as e:

            error_msg = f"Erro ao salvar exame: {str(e)}"

            registrar_log("save_exam", error_msg, level="ERROR")

            return False, error_msg
    
    def _sync_exam_to_csv(self, cfg) -> None:
        """
        Sincroniza um ExamConfig com os arquivos CSV de base.
        
        Garante que o exame exista em exames_config.csv e exames_metadata.csv.
        Se já existir (mesmo nome de exame), atualiza linha.
        Se não existir, insere nova linha.
        
        Campos sincronizados:
            exame        <- cfg.nome_exame
            tipo_placa   <- cfg.tipo_placa_analitica
            numero_kit   <- cfg.kit_codigo
            equipamento  <- cfg.equipamento
            modulo_analise <- padrão: analise.<slug>.analisar_placa
        
        Args:
            cfg: ExamConfig a sincronizar
        """
        import pandas as pd
        from pathlib import Path
        
        try:
            try:
                paths = config_service.get_paths()
                catalog_path = paths.get("exams_catalog_csv")
            except Exception:
                catalog_path = None
            base_dir = Path(catalog_path).parent if catalog_path else Path(BASE_DIR) / "banco_runtime"
            config_path = base_dir / "exames_config.csv"
            meta_path = base_dir / "exames_metadata.csv"
            
            # Definir um módulo de análise padrão (pode ser ajustado manualmente depois)
            modulo_default = f"analise.{cfg.slug}.analisar_placa"
            
            # Dados da linha a inserir/atualizar
            dados_linha = {
                "exame": cfg.nome_exame,
                "modulo_analise": modulo_default,
                "tipo_placa": str(cfg.tipo_placa_analitica),
                "numero_kit": str(cfg.kit_codigo),
                "equipamento": cfg.equipamento,
            }
            
            # Processar cada arquivo CSV
            for path in [config_path, meta_path]:
                policy = RetryPolicy.from_env()
                if path_exists_with_retry(path, policy=policy):
                    df = call_with_retry(
                        lambda: pd.read_csv(path, sep=","),
                        op_name="read_csv",
                        path=path,
                        policy=policy,
                    )
                else:
                    # Criar novo DataFrame com colunas esperadas
                    df = pd.DataFrame(columns=list(dados_linha.keys()))
                
                # Verificar se exame já existe (busca por nome)
                mask = df["exame"].astype(str).str.strip() == cfg.nome_exame.strip()
                
                if mask.any():
                    # Atualiza linha existente
                    for col, val in dados_linha.items():
                        df.loc[mask, col] = val
                    registrar_log(
                        "_sync_exam_to_csv",
                        f"Exame '{cfg.nome_exame}' atualizado em {path.name}",
                        "INFO"
                    )
                else:
                    # Adiciona nova linha
                    df = pd.concat([df, pd.DataFrame([dados_linha])], ignore_index=True)
                    registrar_log(
                        "_sync_exam_to_csv",
                        f"Exame '{cfg.nome_exame}' adicionado em {path.name}",
                        "INFO"
                    )
                
                # Salvar CSV atualizado
                policy = RetryPolicy.from_env()
                with CSVFileLock(path), open_with_retry(
                    path, "w", newline="", encoding="utf-8", policy=policy
                ) as handle:
                    df.to_csv(handle, index=False)
            
            registrar_log(
                "_sync_exam_to_csv",
                f"Sincronização CSV concluída para exame '{cfg.nome_exame}'",
                "INFO"
            )
            
        except Exception as e:
            error_msg = f"Erro ao sincronizar exame com CSV: {str(e)}"
            registrar_log("_sync_exam_to_csv", error_msg, "ERROR")
            # Não levanta exceção - sincronização CSV é opcional/best-effort



    def delete_exam(self, slug_or_key: str) -> tuple:

        """

        Deleta um exame removendo seu arquivo JSON.

        

        Nota: CSVs não são deletados (apenas JSONs são removidos).

        Após deletar, o exame volta Ã  configuração do CSV (se existir).

        

        Args:

            slug_or_key (str): Slug do exame (nome arquivo) OU chave normalizada.

                               Tenta primeiro como chave normalizada do registry.

            

        Returns:

            Tuple[bool, str]: (sucesso, mensagem)

            

        Example:

            >>> success, msg = editor.delete_exam("vr1e2_biomanguinhos_7500")

            >>> if success:

            ...     print("Deletado!")

        """

        if not self._is_operation_allowed("admin.registry.write"):
            return False, "Acesso negado para excluir exame."

        from pathlib import Path



        try:

            # Tentar primeiro como chave normalizada (para compatibilidade com registry.get())

            cfg = self.registry.get(slug_or_key)

            if cfg:

                # Usar o slug do ExamConfig para encontrar o arquivo

                file_slug = cfg.slug

            else:

                # Se não encontrou no registry, usar como slug direto

                file_slug = slug_or_key



            config_dir = Path(BASE_DIR) / "config" / "exams"

            json_path = config_dir / f"{file_slug}.json"



            if json_path.exists():

                json_path.unlink()

                # Remove from active_exams
                from services.core.config_service import config_service
                from services.exam_registry import _norm_exame
                exams_cfg = config_service.get("exams", {})
                if isinstance(exams_cfg, dict):
                    active = exams_cfg.get("active_exams", [])
                    if isinstance(active, list):
                        # Norm target
                        norm_target = _norm_exame(cfg.nome_exame) if cfg else _norm_exame(slug_or_key)
                        new_active = [a for a in active if _norm_exame(a) != norm_target]
                        if len(new_active) != len(active):
                            exams_cfg["active_exams"] = new_active
                            config_service.set("exams", exams_cfg)
                            config_service.save()

                registrar_log("delete_exam", f"Exame deletado: {json_path}", level="INFO")

                return True, "Exame deletado com sucesso"

            else:

                return False, f"Arquivo não encontrado: {json_path}"



        except Exception as e:

            error_msg = f"Erro ao deletar exame: {str(e)}"

            registrar_log("delete_exam", error_msg, level="ERROR")

            return False, error_msg



    def reload_registry(self) -> tuple:

        """

        Recarrega registry do disco (CSV + JSON).

        

        Deve ser chamado após salvar/deletar exames para sincronizar UI.

        

        Returns:

            Tuple[bool, str]: (sucesso, mensagem)

            

        Example:

            >>> # Após save_exam():

            >>> success, msg = editor.reload_registry()

            >>> if success:

            ...     print("Registry recarregado!")

        """

        try:

            self.registry.load()

            registrar_log("reload_registry", "Registry recarregado", level="INFO")

            return True, "Registry recarregado com sucesso"

        except Exception as e:

            error_msg = f"Erro ao recarregar registry: {str(e)}"

            registrar_log("reload_registry", error_msg, level="ERROR")

            return False, error_msg



    def _exam_to_dict(self, cfg) -> dict:

        """

        Converte ExamConfig para dict para serialização em JSON.

        

        Args:

            cfg (ExamConfig): Configuração a converter

            

        Returns:

            dict: Representação JSON-ready do exame

            

        Example:

            >>> exam_dict = editor._exam_to_dict(cfg)

            >>> json.dump(exam_dict, f)

        """

        return {

            "nome_exame": cfg.nome_exame,

            "slug": cfg.slug,

            "equipamento": cfg.equipamento,

            "tipo_placa_analitica": cfg.tipo_placa_analitica,

            "esquema_agrupamento": cfg.esquema_agrupamento,

            "kit_codigo": cfg.kit_codigo,

            "alvos": cfg.alvos,

            "mapa_alvos": cfg.mapa_alvos,

            "faixas_ct": cfg.faixas_ct,

            "rps": cfg.rps,

            "export_fields": cfg.export_fields,

            "panel_tests_id": cfg.panel_tests_id,

            "controles": cfg.controles,

            "comentarios": cfg.comentarios,

            "versao_protocolo": cfg.versao_protocolo,
            "pocos_por_amostra": int(getattr(cfg, "pocos_por_amostra", 1) or 1),
            "targets_por_poco": getattr(cfg, "targets_por_poco", []) or [],
            "limiares_ct_por_alvo_poco": getattr(cfg, "limiares_ct_por_alvo_poco", []) or [],

        }



    def _generate_slug(self, nome_exame: str) -> str:

        """

        Gera slug a partir de nome_exame, garantindo correspondência com _norm_exame().

        

        Normaliza: lowercase, remove acentos, substitui espaços/hífens por underscores.

        

        Args:

            nome_exame (str): Nome do exame

            

        Returns:

            str: Slug (ex: "teste_covid_19")

            

        Example:

            >>> editor._generate_slug("Teste COVID-19")

            >>> "teste_covid_19"  # Acentos removidos, espaço e hífen â†’ underscores

        """

        import unicodedata

        

        # Normalizar como o registry faz

        normalized = str(nome_exame).strip().lower()

        

        # Remover acentos (NFKD + ASCII)

        normalized = unicodedata.normalize('NFKD', normalized)

        normalized = normalized.encode('ASCII', 'ignore').decode('ASCII')

        

        # Substituir espaços e hífens por underscores

        slug = normalized.replace(" ", "_").replace("-", "_")

        return slug

