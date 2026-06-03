# autenticacao/login.py
from __future__ import annotations

import sys
from tkinter import BooleanVar, TclError, messagebox
from typing import Optional

import customtkinter as ctk

from utils.after_mixin import AfterManagerMixin
from utils.gui_utils import center_window, safe_destroy_ctk_toplevel
from utils.logger import registrar_log

from ui.components.base_components import IGTextField
from .auth_service import AuthService

# T-AUD-023 / DHP politica-senha-lockout (OWASP A07): mensagem UI unica para
# qualquer falha de credencial, sem revelar contador nem estado de bloqueio.
MSG_GENERICA = "Credenciais inválidas. Verifique usuário e senha."


def _is_benign_tk_destroy_error(exc: BaseException) -> bool:
    """Identifica erros benignos de ciclo de vida do Tk ao destruir dialogs."""
    mensagem = str(exc).lower()
    return any(
        token in mensagem
        for token in (
            "can't delete tcl command",
            "application has been destroyed",
            "invalid command name",
            "can't invoke",
        )
    )


def _fechar_dialogo_login(login_dialog: "LoginDialog") -> None:
    """
    Fecha o dialogo de login de forma deterministica.

    Em bootstrap single-window o fluxo depende de `wait_window(...)`.
    Se o destroy ficar apenas assíncrono e falhar, a UI pode aparentar travar.
    """
    try:
        login_dialog.dispose()
    except Exception:
        pass

    try:
        login_dialog.grab_release()
    except Exception:
        pass

    try:
        login_dialog.destroy()
    except (TclError, RuntimeError) as exc:
        if _is_benign_tk_destroy_error(exc):
            # Em alguns cenarios o erro benigno ocorre com a janela ainda existente.
            try:
                if hasattr(login_dialog, "winfo_exists") and login_dialog.winfo_exists():
                    safe_destroy_ctk_toplevel(login_dialog, delay_ms=0)
            except Exception:
                pass
            return
        # Fallback seguro para casos de ciclo de vida complexo do Tk.
        safe_destroy_ctk_toplevel(login_dialog, delay_ms=0)
    except Exception:
        safe_destroy_ctk_toplevel(login_dialog, delay_ms=0)


def _cleanup_login_modal_state(root: ctk.CTk, login_window: "LoginDialog") -> None:
    """Remove possiveis residuos modais do login que podem bloquear a UI."""
    stale_dialogs = 0
    try:
        children = root.winfo_children() if hasattr(root, "winfo_children") else []
    except Exception:
        children = []

    for child in children:
        try:
            if not child.winfo_exists():
                continue
        except Exception:
            continue

        class_name = getattr(child, "__class__", type(child)).__name__
        if child is login_window or class_name == "LoginDialog":
            stale_dialogs += 1
            try:
                child.grab_release()
            except Exception:
                pass
            try:
                child.withdraw()
            except Exception:
                pass
            try:
                child.destroy()
            except Exception:
                pass

    try:
        current_grab = root.grab_current() if hasattr(root, "grab_current") else None
    except Exception:
        current_grab = None

    if current_grab is not None:
        try:
            current_grab.grab_release()
        except Exception:
            pass
        registrar_log("Login", "Grab residual liberado apos fechamento do login.", "DEBUG")

    try:
        root.grab_release()
    except Exception:
        pass
    try:
        root.attributes("-disabled", False)
    except Exception:
        pass

    try:
        remaining_grab = root.grab_current() if hasattr(root, "grab_current") else None
    except Exception:
        remaining_grab = None

    remaining = "nenhum" if remaining_grab is None else str(remaining_grab)
    registrar_log(
        "Login",
        f"Estado modal pos-login: dialogs_stale={stale_dialogs}, grab_atual={remaining}",
        "DEBUG",
    )


