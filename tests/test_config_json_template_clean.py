# -*- coding: utf-8 -*-
"""Guardiao: o config.json VERSIONADO e template-clean (FINDING-001 / DEC-001).

DEC-001: o config.json versionado e template/local runtime. Ambientes produtivos
exigem configuracao local validada; o arquivo versionado NAO deve conter caminhos
absolutos reais em `data_root`/`allowed_roots`.

A verificacao e feita sobre o blob COMMITADO (`git show HEAD:config.json`), nao
sobre o arquivo em disco — assim o teste passa em CI e nao quebra o runtime local
do desenvolvedor, que legitimamente preenche caminhos reais no arquivo local
(esses nunca devem ser commitados — ver GIT-002).
"""

import json
import os
import subprocess

import pytest


def _committed_config():
    try:
        proc = subprocess.run(
            ["git", "show", "HEAD:config.json"],
            capture_output=True, text=True, encoding="utf-8",
        )
    except (FileNotFoundError, OSError):
        pytest.skip("git indisponivel; guardiao de template nao aplicavel")
    if proc.returncode != 0 or not proc.stdout.strip():
        pytest.skip("config.json versionado nao acessivel via git HEAD")
    return json.loads(proc.stdout)


def test_data_root_versionado_nao_e_absoluto():
    cfg = _committed_config()
    data_root = cfg.get("data_root", "")
    assert not (isinstance(data_root, str) and data_root and os.path.isabs(data_root)), (
        "config.json versionado nao deve conter caminho absoluto real em data_root (DEC-001)"
    )


def test_allowed_roots_versionado_sem_caminho_absoluto():
    cfg = _committed_config()
    allowed = cfg.get("allowed_roots", [])
    abs_entries = [p for p in allowed if isinstance(p, str) and os.path.isabs(p)]
    assert not abs_entries, (
        "config.json versionado nao deve conter caminhos absolutos em allowed_roots (DEC-001)"
    )
