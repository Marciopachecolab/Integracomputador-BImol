"""
Gerenciador de Menu para a aplicação IntegraGAL.
Responsável por criar e gerenciar os botões do menu principal.
"""

from datetime import datetime
from pathlib import Path
from queue import Queue
from threading import Thread
from tkinter import filedialog, messagebox, simpledialog
from typing import Any, Optional, Protocol, Tuple
import re

import customtkinter as ctk

from exportacao.envio_gal import abrir_janela_envio_gal
from utils.gui_utils import (
    CTkSelectionDialog,
    center_window,
    register_modal_toplevel_usage,
)
from utils.logger import registrar_log
from services.core.runtime_flags import is_menu_analysis_legacy_compat_enabled
from services.legacy_audit.menu_catalog_fallback_audit import record_menu_catalog_fallback_event

class ExamCatalogPort(Protocol):
    """Contrato de catálogo de exames consumido pela camada de menu."""

    exames_disponiveis: Any

    def listar_exames_disponiveis(self) -> Any:
        ...


def _resolve_legacy_analysis_service_class():
    """Resolve classe legada apenas como compatibilidade transitória."""
    import importlib

    return getattr(importlib.import_module("services.analysis_service"), "AnalysisService")


# Compatibilidade transitória para consumidores/testes legados que ainda
# referenciam ui.menu_handler.AnalysisService.
try:  # pragma: no cover - caminho dependente de ambiente/imports opcionais
    AnalysisService = _resolve_legacy_analysis_service_class()
except Exception:  # pragma: no cover
    class AnalysisService:  # type: ignore
        pass


class _LegacyAnalysisCatalogPort:
    """Adapter legado para manter catálogo de exames disponível fora do container."""

    def __init__(self, app_state: Any) -> None:
        self._service = AnalysisService(app_state)

    @property
    def exames_disponiveis(self) -> Any:
        return getattr(self._service, "exames_disponiveis", None)

    def listar_exames_disponiveis(self) -> Any:
        if not hasattr(self._service, "listar_exames_disponiveis"):
            raise RuntimeError(
                "AnalysisService legado não expõe listar_exames_disponiveis."
            )
        return self._service.listar_exames_disponiveis()


class _LoteDataDialog(ctk.CTkToplevel):
    """Dialog modal para coletar dados da corrida (obrigatorios e opcionais)."""

    def __init__(
        self,
        master,
        *,
        nome_corrida: str = "",
        quem_fez_extracao: str = "",
        quem_preparou_placa: str = "",
        quem_analisou_placa: str = "",
        observacoes: str = "",
    ) -> None:
        super().__init__(master)
        self.result: Optional[dict[str, str]] = None
        self.title("Dados da Corrida")
        self.geometry("520x660")
        center_window(self, width=520, height=660)
        register_modal_toplevel_usage(self.__class__.__name__, context="analysis_lote_data")
        self.transient(master)
        self.grab_set()
        self._initial_nome_corrida = str(nome_corrida or "")
        self._initial_quem_fez_extracao = str(quem_fez_extracao or "")
        self._initial_quem_preparou_placa = str(quem_preparou_placa or "")
        self._initial_quem_analisou_placa = str(quem_analisou_placa or "")
        self._initial_observacoes = str(observacoes or "")
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self._build()

    def _build(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(frame, text="Numero do Lote/Kit:").pack(anchor="w", pady=(0, 4))
        self._entry_lote = ctk.CTkEntry(frame)
        self._entry_lote.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(frame, text="Data da realizacao (DD/MM/AAAA):").pack(anchor="w", pady=(0, 4))
        self._entry_data = ctk.CTkEntry(frame)
        self._entry_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self._entry_data.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            frame,
            text="Nome da corrida (opcional):",
        ).pack(anchor="w", pady=(0, 4))
        self._entry_nome_corrida = ctk.CTkEntry(frame)
        self._entry_nome_corrida.insert(0, self._initial_nome_corrida)
        self._entry_nome_corrida.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            frame,
            text="Quem fez extracao (opcional):",
        ).pack(anchor="w", pady=(0, 4))
        self._entry_quem_fez_extracao = ctk.CTkEntry(frame)
        self._entry_quem_fez_extracao.insert(0, self._initial_quem_fez_extracao)
        self._entry_quem_fez_extracao.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            frame,
            text="Quem preparou placa (opcional):",
        ).pack(anchor="w", pady=(0, 4))
        self._entry_quem_preparou_placa = ctk.CTkEntry(frame)
        self._entry_quem_preparou_placa.insert(0, self._initial_quem_preparou_placa)
        self._entry_quem_preparou_placa.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            frame,
            text="Quem analisou a placa (opcional):",
        ).pack(anchor="w", pady=(0, 4))
        self._entry_quem_analisou_placa = ctk.CTkEntry(frame)
        self._entry_quem_analisou_placa.insert(0, self._initial_quem_analisou_placa)
        self._entry_quem_analisou_placa.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            frame,
            text="Observacoes (opcional):",
        ).pack(anchor="w", pady=(0, 4))
        self._textbox_observacoes = ctk.CTkTextbox(frame, height=80)
        self._textbox_observacoes.insert("1.0", self._initial_observacoes)
        self._textbox_observacoes.pack(fill="x", pady=(0, 14))

        button_bar = ctk.CTkFrame(frame, fg_color="transparent")
        button_bar.pack(fill="x")
        button_bar.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(button_bar, text="Confirmar", command=self._on_confirm).grid(
            row=0, column=0, padx=(0, 6), sticky="ew"
        )
        ctk.CTkButton(
            button_bar,
            text="Cancelar",
            command=self._on_cancel,
            fg_color="gray",
        ).grid(row=0, column=1, padx=(6, 0), sticky="ew")

    @staticmethod
    def _sanitize_optional_text(value: str, max_len: int) -> str:
        """Sanitiza texto opcional sem bloquear o fluxo."""
        return str(value or "").strip()[:max_len]

    def _on_confirm(self) -> None:
        lote = self._entry_lote.get().strip()
        data_exame = self._entry_data.get().strip()

        if not lote:
            messagebox.showwarning("Campo obrigatorio", "Informe o numero do lote/kit.", parent=self)
            return

        try:
            datetime.strptime(data_exame, "%d/%m/%Y")
        except Exception:
            messagebox.showwarning(
                "Data invalida",
                "Informe a data no formato DD/MM/AAAA.",
                parent=self,
            )
            return

        self.result = {
            "lote": lote,
            "data_exame": data_exame,
            "nome_corrida": self._sanitize_optional_text(self._entry_nome_corrida.get(), 120),
            "quem_fez_extracao": self._sanitize_optional_text(
                self._entry_quem_fez_extracao.get(),
                80,
            ),
            "quem_preparou_placa": self._sanitize_optional_text(
                self._entry_quem_preparou_placa.get(),
                80,
            ),
            "quem_analisou_placa": self._sanitize_optional_text(
                self._entry_quem_analisou_placa.get(),
                80,
            ),
            "observacoes": self._sanitize_optional_text(
                self._textbox_observacoes.get("1.0", "end"),
                500,
            ),
        }
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()

    def show(self) -> Optional[dict[str, str]]:
        self.wait_window()
        return self.result


