"""

Janela Principal Refatorada da aplicação IntegraGAL.

Versão modularizada para melhor manutenibilidade e escalabilidade.

"""



import os
import traceback

from tkinter import messagebox

from typing import Optional



import customtkinter as ctk

import matplotlib

from autenticacao.login import autenticar_usuario

from models import AppState

from services.core.config_service import config_service
from services.system_paths import BASE_DIR

from ui.menu_handler import MenuHandler

from ui.module_host import ModuleHost
from ui.navigation import NavigationManager
from ui.notification_backend import (
    configure_error_handler_for_ui,
    reset_error_handler_backend,
)
from ui.single_window_bootstrap import (
    create_app_with_rollback,
    resolve_single_window_enabled,
)
from ui.theme import Theme
from ui.status_manager import StatusManager

from utils.after_mixin import AfterManagerMixin

from utils.logger import registrar_log
from utils.gui_utils import safe_destroy_ctk_toplevel
from utils.suppress_ctk_errors import (
    instalar_filtro_bgerror,
    instalar_guardas_customtkinter,
)





# Configurar matplotlib para modo não-interativo

_PLOT_OK = True

try:

    matplotlib.use("TkAgg")

except Exception:

    _PLOT_OK = False



# Importações locais

# Linha comentada devido a alerta do ruff (E402): import em nível de módulo não posicionado no topo do arquivo.

# from autenticacao.login import autenticar_usuario

# Linha comentada devido a alerta do ruff (E402): import em nível de módulo não posicionado no topo do arquivo.

# from models import AppState

# Garantir BASE_DIR no sys.path

# Linha comentada devido a alerta do ruff (E402): import em nível de módulo não posicionado no topo do arquivo.

# from services.system_paths import BASE_DIR

# Importações dos novos módulos

# Linha comentada devido a alerta do ruff (E402): import em nível de módulo não posicionado no topo do arquivo.

# from ui.menu_handler import MenuHandler

# Linha comentada devido a alerta do ruff (E402): import em nível de módulo não posicionado no topo do arquivo.

# from ui.navigation import NavigationManager

# Linha comentada devido a alerta do ruff (E402): import em nível de módulo não posicionado no topo do arquivo.

# from ui.status_manager import StatusManager

# Linha comentada devido a alerta do ruff (E402): import em nível de módulo não posicionado no topo do arquivo.

# from utils.after_mixin import AfterManagerMixin

# Linha comentada devido a alerta do ruff (E402): import em nível de módulo não posicionado no topo do arquivo.

# from utils.logger import registrar_log





