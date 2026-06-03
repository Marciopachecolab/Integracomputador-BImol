"""Guardião T-037 (Fase 3 Audit Refactoring) — AC-12.3.

Falha se qualquer "runtime area" regulada contiver arquivos de backup
abandonados (`.bak`, `.bak.*`, `.orig`, `.swp`, `~`). Esses artefatos
poluem zonas reguladas (`domain/`, `ui/`, `services/`, ...) e mascaram
o estado canônico do código.

Backups históricos legítimos vivem em `docs/obsoletos/refactor_attempts/`
(ver T-038/T-038b) e em `snapshots/` — ambos FORA da lista RUNTIME, logo
naturalmente ignorados por este scan.
"""
from pathlib import Path

# Zonas reguladas onde nenhum .bak pode reaparecer.
RUNTIME = [
    "domain",
    "application",
    "services",
    "ui",
    "exportacao",
    "autenticacao",
    "browser",
    "utils",
    "config",
    "scripts",
]

# Sufixos/padrões de backup proibidos em runtime.
BANNED_MARKERS = (".bak", ".orig", ".swp")

# Allowlist explícita (destinos canônicos de backups históricos).
# Mantida por completude; estes caminhos NÃO estão em RUNTIME, então o
# scan já não os alcança — documentado aqui para rastreabilidade.
ALLOWLIST_DIRS = (
    "docs/obsoletos/refactor_attempts",
    "snapshots",
)


def _is_banned(name: str) -> bool:
    if name.endswith("~"):
        return True
    return any(marker in name for marker in BANNED_MARKERS)


def test_no_bak_files_in_runtime():
    repo_root = Path(__file__).resolve().parent.parent
    offenders = []
    for rel in RUNTIME:
        base = repo_root / rel
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts:
                continue
            if _is_banned(path.name):
                offenders.append(str(path.relative_to(repo_root)))
    assert not offenders, (
        "Arquivos de backup (.bak/.orig/.swp/~) proibidos em runtime areas. "
        "Mova-os para docs/obsoletos/refactor_attempts/ (T-038):\n"
        + "\n".join(sorted(offenders))
    )
