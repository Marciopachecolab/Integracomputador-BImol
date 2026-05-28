"""
Sistema de Alertas e Notificações - IntegaGal
Etapa 3.6 - Última etapa da Fase 3

Funcionalidades:
- Configuração de regras de alerta
- Centro de notificações
- Histórico de alertas
- Priorização e categorização
- Integração com Dashboard
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
import pandas as pd
from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, open_with_retry
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from services.core.config_service import config_service


# Importar estilos do módulo
try:
    from .estilos import CORES, FONTES
except ImportError:
    # Fallback se estilos não existirem
    CORES = {
        'primaria': '#1E88E5',
        'primaria_escuro': '#1565C0',
        'secundaria': '#26A69A',
        'sucesso': '#4CAF50',
        'aviso': '#FFC107',
        'erro': '#F44336',
        'info': '#2196F3',
        'fundo': '#F5F5F5',
        'fundo_escuro': '#E0E0E0',
        'texto': '#212121',
        'texto_claro': '#757575',
        'branco': '#FFFFFF',
        'borda': '#BDBDBD'
    }
    FONTES = {
        'titulo': ('Segoe UI', 24, 'bold'),
        'subtitulo': ('Segoe UI', 18, 'bold'),
        'corpo': ('Segoe UI', 12),
        'corpo_bold': ('Segoe UI', 12, 'bold'),
        'pequena': ('Segoe UI', 10)
    }


class TipoAlerta:
    """Tipos de alertas disponíveis"""
    CRITICO = 'Crítico'
    ALTO = 'Alto'
    MEDIO = 'Médio'
    BAIXO = 'Baixo'
    INFO = 'Info'


class CategoriaAlerta:
    """Categorias de alertas"""
    CONTROLE = 'Controle'
    REGRA = 'Regra'
    EQUIPAMENTO = 'Equipamento'
    SISTEMA = 'Sistema'
    QUALIDADE = 'Qualidade'


class Alerta:
    """Classe para representar um alerta"""
    
    def __init__(self, tipo: str, categoria: str, mensagem: str, 
                 exame: str = '', equipamento: str = '', detalhes: str = ''):
        self.id = datetime.now().strftime('%Y%m%d%H%M%S%f')
        self.tipo = tipo
        self.categoria = categoria
        self.mensagem = mensagem
        self.exame = exame
        self.equipamento = equipamento
        self.detalhes = detalhes
        self.data_hora = datetime.now()
        self.lido = False
        self.resolvido = False
    
    def marcar_lido(self):
        """Marca alerta como lido"""
        self.lido = True
    
    def marcar_resolvido(self):
        """Marca alerta como resolvido"""
        self.resolvido = True
        self.lido = True
    
    def to_dict(self) -> Dict:
        """Converte alerta para dicionário"""
        return {
            'id': self.id,
            'tipo': self.tipo,
            'categoria': self.categoria,
            'mensagem': self.mensagem,
            'exame': self.exame,
            'equipamento': self.equipamento,
            'detalhes': self.detalhes,
            'data_hora': self.data_hora.strftime('%Y-%m-%d %H:%M:%S'),
            'lido': self.lido,
            'resolvido': self.resolvido
        }
    
    def get_cor(self) -> str:
        """Retorna cor baseada no tipo"""
        cores_tipo = {
            TipoAlerta.CRITICO: CORES['erro'],
            TipoAlerta.ALTO: '#FF6F00',
            TipoAlerta.MEDIO: CORES['aviso'],
            TipoAlerta.BAIXO: '#FDD835',
            TipoAlerta.INFO: CORES['info']
        }
        return cores_tipo.get(self.tipo, CORES['info'])
    
    def get_icone(self) -> str:
        """Retorna ícone baseado no tipo"""
        icones_tipo = {
            TipoAlerta.CRITICO: '🔴',
            TipoAlerta.ALTO: '🟠',
            TipoAlerta.MEDIO: '🟡',
            TipoAlerta.BAIXO: '🟢',
            TipoAlerta.INFO: 'ℹ️'
        }
        return icones_tipo.get(self.tipo, 'ℹ️')


class GerenciadorAlertas:
    """Gerenciador central de alertas"""
    
    def __init__(self):
        self.alertas: List[Alerta] = []
        self.regras_ativas: Dict[str, bool] = self._carregar_regras_padrao()
        self.callbacks: List[callable] = []
    
    def _carregar_regras_padrao(self) -> Dict[str, bool]:
        """Carrega regras de alerta padrão"""
        return {
            'ct_alto': True,  # CT > limiar
            'ct_baixo': True,  # CT < limiar
            'controle_falhou': True,  # Controles fora do esperado
            'regra_violada': True,  # Regras de qualidade violadas
            'resultado_invalido': True,  # Resultado inválido
            'equipamento_problema': True,  # Problemas de equipamento
            'taxa_sucesso_baixa': True,  # Taxa de sucesso < 80%
        }
    
    def adicionar_alerta(self, alerta: Alerta):
        """Adiciona novo alerta"""
        self.alertas.insert(0, alerta)  # Insere no início (mais recente primeiro)
        self._notificar_callbacks()
    
    def criar_alerta(self, tipo: str, categoria: str, mensagem: str, **kwargs) -> Alerta:
        """Cria e adiciona novo alerta"""
        alerta = Alerta(tipo, categoria, mensagem, **kwargs)
        self.adicionar_alerta(alerta)
        return alerta
    
    def get_alertas_nao_lidos(self) -> List[Alerta]:
        """Retorna alertas não lidos"""
        return [a for a in self.alertas if not a.lido]
    
    def get_alertas_nao_resolvidos(self) -> List[Alerta]:
        """Retorna alertas não resolvidos"""
        return [a for a in self.alertas if not a.resolvido]
    
    def get_alertas_por_tipo(self, tipo: str) -> List[Alerta]:
        """Retorna alertas de um tipo específico"""
        return [a for a in self.alertas if a.tipo == tipo]
    
    def get_alertas_por_categoria(self, categoria: str) -> List[Alerta]:
        """Retorna alertas de uma categoria específica"""
        return [a for a in self.alertas if a.categoria == categoria]
    
    def marcar_todos_lidos(self):
        """Marca todos os alertas como lidos"""
        for alerta in self.alertas:
            alerta.marcar_lido()
        self._notificar_callbacks()
    
    def limpar_alertas_antigos(self, dias: int = 30):
        """Remove alertas mais antigos que X dias"""
        limite = datetime.now() - timedelta(days=dias)
        self.alertas = [a for a in self.alertas if a.data_hora >= limite]
        self._notificar_callbacks()
    
    def registrar_callback(self, callback: callable):
        """Registra callback para notificação de novos alertas"""
        self.callbacks.append(callback)
    
    def _notificar_callbacks(self):
        """Notifica todos os callbacks registrados"""
        for callback in self.callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Erro ao notificar callback: {e}")
    
    def exportar_alertas(self, filepath: str):
        """Exporta alertas para arquivo CSV"""
        if not self.alertas:
            return

        try:
            paths = config_service.get_paths()
            reports_dir = (
                paths.get("reports_dir")
                or paths.get("default_results_folder")
                or "reports"
            )
        except Exception:
            reports_dir = "reports"
        
        df = pd.DataFrame([a.to_dict() for a in self.alertas])
        policy = RetryPolicy.from_env()
        with CSVFileLock(filepath), open_with_retry(
            filepath,
            "w",
            newline="",
            encoding="utf-8",
            policy=policy,
        ) as handle:
            df.to_csv(handle, index=False, sep=";")
    
    def get_estatisticas(self) -> Dict:
        """Retorna estatísticas dos alertas"""
        return {
            'total': len(self.alertas),
            'nao_lidos': len(self.get_alertas_nao_lidos()),
            'nao_resolvidos': len(self.get_alertas_nao_resolvidos()),
            'criticos': len(self.get_alertas_por_tipo(TipoAlerta.CRITICO)),
            'altos': len(self.get_alertas_por_tipo(TipoAlerta.ALTO)),
            'medios': len(self.get_alertas_por_tipo(TipoAlerta.MEDIO)),
            'baixos': len(self.get_alertas_por_tipo(TipoAlerta.BAIXO)),
        }


class CentroNotificacoes(ctk.CTkToplevel):
    """Centro de Notificações - Janela principal de alertas"""
    
    def __init__(self, parent, gerenciador: GerenciadorAlertas):
        super().__init__(parent)
        
        self.gerenciador = gerenciador
        self.alertas_selecionados: List[str] = []
        
        # Configurar janela
        self.title("Centro de Notificações - IntegaGal")
        self.geometry("1200x700")
        
        # Centralizar janela
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (1200 // 2)
        y = (self.winfo_screenheight() // 2) - (700 // 2)
        self.geometry(f"1200x700+{x}+{y}")
        
        self._criar_interface()
        self._atualizar_lista()
        
        # Registrar callback para atualização automática
        self.gerenciador.registrar_callback(self._atualizar_lista)
    
    def _criar_interface(self):
        """Cria interface do centro de notificações"""
        # Header
        self._criar_header()
        
        # Filtros e estatísticas
        self._criar_filtros()
        
        # Lista de alertas
        self._criar_lista_alertas()
        
        # Rodapé com ações
        self._criar_rodape()
    
    def _criar_header(self):
        """Cria header com título e contador"""
        frame_header = ctk.CTkFrame(self, fg_color=CORES['primaria'], height=70)
        frame_header.pack(fill="x", padx=0, pady=0)
        frame_header.pack_propagate(False)
        
        # Título
        label_titulo = ctk.CTkLabel(
            frame_header,
            text="🔔 CENTRO DE NOTIFICAÇÕES",
            font=FONTES['titulo'],
            text_color=CORES['branco']
        )
        label_titulo.pack(side="left", padx=20)
        
        # Contador de não lidos
        stats = self.gerenciador.get_estatisticas()
        self.label_contador = ctk.CTkLabel(
            frame_header,
            text=f"📬 {stats['nao_lidos']} não lidos | 📋 {stats['total']} total",
            font=FONTES['corpo_bold'],
            text_color=CORES['branco']
        )
        self.label_contador.pack(side="right", padx=20)
    
    def _criar_filtros(self):
        """Cria seção de filtros e estatísticas"""
        frame_filtros = ctk.CTkFrame(self, fg_color=CORES['fundo'])
        frame_filtros.pack(fill="x", padx=20, pady=(20, 10))
        
        # Frame de filtros
        frame_controles = ctk.CTkFrame(frame_filtros, fg_color="transparent")
        frame_controles.pack(side="left", fill="x", expand=True)
        
        # Filtro de tipo
        ctk.CTkLabel(frame_controles, text="Tipo:", font=FONTES['corpo']).pack(side="left", padx=(0, 5))
        self.combo_tipo = ctk.CTkComboBox(
            frame_controles,
            values=["Todos", TipoAlerta.CRITICO, TipoAlerta.ALTO, TipoAlerta.MEDIO, TipoAlerta.BAIXO, TipoAlerta.INFO],
            width=120,
            command=lambda _: self._atualizar_lista()
        )
        self.combo_tipo.set("Todos")
        self.combo_tipo.pack(side="left", padx=5)
        
        # Filtro de categoria
        ctk.CTkLabel(frame_controles, text="Categoria:", font=FONTES['corpo']).pack(side="left", padx=(10, 5))
        self.combo_categoria = ctk.CTkComboBox(
            frame_controles,
            values=["Todos", CategoriaAlerta.CONTROLE, CategoriaAlerta.REGRA, 
                   CategoriaAlerta.EQUIPAMENTO, CategoriaAlerta.SISTEMA, CategoriaAlerta.QUALIDADE],
            width=140,
            command=lambda _: self._atualizar_lista()
        )
        self.combo_categoria.set("Todos")
        self.combo_categoria.pack(side="left", padx=5)
        
        # Filtro de status
        ctk.CTkLabel(frame_controles, text="Status:", font=FONTES['corpo']).pack(side="left", padx=(10, 5))
        self.combo_status = ctk.CTkComboBox(
            frame_controles,
            values=["Todos", "Não lidos", "Não resolvidos", "Lidos", "Resolvidos"],
            width=130,
            command=lambda _: self._atualizar_lista()
        )
        self.combo_status.set("Não resolvidos")
        self.combo_status.pack(side="left", padx=5)
        
        # Botões de ação
        frame_acoes = ctk.CTkFrame(frame_filtros, fg_color="transparent")
        frame_acoes.pack(side="right")
        
        btn_atualizar = ctk.CTkButton(
            frame_acoes,
            text="🔄 Atualizar",
            width=110,
            command=self._atualizar_lista
        )
        btn_atualizar.pack(side="left", padx=5)
        
        btn_marcar_lidos = ctk.CTkButton(
            frame_acoes,
            text="✓ Marcar Lidos",
            width=120,
            fg_color=CORES['secundaria'],
            hover_color="#1E8E85",
            command=self._marcar_todos_lidos
        )
        btn_marcar_lidos.pack(side="left", padx=5)
    
    def _criar_lista_alertas(self):
        """Cria lista de alertas com Treeview"""
        frame_lista = ctk.CTkFrame(self, fg_color="transparent")
        frame_lista.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Estilo do Treeview
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Alertas.Treeview",
            background="white",
            foreground=CORES['texto'],
            rowheight=40,
            fieldbackground="white",
            font=FONTES['corpo']
        )
        style.configure("Alertas.Treeview.Heading",
            background=CORES['primaria'],
            foreground=CORES['branco'],
            font=FONTES['corpo_bold'],
            padding=5
        )
        style.map('Alertas.Treeview',
            background=[('selected', CORES['primaria'])],
            foreground=[('selected', CORES['branco'])]
        )
        
        # Treeview
        colunas = ('tipo', 'categoria', 'mensagem', 'exame', 'data_hora', 'status')
        self.tree = ttk.Treeview(
            frame_lista,
            columns=colunas,
            show='tree headings',
            style="Alertas.Treeview",
            selectmode='extended'
        )
        
        # Configurar colunas
        self.tree.column('#0', width=50, minwidth=50, anchor='center')
        self.tree.column('tipo', width=80, minwidth=80, anchor='center')
        self.tree.column('categoria', width=110, minwidth=110, anchor='center')
        self.tree.column('mensagem', width=450, minwidth=200, anchor='w')
        self.tree.column('exame', width=250, minwidth=150, anchor='w')
        self.tree.column('data_hora', width=150, minwidth=130, anchor='center')
        self.tree.column('status', width=100, minwidth=100, anchor='center')
        
        # Headers
        self.tree.heading('#0', text='')
        self.tree.heading('tipo', text='Tipo')
        self.tree.heading('categoria', text='Categoria')
        self.tree.heading('mensagem', text='Mensagem')
        self.tree.heading('exame', text='Exame')
        self.tree.heading('data_hora', text='Data/Hora')
        self.tree.heading('status', text='Status')
        
        # Scrollbars
        scrollbar_v = ttk.Scrollbar(frame_lista, orient="vertical", command=self.tree.yview)
        scrollbar_h = ttk.Scrollbar(frame_lista, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)
        
        # Pack
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar_v.pack(side="right", fill="y")
        scrollbar_h.pack(side="bottom", fill="x")
        
        # Bind eventos
        self.tree.bind('<Double-Button-1>', self._on_double_click)
    
    def _criar_rodape(self):
        """Cria rodapé com contador e ações"""
        frame_rodape = ctk.CTkFrame(self, fg_color=CORES['fundo'], height=60)
        frame_rodape.pack(fill="x", padx=20, pady=(0, 20))
        frame_rodape.pack_propagate(False)
        
        # Contador
        self.label_exibindo = ctk.CTkLabel(
            frame_rodape,
            text="Exibindo 0 de 0 alertas",
            font=FONTES['corpo'],
            text_color=CORES['texto_claro']
        )
        self.label_exibindo.pack(side="left", padx=10)
        
        # Botões de ação
        btn_detalhes = ctk.CTkButton(
            frame_rodape,
            text="👁️ Ver Detalhes",
            width=130,
            command=self._ver_detalhes
        )
        btn_detalhes.pack(side="right", padx=5)
        
        btn_resolver = ctk.CTkButton(
            frame_rodape,
            text="✓ Resolver",
            width=120,
            fg_color=CORES['sucesso'],
            hover_color="#45A049",
            command=self._resolver_selecionados
        )
        btn_resolver.pack(side="right", padx=5)
        
        btn_exportar = ctk.CTkButton(
            frame_rodape,
            text="📊 Exportar",
            width=120,
            fg_color=CORES['secundaria'],
            hover_color="#1E8E85",
            command=self._exportar_alertas
        )
        btn_exportar.pack(side="right", padx=5)
    
    def _atualizar_lista(self):
        """Atualiza lista de alertas com filtros aplicados"""
        # Limpar árvore
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Aplicar filtros
        alertas_filtrados = self.gerenciador.alertas.copy()
        
        # Filtro de tipo
        tipo = self.combo_tipo.get()
        if tipo != "Todos":
            alertas_filtrados = [a for a in alertas_filtrados if a.tipo == tipo]
        
        # Filtro de categoria
        categoria = self.combo_categoria.get()
        if categoria != "Todos":
            alertas_filtrados = [a for a in alertas_filtrados if a.categoria == categoria]
        
        # Filtro de status
        status = self.combo_status.get()
        if status == "Não lidos":
            alertas_filtrados = [a for a in alertas_filtrados if not a.lido]
        elif status == "Não resolvidos":
            alertas_filtrados = [a for a in alertas_filtrados if not a.resolvido]
        elif status == "Lidos":
            alertas_filtrados = [a for a in alertas_filtrados if a.lido]
        elif status == "Resolvidos":
            alertas_filtrados = [a for a in alertas_filtrados if a.resolvido]
        
        # Preencher árvore
        for alerta in alertas_filtrados:
            status_str = "✓" if alerta.resolvido else ("👁️" if alerta.lido else "📬")
            
            self.tree.insert(
                '',
                'end',
                text=alerta.get_icone(),
                values=(
                    alerta.tipo,
                    alerta.categoria,
                    alerta.mensagem,
                    alerta.exame or '-',
                    alerta.data_hora.strftime('%d/%m/%Y %H:%M'),
                    status_str
                ),
                tags=(alerta.id,)
            )
        
        # Atualizar contadores
        stats = self.gerenciador.get_estatisticas()
        self.label_contador.configure(text=f"📬 {stats['nao_lidos']} não lidos | 📋 {stats['total']} total")
        self.label_exibindo.configure(text=f"Exibindo {len(alertas_filtrados)} de {stats['total']} alertas")
    
    def _on_double_click(self, event):
        """Handler para duplo clique"""
        self._ver_detalhes()
    
    def _ver_detalhes(self):
        """Mostra detalhes do alerta selecionado"""
        selecao = self.tree.selection()
        if not selecao:
            messagebox.showwarning("Aviso", "Selecione um alerta para ver detalhes.")
            return
        
        # Pegar primeiro selecionado
        item = self.tree.item(selecao[0])
        alerta_id = item['tags'][0]
        
        # Buscar alerta
        alerta = next((a for a in self.gerenciador.alertas if a.id == alerta_id), None)
        if not alerta:
            return
        
        # Marcar como lido
        alerta.marcar_lido()
        
        # Mostrar detalhes
        DetalhesAlerta(self, alerta)
        
        # Atualizar lista
        self._atualizar_lista()
    
    def _resolver_selecionados(self):
        """Marca alertas selecionados como resolvidos"""
        selecao = self.tree.selection()
        if not selecao:
            messagebox.showwarning("Aviso", "Selecione alertas para resolver.")
            return
        
        # Marcar como resolvidos
        for item in selecao:
            alerta_id = self.tree.item(item)['tags'][0]
            alerta = next((a for a in self.gerenciador.alertas if a.id == alerta_id), None)
            if alerta:
                alerta.marcar_resolvido()
        
        messagebox.showinfo("Sucesso", f"{len(selecao)} alerta(s) marcado(s) como resolvido(s).")
        self._atualizar_lista()
    
    def _marcar_todos_lidos(self):
        """Marca todos os alertas como lidos"""
        self.gerenciador.marcar_todos_lidos()
        messagebox.showinfo("Sucesso", "Todos os alertas foram marcados como lidos.")
        self._atualizar_lista()
    
    def _exportar_alertas(self):
        """Exporta alertas filtrados para CSV"""
        if not self.gerenciador.alertas:
            messagebox.showwarning("Aviso", "Não há alertas para exportar.")
            return
        
        # Criar pasta reports se não existir
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(reports_dir, f'alertas_{timestamp}.csv')
        
        try:
            self.gerenciador.exportar_alertas(filepath)
            messagebox.showinfo("Sucesso", f"Alertas exportados:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar alertas:\n{e}")


class DetalhesAlerta(ctk.CTkToplevel):
    """Janela de detalhes de um alerta"""
    
    def __init__(self, parent, alerta: Alerta):
        super().__init__(parent)
        
        self.alerta = alerta
        
        # Configurar janela
        self.title(f"Detalhes do Alerta - {alerta.tipo}")
        self.geometry("600x500")
        
        # Centralizar
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.winfo_screenheight() // 2) - (500 // 2)
        self.geometry(f"600x500+{x}+{y}")
        
        self._criar_interface()
    
    def _criar_interface(self):
        """Cria interface de detalhes"""
        # Header com ícone e tipo
        frame_header = ctk.CTkFrame(self, fg_color=self.alerta.get_cor(), height=80)
        frame_header.pack(fill="x")
        frame_header.pack_propagate(False)
        
        label_icone = ctk.CTkLabel(
            frame_header,
            text=self.alerta.get_icone(),
            font=('Segoe UI', 36)
        )
        label_icone.pack(side="left", padx=20)
        
        frame_info = ctk.CTkFrame(frame_header, fg_color="transparent")
        frame_info.pack(side="left", fill="both", expand=True)
        
        label_tipo = ctk.CTkLabel(
            frame_info,
            text=f"ALERTA {self.alerta.tipo.upper()}",
            font=FONTES['subtitulo'],
            text_color=CORES['branco']
        )
        label_tipo.pack(anchor="w", pady=(10, 0))
        
        label_categoria = ctk.CTkLabel(
            frame_info,
            text=f"Categoria: {self.alerta.categoria}",
            font=FONTES['corpo'],
            text_color=CORES['branco']
        )
        label_categoria.pack(anchor="w")
        
        # Conteúdo
        frame_conteudo = ctk.CTkFrame(self, fg_color="transparent")
        frame_conteudo.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Mensagem
        self._criar_campo(frame_conteudo, "📝 Mensagem:", self.alerta.mensagem)
        
        # Data/Hora
        self._criar_campo(frame_conteudo, "🕐 Data/Hora:", 
                         self.alerta.data_hora.strftime('%d/%m/%Y %H:%M:%S'))
        
        # Exame
        if self.alerta.exame:
            self._criar_campo(frame_conteudo, "🧪 Exame:", self.alerta.exame)
        
        # Equipamento
        if self.alerta.equipamento:
            self._criar_campo(frame_conteudo, "🔬 Equipamento:", self.alerta.equipamento)
        
        # Detalhes
        if self.alerta.detalhes:
            self._criar_campo(frame_conteudo, "📋 Detalhes:", self.alerta.detalhes, multiline=True)
        
        # Status
        status_str = "✓ Resolvido" if self.alerta.resolvido else ("👁️ Lido" if self.alerta.lido else "📬 Não lido")
        self._criar_campo(frame_conteudo, "📊 Status:", status_str)
        
        # Botões
        frame_botoes = ctk.CTkFrame(self, fg_color="transparent")
        frame_botoes.pack(fill="x", padx=20, pady=(0, 20))
        
        btn_fechar = ctk.CTkButton(
            frame_botoes,
            text="Fechar",
            width=120,
            command=self.destroy
        )
        btn_fechar.pack(side="right", padx=5)
        
        if not self.alerta.resolvido:
            btn_resolver = ctk.CTkButton(
                frame_botoes,
                text="✓ Marcar como Resolvido",
                width=180,
                fg_color=CORES['sucesso'],
                hover_color="#45A049",
                command=self._resolver
            )
            btn_resolver.pack(side="right", padx=5)
    
    def _criar_campo(self, parent, label: str, valor: str, multiline: bool = False):
        """Cria campo de informação"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=8)
        
        label_titulo = ctk.CTkLabel(
            frame,
            text=label,
            font=FONTES['corpo_bold'],
            anchor="w"
        )
        label_titulo.pack(anchor="w")
        
        if multiline:
            textbox = ctk.CTkTextbox(frame, height=100, font=FONTES['corpo'])
            textbox.pack(fill="both", expand=True, pady=(5, 0))
            textbox.insert("1.0", valor)
            textbox.configure(state="disabled")
        else:
            label_valor = ctk.CTkLabel(
                frame,
                text=valor,
                font=FONTES['corpo'],
                text_color=CORES['texto_claro'],
                anchor="w"
            )
            label_valor.pack(anchor="w", pady=(2, 0))
    
    def _resolver(self):
        """Marca alerta como resolvido"""
        self.alerta.marcar_resolvido()
        messagebox.showinfo("Sucesso", "Alerta marcado como resolvido.")
        self.destroy()


