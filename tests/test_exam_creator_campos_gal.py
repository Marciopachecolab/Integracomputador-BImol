"""Guardioes: wizard de criacao de exames popula corretamente campos GAL.

Cobre:
- _build_registry_exam_config reflete equipamento, tipo_placa, kit, gal_exame_codigo,
  panel_tests_id, export_fields e mapa_alvos capturados pelo wizard.
- Fallback de painel: construir_payload deriva testes_do_painel de export_fields quando
  o painel nao esta em panel_tests.
- _norm_gal_field normaliza nomes de analito corretamente.
- gal_formatter.formatar_para_gal usa kit/painel/analitos do ExamConfig em vez dos
  defaults de VR1e2 quando o exame tem todos os campos preenchidos.
- _exam_to_dict round-trip preserva gal_exame_codigo, kit_codigo, export_fields.
"""

import pytest

pytest.importorskip("customtkinter")


# ---------------------------------------------------------------------------
# Helpers compartilhados
# ---------------------------------------------------------------------------

def _make_exam_config(**kw):
    from services.exam_registry import ExamConfig

    base = dict(
        nome_exame="Teste Dengue",
        slug="teste_dengue",
        equipamento="quantstudio",
        tipo_placa_analitica="96",
        esquema_agrupamento="96->32",
        kit_codigo="1832",
        alvos=["DEN1", "DEN2", "RP"],
        mapa_alvos={"DEN1": "DEN1", "DEN2": "DEN2", "RP": "RP"},
        faixas_ct={"detect_max": 40.0, "inconc_min": 38.1, "inconc_max": 40.0, "rp_min": 8.1, "rp_max": 35.0},
        rps=["RP"],
        export_fields=["Dengue1", "Dengue2"],
        panel_tests_id="zdcbm",
        gal_exame_codigo="PEQZDC",
        controles={"cn": [], "cp": ["RP"]},
    )
    base.update(kw)
    return ExamConfig(**base)


def _make_bare_page(exam_data, targets=None, ct_thresholds=None):
    from ui.modules.exam_creator.wizard import ExamCreatorWizardPage

    page = object.__new__(ExamCreatorWizardPage)
    page.exam_data = exam_data
    page.temp_targets = targets or []
    page.temp_ct_thresholds = ct_thresholds or []
    page._build_v2_payload = lambda: ([], [])
    page._derive_legacy_from_v2 = lambda *a, **k: {
        "alvos": [],
        "mapa_alvos": {},
        "faixas_ct": {},
        "rps": [],
        "controles": {"cn": [], "cp": []},
    }
    return page


# ---------------------------------------------------------------------------
# 1. _build_registry_exam_config usa campos GAL capturados
# ---------------------------------------------------------------------------

def test_build_config_reflete_campos_gal(monkeypatch):
    import services.exam_registry as er

    monkeypatch.setattr(er.registry, "exams", {})
    monkeypatch.setattr(er.registry, "get", lambda _: None)

    page = _make_bare_page({
        "id": "teste_dengue",
        "display_name": "Teste Dengue",
        "version": "1.0",
        "pocos_por_amostra": 3,
        "equipamento": "quantstudio",
        "tipo_placa_analitica": "96",
        "gal_exame_codigo": "PEQZDC",
        "kit_codigo": "1832",
        "panel_tests_id": "zdcbm",
        "export_mapping": {"DEN1": "Dengue1", "DEN2": "Dengue2"},
        "export_fields": ["Dengue1", "Dengue2"],
    })

    cfg = page._build_registry_exam_config()

    assert cfg.equipamento == "quantstudio"
    assert cfg.tipo_placa_analitica == "96"
    assert cfg.gal_exame_codigo == "PEQZDC"
    assert cfg.kit_codigo == "1832"
    assert cfg.panel_tests_id == "zdcbm"
    assert cfg.export_fields == ["Dengue1", "Dengue2"]
    # mapa_alvos deve incluir entrada GAL->internal para Dengue1 e Dengue2
    assert "DENGUE1" in cfg.mapa_alvos
    assert cfg.mapa_alvos["DENGUE1"] == "DEN1"
    assert "DENGUE2" in cfg.mapa_alvos
    assert cfg.mapa_alvos["DENGUE2"] == "DEN2"


