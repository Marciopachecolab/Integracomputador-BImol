# -*- coding: utf-8 -*-
"""T-064 (Fase 6): config.settings salvar/_criar_backup propagam falha critica.

Antes da Fase 6, salvar() e _criar_backup() usavam
@safe_operation(fallback_value=True): qualquer excecao era engolida e a
funcao retornava True, reportando SUCESSO falso para uma persistencia que
falhou. Estes guardioes garantem o novo contrato fail-closed
(propagate_critical=True): falha real propaga, nao retorna True silencioso.

Headless: nenhum dialog tkinter e disparado (show_error herdado, mas a
excecao propaga antes de qualquer interacao de UI critica).
"""

from __future__ import annotations

import pytest

from config.settings import ConfigurationManager


def test_salvar_propaga_falha_de_escrita(monkeypatch):
    """Se a escrita no config service falha, salvar() propaga (nao retorna True)."""
    cfg = ConfigurationManager()

    # Garante que passa pela validacao e chega na escrita.
    monkeypatch.setattr(cfg, "_validar_configuracao", lambda _c: True)

    def _boom(_config):
        raise OSError("disco cheio simulado")

    monkeypatch.setattr(cfg, "_aplicar_no_config_service", _boom)

    with pytest.raises(OSError, match="disco cheio simulado"):
        cfg.salvar(fazer_backup=False)


def test_criar_backup_propaga_falha_de_copia(monkeypatch, tmp_path):
    """Se a copia do backup falha, _criar_backup() propaga (nao retorna True)."""
    cfg = ConfigurationManager()

    # Aponta para um config.json existente para passar do guard de existencia.
    fake_config = tmp_path / "config.json"
    fake_config.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cfg, "CONFIG_JSON_PATH", fake_config)
    monkeypatch.setattr(cfg, "BACKUP_DIR", tmp_path / "backups")

    import config.settings as settings_mod

    def _boom(_src, _dst):
        raise OSError("falha de copia simulada")

    monkeypatch.setattr(settings_mod.shutil, "copy2", _boom)

    with pytest.raises(OSError, match="falha de copia simulada"):
        cfg._criar_backup()
