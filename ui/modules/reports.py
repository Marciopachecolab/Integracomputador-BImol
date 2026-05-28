# -*- coding: utf-8 -*-
"""Modulo de Relatorios - IntegRAGal.

Tela somente leitura para consultas gerenciais e operacionais sobre
analises, execucoes e envio ao GAL.  Nao calcula CT nem Resultado_geral.
"""

from __future__ import annotations

import calendar
import math
from datetime import date, timedelta, datetime
from pathlib import Path
from tkinter import ttk
from typing import Any, Optional

import customtkinter as ctk

from ui.modules.estilos import CORES, FONTES
from utils.logger import registrar_log

# ---------------------------------------------------------------------------
# Constantes puras (testáveis sem display)
# ---------------------------------------------------------------------------

PAGE_SIZE = 50

_ACTIVE_EXAMS_FALLBACK = ("VR1e2 Biomanguinhos 7500", "ZDC BioManguinhos")

_GAL_STATUS_LABELS = {
    "enviado": "Enviado",
    "nao_enviado": "Nao Enviado",
    "erro": "Erro",
    "duplicado": "Duplicado",
    "nao_enviavel": "N/A",
    "sem_chave_gal": "Sem Chave",
}

_POSITIVIDADE_LABELS = {
    "positivo": "Positivo",
    "negativo": "Negativo",
    "inconclusivo": "Inconclusivo",
    "invalido": "Invalido",
    "detectavel": "Detectavel",
    "nao_detectavel": "Nao Detectavel",
    "indeterminado": "Indeterminado",
}

_GAL_TAG_COLORS = {
    "enviado": "#1B5E20",
    "nao_enviado": "#616161",
    "erro": "#B71C1C",
    "duplicado": "#E65100",
    "sem_chave_gal": "#9E9E9E",
    "nao_enviavel": "#9E9E9E",
}


def _gal_status_display(status: str) -> str:
    """Converte status GAL interno para texto de exibicao."""
    return _GAL_STATUS_LABELS.get(status, status)


def _page_count(total: int, page_size: int) -> int:
    """Calcula numero de paginas para paginacao."""
    if total <= 0 or page_size <= 0:
        return 0
    return math.ceil(total / page_size)


# ---------------------------------------------------------------------------
# Componente de Calendário Simples
# ---------------------------------------------------------------------------
class SimpleCalendar(ctk.CTkToplevel):
    def __init__(self, parent, target_entry):
        super().__init__(parent)
        self.title("Selecionar Data")
        self.geometry("280x300")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        
        self.target_entry = target_entry
        
        # Determine initial date
        current_text = target_entry.get().strip()
        try:
            self.current_date = datetime.strptime(current_text, "%Y-%m-%d").date()
        except ValueError:
            self.current_date = date.today()
            
        self.year = self.current_date.year
        self.month = self.current_date.month
        
        # Make the window modal
        self.transient(parent)
        self.grab_set()
        
        self._build_ui()
        
    def _build_ui(self):
        for widget in self.winfo_children():
            widget.destroy()
            
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=10, padx=10)
        
        ctk.CTkButton(header, text="<", width=30, command=self._prev_month).pack(side="left")
        
        lbl_month = ctk.CTkLabel(header, text=f"{calendar.month_name[self.month]} {self.year}", font=FONTES["corpo_bold"])
        lbl_month.pack(side="left", expand=True)
        
        ctk.CTkButton(header, text=">", width=30, command=self._next_month).pack(side="right")
        
        days_frame = ctk.CTkFrame(self, fg_color="transparent")
        days_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        days = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        for i, day in enumerate(days):
            ctk.CTkLabel(days_frame, text=day, font=FONTES["corpo"]).grid(row=0, column=i, padx=2, pady=2)
            
        cal = calendar.monthcalendar(self.year, self.month)
        for row, week in enumerate(cal):
            for col, day in enumerate(week):
                if day != 0:
                    is_today = (day == date.today().day and self.month == date.today().month and self.year == date.today().year)
                    is_selected = (day == self.current_date.day and self.month == self.current_date.month and self.year == self.current_date.year)
                    
                    fg_color = CORES["primaria"] if is_selected else ("transparent" if not is_today else CORES["secundaria"])
                    text_color = CORES["branco"] if (is_selected or is_today) else CORES["texto"]
                    
                    btn = ctk.CTkButton(
                        days_frame, text=str(day), width=30, height=30,
                        fg_color=fg_color,
                        text_color=text_color,
                        hover_color=CORES["primaria_hover"],
                        command=lambda d=day: self._select_date(d)
                    )
                    btn.grid(row=row+1, column=col, padx=2, pady=2)
                    
    def _prev_month(self):
        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1
        self._build_ui()
        
    def _next_month(self):
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1
        self._build_ui()
        
    def _select_date(self, day):
        selected = date(self.year, self.month, day)
        self.target_entry.delete(0, "end")
        self.target_entry.insert(0, selected.isoformat())
        self.destroy()

