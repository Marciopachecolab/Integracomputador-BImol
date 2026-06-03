"""Guardiao AGENTS.md == CLAUDE.md (T-012, Fase 1 Audit Refactoring).

Materializa o MUST de constitution secao 1 / CLAUDE.md: AGENTS.md e
CLAUDE.md devem permanecer identicos byte-a-byte. Qualquer alteracao
em um exige a mesma alteracao no outro.

Falha do teste em CI bloqueia merge (AC-16.2).
"""

import hashlib
from pathlib import Path


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_agents_claude_md_identical():
    root = Path(__file__).parent.parent
    a = root / "AGENTS.md"
    c = root / "CLAUDE.md"
    assert a.exists() and c.exists(), "AGENTS.md ou CLAUDE.md ausente"
    assert _sha(a) == _sha(c), (
        f"sha mismatch: AGENTS={_sha(a)[:8]} CLAUDE={_sha(c)[:8]}"
    )