class LoginDialog(AfterManagerMixin, ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.auth_service = AuthService()
        self.usuario_autenticado: Optional[dict] = None
        self.closed_var = BooleanVar(master=self, value=False)

        self.title("Autenticacao - IntegraGAL")
        self.geometry("350x350")
        center_window(self, width=350, height=350)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._criar_widgets()
        self.grab_set()

    def _criar_widgets(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        ctk.CTkLabel(main_frame, text="Utilizador:").pack(
            padx=10, pady=(0, 5), anchor="w"
        )
        self.user_entry = IGTextField(main_frame)
        self.user_entry.pack(fill="x", padx=10)
        self.user_entry.focus()
        ctk.CTkLabel(main_frame, text="Senha:").pack(padx=10, pady=(10, 5), anchor="w")
        self.pass_entry = IGTextField(main_frame, show="*")
        self.pass_entry.pack(fill="x", padx=10)
        self.pass_entry.bind("<Return>", self.verificar)
        self.login_button = ctk.CTkButton(
            main_frame, text="Login", command=self.verificar
        )
        self.login_button.pack(pady=20)

    def verificar(self, event=None):
        username = self.user_entry.get()
        password = self.pass_entry.get()
        if not username or not password:
            messagebox.showwarning(
                "Atencao", "Utilizador e senha devem ser preenchidos.", parent=self
            )
            return

        # Caminho otimizado: autentica e retorna dados do usuario em uma leitura.
        dados_usuario = self.auth_service.autenticar_credenciais(username, password)
        if dados_usuario:
            registrar_log(
                "Login", f"Utilizador '{username}' autenticado com sucesso.", "INFO"
            )
            self.usuario_autenticado = dados_usuario
            self._on_close()
            return

        registrar_log(
            "Login",
            f"Tentativa de login falhada para o utilizador '{username}'.",
            "WARNING",
        )
        messagebox.showerror("Erro", MSG_GENERICA, parent=self)

    def _on_close(self, force_exit: bool = False):
        try:
            self.closed_var.set(True)
        except Exception:
            pass
        _fechar_dialogo_login(self)
        if force_exit:
            sys.exit(1)


def autenticar_usuario(master: Optional[ctk.CTk] = None) -> Optional[dict]:
    """
    Autentica o usuario atraves do dialogo de login.

    Args:
        master: Janela raiz existente para exibir o dialogo em modo modal.
            Quando None, cria uma root temporaria (modo legado).

    Returns:
        dict com dados do usuario (usuario, nivel_acesso, status) ou None.
    """
    owns_root = master is None
    root = master if master is not None else ctk.CTk()

    if owns_root:
        root.withdraw()
    try:
        from utils.suppress_ctk_errors import instalar_filtro_bgerror

        instalar_filtro_bgerror(root)
    except Exception:
        pass

    login_window = LoginDialog(master=root)
    registrar_log("Login", "Aguardando fechamento do dialogo de login.", "DEBUG")
    waited_with_variable = False
    try:
        if hasattr(root, "wait_variable") and hasattr(login_window, "closed_var"):
            root.wait_variable(login_window.closed_var)
            waited_with_variable = True
    except Exception:
        waited_with_variable = False

    if not waited_with_variable:
        root.wait_window(login_window)

    _cleanup_login_modal_state(root, login_window)

    registrar_log("Login", "Dialogo de login finalizado.", "DEBUG")
    usuario_logado = login_window.usuario_autenticado

    if owns_root:
        try:
            root.destroy()
        except Exception:
            pass
    return usuario_logado

class LoginPageEmbedded(ctk.CTkFrame):
    """
    Página de login embutida para a arquitetura Single Window.
    Substitui o LoginDialog modal por um fluxo de estado unificado.
    """
    def __init__(self, parent, main_window):
        super().__init__(parent, fg_color="transparent")
        self.main_window = main_window
        self.auth_service = AuthService()

        self._build_ui()

    def _build_ui(self):
        from ui.theme import Theme
        
        # Container centralizado
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(2, weight=1)

        content_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        content_wrapper.grid(row=1, column=1)

        try:
            import os
            from PIL import Image
            img_path = os.path.join("images", "sidebar_image.jpg")
            if os.path.exists(img_path):
                img = Image.open(img_path)
                target_width = 900
                aspect_ratio = img.height / img.width
                target_height = int(target_width * aspect_ratio)
                bg_img = ctk.CTkImage(light_image=img, dark_image=img, size=(target_width, target_height))
                img_lbl = ctk.CTkLabel(content_wrapper, image=bg_img, text="")
                img_lbl.pack(side="left", padx=(0, 40))
        except Exception as e:
            from utils.logger import registrar_log
            registrar_log("Login", f"Erro ao carregar sidebar_image.jpg: {e}", "WARNING")

        card = ctk.CTkFrame(
            content_wrapper, 
            width=400,
            height=450,
            corner_radius=15, 
            fg_color=Theme.BG_CARD,
            border_width=1,
            border_color=Theme.BORDER_DEFAULT
        )
        card.pack(side="right")
        card.pack_propagate(False)
        
        # Centralizando o conteúdo dentro do card
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(expand=True, fill="both", padx=40, pady=40)
        
        # Logo ou Título
        ctk.CTkLabel(
            content, 
            text="IntegraGAL", 
            font=Theme.get_font_primary(size=28, weight="bold"),
            text_color=Theme.PRIMARY_BLUE
        ).pack(pady=(0, 10))
        
        ctk.CTkLabel(
            content, 
            text="Autenticação Requerida", 
            font=Theme.get_font_primary(size=14),
            text_color=Theme.TEXT_SECONDARY
        ).pack(pady=(0, 30))

        # Campos
        ctk.CTkLabel(content, text="Utilizador:", font=Theme.get_font_primary(size=12, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(anchor="w", pady=(0, 5))
        self.user_entry = ctk.CTkEntry(content, height=40)
        self.user_entry.pack(fill="x", pady=(0, 15))
        self.user_entry.focus()

        ctk.CTkLabel(content, text="Senha:", font=Theme.get_font_primary(size=12, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(anchor="w", pady=(0, 5))
        self.pass_entry = ctk.CTkEntry(content, show="*", height=40)
        self.pass_entry.pack(fill="x", pady=(0, 20))
        self.pass_entry.bind("<Return>", self.verificar)

        from ui.components.buttons import PrimaryButton
        self.login_button = ctk.CTkButton(
            content, 
            text="Entrar", 
            command=self.verificar,
            height=45,
            fg_color=Theme.COLOR_SUCCESS,
            hover_color="#27ae60",
            font=Theme.get_font_primary(size=14, weight="bold")
        )
        self.login_button.pack(fill="x")

    def verificar(self, event=None):
        username = self.user_entry.get()
        password = self.pass_entry.get()
        
        if not username or not password:
            messagebox.showwarning(
                "Atenção", "Utilizador e senha devem ser preenchidos.", parent=self.main_window
            )
            return

        dados_usuario = self.auth_service.autenticar_credenciais(username, password)
        if dados_usuario:
            registrar_log(
                "Login", f"Utilizador '{username}' autenticado com sucesso via Single Window.", "INFO"
            )
            if hasattr(self.main_window, "on_login_success"):
                self.main_window.on_login_success(dados_usuario)
            return

        registrar_log(
            "Login",
            f"Tentativa de login falhada para o utilizador '{username}'.",
            "WARNING",
        )
        messagebox.showerror("Erro", MSG_GENERICA, parent=self.main_window)

def create_login_page(parent, main_window):
    """Factory para o NavigationManager."""
    return LoginPageEmbedded(parent, main_window)
