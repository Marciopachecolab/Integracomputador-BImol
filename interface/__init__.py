"""
Camada de compatibilidade para o pacote legacy `interface`.

Reexporta as classes e funcoes atualmente localizadas em `ui.modules`.
"""

from ui.modules import (
    Dashboard,
    VisualizadorExame,
    GraficosQualidade,
    ExportadorRelatorios,
    HistoricoAnalises,
    GerenciadorAlertas,
    CentroNotificacoes,
    Alerta,
    TipoAlerta,
    CategoriaAlerta,
    gerar_alertas_exemplo,
    exportar_pdf,
    exportar_excel,
    exportar_csv,
    criar_dados_exame_exemplo,
)

__all__ = [
    "Dashboard",
    "VisualizadorExame",
    "GraficosQualidade",
    "ExportadorRelatorios",
    "HistoricoAnalises",
    "GerenciadorAlertas",
    "CentroNotificacoes",
    "Alerta",
    "TipoAlerta",
    "CategoriaAlerta",
    "gerar_alertas_exemplo",
    "exportar_pdf",
    "exportar_excel",
    "exportar_csv",
    "criar_dados_exame_exemplo",
]
