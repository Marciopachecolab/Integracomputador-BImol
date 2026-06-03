"""Guardiao T-AUD-008 (recriado em T-010, Fase 1 Audit Refactoring).

Garante que a camada `domain/` permaneca pura: sem dependencias de UI,
Selenium, pandas ou pacotes pesados de infraestrutura (CLAUDE.md secao 6).

AST scan que falha se qualquer modulo em `domain/` importar um pacote
proibido. Allowlist vazia por contrato canonico (T-AUD-001/T-AUD-008).
"""

import ast
from pathlib import Path

BANNED_TOP = {
    "pandas",
    "selenium",
    "tkinter",
    "customtkinter",
    "seleniumrequests",
    "openpyxl",
    "requests",
    "PIL",
    "matplotlib",
}


def test_domain_layer_only_uses_stdlib_and_config():
    domain_dir = Path(__file__).parent.parent / "domain"
    offenders = []
    for py in domain_dir.rglob("*.py"):
        if ".bak" in py.name:
            continue
        # utf-8-sig tolera BOM (U+FEFF) presente em alguns modulos legados,
        # para que o scan de imports nao quebre antes de cumprir seu papel.
        tree = ast.parse(py.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top in BANNED_TOP:
                        offenders.append(f"{py}:{node.lineno}: {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                if top in BANNED_TOP:
                    offenders.append(f"{py}:{node.lineno}: from {node.module}")
    assert not offenders, "Imports proibidos em domain/:\n" + "\n".join(offenders)
