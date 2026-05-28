"""
Facade de migracao U2 para cadastros diversos.

Mantem compatibilidade durante a transicao:
- consumidores novos importam de ``ui.modules.cadastros_diversos``;
- implementacao ainda delega para ``services.cadastros_diversos``.
"""

from ui.modules.cadastros_ui import (
    CadastrosDiversosWindow,
    ExamFormDialog,
    RegistryExamEditor,
)

__all__ = [
    "CadastrosDiversosWindow",
    "ExamFormDialog",
    "RegistryExamEditor",
]