# ---------------------------------------------------------------------------
# Widget principal
# ---------------------------------------------------------------------------

class ReportsModule(ctk.CTkFrame):
    """Tela de relatorios com filtros, resumo, tabela detalhada e paginacao."""

    def __init__(
        self,
        master: Any,
        *,
        app_state: Any = None,
        on_close_callback=None,
    ) -> None:
        super().__init__(master)
        self.pack(expand=True, fill="both")

        self._app_state = app_state
        self._on_close_callback = on_close_callback
        self._closing = False
        self._current_page = 0
        self._total_results = 0
        self._use_case = self._build_use_case()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._criar_header()
        self._criar_filtros()
        self._criar_resumo()
        self._criar_tabela()
        self._criar_rodape()

    # ------------------------------------------------------------------
    # Construção de dependências
    # ------------------------------------------------------------------

    def _active_exams(self) -> tuple[str, ...]:
        if self._app_state is not None:
            try:
                from services.exam_registry import ExamRegistry
                reg = getattr(self._app_state, "exam_registry", None)
                if reg is not None:
                    names = [e for e in reg.iter_active_exams()]
                    if names:
                        return tuple(names)
            except Exception:
                pass
        return _ACTIVE_EXAMS_FALLBACK

    def _build_use_case(self):
        try:
            from application.reports_query_use_case import ReportsQueryUseCase
            from services.persistence.exam_runs_sqlite import default_exam_runs_db_path
            from services.gal.gal_transactions import default_transaction_journal_path
            from services.reports.reports_repository import ReportsSQLiteRepository

            db_path = default_exam_runs_db_path()
            journal_path = default_transaction_journal_path()
            return ReportsQueryUseCase(ReportsSQLiteRepository(db_path), journal_path)
        except Exception as exc:
            registrar_log("ReportsModule", f"Erro ao inicializar use case: {exc}", "ERROR")
            return None

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _criar_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=CORES["primaria"], corner_radius=0, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        header.grid_propagate(False)

        ctk.CTkLabel(
            header, text="Relatorios", font=FONTES["titulo"], text_color=CORES["branco"]
        ).grid(row=0, column=0, padx=(30, 10), pady=10, sticky="w")

        self._lbl_header_count = ctk.CTkLabel(
            header, text="", font=FONTES["corpo"], text_color=CORES["branco"]
        )
        self._lbl_header_count.grid(row=0, column=1, padx=10, sticky="w")

        ctk.CTkButton(
            header, text="X", width=36, height=36,
            fg_color="transparent", hover_color=CORES["primaria_escuro"],
            command=self._on_close, font=("Arial", 14, "bold"),
        ).grid(row=0, column=2, padx=(10, 20))

    def _criar_filtros(self) -> None:
        frame = ctk.CTkFrame(
            self, fg_color=CORES["fundo_card"], corner_radius=8,
            border_width=1, border_color=CORES["borda"],
        )
        frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(12, 4))
        for c in range(8):
            frame.grid_columnconfigure(c, weight=1)

        def _lbl(parent, text):
            return ctk.CTkLabel(parent, text=text, font=FONTES["corpo"], text_color=CORES["texto_secundario"])

        today = date.today()
        inicio = (today - timedelta(days=30)).isoformat()
        fim = today.isoformat()

        # Linha 0: datas + exame + positividade + status_gal
        _lbl(frame, "Data inicio").grid(row=0, column=0, padx=(14, 2), pady=(10, 2), sticky="w")
        self._ent_inicio = ctk.CTkEntry(frame, width=110, placeholder_text="YYYY-MM-DD")
        self._ent_inicio.insert(0, inicio)
        self._ent_inicio.grid(row=1, column=0, padx=(14, 4), pady=(0, 10), sticky="ew")
        self._ent_inicio.bind("<Button-1>", lambda e: SimpleCalendar(self.winfo_toplevel(), self._ent_inicio))

        _lbl(frame, "Data fim").grid(row=0, column=1, padx=(4, 2), pady=(10, 2), sticky="w")
        self._ent_fim = ctk.CTkEntry(frame, width=110, placeholder_text="YYYY-MM-DD")
        self._ent_fim.insert(0, fim)
        self._ent_fim.grid(row=1, column=1, padx=(4, 4), pady=(0, 10), sticky="ew")
        self._ent_fim.bind("<Button-1>", lambda e: SimpleCalendar(self.winfo_toplevel(), self._ent_fim))

        _lbl(frame, "Exame").grid(row=0, column=2, padx=(4, 2), pady=(10, 2), sticky="w")
        exame_opts = ["Todos"] + list(self._active_exams())
        self._cmb_exame = ctk.CTkComboBox(frame, values=exame_opts, width=190)
        self._cmb_exame.set("Todos")
        self._cmb_exame.grid(row=1, column=2, padx=(4, 4), pady=(0, 10), sticky="ew")

        _lbl(frame, "Positividade").grid(row=0, column=3, padx=(4, 2), pady=(10, 2), sticky="w")
        pos_opts = ["Todos", "positivo", "negativo", "inconclusivo", "invalido"]
        self._cmb_pos = ctk.CTkComboBox(frame, values=pos_opts, width=130)
        self._cmb_pos.set("Todos")
        self._cmb_pos.grid(row=1, column=3, padx=(4, 4), pady=(0, 10), sticky="ew")

        _lbl(frame, "Status GAL").grid(row=0, column=4, padx=(4, 2), pady=(10, 2), sticky="w")
        gal_opts = ["Todos", "enviado", "nao_enviado", "erro", "duplicado", "sem_chave_gal"]
        self._cmb_gal = ctk.CTkComboBox(frame, values=gal_opts, width=130)
        self._cmb_gal.set("Todos")
        self._cmb_gal.grid(row=1, column=4, padx=(4, 4), pady=(0, 10), sticky="ew")

        _lbl(frame, "Analista").grid(row=0, column=5, padx=(4, 2), pady=(10, 2), sticky="w")
        self._ent_analista = ctk.CTkEntry(frame, width=100, placeholder_text="qualquer")
        self._ent_analista.grid(row=1, column=5, padx=(4, 4), pady=(0, 10), sticky="ew")

        _lbl(frame, "Kit").grid(row=0, column=6, padx=(4, 2), pady=(10, 2), sticky="w")
        self._ent_kit = ctk.CTkEntry(frame, width=90, placeholder_text="qualquer")
        self._ent_kit.grid(row=1, column=6, padx=(4, 4), pady=(0, 10), sticky="ew")

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=0, column=7, rowspan=2, padx=(4, 14), pady=10, sticky="e")

        ctk.CTkButton(
            btn_frame, text="Buscar", width=90,
            fg_color=CORES["primaria"], hover_color=CORES["primaria_hover"],
            command=self._buscar_primeira_pagina,
        ).pack(side="top", pady=(0, 6))

        ctk.CTkButton(
            btn_frame, text="Limpar", width=90,
            fg_color=CORES["borda"], hover_color=CORES["fundo_escuro"],
            text_color=CORES["texto"], command=self._limpar_filtros,
        ).pack(side="top")

    def _criar_resumo(self) -> None:
        frame = ctk.CTkFrame(
            self, fg_color=CORES["fundo_card"], corner_radius=8,
            border_width=1, border_color=CORES["borda"], height=68,
        )
        frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 4))
        frame.grid_propagate(False)

        self._cards: dict[str, ctk.CTkLabel] = {}
        defs = [
            ("total", "Total", CORES["primaria"]),
            ("positivos", "Positivos", CORES["secundaria"]),
            ("negativos", "Negativos", CORES["texto_secundario"]),
            ("inconclusivos", "Inconclusivos", CORES["aviso"]),
            ("invalidos", "Invalidos", CORES["erro"]),
        ]
        for i, (key, label, color) in enumerate(defs):
            sub = ctk.CTkFrame(frame, fg_color="transparent")
            sub.pack(side="left", expand=True, padx=12, pady=8)
            ctk.CTkLabel(sub, text=label, font=FONTES["corpo"], text_color=CORES["texto_secundario"]).pack()
            lbl = ctk.CTkLabel(sub, text="–", font=FONTES["subtitulo"], text_color=color)
            lbl.pack()
            self._cards[key] = lbl

    def _criar_tabela(self) -> None:
        self._frame_tabela = ctk.CTkFrame(
            self, fg_color=CORES["fundo_card"], corner_radius=8,
            border_width=1, border_color=CORES["borda"],
        )
        self._frame_tabela.grid(row=3, column=0, sticky="nsew", padx=16, pady=4)
        self._frame_tabela.grid_columnconfigure(0, weight=1)
        self._frame_tabela.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure(
            "Reports.Treeview",
            background=CORES["branco"], foreground=CORES["texto"],
            rowheight=28, fieldbackground=CORES["branco"], font=FONTES["corpo"],
        )
        style.configure(
            "Reports.Treeview.Heading",
            font=FONTES["corpo_bold"], background=CORES["primaria"],
            foreground=CORES["branco"], relief="flat",
        )
        style.map("Reports.Treeview", background=[("selected", CORES["primaria"])],
                  foreground=[("selected", CORES["branco"])])

        sy = ttk.Scrollbar(self._frame_tabela, orient="vertical")
        sx = ttk.Scrollbar(self._frame_tabela, orient="horizontal")

        cols = ("data", "exame", "amostra", "resultado", "status_gal", "analista", "kit", "lote")
        self.tree = ttk.Treeview(
            self._frame_tabela, columns=cols, show="headings",
            yscrollcommand=sy.set, xscrollcommand=sx.set,
            style="Reports.Treeview",
        )
        hdrs = {
            "data": ("Data", 95, "center"),
            "exame": ("Exame", 180, "w"),
            "amostra": ("Amostra", 100, "center"),
            "resultado": ("Resultado", 140, "w"),
            "status_gal": ("Status GAL", 100, "center"),
            "analista": ("Analista", 90, "center"),
            "kit": ("Kit", 80, "center"),
            "lote": ("Lote", 110, "center"),
        }
        for col, (text, width, anchor) in hdrs.items():
            self.tree.heading(col, text=text, command=lambda c=col: self._sort_treeview(c, False))
            self.tree.column(col, width=width, anchor=anchor, minwidth=60)

        for status, color in _GAL_TAG_COLORS.items():
            self.tree.tag_configure(status, foreground=color)

        sy.config(command=self.tree.yview)
        sx.config(command=self.tree.xview)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        sy.grid(row=0, column=1, sticky="ns", pady=8)
        sx.grid(row=1, column=0, sticky="ew", padx=8)

        # Estado vazio
        self._frame_vazio = ctk.CTkFrame(self._frame_tabela, fg_color="transparent")
        ctk.CTkLabel(
            self._frame_vazio,
            text="Nenhum resultado. Aplique os filtros e clique em Buscar.",
            font=FONTES["subtitulo_normal"],
            text_color=CORES["texto_secundario"],
        ).pack(expand=True)

        # Estado de erro
        self._frame_erro = ctk.CTkFrame(self._frame_tabela, fg_color="transparent")
        self._lbl_erro = ctk.CTkLabel(
            self._frame_erro, text="", font=FONTES["corpo"], text_color=CORES["erro"]
        )
        self._lbl_erro.pack(expand=True, padx=20)

        self._mostrar_estado("vazio")

    def _criar_rodape(self) -> None:
        rodape = ctk.CTkFrame(
            self, fg_color=CORES["fundo_card"], corner_radius=8,
            border_width=1, border_color=CORES["borda"], height=46,
        )
        rodape.grid(row=4, column=0, sticky="ew", padx=16, pady=(4, 14))
        rodape.grid_columnconfigure(1, weight=1)
        rodape.grid_propagate(False)

        self._lbl_status = ctk.CTkLabel(
            rodape, text="Pronto.", font=FONTES["corpo"], text_color=CORES["texto_secundario"]
        )
        self._lbl_status.grid(row=0, column=0, padx=16, pady=10, sticky="w")

        nav = ctk.CTkFrame(rodape, fg_color="transparent")
        nav.grid(row=0, column=1, sticky="e", padx=4)

        self._btn_prev = ctk.CTkButton(
            nav, text="<", width=32, height=28,
            fg_color=CORES["primaria"], hover_color=CORES["primaria_hover"],
            command=self._pagina_anterior,
        )
        self._btn_prev.pack(side="left", padx=4)

        self._lbl_pag = ctk.CTkLabel(nav, text="–", font=FONTES["corpo"], text_color=CORES["texto"])
        self._lbl_pag.pack(side="left", padx=6)

        self._btn_next = ctk.CTkButton(
            nav, text=">", width=32, height=28,
            fg_color=CORES["primaria"], hover_color=CORES["primaria_hover"],
            command=self._proxima_pagina,
        )
        self._btn_next.pack(side="left", padx=4)

        exp = ctk.CTkFrame(rodape, fg_color="transparent")
        exp.grid(row=0, column=2, sticky="e", padx=(4, 12))

        ctk.CTkButton(
            exp, text="CSV", width=62, height=28,
            fg_color=CORES["secundaria"], hover_color=CORES["primaria_hover"],
            command=lambda: self._exportar("csv"),
        ).pack(side="left", padx=(4, 2))

        ctk.CTkButton(
            exp, text="XLSX", width=62, height=28,
            fg_color=CORES["secundaria"], hover_color=CORES["primaria_hover"],
            command=lambda: self._exportar("xlsx"),
        ).pack(side="left", padx=(2, 0))

    # ------------------------------------------------------------------
    # Lógica de busca
    # ------------------------------------------------------------------

    def _read_filters(self) -> dict:
        exame_val = self._cmb_exame.get()
        pos_val = self._cmb_pos.get()
        gal_val = self._cmb_gal.get()
        return {
            "data_inicio": self._ent_inicio.get().strip(),
            "data_fim": self._ent_fim.get().strip(),
            "exames": None if exame_val == "Todos" else [exame_val],
            "positividade": None if pos_val == "Todos" else [pos_val],
            "status_gal": None if gal_val == "Todos" else [gal_val],
            "analistas": [self._ent_analista.get().strip()] if self._ent_analista.get().strip() else None,
            "kits": [self._ent_kit.get().strip()] if self._ent_kit.get().strip() else None,
        }

    def _buscar_primeira_pagina(self) -> None:
        self._current_page = 0
        self._executar_busca()

    def _executar_busca(self) -> None:
        if self._use_case is None:
            self._mostrar_estado("erro")
            self._lbl_erro.configure(text="Use case nao disponivel. Verifique a configuracao.")
            return

        try:
            from application.reports_contracts import ReportsFilterDTO, ReportsValidationError

            raw = self._read_filters()
            offset = self._current_page * PAGE_SIZE

            f = ReportsFilterDTO.from_raw(
                data_inicio=raw["data_inicio"],
                data_fim=raw["data_fim"],
                active_exams=self._active_exams(),
                exames=raw["exames"],
                positividade=raw["positividade"],
                status_gal=raw["status_gal"],
                analistas=raw["analistas"],
                kits=raw["kits"],
                limit=PAGE_SIZE,
                offset=offset,
            )
            result = self._use_case.execute(f)

        except Exception as exc:
            self._mostrar_estado("erro")
            self._lbl_erro.configure(text=f"Erro na consulta: {exc}")
            registrar_log("ReportsModule", f"Erro na busca: {exc}", "ERROR")
            return

        self._total_results = result.paginacao.total_estimado
        self._atualizar_resumo(result.resumo)
        self._atualizar_tabela(result.detalhes)
        self._atualizar_paginacao()

        total = self._total_results
        pagina = self._current_page + 1
        total_pags = max(1, _page_count(total, PAGE_SIZE))
        exibindo = len(result.detalhes)
        self._lbl_status.configure(
            text=f"Exibindo {exibindo} registro(s) | Total: {total} | Pagina {pagina}/{total_pags}"
        )
        self._lbl_header_count.configure(text=f"({total} resultados)")

    def _atualizar_resumo(self, resumo: dict) -> None:
        for key, lbl in self._cards.items():
            lbl.configure(text=str(resumo.get(key, 0)))

    def _atualizar_tabela(self, detalhes) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not detalhes:
            self._mostrar_estado("vazio")
            return

        self._mostrar_estado("tabela")
        for d in detalhes:
            status = d.status_gal
            self.tree.insert(
                "", "end",
                values=(
                    str(d.data_exame),
                    d.exame,
                    d.amostra_codigo,
                    d.resultado_geral,
                    _gal_status_display(status),
                    d.analista or "–",
                    d.kit or "–",
                    d.lote or "–",
                ),
                tags=(status,),
            )

    def _atualizar_paginacao(self) -> None:
        total_pags = _page_count(self._total_results, PAGE_SIZE)
        if total_pags == 0:
            self._lbl_pag.configure(text="–")
            self._btn_prev.configure(state="disabled")
            self._btn_next.configure(state="disabled")
            return

        self._lbl_pag.configure(text=f"Pag {self._current_page + 1}/{total_pags}")
        self._btn_prev.configure(state="normal" if self._current_page > 0 else "disabled")
        self._btn_next.configure(
            state="normal" if self._current_page < total_pags - 1 else "disabled"
        )

    def _mostrar_estado(self, estado: str) -> None:
        """Alterna entre 'tabela', 'vazio' e 'erro' na area da tabela."""
        self.tree.grid_remove()
        self._frame_vazio.place_forget()
        self._frame_erro.place_forget()

        if estado == "tabela":
            self.tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        elif estado == "vazio":
            self.tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._frame_vazio.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._frame_erro.place(relx=0.5, rely=0.5, anchor="center")

    def _sort_treeview(self, col: str, reverse: bool) -> None:
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)
            
        for index, (val, k) in enumerate(l):
            self.tree.move(k, "", index)
            
        self.tree.heading(col, command=lambda: self._sort_treeview(col, not reverse))

    # ------------------------------------------------------------------
    # Paginação
    # ------------------------------------------------------------------

    def _pagina_anterior(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1
            self._executar_busca()

    def _proxima_pagina(self) -> None:
        total_pags = _page_count(self._total_results, PAGE_SIZE)
        if self._current_page < total_pags - 1:
            self._current_page += 1
            self._executar_busca()

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def _exportar(self, formato: str) -> None:
        """Busca todos os resultados filtrados e exporta para CSV ou XLSX."""
        if self._use_case is None:
            self._lbl_status.configure(text="Erro: use case nao disponivel.")
            return

        from tkinter import filedialog

        if formato == "csv":
            ext = ".csv"
            ftypes = [("CSV", "*.csv"), ("Todos", "*.*")]
        else:
            ext = ".xlsx"
            ftypes = [("Excel", "*.xlsx"), ("Todos", "*.*")]

        filepath = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=ftypes,
            title=f"Exportar relatorio ({formato.upper()})",
        )
        if not filepath:
            return

        try:
            from application.reports_contracts import MAX_LIMIT, ReportsFilterDTO, ReportsValidationError
            from services.reports.reports_exporter import export_csv, export_xlsx

            raw = self._read_filters()
            f = ReportsFilterDTO.from_raw(
                data_inicio=raw["data_inicio"],
                data_fim=raw["data_fim"],
                active_exams=self._active_exams(),
                exames=raw["exames"],
                positividade=raw["positividade"],
                status_gal=raw["status_gal"],
                analistas=raw["analistas"],
                kits=raw["kits"],
                limit=MAX_LIMIT,
                offset=0,
            )
            result = self._use_case.execute(f)

            usuario = "sistema"
            if self._app_state is not None:
                for attr in ("usuario_atual", "usuario", "current_user"):
                    val = getattr(self._app_state, attr, None)
                    if val:
                        usuario = str(val)
                        break

            from pathlib import Path as _Path
            if formato == "csv":
                export_csv(result.detalhes, f, usuario, _Path(filepath))
            else:
                export_xlsx(result.detalhes, f, usuario, _Path(filepath))

            total = len(result.detalhes)
            self._lbl_status.configure(
                text=f"Exportado: {total} registro(s) → {_Path(filepath).name}"
            )
        except Exception as exc:
            self._lbl_status.configure(text=f"Erro ao exportar: {exc}")
            registrar_log("ReportsModule", f"Erro ao exportar {formato}: {exc}", "ERROR")

    def _limpar_filtros(self) -> None:
        today = date.today()
        self._ent_inicio.delete(0, "end")
        self._ent_inicio.insert(0, (today - timedelta(days=30)).isoformat())
        self._ent_fim.delete(0, "end")
        self._ent_fim.insert(0, today.isoformat())
        self._cmb_exame.set("Todos")
        self._cmb_pos.set("Todos")
        self._cmb_gal.set("Todos")
        self._ent_analista.delete(0, "end")
        self._ent_kit.delete(0, "end")

    def _on_close(self) -> None:
        if self._closing:
            return
        self._closing = True
        if self._on_close_callback is not None:
            self._on_close_callback()
        else:
            self.destroy()


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def abrir_modulo_relatorios(parent: Any, app_state: Any = None) -> None:
    """Abre a janela do modulo de relatorios."""
    win = ctk.CTkToplevel(parent)
    win.title("Relatorios Operacionais — IntegRAGal")
    win.geometry("1140x740")
    win.minsize(900, 560)

    def _on_close():
        win.destroy()

    ReportsModule(win, app_state=app_state, on_close_callback=_on_close)
    win.after(50, win.lift)

def create_reports_page(parent: ctk.CTkFrame, main_window: Any) -> ctk.CTkFrame:
    """Construtor da página de relatórios para o ModuleHost."""
    def _go_back() -> None:
        nav = getattr(main_window, "navigation_manager", None)
        if nav and hasattr(nav, "navigate_to"):
            nav.navigate_to("dashboard")
            
    app_state = getattr(main_window, "app_state", None)
    return ReportsModule(parent, app_state=app_state, on_close_callback=_go_back)
