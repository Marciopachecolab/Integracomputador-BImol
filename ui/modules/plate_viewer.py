"""
Facade de migracao U2 para o visualizador de placa.

Mantem compatibilidade durante a transicao:
- consumidores novos importam de ``ui.modules.plate_viewer``;
- implementacao ainda delega para ``services.plate_viewer``.
"""

from ui.components.plate_viewer import *  # noqa: F401,F403