def test_build_config_esquema_agrupamento_derivado_de_pocos(monkeypatch):
    import services.exam_registry as er

    monkeypatch.setattr(er.registry, "exams", {})
    monkeypatch.setattr(er.registry, "get", lambda _: None)

    page = _make_bare_page({
        "id": "x", "display_name": "X", "version": "1.0", "pocos_por_amostra": 3,
        "equipamento": "", "tipo_placa_analitica": "",
        "gal_exame_codigo": "", "kit_codigo": "", "panel_tests_id": "",
        "export_mapping": {}, "export_fields": [],
    })
    cfg = page._build_registry_exam_config()
    assert cfg.esquema_agrupamento == "96->32"


# ---------------------------------------------------------------------------
# 2. _build_export_mapping_from_cfg reconstrói mapeamento
# ---------------------------------------------------------------------------

def test_build_export_mapping_from_cfg():
    from ui.modules.exam_creator.wizard import ExamCreatorWizardPage

    cfg = _make_exam_config(
        mapa_alvos={"DEN1": "DEN1", "DEN2": "DEN2", "RP": "RP", "DENGUE1": "DEN1"},
    )
    mapping = ExamCreatorWizardPage._build_export_mapping_from_cfg(cfg)
    # DEN1 tem entrada nao-identidade DENGUE1→DEN1, logo nome_gal = "DENGUE1"
    assert mapping.get("DEN1") == "DENGUE1"
    # DEN2 nao tem entrada nao-identidade → vazio
    assert mapping.get("DEN2", "") == ""


# ---------------------------------------------------------------------------
# 3. _norm_gal_field normaliza corretamente
# ---------------------------------------------------------------------------

def test_norm_gal_field():
    from exportacao.envio_gal import _norm_gal_field

    assert _norm_gal_field("Dengue1") == "dengue1"
    assert _norm_gal_field("Influenza A") == "influenzaa"
    assert _norm_gal_field("VSincicialResp") == "vsincicialresp"
    assert _norm_gal_field("adeno-virus") == "adenovirus"


# ---------------------------------------------------------------------------
# 4. Fallback de painel em construir_payload
# ---------------------------------------------------------------------------

def test_construir_payload_fallback_export_fields():
    """Quando painel nao esta em panel_tests, usa export_fields do exam_cfg."""
    import pandas as pd
    from exportacao.envio_gal import GalService

    cfg = _make_exam_config(export_fields=["Dengue1", "Dengue2"], panel_tests_id="zdcbm")

    gi = object.__new__(GalService)
    gi.base_url = ""
    gi.login_ids = {}
    gi.endpoints = {"submit": "/submit", "metadata": "/meta"}
    gi.panel_tests = {"1": ["influenzaa"]}  # "zdcbm" nao presente
    gi.timeout = 30
    gi._runtime_context = {}
    gi.log = lambda *a, **k: None

    # Painel 99 nao esta em panel_tests ({"1": [...]}), forcando o fallback.
    meta = {"codigo": "123", "requisicao": "REQ", "paciente": "P", "painel": 99,
            "metodo": "RT-PCR", "kit": 1832}
    row = pd.Series({
        "codigoamostra": "123",
        "painel": 99,
        "dengue1": 1,
        "dengue2": 1,
        "dataprocessamentofim": "29/05/2026",
        "kit": 1832,
        "lotekit": "",
        "valorreferencia": "",
        "observacao": "",
    })

    payload = gi.construir_payload(meta, row, "", exam_cfg=cfg)

    # resultados deve conter dengue1 e dengue2 (derivados de export_fields)
    assert "dengue1" in payload["resultados"]
    assert "dengue2" in payload["resultados"]


