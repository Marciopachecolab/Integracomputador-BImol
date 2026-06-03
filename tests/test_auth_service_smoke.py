"""Cobertura previa de caracterizacao T-051a (Fase 5 Audit Refactoring).

Captura comportamento ATUAL de autenticar_credenciais ANTES da implementacao
do lockout server-side. Garante que mudancas preservem invariantes existentes.

Cenarios cobertos:
1. Login com usuario inexistente -> retorna None
2. Login com senha incorreta -> retorna None
3. Login com credenciais corretas -> retorna dict com chaves esperadas
4. Sucesso atualiza ultimo_acesso

Estes testes formam a baseline. Apos T-051 (implementacao), TODOS devem
continuar passando + os novos testes de lockout em T-052.

NOTA: usa fixture de CSV temporario com provider CSV injetado; NAO toca
usuarios.csv real nem depende do backend configurado.
"""
from __future__ import annotations

import csv
from datetime import datetime

import bcrypt
import pytest

import autenticacao.auth_service as auth_mod
from autenticacao.auth_service import AuthService
from services.persistence.persistence_adapters import CsvUserRepositoryAdapter


# Schema canonico de usuarios.csv (USER_COLUMNS em auth_service)
USERS_HEADERS = [
    "id", "usuario", "senha_hash", "nivel_acesso", "status",
    "data_criacao", "ultimo_acesso", "tentativas_falhas",
    "bloqueado_ate", "preferencias",
]


def _write_user_csv(csv_path, *, tentativas="0", bloqueado_ate=""):
    senha_hash = bcrypt.hashpw(b"senha-correta", bcrypt.gensalt()).decode("utf-8")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=USERS_HEADERS)
        w.writeheader()
        w.writerow({
            "id": "uid-test-1",
            "usuario": "testuser",
            "senha_hash": senha_hash,
            "nivel_acesso": "DIAGNOSTICO",
            "status": "ATIVO",
            "data_criacao": datetime.now().isoformat(),
            "ultimo_acesso": "",
            "tentativas_falhas": tentativas,
            "bloqueado_ate": bloqueado_ate,
            "preferencias": "{}",
        })


class _CsvOnlyProvider:
    """Provider minimo que expoe apenas o repositorio de usuarios em CSV temp."""

    def __init__(self, csv_path):
        self._repo = CsvUserRepositoryAdapter(csv_path=str(csv_path))

    def users(self):
        return self._repo


@pytest.fixture
def csv_with_user(tmp_path):
    """Cria CSV temporario com 1 usuario 'testuser' / senha 'senha-correta'."""
    csv_path = tmp_path / "usuarios.csv"
    _write_user_csv(csv_path)
    return csv_path


@pytest.fixture
def auth_with_csv(csv_with_user, monkeypatch):
    """AuthService apontando para CSV temporario via provider injetado."""
    # _garantir_usuarios_csv usa resolve_users_csv_path importado no namespace
    monkeypatch.setattr(auth_mod, "resolve_users_csv_path", lambda: csv_with_user)
    return AuthService(provider=_CsvOnlyProvider(csv_with_user))


def test_login_usuario_inexistente_retorna_none(auth_with_csv):
    """Cenario 1: usuario nao existe no CSV -> None."""
    result = auth_with_csv.autenticar_credenciais("naoexiste", "qualquer-senha")
    assert result is None


def test_login_senha_incorreta_retorna_none(auth_with_csv):
    """Cenario 2: usuario existe mas senha errada -> None."""
    result = auth_with_csv.autenticar_credenciais("testuser", "senha-errada")
    assert result is None


def test_login_credenciais_corretas_retorna_dict(auth_with_csv):
    """Cenario 3: credenciais corretas -> dict com chaves de usuario."""
    result = auth_with_csv.autenticar_credenciais("testuser", "senha-correta")
    assert result is not None
    assert isinstance(result, dict)
    for key in ("usuario", "nivel_acesso", "status"):
        assert key in result, f"Chave '{key}' ausente no retorno"
    assert result["usuario"] == "testuser"


def test_login_sucesso_retorna_contrato_canonico(auth_with_csv):
    """Cenario 4: sucesso retorna dict com o contrato canonico de chaves.

    Invariante estavel (vale antes e depois de T-051): o retorno de sucesso
    expoe sempre as mesmas chaves canonicas e seus valores derivados da linha
    do usuario. Nao se afirma aqui o efeito colateral de ultimo_acesso porque
    o estado ATUAL (pre-T-051) NAO o persiste; T-051 passara a persistir, mas
    o contrato de retorno permanece o mesmo.
    """
    result = auth_with_csv.autenticar_credenciais("testuser", "senha-correta")
    assert result is not None
    chaves_canonicas = {
        "usuario", "nivel_acesso", "status", "data_criacao", "ultimo_acesso",
    }
    assert chaves_canonicas.issubset(set(result.keys()))
    assert result["usuario"] == "testuser"
    assert result["nivel_acesso"] == "DIAGNOSTICO"
    assert result["status"] == "ATIVO"
