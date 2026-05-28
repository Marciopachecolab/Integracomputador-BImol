"""
Módulo de Cadastros Diversos para o IntegraGAL.
Este módulo fornece serviços de acesso a dados para:
- Exames (banco/exames_config.csv)
- Equipamentos (banco/equipamentos.csv)
- Placas (banco/placas.csv)
- Regras (banco/regras.csv)
"""

import csv
import os
from dataclasses import dataclass
from typing import Dict, List

from services.system_paths import BASE_DIR
from services.core.config_service import config_service
from utils.logger import registrar_log
from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, open_with_retry, path_exists_with_retry

@dataclass
class CsvConfig:
    path: str
    headers: List[str]
    description: str
    separator: str = ","

def get_csv_configs() -> Dict[str, CsvConfig]:
    from pathlib import Path
    try:
        paths_cfg = config_service.get_paths()
    except Exception:
        paths_cfg = {}

    exams_path = paths_cfg.get("exams_catalog_csv") or os.path.join(BASE_DIR, "banco_runtime", "exames_config.csv")
    banco_dir = Path(exams_path).parent

    return {
        "exames": CsvConfig(
            path=exams_path,
            headers=["exame", "modulo_analise", "tipo_placa", "numero_kit", "equipamento"],
            description="Catálogo de exames e módulos de análise."
        ),
        "equipamentos": CsvConfig(
            path=str(banco_dir / "equipamentos.csv"),
            headers=["nome", "modelo", "fabricante", "observacoes"],
            description="Cadastro de equipamentos disponíveis."
        ),
        "placas": CsvConfig(
            path=str(banco_dir / "placas.csv"),
            headers=["nome", "tipo", "num_pocos", "descricao"],
            description="Cadastro de tipos de placas."
        ),
        "regras": CsvConfig(
            path=str(banco_dir / "regras.csv"),
            headers=["nome_regra", "exame", "descricao", "parametros"],
            description="Cadastro de regras de interpretação/negócio."
        )
    }

def ensure_csv(cfg: CsvConfig) -> None:
    os.makedirs(os.path.dirname(cfg.path), exist_ok=True)
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(cfg.path, policy=policy):
        with CSVFileLock(cfg.path):
            with open_with_retry(cfg.path, "w", encoding="utf-8", newline="", policy=policy) as f:
                writer = csv.writer(f, delimiter=cfg.separator)
                writer.writerow(cfg.headers)
        registrar_log("CadastrosDiversos", f"Arquivo criado: {cfg.path}", "INFO")

def load_csv(cfg: CsvConfig) -> List[Dict[str, str]]:
    ensure_csv(cfg)
    rows: List[Dict[str, str]] = []
    try:
        policy = RetryPolicy.from_env()
        with open_with_retry(cfg.path, "r", encoding="utf-8", policy=policy) as f:
            reader = csv.DictReader(f, delimiter=cfg.separator)
            for row in reader:
                normalized = {h: row.get(h, "").strip() for h in cfg.headers}
                rows.append(normalized)
    except Exception as e:
        registrar_log("CadastrosDiversos", f"Erro ao ler CSV {cfg.path}: {e}", "ERROR")
        raise
    return rows

def save_csv(cfg: CsvConfig, rows: List[Dict[str, str]]) -> None:
    try:
        policy = RetryPolicy.from_env()
        with CSVFileLock(cfg.path):
            with open_with_retry(cfg.path, "w", encoding="utf-8", newline="", policy=policy) as f:
                writer = csv.DictWriter(f, fieldnames=cfg.headers, delimiter=cfg.separator)
                writer.writeheader()
                for r in rows:
                    writer.writerow({h: r.get(h, "") for h in cfg.headers})
        registrar_log("CadastrosDiversos", f"Arquivo salvo: {cfg.path}, {len(rows)} registros.", "INFO")
    except Exception as e:
        registrar_log("CadastrosDiversos", f"Erro ao salvar CSV {cfg.path}: {e}", "ERROR")
        raise
