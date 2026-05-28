import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional, Tuple, Dict, Any

import customtkinter as ctk
import pandas as pd

from extracao.mapeamento_placas import (gerar_mapeamento_24,
                                        gerar_mapeamento_32,
                                        gerar_mapeamento_48,
                                        gerar_mapeamento_96)
# --- Bloco de Configuração Inicial ---
from utils.after_mixin import AfterManagerMixin
from utils.logger import registrar_log

COLOR_VALID = "#2ecc71"
COLOR_INVALID = "#e74c3c"
COLOR_NEUTRAL = "gray"


def _encontrar_inicio_matriz(df: pd.DataFrame) -> Tuple[int, int]:
    """
    Nova abordagem: Prioriza o intervalo A9:M17 (linhas 9-17, colunas A-M).
    Verifica por cabeçalho 1-12 e dados consistentes, com mais flexibilidade.
    Se não encontrar, faz uma varredura geral.
    """

    # Helper to check non-empty
    def _is_nonempty(val) -> bool:
        if pd.isna(val):
            return False
        s = str(val).strip()
        if s == "" or s.upper() == "NAN":
            return False
        return True

    # 1) Tentativa direta no intervalo A9:M17 (índices 8-16, 0-12)
    if df.shape[0] >= 17 and df.shape[1] >= 13:
        block = df.iloc[9:17, 1:13]
        non_empty = sum(1 for v in block.values.flatten() if _is_nonempty(v))
        col0_nonempty = sum(
            1 for v in block.iloc[:, 0].values.flatten() if _is_nonempty(v)
        )
        # Se houver um número razoável de células preenchidas, assumimos que é o bloco correto.
        # Também verifica se existe uma linha de cabeçalho com 1..12 (pode haver coluna A vazia)
        header_row = df.iloc[8, 0:13].tolist()
        header_ok = False
        try:
            header_vals = [str(x).strip() for x in header_row]
            # possibilidade: ['', '1','2',..'12'] ou ['1','2',..'12'] com deslocamento
            nums = [str(i) for i in range(1, 13)]
            if all(n in header_vals for n in nums):
                header_ok = True
        except Exception:
            header_ok = False

        if (non_empty >= 12 and col0_nonempty >= 4) or header_ok:
            registrar_log("Busca Matriz", "Bloco A9:M17 detectado diretamente.", "INFO")
            return 8, 0

    # 2) Fallback: varredura flexível procurando por um bloco 8x12 com células não vazias suficientes
    max_rows = df.shape[0] - 7
    max_cols = df.shape[1] - 11
    for row_idx in range(max_rows):
        for col_idx in range(max_cols):
            block = df.iloc[row_idx : row_idx + 8, col_idx : col_idx + 12]
            non_empty = sum(1 for v in block.values.flatten() if _is_nonempty(v))
            # Tenta validar rótulos de linha A..H na primeira coluna do bloco
            first_col_vals = [str(x).strip().upper() for x in block.iloc[:, 0].tolist()]
            row_labels = ["A", "B", "C", "D", "E", "F", "G", "H"]
            labels_ok = sum(1 for v in first_col_vals if v in row_labels)
            # Heurística: se pelo menos 12 células preenchidas e ao menos 4 labels A..H, consideramos válido
            if non_empty >= 12 and labels_ok >= 4:
                registrar_log(
                    "Busca Matriz",
                    f"Bloco 8x12 encontrado em ({row_idx}, {col_idx}) com {non_empty} células não vazias e {labels_ok} labels de linha.",
                    "INFO",
                )
                return row_idx, col_idx

    registrar_log("Busca Matriz", "Matriz não encontrada após varredura.", "ERROR")
    raise ValueError(
        "Não foi possível encontrar a matriz de extração. Verifique se o intervalo A9:M17 esta correto."
    )


