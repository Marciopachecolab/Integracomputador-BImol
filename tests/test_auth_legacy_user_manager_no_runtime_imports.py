"""Guardiao T-AUD-004A (recriado em T-011, Fase 1 Audit Refactoring).

Garante que nenhuma area de runtime importe o modulo legado
`core.authentication.user_manager` (DEC-003: deprecacao controlada).

Fluxo ativo de autenticacao: autenticacao/auth_service.py +
autenticacao/login.py + matriz application/access_control.py.

AST scan que falha se qualquer modulo nos RUNTIME_ROOTS importar o
legado. Allowlist vazia por DEC-003.
"""

import ast
from pathlib import Path

RUNTIME_ROOTS = [
    "autenticacao",
    "application",
    "services",
    "ui",
    "interface",
    "exportacao",
    "browser",
    "scripts",
]
BANNED = {"core.authentication.user_manager"}
ALLOWLIST: set = set()  # vazia por DEC-003


def test_no_runtime_imports_of_legacy_user_manager():
    repo_root = Path(__file__).parent.parent
    offenders = []
    for root in RUNTIME_ROOTS:
        if not (repo_root / root).exists():
            continue
        for py in (repo_root / root).rglob("*.py"):
            if str(py) in ALLOWLIST:
                continue
            # utf-8-sig tolera BOM (U+FEFF) presente em modulos legados.
            tree = ast.parse(py.read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module in BANNED:
                    offenders.append(f"{py}:{node.lineno}")
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in BANNED:
                            offenders.append(f"{py}:{node.lineno}")
    assert not offenders, "Imports proibidos:\n" + "\n".join(offenders)
