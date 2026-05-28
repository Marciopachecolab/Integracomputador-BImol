# -*- coding: utf-8 -*-
"""Schema unificado do historico (CSV/DTO/compatibilidade)."""

from __future__ import annotations

HISTORY_SCHEMA_VERSION = "1.0.0"

# Contrato CSV critico (minimo) mantido em csv_contracts.py.
HISTORY_REQUIRED_HEADERS_MINIMAL: tuple[str, ...] = (
    "data_hora",
    "exame",
    "equipamento",
)

# Campos canonicos usados na escrita principal de historico.
HISTORY_CSV_FIELDNAMES: tuple[str, ...] = (
    "data_hora",
    "exame",
    "equipamento",
    "usuario",
    "num_placa",
    "status_corrida",
    "total_amostras",
    "total_detectados",
    "total_nao_detectados",
    "total_inconclusivos",
    "total_invalidos",
    "arquivo_corrida",
    "observacoes",
    "nome_corrida",
    "quem_fez_extracao",
    "quem_preparou_placa",
    "corrida_id",
    "amostra_codigo",
    "lote",
    "data_exame",
)

# Mapeamento legado -> canonico para leitura/compat.
HISTORY_LEGACY_ALIASES: dict[str, str] = {
    "data_hora_analise": "data_hora",
    "usuario_analise": "usuario",
    "bioquímico": "bioquimico",
}

# Campos de chave de dedupe contratual.
HISTORY_DEDUPE_FIELDS: tuple[str, str, str, str] = (
    "corrida_id",
    "amostra_codigo",
    "lote",
    "data_exame",
)
