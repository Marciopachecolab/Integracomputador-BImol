# -*- coding: utf-8 -*-
"""Guardiao da mensagem de ExamForaDoEscopoError (FINDING-002).

O escopo operacional e definido dinamicamente por `active_exams` (CA-09/CA-10,
design.md 3.6). A mensagem de erro nao pode mais afirmar que apenas
'VR1e2 Biomanguinhos 7500' e 'ZDC BioManguinhos' sao permitidos, pois isso
contradiz o escopo dinamico quando outros exames estao habilitados.
"""

from domain.exam_scope import ExamForaDoEscopoError


def test_mensagem_cita_active_exams():
    msg = str(ExamForaDoEscopoError("Exame Novo Qualquer"))
    assert "active_exams" in msg


def test_mensagem_nao_fixa_lista_vr1e2_zdc():
    msg = str(ExamForaDoEscopoError("Exame Novo Qualquer"))
    # Nao deve afirmar que "apenas" os dois exames canonicos sao permitidos.
    assert "Apenas 'VR1e2 Biomanguinhos 7500' e 'ZDC BioManguinhos'" not in msg


def test_mensagem_inclui_nome_do_exame():
    msg = str(ExamForaDoEscopoError("Exame Novo Qualquer"))
    assert "Exame Novo Qualquer" in msg
