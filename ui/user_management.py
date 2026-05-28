"""
Painel de Gerenciamento de Usuários do Sistema IntegragalGit.
Fornece funcionalidades para gerenciar usuários do sistema.
"""

import uuid
from datetime import datetime
from tkinter import messagebox, simpledialog
import tkinter as tk

import bcrypt
import customtkinter as ctk
import pandas as pd
from ui.components.base_components import IGCard, IGButton, IGLabel, IGTextField, IGSelect
from ui.theme import Theme

from autenticacao.auth_service import AuthService
from utils.logger import registrar_log
from utils.gui_utils import safe_destroy_ctk_toplevel


class UserManagementPanel:
    """Painel de gerenciamento de usuários"""

    def __init__(self, main_window, usuario_logado: str, *, host_frame=None):
        """
        Inicializa o painel de gerenciamento de usuários

        Args:
            main_window: Janela principal da aplicação
            usuario_logado: Nome do usuário logado
            host_frame: Frame onde a página será renderizada (modo Single Window)
        """
        self.main_window = main_window
        self.usuario_logado = usuario_logado
        self.host_frame = host_frame
        self.page_mode = host_frame is not None
        self.auth_service = AuthService()
        # Configurar caminho do arquivo
        from services.core.config_service import config_service
        paths = config_service.get_paths()
        self.usuarios_path = paths.get("users_csv") or paths.get("credentials_csv")
        self._criar_interface()

    def _load_users_df(self) -> pd.DataFrame:
        """Carrega usuarios.csv via AuthService com schema normalizado."""
        return self.auth_service.load_users_df()

    def _save_users_df(self, df: pd.DataFrame, parent=None) -> bool:
        """
        Salva usuarios.csv via AuthService.

        Args:
            df: DataFrame com usuarios.
            parent: widget pai para mensagens (opcional).
        """
        ok = self.auth_service.save_users_df_actor_required(
            df,
            actor_username=self.usuario_logado,
            actor_access_level=str(
                getattr(self.main_window.app_state, "nivel_acesso", "") or ""
            ),
        )
        if not ok and parent is not None:
            messagebox.showerror(
                "Erro",
                "Falha ao salvar usuarios (verifique permissao e lock/rede).",
                parent=parent,
            )
        return ok

    def _criar_interface(self):
        """Cria a interface do painel de gerenciamento"""
        if self.page_mode:
            self.user_window = ctk.CTkFrame(self.host_frame, fg_color="transparent")
            # self.user_window.pack(expand=True, fill="both")  # Let ModuleHost handle it
        else:
            self.user_window = tk.Toplevel(self.main_window)
            self.user_window.title(" Gerenciamento de Usuários")
            self.user_window.geometry("1100x800")
            self.user_window.transient(self.main_window)
            self.user_window.grab_set()

            # Protocolo de fechamento correto
            self.user_window.protocol("WM_DELETE_WINDOW", self._fechar_janela)

            # Centrar janela
            self.user_window.update_idletasks()
            x = (self.user_window.winfo_screenwidth() // 2) - (1100 // 2)
            y = (self.user_window.winfo_screenheight() // 2) - (800 // 2)
            self.user_window.geometry(f"1100x800+{x}+{y}")

        # Header
        header_frame = ctk.CTkFrame(self.user_window)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        from ui.components.base_components import IGLabel
        from ui.theme import Theme
        title_label = IGLabel(
            header_frame,
            text=" Gerenciamento de Usuários",
            font=Theme.get_font_primary(size=24, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        title_label.pack(pady=15)

        info_label = IGLabel(
            header_frame,
            text=f"Operador: {self.usuario_logado} | Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            font=Theme.get_font_primary(size=12),
            text_color=Theme.TEXT_MUTED
        )
        info_label.pack(pady=(0, 15))

        # Toolbar
        self._criar_toolbar()

        # rea principal com scroll
        self.main_scroll_frame = ctk.CTkScrollableFrame(self.user_window, fg_color="transparent")
        self.main_scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Lista de usuários
        self._carregar_usuarios(self.main_scroll_frame)

    def _criar_toolbar(self):
        """Cria barra de ferramentas"""
        toolbar_frame = ctk.CTkFrame(self.user_window)
        toolbar_frame.pack(fill="x", padx=20, pady=(0, 10))

        # Botes de ao
        from ui.components.base_components import IGButton
        from ui.theme import Theme
        IGButton(
            toolbar_frame,
            text=" Adicionar Usuário",
            command=self._adicionar_usuario,
            width=150,
        ).pack(side="left", padx=5, pady=10)

        IGButton(
            toolbar_frame,
            text=" Alterar Senha",
            command=self._alterar_senha,
            width=150,
        ).pack(side="left", padx=5, pady=10)

        IGButton(
            toolbar_frame,
            text=" Remover Usuário",
            command=self._remover_usuario,
            variant="danger",
            width=150,
        ).pack(side="left", padx=5, pady=10)

        IGButton(
            toolbar_frame, text=" Buscar", command=self._buscar_usuario, width=100
        ).pack(side="right", padx=5, pady=10)

        IGButton(
            toolbar_frame, text=" Atualizar", command=self._atualizar_lista, width=100
        ).pack(side="right", padx=5, pady=10)

    def _carregar_usuarios(self, parent):
        """Carrega e exibe lista de usuários"""
        try:
            df = self._load_users_df()

            if df.empty:
                self._mostrar_mensagem_info(
                    parent, "Nenhum usuário cadastrado no sistema"
                )
                return

            # Contador de usuários
            total_usuarios = len(df)
            # Linha comentada devido a correo de compatibilidade: alguns arquivos CSV legados podem no possuir a coluna 'senha_hash'.
            # usuarios_ativos = len(
            #     df[df["senha_hash"].notna() & (df["senha_hash"] != "")]
            # )
            if "senha_hash" in df.columns:
                usuarios_ativos = len(
                    df[df["senha_hash"].notna() & (df["senha_hash"] != "")]
                )
            else:
                # Caso de arquivo legado sem coluna de hash: considera-se 0 usuários com senha configurada.
                usuarios_ativos = 0
            # Header com estatsticas
            stats_frame = ctk.CTkFrame(parent)
            stats_frame.pack(fill="x", pady=(0, 20))

            from ui.components.base_components import IGLabel
            from ui.theme import Theme
            IGLabel(
                stats_frame,
                text=f" Total de Usuários: {total_usuarios} |  Ativos: {usuarios_ativos}",
                font=Theme.get_font_primary(size=14, weight="bold"),
                text_color=Theme.TEXT_PRIMARY
            ).pack(pady=10)

            # Lista de usuários
            for idx, usuario in df.iterrows():
                self._criar_card_usuario(parent, usuario)

        except Exception as e:
            self._mostrar_mensagem_erro(parent, f"Erro ao carregar usuários: {str(e)}")

    def _criar_card_usuario(self, parent, usuario):
        """Cria card individual para cada usuário"""
        from ui.components.base_components import IGCard, IGLabel, IGButton
        from ui.theme import Theme
        card_frame = IGCard(parent)
        card_frame.pack(fill="x", pady=5)

        # Informaߵes principais
        info_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        # Nome do usuário
        nome_label = IGLabel(
            info_frame,
            text=f" {usuario.get('usuario', 'Desconhecido')}",
            font=Theme.get_font_primary(size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        nome_label.pack(anchor="w")

        # Nvel de acesso
        nivel_label = IGLabel(
            info_frame,
            text=f" Nível: {usuario.get('nivel_acesso', 'USER')}",
            font=Theme.get_font_primary(size=12),
            text_color=Theme.TEXT_MUTED
        )
        nivel_label.pack(anchor="w", pady=(2, 0))

        # Status
        senha_hash = usuario.get("senha_hash", "")
        if pd.notna(senha_hash) and senha_hash != "":
            status_text = " Ativo"
            status_color = Theme.COLOR_SUCCESS
        else:
            status_text = " Inativo"
            status_color = Theme.COLOR_DANGER

        status_label = IGLabel(
            info_frame,
            text=status_text,
            text_color=status_color,
            font=Theme.get_font_primary(size=12, weight="bold"),
        )
        status_label.pack(anchor="w", pady=(2, 0))

        # Informaߵes de hash (parcial)
        if pd.notna(senha_hash) and senha_hash != "":
            hash_preview = (
                senha_hash[:20] + "..." if len(senha_hash) > 20 else senha_hash
            )
            hash_label = IGLabel(
                info_frame,
                text=f" Hash: {hash_preview}",
                font=Theme.get_font_primary(size=10),
                text_color=Theme.TEXT_MUTED,
            )
            hash_label.pack(anchor="w", pady=(2, 0))

        # Botes de ao rpida
        acoes_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
        acoes_frame.pack(side="right", padx=10, pady=10)

        IGButton(
            acoes_frame,
            text="Editar",
            width=100,
            command=lambda u=usuario: self._editar_usuario_rapido(u),
        ).pack(side="left", padx=5)

        IGButton(
            acoes_frame,
            text="Senha",
            width=100,
            command=lambda u=usuario: self._alterar_senha_rapido(u),
        ).pack(side="left", padx=5)

        if usuario["usuario"] != self.usuario_logado:  # No permitir remover a si mesmo
            IGButton(
                acoes_frame,
                text="Remover",
                width=100,
                variant="danger",
                command=lambda u=usuario: self._remover_usuario_rapido(u),
            ).pack(side="left", padx=5)

    def _adicionar_usuario(self):
        """Abre diálogo para adicionar novo usuário"""
        try:
            dialog = AdicionarUsuarioDialog(self.user_window)
            if dialog.result:
                username, password, nivel = dialog.result
                self._salvar_usuario(username, password, nivel)
                self._atualizar_lista()
        except Exception as e:
            messagebox.showerror(
                "Erro", f"Erro ao abrir diálogo: {str(e)}", parent=self.user_window
            )
            # Fallback para mtodo simples
            self._adicionar_usuario_simples()

    def _editar_usuario(self):
        """Abre diálogo para editar usuário existente"""
        usuario = self._selecionar_usuario()
        if usuario is not None:
            self._editar_usuario_completo(usuario)

    def _editar_usuario_rapido(self, usuario):
        """Edita usuário rapidamente"""
        self._editar_usuario_completo(usuario)

    def _editar_usuario_completo(self, usuario):
        """Edita usuário com diálogo completo e melhor validação"""
        try:
            # Extrair informações do usuário de forma segura
            if isinstance(usuario, dict):
                usuario_nome = usuario.get("usuario", "usuário")
                usuario_nivel = usuario.get("nivel_acesso", "USER")
            else:
                usuario_nome = getattr(usuario, "usuario", "usuário")
                usuario_nivel = getattr(usuario, "nivel_acesso", "USER")

            novo_nivel = simpledialog.askstring(
                "Editar Usuário",
                f"Novo nvel de acesso para {usuario_nome}:\n(ADMIN, MASTER, DIAGNOSTICO, USER)",
                initialvalue=usuario_nivel,
                parent=self.user_window,
            )

            if novo_nivel and novo_nivel.strip():
                novo_nivel = novo_nivel.upper().strip()
                niveis_validos = ["ADMIN", "MASTER", "DIAGNOSTICO", "USER"]

                if novo_nivel in niveis_validos:
                    # Carregar arquivo
                    df = self._load_users_df()

                    # Verificar se o usuário existe
                    if usuario_nome in df["usuario"].values:
                        # Atualizar nvel
                        df.loc[df["usuario"] == usuario_nome, "nivel_acesso"] = (
                            novo_nivel
                        )

                        # Salvar (SEGURO)
                        if not self._save_users_df(df, parent=self.user_window):
                            return

                        messagebox.showinfo(
                            "Sucesso",
                            f"Nvel de {usuario_nome} alterado para {novo_nivel}",
                            parent=self.user_window,
                        )

                        if "registrar_log" in globals():
                            registrar_log(
                                "UserManagement",
                                f"Usuário {usuario_nome} editado por {self.usuario_logado}",
                                "INFO",
                            )

                        self._atualizar_lista()
                    else:
                        messagebox.showerror(
                            "Erro",
                            f"Usuário {usuario_nome} no encontrado no arquivo!",
                            parent=self.user_window,
                        )
                else:
                    messagebox.showerror(
                        "Erro",
                        f"Nvel '{novo_nivel}' no  vlido!\nUse: {', '.join(niveis_validos)}",
                        parent=self.user_window,
                    )
        except Exception as e:
            messagebox.showerror(
                "Erro", f"Erro ao editar usuário: {str(e)}", parent=self.user_window
            )

    def _alterar_senha(self):
        """Abre diálogo para alterar senha"""
        usuario = self._selecionar_usuario()
        if usuario is not None:
            self._alterar_senha_usuario(usuario)

    def _alterar_senha_rapido(self, usuario):
        """Altera senha rapidamente"""
        self._alterar_senha_usuario(usuario)

    def _alterar_senha_usuario(self, usuario):
        """Altera senha de usuário específico com melhor tratamento de erros"""
        try:
            # Extrair nome do usuário de forma segura
            if isinstance(usuario, dict):
                usuario_nome = usuario.get("usuario", "usuário")
            else:
                usuario_nome = getattr(usuario, "usuario", "usuário")

            nova_senha = simpledialog.askstring(
                "Alterar Senha",
                f"Nova senha para {usuario_nome}:",
                show="*",
                parent=self.user_window,
            )

            if nova_senha and nova_senha.strip():
                if len(nova_senha) < 6:
                    messagebox.showwarning(
                        "Aviso",
                        "A senha deve ter pelo menos 6 caracteres!",
                        parent=self.user_window,
                    )
                    return

                # Confirmar senha
                confirmar_senha = simpledialog.askstring(
                    "Confirmar Senha",
                    f"Confirme a senha para {usuario_nome}:",
                    show="*",
                    parent=self.user_window,
                )

                if nova_senha == confirmar_senha:
                    try:
                        # Gerar hash da nova senha
                        try:
                            import bcrypt

                            senha_bytes = nova_senha.encode("utf-8")
                            salt = bcrypt.gensalt()
                            hash_senha = bcrypt.hashpw(senha_bytes, salt).decode(
                                "utf-8"
                            )
                        except ImportError:
                            messagebox.showerror(
                                "Erro",
                                "Biblioteca bcrypt no disponvel!",
                                parent=self.user_window,
                            )
                            return

                        # Carregar arquivo
                        df = self._load_users_df()

                        # Verificar se o usuário existe
                        if usuario_nome in df["usuario"].values:
                            # Atualizar senha (campo correto  senha_hash)
                            df.loc[df["usuario"] == usuario_nome, "senha_hash"] = (
                                hash_senha
                            )

                            # Salvar (SEGURO)
                            if not self._save_users_df(df, parent=self.user_window):
                                return

                            messagebox.showinfo(
                                "Sucesso",
                                f"Senha do usuário {usuario_nome} alterada com sucesso!",
                                parent=self.user_window,
                            )

                            if "registrar_log" in globals():
                                registrar_log(
                                    "UserManagement",
                                    f"Senha do usuário {usuario_nome} alterada por {self.usuario_logado}",
                                    "INFO",
                                )

                            self._atualizar_lista()
                        else:
                            messagebox.showerror(
                                "Erro",
                                f"Usuário {usuario_nome} no encontrado!",
                                parent=self.user_window,
                            )

                    except Exception as e:
                        messagebox.showerror(
                            "Erro",
                            f"Erro ao alterar senha: {str(e)}",
                            parent=self.user_window,
                        )
                else:
                    messagebox.showwarning(
                        "Aviso", "As senhas no coincidem!", parent=self.user_window
                    )
            else:
                messagebox.showwarning(
                    "Aviso", "Senha no pode estar vazia!", parent=self.user_window
                )
        except Exception as e:
            messagebox.showerror(
                "Erro", f"Erro ao alterar senha: {str(e)}", parent=self.user_window
            )

    def _remover_usuario(self):
        """Remove usuário do sistema"""
        usuario = self._selecionar_usuario()
        if usuario is not None:
            self._remover_usuario_confirmado(usuario)

    def _remover_usuario_rapido(self, usuario):
        """Remove usuário rapidamente com confirmação"""
        self._remover_usuario_confirmado(usuario)

    def _remover_usuario_confirmado(self, usuario):
        """Remove usuário com confirmação"""
        if usuario["usuario"] == self.usuario_logado:
            messagebox.showwarning(
                "Aviso", "Você não pode remover a si mesmo!", parent=self.user_window
            )
            return

        if messagebox.askyesno(
            "Confirmar Remoção",
            f"Tem certeza que deseja remover o usuário '{usuario['usuario']}'?\n\nEsta ação não pode ser desfeita!",
            parent=self.user_window,
        ):
            try:
                # Carregar arquivo
                df = self._load_users_df()

                # Remover usuário
                df = df[df["usuario"] != usuario["usuario"]]

                # Salvar (SEGURO)
                if not self._save_users_df(df, parent=self.user_window):
                    return

                messagebox.showinfo(
                    "Sucesso",
                    f"Usuário {usuario['usuario']} removido com sucesso!",
                    parent=self.user_window,
                )
                registrar_log(
                    "UserManagement",
                    f"Usuário {usuario['usuario']} removido por {self.usuario_logado}",
                    "WARNING",
                )
                self._atualizar_lista()

            except Exception as e:
                messagebox.showerror(
                    "Erro",
                    f"Erro ao remover usuário: {str(e)}",
                    parent=self.user_window,
                )

    def _buscar_usuario(self):
        """Busca usuário por nome"""
        nome_busca = simpledialog.askstring(
            "Buscar Usuário",
            "Digite o nome do usuário para buscar:",
            parent=self.user_window,
        )

        if nome_busca and nome_busca.strip():
            try:
                df = self._load_users_df()


                # Normalizar nome para busca (case-insensitive)
                nome_busca = nome_busca.strip().lower()

                # Buscar usuários que contenham o nome
                usuarios_encontrados = df[
                    df["usuario"].str.lower().str.contains(nome_busca, na=False)
                ]

                if not usuarios_encontrados.empty:
                    # Mostrar resultados da busca
                    resultado = f" Resultados da busca por '{nome_busca}':\n\n"

                    for _, usuario in usuarios_encontrados.iterrows():
                        nivel = usuario.get("nivel_acesso", "USER")
                        resultado += f" {usuario['usuario']} |  {nivel}\n"

                    # Criar janela de resultados
                    resultado_window = ctk.CTkToplevel(self.user_window)
                    resultado_window.title("Resultados da Busca")
                    resultado_window.geometry("400x300")
                    resultado_window.transient(self.user_window)
                    resultado_window.grab_set()

                    # Texto com resultados
                    texto_resultado = ctk.CTkTextbox(resultado_window, height=200)
                    texto_resultado.pack(fill="both", expand=True, padx=20, pady=20)
                    texto_resultado.insert("1.0", resultado)
                    texto_resultado.configure(state="disabled")

                    # Boto fechar
                    IGButton(
                        resultado_window,
                        text="Fechar",
                        command=resultado_window.destroy,
                    ).pack(pady=10)

                else:
                    messagebox.showinfo(
                        "Busca",
                        f"Nenhum usuário encontrado com o nome '{nome_busca}'.",
                        parent=self.user_window,
                    )

            except Exception as e:
                messagebox.showerror(
                    "Erro", f"Erro durante a busca: {str(e)}", parent=self.user_window
                )

    def _sair_para_menu_principal(self):
        """Fecha a janela de gerenciamento de usuários e volta ao menu principal"""
        if not self.page_mode:
            self.user_window.destroy()
        self.main_window.deiconify()  # Volta a mostrar a janela principal

    def _atualizar_lista(self):
        """Atualiza lista de usuários"""
        try:
            if hasattr(self, "main_scroll_frame") and self.main_scroll_frame.winfo_exists():
                for child in self.main_scroll_frame.winfo_children():
                    child.destroy()
                self._carregar_usuarios(self.main_scroll_frame)
            else:
                self._criar_interface()

            messagebox.showinfo(
                "Atualizar", "Lista de usuários atualizada!", parent=self.user_window
            )

        except Exception as e:
            messagebox.showerror(
                "Erro", f"Erro ao atualizar lista: {str(e)}", parent=self.user_window
            )
    def _selecionar_usuario(self, parent):
        """Permite selecionar um usuario para edicao/remocao."""
        try:
            df = self._load_users_df()
            if df.empty:
                messagebox.showwarning(
                    "Aviso",
                    "Nenhum usuario cadastrado!",
                    parent=self.user_window,
                )
                return None

            if "usuario" not in df.columns:
                messagebox.showerror(
                    "Erro",
                    "Coluna 'usuario' nao encontrada no arquivo de usuarios.",
                    parent=self.user_window,
                )
                return None

            usuarios_opcoes = df["usuario"].dropna().astype(str).tolist()
            if not usuarios_opcoes:
                messagebox.showwarning(
                    "Aviso",
                    "Nenhum usuario encontrado na coluna de identificacao.",
                    parent=self.user_window,
                )
                return None

            usuario_selecionado = simpledialog.askstring(
                "Selecionar usuario",
                "Digite ou confirme o usuario a ser editado:",
                initialvalue=usuarios_opcoes[0],
                parent=self.user_window,
            )
            if not usuario_selecionado:
                return None

            filtro = (
                df["usuario"].astype(str).str.strip().str.lower()
                == str(usuario_selecionado).strip().lower()
            )
            df_filtrado = df[filtro]

            if df_filtrado.empty:
                messagebox.showerror(
                    "Erro",
                    f"Usuario '{usuario_selecionado}' nao encontrado.",
                    parent=self.user_window,
                )
                return None

            return df_filtrado.iloc[0].to_dict()

        except Exception as e:
            messagebox.showerror(
                "Erro",
                f"Erro ao selecionar usuario: {str(e)}",
                parent=self.user_window,
            )
            return None

    def _adicionar_usuario_simples(self):
        """Método simplificado para adicionar usuário (fallback)"""
        try:
            username = simpledialog.askstring(
                "Adicionar Usuário", "Nome do usuário:", parent=self.user_window
            )
            if not username or not username.strip():
                return

            password = simpledialog.askstring(
                "Adicionar Usuário", "Senha:", show="*", parent=self.user_window
            )
            if not password or len(password.strip()) < 6:
                messagebox.showwarning(
                    "Aviso",
                    "Senha deve ter pelo menos 6 caracteres!",
                    parent=self.user_window,
                )
                return

            nivel = simpledialog.askstring(
                "Adicionar Usuário",
                "Nvel (USER/ADMIN/OPERATOR):",
                initialvalue="USER",
                parent=self.user_window,
            )
            if not nivel:
                nivel = "USER"

            self._salvar_usuario(username.strip(), password.strip(), nivel.strip())
            self._atualizar_lista()

        except Exception as e:
            messagebox.showerror(
                "Erro", f"Erro ao adicionar usuário: {str(e)}", parent=self.user_window
            )

    def _salvar_usuario(self, username: str, password: str, nivel: str):
        """Salva novo usuario no sistema."""
        try:
            if not username or not password or not nivel:
                messagebox.showerror(
                    "Erro",
                    "Todos os campos sao obrigatorios!",
                    parent=self.user_window,
                )
                return

            if len(password) < 6:
                messagebox.showerror(
                    "Erro",
                    "A senha deve ter pelo menos 6 caracteres!",
                    parent=self.user_window,
                )
                return

            try:
                senha_bytes = password.encode("utf-8")
                salt = bcrypt.gensalt()
                hash_senha = bcrypt.hashpw(senha_bytes, salt).decode("utf-8")
            except Exception as bcrypt_error:
                messagebox.showerror(
                    "Erro",
                    f"Erro ao criptografar senha: {str(bcrypt_error)}",
                    parent=self.user_window,
                )
                return

            df = self._load_users_df()
            if "usuario" in df.columns and username in df["usuario"].values:
                messagebox.showwarning(
                    "Aviso",
                    f"Usuario '{username}' ja existe!",
                    parent=self.user_window,
                )
                return

            now_date = datetime.now().strftime("%Y-%m-%d")
            novo_usuario = {
                "id": uuid.uuid4().hex[:8],
                "usuario": username,
                "senha_hash": hash_senha,
                "nivel_acesso": nivel.upper(),
                "status": "ATIVO",
                "data_criacao": now_date,
                "ultimo_acesso": "",
                "tentativas_falhas": "0",
                "bloqueado_ate": "",
                "preferencias": "{}",
            }

            df = pd.concat([df, pd.DataFrame([novo_usuario])], ignore_index=True)
            if not self._save_users_df(df, parent=self.user_window):
                return

            messagebox.showinfo(
                "Sucesso",
                f"Usuario '{username}' criado com sucesso!\n\nNivel: {nivel.upper()}",
                parent=self.user_window,
            )

            registrar_log(
                "UserManagement",
                f"Usuario {username} criado por {self.usuario_logado}",
                "INFO",
            )

        except Exception as e:
            messagebox.showerror(
                "Erro",
                f"Erro inesperado: {str(e)}",
                parent=self.user_window,
            )

    def _mostrar_mensagem_erro(self, parent, mensagem: str):
        """Exibe mensagem de erro"""
        IGLabel(
            parent, text=f" {mensagem}", text_color="red", font=Theme.get_font_primary(size=14)
        ).pack(pady=20)

    def _mostrar_mensagem_info(self, parent, mensagem: str):
        """Exibe mensagem informativa"""
        IGLabel(
            parent, text=f"ج {mensagem}", text_color="blue", font=Theme.get_font_primary(size=14)
        ).pack(pady=20)

    def _fechar_janela(self):
        """Fecha a janela de gerenciamento corretamente"""
        try:
            # Liberar grab se estiver ativo
            if hasattr(self, "user_window") and self.user_window.winfo_exists():
                try:
                    self.user_window.grab_release()
                    # Forcar o release de qualquer grab ativo
                    if (
                        hasattr(self.user_window, "tk")
                        and self.user_window.tk.call("grab", "status", self.user_window)
                        != "none"
                    ):
                        self.user_window.tk.call("grab", "release", self.user_window)
                except Exception as grab_error:
                    print(f"Erro no grab: {grab_error}")

                safe_destroy_ctk_toplevel(self.user_window)

                # Garbage collection manual para garantir limpeza
                del self.user_window
        except Exception as e:
            print(f"Erro ao fechar janela: {e}")
            # Fallback - tentar ocultar mesmo em caso de erro
            try:
                if hasattr(self, "user_window"):
                    self.user_window.withdraw()
            except Exception:
                pass


    def _on_closing(self):
        """Handler para fechamento da janela"""
        self._fechar_janela()


from ui.components.base_components import IGLabel, IGButton, IGTextField, IGSelect
from ui.theme import Theme

class AdicionarUsuarioDialog:
    """Diálogo para adicionar novo usuário"""

    def __init__(self, parent):
        self.result = None

        # Janela de diálogo
        # Linha comentada devido a problemas recorrentes de fechamento com CTkToplevel em algumas verses do customtkinter.
        # self.dialog = ctk.CTkToplevel(parent)
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(" Adicionar Novo Usuário")
        self.dialog.geometry("450x650")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Centrar janela
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (650 // 2)
        self.dialog.geometry(f"450x650+{x}+{y}")

        self._criar_interface()
        self.dialog.wait_window()

    def _criar_interface(self):
        """Cria interface do diálogo"""
        # Frame principal
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Ttulo
        title_label = IGLabel(
            main_frame,
            text=" Adicionar Novo Usuário",
            font=Theme.get_font_primary(size=18, weight="bold"),
        )
        title_label.pack(pady=(20, 30))

        # Campo nome de usuário
        username_frame = ctk.CTkFrame(main_frame)
        username_frame.pack(fill="x", padx=20, pady=10)

        IGLabel(username_frame, text="Nome de Usuário:").pack(
            anchor="w", padx=10, pady=(10, 5)
        )
        self.username_entry = IGTextField(
            username_frame, placeholder_text="Digite o nome do usuário"
        )
        self.username_entry.pack(fill="x", padx=10, pady=(0, 10))

        # Campo senha
        password_frame = ctk.CTkFrame(main_frame)
        password_frame.pack(fill="x", padx=20, pady=10)

        IGLabel(password_frame, text="Senha:").pack(
            anchor="w", padx=10, pady=(10, 5)
        )
        self.password_entry = IGTextField(
            password_frame, placeholder_text="Digite a senha", show="*"
        )
        self.password_entry.pack(fill="x", padx=10, pady=(0, 10))

        # Campo confirmar senha
        confirm_password_frame = ctk.CTkFrame(main_frame)
        confirm_password_frame.pack(fill="x", padx=20, pady=10)

        IGLabel(confirm_password_frame, text="Confirmar Senha:").pack(
            anchor="w", padx=10, pady=(10, 5)
        )
        self.confirm_password_entry = IGTextField(
            confirm_password_frame, placeholder_text="Confirme a senha", show="*"
        )
        self.confirm_password_entry.pack(fill="x", padx=10, pady=(0, 10))

        # Campo nvel de acesso
        level_frame = ctk.CTkFrame(main_frame)
        level_frame.pack(fill="x", padx=20, pady=10)

        IGLabel(level_frame, text="Nível de Acesso:").pack(
            anchor="w", padx=10, pady=(10, 5)
        )
        self.level_combo = ctk.CTkComboBox(
            level_frame, values=["USER", "ADMIN", "OPERATOR"], state="readonly"
        )
        self.level_combo.set("USER")
        self.level_combo.pack(fill="x", padx=10, pady=(0, 10))

        # Botes
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=20, pady=20)

        IGButton(
            button_frame, text="Cancelar", command=self._cancelar, width=100
        ).pack(side="right", padx=(10, 0))

        IGButton(
            button_frame, text="Criar Usuário", command=self._criar_usuario, width=100
        ).pack(side="right")

    def _criar_usuario(self):
        """Valida e cria o usuário"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        confirm_password = self.confirm_password_entry.get()
        level = self.level_combo.get()

        # Validaߵes
        if not username:
            messagebox.showwarning(
                "Aviso", "Nome de usuário  obrigatório!", parent=self.dialog
            )
            return

        if not password:
            messagebox.showwarning("Aviso", "Senha  obrigatria!", parent=self.dialog)
            return

        if password != confirm_password:
            messagebox.showwarning(
                "Aviso", "As senhas no coincidem!", parent=self.dialog
            )
            return

        if len(password) < 6:
            messagebox.showwarning(
                "Aviso", "A senha deve ter pelo menos 6 caracteres!", parent=self.dialog
            )
            return

        # Sucesso
        self.result = (username, password, level)
        self.dialog.destroy()

    def _cancelar(self):
        """Cancela a operao"""
        self.dialog.destroy()




def create_user_management_page(parent, main_window):
    return UserManagementPanel(main_window=main_window, usuario_logado=getattr(main_window.app_state, 'usuario_logado', 'Admin'), host_frame=parent)

