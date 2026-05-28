# -*- coding: utf-8 -*-
"""
ui/components/scientific_data_grid.py

Componente visual de Tabela Científica com roupagem moderna.
Utiliza ttk.Treeview estilizado para garantir formato de tabela clássico
(colunas, classificação, seleção), mas com cores e fontes do Design System.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from typing import List, Callable, Optional
from application.contracts.ui_view_models import DataGridRowViewModel
from ui.theme.design_tokens import SemanticColors, Typography, Spacing, Radii, Colors

class ScientificDataGrid(ctk.CTkFrame):
    """
    Tabela de dados baseada em ttk.Treeview altamente estilizado para
    combinar com o tema CustomTkinter.
    """
    
    def __init__(self, master, on_toggle_select: Optional[Callable[[str, bool], None]] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_toggle_select = on_toggle_select
        self._items_map = {}
        
        # 1. Configurar o estilo premium da tabela
        self.style = ttk.Style(self)
        self.style.theme_use("default")
        
        # Usando os novos design tokens "blueprint" institucionais
        bg_color = Colors.bgWhite
        text_color = Colors.textSecondary
        header_bg = Colors.bgPanel
        header_text = Colors.textMuted
        
        self.style.configure("Premium.Treeview", 
                             background=bg_color,
                             foreground=text_color,
                             fieldbackground=bg_color,
                             rowheight=38, # Blueprint padronizou linhas mais soltas
                             borderwidth=0,
                             font=Typography.BODY_DEFAULT)
                             
        self.style.map('Premium.Treeview', 
                       background=[('selected', Colors.blueSoft)],
                       foreground=[('selected', Colors.blue)])
        
        self.style.configure("Premium.Treeview.Heading",
                             background=header_bg,
                             foreground=header_text,
                             font=Typography.TABLE_HEADER,
                             borderwidth=0,
                             padding=10)
                             
        self.style.map("Premium.Treeview.Heading",
                       background=[('active', Colors.graySoft)])
        
        # 2. Criar o Treeview
        columns = ("sel", "poco", "amostra", "resumo", "resultado")
        self.tree = ttk.Treeview(self, style="Premium.Treeview", columns=columns, show="headings")
        
        # 3. Configurar cabeçalhos
        self.tree.heading("sel", text="Sel", command=lambda: self._sort_column("sel", False))
        self.tree.heading("poco", text="Poço", command=lambda: self._sort_column("poco", False))
        self.tree.heading("amostra", text="Amostra", command=lambda: self._sort_column("amostra", False))
        self.tree.heading("resumo", text="Resumo de Alvos", command=lambda: self._sort_column("resumo", False))
        self.tree.heading("resultado", text="Resultado Final", command=lambda: self._sort_column("resultado", False))
        
        # 4. Configurar colunas
        self.tree.column("sel", width=50, anchor="center", stretch=False)
        self.tree.column("poco", width=80, anchor="center", stretch=False)
        self.tree.column("amostra", width=180, anchor="w")
        self.tree.column("resumo", width=300, anchor="w")
        self.tree.column("resultado", width=150, anchor="center")
        
        # 5. Adicionar scrollbar
        self.scrollbar = ctk.CTkScrollbar(self, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.scrollbar.pack(side="right", fill="y")
        
        # 6. Configurar Tags de Cor (Design Tokens Blueprint)
        self.tree.tag_configure("detectado", background=SemanticColors.DETECTADO, foreground=Colors.danger)
        self.tree.tag_configure("inconclusivo", background=SemanticColors.INCONCLUSIVO, foreground=Colors.warning)
        self.tree.tag_configure("invalido", background=SemanticColors.INVALIDO, foreground=Colors.textMuted)
        self.tree.tag_configure("nao_detectavel", background=SemanticColors.NAO_DETECTAVEL, foreground=Colors.success)
        self.tree.tag_configure("controle", background=Colors.blueSoft, foreground=Colors.blue)
        self.tree.tag_configure("disabled", foreground=Colors.textDisabled)
        
        # 7. Bindings
        self.tree.bind("<ButtonRelease-1>", self._on_click)
        
        self._sort_states = {col: False for col in columns}

    def populate(self, rows: List[DataGridRowViewModel]):
        """Limpa e insere as linhas no Treeview."""
        # Limpar existentes
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self._items_map.clear()
        
        # Inserir novos itens
        for row_vm in rows:
            self._insert_row(row_vm)
            
    def _insert_row(self, row_vm: DataGridRowViewModel):
        """Insere uma única linha no Treeview."""
        # Configurar estado do checkbox
        if row_vm.is_disabled or row_vm.is_control:
            sel_text = "🔒" # Travado
        else:
            sel_text = "☑" if row_vm.is_selected else "☐"
            
        # Determinar tag primária
        tags = []
        if row_vm.is_control:
            tags.append("controle")
        elif row_vm.is_disabled:
            tags.append("disabled")
            tags.append("invalido")
        else:
            # tag baseada no resultado
            tag_name = str(row_vm.result_tag).lower().strip()
            if tag_name in ["detectado", "inconclusivo", "invalido", "nao_detectavel"]:
                tags.append(tag_name)
                
        values = (
            sel_text,
            row_vm.well,
            row_vm.sample,
            row_vm.targets_summary,
            str(row_vm.result_tag).upper().replace("_", " ")
        )
        
        item_id = self.tree.insert("", "end", values=values, tags=tags)
        self._items_map[item_id] = row_vm

    def _on_click(self, event):
        """Detecta cliques, especialmente na coluna de seleção (checkbox simulado)."""
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
            
        column = self.tree.identify_column(event.x)
        item_id = self.tree.identify_row(event.y)
        
        # Se clicou na primeira coluna (Sel)
        if column == "#1" and item_id in self._items_map:
            row_vm = self._items_map[item_id]
            
            # Não permite alterar estado de controle ou inválido
            if row_vm.is_disabled or row_vm.is_control:
                return
                
            # Inverter estado
            new_state = not row_vm.is_selected
            row_vm.is_selected = new_state
            
            # Atualizar visual
            current_values = list(self.tree.item(item_id, "values"))
            current_values[0] = "☑" if new_state else "☐"
            self.tree.item(item_id, values=current_values)
            
            # Notificar callback
            if self.on_toggle_select:
                self.on_toggle_select(row_vm.well, new_state)

    def _sort_column(self, col: str, reverse: bool):
        """Classifica as linhas da tabela clicando no cabeçalho."""
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        
        # Tentativa de ordenar de forma inteligente (numérica se possível, poço A1, A2...)
        def sort_key(item):
            val = item[0]
            if col == "poco" and len(val) >= 2:
                # Ex: A1, A12, B3 -> A01, A12, B03
                letra = val[0]
                num = val[1:]
                return (letra, int(num) if num.isdigit() else 0)
            return val.lower()

        try:
            l.sort(key=sort_key, reverse=reverse)
        except Exception:
            l.sort(reverse=reverse)
            
        # Reorganizar itens
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)
            
        # Inverter direção para o próximo clique
        self.tree.heading(col, command=lambda: self._sort_column(col, not reverse))
