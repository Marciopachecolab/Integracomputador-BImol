# -*- coding: utf-8 -*-
"""Caminhos centralizados do sistema IntegRAGal."""

from pathlib import Path


# Diretório raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Diretórios principais
BANCO_DIR = BASE_DIR / "banco_runtime"
LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
CONFIG_DIR = BASE_DIR / "config"
TESTS_DIR = BASE_DIR / "tests"

# Arquivos importantes
HISTORICO_ANALISES_CSV = REPORTS_DIR / "historico_analises.csv"
USUARIOS_CSV = BANCO_DIR / "usuarios.csv"
# Credenciais legadas: alias para usuarios.csv
CREDENCIAIS_CSV = USUARIOS_CSV
PLACAS_CSV = BANCO_DIR / "placas.csv"
EQUIPAMENTOS_CSV = BANCO_DIR / "equipamentos.csv"

# Criar diretórios se não existirem
for directory in [BANCO_DIR, LOGS_DIR, REPORTS_DIR, CONFIG_DIR, TESTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