def _extrair_numero_extracao(caminho_arquivo: str) -> Optional[str]:
    """
    Extrai o número da extração da célula C8 do arquivo de extração.
    
    FASE 4: Metadados para exibição no header da janela de análise.
    
    Args:
        caminho_arquivo: Caminho completo do arquivo .xlsx de extração
        
    Returns:
        String com o número da extração ou None se não encontrado
        
    Exemplos:
        C8 = "49" → retorna "49"
        C8 = "EXT 49" → retorna "EXT 49"
        C8 vazio/erro → retorna None
    """
    try:
        # Ler célula C8 (row=7, col=2 em índice 0-based)
        df_c8 = pd.read_excel(
            caminho_arquivo,
            sheet_name="PLANILHA EXTRAÇÃO",
            usecols="C",  # Coluna C
            skiprows=7,   # Pular 7 linhas (chegar na linha 8)
            nrows=1,      # Ler apenas 1 linha
            header=None,
            engine="openpyxl"
        )
        
        # Extrair valor
        if not df_c8.empty and not df_c8.iloc[0, 0] is pd.NA:
            valor_c8 = str(df_c8.iloc[0, 0]).strip()
            if valor_c8 and valor_c8.upper() not in ("NAN", "NONE", ""):
                registrar_log(
                    "BuscaExtração",
                    f"Número extração encontrado em C8: {valor_c8}",
                    "INFO"
                )
                return valor_c8
        
        registrar_log(
            "BuscaExtração",
            "Célula C8 vazia ou inválida - número extração não encontrado",
            "WARNING"
        )
        return None
        
    except Exception as e:
        registrar_log(
            "BuscaExtração",
            f"Erro ao extrair número extração de C8: {e}",
            "WARNING"
        )
        return None


