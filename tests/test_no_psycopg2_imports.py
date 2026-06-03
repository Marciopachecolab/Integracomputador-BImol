"""Guardião T-030 (Fase 3 Audit Refactoring) — AC-10.1, AC-10.3.

CLAUDE.md §7 proíbe Postgres dedicado ("provider nao implementado").
`requirements.txt` listava `psycopg2-binary` como dependência "opcional";
foi removido (AC-10.1). Este guardião impede a reintrodução de qualquer
`import psycopg2` / `from psycopg2 ...` em runtime areas (AC-10.3).

Allowlist temporária (legado em deprecação controlada — Fase 7):
  - `db/`  — `db_utils.py` legado (T-AUD-016 / T-085).
  - `sql/` — pasta órfã de DDL PostgreSQL (T-084).
  - `docs/obsoletos/` — material arquivado.
Esses caminhos NÃO estão na lista RUNTIME_ROOTS, logo já ficam fora do
scan; mantidos aqui apenas para rastreabilidade. A allowlist deve ser
removida quando a Fase 7 arquivar `db/` e `sql/`.
"""
import ast
from pathlib import Path

# Zonas runtime varridas pelo guardião.
RUNTIME_ROOTS = [
    "application",
    "services",
    "ui",
    "interface",
    "exportacao",
    "autenticacao",
    "browser",
    "domain",
    "utils",
    "scripts",
]

BANNED_TOP = "psycopg2"

# Caminhos legados explicitamente tolerados (Fase 7). Relativos ao repo.
ALLOWLIST_PREFIXES = (
    "db/",
    "sql/",
    "docs/obsoletos/",
)


def _is_allowlisted(rel_posix: str) -> bool:
    return any(rel_posix.startswith(prefix) for prefix in ALLOWLIST_PREFIXES)


def _scan_targets(repo_root: Path):
    # Roots runtime declarados.
    for rel in RUNTIME_ROOTS:
        base = repo_root / rel
        if not base.exists():
            continue
        for py in base.rglob("*.py"):
            if "__pycache__" in py.parts:
                continue
            yield py
    # Arquivos .py soltos na raiz do repo.
    for py in repo_root.glob("*.py"):
        yield py


def test_no_psycopg2_imports_in_runtime():
    repo_root = Path(__file__).resolve().parent.parent
    offenders = []
    for py in _scan_targets(repo_root):
        rel_posix = py.relative_to(repo_root).as_posix()
        if _is_allowlisted(rel_posix):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] == BANNED_TOP:
                        offenders.append(f"{rel_posix}:{node.lineno}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] == BANNED_TOP:
                    offenders.append(f"{rel_posix}:{node.lineno}: from {node.module}")
    assert not offenders, (
        "Import de psycopg2 proibido em runtime (CLAUDE.md §7 — sem Postgres):\n"
        + "\n".join(sorted(offenders))
    )
