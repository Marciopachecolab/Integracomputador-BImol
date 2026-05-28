"""Regras de escopo operacional de exames."""

from __future__ import annotations


class ExamForaDoEscopoError(ValueError):
    """Levantado quando um exame nao esta na lista de exames ativos do sistema."""

    def __init__(self, nome_exame: str) -> None:
        self.nome_exame = nome_exame
        super().__init__(
            f"Exame '{nome_exame}' nao esta nos exames ativos. "
            "Apenas 'VR1e2 Biomanguinhos 7500' e 'ZDC BioManguinhos' sao permitidos."
        )
