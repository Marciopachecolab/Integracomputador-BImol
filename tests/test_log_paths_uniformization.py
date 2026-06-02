"""
Teste-guardiao: todos os componentes de log devem resolver para o mesmo root logs/.

Ref: LOG-UNIF-001 / plano de uniformizacao de paths de log (2026-05-29).

Verifica:
- config/default_config.json nao aponta logs_dir para dados/banco (bug)
- AuditLogger() sem argumento resolve para logs/audit
- DataFrameReporter() sem argumento resolve para logs/dataframe_reports
- _resolve_log_path() de legacy_panel_governance resolve para logs/
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).parent.parent
DEFAULT_CONFIG_PATH = ROOT / "config" / "default_config.json"

EXPECTED_LOGS_ROOT = "logs"


# ---------------------------------------------------------------------------
# 1. Teste de configuracao central
# ---------------------------------------------------------------------------

def test_default_config_logs_dir_nao_aponta_para_dados_banco():
    """logs_dir nao deve apontar para dados/banco (era um bug de configuracao)."""
    with open(DEFAULT_CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)

    logs_dir = cfg.get("paths", {}).get("logs_dir", "")
    assert "dados/banco" not in logs_dir, (
        f"logs_dir ainda aponta para dados/banco: '{logs_dir}'. "
        "Corrigir em config/default_config.json."
    )


def test_default_config_logs_dir_aponta_para_logs():
    """logs_dir deve apontar para 'logs' (root unificado)."""
    with open(DEFAULT_CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)

    logs_dir = cfg.get("paths", {}).get("logs_dir", "")
    assert EXPECTED_LOGS_ROOT in logs_dir, (
        f"logs_dir esperado conter '{EXPECTED_LOGS_ROOT}', obtido: '{logs_dir}'."
    )


# ---------------------------------------------------------------------------
# 2. AuditLogger - deve usar config service e resolver para logs/audit
# ---------------------------------------------------------------------------

def test_audit_logger_resolve_para_logs_audit_via_config(tmp_path):
    """AuditLogger() sem argumento deve resolver log_dir para logs/audit quando config retorna logs_dir='logs'."""
    fake_paths = {"logs_dir": str(tmp_path / "logs")}
    mock_cfg = MagicMock()
    mock_cfg.get_paths.return_value = fake_paths

    with patch("services.core.config_service.config_service", mock_cfg):
        from utils import audit_logger as al
        import importlib
        importlib.reload(al)

        logger_instance = al.AuditLogger()

    expected = tmp_path / "logs" / "audit"
    assert Path(logger_instance.log_dir).resolve() == expected.resolve(), (
        f"AuditLogger.log_dir esperado '{expected}', obtido '{logger_instance.log_dir}'."
    )


def test_audit_logger_fallback_para_logs_audit_sem_config():
    """AuditLogger() sem logs_dir no config deve usar fallback logs/audit."""
    mock_cfg = MagicMock()
    mock_cfg.get_paths.return_value = {}
    with patch("services.core.config_service.config_service", mock_cfg):
        from utils import audit_logger as al
        import importlib
        importlib.reload(al)

        with patch.object(Path, "mkdir"):
            logger_instance = al.AuditLogger()

    assert "logs" in str(logger_instance.log_dir), (
        f"Fallback de AuditLogger.log_dir nao contem 'logs': '{logger_instance.log_dir}'."
    )
    assert "audit" in str(logger_instance.log_dir), (
        f"Fallback de AuditLogger.log_dir nao contem 'audit': '{logger_instance.log_dir}'."
    )


# ---------------------------------------------------------------------------
# 3. DataFrameReporter - deve usar config service e resolver para logs/dataframe_reports
# ---------------------------------------------------------------------------

def test_dataframe_reporter_resolve_para_logs_via_config(tmp_path):
    """DataFrameReporter() sem argumento deve resolver log_dir via config service."""
    fake_paths = {"logs_dir": str(tmp_path / "logs")}
    mock_cfg = MagicMock()
    mock_cfg.get_paths.return_value = fake_paths

    with patch("services.core.config_service.config_service", mock_cfg):
        from utils import dataframe_reporter as dr
        import importlib
        importlib.reload(dr)

        reporter = dr.DataFrameReporter()

    expected = tmp_path / "logs" / "dataframe_reports"
    assert Path(reporter.log_dir).resolve() == expected.resolve(), (
        f"DataFrameReporter.log_dir esperado '{expected}', obtido '{reporter.log_dir}'."
    )


def test_dataframe_reporter_fallback_contem_logs():
    """DataFrameReporter() sem logs_dir no config deve usar fallback que contem 'logs'."""
    mock_cfg = MagicMock()
    mock_cfg.get_paths.return_value = {}
    with patch("services.core.config_service.config_service", mock_cfg):
        from utils import dataframe_reporter as dr
        import importlib
        importlib.reload(dr)

        with patch.object(Path, "mkdir"):
            reporter = dr.DataFrameReporter()

    assert "logs" in str(reporter.log_dir), (
        f"Fallback de DataFrameReporter.log_dir nao contem 'logs': '{reporter.log_dir}'."
    )


# ---------------------------------------------------------------------------
# 4. legacy_panel_governance - _resolve_default_log_path deve usar config service
# ---------------------------------------------------------------------------

def test_legacy_panel_resolve_log_path_via_config(tmp_path):
    """_resolve_default_log_path() deve consultar config service e resolver para logs_dir/legacy_panel_rollout.csv."""
    fake_paths = {"logs_dir": str(tmp_path / "logs")}
    mock_cfg = MagicMock()
    mock_cfg.get_paths.return_value = fake_paths

    with patch("services.core.config_service.config_service", mock_cfg):
        from services import legacy_panel_governance as lpg
        import importlib
        importlib.reload(lpg)

        resolved = lpg._resolve_default_log_path()

    expected = tmp_path / "logs" / "legacy_panel_rollout.csv"
    assert Path(resolved).resolve() == expected.resolve(), (
        f"_resolve_default_log_path() esperado '{expected}', obtido '{resolved}'."
    )


def test_legacy_panel_resolve_log_path_fallback_contem_logs(monkeypatch):
    """_resolve_default_log_path() sem logs_dir no config deve retornar path com 'logs'."""
    monkeypatch.delenv("INTEGRAGAL_LEGACY_PANEL_GOV_LOG_PATH", raising=False)

    mock_cfg = MagicMock()
    mock_cfg.get_paths.return_value = {}
    with patch("services.core.config_service.config_service", mock_cfg):
        from services import legacy_panel_governance as lpg
        import importlib
        importlib.reload(lpg)

        resolved = lpg._resolve_default_log_path()

    assert "logs" in str(resolved), (
        f"Fallback de _resolve_default_log_path() nao contem 'logs': '{resolved}'."
    )


def test_legacy_panel_resolve_log_path_env_var_tem_precedencia(tmp_path, monkeypatch):
    """_resolve_default_log_path() deve respeitar env var INTEGRAGAL_LEGACY_PANEL_GOV_LOG_PATH."""
    custom_path = str(tmp_path / "custom" / "log.csv")
    monkeypatch.setenv("INTEGRAGAL_LEGACY_PANEL_GOV_LOG_PATH", custom_path)

    from services import legacy_panel_governance as lpg
    import importlib
    importlib.reload(lpg)

    resolved = lpg._resolve_default_log_path()
    assert str(resolved) == custom_path, (
        f"Env var nao teve precedencia. Esperado '{custom_path}', obtido '{resolved}'."
    )
