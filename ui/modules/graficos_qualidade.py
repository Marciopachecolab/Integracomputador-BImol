"""
Gráficos de Qualidade e Estatísticas - IntegaGal
Fase 3.3 - Interface Gráfica
"""

import customtkinter as ctk
from tkinter import ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Any, Optional

from .estilos import CORES, FONTES, GRAFICO_CORES
from utils.gui_utils import safe_destroy_ctk_toplevel
from utils.logger import registrar_log
from services.reports.history_report import HistoryReportService


class GraficosQualidade(ctk.CTkFrame):
    """Tela de graficos em modo legado (janela) ou pagina single-window."""

    def __init__(
        self,
        master,
        dados_historico: Optional[pd.DataFrame] = None,
        *,
        host_frame: Optional[ctk.CTkFrame] = None,
        on_close_callback: Optional[Callable[[], None]] = None,
    ):
        self._is_page_mode = host_frame is not None
        self._window: Optional[ctk.CTkToplevel] = None
        self._on_close_callback = on_close_callback

        if self._is_page_mode:
            super().__init__(host_frame)
            self.pack(expand=True, fill="both")
        else:
            self._window = ctk.CTkToplevel(master)
            super().__init__(self._window)
            self.pack(expand=True, fill="both")

        self._parent = master
        self._closing = False

        self.df = dados_historico if dados_historico is not None else self._carregar_dados_reais()

        if self._window is not None:
            self._window.title("Graficos de Qualidade e Estatisticas")
            self._window.geometry("1400x900")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._criar_header()
        self._criar_conteudo()

        if self._window is not None:
            self._window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _criar_header(self):
        """Cria header com título e controles"""
        header = ctk.CTkFrame(
            self,
            fg_color=CORES['primaria'],
            corner_radius=0,
            height=80
        )
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        header.grid_propagate(False)
        
        # Ícone e título
        label_icone = ctk.CTkLabel(
            header,
            text="ðŸ“Š",
            font=("Arial", 36),
            text_color=CORES['branco']
        )
        label_icone.grid(row=0, column=0, padx=(30, 15), pady=20)
        
        label_titulo = ctk.CTkLabel(
            header,
            text="Gráficos de Qualidade e Estatísticas",
            font=FONTES['titulo_grande'],
            text_color=CORES['branco']
        )
        label_titulo.grid(row=0, column=1, sticky="w", pady=20)
        
        # Informações do período
        if self.df is not None and not self.df.empty:
            data_min = self.df['data_hora'].min()
            data_max = self.df['data_hora'].max()
            total_analises = len(self.df)
            
            info_text = f"📅 {data_min} a {data_max} | 🔬 {total_analises} análises"
            
            label_info = ctk.CTkLabel(
                header,
                text=info_text,
                font=FONTES['corpo'],
                text_color=CORES['branco']
            )
            label_info.grid(row=0, column=2, padx=20)
        
        # Botão fechar
        btn_fechar = ctk.CTkButton(
            header,
            text="✕",
            command=self._on_close,
            fg_color="transparent",
            hover_color=CORES['primaria_escuro'],
            width=40,
            height=40,
            font=("Arial", 20, "bold"),
            corner_radius=5
        )
        btn_fechar.grid(row=0, column=3, padx=(10, 30))
    
    def _criar_conteudo(self):
        """Cria conteúdo principal com gráficos"""
        # Container com scroll
        container = ctk.CTkScrollableFrame(
            self,
            fg_color=CORES['fundo'],
            corner_radius=0
        )
        container.grid(row=1, column=0, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        
        # Seções
        self._criar_secao_estatisticas(container)
        self._criar_secao_distribuicao_ct(container)
        self._criar_secao_tendencia_temporal(container)
        self._criar_secao_taxa_sucesso(container)
        self._criar_secao_analise_equipamentos(container)
        self._criar_secao_acoes(container)
    
    def _criar_secao_estatisticas(self, parent):
        """Cria seção de estatísticas descritivas"""
        frame = self._criar_frame_secao(
            parent,
            titulo="📈 Estatísticas Gerais",
            row=0
        )
        
        if self.df is None or self.df.empty:
            self._criar_mensagem_vazio(frame, "Sem dados para análise estatística")
            return
        
        # Container de cards
        cards_container = ctk.CTkFrame(frame, fg_color="transparent")
        cards_container.pack(fill="x", padx=20, pady=(0, 15))
        cards_container.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # Calcular estatisticas
        total_analises = len(self.df)
        _status_col = self.df.get('status', self.df.get('status_corrida', pd.Series(dtype=str)))
        _status_norm = _status_col.fillna('').str.strip().str.lower()
        analises_validas = int((_status_norm.isin(['valida', 'válida', 'processada', ''])).sum())
        taxa_sucesso = (analises_validas / total_analises * 100) if total_analises > 0 else 0
        
        # Equipamento mais usado
        equipamento_mais_usado = self.df['equipamento'].mode()[0] if self.df is not None and not self.df.empty else "N/A"
        
        # Exame mais frequente
        exame_mais_freq = self.df['exame'].mode()[0] if self.df is not None and not self.df.empty else "N/A"
        
        # Criar cards
        stats = [
            ("📊", str(total_analises), "Total de Análises", CORES['primaria']),
            ("✅", f"{taxa_sucesso:.1f}%", "Taxa de Sucesso", CORES['sucesso']),
            ("ðŸ”§", equipamento_mais_usado, "Equipamento + Usado", CORES['secundaria']),
            ("ðŸ”¬", exame_mais_freq, "Exame + Frequente", CORES['info'])
        ]
        
        for col, (emoji, valor, titulo, cor) in enumerate(stats):
            self._criar_card_estatistica(cards_container, emoji, valor, titulo, cor, col)
    
    def _criar_card_estatistica(self, parent, emoji: str, valor: str, titulo: str, cor: str, col: int):
        """Cria card de estatística"""
        card = ctk.CTkFrame(
            parent,
            fg_color=CORES['branco'],
            corner_radius=10,
            border_width=2,
            border_color=cor
        )
        card.grid(row=0, column=col, padx=10, pady=10, sticky="ew")
        
        # Emoji
        label_emoji = ctk.CTkLabel(
            card,
            text=emoji,
            font=("Arial", 32),
            text_color=cor
        )
        label_emoji.pack(pady=(15, 5))
        
        # Valor
        label_valor = ctk.CTkLabel(
            card,
            text=valor,
            font=FONTES['titulo'],
            text_color=cor
        )
        label_valor.pack(pady=5)
        
        # Título
        label_titulo = ctk.CTkLabel(
            card,
            text=titulo,
            font=FONTES['corpo'],
            text_color=CORES['texto_secundario']
        )
        label_titulo.pack(pady=(0, 15))
    
    def _criar_secao_distribuicao_ct(self, parent):
        """Cria seção com gráfico de distribuição de valores CT"""
        frame = self._criar_frame_secao(
            parent,
            titulo="📊 Distribuição de Valores CT",
            row=1
        )
        
        if self.df is None or self.df.empty:
            self._criar_mensagem_vazio(frame, "Sem dados para gráfico de distribuição")
            return
        
        # Frame para gráfico
        frame_canvas = ctk.CTkFrame(frame, fg_color=CORES['branco'])
        frame_canvas.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        # Criar figura
        fig = Figure(figsize=(12, 5), dpi=100, facecolor=CORES['branco'])
        
        # Subplot 1: Histograma de CT reais
        ax1 = fig.add_subplot(121)

        ct_cols = [c for c in self.df.columns if c.endswith(' - CT') or c.endswith('- CT')]
        all_ct = pd.Series(dtype=float)
        for col in ct_cols:
            vals = pd.to_numeric(self.df[col], errors='coerce').dropna()
            all_ct = pd.concat([all_ct, vals], ignore_index=True)

        if len(all_ct) > 0:
            ct_values = all_ct.values
            ax1.hist(ct_values, bins=30, color=GRAFICO_CORES[0], edgecolor='white', alpha=0.8)
            ax1.axvline(x=30, color=CORES['erro'], linestyle='--', linewidth=2, label='Threshold (30)')
        else:
            ax1.text(0.5, 0.5, 'Sem dados CT', ha='center', va='center', transform=ax1.transAxes)

        ax1.set_xlabel('Valor CT', fontsize=10)
        ax1.set_ylabel('Frequencia', fontsize=10)
        ax1.set_title('Distribuicao de Valores CT', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.legend()
        ax1.set_facecolor(CORES['branco'])

        # Subplot 2: Boxplot por alvo real
        ax2 = fig.add_subplot(122)

        ct_por_alvo = {}
        for col in ct_cols:
            alvo = col.replace(' - CT', '').replace('- CT', '').strip()
            vals = pd.to_numeric(self.df[col], errors='coerce').dropna().values
            if len(vals) >= 5:
                ct_por_alvo[alvo] = vals

        if ct_por_alvo:
            labels = list(ct_por_alvo.keys())
            data = [ct_por_alvo[l] for l in labels]
            bp = ax2.boxplot(data, labels=labels, patch_artist=True,
                             medianprops=dict(color='red', linewidth=2),
                             boxprops=dict(facecolor=GRAFICO_CORES[1], alpha=0.8))
            ax2.axhline(y=30, color=CORES['erro'], linestyle='--', linewidth=2, label='Threshold')
            ax2.tick_params(axis='x', rotation=45)
        else:
            ax2.text(0.5, 0.5, 'Sem dados CT por alvo', ha='center', va='center', transform=ax2.transAxes)

        ax2.set_ylabel('Valor CT', fontsize=10)
        ax2.set_xlabel('Alvos', fontsize=10)
        ax2.set_title('Distribuicao CT por Alvo', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y', linestyle='--')
        ax2.legend()
        ax2.set_facecolor(CORES['branco'])
        
        fig.tight_layout()
        
        # Canvas
        canvas = FigureCanvasTkAgg(fig, master=frame_canvas)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
    
    def _criar_secao_tendencia_temporal(self, parent):
        """Cria seção com gráfico de tendência temporal"""
        frame = self._criar_frame_secao(
            parent,
            titulo="📈 Tendência Temporal de Análises",
            row=2
        )
        
        if self.df is None or self.df.empty:
            self._criar_mensagem_vazio(frame, "Sem dados para gráfico de tendência")
            return
        
        # Frame para gráfico
        frame_canvas = ctk.CTkFrame(frame, fg_color=CORES['branco'])
        frame_canvas.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        # Criar figura
        fig = Figure(figsize=(12, 5), dpi=100, facecolor=CORES['branco'])
        ax = fig.add_subplot(111)
        
        # Tendencia temporal a partir dos dados reais
        df_temp = self.df.copy()
        df_temp['_data'] = pd.to_datetime(df_temp['data_hora'], errors='coerce')
        df_temp = df_temp.dropna(subset=['_data'])
        df_temp['_dia'] = df_temp['_data'].dt.date

        daily = df_temp.groupby('_dia').size().sort_index()

        if len(daily) > 0:
            datas_str = [d.strftime('%d/%m') for d in daily.index]
            totais = daily.values

            ax.fill_between(range(len(totais)), 0, totais, color=CORES['primaria'], alpha=0.5, label='Analises')
            ax.plot(range(len(totais)), totais, color=CORES['primaria'], linewidth=2, marker='o',
                    markersize=4, label='Total')

            step = max(1, len(datas_str) // 8)
            indices = list(range(0, len(datas_str), step))
            ax.set_xticks(indices)
            ax.set_xticklabels([datas_str[i] for i in indices], rotation=45)
        else:
            ax.text(0.5, 0.5, 'Sem dados temporais', ha='center', va='center', transform=ax.transAxes)

        ax.set_xlabel('Data', fontsize=10)
        ax.set_ylabel('Numero de Analises', fontsize=10)
        ax.set_title('Evolucao de Analises por Dia', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper left')
        ax.set_facecolor(CORES['branco'])
        
        fig.tight_layout()
        
        # Canvas
        canvas = FigureCanvasTkAgg(fig, master=frame_canvas)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
    
    def _criar_secao_taxa_sucesso(self, parent):
        """Cria seção com gráfico de taxa de sucesso"""
        frame = self._criar_frame_secao(
            parent,
            titulo="✅ Taxa de Sucesso por Exame",
            row=3
        )
        
        if self.df is None or self.df.empty:
            self._criar_mensagem_vazio(frame, "Sem dados para taxa de sucesso")
            return
        
        # Frame para gráfico
        frame_canvas = ctk.CTkFrame(frame, fg_color=CORES['branco'])
        frame_canvas.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        # Criar figura
        fig = Figure(figsize=(12, 5), dpi=100, facecolor=CORES['branco'])
        
        # Subplot 1: Analises por tipo de exame (dados reais)
        ax1 = fig.add_subplot(121)

        exam_counts = self.df['exame'].value_counts().head(8)
        if len(exam_counts) > 0:
            labels = [e[:20] for e in exam_counts.index]
            colors = [GRAFICO_CORES[i % len(GRAFICO_CORES)] for i in range(len(exam_counts))]
            bars = ax1.barh(labels, exam_counts.values, color=colors, edgecolor='white', linewidth=2)
            for bar, val in zip(bars, exam_counts.values):
                ax1.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
                         str(val), va='center', fontweight='bold', fontsize=10)
        else:
            ax1.text(0.5, 0.5, 'Sem dados', ha='center', va='center', transform=ax1.transAxes)

        ax1.set_xlabel('Quantidade de Analises', fontsize=10)
        ax1.set_title('Analises por Tipo de Exame', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='x', linestyle='--')
        ax1.set_facecolor(CORES['branco'])

        # Subplot 2: Pizza de distribuicao por exame
        ax2 = fig.add_subplot(122)

        if len(exam_counts) > 0:
            cores_pizza = [GRAFICO_CORES[i % len(GRAFICO_CORES)] for i in range(len(exam_counts))]
            wedges, texts, autotexts = ax2.pie(
                exam_counts.values,
                labels=[e[:15] for e in exam_counts.index],
                autopct='%1.1f%%',
                colors=cores_pizza,
                startangle=90,
                textprops={'fontsize': 9, 'fontweight': 'bold'},
            )
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(10)
                autotext.set_fontweight('bold')
        else:
            ax2.text(0.5, 0.5, 'Sem dados', ha='center', va='center', transform=ax2.transAxes)

        ax2.set_title('Distribuicao por Exame', fontsize=12, fontweight='bold')
        
        fig.tight_layout()
        
        # Canvas
        canvas = FigureCanvasTkAgg(fig, master=frame_canvas)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
    
    def _criar_secao_analise_equipamentos(self, parent):
        """Cria seção com análise por equipamento"""
        frame = self._criar_frame_secao(
            parent,
            titulo="🔧 Análise por Equipamento",
            row=4
        )
        
        if self.df is None or self.df.empty:
            self._criar_mensagem_vazio(frame, "Sem dados para análise de equipamentos")
            return
        
        # Frame para gráfico
        frame_canvas = ctk.CTkFrame(frame, fg_color=CORES['branco'])
        frame_canvas.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        # Criar figura
        fig = Figure(figsize=(12, 5), dpi=100, facecolor=CORES['branco'])
        ax = fig.add_subplot(111)
        
        # Dados reais por equipamento
        equip_counts = self.df['equipamento'].value_counts().head(6)

        if len(equip_counts) > 0:
            equipamentos = [e[:20] for e in equip_counts.index]
            x = np.arange(len(equipamentos))
            valores = equip_counts.values

            colors = [GRAFICO_CORES[i % len(GRAFICO_CORES)] for i in range(len(equipamentos))]
            bars = ax.bar(x, valores, color=colors, edgecolor='white', linewidth=2)

            for bar, val in zip(bars, valores):
                ax.text(bar.get_x() + bar.get_width() / 2., val,
                        str(val), ha='center', va='bottom', fontsize=10, fontweight='bold')

            ax.set_xticks(x)
            ax.set_xticklabels(equipamentos, rotation=30, ha='right')
        else:
            ax.text(0.5, 0.5, 'Sem dados', ha='center', va='center', transform=ax.transAxes)

        ax.set_xlabel('Equipamento', fontsize=10)
        ax.set_ylabel('Numero de Analises', fontsize=10)
        ax.set_title('Analises por Equipamento', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y', linestyle='--')
        ax.set_facecolor(CORES['branco'])
        
        fig.tight_layout()
        
        # Canvas
        canvas = FigureCanvasTkAgg(fig, master=frame_canvas)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
    
    def _criar_frame_secao(self, parent, titulo: str, row: int) -> ctk.CTkFrame:
        """Helper para criar frame de seção"""
        frame = ctk.CTkFrame(
            parent,
            fg_color=CORES['fundo_card'],
            corner_radius=10,
            border_width=1,
            border_color=CORES['borda']
        )
        frame.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 20))
        frame.grid_columnconfigure(0, weight=1)
        
        # Título
        label_titulo = ctk.CTkLabel(
            frame,
            text=titulo,
            font=FONTES['subtitulo'],
            text_color=CORES['texto']
        )
        label_titulo.pack(anchor="w", padx=20, pady=(15, 10))
        
        return frame
    
    def _criar_mensagem_vazio(self, parent, mensagem: str):
        """Cria mensagem de container vazio"""
        label = ctk.CTkLabel(
            parent,
            text=mensagem,
            font=FONTES['corpo'],
            text_color=CORES['texto_secundario']
        )
        label.pack(padx=20, pady=20)
    
    def _criar_secao_acoes(self, parent):
        """Cria seção de ações de exportação"""
        frame = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )
        frame.grid(row=5, column=0, sticky="ew", padx=20, pady=20)
        frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Botões de exportação
        btn_exportar_excel = ctk.CTkButton(
            frame,
            text="📊 Exportar Histórico (Excel)",
            command=lambda: self._exportar_historico_excel(),
            fg_color=CORES['secundaria'],
            hover_color=CORES['secundaria_hover'],
            height=40,
            font=FONTES['corpo_bold']
        )
        btn_exportar_excel.grid(row=0, column=0, padx=10)
        
        btn_exportar_csv = ctk.CTkButton(
            frame,
            text="📄 Exportar Histórico (CSV)",
            command=lambda: self._exportar_historico_csv(),
            fg_color=CORES['info'],
            hover_color=CORES['info'],
            height=40,
            font=FONTES['corpo_bold']
        )
        btn_exportar_csv.grid(row=0, column=1, padx=10)
        
        btn_fechar = ctk.CTkButton(
            frame,
            text="✕ Fechar",
            command=self._on_close,
            fg_color=CORES['texto_secundario'],
            hover_color=CORES['texto'],
            height=40,
            font=FONTES['corpo_bold']
        )
        btn_fechar.grid(row=0, column=2, padx=10)
    
    def _exportar_historico_excel(self):
        """Exporta histórico para Excel"""
        try:
            from .exportacao_relatorios import ExportadorRelatorios
            import tkinter.messagebox as messagebox
            
            exportador = ExportadorRelatorios()
            caminho = exportador.exportar_historico_excel(self.df)
            messagebox.showinfo("Sucesso", f"Excel gerado com sucesso!\\n\\nLocal: {caminho}")
            print(f"✅ Excel exportado: {caminho}")
        except Exception as e:
            import tkinter.messagebox as messagebox
            messagebox.showerror("Erro", f"Erro ao exportar Excel:\\n{e}")
            print(f"âŒ Erro ao exportar Excel: {e}")
    
    def _exportar_historico_csv(self):
        """Exporta histórico para CSV"""
        try:
            from .exportacao_relatorios import ExportadorRelatorios
            import tkinter.messagebox as messagebox
            
            exportador = ExportadorRelatorios()
            caminho = exportador.exportar_historico_csv(self.df)
            messagebox.showinfo("Sucesso", f"CSV gerado com sucesso!\\n\\nLocal: {caminho}")
            print(f"✅ CSV exportado: {caminho}")
        except Exception as e:
            import tkinter.messagebox as messagebox
            messagebox.showerror("Erro", f"Erro ao exportar CSV:\\n{e}")
            print(f"âŒ Erro ao exportar CSV: {e}")
    
    def _on_close(self):
        if self._closing:
            return
        self._closing = True

        if self._is_page_mode:
            if self._on_close_callback is not None:
                self._on_close_callback()
            else:
                self.destroy()
            return

        try:
            if self._parent is not None and hasattr(self._parent, "_graficos_window"):
                if self._parent._graficos_window is self:
                    self._parent._graficos_window = None
        except Exception:
            pass

        if self._window is not None:
            safe_destroy_ctk_toplevel(self._window)
        else:
            self.destroy()

    def _carregar_dados_reais(self) -> pd.DataFrame:
        """Carrega dados reais do CSV de historico (preserva colunas CT) com fallback."""
        from pathlib import Path

        # Leitura direta do CSV para preservar colunas CT por alvo
        csv_path = Path(__file__).resolve().parents[2] / "logs" / "historico_analises.csv"
        try:
            if csv_path.exists():
                df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig', low_memory=False)
                if not df.empty:
                    if 'data_hora' not in df.columns and 'data_hora_analise' in df.columns:
                        df['data_hora'] = df['data_hora_analise']
                    if 'status' not in df.columns:
                        df['status'] = df.get('status_corrida', pd.Series([''] * len(df), index=df.index))
                    df['status'] = df['status'].fillna('').replace('', 'Processada')
                    if 'equipamento' not in df.columns:
                        df['equipamento'] = df.get('exame', 'N/A')
                    registrar_log("GraficosQualidade", f"Carregados {len(df)} registros reais (CSV direto).", "INFO")
                    return df
        except Exception as e:
            registrar_log("GraficosQualidade", f"Erro ao ler CSV direto: {e}", "WARNING")

        # Fallback via service (sem colunas CT, mas com dados basicos)
        try:
            df = HistoryReportService().ler_historico(limit=1000)
            if df is not None and not df.empty:
                if 'data_hora' not in df.columns and 'data_hora_analise' in df.columns:
                    df['data_hora'] = df['data_hora_analise']
                if 'status' not in df.columns:
                    df['status'] = df.get('status_corrida', pd.Series([''] * len(df), index=df.index))
                df['status'] = df['status'].fillna('').replace('', 'Processada')
                if 'equipamento' not in df.columns:
                    df['equipamento'] = df.get('exame', 'N/A')
                registrar_log("GraficosQualidade", f"Carregados {len(df)} registros via service.", "INFO")
                return df
        except Exception as e:
            registrar_log("GraficosQualidade", f"Erro ao carregar via service: {e}", "WARNING")

        registrar_log("GraficosQualidade", "Sem dados reais, usando dados de exemplo.", "WARNING")
        return self._gerar_dados_exemplo()

    def _gerar_dados_exemplo(self) -> pd.DataFrame:
        """Gera dados de exemplo para demonstração (fallback)."""
        hoje = datetime.now()
        datas = [hoje - timedelta(days=x) for x in range(90)]
        
        dados = []
        exames = ['VR1e2 Biomanguinhos 7500', 'Dengue Quadruplex', 'Zika Detecção']
        equipamentos = ['ABI 7500', 'QuantStudio 5', 'CFX96']
        status_opcoes = ['Válida', 'Válida', 'Válida', 'Válida', 'Aviso', 'Inválida']
        
        for data in datas:
            n_analises = np.random.randint(8, 15)
            for _ in range(n_analises):
                dados.append({
                    'data_hora': data.strftime('%d/%m/%Y %H:%M:%S'),
                    'exame': np.random.choice(exames),
                    'equipamento': np.random.choice(equipamentos),
                    'status': np.random.choice(status_opcoes)
                })
        
        return pd.DataFrame(dados)




def create_graficos_page(
    parent: ctk.CTkFrame,
    main_window,
    dados_historico: Optional[pd.DataFrame] = None,
) -> ctk.CTkFrame:
    """Cria graficos como pagina no ModuleHost."""

    def _close() -> None:
        nav = getattr(main_window, "navigation_manager", None)
        if nav and hasattr(nav, "navigate_to"):
            nav.navigate_to("dashboard")

    page = GraficosQualidade(
        main_window,
        dados_historico=dados_historico,
        host_frame=parent,
        on_close_callback=_close,
    )
    return page

# Teste standalone
if __name__ == '__main__':
    import customtkinter as ctk
    
    app = ctk.CTk()
    app.withdraw()
    
    graficos = GraficosQualidade(app)
    
    app.mainloop()

