"""Guardião T-AUD-023: login.py UI não vaza contador de tentativas.

DHP politica-senha-lockout (Fase 5) determina mensagem UI genérica
(OWASP A07). Este guardião falha se login.py contiver literais que
revelam: (a) número de tentativas, (b) que conta foi bloqueada,
(c) qualquer mensagem distinta entre senha errada e usuário inexistente.

Allowlist: comentários (linhas começando com #) e docstrings podem
mencionar 'tentativa' / 'restante' / 'excedido' para documentar a
ausência de exposição.
"""
from __future__ import annotations
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = REPO_ROOT / "autenticacao" / "login.py"

# Mensagens proibidas em strings de usuário (case-insensitive)
BANNED_PATTERNS = [
    re.compile(r"\b\d+\s+tentativa", re.IGNORECASE),
    re.compile(r"tentativa\(s?\)\s+restante", re.IGNORECASE),
    re.compile(r"tentativas?\s+restantes?", re.IGNORECASE),
    re.compile(r"m[áa]ximo\s+de\s+tentativas", re.IGNORECASE),
    re.compile(r"tentativas?\s+excedid", re.IGNORECASE),
    re.compile(r"acesso\s+bloqueado", re.IGNORECASE),
    re.compile(r"conta\s+bloqueada", re.IGNORECASE),
]


def test_login_ui_does_not_leak_attempt_count():
    assert TARGET.exists(), f"{TARGET} não existe"
    content = TARGET.read_text(encoding="utf-8-sig")
    offenders = []
    for ln_idx, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        # Allowlist: comentários e docstrings
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue
        for pat in BANNED_PATTERNS:
            if pat.search(line):
                offenders.append(f"{TARGET.name}:{ln_idx}: {line.strip()[:120]}")
                break
    assert not offenders, (
        "login.py vaza contador de tentativas (viola DHP "
        "politica-senha-lockout OWASP A07):\n" + "\n".join(offenders)
    )
