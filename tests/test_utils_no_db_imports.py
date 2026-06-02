"""Guardiao T-067 (Fase 6): utils/ nao importa o pacote local db/.

Apos a migracao T-065/T-066, a fonte canonica de
salvar_historico_processamento e services.reports.history_report. O
pacote db/ permanece fisicamente presente (remocao e Fase 7 / DHP-13),
mas a camada utils/ NAO deve depender dele (cross-layer ban): utils sao
helpers genericos e nao devem acoplar persistencia legada.

Verifica via AST que nenhum arquivo em utils/*.py contem
`from db...` nem `import db`. Allowlist explicita: vazia.

Nota: o prefixo exato `db` nao afeta bibliotecas como `dbm` ou nomes
como `database` (so casa `db` ou `db.<algo>`).

Referencias:
- specs/audit_refactoring/spec.md US-18
- CLAUDE.md §6 (camadas) / §15.2 (DHP-13)
"""
from __future__ import annotations

import ast
from pathlib import Path

BANNED_MODULE_PREFIX = "db"
ALLOWLIST: set[str] = set()

REPO_ROOT = Path(__file__).resolve().parent.parent
UTILS_DIR = REPO_ROOT / "utils"


def _scan_file(py_path: Path) -> list[str]:
    """Retorna lista de violacoes `arquivo:linha: import`."""
    offenders: list[str] = []
    try:
        tree = ast.parse(py_path.read_text(encoding="utf-8-sig"))
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == BANNED_MODULE_PREFIX or mod.startswith(f"{BANNED_MODULE_PREFIX}."):
                offenders.append(f"{py_path}:{node.lineno}: from {mod}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == BANNED_MODULE_PREFIX or alias.name.startswith(
                    f"{BANNED_MODULE_PREFIX}."
                ):
                    offenders.append(f"{py_path}:{node.lineno}: import {alias.name}")
    return offenders


def test_utils_nao_importa_pacote_db():
    assert UTILS_DIR.is_dir(), f"utils/ nao encontrado em {UTILS_DIR}"
    offenders: list[str] = []
    for py in UTILS_DIR.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        if str(py) in ALLOWLIST:
            continue
        offenders.extend(_scan_file(py))
    assert not offenders, (
        "Imports proibidos do pacote local 'db' em utils/ (cross-layer ban, "
        "T-067 — use services.reports.history_report):\n" + "\n".join(offenders)
    )
