"""
Ponto de entrada principal da aplicação IntegraGAL v2.0 - versão refatorada.
Mantém utilitários globais (_formatar_para_gal) para compatibilidade.
"""

import os
import sys
import threading
import traceback
from datetime import datetime

from services.contract_preflight import run_contract_preflight
from services.system_paths import BASE_DIR
from services.core.runtime_flags import is_legacy_panel_csv_enabled
from services.legacy_panel_governance import record_legacy_panel_event
from ui.main_window import criar_aplicacao_principal_por_modo
from utils.logger import registrar_log

# Aplicar filtro para suprimir erros cosméticos do CustomTkinter
# Esses erros não afetam a funcionalidade mas poluem o console
from utils.suppress_ctk_errors import aplicar_filtro_global
aplicar_filtro_global()

import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')


def _install_global_exception_observability() -> None:
    """Registra excecoes nao tratadas em logs operacionais."""

    def _log_exception(exc_type, exc_value, exc_tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            return
        try:
            registrar_log(
                "UnhandledException",
                f"{exc_type.__name__}: {exc_value}",
                "CRITICAL",
                error_code="UNHANDLED_EXCEPTION",
            )
            registrar_log(
                "UnhandledException",
                "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
                "DEBUG",
            )
        except Exception:
            pass

    def _threading_hook(args) -> None:
        try:
            _log_exception(args.exc_type, args.exc_value, args.exc_traceback)
        except Exception:
            pass

    sys.excepthook = _log_exception
    if hasattr(threading, "excepthook"):
        threading.excepthook = _threading_hook


def _schedule_main_window_watchdog(app, attempts: int = 4, delay_ms: int = 250) -> None:
    """Monitora visibilidade da janela principal e aplica recovery quando necessario."""

    def _probe(step: int) -> None:
        try:
            state = str(app.state())
            viewable = int(bool(app.winfo_viewable()))
            mapped = int(bool(app.winfo_ismapped()))
            geometry = app.geometry()
            registrar_log(
                "Sistema",
                (
                    f"UI watchdog {step}/{attempts}: "
                    f"state={state}, viewable={viewable}, mapped={mapped}, geometry={geometry}"
                ),
                "DEBUG",
            )
        except Exception as exc:
            registrar_log("Sistema", f"UI watchdog falhou ao inspecionar janela: {exc}", "WARNING")
            return

        needs_recovery = state in {"withdrawn", "iconic"} or not viewable or not mapped
        if needs_recovery:
            try:
                app.deiconify()
                app.state("normal")
                app.update_idletasks()
                app.lift()
                app.focus_force()
                app.attributes("-topmost", True)
                app.after(120, lambda: app.attributes("-topmost", False))
                registrar_log(
                    "Sistema",
                    "UI watchdog aplicou recovery de visibilidade na janela principal.",
                    "WARNING",
                )
            except Exception as exc:
                registrar_log("Sistema", f"UI watchdog falhou no recovery: {exc}", "WARNING")

        if step < attempts:
            try:
                app.after(delay_ms, lambda: _probe(step + 1))
            except Exception:
                pass

    try:
        app.after(delay_ms, lambda: _probe(1))
    except Exception:
        pass


def _run_app_loop(app) -> None:
    """Executa mainloop com diagnostico de bootstrap/loop de UI."""
    if app is None:
        return
    try:
        app.after(
            120,
            lambda: registrar_log(
                "Sistema",
                "UI heartbeat inicial: loop principal ativo.",
                "DEBUG",
            ),
        )
    except Exception:
        pass
    _schedule_main_window_watchdog(app)
    registrar_log("Sistema", "Entrando no mainloop da aplicacao.", "DEBUG")
    app.mainloop()
    registrar_log("Sistema", "Mainloop encerrado.", "DEBUG")


def _execute_startup_contract_preflight() -> None:
    """Executa preflight contratual de startup por ambiente."""
    result = run_contract_preflight()
    if result.issue_count > 0 and result.mode == "audit":
        registrar_log(
            "Sistema",
            (
                "Preflight de contratos em modo audit: "
                f"{result.issue_count} inconformidade(s) detectada(s)."
            ),
            "WARNING",
        )

def gerar_painel_csvs(*args, **kwargs):
    """
    Wrapper de compatibilidade para gerar paineis de CSV via gal_formatter.
    """
    user_id = (
        kwargs.get("user_id")
        or kwargs.get("usuario_logado")
        or kwargs.get("usuario")
    )
    if not is_legacy_panel_csv_enabled():
        record_legacy_panel_event(
            "legacy_panel_blocked",
            user_id=str(user_id) if user_id else None,
            note="flag_off",
            details={"source": "main.gerar_painel_csvs"},
        )
        raise RuntimeError(
            "gerar_painel_csvs desabilitado por rollout. "
            "Use o writer oficial GAL (gal_<timestamp>_exame.csv)."
        )

    from exportacao.gal_formatter import gerar_painel_csvs as _gerar_painel_csvs
    record_legacy_panel_event(
        "legacy_panel_enabled",
        user_id=str(user_id) if user_id else None,
        note="flag_on",
        details={"source": "main.gerar_painel_csvs"},
    )
    return _gerar_painel_csvs(*args, **kwargs)















def main_cli():
    """
    Interface de linha de comando (CLI) para executar módulos específicos.
    
    Uso:
        python main.py              # Abre GUI principal (padrão)
        python main.py dashboard    # Abre Dashboard
        python main.py historico    # Abre Histórico
        python main.py alertas      # Abre Sistema de Alertas
        python main.py graficos     # Abre Gráficos
        python main.py visualizador # Abre Visualizador de Placas
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="IntegRAGal - Sistema Integrado de Análises Laboratoriais",
        epilog="Se nenhum comando for especificado, abre a interface gráfica principal."
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponíveis')
    
    # Subcomandos
    subparsers.add_parser('dashboard', help='Abrir Dashboard de Análises')
    subparsers.add_parser('historico', help='Abrir Visualizador de Histórico')
    subparsers.add_parser('alertas', help='Abrir Sistema de Alertas')
    subparsers.add_parser('graficos', help='Abrir Gráficos e Estatísticas')
    subparsers.add_parser('visualizador', help='Abrir Visualizador de Placas')
    
    args = parser.parse_args()
    
    if args.command == 'dashboard':
        registrar_log("Main", "Iniciando Dashboard via CLI", "INFO")
        from ui.modules.dashboard import Dashboard
        app = Dashboard()
        app.mainloop()
        
    elif args.command == 'historico':
        registrar_log("Main", "Iniciando Histórico via CLI", "INFO")
        from ui.modules.historico_analises import HistoricoAnalises
        # HistoricoAnalises requer um master window
        import customtkinter as ctk
        root = ctk.CTk()
        root.withdraw()  # Esconder janela principal
        app = HistoricoAnalises(root)
        app.mainloop()
        
    elif args.command == 'alertas':
        registrar_log("Main", "Iniciando Sistema de Alertas via CLI", "INFO")
        from ui.modules.sistema_alertas import CentroNotificacoes
        app = CentroNotificacoes()
        app.mainloop()
        
    elif args.command == 'graficos':
        registrar_log("Main", "Iniciando Gráficos via CLI", "INFO")
        from ui.modules.graficos_qualidade import GraficosQualidade
        # GraficosQualidade requer um master window
        import customtkinter as ctk
        root = ctk.CTk()
        root.withdraw()  # Esconder janela principal
        app = GraficosQualidade(root)
        app.mainloop()
        
    elif args.command == 'visualizador':
        registrar_log("Main", "Iniciando Visualizador via CLI", "INFO")
        # Executar visualizador com dados de exemplo (modo demo/teste)
        import customtkinter as ctk
        from ui.modules.visualizador_exame import VisualizadorExame, criar_dados_exame_exemplo
        
        root = ctk.CTk()
        root.withdraw()
        
        dados = criar_dados_exame_exemplo()
        app = VisualizadorExame(root, dados)
        root.mainloop()
        
    else:
        # Modo GUI padrão
        app = criar_aplicacao_principal_por_modo()
        _run_app_loop(app)




if __name__ == "__main__":
    """Ponto de entrada principal da aplicação"""
    
    os.chdir(BASE_DIR)
    _install_global_exception_observability()
    try:
        _execute_startup_contract_preflight()
    except Exception as exc:
        registrar_log(
            "Sistema",
            f"Bootstrap bloqueado no preflight contratual: {exc}",
            "CRITICAL",
        )
        print(f"[Sistema] ERRO no preflight de contratos: {exc}")
        sys.exit(2)
    
    # Se houver argumentos de linha de comando, usar CLI
    # Caso contrário, abrir GUI principal
    if len(sys.argv) > 1:
        main_cli()
    else:
        app = criar_aplicacao_principal_por_modo()
        _run_app_loop(app)
