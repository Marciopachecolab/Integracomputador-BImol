# -*- coding: utf-8 -*-
"""
ui/components/full_analysis_grid.py

Componente de tabela completa de análise.
Exibe todas as colunas do df_analise (CT por alvo, Res por alvo, CT_RP, etc.)
no estilo da tela de referência operacional.

Substitui ScientificDataGrid na janela_analise_completa.
ScientificDataGrid permanece intacto para usos futuros.
"""

import math
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Constantes de layout
# ---------------------------------------------------------------------------

_WIDTHS: Dict[str, int] = {
    "Selecionado":         45,
    "Amostra":            105,
    "Poco":                55,
    "Resultado_geral":    100,
    "Status_Placa":        70,
    "Codigo":              90,
    # colunas dinâmicas de CT
    "_ct_default":         62,
    # colunas dinâmicas de Res
    "_res_default":        85,
    # sugestão
    "_sug_default":        82,
}

_DISPLAY: Dict[str, str] = {
    "Selecionado":           "Sel",
    "Amostra":               "Amostra",
    "Poco":                  "Poço",
    "Resultado_geral":       "Geral",
    "Status_Placa":          "Status Pl.",
    "Codigo":                "Código",
    "Sugestão_de_repetição": "Sug. Rep.",
    "Sugestao_de_repeticao": "Sug. Rep.",
}

# Colunas que sempre aparecem antes dos alvos dinâmicos (se existirem no DF)
_FIXED_BEFORE = ["Selecionado", "Amostra", "Poco"]

# Colunas que sempre aparecem depois dos alvos dinâmicos (se existirem no DF)
_FIXED_AFTER = [
    "Sugestão_de_repetição",
    "Sugestao_de_repeticao",
    "Resultado_geral",
    "Status_Placa",
    "Codigo",
]

# Padrões que identificam controles internos por nome de amostra
_CONTROL_LABELS = ("CN", "CP", "NEG", "POS", "BRANCO")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_control(row: pd.Series) -> bool:
    amostra = str(row.get("Amostra", "")).upper()
    return any(lbl in amostra for lbl in _CONTROL_LABELS)


def _result_tag(row: pd.Series) -> str:
    """Mapeia Resultado_geral para uma tag de cor canônica."""
    if _is_control(row):
        return "controle"
    rg = str(row.get("Resultado_geral", "")).lower()
    if "detect" in rg and "nao" not in rg and "não" not in rg:
        return "detectavel"
    if "indeterm" in rg or "inconclus" in rg:
        return "indeterminado"
    if "inv" in rg:
        return "invalido"
    return "nao_detectavel"


def _fmt_ct(val) -> str:
    """Formata valor de CT para exibição."""
    if val is None:
        return ""
    if isinstance(val, float):
        if math.isnan(val):
            return ""
        return f"{val:.2f}"
    try:
        f = float(val)
        if math.isnan(f):
            return ""
        return f"{f:.2f}"
    except (TypeError, ValueError):
        return str(val)


def _fmt_cell(col: str, val) -> str:
    """Formata o valor de uma célula para exibição."""
    if val is None:
        return ""
    if isinstance(val, float) and math.isnan(val):
        return ""
    if col.startswith("CT_"):
        return _fmt_ct(val)
    s = str(val)
    # Normaliza rótulos longas demais
    if len(s) > 22:
        s = s[:21] + "…"
    return s


# ---------------------------------------------------------------------------
# Componente principal
# ---------------------------------------------------------------------------

