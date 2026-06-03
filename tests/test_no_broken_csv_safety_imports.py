# -*- coding: utf-8 -*-
"""
Guardiao (AC-1.3 / Audit Refactoring T-003).

Garante que nenhum import de `utils.csv_safety` em areas de runtime referencie
um simbolo inexistente. Protege contra a regressao em que `utils/csv_safety.py`
foi deletado do working tree quebrando 10 callers em runtime (ModuleNotFoundError)
ou contra remocao parcial de funcoes exportadas (ImportError).

Estrategia: scan AST das areas de runtime; para cada
`from utils.csv_safety import X`, verifica que `X` e resolvivel no modulo real.
"""

import ast
import importlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Areas de runtime que consomem utils.csv_safety (CLAUDE.md §4).
RUNTIME_ROOTS = [
    "autenticacao",
    "application",
    "services",
    "exportacao",
    "ui",
    "scripts",
    "db",
    "utils",
]

TARGET_MODULE = "utils.csv_safety"


def _disponiveis_no_modulo() -> set[str]:
    """Nomes publicos efetivamente exportados por utils.csv_safety."""
    mod = importlib.import_module(TARGET_MODULE)
    return {nome for nome in dir(mod) if not nome.startswith("__")}


def _iter_py_files():
    for root in RUNTIME_ROOTS:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for py in base.rglob("*.py"):
            if ".bak" in py.name:
                continue
            yield py


def test_csv_safety_importavel():
    """O modulo restaurado deve importar sem erro."""
    mod = importlib.import_module(TARGET_MODULE)
    assert hasattr(mod, "sanitize_csv_value"), (
        "utils.csv_safety deve expor sanitize_csv_value (CWE-1236)."
    )


def test_no_broken_csv_safety_imports():
    """Todo `from utils.csv_safety import X` em runtime deve resolver X."""
    disponiveis = _disponiveis_no_modulo()
    offenders = []

    for py in _iter_py_files():
        try:
            # utf-8-sig tolera BOM (U+FEFF) presente em varios modulos legados.
            tree = ast.parse(py.read_text(encoding="utf-8-sig"))
        except (SyntaxError, UnicodeDecodeError) as exc:
            offenders.append(f"{py}: falha ao parsear ({exc})")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == TARGET_MODULE:
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    if alias.name not in disponiveis:
                        offenders.append(
                            f"{py}:{node.lineno}: simbolo inexistente "
                            f"'{alias.name}' em {TARGET_MODULE} "
                            f"(disponiveis: {sorted(disponiveis)})"
                        )

    assert not offenders, (
        "Imports quebrados de utils.csv_safety em runtime:\n"
        + "\n".join(offenders)
    )
