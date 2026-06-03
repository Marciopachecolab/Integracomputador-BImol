# -*- coding: utf-8 -*-
"""T-063 (Fase 6): cobertura de safe_operation(propagate_critical=...).

Garante o contrato fail-closed do decorator:
- default (propagate_critical=False) captura excecao e retorna fallback;
- propagate_critical=True re-levanta apos log;
- sem excecao, executa normalmente em ambos os modos.

show_error=False em todos os cenarios para manter o teste headless
(sem dialog tkinter; evita dependencia de display — ver T-AUD-021).
"""

from __future__ import annotations

import pytest

from utils.error_handler import safe_operation


def test_default_captura_e_retorna_fallback():
    """Modo fail-open (default): excecao capturada, retorna fallback_value."""

    @safe_operation(fallback_value="FALLBACK", show_error=False)
    def explode():
        raise ValueError("boom")

    assert explode() == "FALLBACK"


def test_propagate_critical_re_levanta():
    """Modo fail-closed: excecao re-levantada apos log (nao retorna fallback)."""

    @safe_operation(fallback_value="FALLBACK", show_error=False, propagate_critical=True)
    def explode():
        raise ValueError("boom critico")

    with pytest.raises(ValueError, match="boom critico"):
        explode()


def test_sem_excecao_executa_normalmente_ambos_modos():
    """Sem excecao, ambos os modos retornam o valor real da funcao."""

    @safe_operation(fallback_value="FALLBACK", show_error=False)
    def ok_open():
        return "OK"

    @safe_operation(fallback_value="FALLBACK", show_error=False, propagate_critical=True)
    def ok_closed():
        return "OK"

    assert ok_open() == "OK"
    assert ok_closed() == "OK"