class FullAnalysisGrid(ctk.CTkFrame):
    """
    Tabela expandida da Análise Completa.

    Recebe um pandas.DataFrame e exibe uma coluna para cada par CT/<alvo> +
    Res/<alvo>, mais CT_RP_1/CT_RP_2 (sem Res_RP), e as colunas fixas.

    Parâmetros
    ----------
    master : widget pai
    on_toggle_select : callable(poco: str, new_state: bool) | None
        Callback invocado quando o usuário clica no checkbox de uma linha.
    """

    def __init__(
        self,
        master,
        on_toggle_select: Optional[Callable[[str, bool], None]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_toggle_select = on_toggle_select

        # Estado interno
        self._df: Optional[pd.DataFrame] = None
        self._columns: List[str] = []
        self._iid_to_idx: Dict[str, int] = {}  # treeview iid -> df row index

        # Monta widget
        self._setup_style()
        self._build_widget()

    # ------------------------------------------------------------------
    # Construção do widget
    # ------------------------------------------------------------------

    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("default")

        style.configure(
            "FullAnalysis.Treeview",
            background="#FFFFFF",
            foreground="#222222",
            fieldbackground="#FFFFFF",
            rowheight=22,
            font=("Segoe UI", 9),
            borderwidth=1,
            relief="flat",
        )
        style.map(
            "FullAnalysis.Treeview",
            background=[("selected", "#C5CAE9")],
            foreground=[("selected", "#1A237E")],
        )
        style.configure(
            "FullAnalysis.Treeview.Heading",
            background="#E8EAF6",
            foreground="#3949AB",
            font=("Segoe UI", 9, "bold"),
            padding=3,
            relief="flat",
        )
        style.map(
            "FullAnalysis.Treeview.Heading",
            background=[("active", "#C5CAE9")],
        )

    def _build_widget(self):
        """Cria a estrutura de scrollbars + Treeview."""
        container = tk.Frame(self, bg="#E8EAF6", bd=1, relief="sunken")
        container.pack(fill="both", expand=True)

        self._xscroll = tk.Scrollbar(container, orient="horizontal")
        self._yscroll = tk.Scrollbar(container, orient="vertical")

        self.tree = ttk.Treeview(
            container,
            style="FullAnalysis.Treeview",
            show="headings",
            selectmode="browse",
            xscrollcommand=self._xscroll.set,
            yscrollcommand=self._yscroll.set,
        )

        self._xscroll.config(command=self.tree.xview)
        self._yscroll.config(command=self.tree.yview)

        self._xscroll.pack(side="bottom", fill="x")
        self._yscroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<ButtonRelease-1>", self._on_click)

        # Tags de cor (alinhadas com SemanticColors de design_tokens.py)
        self.tree.tag_configure("detectavel",     background="#FEE2E2", foreground="#B71C1C")
        self.tree.tag_configure("indeterminado",  background="#FEF9C3", foreground="#E65100")
        self.tree.tag_configure("nao_detectavel", background="#C8E6C9", foreground="#1B5E20")  # verde claro
        self.tree.tag_configure("invalido",        background="#BDBDBD", foreground="#424242")  # cinza médio
        self.tree.tag_configure("controle",        background="#E3F2FD", foreground="#0D47A1")

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def load_dataframe(self, df: pd.DataFrame) -> None:
        """
        Carrega (ou recarrega) o DataFrame e renderiza a tabela.

        Deve ser chamado sempre que o df_analise mudar (análise nova,
        seleção em lote, reaplicar seleção).
        """
        if df is None or df.empty:
            return
        self._df = df  # referência viva — não copia
        self._build_columns()
        self._populate_rows()

    def refresh(self) -> None:
        """Re-renderiza as linhas sem reconfigurar as colunas."""
        if self._df is None:
            return
        self._populate_rows()

    def get_dataframe(self) -> Optional[pd.DataFrame]:
        """Retorna o DataFrame atual (com estado de Selecionado atualizado)."""
        return self._df

    # ------------------------------------------------------------------
    # Montagem das colunas
    # ------------------------------------------------------------------

    def _build_columns(self) -> None:
        df_cols = list(self._df.columns)
        ordered: List[str] = []

        # 1. Colunas fixas iniciais
        for c in _FIXED_BEFORE:
            if c in df_cols:
                ordered.append(c)

        # 2. Pares CT_<alvo> + Res_<alvo> dinâmicos (excluindo RP)
        ct_alvo_cols = [
            c for c in df_cols
            if c.startswith("CT_") and not c.startswith("CT_RP")
        ]
        for ct_col in ct_alvo_cols:
            alvo = ct_col[3:]  # ex: "ADV" de "CT_ADV"
            res_col = f"Res_{alvo}"
            if ct_col not in ordered:
                ordered.append(ct_col)
            if res_col in df_cols and res_col not in ordered:
                ordered.append(res_col)

        # 3. Apenas CT_RP (sem Res_RP — conforme decisão do usuário)
        rp_ct_cols = sorted(
            c for c in df_cols if c.startswith("CT_RP")
        )
        for c in rp_ct_cols:
            if c not in ordered:
                ordered.append(c)

        # 4. Colunas fixas finais (aceita variações com/sem acento)
        _after_set = set(_FIXED_AFTER)
        for c in df_cols:
            if c in _after_set and c not in ordered:
                ordered.append(c)

        self._columns = ordered

        # Aplica ao Treeview
        self.tree.config(columns=self._columns)
        for col in self._columns:
            display = _DISPLAY.get(col, col)
            width   = self._col_width(col)
            anchor  = self._col_anchor(col)
            self.tree.heading(col, text=display,
                              command=lambda c=col: self._sort_column(c, False))
            self.tree.column(col, width=width, anchor=anchor,
                             stretch=False, minwidth=28)

    def _col_width(self, col: str) -> int:
        if col in _WIDTHS:
            return _WIDTHS[col]
        if col.startswith("CT_"):
            return _WIDTHS["_ct_default"]
        if col.startswith("Res_"):
            return _WIDTHS["_res_default"]
        if "ugest" in col:
            return _WIDTHS["_sug_default"]
        return 80

    def _col_anchor(self, col: str) -> str:
        if col in ("Selecionado", "Poco"):
            return "center"
        if col.startswith("CT_"):
            return "center"
        if col in ("Resultado_geral", "Status_Placa", "Codigo"):
            return "center"
        return "w"

    # ------------------------------------------------------------------
    # Renderização das linhas
    # ------------------------------------------------------------------

    def _populate_rows(self) -> None:
        """Limpa e insere todas as linhas do DataFrame."""
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._iid_to_idx.clear()

        for idx, row in self._df.iterrows():
            tag   = _result_tag(row)
            vals  = self._row_values(row)
            iid   = self.tree.insert("", "end", values=vals, tags=(tag,))
            self._iid_to_idx[iid] = idx

    def _row_values(self, row: pd.Series) -> tuple:
        values = []
        for col in self._columns:
            if col == "Selecionado":
                if _is_control(row):
                    values.append("--")
                else:
                    sel = row.get("Selecionado", False)
                    # Compatível com bool ou string "[X]"
                    if isinstance(sel, str):
                        is_sel = sel.strip().upper() in ("[X]", "TRUE", "1")
                    else:
                        is_sel = bool(sel)
                    values.append("[X]" if is_sel else "[ ]")
            else:
                val = row.get(col, "")
                values.append(_fmt_cell(col, val))
        return tuple(values)

    # ------------------------------------------------------------------
    # Interação (checkbox)
    # ------------------------------------------------------------------

    def _on_click(self, event) -> None:
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col_id = self.tree.identify_column(event.x)
        iid    = self.tree.identify_row(event.y)

        if not iid or iid not in self._iid_to_idx:
            return

        # Somente a primeira coluna é clicável (Selecionado)
        if col_id != "#1":
            return

        idx = self._iid_to_idx[iid]
        row = self._df.loc[idx]

        if _is_control(row):
            return

        # Estado atual
        cur = row.get("Selecionado", False)
        if isinstance(cur, str):
            cur = cur.strip().upper() in ("[X]", "TRUE", "1")
        new_val = not bool(cur)

        # Atualiza DataFrame (referência viva)
        self._df.at[idx, "Selecionado"] = new_val

        # Atualiza visual imediato
        cur_vals = list(self.tree.item(iid, "values"))
        cur_vals[0] = "[X]" if new_val else "[ ]"
        self.tree.item(iid, values=cur_vals)

        # Dispara callback para janela_analise_completa
        if self.on_toggle_select:
            poco = str(row.get("Poco", ""))
            self.on_toggle_select(poco, new_val)

    # ------------------------------------------------------------------
    # Ordenação
    # ------------------------------------------------------------------

    def _sort_column(self, col: str, reverse: bool) -> None:
        """Ordena clicando no cabeçalho."""
        pairs = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]

        def sort_key(item):
            val = item[0]
            if col == "Poco" and len(val) >= 2:
                letra = val[0]
                num   = val[1:]
                return (letra, int(num) if num.isdigit() else 0)
            # Tenta ordenar numericamente (CT)
            try:
                return (0, float(val))
            except (ValueError, TypeError):
                return (1, val.lower())

        try:
            pairs.sort(key=sort_key, reverse=reverse)
        except Exception:
            pairs.sort(reverse=reverse)

        for index, (_, k) in enumerate(pairs):
            self.tree.move(k, "", index)

        self.tree.heading(col, command=lambda: self._sort_column(col, not reverse))
