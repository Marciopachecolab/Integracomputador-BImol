"""
Interface grafica - IntegaGal.

Este pacote usa exportacao lazy para evitar importar dependencias opcionais
(ex.: reportlab) durante navegacao em telas que nao usam PDF.
"""

from __future__ import annotations

from importlib import import_module
from typing import Dict, Tuple

_EXPORT_MAP: Dict[str, Tuple[str, str]] = {
    "Dashboard": (".dashboard", "Dashboard"),
    "VisualizadorExame": (".visualizador_exame", "VisualizadorExame"),
    "criar_dados_exame_exemplo": (".visualizador_exame", "criar_dados_exame_exemplo"),
    "GraficosQualidade": (".graficos_qualidade", "GraficosQualidade"),
    "HistoricoAnalises": (".historico_analises", "HistoricoAnalises"),
    "ExportadorRelatorios": (".exportacao_relatorios", "ExportadorRelatorios"),
    "exportar_pdf": (".exportacao_relatorios", "exportar_pdf"),
    "exportar_excel": (".exportacao_relatorios", "exportar_excel"),
    "exportar_csv": (".exportacao_relatorios", "exportar_csv"),
    "GerenciadorAlertas": (".sistema_alertas", "GerenciadorAlertas"),
    "CentroNotificacoes": (".sistema_alertas", "CentroNotificacoes"),
    "Alerta": (".sistema_alertas", "Alerta"),
    "TipoAlerta": (".sistema_alertas", "TipoAlerta"),
    "CategoriaAlerta": (".sistema_alertas", "CategoriaAlerta"),
    "gerar_alertas_exemplo": (".sistema_alertas", "gerar_alertas_exemplo"),
}

__all__ = list(_EXPORT_MAP.keys())


def __getattr__(name: str):
    target = _EXPORT_MAP.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
