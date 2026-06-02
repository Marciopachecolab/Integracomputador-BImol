"""
Teste-guardiao: fallbacks de path de banco devem apontar para banco_runtime/ e banco_template/.

Ref: LOG-UNIF-002 / plano de uniformizacao de pastas de dados (2026-05-29).

Verifica:
- resolve_banco_dir() sem config aponta para banco_runtime/, nao banco/
- ConfigLoader.BASE_PATH aponta para banco_template/
- DEFAULT_ROOTS dos scripts de encoding inclui banco_runtime
"""

import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# 1. path_resolver.resolve_banco_dir() fallback
# ---------------------------------------------------------------------------

def test_resolve_banco_dir_fallback_aponta_para_banco_runtime():
    """resolve_banco_dir() sem config deve retornar banco_runtime/, nao banco/."""
    mock_cfg = MagicMock()
    mock_cfg.get_paths.return_value = {}

    with patch("services.core.config_service.config_service", mock_cfg):
        from services import path_resolver
        importlib.reload(path_resolver)
        result = path_resolver.resolve_banco_dir()

    assert "banco_runtime" in str(result), (
        f"resolve_banco_dir() fallback deveria apontar para banco_runtime/, obtido: '{result}'."
    )
    assert "banco/" not in str(result).replace("banco_runtime", ""), (
        f"resolve_banco_dir() nao deve cair em banco/ legado. Obtido: '{result}'."
    )


def test_resolve_banco_dir_usa_exams_catalog_csv_quando_configurado(tmp_path):
    """resolve_banco_dir() usa dirname do exams_catalog_csv quando configurado."""
    fake_catalog = str(tmp_path / "banco_runtime" / "exames_config.csv")
    mock_cfg = MagicMock()
    mock_cfg.get_paths.return_value = {"exams_catalog_csv": fake_catalog}

    with patch("services.core.config_service.config_service", mock_cfg):
        from services import path_resolver
        importlib.reload(path_resolver)
        result = path_resolver.resolve_banco_dir()

    expected = tmp_path / "banco_runtime"
    assert result.resolve() == expected.resolve(), (
        f"resolve_banco_dir() deveria retornar '{expected}', obtido '{result}'."
    )


# ---------------------------------------------------------------------------
# 2. ConfigLoader.BASE_PATH aponta para banco_template/
# ---------------------------------------------------------------------------

def test_config_loader_base_path_e_banco_template():
    """ConfigLoader.BASE_PATH deve ser 'banco_template', nao 'banco'."""
    from services.engine.config_loader import ConfigLoader

    assert str(ConfigLoader.BASE_PATH) == "banco_template", (
        f"ConfigLoader.BASE_PATH deveria ser 'banco_template', obtido '{ConfigLoader.BASE_PATH}'."
    )


def test_config_loader_base_path_nao_e_banco_legado():
    """ConfigLoader.BASE_PATH nao deve apontar para 'banco' (pasta legada)."""
    from services.engine.config_loader import ConfigLoader

    assert str(ConfigLoader.BASE_PATH) != "banco", (
        "ConfigLoader.BASE_PATH ainda aponta para 'banco' (legado). "
        "Deve ser 'banco_template'."
    )


def test_config_loader_encontra_equipment_profiles():
    """ConfigLoader.get_equipment_profiles() deve retornar dados nao vazios com BASE_PATH correto."""
    from services.engine.config_loader import ConfigLoader

    profiles = ConfigLoader.get_equipment_profiles()
    assert isinstance(profiles, list), (
        f"get_equipment_profiles() deve retornar list, obtido {type(profiles)}."
    )
    assert len(profiles) > 0, (
        "get_equipment_profiles() retornou lista vazia — BASE_PATH incorreto ou arquivo ausente."
    )


# ---------------------------------------------------------------------------
# 3. DEFAULT_ROOTS dos scripts inclui banco_runtime
# ---------------------------------------------------------------------------

def test_normalize_legacy_csv_default_roots_inclui_banco_runtime():
    """DEFAULT_ROOTS de normalize_legacy_csv_utf8.py deve incluir 'banco_runtime'."""
    import scripts.normalize_legacy_csv_utf8 as m
    importlib.reload(m)

    assert "banco_runtime" in m.DEFAULT_ROOTS, (
        f"normalize_legacy_csv_utf8.DEFAULT_ROOTS nao inclui 'banco_runtime'. "
        f"Obtido: {m.DEFAULT_ROOTS}"
    )


def test_scan_csv_encoding_default_roots_inclui_banco_runtime():
    """DEFAULT_ROOTS de scan_csv_encoding_conformance.py deve incluir 'banco_runtime'."""
    import scripts.scan_csv_encoding_conformance as m
    importlib.reload(m)

    assert "banco_runtime" in m.DEFAULT_ROOTS, (
        f"scan_csv_encoding_conformance.DEFAULT_ROOTS nao inclui 'banco_runtime'. "
        f"Obtido: {m.DEFAULT_ROOTS}"
    )
