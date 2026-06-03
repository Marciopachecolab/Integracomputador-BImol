"""Guardião T-044: scripts/ sem paths absolutos para Downloads/Integragal.

Após T-045 (Fase 4 Audit Refactoring), todos os scripts usam paths
relativos a $PSScriptRoot/Path(__file__)/%~dp0. Este guardião impede
regressão do path do *root do projeto* (a cópia antiga não-portável
'c:\\Users\\marci\\Downloads\\Integragal - Copia (3)').

ESCOPO DELIBERADO (DHP Q1 da Fase 4, aprovado opção A): o guardião vigia
apenas o padrão `Downloads/Integragal` (o endereço do projeto). NÃO usa o
padrão amplo `c:/Users/<user>/Downloads` porque ele bloquearia
indevidamente scripts dev legítimos que referenciam *dados externos*
fora do repo — caso de scripts/generate_phase0_baseline.py, que aponta
para fixtures .xlsx de laboratório em 'Downloads\\18 JULHO 2025\\'. Essas
fixtures não podem virar path relativo (vivem fora do repositório) e
ficaram registradas como pendência para rodada futura dedicada.

Referências:
- specs/audit_refactoring/spec.md US-13 (AC-13.2)
- specs/audit_refactoring/tasks.md T-044, T-045
"""
from __future__ import annotations
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Padrão proibido (regex case-insensitive): apenas o root do projeto.
# Ver docstring sobre por que o padrão amplo c:/Users/<user>/Downloads
# NÃO é usado (DHP Q1 Fase 4, opção A).
BANNED_PATTERNS = [
    re.compile(r"Downloads[\\\/]Integragal", re.IGNORECASE),
]

# Allowlist: scripts gerados externamente ou comentários históricos podem
# ser exceções pontuais (vazio por padrão; documentar se necessário)
ALLOWLIST: set[str] = set()

# Extensões a varrer
EXTENSIONS = {".py", ".ps1", ".cmd", ".bat"}


def test_scripts_have_no_hardcoded_downloads_paths():
    if not SCRIPTS_DIR.exists():
        return  # nada a verificar
    offenders = []
    for entry in SCRIPTS_DIR.rglob("*"):
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in EXTENSIONS:
            continue
        if str(entry) in ALLOWLIST:
            continue
        try:
            content = entry.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        for ln_idx, line in enumerate(content.splitlines(), start=1):
            for pat in BANNED_PATTERNS:
                if pat.search(line):
                    offenders.append(f"{entry}:{ln_idx}: {line.strip()[:120]}")
                    break
    assert not offenders, (
        "Paths absolutos hardcoded detectados em scripts/ "
        "(use Path(__file__) / $PSScriptRoot / %~dp0):\n" + "\n".join(offenders)
    )