class MainWindow(AfterManagerMixin, ctk.CTk):

    """Janela principal refatorada da aplicação IntegraGAL"""



    def __init__(self, app_state: AppState):

        """

        Inicializa a janela principal



        Args:

            app_state: Estado da aplicação

        """

        super().__init__()

        # Instalar guardas de ciclo de vida e filtro Tcl para callbacks de UI.
        instalar_guardas_customtkinter()
        instalar_filtro_bgerror(self)
        configure_error_handler_for_ui(lambda: self)



        # Estado da aplicação

        self.app_state = app_state



        # Configuracao basica da janela principal
        self.title("IntegraGAL")
        self._configurar_janela()



        # Widgets principais

        self.main_frame: Optional[ctk.CTkFrame] = None
        self.content_frame: Optional[ctk.CTkFrame] = None
        self.module_host: Optional[ModuleHost] = None



        # Gerenciadores de módulos

        self.menu_handler: Optional[MenuHandler] = None

        self.status_manager: Optional[StatusManager] = None

        self.navigation_manager: Optional[NavigationManager] = None
        self.service_container = None



        # Criar interface

        self._criar_widgets()



        # Configurar eventos

        self.protocol("WM_DELETE_WINDOW", self._on_close)



        # Log de inicialização

        registrar_log(

            "Sistema", "Aplicação principal inicializada (versão refatorada).", "INFO"

        )



    def report_callback_exception(self, exc, val, tb):
        """Captura excecoes de callbacks Tkinter no log operacional."""
        try:
            exc_name = getattr(exc, "__name__", str(exc))
            registrar_log(
                "UI Callback",
                f"Excecao em callback Tkinter: {exc_name}: {val}",
                "ERROR",
                error_code="UI_CALLBACK_EXCEPTION",
            )
            tb_text = "".join(traceback.format_exception(exc, val, tb))
            registrar_log("UI Callback", tb_text, "DEBUG")
        except Exception:
            pass

    def _configurar_janela(self):
        """Configura as propriedades da janela principal"""
        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()

        largura_janela, altura_janela = 1024, 768
        x_pos = (largura_tela - largura_janela) // 2
        y_pos = (altura_tela - altura_janela) // 2

        self.geometry(f"{largura_janela}x{altura_janela}+{x_pos}+{y_pos}")
        self.minsize(800, 600)
        
        # Maximizar no Windows — tenta imediatamente e depois com delay
        try:
            self.state("zoomed")
        except Exception:
            pass
        
        def _maximizar_retry():
            try:
                if self.state() != "zoomed":
                    self.state("zoomed")
            except Exception:
                try:
                    sw = self.winfo_screenwidth()
                    sh = self.winfo_screenheight()
                    self.geometry(f"{sw}x{sh}+0+0")
                except Exception:
                    pass
        
        self.after(300, _maximizar_retry)

        ctk.set_appearance_mode("Light")

        try:
            icon_path = os.path.join(BASE_DIR, "assets", "icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

    def _criar_widgets(self):
        """Cria todos os widgets da interface principal"""
        self.configure(fg_color=Theme.BG_ROOT)

        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(expand=True, fill="both")
        
        self.main_frame.grid_columnconfigure(0, weight=0, minsize=200)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=0)  # Row for status bar

        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(
            self.main_frame, 
            width=200, 
            corner_radius=0, 
            fg_color=Theme.BG_PANEL,
            border_width=1,
            border_color=Theme.BORDER_DEFAULT
        )
        # NÃO grid ainda — será feito em on_login_success
        self.sidebar_frame.grid_propagate(False)
        self.sidebar_frame.pack_propagate(False)
        
        self._criar_titulo(self.sidebar_frame)
        self.sidebar_nav_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.sidebar_nav_frame.pack(fill="both", expand=True, padx=16, pady=16)

        # Container para a direita (Topbar + Conteudo)
        self.right_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.right_container.grid(row=0, column=1, sticky="nsew")
        
        # Topbar - Construida mas ocultada ate o login (se necessario)
        self.topbar_frame = ctk.CTkFrame(
            self.right_container, 
            height=64, 
            corner_radius=0, 
            fg_color=Theme.BG_CARD,
            border_width=1,
            border_color=Theme.BORDER_DEFAULT
        )
        # Não fazer pack aqui ainda, será feito no on_login_success
        self.topbar_frame.pack_propagate(False)
        self._construir_topbar()

        # Content Frame — padding reduzido para harmonizar com a sidebar
        self.content_frame = ctk.CTkFrame(self.right_container, fg_color="transparent")
        self.content_frame.pack(side="top", expand=True, fill="both", padx=0, pady=0)
        
        self.module_host = ModuleHost(self.content_frame, keep_cache=False)
        self._inicializar_gerenciadores()

    def _construir_topbar(self):
        """Constrói os elementos fixos da Topbar"""
        self.topbar_breadcrumbs = ctk.CTkLabel(
            self.topbar_frame, 
            text="Dashboard", 
            font=Theme.get_font_primary(size=14, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        self.topbar_breadcrumbs.pack(side="left", padx=32)
        
        # Área direita da topbar
        right_frame = ctk.CTkFrame(self.topbar_frame, fg_color="transparent")
        right_frame.pack(side="right", fill="y", padx=32)
        
        self.topbar_version_lbl = ctk.CTkLabel(
            right_frame,
            text="v2.4.0",
            font=Theme.get_font_primary(size=11),
            text_color=Theme.TEXT_MUTED
        )
        self.topbar_version_lbl.pack(side="left", padx=(10, 5))

        try:
            from services.core.config_service import config_service
            cfg_root = config_service.get("data_root")
            net_text = f"🔌 {cfg_root}" if cfg_root else "🖥️ Local"
            
            gal_integration = config_service.get("gal_integration", {})
            gal_url = gal_integration.get("base_url", "https://gal.saude.sc.gov.br")
            gal_env_text = "🌐 GAL: Produção" if "galteste" not in gal_url else "🧪 GAL: Teste"
            
            avancado = config_service.get("avancado", {})
            nivel_log = avancado.get("nivel_log", "INFO")
            
            gal_env_text = f"{gal_env_text} | 📝 Log: {nivel_log}"
        except Exception:
            net_text = "🖥️ Local"
            gal_env_text = "🌐 GAL: Produção | 📝 Log: INFO"

        self.topbar_network_lbl = ctk.CTkLabel(
            right_frame,
            text=net_text,
            font=Theme.get_font_primary(size=12),
            text_color=Theme.PRIMARY_BLUE
        )
        self.topbar_network_lbl.pack(side="left", padx=10)
        
        self.topbar_gal_env_lbl = ctk.CTkLabel(
            right_frame,
            text=gal_env_text,
            font=Theme.get_font_primary(size=12),
            text_color=Theme.COLOR_WARNING
        )
        self.topbar_gal_env_lbl.pack(side="left", padx=10)
        
        self.topbar_user_lbl = ctk.CTkLabel(
            right_frame, 
            text="Usuário", 
            font=Theme.get_font_primary(size=12, weight="bold"),
            text_color=Theme.TEXT_SECONDARY
        )
        self.topbar_user_lbl.pack(side="left", padx=(10, 0))

    def atualizar_topbar_gal(self):
        """Atualiza a label do GAL e Nível de Log na topbar baseado nas configurações mais recentes."""
        try:
            from services.core.config_service import config_service
            gal_integration = config_service.get("gal_integration", {})
            gal_url = gal_integration.get("base_url", "https://gal.saude.sc.gov.br")
            gal_env_text = "🌐 GAL: Produção" if "galteste" not in gal_url else "🧪 GAL: Teste"
            
            avancado = config_service.get("avancado", {})
            nivel_log = avancado.get("nivel_log", "INFO")
            
            full_text = f"{gal_env_text} | 📝 Log: {nivel_log}"
            
            if hasattr(self, "topbar_gal_env_lbl") and self.topbar_gal_env_lbl.winfo_exists():
                self.topbar_gal_env_lbl.configure(text=full_text)
        except Exception:
            pass

    def _criar_titulo(self, parent=None):
        """Cria o título da aplicação com subtítulo"""
        parent = parent or self.main_frame
        
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(pady=(24, 10), padx=20, fill="x")
        
        titulo = ctk.CTkLabel(
            container,
            text=" IntegraGAL",
            font=Theme.get_font_primary(size=20, weight="bold"),
            text_color=Theme.PRIMARY_BLUE
        )
        titulo.pack(anchor="w")
        
        sub = ctk.CTkLabel(
            container,
            text=" LIMS v2.4.0",
            font=Theme.get_font_primary(size=11),
            text_color=Theme.TEXT_MUTED
        )
        sub.pack(anchor="w", padx=2)

        autor = ctk.CTkLabel(
            container,
            text="Sistema desenvolvido por\nMárcio Pacheco de Andrade",
            font=Theme.get_font_primary(size=10),
            text_color=Theme.TEXT_MUTED,
            justify="left"
        )
        autor.pack(anchor="w", padx=2, pady=(5, 0))
        
        # Linha separadora
        linha = ctk.CTkFrame(parent, height=1, fg_color=Theme.BORDER_DEFAULT)
        linha.pack(fill="x", pady=(10, 0))

    def _inicializar_gerenciadores(self):
        """Inicializa todos os gerenciadores de módulos"""
        try:
            from services.core.service_container import get_service_container
            self.service_container = get_service_container(self.app_state)
            self.status_manager = StatusManager(self)
            self.navigation_manager = NavigationManager(self)
            self.menu_handler = MenuHandler(self, services=self.service_container)
            
            # Construir botoes da sidebar
            self.menu_handler.build_sidebar(self.sidebar_nav_frame)
            
            registrar_log("Sistema", "Todos os gerenciadores de módulo inicializados com sucesso.", "INFO")
        except Exception as e:
            import traceback
            registrar_log("Sistema", f"Erro ao inicializar gerenciadores: {e}", "ERROR")
            if hasattr(self, "status_manager") and self.status_manager:
                self.status_manager.update_status("Erro na inicialização dos módulos")

    def on_login_success(self, dados_usuario: dict) -> None:
        """
        Chamado pelo LoginPageEmbedded após sucesso.
        """
        self.app_state.usuario_logado = dados_usuario["usuario"]
        self.app_state.nivel_acesso = dados_usuario.get("nivel_acesso", "DIAGNOSTICO")
        
        # Mostrar o topbar
        self.topbar_frame.pack(side="top", fill="x", before=self.content_frame)
        
        # Mostrar o sidebar
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        # Atualizar nome do usuario na topbar
        nome_usuario = dados_usuario.get("usuario", "Usuário")
        nivel = self.app_state.nivel_acesso
        if hasattr(self, "topbar_user_lbl"):
            self.topbar_user_lbl.configure(text=f"{nome_usuario} ({nivel})")
        
        registrar_log("Sistema", f"Login executado. Nível: {self.app_state.nivel_acesso}", "INFO")
        
        # Navega para o dashboard central
        if self.navigation_manager:
            self.navigation_manager.navigate_to("dashboard")
        
        # Garantir que a janela continua maximizada após login
        try:
            self.state("zoomed")
        except Exception:
            pass

    def update_status(self, message: str):
        """Atualiza a mensagem de status (método de compatibilidade)"""
        if self.status_manager:
            self.status_manager.update_status(message)

    def get_main_frame(self):
        """Retorna o frame principal (método de compatibilidade)"""
        return self.main_frame

    def get_content_frame(self):

        """

        Retorna o frame de conteúdo central (área navegável).

        """

        return self.content_frame or self.main_frame



    def get_module_host(self) -> Optional[ModuleHost]:

        """

        Retorna o host de modulos para navegacao single-window.

        """

        return self.module_host



    def get_app_state(self):

        """

        Retorna o estado da aplicação (método de compatibilidade)



        Returns:

            Estado atual da aplicação

        """

        return self.app_state



    def _on_close(self):
        """Handler para fechamento da aplicacao"""
        if messagebox.askokcancel("Sair", "Tem a certeza que deseja fechar o sistema?", parent=self):
            registrar_log("Sistema", "Sistema encerrado pelo utilizador.", "INFO")
            reset_error_handler_backend()
            try:
                self.quit()
                self.destroy()
            except Exception:
                pass
            import os
            os._exit(0)




    def show_info(self, title: str, message: str):

        """

        Exibe uma mensagem de informação (método de compatibilidade)



        Args:

            title: Título da janela

            message: Mensagem a ser exibida

        """

        messagebox.showinfo(title, message, parent=self)



    def show_warning(self, title: str, message: str):

        """

        Exibe uma mensagem de aviso (método de compatibilidade)



        Args:

            title: Título da janela

            message: Mensagem a ser exibida

        """

        messagebox.showwarning(title, message, parent=self)



    def show_error(self, title: str, message: str):

        """

        Exibe uma mensagem de erro (método de compatibilidade)



        Args:

            title: Título da janela

            message: Mensagem a ser exibida

        """

        messagebox.showerror(title, message, parent=self)



    def get_navigation_manager(self):

        """

        Retorna o gerenciador de navegação (método de acesso público)



        Returns:

            Instância do NavigationManager

        """

        return self.navigation_manager



    def get_menu_handler(self):

        """

        Retorna o gerenciador de menu (método de acesso público)



        Returns:

            Instância do MenuHandler

        """

        return self.menu_handler



    def get_status_manager(self):

        """

        Retorna o gerenciador de status (método de acesso público)



        Returns:

            Instância do StatusManager

        """

        return self.status_manager



    def refresh_interface(self):

        """Atualiza toda a interface (método para refresh manual)"""

        try:

            self._criar_widgets()

            registrar_log("Sistema", "Interface atualizada manualmente.", "INFO")

        except Exception as e:

            registrar_log("Sistema", f"Erro ao atualizar interface: {e}", "ERROR")





def criar_aplicacao_principal():

    """

    Função factory para criar a aplicação principal



    Returns:

        Instância da MainWindow ou None se falhar

    """

    try:

        # Autenticar usuário

        usuario_autenticado = autenticar_usuario()

        if usuario_autenticado:

            # Criar estado da aplicação

            estado = AppState()

            estado.usuario_logado = usuario_autenticado["usuario"]

            estado.nivel_acesso = usuario_autenticado.get("nivel_acesso", "DIAGNOSTICO")



            # Criar e retornar janela principal

            root = MainWindow(app_state=estado)

            return root

        else:

            registrar_log(

                "Sistema", "Login falhou ou foi cancelado. Programa encerrado.", "INFO"

            )

            return None



    except Exception as e:

        registrar_log(

            "Sistema", f"Erro crítico ao criar aplicação principal: {e}", "CRITICAL"

        )

        messagebox.showerror(

            "Erro Crítico",

            f"Não foi possível inicializar a aplicação.\n\nDetalhes: {e}",

        )

        return None




def criar_aplicacao_principal_single_window():
    """
    Bootstrap single-window (Fase 4).
    Instancia a root CTk e redireciona imediatamente para o host de login.
    """
    root = None
    try:
        estado = AppState()
        root = MainWindow(app_state=estado)
        
        # Ao invés de popup, disparamos a rota de login no navigation_manager
        if root.navigation_manager:
            root.navigation_manager.navigate_to("login")
            
        registrar_log(
            "Sistema",
            "Aplicação principal inicializada (single-window embutida).",
            "INFO",
        )
        return root

    except Exception as e:
        registrar_log(
            "Sistema",
            f"Erro crítico ao criar aplicação principal (single-window): {e}",
            "CRITICAL",
        )
        try:
            if root is not None:
                root.destroy()
        except Exception:
            pass
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "Erro Crítico",
                f"Não foi possível inicializar a aplicação.\n\nDetalhes: {e}",
            )
        except Exception:
            pass
        return None




def _safe_get_window_state(window: ctk.CTk) -> str:
    """Retorna o estado da janela sem propagar excecoes."""
    try:
        return str(window.state())
    except Exception:
        return "unknown"


def _ensure_main_window_visible_after_login(window: ctk.CTk) -> None:
    """
    Forca estado visivel da janela principal apos login.

    Em Windows + CustomTkinter, quando `withdraw()` acontece antes do primeiro
    `mainloop()`, a janela pode permanecer oculta se o estado nao for normalizado.
    """
    try:
        window.deiconify()
    except Exception:
        pass

    try:
        window.state("normal")
    except Exception:
        pass

    try:
        window.update_idletasks()
        window.update()
    except Exception:
        pass

    for attr_name, value in (
        ("_window_exists", True),
        ("_withdraw_called_before_window_exists", False),
        ("_iconify_called_before_window_exists", False),
    ):
        try:
            if hasattr(window, attr_name):
                setattr(window, attr_name, value)
        except Exception:
            pass

    try:
        window.lift()
        window.focus_force()
    except Exception:
        pass

    try:
        window.attributes("-topmost", True)
        window.after(120, lambda: window.attributes("-topmost", False))
    except Exception:
        pass

    try:
        state = _safe_get_window_state(window)
        viewable = int(bool(window.winfo_viewable()))
        mapped = int(bool(window.winfo_ismapped()))
        geometry = window.geometry()
        registrar_log(
            "Sistema",
            (
                "Estado UI pos-login: "
                f"state={state}, viewable={viewable}, mapped={mapped}, geometry={geometry}"
            ),
            "DEBUG",
        )
    except Exception:
        pass

def criar_aplicacao_principal_por_modo():

    """

    Resolve modo de inicializacao da UI com rollback automatico.

    """

    def _config_get(key: str, default=None):
        try:
            return config_service.get(key, default)
        except Exception:
            return default

    single_window_enabled = resolve_single_window_enabled(_config_get)

    def _on_rollback(exc: BaseException) -> None:
        registrar_log(
            "Sistema",
            f"Falha no bootstrap single-window; revertendo para legado: {exc}",
            "WARNING",
        )

    app, mode = create_app_with_rollback(
        single_window_enabled=single_window_enabled,
        create_single=criar_aplicacao_principal_single_window,
        create_legacy=criar_aplicacao_principal,
        on_rollback=_on_rollback,
    )
    registrar_log("Sistema", f"Modo de bootstrap UI resolvido: {mode}", "INFO")
    return app




if __name__ == "__main__":

    """Ponto de entrada da aplicação (alternativo)"""

    import os



    os.chdir(BASE_DIR)



    app = criar_aplicacao_principal_por_modo()

    if app:

        app.mainloop()