def test_construir_payload_nao_afeta_painel_existente():
    """Quando painel existe em panel_tests, comportamento original e mantido."""
    import pandas as pd
    from exportacao.envio_gal import GalService

    cfg = _make_exam_config(export_fields=["Dengue1"], panel_tests_id="1")

    gi = object.__new__(GalService)
    gi.base_url = ""
    gi.login_ids = {}
    gi.endpoints = {"submit": "/submit", "metadata": "/meta"}
    gi.panel_tests = {"1": ["influenzaa", "influenzab"]}
    gi.timeout = 30
    gi._runtime_context = {}
    gi.log = lambda *a, **k: None

    meta = {"codigo": "456", "requisicao": "", "paciente": "", "painel": 1,
            "metodo": "", "kit": 427}
    row = pd.Series({
        "codigoamostra": "456", "painel": 1,
        "influenzaa": 1, "influenzab": 0,
        "dataprocessamentofim": "29/05/2026",
        "kit": 427, "lotekit": "", "valorreferencia": "", "observacao": "",
    })

    payload = gi.construir_payload(meta, row, "", exam_cfg=cfg)
    assert "influenzaa" in payload["resultados"]
    assert "influenzab" in payload["resultados"]
    # dengue1 nao deve aparecer (painel existente tem prioridade)
    assert "dengue1" not in payload["resultados"]


# ---------------------------------------------------------------------------
# 5. gal_formatter usa kit/painel/analitos do ExamConfig (sem fallback VR1e2)
# ---------------------------------------------------------------------------

def test_formatar_para_gal_usa_campos_do_exame():
    import pandas as pd

    pytest.importorskip("pandas")
    from exportacao.gal_formatter import formatar_para_gal

    cfg = _make_exam_config(
        kit_codigo="1832",
        panel_tests_id="zdcbm",
        gal_exame_codigo="PEQZDC",
        export_fields=["Dengue1", "Dengue2"],
        mapa_alvos={"DEN1": "DEN1", "DEN2": "DEN2", "DENGUE1": "DEN1", "DENGUE2": "DEN2", "RP": "RP"},
    )

    df = pd.DataFrame([{
        "codigo": "100",
        "Res_DEN1": "Detectado",
        "Res_DEN2": "Nao Detectado",
        "Resultado_geral": "Detectavel para DEN1",
    }])

    out = formatar_para_gal(df, exam_cfg=cfg)

    # kit deve ser o do exame, nao "1175" (default VR1e2)
    assert str(out["kit"].iloc[0]) == "1832"
    # painel deve ser o do exame
    assert str(out["painel"].iloc[0]) == "zdcbm"
    # exame deve ser o gal_exame_codigo
    assert str(out["exame"].iloc[0]) == "PEQZDC"
    # colunas de analito do exame devem existir
    assert "dengue1" in out.columns or "dengue2" in out.columns


# ---------------------------------------------------------------------------
# 6. _exam_to_dict round-trip preserva campos GAL
# ---------------------------------------------------------------------------

def test_exam_to_dict_round_trip_campos_gal():
    from ui.modules.cadastros_ui import RegistryExamEditor

    cfg = _make_exam_config(
        gal_exame_codigo="PEQZDC",
        kit_codigo="1832",
        panel_tests_id="zdcbm",
        export_fields=["Dengue1", "Dengue2"],
    )
    editor = object.__new__(RegistryExamEditor)
    d = RegistryExamEditor._exam_to_dict(editor, cfg)

    assert d["gal_exame_codigo"] == "PEQZDC"
    assert str(d["kit_codigo"]) == "1832"
    assert d["panel_tests_id"] == "zdcbm"
    assert d["export_fields"] == ["Dengue1", "Dengue2"]
