# -*- coding: utf-8 -*-
"""Suite mockada do GalSendUseCase sem Selenium real (GAL-PEND-002 / FINDING-006/007).

Cobre o contrato de orquestracao do envio GAL usando um fake do
`GalSendServicePort`, um fake de webdriver injetado via `webdriver_factory` e a
funcao real `build_idempotency_key` (dual-key autentica). Nenhum navegador,
Selenium, requests externo ou GAL real e acionado.

Comportamentos validados:
- envio com sucesso persiste no journal e marca status sucesso;
- idempotencia dual-key: chave com escopo bloqueia como duplicado;
- idempotencia dual-key: match apenas pela chave legada (4 campos) bloqueia (CA-11);
- inflight_keys: linhas identicas no mesmo CSV nao geram envio duplo;
- amostra sem metadados vira 'nao_encontrado' sem chamar enviar_amostra;
- CSV invalido (None) falha cedo com ValueError, antes de abrir o navegador;
- autorizacao por matriz: nivel sem permissao levanta AuthorizationDeniedError;
- guardiao: a camada de aplicacao nao importa Selenium no topo do modulo.
"""

import ast
import io
from pathlib import Path

import pandas as pd
import pytest

from application.access_control import AuthorizationDeniedError
from application.gal_send_use_case import GalSendRequest, GalSendUseCase
from services.gal.gal_transactions import build_idempotency_key


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _FakeDriver:
    """Driver minimo: forca o fallback http_client=driver e registra quit()."""

    def __init__(self):
        self.quit_called = False

    def execute_script(self, *_a, **_k):
        # Forca o except em execute() -> http_client = driver (sem requests real).
        raise RuntimeError("sem navegador real no teste")

    def get_cookies(self):
        return []

    def quit(self):
        self.quit_called = True


class _FakeService:
    """Implementacao fake do GalSendServicePort para os testes."""

    def __init__(
        self,
        *,
        df,
        successful_keys=None,
        metas=None,
        access_level="ADMIN",
        envio_status="sucesso",
    ):
        self._df = df
        self._successful_keys = set(successful_keys or set())
        self._metas = metas
        self._access_level = access_level
        self._envio_status = envio_status
        # instrumentacao
        self.enviadas = []
        self.journal_appends = []
        self.salvar_relatorios_called = False
        self.logs = []

    # --- autenticacao/escopo ---
    def get_user_access_level(self, username):
        return self._access_level

    # --- login ---
    def realizar_login(self, driver, usuario, senha):
        self.login_called = True

    # --- io de CSV ---
    def ler_csv_resultados(self, csv_path):
        return self._df

    # --- idempotencia (delegada a funcao real) ---
    def build_idempotency_key(self, **kwargs):
        return build_idempotency_key(**kwargs)

    def get_transaction_journal_path(self):
        return Path("journal_fake.csv")

    def load_successful_idempotency_keys(self, journal_path):
        return set(self._successful_keys)

    # --- metadados/payload/envio ---
    def buscar_metadados(self, driver, codigos_amostra_set, exam_cfg=None):
        if self._metas is not None:
            return dict(self._metas)
        return {str(c).strip(): {"meta": True} for c in codigos_amostra_set}

    def construir_payload(self, meta, row, observacao_geral, exam_cfg=None):
        return {
            "codigoAmostra": str(row.get("codigoamostra", "")),
            "kit": str(row.get("kit", "")),
            "loteKit": str(row.get("lotekit", "")),
            "dataProcessamentoFim": str(row.get("dataprocessamentofim", "")),
        }

    def enviar_amostra(self, driver, payload):
        self.enviadas.append(payload)
        return {
            "codigoAmostra": payload.get("codigoAmostra", ""),
            "status": self._envio_status,
            "erro": [],
            "campos_invalidos": [],
        }

    # --- persistencia/relatorios ---
    def append_journal_events(self, *, relatorio_local, run_id, kit_default):
        self.journal_appends.append(list(relatorio_local))
        return len(relatorio_local)

    def salvar_relatorios(self, **kwargs):
        self.salvar_relatorios_called = True

    # --- log opcional ---
    def log(self, message, level="info"):
        self.logs.append((level, message))


def _df_uma_amostra(codigo="A001", kit="1175", lote="L1", data="2026-06-01"):
    return pd.DataFrame(
        [{"codigoamostra": codigo, "kit": kit, "lotekit": lote, "dataprocessamentofim": data}]
    )


