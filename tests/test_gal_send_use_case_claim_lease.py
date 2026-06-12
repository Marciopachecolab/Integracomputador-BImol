# -*- coding: utf-8 -*-
"""Integracao claim/lease no GalSendUseCase, sem Selenium (CONC-003 / FINDING-005).

Demonstra a propriedade que o codigo antigo NAO tinha: idempotencia cross-process.
Usa um fake do GalSendServicePort + um SqliteGalClaimsRepository real (em tmp)
injetado no use case, simulando duas "estacoes" que compartilham o claim store.
"""

import pandas as pd
import pytest

from application.gal_send_use_case import GalSendRequest, GalSendUseCase
from services.gal.gal_claims import ClaimOutcome, SqliteGalClaimsRepository
from services.gal.gal_transactions import build_idempotency_key


class _FakeDriver:
    def execute_script(self, *_a, **_k):
        raise RuntimeError("sem navegador real no teste")

    def get_cookies(self):
        return []

    def quit(self):
        pass


class _FakeService:
    def __init__(self, *, df, metas=None, envio_status="sucesso"):
        self._df = df
        self._metas = metas
        self._envio_status = envio_status
        self.enviadas = []

    def get_user_access_level(self, username):
        return "ADMIN"

    def realizar_login(self, driver, usuario, senha):
        pass

    def ler_csv_resultados(self, csv_path):
        return self._df

    def build_idempotency_key(self, **kwargs):
        return build_idempotency_key(**kwargs)

    def get_transaction_journal_path(self):
        from pathlib import Path
        return Path("journal_fake.csv")

    def load_successful_idempotency_keys(self, journal_path):
        return set()

    def buscar_metadados(self, driver, codigos, exam_cfg=None):
        if self._metas is not None:
            return dict(self._metas)
        return {str(c).strip(): {"meta": True} for c in codigos}

    def construir_payload(self, meta, row, observacao_geral, exam_cfg=None):
        return {"codigoAmostra": str(row.get("codigoamostra", "")), "kit": str(row.get("kit", ""))}

    def enviar_amostra(self, driver, payload):
        self.enviadas.append(payload)
        return {"codigoAmostra": payload.get("codigoAmostra", ""), "status": self._envio_status, "erro": []}

    def append_journal_events(self, *, relatorio_local, run_id, kit_default):
        return len(relatorio_local)

    def salvar_relatorios(self, **kwargs):
        pass

    def log(self, message, level="info"):
        pass


_CODIGO, _KIT, _LOTE, _DATA = "A001", "1175", "L1", "2026-06-01"
_CORRIDA, _NOME, _ARQ, _PARTE = "C1", "Corrida 1", "arq.xlsx", 1


def _df():
    return pd.DataFrame(
        [{"codigoamostra": _CODIGO, "kit": _KIT, "lotekit": _LOTE, "dataprocessamentofim": _DATA}]
    )


def _request():
    return GalSendRequest(
        csv_path="x.csv", usuario="u", senha="s", usuario_logado="op", observacao="obs",
        relatorio_filename="rel.csv", exame_id="",
        corrida_id=_CORRIDA, nome_corrida=_NOME, arquivo_corrida=_ARQ, parte_placa=_PARTE,
    )


def _keys():
    legacy = build_idempotency_key(codigo_amostra=_CODIGO, kit=_KIT, lote_kit=_LOTE, data_exame=_DATA)
    scoped = build_idempotency_key(
        codigo_amostra=_CODIGO, kit=_KIT, lote_kit=_LOTE, data_exame=_DATA,
        corrida_id=_CORRIDA, nome_corrida=_NOME, arquivo_corrida=_ARQ, parte_placa=_PARTE,
    )
    return legacy, scoped


def _run(service, claims):
    uc = GalSendUseCase(service, webdriver_factory=lambda: _FakeDriver(), claims_repository=claims)
    return uc.execute(_request())


def test_fresh_sample_acquires_and_commits(tmp_path):
    claims = SqliteGalClaimsRepository(tmp_path / "claims.db")
    svc = _FakeService(df=_df())
    result = _run(svc, claims)

    assert result.sucessos == 1
    assert len(svc.enviadas) == 1
    # Apos sucesso, as chaves ficam committed -> outra estacao veria duplicado.
    legacy, scoped = _keys()
    assert claims.try_claim([scoped], owner="outra", ttl_seconds=300) == ClaimOutcome.ALREADY_COMMITTED
    assert claims.try_claim([legacy], owner="outra", ttl_seconds=300) == ClaimOutcome.ALREADY_COMMITTED


def test_second_station_sees_committed_as_duplicado(tmp_path):
    claims = SqliteGalClaimsRepository(tmp_path / "claims.db")
    legacy, scoped = _keys()
    # Estacao A ja enviou e commitou (compartilham o mesmo claim store).
    claims.try_claim([scoped, legacy], owner="estacaoA", ttl_seconds=300)
    claims.commit([scoped, legacy], owner="estacaoA")

    svc = _FakeService(df=_df())
    result = _run(svc, claims)

    assert result.sucessos == 0
    assert svc.enviadas == [], "estacao B nao pode reenviar amostra ja committed por A"
    assert result.relatorio_local[0]["status"] == "duplicado"


def test_inflight_held_by_other_is_duplicado(tmp_path):
    claims = SqliteGalClaimsRepository(tmp_path / "claims.db")
    legacy, scoped = _keys()
    # Estacao A esta com o envio EM VOO (inflight, nao expirado).
    assert claims.try_claim([scoped, legacy], owner="estacaoA", ttl_seconds=300) == ClaimOutcome.ACQUIRED

    svc = _FakeService(df=_df())
    result = _run(svc, claims)

    assert svc.enviadas == [], "estacao B nao pode enviar enquanto A esta em voo"
    assert result.relatorio_local[0]["status"] == "duplicado"


def test_failed_send_releases_claim_for_retry(tmp_path):
    claims = SqliteGalClaimsRepository(tmp_path / "claims.db")
    svc = _FakeService(df=_df(), envio_status="erro")
    result = _run(svc, claims)

    assert result.sucessos == 0
    assert len(svc.enviadas) == 1  # tentou enviar
    # Como falhou, o claim foi liberado -> nova tentativa pode reivindicar.
    _, scoped = _keys()
    assert claims.try_claim([scoped], owner="retry", ttl_seconds=300) == ClaimOutcome.ACQUIRED