class MenuHandler:
    """Gerenciador de menu da aplicação"""

    def __init__(self, main_window, services=None):
        """
        Inicializa o gerenciador de menu.
        
        OTIMIZAÇÃO (P1 - Dependency Injection):
        Aceita ServiceContainer para desacoplar MenuHandler dos services concretos.

        Args:
            main_window: Instância da janela principal (App)
            services: ServiceContainer (opcional, cria um se não fornecido)
        """
        self.main_window = main_window
        
        # P1 FIX: Dependency Injection (com fallback se falhar)
        try:
            if services is None:
                from services.core.service_container import get_service_container
                services = get_service_container(self.main_window.app_state)
            self.services = services
        except Exception as e:
            # Se ServiceContainer falhar, continuar sem ele
            registrar_log("MenuHandler", f"ServiceContainer não disponíÂ­vel: {e}", "WARNING")
            self.services = None
        
        # COMPATIBILIDADE: Mantém referência direta para não quebrar código existente
        if self.services is not None and hasattr(self.services, "bind_app_state"):
            try:
                self.services.bind_app_state(self.main_window.app_state)
            except Exception as e:
                registrar_log("MenuHandler", f"Falha ao vincular app_state no container: {e}", "WARNING")

        # Controle de instâncias únicas de janelas
        self._resultado_window = None
        self._gal_window = None
        self._dashboard_window = None
        
        # Flags para prevenir race condition
        self._criando_janela_resultado = False
        self._criando_janela_gal = False
        self._criando_janela_dashboard = False
        self._analise_em_execucao = False
        self._analise_result_queue: Optional[Queue] = None
        self._analise_worker: Optional[Thread] = None
        self._menu_frame: Optional[ctk.CTkFrame] = None

        self._registrar_rotas_single_window()
        self._inicializar_menu_principal()

    def _get_analysis_use_case(self):
        """
        Resolve o caso de uso de análise via container.

        Nao instancia AnalysisService diretamente na UI.
        """
        services = getattr(self, "services", None)
        if services is None:
            raise RuntimeError("Container de servicos indisponivel para análise.")
        if not hasattr(services, "analysis"):
            raise RuntimeError("Container nao expoe use case de análise.")
        return services.analysis

    def _get_exam_catalog_port(self) -> ExamCatalogPort:
        """
        Resolve port de catálogo de exames para a UI.

        Prioriza `services.analysis` quando disponível e usa adapter legado
        quando o container não expõe o port e a compatibilidade está ativa.
        """
        services = getattr(self, "services", None)
        analysis_port = getattr(services, "analysis", None) if services is not None else None
        if analysis_port is not None and hasattr(analysis_port, "listar_exames_disponiveis"):
            return analysis_port
        usuario = getattr(getattr(self.main_window, "app_state", None), "usuario_logado", None)
        if not is_menu_analysis_legacy_compat_enabled(user_id=usuario):
            mensagem = "Fallback de compatibilidade legada desabilitado para catalogo de exames."
            self._registrar_telemetria_fallback_catalogo_legado(
                mode="legacy_fallback",
                outcome="blocked",
                error=mensagem,
            )
            raise RuntimeError(mensagem)
        try:
            adapter = _LegacyAnalysisCatalogPort(self.main_window.app_state)
        except Exception as exc:
            self._registrar_telemetria_fallback_catalogo_legado(
                mode="legacy_fallback",
                outcome="error",
                error=str(exc),
            )
            raise
        self._registrar_telemetria_fallback_catalogo_legado(
            mode="legacy_fallback",
            outcome="used",
        )
        return adapter

    def _registrar_telemetria_fallback_catalogo_legado(
        self,
        *,
        mode: str,
        outcome: str,
        error: str = "",
    ) -> None:
        app_state = getattr(self.main_window, "app_state", None)
        actor = str(getattr(app_state, "usuario_logado", "") or "")
        event: dict[str, str] = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "actor": actor,
            "mode": str(mode or ""),
            "outcome": str(outcome or ""),
        }
        if error:
            event["error"] = str(error)

        if app_state is not None:
            events = getattr(app_state, "legacy_exam_catalog_fallback_events", None)
            if not isinstance(events, list):
                events = []
            events.append(event)
            setattr(app_state, "legacy_exam_catalog_fallback_events", events[-200:])
            setattr(app_state, "legacy_exam_catalog_fallback_last_event", event)

        try:
            record_menu_catalog_fallback_event(logs_dir=None, event=event, max_rows=2000)
        except Exception as exc:  # pragma: no cover
            registrar_log(
                "MenuCatalog",
                f"Falha ao persistir trilha auditavel de fallback: {exc}",
                "WARNING",
            )

        nivel = "WARNING" if outcome in {"blocked", "error"} else "INFO"
        registrar_log(
            "MenuCatalog",
            (
                "legacy_fallback "
                f"mode={event['mode']} outcome={event['outcome']} "
                f"actor={actor or '-'} error={event.get('error', '-')}"
            ),
            nivel,
        )

    def _registrar_rotas_single_window(self) -> None:
        """Registra rotas de módulos no modo single-window (quando disponíÂ­vel)."""
        nav = getattr(self.main_window, "navigation_manager", None)
        if not nav or not hasattr(nav, "register_module"):
            return
        nav.register_module("main_menu", self._criar_botoes_menu)
        nav.register_module("administracao", self._criar_admin_panel_page)
        nav.register_module("novo_exame", self._criar_exam_creator_page)
        nav.register_module("tela_configuracoes", self._criar_configuracoes_page)
        nav.register_module("dashboard", self._criar_dashboard_page)
        nav.register_module("graficos_qualidade", self._criar_graficos_page)
        nav.register_module("historico_analises", self._criar_historico_page)
        nav.register_module("analise_completa", self._criar_analise_completa_page)
        nav.register_module("gal", self._criar_gal_page)
        nav.register_module("extracao", self._criar_extracao_page)
        nav.register_module("login", self._criar_login_page)
        nav.register_module("relatorios", self._criar_relatorios_page)
        nav.register_module("usuarios", self._criar_user_management_page)
        nav.register_module("analise_setup", self._criar_analise_setup_page)
        nav.register_module("analise_completa", self._criar_analise_completa_page)

    def _criar_user_management_page(self, parent):
        from ui.user_management import create_user_management_page
        return create_user_management_page(parent, self.main_window).user_window
        
    def _criar_analise_setup_page(self, parent):
        from ui.modules.analise_setup import create_analise_setup_page
        return create_analise_setup_page(parent, self.main_window)
        
    def _criar_analise_completa_page(self, parent):
        from ui.janela_analise_completa import JanelaAnaliseCompleta
        from datetime import datetime
        app_state = self.main_window.app_state
        return JanelaAnaliseCompleta(
            root=self.main_window,
            dataframe=app_state.resultados_analise,
            status_corrida="N/A",
            num_placa="N/A",
            data_placa_formatada=getattr(app_state, "data_exame", datetime.now().strftime("%d/%m/%Y")),
            agravos=["SC2", "HMPV", "INF A", "INF B", "ADV", "RSV", "HRV"],
            usuario_logado=getattr(app_state, "usuario_logado", "Desconhecido"),
            exame=getattr(app_state, "exame_selecionado", ""),
            lote=getattr(app_state, "lote", ""),
            arquivo_corrida=getattr(app_state, "caminho_arquivo_corrida", ""),
            bloco_tamanho=getattr(app_state, "bloco_tamanho", 1),
            numero_extracao=getattr(app_state, "numero_extracao", ""),
            host_frame=parent,
            on_close_callback=lambda: self.main_window.navigation_manager.navigate_to("dashboard"),
        )
    
    def _criar_relatorios_page(self, parent):
        from ui.modules.reports import create_reports_page
        return create_reports_page(parent, self.main_window)
    
    def _criar_login_page(self, parent):
        from autenticacao.login import create_login_page
        return create_login_page(parent, self.main_window)

    def _criar_extracao_page(self, parent):
        from ui.modules.extraction_plate_mapping import create_extraction_mapping_page
        return create_extraction_mapping_page(parent, self.main_window)
        
    def _verificar_permissao(self, niveis_permitidos: list) -> bool:
        """
        Verifica se o usuário logado tem permissão para acessar determinado módulo.
        
        Args:
            niveis_permitidos: Lista de níÂ­veis de acesso permitidos (ex: ["ADMIN", "MASTER"])
        
        Returns:
            True se tem permissão, False caso contrário
        """
        nivel_usuario = self.main_window.app_state.nivel_acesso
        if not nivel_usuario:
            return False
        return nivel_usuario.upper() in [n.upper() for n in niveis_permitidos]

    def _inicializar_menu_principal(self) -> None:
        """
        Inicializa o menu principal (descontinuado no modo sidebar_nav, mantido para legado).
        """
        nav = getattr(self.main_window, "navigation_manager", None)
        if nav and hasattr(nav, "register_module"):
            # Apenas retorna, o fluxo de login cuidará de mostrar o dashboard depois
            return
        self._criar_rodape_sidebar(parent_frame)

    def set_active_menu(self, active_title: str):
        """Atualiza o estado visual (destaque) do botão ativo no menu lateral."""
        if not hasattr(self, "_sidebar_buttons"):
            return
        from ui.theme import Theme
        for title, btn in self._sidebar_buttons.items():
            if title == active_title:
                btn.configure(fg_color=Theme.PRIMARY_BLUE_SOFT, text_color=Theme.PRIMARY_BLUE, font=Theme.get_font_primary(size=13, weight="bold"))
            else:
                btn.configure(fg_color="transparent", text_color=Theme.TEXT_PRIMARY, font=Theme.get_font_primary(size=13, weight="normal"))

    def build_sidebar(self, parent_frame: ctk.CTkFrame):
        """
        Constrói os botões da barra lateral de navegação.
        """
        from ui.theme import Theme
        
        # Botão principal (Call to Action)
        btn_cta = ctk.CTkButton(
            parent_frame,
            text="+ Iniciar Nova Placa",
            font=Theme.get_font_primary(size=14, weight="bold"),
            fg_color=Theme.PRIMARY_BLUE,
            hover_color=Theme.PRIMARY_BLUE_HOVER,
            command=self._wrap_menu_action("Nova Placa", self.abrir_busca_extracao),
            height=44,
            corner_radius=22
        )
        btn_cta.pack(fill="x", pady=(0, 24))

        # Título da seção
        lbl_section = ctk.CTkLabel(
            parent_frame,
            text="MAIN MENU",
            font=Theme.get_font_primary(size=11, weight="bold"),
            text_color=Theme.TEXT_MUTED,
            anchor="w"
        )
        lbl_section.pack(fill="x", pady=(0, 8), padx=8)

        # Configuração para os botões flat
        btn_kwargs = {
            "font": Theme.get_font_primary(size=13),
            "fg_color": "transparent",
            "text_color": Theme.TEXT_PRIMARY,
            "hover_color": Theme.PRIMARY_BLUE_SOFT,
            "anchor": "w",
            "height": 36,
            "corner_radius": 6
        }

        # Menu itens
        botoes = [
            ("Dashboard", self.abrir_dashboard),
            ("Mapeamento", self.abrir_busca_extracao),
            ("Realizar Análise", self.realizar_analise),
            ("Resultados", self.mostrar_resultados_analise),
            ("Enviar GAL", self.enviar_para_gal),
            ("Administração", self.abrir_administracao),
            ("Usuários", self.gerenciar_usuarios),
            ("Incluir Exames", self.incluir_novo_exame),
            ("Relatórios", self.gerar_relatorios),
            ("Configurações", self.abrir_configuracoes),
        ]

        self._sidebar_buttons = {}
        for texto, comando in botoes:
            def criar_comando_com_titulo(titulo, cmd):
                def wrapper():
                    if hasattr(self.main_window, "topbar_breadcrumbs"):
                        self.main_window.topbar_breadcrumbs.configure(text=titulo)
                    self.set_active_menu(titulo)
                    cmd()
                return wrapper
                
            btn = ctk.CTkButton(
                parent_frame,
                text=texto,
                command=self._wrap_menu_action(texto, criar_comando_com_titulo(texto, comando)),
                **btn_kwargs
            )
            btn.pack(fill="x", pady=2, padx=8)
            self._sidebar_buttons[texto] = btn
            
        # Botão de Sair no final
        btn_sair = ctk.CTkButton(
            parent_frame,
            text="Log out",
            command=self._wrap_menu_action("Sair", self.main_window._on_close),
            **btn_kwargs
        )
        btn_sair.pack(fill="x", pady=(10, 0), side="bottom")

        # Imagem INTEGRAGAL.jpg (acima do logout)
        try:
            from PIL import Image
            import os
            img_path = os.path.join("images", "INTEGRAGAL.jpg")
            if os.path.exists(img_path):
                img = Image.open(img_path)
                target_width = 160
                aspect_ratio = img.height / img.width
                target_height = int(target_width * aspect_ratio)
                sidebar_img = ctk.CTkImage(light_image=img, dark_image=img, size=(target_width, target_height))
                lbl_img = ctk.CTkLabel(parent_frame, image=sidebar_img, text="")
                lbl_img.pack(pady=(10, 10), side="bottom")
        except Exception as e:
            from utils.logger import registrar_log
            registrar_log("Sidebar", f"Erro ao carregar INTEGRAGAL.jpg: {e}", "WARNING")

        # Espaçador
        frame_spacer = ctk.CTkFrame(parent_frame, fg_color="transparent")
        frame_spacer.pack(fill="both", expand=True)

    def _criar_botoes_menu(self, parent=None):
        """Cria o painel principal (redirecionado para o dashboard na nova interface)."""
        return self._criar_dashboard_page(parent or self.main_window.get_content_frame())

    def _wrap_menu_action(self, label: str, action):
        """Envolve a acao do menu com logs para diagnostico de travamentos pos-bootstrap."""

        def _runner():
            registrar_log("Menu", f"Acao acionada: {label}", "DEBUG")
            try:
                action()
                registrar_log("Menu", f"Acao concluida: {label}", "DEBUG")
            except Exception as exc:  # pragma: no cover - caminho defensivo UI
                registrar_log("Menu", f"Erro em acao '{label}': {exc}", "ERROR")
                if self._is_main_window_alive():
                    try:
                        messagebox.showerror(
                            "Erro",
                            f"Falha ao executar '{label}'.\n\nDetalhes: {exc}",
                            parent=self.main_window,
                        )
                    except Exception as show_exc:
                        registrar_log(
                            "Menu",
                            f"Falha ao exibir messagebox de erro: {show_exc}",
                            "WARNING",
                        )

        return _runner

    def _is_main_window_alive(self) -> bool:
        """Valida se a janela principal ainda possui interpretador Tk ativo."""
        window = getattr(self, "main_window", None)
        if window is None:
            return False
        try:
            if hasattr(window, "winfo_exists"):
                return bool(window.winfo_exists())
        except Exception:
            return False
        return True

    def _navigate_if_registered(self, route_name: str) -> bool:
        """Navega para rota registrada no host; retorna True quando aplicada."""
        nav = getattr(self.main_window, "navigation_manager", None)
        if not nav:
            return False
        factories = getattr(nav, "module_factories", None)
        if isinstance(factories, dict) and route_name not in factories:
            return False
        if hasattr(nav, "navigate_to"):
            nav.navigate_to(route_name)
            return True
        return False

    def _criar_admin_panel_page(self, parent):
        from ui.admin_panel import create_admin_panel_page

        return create_admin_panel_page(
            parent, self.main_window, self.main_window.app_state.usuario_logado
        )

    def _criar_exam_creator_page(self, parent):
        from ui.modules.exam_creator.wizard import create_exam_creator_wizard_page

        return create_exam_creator_wizard_page(parent, self.main_window)

    def _criar_configuracoes_page(self, parent):
        from ui.modules.tela_configuracoes import create_configuracoes_page

        return create_configuracoes_page(parent, self.main_window)

    def _criar_dashboard_page(self, parent):
        from ui.modules.dashboard import create_dashboard_page

        return create_dashboard_page(parent, self.main_window)

    def _criar_graficos_page(self, parent):
        from ui.modules.graficos_qualidade import create_graficos_page

        return create_graficos_page(parent, self.main_window)

    def _criar_historico_page(self, parent):
        from ui.modules.historico_analises import create_historico_page

        return create_historico_page(parent, self.main_window)

    def _criar_analise_completa_page(self, parent):
        from ui.janela_analise_completa import create_analise_completa_page

        return create_analise_completa_page(parent, self.main_window)

    def _criar_gal_page(self, parent):
        from exportacao.envio_gal import create_gal_page

        return create_gal_page(parent, self.main_window)

    def iniciar_nova_analise(self):
        """Limpa o estado da sessão atual para iniciar uma nova análise."""
        resposta = messagebox.askyesno(
            "Nova Análise",
            "Atenção: Os dados atuais de mapeamento e análise serão apagados.\nDeseja iniciar uma nova análise?",
            parent=self.main_window
        )
        if resposta:
            if hasattr(self.main_window, "app_state"):
                self.main_window.app_state.reset_extracao_state()
                # Invalidação visual: expurgar as views cacheadas que dependem do app_state
                if hasattr(self.main_window, "module_host") and self.main_window.module_host:
                    for tab in ["extracao", "analise", "resultados", "dashboard", "analise_completa"]:
                        self.main_window.module_host.remove_module(tab)
            
            # Opcional: Redirecionar o usuário para a Home após o reset
            if hasattr(self.main_window, "navigation_manager") and self.main_window.navigation_manager:
                self.main_window.navigation_manager.navigate_to("main_menu")
                
            self.main_window.update_status("Sessão limpa. Pronto para nova análise.")
            registrar_log("MenuHandler", "Sessão resetada via botão Nova Análise.", "INFO")

    def abrir_busca_extracao(self):
        """Navega para a página de mapeamento da placa."""
        self.main_window.update_status("A carregar painel de extração...")
        
        # Reset completo da sessão antes de ir para o mapeamento
        if hasattr(self.main_window, "app_state"):
            self.main_window.app_state.reset_extracao_state()
            if hasattr(self.main_window, "module_host") and self.main_window.module_host:
                for tab in ["extracao", "analise", "resultados", "dashboard", "analise_completa"]:
                    self.main_window.module_host.remove_module(tab)
                    
        if hasattr(self.main_window, "navigation_manager"):
            self.main_window.navigation_manager.navigate_to("extracao")
        else:
            from tkinter import messagebox
            messagebox.showerror("Erro de Arquitetura", "NavigationManager indisponível", parent=self.main_window)

    def _obter_detalhes_analise_via_dialogo(
        self,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Exibe dialog para seleção de exame e lote.

        Returns
        -------
        Tuple[Optional[str], Optional[str]]
            (exame_selecionado, lote_kit) ou (None, None) se o usuário cancelar
            alguma etapa.
        """
        try:
            from services.suspected_orphan_telemetry import log_suspected_orphan_usage

            log_suspected_orphan_usage(
                "ui.menu_handler._obter_detalhes_analise_via_dialogo",
                user_id=str(getattr(self.main_window.app_state, "usuario_logado", "") or ""),
            )
        except Exception:
            pass

        # Tenta obter a lista de exames disponíÂ­veis a partir do serviço.
        # Primeiro usa, se existir, o atributo de cache; se não existir ou estiver vazio,
        # chama o método público de listagem.
        try:
            analysis_use_case = self._get_analysis_use_case()
            exames_disponiveis = getattr(analysis_use_case, "exames_disponiveis", None)

            if (not exames_disponiveis) and hasattr(analysis_use_case, "listar_exames_disponiveis"):
                exames_disponiveis = analysis_use_case.listar_exames_disponiveis()

            # Normaliza para uma lista de strings, independentemente de como veio.
            if exames_disponiveis is None:
                lista_exames: list[str] = []
            else:
                try:
                    import pandas as _pd  # import local para evitar dependência no topo

                    # Caso seja DataFrame com coluna "exame"
                    if isinstance(exames_disponiveis, _pd.DataFrame) and "exame" in exames_disponiveis.columns:
                        lista_exames = exames_disponiveis["exame"].astype(str).tolist()
                    # Caso seja um dicionário com chave "exame"
                    elif isinstance(exames_disponiveis, dict) and "exame" in exames_disponiveis:
                        lista_exames = [str(x) for x in exames_disponiveis["exame"]]
                    else:
                        # Assume que é um iterável de strings (ou convertíÂ­vel para string)
                        lista_exames = [str(x) for x in exames_disponiveis]
                except Exception:
                    # Fallback extremamente defensivo
                    try:
                        lista_exames = [str(x) for x in exames_disponiveis]
                    except Exception:
                        lista_exames = []
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Erro de Configuração",
                f"Falha ao carregar lista de exames disponíÂ­veis: {exc}",
                parent=self.main_window,
            )
            return None, None

        if not lista_exames:
            messagebox.showwarning(
                "Aviso",
                "Não há exames configurados para análise.",
                parent=self.main_window,
            )
            return None, None

        dialog = CTkSelectionDialog(
            self.main_window,
            title="Seleção de Exame",
            text="Selecione o exame para análise:",
            values=lista_exames,
        )
        exame_selecionado = dialog.get_selection()
        if not exame_selecionado:
            registrar_log("Análise", "Seleção de exame cancelada.", "INFO")
            return None, None

        lote_kit = simpledialog.askstring(
            "Lote do Kit",
            "Digite o lote do kit utilizado:",
            parent=self.main_window,
        )
        if not lote_kit:
            registrar_log("Análise", "Digitação do lote do kit cancelada.", "INFO")
            return None, None

        return exame_selecionado, lote_kit

    def _extrair_dataframe_resultado(self, ret):
        """Extrai DataFrame de retorno heterogeneo (DataFrame, tuple/list, DTO)."""
        if isinstance(ret, (tuple, list)):
            if len(ret) >= 1 and hasattr(ret[0], "empty"):
                return ret[0]
            for item in ret:
                if hasattr(item, "empty"):
                    return item
            return None
        return ret

    def _tem_mapeamento_extracao_valido(self) -> bool:
        """Valida precondicao de mapeamento antes da análise."""
        dados = getattr(self.main_window.app_state, "dados_extracao", None)
        if dados is None:
            return False
        try:
            if hasattr(dados, "empty"):
                return not bool(dados.empty)
            if isinstance(dados, dict):
                return len(dados) > 0
            if isinstance(dados, (list, tuple, set)):
                return len(dados) > 0
            return bool(dados)
        except Exception:
            return False

    def _contar_amostras_uteis(self, resultados_df) -> int:
        """
        Conta amostras uteis (nao-controle) para evitar abrir tela vazia.

        Se coluna `Amostra` nao existir, considera qualquer linha como util.
        """
        if resultados_df is None or not hasattr(resultados_df, "empty") or resultados_df.empty:
            return 0
        if "Amostra" not in resultados_df.columns:
            return int(len(resultados_df))
        control_re = re.compile(r"(?:^|\b)(?:CN|CP)\b|CONTROLE.*(?:NEG|POS)", re.IGNORECASE)
        amostras = resultados_df["Amostra"].fillna("").astype(str).str.strip()
        uteis_mask = (amostras != "") & (~amostras.str.contains(control_re))
        return int(uteis_mask.sum())

    def _resolver_bloco_tamanho_por_contrato(self) -> int:
        """Resolve tamanho de bloco pela decisao contratual do exame selecionado."""
        app_state = getattr(self.main_window, "app_state", None)
        if app_state is None:
            return 1

        current = getattr(app_state, "bloco_tamanho", None)
        if isinstance(current, int) and current > 0:
            return current

        decision: dict[str, Any] = {}
        state_decision = getattr(app_state, "analysis_contract_decision", None)
        if isinstance(state_decision, dict):
            decision = dict(state_decision)
        elif isinstance(getattr(app_state, "analise_metadados", None), dict):
            meta_decision = app_state.analise_metadados.get("analysis_contract_decision")
            if isinstance(meta_decision, dict):
                decision = dict(meta_decision)

        if not decision:
            exam_name = str(getattr(app_state, "exame_selecionado", "") or "").strip()
            equipment_name = (
                str(getattr(app_state, "tipo_de_placa_selecionado", "") or "").strip()
                or str(getattr(app_state, "tipo_de_placa_detectado", "") or "").strip()
            )
            if exam_name:
                try:
                    from services.contract_catalog import get_contract_catalog

                    decision = get_contract_catalog().resolve_analysis_contract_decision(
                        exam_name=exam_name,
                        equipment_name=equipment_name,
                    )
                except Exception as exc:
                    registrar_log(
                        "Analise",
                        f"Falha ao resolver contrato de agrupamento no menu: {exc}",
                        "WARNING",
                    )

        try:
            resolved = max(1, int(decision.get("group_size", 1) or 1))
        except Exception:
            resolved = 1

        app_state.bloco_tamanho = resolved
        if decision:
            app_state.analysis_contract_decision = decision
            try:
                app_state.pocos_por_amostra = max(
                    1, int(decision.get("pocos_por_amostra", resolved) or resolved)
                )
            except Exception:
                app_state.pocos_por_amostra = resolved
            app_state.esquema_agrupamento = str(decision.get("esquema_agrupamento", "")).strip()
        return resolved

    def _aplicar_resultado_analise(self, ret) -> None:
        """Aplica retorno da análise na UI (somente thread principal)."""
        resultados_df = self._extrair_dataframe_resultado(ret)
        if resultados_df is None or not hasattr(resultados_df, "empty") or resultados_df.empty:
            messagebox.showwarning("Aviso", "Nenhum resultado a exibir.", parent=self.main_window)
            return

        amostras_uteis = self._contar_amostras_uteis(resultados_df)
        if amostras_uteis <= 0:
            registrar_log(
                "Analise",
                "Resultado sem amostras uteis para exibicao; abrindo bloqueado para evitar tela vazia.",
                "WARNING",
            )
            messagebox.showwarning(
                "Sem amostras",
                "A análise concluiu sem amostras validas para exibicao.\n\n"
                "Verifique se o mapeamento da placa foi carregado corretamente antes de analisar.",
                parent=self.main_window,
            )
            self.main_window.app_state.resultados_analise = None
            return

        self.main_window.app_state.resultados_analise = resultados_df
        self._resolver_bloco_tamanho_por_contrato()

        exam_cfg = getattr(self.main_window.app_state, "exam_cfg", None)
        if exam_cfg:
            self.main_window.app_state.exam_cfg_for_gal = exam_cfg

        registrar_log(
            "Analise Completa",
            "Analise concluida. CSV GAL sera gerado apos salvamento do historico.",
            "INFO",
        )

        if self._navigate_if_registered("analise_completa"):
            return

        if self._criando_janela_resultado:
            registrar_log(
                "UI Main",
                "Janela de resultados ja esta sendo criada, aguardando...",
                "INFO",
            )
            return

        if self._resultado_window and self._resultado_window.winfo_exists():
            try:
                self._resultado_window.recarregar_dados(resultados_df)
                self._resultado_window.focus()
                self._resultado_window.lift()
                messagebox.showinfo(
                    "Analise Concluida",
                    "Nova análise concluida. Os resultados foram atualizados na janela existente.",
                    parent=self.main_window,
                )
            except Exception as e:
                registrar_log("UI Main", f"Erro ao recarregar dados: {e}", "ERROR")
                try:
                    self._resultado_window.destroy()
                except Exception:
                    pass
                self._resultado_window = None
                self.mostrar_resultados_analise()
        else:
            self.mostrar_resultados_analise()

    def _executar_servico_analise_core(
        self,
        exame: str,
        lote: str,
        arquivo_resultados: Path,
    ):
        """Executa use case de análise sem tocar em widgets/UI."""
        analysis_use_case = self._get_analysis_use_case()
        kwargs = {"arquivo_resultados": arquivo_resultados}
        try:
            return analysis_use_case.executar_analise(
                self.main_window.app_state,
                None,
                exame,
                lote,
                **kwargs,
            )
        except TypeError:
            # Compatibilidade com stubs/implementacoes antigas.
            self.main_window.app_state.caminho_arquivo_corrida = str(arquivo_resultados)
            return analysis_use_case.executar_analise(
                self.main_window.app_state,
                None,
                exame,
                lote,
            )

    def _worker_executar_analise(self, exame: str, lote: str, arquivo_resultados: Path) -> None:
        """Worker thread da análise (sem acesso direto a UI)."""
        registrar_log(
            "AnaliseAsync",
            f"Worker iniciado: exame={exame}, lote={lote}, arquivo={arquivo_resultados}",
            "INFO",
        )
        try:
            ret = self._executar_servico_analise_core(exame, lote, arquivo_resultados)
            registrar_log("AnaliseAsync", "Worker concluido com sucesso.", "INFO")
            self._analise_result_queue.put(("ok", ret))
        except Exception as exc:  # pragma: no cover - caminho defensivo
            registrar_log("AnaliseAsync", f"Worker falhou: {exc}", "ERROR")
            self._analise_result_queue.put(("error", exc))

    def _poll_analise_resultado(self) -> None:
        """Polling thread-safe do resultado da análise."""
        if self._analise_result_queue is None:
            self._analise_em_execucao = False
            self._analise_worker = None
            return

        if self._analise_result_queue.empty():
            self.main_window.after(120, self._poll_analise_resultado)
            return

        status, payload = self._analise_result_queue.get()
        self._analise_em_execucao = False
        self._analise_result_queue = None
        self._analise_worker = None

        if status == "ok":
            registrar_log("AnaliseAsync", "Resultado aplicado na thread principal.", "INFO")
            self._aplicar_resultado_analise(payload)
            return

        exc = payload
        registrar_log("UI Main", f"Erro ao executar servico de analise: {exc}", "CRITICAL")
        messagebox.showerror(
            "Erro",
            f"Falha ao executar a analise: {exc}",
            parent=self.main_window,
        )

    def _iniciar_execucao_analise_assincrona(
        self,
        exame: str,
        lote: str,
        arquivo_resultados: Path,
    ) -> None:
        """Dispara execucao da análise em worker para nao bloquear UI."""
        if self._analise_em_execucao:
            messagebox.showwarning(
                "Analise em execucao",
                "Aguarde a análise atual finalizar antes de iniciar outra.",
                parent=self.main_window,
            )
            return

        self._analise_em_execucao = True
        self._analise_result_queue = Queue()
        registrar_log(
            "AnaliseAsync",
            f"Execucao assincrona disparada: exame={exame}, lote={lote}",
            "INFO",
        )

        # Fallback de teste/CLI sem loop Tk real: executa worker de forma deterministica.
        if not hasattr(self.main_window, "tk"):
            self._worker_executar_analise(exame, lote, arquivo_resultados)
            self._poll_analise_resultado()
            return

        worker = Thread(
            target=self._worker_executar_analise,
            args=(exame, lote, arquivo_resultados),
            daemon=True,
            name="analise-worker",
        )
        self._analise_worker = worker
        worker.start()
        self.main_window.after(120, self._poll_analise_resultado)

    def _executar_servico_analise(
        self,
        exame: str,
        lote: str,
        arquivo_resultados: Optional[Path] = None,
    ):
        """Caminho sincrono (compatibilidade de testes e rotas legadas)."""
        try:
            caminho = arquivo_resultados or Path(
                str(getattr(self.main_window.app_state, "caminho_arquivo_corrida", "")).strip()
            )
            if not str(caminho):
                raise RuntimeError("Arquivo de resultados obrigatorio para iniciar a análise.")
            ret = self._executar_servico_analise_core(exame, lote, Path(caminho))
            self._aplicar_resultado_analise(ret)
        except Exception as e:
            registrar_log("UI Main", f"Erro ao executar servico de analise: {e}", "CRITICAL")
            messagebox.showerror("Erro", f"Falha ao executar a analise: {e}", parent=self.main_window)

    def realizar_analise(self):
        """Redireciona para a tela de preparação da análise."""
        if hasattr(self.main_window, "navigation_manager"):
            self.main_window.navigation_manager.navigate_to("analise_setup")

    def _solicitar_arquivo_resultados(self) -> Optional[Path]:
        """Solicita arquivo de resultados na camada de UI (fronteira correta)."""
        caminho = filedialog.askopenfilename(
            parent=self.main_window,
            title="Selecione o arquivo de resultados do equipamento",
            filetypes=[
                ("Arquivos de planilha", "*.csv;*.xlsx;*.xls"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not caminho:
            return None
        return Path(caminho)

    def _solicitar_dados_corrida(self) -> Optional[Tuple[str, str]]:
        """Solicita lote/kit e data de realizacao em um unico dialogo modal."""
        if not self._is_main_window_alive():
            registrar_log(
                "Analise",
                "Janela principal indisponivel antes do prompt de dados da corrida.",
                "ERROR",
            )
            return None

        try:
            app_state = getattr(self.main_window, "app_state", None)
            dialog = _LoteDataDialog(
                self.main_window,
                nome_corrida=str(getattr(app_state, "nome_corrida", "") or ""),
                quem_fez_extracao=str(getattr(app_state, "quem_fez_extracao", "") or ""),
                quem_preparou_placa=str(getattr(app_state, "quem_preparou_placa", "") or ""),
                quem_analisou_placa=str(getattr(app_state, "quem_analisou_placa", "") or ""),
                observacoes=str(getattr(app_state, "observacoes_corrida", "") or ""),
            )
            resultado = dialog.show()
            if resultado:
                if isinstance(resultado, tuple):
                    lote = str(resultado[0]).strip()
                    data_exame = str(resultado[1]).strip()
                    opcionais = {
                        "nome_corrida": "",
                        "quem_fez_extracao": "",
                        "quem_preparou_placa": "",
                        "quem_analisou_placa": "",
                        "observacoes": "",
                    }
                else:
                    lote = str(resultado.get("lote") or "").strip()
                    data_exame = str(resultado.get("data_exame") or "").strip()
                    opcionais = {
                        "nome_corrida": str(resultado.get("nome_corrida") or "").strip(),
                        "quem_fez_extracao": str(resultado.get("quem_fez_extracao") or "").strip(),
                        "quem_preparou_placa": str(
                            resultado.get("quem_preparou_placa") or ""
                        ).strip(),
                        "quem_analisou_placa": str(
                            resultado.get("quem_analisou_placa") or ""
                        ).strip(),
                        "observacoes": str(resultado.get("observacoes") or "").strip(),
                    }

                if not lote or not data_exame:
                    registrar_log(
                        "Analise",
                        "Dialogo retornou dados obrigatorios vazios; operacao cancelada.",
                        "WARNING",
                    )
                    return None

                if app_state is not None:
                    app_state.nome_corrida = opcionais["nome_corrida"]
                    app_state.quem_fez_extracao = opcionais["quem_fez_extracao"]
                    app_state.quem_preparou_placa = opcionais["quem_preparou_placa"]
                    app_state.quem_analisou_placa = opcionais["quem_analisou_placa"]
                    app_state.observacoes_corrida = opcionais["observacoes"]
                registrar_log(
                    "Analise",
                    (
                        "Dados da corrida informados: "
                        f"lote={lote}, data={data_exame}, "
                        f"nome_corrida={'sim' if bool(opcionais['nome_corrida']) else 'nao'}, "
                        f"quem_fez_extracao={'sim' if bool(opcionais['quem_fez_extracao']) else 'nao'}, "
                        f"quem_preparou_placa={'sim' if bool(opcionais['quem_preparou_placa']) else 'nao'}, "
                        f"observacoes={'sim' if bool(opcionais['observacoes']) else 'nao'}"
                    ),
                    "DEBUG",
                )
                return lote, data_exame
        except Exception as exc:
            registrar_log("Analise", f"Falha no dialogo de dados da corrida: {exc}", "WARNING")

        if self._is_main_window_alive():
            try:
                messagebox.showwarning(
                    "Dados obrigatorios",
                    "E necessario informar lote/kit e data da realizacao para iniciar a análise.",
                    parent=self.main_window,
                )
            except Exception as exc:
                registrar_log("Analise", f"Nao foi possivel exibir aviso de dados obrigatorios: {exc}", "WARNING")
        return None

    def mostrar_resultados_analise(self):
        """Exibe os resultados da análise em tabela"""
        # Verificar se já está criando janela (proteção contra race condition)
        if self._criando_janela_resultado:
            registrar_log("UI Main", "Janela de resultados já está sendo criada, ignorando chamada duplicada.", "INFO")
            return

        df = self.main_window.app_state.resultados_analise
        if df is None or df.empty:
            messagebox.showwarning(
                "Aviso", "Sem resultados para exibir.", parent=self.main_window
            )
            return

        if self._navigate_if_registered("analise_completa"):
            return

        # Verificar se janela de resultados já existe (modo legado)
        if self._resultado_window and self._resultado_window.winfo_exists():
            self._resultado_window.focus()
            self._resultado_window.lift()
            return

        agravos = ["SC2", "HMPV", "INF A", "INF B", "ADV", "RSV", "HRV"]
        status_corrida = "N/A"
        num_placa = "N/A"
        from datetime import datetime

        data_placa_formatada = getattr(
            self.main_window.app_state,
            "data_exame",
            datetime.now().strftime("%d/%m/%Y"),
        )

        # NOVO: Usar janela única com abas no ModuleHost
        # Setar flag ANTES de criar janela (proteção contra race condition)
        self._criando_janela_resultado = True
        
        try:
            bloco_tamanho = self._resolver_bloco_tamanho_por_contrato()
            
            def factory(parent):
                from ui.janela_analise_completa import JanelaAnaliseCompleta
                return JanelaAnaliseCompleta(
                    self.main_window,
                    df,
                    status_corrida,
                    num_placa,
                    data_placa_formatada,
                    agravos,
                    usuario_logado=getattr(
                        self.main_window.app_state, "usuario_logado", "Desconhecido"
                    ),
                    exame=getattr(self.main_window.app_state, "exame_selecionado", ""),
                    lote=getattr(self.main_window.app_state, "lote", ""),
                    arquivo_corrida=getattr(self.main_window.app_state, "caminho_arquivo_corrida", ""),
                    bloco_tamanho=bloco_tamanho,
                    numero_extracao=getattr(self.main_window.app_state, "numero_extracao", ""),  # FASE 4
                    host_frame=parent
                )
            
            nav = getattr(self.main_window, "navigation_manager", None)
            if nav and hasattr(nav, "register_module") and hasattr(nav, "navigate_to"):
                nav.register_module("analise_completa_dinamica", factory)
                nav.navigate_to("analise_completa_dinamica")
            else:
                self._resultado_window = factory(None)
                
        except Exception as e:
            registrar_log("UI Main", f"Erro ao exibir resultados: {e}", "ERROR")
            messagebox.showerror(
                "Erro", f"Falha ao exibir resultados: {e}", parent=self.main_window

            )
        finally:
            # Limpar flag após janela ser criada (sucesso ou falha)
            self._criando_janela_resultado = False

    def enviar_para_gal(self):
        """Abre o módulo de envio para o GAL"""
        if self._navigate_if_registered("gal"):
            return

        # Verificar se já está criando janela (proteção contra race condition)
        if self._criando_janela_gal:
            registrar_log("UI Main", "Janela GAL já está sendo criada, ignorando chamada duplicada.", "INFO")
            return
        
        # Verificar se janela GAL já existe
        if self._gal_window and self._gal_window.winfo_exists():
            self._gal_window.focus()
            self._gal_window.lift()
            return
        
        self.main_window.update_status("Abrindo módulo de envio para o GAL...")
        
        # Setar flag ANTES de criar janela
        self._criando_janela_gal = True
        
        try:
            self._gal_window = abrir_janela_envio_gal(
                self.main_window, self.main_window.app_state.usuario_logado, 
                app_state=self.main_window.app_state
            )
        except Exception as e:
            # Garantir que flag seja limpa em caso de erro
            self.main_window.update_status("Erro ao abrir o módulo de envio.")
            registrar_log(
                "UI Main", f"Falha ao abrir a janela de envio ao GAL: {e}", "CRITICAL"
            )
            messagebox.showerror(
                "Erro CríÂ­tico",
                f"Não foi possíÂ­vel iniciar o módulo de envio ao GAL.\n\nDetalhes: {e}",
                parent=self.main_window,
            )
        finally:
            # Limpar flag após janela ser criada (sucesso ou falha)
            self._criando_janela_gal = False

    def abrir_administracao(self):
        """Abre o painel administrativo"""
        # Verificar permissão: apenas ADMIN e MASTER
        if not self._verificar_permissao(["ADMIN", "MASTER"]):
            messagebox.showerror(
                "Acesso Negado",
                "Você não tem permissão para acessar o módulo de Administração.\n\n"
                "Apenas usuários ADMIN e MASTER podem acessar este módulo.",
                parent=self.main_window
            )
            registrar_log(
                "MenuHandler",
                f"Acesso negado Ã  Administração para usuário {self.main_window.app_state.usuario_logado} "
                f"(níÂ­vel: {self.main_window.app_state.nivel_acesso})",
                "WARNING"
            )
            return

        if self._navigate_if_registered("administracao"):
            return
        
        from ui.admin_panel import AdminPanel

        AdminPanel(self.main_window, self.main_window.app_state.usuario_logado)

    def gerenciar_usuarios(self):
        """Abre o painel de gerenciamento de usuários"""
        # Verificar permissão: apenas ADMIN e MASTER
        if not self._verificar_permissao(["ADMIN", "MASTER"]):
            messagebox.showerror(
                "Acesso Negado",
                "Você não tem permissão para gerenciar usuários.\n\n"
                "Apenas usuários ADMIN e MASTER podem acessar este módulo.",
                parent=self.main_window
            )
            registrar_log(
                "MenuHandler",
                f"Acesso negado ao Gerenciamento de Usuários para {self.main_window.app_state.usuario_logado} "
                f"(níÂ­vel: {self.main_window.app_state.nivel_acesso})",
                "WARNING"
            )
            return
        
        if self._navigate_if_registered("usuarios"):
            return
        
        from ui.user_management import UserManagementPanel
        UserManagementPanel(self.main_window, self.main_window.app_state.usuario_logado)

    def incluir_novo_exame(self):
        """Abre o módulo de inclusão/edição de exames (registry)."""
        # Verificar permissão: apenas ADMIN e MASTER
        if not self._verificar_permissao(["ADMIN", "MASTER"]):
            messagebox.showerror(
                "Acesso Negado",
                "Você não tem permissão para cadastrar exames.\n\n"
                "Apenas usuários ADMIN e MASTER podem acessar este módulo.",
                parent=self.main_window
            )
            registrar_log(
                "MenuHandler",
                f"Acesso negado ao Cadastro de Exames para {self.main_window.app_state.usuario_logado} "
                f"(nível: {self.main_window.app_state.nivel_acesso})",
                "WARNING"
            )
            return

        if self._navigate_if_registered("novo_exame"):
            return

        # Preferir tela maximizada para o fluxo de criação/edição de exames.
        try:
            if hasattr(self.main_window, "state"):
                self.main_window.state("zoomed")
        except Exception as exc:
            registrar_log(
                "MenuHandler",
                f"Não foi possível maximizar janela principal antes do módulo de exames: {exc}",
                "DEBUG",
            )

        if self._navigate_if_registered("novo_exame"):
            return
        
        from ui.modules.exam_creator.wizard import ExamCreatorWizard

        ExamCreatorWizard(self.main_window)

    def abrir_configuracoes(self):
        """Abre o módulo de configurações."""
        if self._navigate_if_registered("tela_configuracoes"):
            return
        from ui.modules.tela_configuracoes import abrir_configuracoes

        abrir_configuracoes(self.main_window)

    def gerar_relatorios(self):
        """Abre o modulo de relatorios operacionais."""
        if self._navigate_if_registered("relatorios"):
            return
            
        try:
            from ui.modules.reports import abrir_modulo_relatorios

            app_state = getattr(self.main_window, "app_state", None)
            abrir_modulo_relatorios(self.main_window, app_state=app_state)
        except Exception as e:
            registrar_log("Relatorios", f"Erro ao abrir modulo de relatorios: {e}", "ERROR")
            messagebox.showerror(
                "Erro",
                f"Falha ao abrir o modulo de relatorios:\n{e}",
                parent=self.main_window,
            )
    
    def abrir_dashboard(self):
        """Abre o Dashboard de Analises"""
        # Verificar permissao: apenas ADMIN e MASTER
        if not self._verificar_permissao(["ADMIN", "MASTER"]):
            messagebox.showerror(
                "Acesso Negado",
                "Voce nao tem permissao para acessar os Dashboards.\n\n"
                "Apenas usuarios ADMIN e MASTER podem acessar este modulo.",
                parent=self.main_window,
            )
            registrar_log(
                "MenuHandler",
                f"Acesso negado aos Dashboards para {self.main_window.app_state.usuario_logado} "
                f"(nivel: {self.main_window.app_state.nivel_acesso})",
                "WARNING",
            )
            return

        if self._navigate_if_registered("dashboard"):
            return

        if getattr(self, "_criando_janela_dashboard", False):
            registrar_log("UI Main", "Janela de dashboard ja esta sendo criada, ignorando chamada duplicada.", "INFO")
            return

        if self._dashboard_window and self._dashboard_window.winfo_exists():
            self._dashboard_window.focus()
            self._dashboard_window.lift()
            return

        try:
            from ui.modules.dashboard import Dashboard

            registrar_log("UI Main", "Abrindo Dashboard...", "INFO")

            self._criando_janela_dashboard = True
            self._dashboard_window = Dashboard(self.main_window)
        except Exception as e:
            registrar_log("UI Main", f"Erro ao abrir Dashboard: {e}", "ERROR")
            messagebox.showerror(
                "Erro",
                f"Falha ao abrir Dashboard:\n{str(e)}",
                parent=self.main_window,
            )
        finally:
            self._criando_janela_dashboard = False

    def _detectar_e_confirmar_equipamento(self) -> Optional[str]:
        """
        Detecta equipamento automaticamente e pede confirmação do usuário.

        Returns:
            Nome do equipamento escolhido ou None se cancelado
        """
        from application.equipment_profile_service import EquipmentProfileService
        from ui.equipment_confirmation_dialog import EquipmentConfirmationDialog

        service = EquipmentProfileService()
        active_profiles = service.list_active_profiles()
        active_names = [
            str(profile.get("display_name") or profile.get("equipment_id") or "").strip()
            for profile in active_profiles
            if str(profile.get("display_name") or profile.get("equipment_id") or "").strip()
        ]

        arquivo_xlsx = getattr(self.main_window.app_state, "caminho_arquivo_extracao", None)
        if not arquivo_xlsx or not Path(str(arquivo_xlsx)).exists():
            registrar_log(
                "UI Main",
                "Arquivo de extração ausente para detecção automática; usando seleção manual.",
                "INFO",
            )
            return self._escolher_equipamento_manual()

        try:
            self.main_window.update_status("Detectando equipamento...")
            resultado = service.detect_equipment(Path(str(arquivo_xlsx)))
            dialog = EquipmentConfirmationDialog(
                self.main_window,
                resultado,
                active_names,
            )
            escolha = dialog.obter_escolha()
            if escolha:
                self.main_window.update_status(f"Equipamento selecionado: {escolha}")
                registrar_log("UI Main", f"Equipamento confirmado: {escolha}", "INFO")
            return escolha
        except Exception as exc:
            registrar_log("UI Main", f"Erro na detecção automática: {exc}", "WARNING")
            return self._escolher_equipamento_manual()
    def _normalizar_lista_exames(self, exames_disponiveis) -> list[str]:
        """Normaliza payload de exames para lista de strings sem vazios."""
        if exames_disponiveis is None:
            return []
        try:
            import pandas as _pd  # import local para evitar dependencia no topo

            if isinstance(exames_disponiveis, _pd.DataFrame):
                if "exame" in exames_disponiveis.columns:
                    values = exames_disponiveis["exame"].astype(str).tolist()
                else:
                    return []
            elif isinstance(exames_disponiveis, dict) and "exame" in exames_disponiveis:
                values = [str(x) for x in exames_disponiveis["exame"]]
            else:
                values = [str(x) for x in exames_disponiveis]
        except Exception:
            try:
                values = [str(x) for x in exames_disponiveis]
            except Exception:
                return []

        lista: list[str] = []
        for value in values:
            normalized = str(value).strip()
            if normalized and normalized not in lista:
                lista.append(normalized)
        return lista

    def _carregar_exames_para_ui(self) -> list[str]:
        """
        Carrega exames via use case/service (sem leitura direta de arquivo na UI).

        Prioridade:
        1) AnalysisService.listar_exames_disponiveis()
        2) cache do proprio service (analysis.exames_disponiveis)
        3) cache em app_state (exames_disponiveis_cache)
        """
        analysis_use_case = self._get_exam_catalog_port()
        erro_principal: Optional[Exception] = None

        try:
            exames = analysis_use_case.listar_exames_disponiveis()
            lista = self._normalizar_lista_exames(exames)
            if lista:
                setattr(self.main_window.app_state, "exames_disponiveis_cache", list(lista))
                return lista
        except Exception as exc:  # noqa: BLE001
            erro_principal = exc
            registrar_log("UI Main", f"Falha ao listar exames no service: {exc}", "WARNING")

        cache_candidates = [
            getattr(analysis_use_case, "exames_disponiveis", None),
            getattr(self.main_window.app_state, "exames_disponiveis_cache", None),
        ]
        for candidate in cache_candidates:
            lista_cache = self._normalizar_lista_exames(candidate)
            if lista_cache:
                registrar_log(
                    "UI Main",
                    f"Fallback de exames via cache aplicado ({len(lista_cache)} itens).",
                    "INFO",
                )
                setattr(self.main_window.app_state, "exames_disponiveis_cache", list(lista_cache))
                return lista_cache

        if erro_principal is not None:
            raise RuntimeError(str(erro_principal)) from erro_principal
        return []

    def _escolher_exame(self) -> Optional[str]:
        """
        Permite ao usuario escolher o exame para análise.

        Returns:
            Nome do exame ou None se cancelado.
        """
        try:
            lista_exames = self._carregar_exames_para_ui()

            if not lista_exames:
                messagebox.showerror(
                    "Erro",
                    "Nenhum exame cadastrado no sistema.",
                    parent=self.main_window,
                )
                return None

            escolha = CTkSelectionDialog(
                self.main_window,
                title="Selecao de Exame",
                text="Selecione o exame para analise:",
                values=lista_exames,
            ).get_selection()

            return escolha

        except Exception as e:
            registrar_log("UI Main", f"Erro ao escolher exame: {e}", "ERROR")
            messagebox.showerror(
                "Erro",
                f"Falha ao carregar lista de exames:\\n{str(e)}",
                parent=self.main_window,
            )
            return None

    def _escolher_equipamento_manual(self) -> Optional[str]:
        """
        [OBSOLETO - Mantido para compatibilidade com código comentado]
        Permite ao usuário escolher equipamento manualmente via dialog.
        
        Returns:
            Nome do equipamento ou None se cancelado
        """
        try:
            from application.equipment_profile_service import EquipmentProfileService

            service = EquipmentProfileService()
            equipamentos = [
                str(profile.get("display_name") or profile.get("equipment_id") or "").strip()
                for profile in service.list_active_profiles()
                if str(profile.get("display_name") or profile.get("equipment_id") or "").strip()
            ]

            if not equipamentos:
                messagebox.showerror(
                    "Erro",
                    "Nenhum equipamento cadastrado no sistema.",
                    parent=self.main_window
                )
                return None
            
            # Usar CTkSelectionDialog para escolha
            escolha = CTkSelectionDialog(
                self.main_window,
                title="Seleção Manual",
                text="Selecione o equipamento:",
                values=equipamentos
            ).get_selection()
            
            return escolha
            
        except Exception as e:
            registrar_log("UI Main", f"Erro ao escolher equipamento manual: {e}", "ERROR")
            messagebox.showerror(
                "Erro",
                f"Falha ao carregar lista de equipamentos:\n{str(e)}",
                parent=self.main_window
            )
            return None