class BuscaExtracaoApp(AfterManagerMixin, ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Mapeamento da Placa de Extração")
        self.geometry("700x750")

        self.resultado: Optional[Dict[str, Any]] = None  # FASE 4: Expandido para dict com metadados
        self.df_extracao_bruto: Optional[pd.DataFrame] = None
        self.caminho_arquivo_extracao: Optional[str] = None  # FASE 4: Armazenar caminho
        self.numero_extracao: Optional[str] = None  # FASE 4: Número da extração (C8)

        self.transient(parent)
        self.grab_set()

        self._criar_widgets()
        self.protocol("WM_DELETE_WINDOW", self.cancelar)
        registrar_log("BuscaExtração GUI", "Janela de mapeamento inicializada.", "INFO")

    def _criar_widgets(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(expand=True, fill="both", padx=10, pady=10)
        main_frame.grid_rowconfigure(7, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            main_frame,
            text="Etapa 1: Selecionar Planilha de Extração",
            font=("", 14, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.btn_selecionar = ctk.CTkButton(
            main_frame,
            text="Selecionar Arquivo (.xlsx)",
            command=self._selecionar_e_validar_planilha,
        )
        self.btn_selecionar.grid(row=1, column=0, sticky="ew")
        self.lbl_status_arquivo = ctk.CTkLabel(
            main_frame, text="Nenhum arquivo selecionado.", text_color=COLOR_NEUTRAL
        )
        self.lbl_status_arquivo.grid(row=2, column=0, sticky="w", pady=(5, 10))

        ctk.CTkLabel(
            main_frame, text="Etapa 2: Escolher Tipo de Kit", font=("", 14, "bold")
        ).grid(row=3, column=0, sticky="w", pady=(10, 5))
        self.kit_var = ctk.StringVar(value="")
        kit_options_frame = ctk.CTkFrame(main_frame)
        kit_options_frame.grid(row=4, column=0, sticky="ew")
        for kit in ["96", "48", "32", "24"]:
            rb = ctk.CTkRadioButton(
                kit_options_frame,
                text=f"{kit} Pocos",
                variable=self.kit_var,
                value=kit,
                command=self._atualizar_ui_parte,
            )
            rb.pack(side="left", padx=10, expand=True)

        self.parte_frame = ctk.CTkFrame(main_frame)
        self.parte_frame.grid(row=5, column=0, sticky="ew", pady=5)
        ctk.CTkLabel(self.parte_frame, text="Etapa 3: Parte da Placa").pack(anchor="w")
        self.parte_radios_frame = ctk.CTkFrame(self.parte_frame)
        self.parte_radios_frame.pack(fill="x")
        self.parte_var = ctk.StringVar(value="")

        ctk.CTkLabel(
            main_frame,
            text="Pré-visualização do Intervalo A9:M17:",
            font=("", 12, "bold"),
        ).grid(row=6, column=0, sticky="w", pady=(10, 5))
        
        # Criação da fonte monoespaçada
        fonte_mono = ctk.CTkFont(family="Courier New", size=12)
        
        # Aplicação da fonte na caixa de texto
        self.preview_textbox = ctk.CTkTextbox(main_frame, wrap="none", font=fonte_mono)
        self.preview_textbox.grid(row=7, column=0, sticky="nsew")
        
        self.preview_textbox.insert(
            "0.0", "Selecione um arquivo para ver o intervalo A9:M17..."
        )
        self.preview_textbox.configure(state="disabled")

        button_frame = ctk.CTkFrame(main_frame)
        button_frame.grid(row=8, column=0, sticky="ew", pady=(10, 0))
        self.btn_gerar = ctk.CTkButton(
            button_frame,
            text="Gerar Mapeamento",
            command=self._gerar_mapeamento,
            state="disabled",
        )
        self.btn_gerar.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.btn_cancelar = ctk.CTkButton(
            button_frame, text="Cancelar", command=self.cancelar, fg_color="gray"
        )
        self.btn_cancelar.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        self._atualizar_ui_parte()

    def _atualizar_ui_parte(self):
        for widget in self.parte_radios_frame.winfo_children():
            widget.destroy()

        kit = self.kit_var.get()
        partes_map = {
            "48": ["1", "2"],
            "32": ["1", "2", "3"],
            "24": ["1", "2", "3", "4"],
        }

        if kit in partes_map:
            self.parte_var.set("")
            for parte in partes_map[kit]:
                rb = ctk.CTkRadioButton(
                    self.parte_radios_frame,
                    text=f"Parte {parte}",
                    variable=self.parte_var,
                    value=parte,
                )
                rb.pack(side="left", padx=10)
            self.parte_frame.grid(row=5, column=0, sticky="ew")
        else:
            self.parte_frame.grid_forget()

    def _selecionar_e_validar_planilha(self):
        initial_dir = None
        try:
            from services.core.config_service import config_service
            data_root = config_service.get("data_root")
            if data_root:
                ext_path = os.path.join(data_root, "extracao")
                if not os.path.exists(ext_path):
                    os.makedirs(ext_path, exist_ok=True)
                initial_dir = os.path.abspath(ext_path)
        except Exception:
            pass

        kwargs = {
            "title": "Selecione a planilha de extração",
            "filetypes": [("Excel files", "*.xlsx")],
        }
        if initial_dir:
            kwargs["initialdir"] = initial_dir

        path = filedialog.askopenfilename(**kwargs)
        if not path:
            return

        try:
            # FASE 4: Armazenar caminho do arquivo
            self.caminho_arquivo_extracao = path
            
            # FASE 4: Extrair número da extração (C8)
            self.numero_extracao = _extrair_numero_extracao(path)
            
            df_full = pd.read_excel(path, sheet_name="PLANILHA EXTRAÇÃO", header=None)
            # read full B10:M17 block (8 rows x 12 cols)
            df_block = pd.read_excel(
                path,
                sheet_name="PLANILHA EXTRAÇÃO",
                usecols="B:M",
                skiprows=9,
                nrows=8,
                header=None,
            )

            # store the full block for later slicing according to selected parte
            self.df_extracao_full_block = df_block

            df_preview = df_block.copy()
            # Ajusta índices/colunas para exibir linhas como A..H e colunas como 1..12
            try:
                row_labels = list("ABCDEFGH")
                df_preview.index = row_labels[: df_preview.shape[0]]
                df_preview.columns = [str(i) for i in range(1, df_preview.shape[1] + 1)]
            except Exception:
                # se algo falhar, mantém o DataFrame original
                pass

            start_row, start_col = _encontrar_inicio_matriz(df_full)
            self._validar_estrutura_planilha(df_full, start_row, start_col)
            # defer extracting amostras until user chooses parte
            self.df_extracao_bruto = None

            self.lbl_status_arquivo.configure(
                text=f"Arquivo Válido: {os.path.basename(path)}", text_color=COLOR_VALID
            )
            self.btn_gerar.configure(state="normal")
            registrar_log(
                "BuscaExtração",
                f"Planilha '{os.path.basename(path)}' validada.",
                "INFO",
            )

            self.preview_textbox.configure(state="normal")
            self.preview_textbox.delete("0.0", "end")
            self.preview_textbox.insert("0.0", df_preview.to_string())
            self.preview_textbox.configure(state="disabled")

        except Exception as e:
            self.lbl_status_arquivo.configure(
                text=f"Erro: {e}", text_color=COLOR_INVALID
            )
            self.btn_gerar.configure(state="disabled")
            self.preview_textbox.configure(state="normal")
            self.preview_textbox.delete("0.0", "end")
            self.preview_textbox.insert(
                "0.0", f"Erro ao ler o intervalo A9:M17:\n\n{e}"
            )
            self.preview_textbox.configure(state="disabled")
            messagebox.showerror("Erro", str(e), parent=self)
            registrar_log("BuscaExtração", f"Falha: {e}", "ERROR")

    def _validar_estrutura_planilha(
        self, df: pd.DataFrame, start_row: int, start_col: int
    ):
        if not (start_row - 1 >= 0 and start_col + 12 < df.shape[1]):
            raise ValueError("A matriz está muito perto das bordas.")

    def _extrair_amostras(
        self, df: pd.DataFrame, start_row: int, start_col: int
    ) -> pd.DataFrame:
        amostras = []
        for j in range(12):  # Colunas A a L
            for i in range(8):  # Linhas 9 a 16
                row_idx = start_row + i
                col_idx = start_col + j
                if row_idx < df.shape[0] and col_idx < df.shape[1]:
                    amostra = df.iloc[row_idx, col_idx]
                    amostra_str = (
                        str(int(amostra))
                        if isinstance(amostra, float) and amostra.is_integer()
                        else str(amostra)
                    )
                    amostras.append({"Amostra": amostra_str})
                else:
                    amostras.append({"Amostra": ""})
        return pd.DataFrame(amostras)

    def _gerar_mapeamento(self):
        kit = self.kit_var.get()
        parte = self.parte_var.get()
        if not kit or not parte:
            messagebox.showerror("Erro", "Selecione kit e parte.", parent=self)
            return
        try:
            mapeamento_func = {
                "96": gerar_mapeamento_96,
                "48": lambda: gerar_mapeamento_48(int(parte)),
                "32": lambda: gerar_mapeamento_32(int(parte)),
                "24": lambda: gerar_mapeamento_24(int(parte)),
            }
            map_data = mapeamento_func[kit]()
            df_map = pd.DataFrame(map_data)
            df_map["Poco"] = [item[0] for item in df_map["analise"]]

            # Determine which slice of the full block to use based on parte
            if (
                not hasattr(self, "df_extracao_full_block")
                or self.df_extracao_full_block is None
            ):
                raise ValueError(
                    "Bloco de extração não carregado. Selecione a planilha novamente."
                )

            part_idx = int(parte) - 1
            total_cols = self.df_extracao_full_block.shape[1]
            if kit == "96":
                start_c, end_c = 0, 12
            elif kit == "48":
                width = 6
                start_c, end_c = part_idx * width, (part_idx + 1) * width
            elif kit == "32":
                width = 4
                start_c, end_c = part_idx * width, (part_idx + 1) * width
            elif kit == "24":
                width = 3
                start_c, end_c = part_idx * width, (part_idx + 1) * width
            else:
                start_c, end_c = 0, total_cols
            block_slice = self.df_extracao_full_block.iloc[:, start_c:end_c]

            # Compute both flatten orders: row-major (linha-major) and column-major (coluna-major)
            flat_row = []
            for r in range(block_slice.shape[0]):
                for c in range(block_slice.shape[1]):
                    val = block_slice.iat[r, c]
                    flat_row.append(val)

            flat_col = []
            for c in range(block_slice.shape[1]):
                for r in range(block_slice.shape[0]):
                    val = block_slice.iat[r, c]
                    flat_col.append(val)

            # default to row-major
            # default to row-major
            current_flat = flat_row
            df_map["Amostra"] = [
                (
                    str(current_flat[i - 1])
                    if (i - 1) < len(current_flat) and i - 1 >= 0
                    else ""
                )
                for i in df_map["amostra"]
            ]
            seq = list(range(1, len(df_map) + 1))
            df_map["Amostra"] = [
                (
                    str(current_flat[i - 1])
                    if 0 <= (i - 1) and (i - 1) < len(current_flat)
                    else ""
                )
                for i in seq
            ]
            df_map["Codigo"] = df_map["Amostra"]
            preview_win = ctk.CTkToplevel(self)
            df_map["Codigo"] = df_map["Amostra"]
            preview_win.title("Confirme o Mapeamento")
            preview_win.geometry("1200x900")  # FASE 1.1: Aumentado em 50% (800x750 → 1200x900)
            try:
                preview_win.attributes("-topmost", True)
                preview_win.lift()
                preview_win.focus_force()
            except Exception:
                pass
            lbl = ctk.CTkLabel(
                preview_win,
                text="Pré-visualização do mapeamento gerado (verifique e confirme):",
                anchor="w",
            )
            lbl.pack(fill="x", padx=10, pady=(10, 0))
            # Use column-major only (coluna-major) as required
            current_flat = flat_col
            
            # Atualizar df_map com ordem de coluna ANTES de criar visualizações
            seq = list(range(1, len(df_map) + 1))
            df_map["Amostra"] = [
                (
                    str(current_flat[i - 1])
                    if 0 <= (i - 1) and (i - 1) < len(current_flat)
                    else ""
                )
                for i in seq
            ]
            df_map["Codigo"] = df_map["Amostra"]
            
            # ======================================================================
            # VISUALIZAÇÃO GRÁFICA DO MAPEAMENTO (tipo mapa da placa)
            # ======================================================================
            visual_frame = ctk.CTkFrame(preview_win)
            visual_frame.pack(fill="x", padx=10, pady=5)
            
            # Criar grid visual (8 linhas x 12 colunas para placa 96)
            grid_frame = ctk.CTkFrame(visual_frame, fg_color="transparent")
            grid_frame.pack(padx=5, pady=5)
            
            # Cabeçalho com números das colunas
            ctk.CTkLabel(grid_frame, text="", width=45).grid(row=0, column=0, padx=1, pady=1)
            for col in range(1, 13):
                ctk.CTkLabel(
                    grid_frame, 
                    text=str(col), 
                    width=68,  # FASE 1.1: 45 → 68 pixels (+50%)
                    font=("", 10, "bold")
                ).grid(row=0, column=col, padx=1, pady=1)
            
            # Criar células do mapeamento
            rows_labels = ["A", "B", "C", "D", "E", "F", "G", "H"]
            for row_idx, row_label in enumerate(rows_labels, 1):
                # Label da linha
                ctk.CTkLabel(
                    grid_frame, 
                    text=row_label, 
                    width=45,  # FASE 1.1: 30 → 45 pixels (+50%)
                    font=("", 10, "bold")
                ).grid(row=row_idx, column=0, padx=1, pady=1)
                
                # Células com amostras
                for col_idx in range(1, 13):
                    poco = f"{row_label}{col_idx}"
                    # CORRIGIDO: Procurar se poco está em QUALQUER posição da tupla "analise"
                    # Isso suporta placas 48 (2 poços), 32 (3 poços) e 24 (4 poços)
                    amostra_val = ""
                    try:
                        for idx, row_data in df_map.iterrows():
                            analise_pocos = row_data.get("analise", ())
                            # analise_pocos é uma tupla tipo ("A1", "A2") para 48 poços
                            if poco in analise_pocos:
                                amostra_val = str(row_data["Amostra"])[:8]  # Limitar a 8 chars
                                break
                    except Exception:
                        pass
                    
                    # Criar célula
                    cor_celula = "#2ecc71" if amostra_val else "#95a5a6"
                    celula = ctk.CTkLabel(
                        grid_frame,
                        text=amostra_val if amostra_val else poco,
                        width=68,  # FASE 1.1: 45 → 68 pixels (+50%)
                        height=38,  # FASE 1.1: 25 → 38 pixels (+52%)
                        fg_color=cor_celula,
                        text_color="black",  # Texto preto
                        corner_radius=4,
                        font=("", 8)
                    )
                    celula.grid(row=row_idx, column=col_idx, padx=1, pady=1)
            # ======================================================================

            txt = ctk.CTkTextbox(preview_win, wrap="none")
            txt.pack(expand=True, fill="both", padx=10, pady=10)

            # Inserir texto descritivo do mapeamento (já atualizado com flat_col acima)
            txt.insert(
                "0.0",
                df_map[
                    [c for c in ["Poco", "Amostra", "Codigo"] if c in df_map.columns]
                ].to_string(index=False),
            )
            txt.configure(state="disabled")

            def _open_edit_window():
                """Open a small scrollable editor allowing inline edits to Amostra and Codigo."""
                edit_win = ctk.CTkToplevel(preview_win)
                edit_win.title("Editar Mapeamento")
                edit_win.geometry("600x400")
                
                # Tornar modal para evitar travamento
                edit_win.transient(preview_win)
                edit_win.grab_set()
                
                # Centralizar na tela
                edit_win.update_idletasks()
                x = (edit_win.winfo_screenwidth() // 2) - (edit_win.winfo_width() // 2)
                y = (edit_win.winfo_screenheight() // 2) - (edit_win.winfo_height() // 2)
                edit_win.geometry(f"+{x}+{y}")

                # Scrollable area using a Canvas and a frame
                canvas = tk.Canvas(edit_win)
                vsb = tk.Scrollbar(edit_win, orient="vertical", command=canvas.yview)
                canvas.configure(yscrollcommand=vsb.set)
                vsb.pack(side="right", fill="y")
                canvas.pack(side="left", fill="both", expand=True)

                inner_frame = ctk.CTkFrame(canvas)
                canvas.create_window((0, 0), window=inner_frame, anchor="nw")

                entries_amostra = []
                entries_codigo = []

                # Header
                ctk.CTkLabel(inner_frame, text="Poco", width=10).grid(
                    row=0, column=0, padx=5, pady=5
                )
                ctk.CTkLabel(inner_frame, text="Amostra").grid(
                    row=0, column=1, padx=5, pady=5
                )
                ctk.CTkLabel(inner_frame, text="Codigo").grid(
                    row=0, column=2, padx=5, pady=5
                )

                for idx, row in (
                    df_map[["Poco", "Amostra", "Codigo"]]
                    .reset_index(drop=True)
                    .iterrows()
                ):
                    ctk.CTkLabel(inner_frame, text=str(row["Poco"])).grid(
                        row=idx + 1, column=0, padx=5, pady=2
                    )
                    ent_a = ctk.CTkEntry(inner_frame)
                    ent_a.insert(
                        0, "" if pd.isna(row["Amostra"]) else str(row["Amostra"])
                    )
                    ent_a.grid(row=idx + 1, column=1, padx=5, pady=2)
                    ent_c = ctk.CTkEntry(inner_frame)
                    ent_c.insert(
                        0, "" if pd.isna(row["Codigo"]) else str(row["Codigo"])
                    )
                    ent_c.grid(row=idx + 1, column=2, padx=5, pady=2)
                    entries_amostra.append(ent_a)
                    entries_codigo.append(ent_c)

                def _on_inner_config(event):
                    canvas.configure(scrollregion=canvas.bbox("all"))

                inner_frame.bind("<Configure>", _on_inner_config)

                btnf = ctk.CTkFrame(edit_win)
                btnf.pack(fill="x", padx=10, pady=5)

                def _save_edits():
                    # Atualizar DataFrame com edições
                    for i in range(len(entries_amostra)):
                        df_map.at[i, "Amostra"] = entries_amostra[i].get()
                        df_map.at[i, "Codigo"] = entries_codigo[i].get()
                    
                    # Atualizar textbox de preview
                    txt.configure(state="normal")
                    txt.delete("0.0", "end")
                    txt.insert(
                        "0.0",
                        df_map[["Poco", "Amostra", "Codigo"]].to_string(index=False),
                    )
                    txt.configure(state="disabled")
                    
                    # Atualizar grid visual
                    for row_idx, row_label in enumerate(["A", "B", "C", "D", "E", "F", "G", "H"], 1):
                        for col_idx in range(1, 13):
                            poco = f"{row_label}{col_idx}"
                            # Procurar nova amostra
                            amostra_val = ""
                            try:
                                matches = df_map[df_map["Poco"] == poco]
                                if not matches.empty:
                                    amostra_val = str(matches.iloc[0]["Amostra"])[:8]
                            except Exception:
                                pass
                            
                            # Atualizar célula existente no grid
                            for widget in grid_frame.grid_slaves(row=row_idx, column=col_idx):
                                if isinstance(widget, ctk.CTkLabel):
                                    widget.configure(
                                        text=amostra_val if amostra_val else poco,
                                        fg_color="#2ecc71" if amostra_val else "#95a5a6"
                                    )
                    
                    # Liberar grab e fechar janela de edição
                    try:
                        edit_win.grab_release()
                    except Exception:
                        pass
                    edit_win.destroy()
                    
                    # Voltar foco para preview sem travar
                    preview_win.after(50, lambda: preview_win.focus_force())

                def _cancel_edits():
                    # Liberar grab e fechar janela de edição
                    try:
                        edit_win.grab_release()
                    except Exception:
                        pass
                    edit_win.destroy()
                    
                    # Voltar foco para preview sem travar
                    preview_win.after(50, lambda: preview_win.focus_force())

                save_btn = ctk.CTkButton(
                    btnf, text="Salvar", command=_save_edits, fg_color="#2ecc71"
                )
                save_btn.pack(side="left", expand=True, padx=5)
                cancel_btn = ctk.CTkButton(
                    btnf, text="Cancelar", command=_cancel_edits, fg_color="#e74c3c"
                )
                cancel_btn.pack(side="left", expand=True, padx=5)

            def _open_detalhes_window():
                """Open a window that shows detailed mapping (index, Poco, Amostra, flat value) to help debug order."""
                det_win = ctk.CTkToplevel(preview_win)
                det_win.title("Detalhes do Mapeamento")
                det_win.geometry("700x500")
                
                # Tornar modal
                det_win.transient(preview_win)
                det_win.grab_set()
                
                # Centralizar na tela
                det_win.update_idletasks()
                x = (det_win.winfo_screenwidth() // 2) - (det_win.winfo_width() // 2)
                y = (det_win.winfo_screenheight() // 2) - (det_win.winfo_height() // 2)
                det_win.geometry(f"+{x}+{y}")

                # Build a DataFrame for details
                try:
                    detalhe_rows = []
                    for idx, row in (
                        df_map[["Poco", "Amostra"]].reset_index(drop=True).iterrows()
                    ):
                        # Use the sequential index for i (1-based). If an 'analise' column exists and is valid, include it as extra info.
                        i = idx + 1
                        flat_val = (
                            current_flat[i - 1]
                            if (i - 1) < len(current_flat) and i - 1 >= 0
                            else ""
                        )
                        detalhe = {
                            "i": i,
                            "Poco": row["Poco"],
                            "Amostra": row["Amostra"],
                            "Flat": flat_val,
                        }
                        if "analise" in df_map.columns:
                            try:
                                detalhe["analise"] = df_map["analise"].iat[idx]
                            except Exception:
                                detalhe["analise"] = None
                        detalhe_rows.append(detalhe)
                    df_det = pd.DataFrame(detalhe_rows)

                    txtd = ctk.CTkTextbox(det_win, wrap="none")
                    txtd.pack(expand=True, fill="both", padx=10, pady=10)
                    txtd.insert("0.0", df_det.to_string(index=False))
                    txtd.configure(state="disabled")
                    
                    # Botão para fechar
                    def _close_detalhes():
                        try:
                            det_win.grab_release()
                        except Exception:
                            pass
                        det_win.destroy()
                        preview_win.after(50, lambda: preview_win.focus_force())
                    
                    btn_close = ctk.CTkButton(
                        det_win, 
                        text="Fechar", 
                        command=_close_detalhes
                    )
                    btn_close.pack(pady=10)
                    
                except Exception as e:
                    registrar_log(
                        "Mapeamento", f"Erro ao construir detalhes: {e}", "ERROR"
                    )
                    messagebox.showerror(
                        "Erro", f"Erro ao montar detalhes: {e}", parent=det_win
                    )

            def _confirm():
                # adicionar colunas alias com acentos para compatibilidade com analisadores existentes
                try:
                    df_map["Poço"] = df_map["Poco"]
                except Exception:
                    pass
                try:
                    df_map["Código"] = df_map["Codigo"]
                except Exception:
                    pass
                # retorna mapeamento com ambas variações para máxima compatibilidade
                cols = [
                    c
                    for c in ["Poco", "Poço", "Amostra", "Codigo", "Código"]
                    if c in df_map.columns
                ]
                # FASE 4: Retornar dict com DataFrame + metadados
                self.resultado = {
                    "mapeamento": df_map[cols],
                    "parte": int(parte),
                    "numero_extracao": self.numero_extracao,
                    "caminho_arquivo": self.caminho_arquivo_extracao
                }
                preview_win.destroy()
                # Fechar janela de mapeamento de forma segura para retornar ao menu
                self._safe_destroy()

            def _cancel():
                preview_win.destroy()
                # Cancelar também precisa fechar de forma segura
                self.cancelar()

            btn_frame = ctk.CTkFrame(preview_win)
            btn_frame.pack(fill="x", padx=10, pady=(0, 10))
            det_btn = ctk.CTkButton(
                btn_frame, text="Detalhes", command=_open_detalhes_window
            )
            det_btn.pack(side="left", expand=True, padx=5)
            edit_btn = ctk.CTkButton(
                btn_frame, text="Editar Mapeamento", command=_open_edit_window
            )
            edit_btn.pack(side="left", expand=True, padx=5)
            ok_btn = ctk.CTkButton(
                btn_frame, text="Confirmar", command=_confirm, fg_color="#2ecc71"
            )
            ok_btn.pack(side="left", expand=True, padx=5)
            cancel_btn = ctk.CTkButton(
                btn_frame, text="Cancelar", command=_cancel, fg_color="#e74c3c"
            )
            cancel_btn.pack(side="left", expand=True, padx=5)
        except Exception as e:
            messagebox.showerror("Erro", f"{e}", parent=self)
            registrar_log("Mapeamento", f"Falha: {e}", "ERROR")

    def cancelar(self):
        self.resultado = None
        self._safe_destroy()

    def _safe_destroy(self):
        try:
            self.dispose()
        except Exception:
            pass
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.withdraw()
        except Exception:
            pass
        self.after(100, self.destroy)


def carregar_dados_extracao(parent) -> Optional[Dict[str, Any]]:
    """
    Abre janela de mapeamento de extração e retorna dados.
    
    FASE 4: Retorna dict com mapeamento + metadados (número extração, caminho).
    
    Returns:
        Dict com chaves: 'mapeamento', 'parte', 'numero_extracao', 'caminho_arquivo'
        ou None se cancelado
    """
    dialog = BuscaExtracaoApp(parent)
    parent.wait_window(dialog)
    
    # Garantir que o parent recupere o foco após fechar o dialog
    try:
        parent.focus_force()
        parent.lift()
    except Exception:
        pass
    
    return dialog.resultado
