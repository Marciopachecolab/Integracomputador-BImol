from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class CsvContract:
    name: str
    delimiter: str
    encoding: str
    required_headers: tuple[str, ...] = ()
    schema_version: str = "1"


CSV_CONTRACTS: Dict[str, CsvContract] = {
    "usuarios.csv": CsvContract(
        name="usuarios.csv",
        delimiter=",",
        encoding="utf-8",
        required_headers=("usuario", "senha_hash"),
        schema_version="1",
    ),
    "historico_analises.csv": CsvContract(
        name="historico_analises.csv",
        delimiter=";",
        encoding="utf-8",
        required_headers=("data_hora", "exame", "equipamento"),
        schema_version="1",
    ),
    "historico_processos.csv": CsvContract(
        name="historico_processos.csv",
        delimiter=";",
        encoding="utf-8",
        required_headers=("data_hora", "analista", "exame", "status"),
        schema_version="1",
    ),
    "relatorio.csv": CsvContract(
        name="relatorio.csv",
        delimiter=";",
        encoding="utf-8",
        required_headers=("run_id", "codigo_amostra", "status_final"),
        schema_version="1",
    ),
    "gal_upload_history.csv": CsvContract(
        name="gal_upload_history.csv",
        delimiter=";",
        encoding="utf-8",
        required_headers=(
            "codigoAmostra",
            "registroInterno",
            "kit",
            "usuario",
            "timestamp",
        ),
        schema_version="1",
    ),
    "total_importados_gal.csv": CsvContract(
        name="total_importados_gal.csv",
        delimiter=";",
        encoding="utf-8",
        required_headers=(
            "codigoAmostra",
            "registroInterno",
            "kit",
            "usuario",
            "timestamp",
        ),
        schema_version="1",
    ),
    "gal_transacoes_sucesso.csv": CsvContract(
        name="gal_transacoes_sucesso.csv",
        delimiter=";",
        encoding="utf-8",
        required_headers=(
            "run_id",
            "codigo_amostra",
            "transaction_id",
            "ts_sucesso",
            "status",
        ),
        schema_version="1",
    ),
    "gal_transacoes.csv": CsvContract(
        name="gal_transacoes.csv",
        delimiter=";",
        encoding="utf-8",
        required_headers=(
            "idempotencia_chave",
            "run_id",
            "codigo_amostra",
            "kit",
            "lote_kit",
            "data_exame",
            "status",
            "transaction_id",
            "ts_evento",
            "erro",
            "detalhes",
        ),
        schema_version="1",
    ),
    "sistema.log": CsvContract(
        name="sistema.log",
        delimiter=";",
        encoding="utf-8",
        required_headers=(),
        schema_version="1",
    ),
    "corridas_<slug_exame>.csv": CsvContract(
        name="corridas_<slug_exame>.csv",
        delimiter=",",
        encoding="utf-8",
        required_headers=(
            "corrida_id",
            "exame_slug",
            "equipamento_id",
            "equipamento_modelo",
            "data_exame",
            "hora_exame",
            "lote",
            "amostra_codigo",
            "pocos",
            "resultado_geral",
            "status_placa",
        ),
        schema_version="1",
    ),
    "query_latency.csv": CsvContract(
        name="query_latency.csv",
        delimiter=";",
        encoding="utf-8",
        required_headers=(
            "timestamp",
            "operation",
            "backend",
            "duration_ms",
            "result_count",
            "meta",
        ),
        schema_version="1",
    ),
}


def _normalize_contract_name(path_or_name: str | Path) -> str:
    raw = Path(str(path_or_name)).name.strip().lower()
    return raw


def get_csv_contract(path_or_name: str | Path) -> Optional[CsvContract]:
    """Return the CSV contract for a known file name, or None."""
    normalized = _normalize_contract_name(path_or_name)
    if normalized.startswith("corridas_") and normalized.endswith(".csv"):
        return CSV_CONTRACTS["corridas_<slug_exame>.csv"]
    return CSV_CONTRACTS.get(normalized)
