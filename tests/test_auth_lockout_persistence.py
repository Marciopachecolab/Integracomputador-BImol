"""Teste T-052 (Fase 5 Audit Refactoring) - lockout server-side persistente.

Cenarios cobertos (AC-7.5):
1. 5 falhas consecutivas bloqueiam usuario (mesmo com senha correta na 6a tentativa).
2. Sucesso anterior reseta contador.
3. Apos auto-desbloqueio (bloqueado_ate expirado), usuario consegue logar.
4. Timestamp bloqueado_ate e persistido no CSV (verificavel via re-leitura).

NOTA: usa provider CSV injetado em tmp_path; NAO toca usuarios.csv real
nem depende do backend configurado (T-AUD-021: rodar SEM -n auto).
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

import bcrypt
import pytest

import autenticacao.auth_service as auth_mod
from autenticacao.auth_service import (
    AuthService,
    MAX_TENTATIVAS_FALHAS,
    BLOQUEIO_DURACAO_MINUTOS,
)
from services.persistence.persistence_adapters import CsvUserRepositoryAdapter


USERS_HEADERS = [
    "id", "usuario", "senha_hash", "nivel_acesso", "status",
    "data_criacao", "ultimo_acesso", "tentativas_falhas",
    "bloqueado_ate", "preferencias",
]


class _CsvOnlyProvider:
    """Provider minimo que expoe apenas o repositorio de usuarios em CSV temp."""

    def __init__(self, csv_path):
        self._repo = CsvUserRepositoryAdapter(csv_path=str(csv_path))

    def users(self):
        return self._repo


@pytest.fixture
def csv_with_user(tmp_path):
    csv_path = tmp_path / "usuarios.csv"
    senha_hash = bcrypt.hashpw(b"senha-correta", bcrypt.gensalt()).decode("utf-8")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=USERS_HEADERS)
        w.writeheader()
        w.writerow({
            "id": "uid-1",
            "usuario": "testuser",
            "senha_hash": senha_hash,
            "nivel_acesso": "DIAGNOSTICO",
            "status": "ATIVO",
            "data_criacao": datetime.now().isoformat(),
            "ultimo_acesso": "",
            "tentativas_falhas": "0",
            "bloqueado_ate": "",
            "preferencias": "{}",
        })
    return csv_path


@pytest.fixture
def auth_svc(csv_with_user, monkeypatch):
    monkeypatch.setattr(auth_mod, "resolve_users_csv_path", lambda: csv_with_user)
    return AuthService(provider=_CsvOnlyProvider(csv_with_user))


def _read_user_row(csv_path: Path) -> dict:
    with open(csv_path, encoding="utf-8") as f:
        return next(csv.DictReader(f))


def test_5_falhas_bloqueiam_usuario_mesmo_com_senha_correta_na_6a(auth_svc, csv_with_user):
    """AC-7.5 cenario 1: apos MAX_TENTATIVAS, proxima retorna None mesmo
    com senha correta."""
    for i in range(MAX_TENTATIVAS_FALHAS):
        result = auth_svc.autenticar_credenciais("testuser", f"senha-errada-{i}")
        assert result is None, f"Falha {i + 1} deveria retornar None"

    row = _read_user_row(csv_with_user)
    assert int(row["tentativas_falhas"]) >= MAX_TENTATIVAS_FALHAS
    assert row["bloqueado_ate"], "bloqueado_ate deve estar populado apos atingir o limite"

    # 6a tentativa COM SENHA CORRETA deve retornar None (bloqueado)
    result = auth_svc.autenticar_credenciais("testuser", "senha-correta")
    assert result is None, "Login bloqueado deve retornar None mesmo com senha correta"


def test_sucesso_reseta_contador(auth_svc, csv_with_user):
    """AC-7.5 cenario 2: sucesso zera tentativas_falhas e bloqueado_ate."""
    auth_svc.autenticar_credenciais("testuser", "errada-1")
    auth_svc.autenticar_credenciais("testuser", "errada-2")
    row = _read_user_row(csv_with_user)
    assert int(row["tentativas_falhas"]) == 2

    result = auth_svc.autenticar_credenciais("testuser", "senha-correta")
    assert result is not None
    row = _read_user_row(csv_with_user)
    assert int(row["tentativas_falhas"]) == 0, "Contador deve zerar apos sucesso"
    assert row["bloqueado_ate"] == "", "bloqueado_ate deve limpar apos sucesso"


def test_auto_desbloqueio_apos_expiracao(auth_svc, csv_with_user):
    """AC-7.5 cenario 3: bloqueado_ate no passado permite novo login."""
    with open(csv_with_user, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    expirado = (datetime.now() - timedelta(minutes=1)).isoformat()
    rows[0]["tentativas_falhas"] = "5"
    rows[0]["bloqueado_ate"] = expirado
    with open(csv_with_user, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=USERS_HEADERS)
        w.writeheader()
        w.writerows(rows)

    result = auth_svc.autenticar_credenciais("testuser", "senha-correta")
    assert result is not None, "Bloqueio expirado deve liberar login"
    row = _read_user_row(csv_with_user)
    assert int(row["tentativas_falhas"]) == 0
    assert row["bloqueado_ate"] == ""


def test_timestamp_persistido_corretamente(auth_svc, csv_with_user):
    """Sanidade: timestamp gerado em bloqueio e ISO format parseavel e no futuro."""
    for i in range(MAX_TENTATIVAS_FALHAS):
        auth_svc.autenticar_credenciais("testuser", f"errada-{i}")
    row = _read_user_row(csv_with_user)
    assert row["bloqueado_ate"], "bloqueado_ate populado"
    parsed = datetime.fromisoformat(row["bloqueado_ate"])
    now = datetime.now()
    assert now < parsed <= now + timedelta(minutes=BLOQUEIO_DURACAO_MINUTOS + 1)