def gerar_alertas_reais(gerenciador: GerenciadorAlertas):
    """Gera alertas baseados nos dados reais do historico."""
    try:
        from services.reports.history_report import HistoryReportService
        df = HistoryReportService().ler_historico(limit=1000)
        if df is None or df.empty:
            gerenciador.criar_alerta(
                TipoAlerta.INFO,
                CategoriaAlerta.SISTEMA,
                "Nenhum dado de historico encontrado",
                detalhes="HistoryReportService retornou vazio. Execute analises para gerar dados.",
            )
            return

        # Analises invalidas
        status_col = df.get('status_corrida', df.get('status', pd.Series(dtype=str)))
        status_norm = status_col.fillna('').str.strip().str.lower()
        invalidas = int((status_norm == 'invalida').sum())
        if invalidas > 0:
            gerenciador.criar_alerta(
                TipoAlerta.ALTO,
                CategoriaAlerta.QUALIDADE,
                f"{invalidas} analise(s) com status Invalida",
                detalhes=f"Total de corridas marcadas como invalidas no historico.",
            )

        # GAL nao enviados
        if 'status_gal' in df.columns:
            gal_status = df['status_gal'].fillna('').str.strip()
            nao_enviados = int(gal_status.isin(['não enviável', 'nao enviavel', 'erro', '']).sum())
            if nao_enviados > 0:
                gerenciador.criar_alerta(
                    TipoAlerta.MEDIO,
                    CategoriaAlerta.SISTEMA,
                    f"{nao_enviados} registro(s) sem envio ao GAL",
                    detalhes="Registros com status GAL vazio ou nao enviavel.",
                )

        # Info resumo
        gerenciador.criar_alerta(
            TipoAlerta.INFO,
            CategoriaAlerta.SISTEMA,
            f"Historico com {len(df)} registros reais carregados",
            detalhes="Alertas gerados a partir dos dados reais do HistoryReportService.",
        )
    except Exception as e:
        gerenciador.criar_alerta(
            TipoAlerta.BAIXO,
            CategoriaAlerta.SISTEMA,
            f"Erro ao gerar alertas reais: {e}",
            detalhes="Fallback: execute a analise novamente.",
        )


