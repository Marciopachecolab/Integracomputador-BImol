"""
Teste guardiao: iniciar_nova_analise() deve navegar para "main_menu", nao "dashboard".
Ref: AGENTS.md §12.
"""
from unittest.mock import MagicMock, patch


def test_nova_analise_navega_para_main_menu_nao_dashboard():
    """
    GREEN: iniciar_nova_analise() deve chamar navigate_to("main_menu").
    Confirma que a correcao na linha 551 de ui/menu_handler.py esta vigente.
    """
    mock_nav = MagicMock()
    mock_nav.navigate_to = MagicMock()

    mock_app_state = MagicMock()
    mock_app_state.nivel_acesso = "ADMIN"

    mock_window = MagicMock()
    mock_window.app_state = mock_app_state
    mock_window.navigation_manager = mock_nav
    mock_window.module_host = None  # pula bloco de invalidacao de cache

    from ui.menu_handler import MenuHandler

    handler = MenuHandler.__new__(MenuHandler)
    handler.main_window = mock_window
    handler.services = None
    handler._dashboard_window = None
    handler._criando_janela_dashboard = False
    handler._resultado_window = None
    handler._criando_janela_resultado = False
    handler._analise_em_execucao = False
    handler._analise_result_queue = None
    handler._analise_worker = None
    handler._menu_frame = None

    with patch("ui.menu_handler.messagebox") as mock_msgbox, \
         patch("ui.menu_handler.registrar_log"):
        mock_msgbox.askyesno.return_value = True
        handler.iniciar_nova_analise()

    calls = [str(c) for c in mock_nav.navigate_to.call_args_list]

    assert any("main_menu" in c for c in calls), (
        f"navigate_to('main_menu') nao foi chamado. Chamadas reais: {calls}"
    )
    assert not any("dashboard" in c for c in calls), (
        f"navigate_to('dashboard') foi chamado indevidamente. Chamadas reais: {calls}"
    )