def _request(**over):
    base = dict(
        csv_path="x.csv",
        usuario="u",
        senha="s",
        usuario_logado="op",
        observacao="obs",
        relatorio_filename="rel.csv",
        exame_id="",  # vazio -> nao consulta get_exam_cfg
        corrida_id="C1",
        nome_corrida="Corrida 1",
        arquivo_corrida="arq.xlsx",
        parte_placa=1,
    )
    base.update(over)
    return GalSendRequest(**base)


def _run(service, request):
    uc = GalSendUseCase(service, webdriver_factory=lambda: _FakeDriver())
    return uc.execute(request)


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

def test_envio_sucesso_persiste_e_marca_sucesso():
    svc = _FakeService(df=_df_uma_amostra())
    result = _run(svc, _request())

    assert result.total_amostras == 1
    assert result.sucessos == 1
    assert len(svc.enviadas) == 1
    assert len(svc.journal_appends) == 1  # _persist_success_immediately chamado
    assert svc.salvar_relatorios_called is True
    assert result.relatorio_local[0]["status"] == "sucesso"


def test_chave_escopo_existente_bloqueia_como_duplicado():
    scoped = build_idempotency_key(
        codigo_amostra="A001", kit="1175", lote_kit="L1", data_exame="2026-06-01",
        corrida_id="C1", nome_corrida="Corrida 1", arquivo_corrida="arq.xlsx", parte_placa=1,
    )
    svc = _FakeService(df=_df_uma_amostra(), successful_keys={scoped})
    result = _run(svc, _request())

    assert result.sucessos == 0
    assert svc.enviadas == []  # enviar_amostra NAO chamado
    assert result.relatorio_local[0]["status"] == "duplicado"


def test_match_apenas_chave_legada_bloqueia_ca11():
    # Apenas a chave legada (4 campos) consta no journal; a chave com escopo e nova.
    legacy = build_idempotency_key(
        codigo_amostra="A001", kit="1175", lote_kit="L1", data_exame="2026-06-01",
    )
    svc = _FakeService(df=_df_uma_amostra(), successful_keys={legacy})
    result = _run(svc, _request())

    assert result.sucessos == 0
    assert svc.enviadas == []
    assert result.relatorio_local[0]["status"] == "duplicado"
    assert legacy in result.relatorio_local[0]["detalhes"]


def test_inflight_impede_duplo_envio_no_mesmo_csv():
    # Duas linhas identicas no mesmo CSV: apenas uma deve ser enviada.
    df = pd.concat([_df_uma_amostra(), _df_uma_amostra()], ignore_index=True)
    svc = _FakeService(df=df)
    result = _run(svc, _request())

    assert result.total_amostras == 2
    assert len(svc.enviadas) == 1  # somente um envio efetivo
    status = sorted(item["status"] for item in result.relatorio_local)
    assert status == ["duplicado", "sucesso"]


def test_amostra_sem_metadados_vira_nao_encontrado():
    svc = _FakeService(df=_df_uma_amostra(), metas={})  # nenhum metadado
    result = _run(svc, _request())

    assert result.sucessos == 0
    assert svc.enviadas == []
    assert result.relatorio_local[0]["status"] == "nao_encontrado"


def test_csv_invalido_falha_cedo_com_valueerror():
    svc = _FakeService(df=None)
    with pytest.raises(ValueError):
        _run(svc, _request())
    assert svc.enviadas == []


def test_autorizacao_negada_para_nivel_sem_permissao():
    svc = _FakeService(df=_df_uma_amostra(), access_level="TECNICO")
    with pytest.raises(AuthorizationDeniedError):
        _run(svc, _request())
    assert svc.enviadas == []


def test_aplicacao_nao_importa_selenium_no_topo():
    """Guardiao FINDING-007: nenhum import de Selenium no nivel de modulo."""
    arq = Path(__file__).resolve().parents[1] / "application" / "gal_send_use_case.py"
    tree = ast.parse(io.open(arq, encoding="utf-8").read())
    proibidos = {"seleniumrequests", "selenium"}
    top_level_imports = []
    for node in tree.body:  # apenas nivel de modulo
        if isinstance(node, ast.Import):
            top_level_imports += [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            top_level_imports.append(node.module.split(".")[0])
    assert proibidos.isdisjoint(top_level_imports), (
        f"Selenium nao deve ser importado no topo da camada de aplicacao: {top_level_imports}"
    )