def gerar_alertas_exemplo(gerenciador: GerenciadorAlertas):
    """Gera alertas de exemplo para demonstração (fallback)."""
    
    # Alertas críticos
    gerenciador.criar_alerta(
        TipoAlerta.CRITICO,
        CategoriaAlerta.CONTROLE,
        "Controle positivo falhou - Resultado não detectado",
        exame="VR1e2_Biomanguinhos_7500",
        equipamento="VR1e2",
        detalhes="O controle positivo esperado não foi detectado. Verificar integridade dos reagentes e repetir análise."
    )
    
    gerenciador.criar_alerta(
        TipoAlerta.CRITICO,
        CategoriaAlerta.REGRA,
        "Múltiplas regras de qualidade violadas",
        exame="CFXII_SARS-CoV-2",
        equipamento="CFXII",
        detalhes="Regras R1, R3 e R5 foram violadas simultaneamente. Resultado marcado como inválido."
    )
    
    # Alertas altos
    gerenciador.criar_alerta(
        TipoAlerta.ALTO,
        CategoriaAlerta.QUALIDADE,
        "Taxa de sucesso abaixo de 70%",
        equipamento="Bio7500",
        detalhes="Nas últimas 24h, apenas 65% das análises foram válidas. Recomenda-se manutenção preventiva."
    )
    
    gerenciador.criar_alerta(
        TipoAlerta.ALTO,
        CategoriaAlerta.EQUIPAMENTO,
        "CT valores consistentemente altos",
        exame="Quant5_HIV",
        equipamento="Quant5",
        detalhes="CTs acima de 35 em 80% das amostras positivas. Verificar calibração do equipamento."
    )
    
    # Alertas médios
    gerenciador.criar_alerta(
        TipoAlerta.MEDIO,
        CategoriaAlerta.CONTROLE,
        "Controle negativo com CT alto (>35)",
        exame="VR1e2_Dengue",
        equipamento="VR1e2",
        detalhes="CT detectado em controle negativo, mas acima do limiar de preocupação."
    )
    
    gerenciador.criar_alerta(
        TipoAlerta.MEDIO,
        CategoriaAlerta.REGRA,
        "Regra de qualidade R2 violada",
        exame="Bio7500_Zika",
        equipamento="Bio7500",
        detalhes="Diferença de CT entre replicatas maior que 2.0 ciclos."
    )
    
    # Alertas baixos
    gerenciador.criar_alerta(
        TipoAlerta.BAIXO,
        CategoriaAlerta.SISTEMA,
        "Atualização de software disponível",
        detalhes="Nova versão do IntegaGal (v2.1.0) disponível com correções de bugs."
    )
    
    # Alertas info
    gerenciador.criar_alerta(
        TipoAlerta.INFO,
        CategoriaAlerta.SISTEMA,
        "Backup automático concluído",
        detalhes="Backup diário dos dados realizado com sucesso às 02:00."
    )


