"""Guardião T-043: pasta sql/ órfã sem callers runtime.

Ver auditoria sql/ (16 auditorias por pasta, 2026-05-31) — sql/ é camada
paralela órfã (0 consumidores em produção). A persistência canônica usa
services/* (ExamRunsSQLiteRepository e afins). Bloqueio de import-ban
impede reativação do pacote local sql/ até DHP-13 decidir destino final.

Nota: este guardião verifica apenas o pacote local `sql` (ex.: `from sql
import X`, `import sql.algo`). Bibliotecas como `sqlite3`/`sqlalchemy`
não são afetadas (prefixo exato `sql`).

Referências:
- specs/audit_refactoring/spec.md US-8 (AC-8.3)
- docs/obsoletos/inventario_de_lixo.md
- CLAUDE.md §15.2 (DHP-13 sugerida)
"""
from __future__ import annotations
import ast
from pathlib import Path

RUNTIME_ROOTS = [
    "application", "autenticacao", "browser", "config", "core",
    "domain", "exportacao", "main.py", "models.py", "services",
    "ui", "utils",
]
BANNED_MODULE_PREFIX = "sql"
# Allowlist: auto-importação interna em sql/ é OK (a pasta importa si)
# tests/, snapshots/, docs/, _rollback_*, __pycache__ ficam fora do scan
ALLOWLIST: set[str] = set()

REPO_ROOT = Path(__file__).resolve().parent.parent


def _scan_file(py_path: Path) -> list[str]:
    """Retorna lista de violações `arquivo:linha: import`."""
    offenders = []
    try:
        tree = ast.parse(py_path.read_text(encoding="utf-8-sig"))
    except SyntaxError:
        # arquivos com sintaxe quebrada — ignorar (não impactam imports vivos)
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == BANNED_MODULE_PREFIX or mod.startswith(f"{BANNED_MODULE_PREFIX}."):
                offenders.append(f"{py_path}:{node.lineno}: from {mod}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == BANNED_MODULE_PREFIX or alias.name.startswith(f"{BANNED_MODULE_PREFIX}."):
                    offenders.append(f"{py_path}:{node.lineno}: import {alias.name}")
    return offenders


def test_no_runtime_imports_of_sql_package():
    offenders = []
    for entry in RUNTIME_ROOTS:
        target = REPO_ROOT / entry
        if not target.exists():
            continue
        if target.is_file() and target.suffix == ".py":
            offenders.extend(_scan_file(target))
        elif target.is_dir():
            for py in target.rglob("*.py"):
                if "__pycache__" in py.parts:
                    continue
                if str(py) in ALLOWLIST:
                    continue
                offenders.extend(_scan_file(py))
    assert not offenders, (
        f"Imports proibidos do pacote local orfão 'sql/' em runtime "
        f"(DHP-13 sugerida em CLAUDE.md §15.2):\n" + "\n".join(offenders)
    )
