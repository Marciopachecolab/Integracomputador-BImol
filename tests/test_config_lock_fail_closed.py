# -*- coding: utf-8 -*-
"""Guardiao do lock de gravacao do config.json (FINDING-004 / CONC-004 / INST-001).

O `_save_config` deve:
  - falhar-fechado quando nao conseguir o lock (nao gravar; retornar False);
  - NAO remover um lock alheio (apenas o lock que ele proprio criou);
  - gravar normalmente e remover o proprio lock quando nao ha contencao.

Todos os testes redirecionam `CONFIG_PATH` para um arquivo temporario via
monkeypatch — o `config.json` real do projeto NUNCA e tocado.
"""

import os

import services.core.config_service as cs_mod


def _isolar_config(tmp_path, monkeypatch, conteudo):
    """Aponta CONFIG_PATH para tmp e injeta um _config controlado no singleton."""
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "CONFIG_PATH", str(cfg_path))
    monkeypatch.setattr(cs_mod.config_service, "_config", dict(conteudo))
    return cfg_path


def test_timeout_falha_fechado_e_nao_remove_lock_alheio(tmp_path, monkeypatch):
    cfg_path = _isolar_config(tmp_path, monkeypatch, {"marcador": "novo"})
    # Acelera o timeout (sem alterar a logica de producao).
    monkeypatch.setattr(cs_mod, "_CONFIG_LOCK_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(cs_mod, "_CONFIG_LOCK_SLEEP_SECONDS", 0.01)

    # Lock "alheio" pre-existente (simula outro administrador gravando).
    foreign_lock = str(cfg_path) + ".lock"
    open(foreign_lock, "w").close()

    ok = cs_mod.config_service._save_config()

    assert ok is False, "deve falhar-fechado quando nao consegue o lock"
    assert os.path.exists(foreign_lock), "NAO pode remover o lock alheio"
    assert not cfg_path.exists(), "nao pode gravar config sob lock alheio"

    os.unlink(foreign_lock)


def test_grava_e_remove_proprio_lock_sem_contencao(tmp_path, monkeypatch):
    cfg_path = _isolar_config(tmp_path, monkeypatch, {"marcador": "gravado"})

    ok = cs_mod.config_service._save_config()

    assert ok is True
    assert cfg_path.exists(), "deve gravar o config quando nao ha contencao"
    assert not os.path.exists(str(cfg_path) + ".lock"), "deve remover o proprio lock"


def test_configure_shared_storage_falha_fechado_sob_lock(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "CONFIG_PATH", str(cfg_path))
    monkeypatch.setattr(cs_mod, "_CONFIG_LOCK_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(cs_mod, "_CONFIG_LOCK_SLEEP_SECONDS", 0.01)
    monkeypatch.setattr(cs_mod.config_service, "_config", {})

    foreign_lock = str(cfg_path) + ".lock"
    open(foreign_lock, "w").close()

    shared_root = str(tmp_path / "share")
    ok, msg = cs_mod.config_service.configure_shared_storage(shared_root)

    assert ok is False
    assert "lock" in msg.lower() or "novamente" in msg.lower()
    assert os.path.exists(foreign_lock), "NAO pode remover o lock alheio"

    os.unlink(foreign_lock)