# Teste standalone
if __name__ == '__main__':
    print("\n" + "="*60)
    print("TESTE DO SISTEMA DE ALERTAS - INTEGAGAL")
    print("="*60)
    
    # Criar gerenciador
    print("\n1. Criando gerenciador de alertas...")
    gerenciador = GerenciadorAlertas()
    print("   ✅ Gerenciador criado")
    
    # Gerar alertas de exemplo
    print("\n2. Gerando alertas de exemplo...")
    gerar_alertas_exemplo(gerenciador)
    stats = gerenciador.get_estatisticas()
    print(f"   ✅ {stats['total']} alertas gerados")
    print(f"      - Críticos: {stats['criticos']}")
    print(f"      - Altos: {stats['altos']}")
    print(f"      - Médios: {stats['medios']}")
    print(f"      - Baixos: {stats['baixos']}")
    
    # Abrir centro de notificações
    print("\n3. Abrindo Centro de Notificações...")
    app = ctk.CTk()
    app.withdraw()
    
    centro = CentroNotificacoes(app, gerenciador)
    
    print("   ✅ Centro de Notificações aberto")
    print("\n" + "="*60)
    print("INSTRUÇÕES DE TESTE:")
    print("="*60)
    print("\n📋 TESTE DE FILTROS:")
    print("   - Filtre por tipo (Crítico, Alto, Médio, Baixo)")
    print("   - Filtre por categoria (Controle, Regra, Equipamento, etc.)")
    print("   - Filtre por status (Não lidos, Não resolvidos, etc.)")
    print("\n👁️ TESTE DE VISUALIZAÇÃO:")
    print("   - Dê duplo clique em um alerta")
    print("   - Ou selecione e clique 'Ver Detalhes'")
    print("   - Verifique informações completas")
    print("\n✓ TESTE DE RESOLUÇÃO:")
    print("   - Selecione um ou mais alertas")
    print("   - Clique 'Resolver'")
    print("   - Verifique mudança de status")
    print("\n📊 TESTE DE EXPORTAÇÃO:")
    print("   - Clique 'Exportar'")
    print("   - Verifique arquivo CSV em reports/")
    print("\n" + "="*60 + "\n")
    
    app.mainloop()
    
    print("\n✅ Testes concluídos!")
