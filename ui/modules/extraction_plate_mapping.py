# -*- coding: utf-8 -*-
"""
Pagina de mapeamento da placa de extracao com preview visual 8x12.

Adaptado para a arquitetura Single Window (ModuleHost).
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import customtkinter as ctk

from application.extraction_plate_mapping_use_case import (
    ExtractionMappingResult,
    build_extraction_mapping,
)
from ui.theme import Theme

_ROWS_LABELS = list("ABCDEFGH")
_LINHAS_GRID = _ROWS_LABELS

_KIT_PARTES = {"96": 1, "48": 2, "32": 3, "24": 4}

_COR_PREENCHIDA = Theme.PRIMARY_BLUE
_COR_VAZIA = Theme.BG_ROOT
_COR_VALIDO = Theme.COLOR_SUCCESS

def _construir_df_mapeamento(file_result: Any, kit: str, parte: int):
    """Compatibility wrapper returning the base mapping DataFrame."""
    return build_extraction_mapping(file_result.df_bloco, kit, parte).mapeamento


class ExtractionPlateMappingPageEmbedded(ctk.CTkFrame):
    """View embutida de mapeamento da placa."""

    def __init__(self, parent: Any, main_window: Any) -> None:
        super().__init__(parent, fg_color="transparent")
        self.main_window = main_window

        self.resultado: Optional[Dict] = None
        self._file_result = None
        self._mapping_result: Optional[ExtractionMappingResult] = None
        self._df_map = None
        self._grid_cells: Dict[str, Any] = {}

        self._kit_var = ctk.StringVar(value="96")
        self._parte_var = ctk.StringVar(value="1")
        self._status_var = ctk.StringVar(value="Nenhum arquivo selecionado.")

        self._build()

    def _build(self) -> None:
        # Título da view
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(
            header,
            text="Configuração de Mapeamento de Placa",
            font=Theme.get_font_primary(size=24, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(side="left")

        # Container principal de duas colunas
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True)
        content_frame.grid_columnconfigure(0, weight=1, minsize=300)
        content_frame.grid_columnconfigure(1, weight=2, minsize=450)
        content_frame.grid_rowconfigure(0, weight=1)

        # Coluna Esquerda (Passos 1 e 2)
        left_col = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Passo 1 Card
        from ui.components.cards import ContentCard
        step1_card = ContentCard(left_col)
        step1_card.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            step1_card, text="Passo 1: Upload de Dados da Placa",
            font=Theme.get_font_primary(size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w", padx=20, pady=(20, 10))
        
        row_arquivo = ctk.CTkFrame(step1_card, fg_color="transparent")
        row_arquivo.pack(fill="x", padx=20, pady=10)
        
        from ui.components.buttons import PrimaryButton
        PrimaryButton(
            row_arquivo, text="Upload Excel File", command=self._selecionar_arquivo, width=180
        ).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(row_arquivo, textvariable=self._status_var, font=Theme.get_font_primary(size=12), text_color=Theme.TEXT_PRIMARY).pack(side="left")

        row_kit = ctk.CTkFrame(step1_card, fg_color="transparent")
        row_kit.pack(fill="x", padx=20, pady=(10, 20))
        ctk.CTkLabel(row_kit, text="Tipo de Placa:", width=80, anchor="w", font=Theme.get_font_primary(size=13, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(side="left")
        for kit_opt in ("96", "48", "32", "24"):
            ctk.CTkRadioButton(
                row_kit, text=f"{kit_opt} wells", variable=self._kit_var, value=kit_opt,
                command=self._atualizar_partes, font=Theme.get_font_primary(size=12), text_color=Theme.TEXT_PRIMARY
            ).pack(side="left", padx=8)

        # Passo 2 Card
        self.step2_card = ContentCard(left_col)
        self.step2_card.pack(fill="x")
        
        ctk.CTkLabel(
            self.step2_card, text="Passo 2: Seleção de Placa",
            font=Theme.get_font_primary(size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w", padx=20, pady=(20, 10))
        
        self._row_parte = ctk.CTkFrame(self.step2_card, fg_color="transparent")
        self._row_parte.pack(fill="x", padx=20, pady=(10, 20))
        
        self._parte_label = ctk.CTkLabel(self._row_parte, text="Parte:", width=80, anchor="w", font=Theme.get_font_primary(size=13, weight="bold"), text_color=Theme.TEXT_PRIMARY)
        self._parte_label.pack(side="left")
        self._parte_radios_frame = ctk.CTkFrame(self._row_parte, fg_color="transparent")
        self._parte_radios_frame.pack(side="left")
        self._atualizar_partes()

        # Coluna Direita (Passo 3)
        right_col = ctk.CTkFrame(content_frame, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        step3_card = ContentCard(right_col)
        step3_card.pack(fill="both", expand=True)

        ctk.CTkLabel(
            step3_card, text="Passo 3: Pré-visualização do Mapeamento de Placa",
            font=Theme.get_font_primary(size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor="w", padx=20, pady=(20, 10))

        self._grid_frame = ctk.CTkFrame(step3_card, fg_color="transparent")
        self._grid_frame.pack(pady=10, padx=20)
        self._construir_grid_vazio()

        self._txt = ctk.CTkTextbox(
            step3_card, wrap="none", height=100,
            font=ctk.CTkFont(family="Courier New", size=11),
            fg_color=Theme.BG_ROOT, border_width=1, border_color=Theme.BORDER_DEFAULT,
            text_color=Theme.TEXT_PRIMARY
        )
        self._txt.pack(fill="both", expand=True, padx=20, pady=10)
        self._txt.insert("0.0", "Select a file to preview mapping.")
        self._txt.configure(state="disabled")

        # Botões de Ação na parte inferior direita
        btn_bar = ctk.CTkFrame(step3_card, fg_color="transparent")
        btn_bar.pack(fill="x", padx=20, pady=20)
        
        from ui.components.buttons import SecondaryButton
        SecondaryButton(btn_bar, text="Atualizar Pré-visualização", command=self._gerar).pack(side="left", padx=(0, 10))
        SecondaryButton(btn_bar, text="Editar Mapeamento", command=self._abrir_editor).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(
            btn_bar, text="Prosseguir para a Análise da Corrida", command=self._confirmar, fg_color=Theme.COLOR_SUCCESS, hover_color="#059669",
            font=Theme.get_font_primary(size=13, weight="bold"), text_color="#000000"
        ).pack(side="right", padx=(10, 0))
        
        ctk.CTkButton(
            btn_bar, text="Cancelar", command=self._cancelar, fg_color="transparent", border_width=1, border_color=Theme.BORDER_DEFAULT,
            text_color=Theme.TEXT_PRIMARY, hover_color=Theme.BG_ROOT,
            font=Theme.get_font_primary(size=13, weight="bold")
        ).pack(side="right")

    def _construir_grid_vazio(self) -> None:
        for widget in self._grid_frame.winfo_children():
            widget.destroy()
        self._grid_cells = {}

        ctk.CTkLabel(self._grid_frame, text="", width=20).grid(row=0, column=0, sticky="nsew")
        for col in range(1, 13):
            self._grid_frame.grid_columnconfigure(col, weight=1)
            ctk.CTkLabel(
                self._grid_frame,
                text=str(col),
                font=Theme.get_font_primary(weight="bold", size=10),
                text_color="black"
            ).grid(row=0, column=col, padx=1, sticky="nsew")

        for row_index, row_label in enumerate(_LINHAS_GRID, 1):
            self._grid_frame.grid_rowconfigure(row_index, weight=1)
            ctk.CTkLabel(
                self._grid_frame,
                text=row_label,
                font=Theme.get_font_primary(weight="bold", size=10),
                text_color="black"
            ).grid(row=row_index, column=0, pady=1, sticky="nsew")
            for col in range(1, 13):
                poco = f"{row_label}{col}"
                cell = ctk.CTkLabel(
                    self._grid_frame,
                    text=poco,
                    fg_color=_COR_VAZIA,
                    text_color="black",
                    corner_radius=2,
                    width=35,
                    height=25,
                    font=Theme.get_font_primary(size=9, weight="bold"),
                )
                cell.grid(row=row_index, column=col, padx=1, pady=1, sticky="nsew")
                self._grid_cells[poco] = cell

    def _atualizar_partes(self) -> None:
        for widget in self._parte_radios_frame.winfo_children():
            widget.destroy()

        kit = self._kit_var.get()
        n_partes = _KIT_PARTES.get(kit, 1)
        
        # Garante que a linha esteja visível usando pack (já que foi criada com pack)
        try:
            self._row_parte.pack(fill="x", padx=20, pady=(10, 20))
        except Exception:
            pass

        self._parte_var.set("1")
        for parte in range(1, n_partes + 1):
            rb = ctk.CTkRadioButton(
                self._parte_radios_frame,
                text=f"Part {parte} {'(Full Plate)' if n_partes == 1 else ''}",
                variable=self._parte_var,
                value=str(parte),
                command=self._recalcular_preview,
                font=Theme.get_font_primary(size=12),
                text_color=Theme.TEXT_PRIMARY
            )
            rb.pack(side="left", padx=8)
                
        self._recalcular_preview()

    def _selecionar_arquivo(self) -> None:
        from application.equipment_extraction_use_case import ExtractionUseCase
        from services.tk_file_chooser import TkFileChooser

        uc = ExtractionUseCase(file_chooser=TkFileChooser())
        file_result = uc.executar()
        if file_result is None:
            return
        self._file_result = file_result
        nome = file_result.caminho_arquivo.name
        num = file_result.numero_extracao or ""
        label = f"{nome}" + (f"  [Extração: {num}]" if num else "")
        self._status_var.set(label)
        self._recalcular_preview(show_errors=True)

    def _gerar(self) -> None:
        if self._file_result is None:
            from tkinter import messagebox
            messagebox.showwarning("Aviso", "Selecione um arquivo primeiro.", parent=self.main_window)
            return
        self._recalcular_preview(show_errors=True)

    def _recalcular_preview(self, show_errors: bool = False) -> None:
        if self._file_result is None:
            return

        kit = self._kit_var.get()
        parte = int(self._parte_var.get() or "1")

        try:
            self._mapping_result = build_extraction_mapping(
                self._file_result.df_bloco,
                kit,
                parte,
            )
            self._df_map = self._mapping_result.mapeamento.copy()
        except Exception as exc:
            self._mapping_result = None
            self._df_map = None
            if show_errors:
                from tkinter import messagebox
                messagebox.showerror("Erro", str(exc), parent=self.main_window)
            return

        self._atualizar_grid()
        self._atualizar_texto()

    def _atualizar_grid(self) -> None:
        if self._df_map is None:
            return

        poco_to_amostra: Dict[str, tuple] = {}
        for _, row in self._df_map.iterrows():
            sample = str(row.get("Amostra", ""))
            tem_valor = bool(sample and sample.strip().lower() not in ("nan", ""))
            poco_analise = row.get("Poco_Analise", None)
            if isinstance(poco_analise, (tuple, list)):
                pocos = [str(p) for p in poco_analise]
            else:
                pocos = [str(row.get("Poco", ""))]
            for poco in pocos:
                poco_to_amostra[poco] = (sample, tem_valor)

        for poco, cell in self._grid_cells.items():
            amostra, tem_valor = poco_to_amostra.get(poco, (poco, False))
            
            # Trunca o texto da amostra para caber na celula de width=35
            texto_exibicao = amostra
            if tem_valor:
                texto_exibicao = amostra[:4] + ".." if len(amostra) > 6 else amostra
                
            cell.configure(
                text=texto_exibicao if tem_valor else poco,
                fg_color=_COR_PREENCHIDA if tem_valor else _COR_VAZIA,
                text_color="white" if tem_valor else "black",
            )

    def _atualizar_texto(self) -> None:
        if self._mapping_result is None or self._df_map is None:
            return

        bloco = self._mapping_result.bloco_fatiado
        cols = [c for c in ["Poco", "Amostra", "Codigo"] if c in self._df_map.columns]
        texto = (
            "Planilha de extração (colunas 1-12, linhas A-H):\n"
            f"{bloco.to_string()}\n\n"
            "Mapeamento:\n"
            f"{self._df_map[cols].to_string(index=False)}"
        )
        self._txt.configure(state="normal")
        self._txt.delete("0.0", "end")
        self._txt.insert("0.0", texto)
        self._txt.configure(state="disabled")

    def _abrir_editor(self) -> None:
        if self._df_map is None:
            from tkinter import messagebox
            messagebox.showwarning(
                "Aviso", "Gere o mapeamento antes de editar.", parent=self.main_window
            )
            return

        import tkinter as tk
        edit_win = ctk.CTkToplevel(self.main_window)
        edit_win.title("Editar Mapeamento")
        edit_win.geometry("620x500")
        edit_win.transient(self.main_window)
        edit_win.grab_set()

        edit_win.update_idletasks()
        sw = edit_win.winfo_screenwidth()
        sh = edit_win.winfo_screenheight()
        edit_win.geometry(f"+{sw // 2 - 310}+{sh // 2 - 250}")

        btnf = ctk.CTkFrame(edit_win)
        btnf.pack(side="bottom", fill="x", padx=10, pady=(0, 8))

        scroll_frame = ctk.CTkFrame(edit_win)
        scroll_frame.pack(side="top", fill="both", expand=True, padx=10, pady=(8, 0))

        canvas = tk.Canvas(scroll_frame, highlightthickness=0, bg=Theme.BG_ROOT)
        vsb = tk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = ctk.CTkFrame(canvas)
        cw_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        header_font = ctk.CTkFont(weight="bold")
        ctk.CTkLabel(inner, text="Poço", width=70, font=header_font).grid(
            row=0, column=0, padx=6, pady=6
        )
        ctk.CTkLabel(inner, text="Amostra", width=220, font=header_font).grid(
            row=0, column=1, padx=6, pady=6
        )
        ctk.CTkLabel(inner, text="Código", width=220, font=header_font).grid(
            row=0, column=2, padx=6, pady=6
        )

        df_edit = self._df_map[["Poco", "Amostra", "Codigo"]].reset_index(drop=True)
        entries_amostra: list = []
        entries_codigo: list = []

        for idx in range(len(df_edit)):
            row = df_edit.iloc[idx]
            ctk.CTkLabel(inner, text=str(row["Poco"]), width=70).grid(
                row=idx + 1, column=0, padx=6, pady=2
            )
            val_a = str(row["Amostra"]) if str(row["Amostra"]).lower() not in ("nan", "none") else ""
            ent_a = ctk.CTkEntry(inner, width=220)
            ent_a.insert(0, val_a)
            ent_a.grid(row=idx + 1, column=1, padx=6, pady=2)

            val_c = str(row["Codigo"]) if str(row["Codigo"]).lower() not in ("nan", "none") else ""
            ent_c = ctk.CTkEntry(inner, width=220)
            ent_c.insert(0, val_c)
            ent_c.grid(row=idx + 1, column=2, padx=6, pady=2)

            entries_amostra.append(ent_a)
            entries_codigo.append(ent_c)

        def _on_inner_configure(event: Any) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event: Any) -> None:
            canvas.itemconfig(cw_id, width=event.width)

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event: Any) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _salvar() -> None:
            n = len(entries_amostra)
            for i in range(n):
                novo_a = entries_amostra[i].get()
                novo_c = entries_codigo[i].get()
                self._df_map.at[i, "Amostra"] = novo_a
                self._df_map.at[i, "Codigo"] = novo_c
                if "Poço" in self._df_map.columns:
                    pass
                if "Código" in self._df_map.columns:
                    self._df_map.at[i, "Código"] = novo_c
            self._atualizar_grid()
            self._atualizar_texto()
            try:
                canvas.unbind_all("<MouseWheel>")
                edit_win.grab_release()
            except Exception:
                pass
            edit_win.destroy()
            self.main_window.after(50, self.main_window.focus_force)

        def _cancelar_edit() -> None:
            try:
                canvas.unbind_all("<MouseWheel>")
                edit_win.grab_release()
            except Exception:
                pass
            edit_win.destroy()
            self.main_window.after(50, self.main_window.focus_force)

        ctk.CTkButton(
            btnf, text="Salvar", command=_salvar, fg_color=Theme.COLOR_SUCCESS
        ).pack(side="left", expand=True, padx=6)
        ctk.CTkButton(
            btnf, text="Cancelar", command=_cancelar_edit, fg_color="gray"
        ).pack(side="left", expand=True, padx=6)

    def _confirmar(self) -> None:
        if self._df_map is None or self._file_result is None:
            from tkinter import messagebox
            messagebox.showwarning(
                "Aviso", "Selecione um arquivo válido antes de confirmar.", parent=self.main_window
            )
            return

        if "Poço" not in self._df_map.columns:
            self._df_map["Poço"] = self._df_map["Poco"]
        if "Código" not in self._df_map.columns:
            self._df_map["Código"] = self._df_map["Codigo"]

        parte = self._mapping_result.parte if self._mapping_result else int(self._parte_var.get() or "1")

        # Atualiza o estado global com os resultados do mapeamento
        self.main_window.app_state.dados_extracao = self._df_map
        self.main_window.app_state.parte_placa = parte
        self.main_window.app_state.numero_extracao = self._file_result.numero_extracao
        self.main_window.app_state.caminho_arquivo_extracao = str(self._file_result.caminho_arquivo)

        from tkinter import messagebox
        messagebox.showinfo("Sucesso", "Extração carregada com sucesso!", parent=self.main_window)
        self.main_window.update_status("Mapeamento carregado. Clique em 'Realizar Análise' para continuar.")
        
        # Avançar para Análise
        if hasattr(self.main_window, "navigation_manager"):
            if hasattr(self.main_window, "menu_handler"):
                self.main_window.menu_handler.set_active_menu("Realizar Análise")
                if hasattr(self.main_window, "topbar_breadcrumbs"):
                    self.main_window.topbar_breadcrumbs.configure(text="Realizar Análise")
            self.main_window.navigation_manager.navigate_to("analise_setup")

    def _cancelar(self) -> None:
        self.main_window.update_status("Mapeamento cancelado.")
        if hasattr(self.main_window, "navigation_manager"):
            self.main_window.navigation_manager.navigate_to("main_menu")


def create_extraction_mapping_page(parent: Any, main_window: Any) -> Any:
    """Factory method for NavigationManager."""
    page = ExtractionPlateMappingPageEmbedded(parent, main_window)
    return page

def abrir_mapeamento_extracao(parent: Any) -> Optional[Dict]:
    """Modal de mapeamento de compatibilidade (nao mais utilizado ativamente, mantido caso algo dependa)."""
    # Apenas retorna None se invocado no modo legado para evitar crash.
    from tkinter import messagebox
    messagebox.showwarning("Aviso", "Esta janela foi migrada para o modo embutido.", parent=parent)
    return None
