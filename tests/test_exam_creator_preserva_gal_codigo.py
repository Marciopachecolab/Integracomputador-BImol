"""Guardiao de regressao: o wizard de cadastro e o editor de exames nao podem
zerar `gal_exame_codigo`/`panel_tests_id` ao salvar/reeditar um exame.

Contexto: em 2026-05-28 o exame VR1e2 foi reeditado pelo wizard, que reescreveu
`config/exams/vr1e2_biomanguinhos_7500.json` removendo `gal_exame_codigo` ("VRSRT")
e trocando `panel_tests_id` ("1" -> protocol_id). Sem `gal_exame_codigo`, a busca
de metadados do envio GAL nao envia `codExame` e o filtro local descarta todas as
amostras ("0 metadados encontrados"). Ver exportacao/envio_gal.buscar_metadados.
"""

import pytest

pytest.importorskip("customtkinter")


def _make_exam_config(**overrides):
    from services.exam_registry import ExamConfig

    base = dict(
        nome_exame="Exame X",
        slug="exame_x",
        equipamento="7500",
        tipo_placa_analitica="96",
        esquema_agrupamento="96->96",
        kit_codigo="",
        panel_tests_id="1",
        gal_exame_codigo="VRSRT",
    )
    base.update(overrides)
    return ExamConfig(**base)


def test_exam_to_dict_serializa_gal_exame_codigo():
    """Bug #1: _exam_to_dict precisa incluir gal_exame_codigo, senao o campo e
    descartado em todo save e o envio ao GAL quebra."""
    from ui.modules.cadastros_ui import RegistryExamEditor

    cfg = _make_exam_config(gal_exame_codigo="VRSRT", panel_tests_id="1")
    editor = object.__new__(RegistryExamEditor)  # evita __init__ (carrega registry/UI)

    exam_dict = RegistryExamEditor._exam_to_dict(editor, cfg)

    assert "gal_exame_codigo" in exam_dict
    assert exam_dict["gal_exame_codigo"] == "VRSRT"
    assert exam_dict["panel_tests_id"] == "1"


def _make_bare_wizard_page(exam_data):
    from ui.modules.exam_creator.wizard import ExamCreatorWizardPage

    page = object.__new__(ExamCreatorWizardPage)  # sem CTk __init__
    page.exam_data = exam_data
    # Stubs dos helpers de payload (independentes do estado de UI)
    page._build_v2_payload = lambda: ([], [])  # type: ignore[attr-defined]
    page._derive_legacy_from_v2 = lambda *a, **k: {  # type: ignore[attr-defined]
        "alvos": [],
        "mapa_alvos": {},
        "faixas_ct": {},
        "rps": [],
        "controles": {"cn": [], "cp": []},
    }
    return page


def test_wizard_preserva_gal_codigo_ao_reeditar(monkeypatch):
    """Bug #2: ao reeditar um exame existente, o wizard deve preservar
    gal_exame_codigo e panel_tests_id em vez de sobrescrever com protocol_id."""
    import services.exam_registry as exam_registry

    existing = _make_exam_config(
        nome_exame="VR1e2 Biomanguinhos 7500",
        slug="vr1e2_biomanguinhos_7500",
        gal_exame_codigo="VRSRT",
        panel_tests_id="1",
    )
    monkeypatch.setattr(exam_registry.registry, "exams", {"vr1e2 biomanguinhos 7500": existing})
    monkeypatch.setattr(
        exam_registry.registry,
        "get",
        lambda nome: existing if str(nome).strip() else None,
    )

    page = _make_bare_wizard_page(
        {
            "id": "12",  # protocol_id que ANTES virava panel_tests_id
            "display_name": "VR1e2 Biomanguinhos 7500",
            "version": "1.0",
            "pocos_por_amostra": 2,
        }
    )

    cfg = page._build_registry_exam_config()

    assert cfg.gal_exame_codigo == "VRSRT"
    assert cfg.panel_tests_id == "1"  # nao "12"


def test_wizard_exame_novo_sem_passo4(monkeypatch):
    """Exame novo sem Passo 4 preenchido: campos GAL ficam vazios (sem fallback
    para protocol_id). O wizard agora captura panel_tests_id explicitamente no
    Passo 4; se o usuario nao preencher, o valor permanece vazio."""
    import services.exam_registry as exam_registry

    monkeypatch.setattr(exam_registry.registry, "exams", {"algum exame": object()})
    monkeypatch.setattr(exam_registry.registry, "get", lambda nome: None)

    page = _make_bare_wizard_page(
        {
            "id": "99",
            "display_name": "Exame Novo",
            "version": "1.0",
            "pocos_por_amostra": 1,
            # panel_tests_id e gal_exame_codigo nao definidos (Passo 4 nao concluido)
        }
    )

    cfg = page._build_registry_exam_config()

    assert cfg.gal_exame_codigo == ""
    assert cfg.panel_tests_id == ""  # vazio, nao mais protocol_id
