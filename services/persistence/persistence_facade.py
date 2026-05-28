# -*- coding: utf-8 -*-
"""
Persistence Facade (CSV Backend)

Facade que redireciona operacoes de "banco" para leitura/escrita em CSV,
mantendo assinaturas compatíveis com os repositorios atuais.
"""

from __future__ import annotations

import csv
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from services.core.config_service import config_service
from services.path_resolver import resolve_users_csv_path
from utils.csv_lock import CSVFileLock
from utils.csv_safety import sanitize_csv_value
from utils.logger import registrar_log
from utils.network_io import RetryPolicy, call_with_retry, open_with_retry, path_exists_with_retry

USER_HEADERS = [
    "id",
    "usuario",
    "senha_hash",
    "nivel_acesso",
    "status",
    "data_criacao",
    "ultimo_acesso",
    "tentativas_falhas",
    "bloqueado_ate",
    "preferencias",
]

HISTORY_HEADERS = [
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
]


class CsvUserRepository:
    """Facade CSV compatível com UserRepository (SQLite)."""

    is_csv_facade = True

    def __init__(self, csv_path: Optional[str] = None) -> None:
        resolved = csv_path or str(resolve_users_csv_path())
        self.csv_path = Path(resolved)
        self._ensure_csv()

    def _ensure_csv(self) -> None:
        policy = RetryPolicy.from_env()
        if path_exists_with_retry(self.csv_path, policy=policy):
            return

        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with CSVFileLock(self.csv_path):
                with open_with_retry(
                    self.csv_path, "w", encoding="utf-8", newline="", policy=policy
                ) as f:
                    writer = csv.writer(f, delimiter=",")
                    writer.writerow(USER_HEADERS)
        except Exception as exc:
            registrar_log(
                "CsvUserRepository",
                f"Erro ao criar CSV de usuarios: {exc}",
                "ERROR",
            )

    def _read_rows(self) -> List[Dict[str, str]]:
        policy = RetryPolicy.from_env()
        if not path_exists_with_retry(self.csv_path, policy=policy):
            return []

        try:
            with open_with_retry(
                self.csv_path, "r", encoding="utf-8", newline="", policy=policy
            ) as f:
                reader = csv.DictReader(f, delimiter=",")
                return [dict(row) for row in reader]
        except Exception as exc:
            registrar_log(
                "CsvUserRepository",
                f"Erro ao ler CSV de usuarios: {exc}",
                "ERROR",
            )
            return []

    def _write_rows(self, rows: List[Dict[str, str]]) -> bool:
        policy = RetryPolicy.from_env()
        try:
            with CSVFileLock(self.csv_path):
                with open_with_retry(
                    self.csv_path, "w", encoding="utf-8", newline="", policy=policy
                ) as f:
                    writer = csv.DictWriter(f, fieldnames=USER_HEADERS, delimiter=",")
                    writer.writeheader()
                    for row in rows:
                        writer.writerow({h: row.get(h, "") for h in USER_HEADERS})
            return True
        except Exception as exc:
            registrar_log(
                "CsvUserRepository",
                f"Erro ao salvar CSV de usuarios: {exc}",
                "ERROR",
            )
            return False

    def adicionar_usuario(self, usuario: str, senha_hash: str, nivel: str) -> bool:
        usuarios = self._read_rows()
        if any(u.get("usuario", "").lower() == usuario.lower() for u in usuarios):
            registrar_log(
                "CsvUserRepository",
                f"Usuario '{usuario}' já existe",
                "WARNING",
            )
            return False

        now_date = datetime.now().strftime("%Y-%m-%d")
        usuarios.append(
            {
                "id": uuid.uuid4().hex[:8],
                "usuario": sanitize_csv_value(usuario),
                "senha_hash": sanitize_csv_value(senha_hash),
                "nivel_acesso": sanitize_csv_value(nivel),
                "status": "ATIVO",
                "data_criacao": now_date,
                "ultimo_acesso": "",
                "tentativas_falhas": "0",
                "bloqueado_ate": "",
                "preferencias": "{}",
            }
        )

        if self._write_rows(usuarios):
            registrar_log(
                "CsvUserRepository",
                f"Usuario '{usuario}' adicionado",
                "INFO",
            )
            return True
        return False

    def autenticar(self, usuario: str, senha_hash: str) -> Optional[Dict]:
        usuarios = self._read_rows()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for row in usuarios:
            if row.get("usuario", "").lower() != usuario.lower():
                continue
            if row.get("senha_hash") != senha_hash:
                return None
            if row.get("status", "ATIVO").upper() != "ATIVO":
                return None

            row["ultimo_acesso"] = now_str
            self._write_rows(usuarios)

            return {
                "id": row.get("id"),
                "usuario": row.get("usuario"),
                "nivel_acesso": row.get("nivel_acesso"),
                "criado_em": row.get("data_criacao"),
                "ultimo_login": row.get("ultimo_acesso"),
            }

        return None

    def listar_usuarios(self) -> List[Dict]:
        usuarios = self._read_rows()
        ativos = [u for u in usuarios if u.get("status", "ATIVO").upper() == "ATIVO"]
        return [
            {
                "id": u.get("id"),
                "usuario": u.get("usuario"),
                "nivel_acesso": u.get("nivel_acesso"),
                "criado_em": u.get("data_criacao"),
                "ultimo_login": u.get("ultimo_acesso"),
            }
            for u in ativos
        ]

    def importar_de_csv(self, csv_path: str) -> int:
        policy = RetryPolicy.from_env()
        if not path_exists_with_retry(csv_path, policy=policy):
            return 0

        try:
            with open_with_retry(csv_path, "r", encoding="utf-8", newline="", policy=policy) as f:
                reader = csv.DictReader(f, delimiter=";")
                count = 0
                for row in reader:
                    usuario = row.get("usuario", "")
                    senha_hash = row.get("senha_hash") or row.get("senha") or ""
                    nivel = row.get("nivel_acesso") or row.get("nivel") or "USER"
                    if usuario and senha_hash:
                        if self.adicionar_usuario(usuario, senha_hash, nivel):
                            count += 1
                return count
        except Exception as exc:
            registrar_log(
                "CsvUserRepository",
                f"Erro ao importar usuarios do CSV: {exc}",
                "ERROR",
            )
            return 0

    def exportar_para_csv(self, csv_path: str) -> bool:
        usuarios = self._read_rows()
        policy = RetryPolicy.from_env()
        try:
            with open_with_retry(
                csv_path, "w", encoding="utf-8", newline="", policy=policy
            ) as f:
                writer = csv.DictWriter(f, fieldnames=USER_HEADERS, delimiter=";")
                writer.writeheader()
                for row in usuarios:
                    writer.writerow({h: row.get(h, "") for h in USER_HEADERS})
            return True
        except Exception as exc:
            registrar_log(
                "CsvUserRepository",
                f"Erro ao exportar usuarios para CSV: {exc}",
                "ERROR",
            )
            return False


class CsvHistoryRepository:
    """Facade CSV compatível com HistoryRepository (SQLite)."""

    is_csv_facade = True

    def __init__(self, csv_path: Optional[str] = None) -> None:
        paths = config_service.get_paths()
        resolved = csv_path or paths.get("gal_history_csv", "logs/historico_analises.csv")
        self.csv_path = Path(resolved)
        self._ensure_csv()

    def _ensure_csv(self) -> None:
        policy = RetryPolicy.from_env()
        if path_exists_with_retry(self.csv_path, policy=policy):
            return

        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with CSVFileLock(self.csv_path):
                with open_with_retry(
                    self.csv_path, "w", encoding="utf-8", newline="", policy=policy
                ) as f:
                    writer = csv.DictWriter(f, fieldnames=HISTORY_HEADERS, delimiter=";")
                    writer.writeheader()
        except Exception as exc:
            registrar_log(
                "CsvHistoryRepository",
                f"Erro ao criar CSV de historico: {exc}",
                "ERROR",
            )

    def adicionar_registro(self, dados: Dict[str, object]) -> int:
        self._ensure_csv()
        policy = RetryPolicy.from_env()

        payload = {k: sanitize_csv_value(v) for k, v in dados.items()}
        if "data_hora" not in payload:
            payload["data_hora"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with CSVFileLock(self.csv_path):
                with open_with_retry(
                    self.csv_path, "a", encoding="utf-8", newline="", policy=policy
                ) as f:
                    writer = csv.DictWriter(f, fieldnames=HISTORY_HEADERS, delimiter=";")
                    writer.writerow({h: payload.get(h, "") for h in HISTORY_HEADERS})
            return 1
        except Exception as exc:
            registrar_log(
                "CsvHistoryRepository",
                f"Erro ao adicionar registro no historico CSV: {exc}",
                "ERROR",
            )
            return 0

    def obter_ultimos(self, limit: int = 1000) -> pd.DataFrame:
        policy = RetryPolicy.from_env()
        if not path_exists_with_retry(self.csv_path, policy=policy):
            return pd.DataFrame()

        try:
            df = call_with_retry(
                lambda: pd.read_csv(self.csv_path, sep=";", encoding="utf-8"),
                op_name="read_csv",
                path=self.csv_path,
                policy=policy,
            )
            if "data_hora" in df.columns:
                df = df.sort_values(by="data_hora", ascending=False)
            return df.head(limit) if limit else df
        except Exception as exc:
            registrar_log(
                "CsvHistoryRepository",
                f"Erro ao ler historico CSV: {exc}",
                "ERROR",
            )
            return pd.DataFrame()


_user_repo: Optional[CsvUserRepository] = None
_history_repo: Optional[CsvHistoryRepository] = None


def get_user_repository() -> CsvUserRepository:
    """Retorna instancia singleton de CsvUserRepository."""
    global _user_repo
    if _user_repo is None:
        _user_repo = CsvUserRepository()
    return _user_repo


def get_history_repository() -> CsvHistoryRepository:
    """Retorna instancia singleton de CsvHistoryRepository."""
    global _history_repo
    if _history_repo is None:
        _history_repo = CsvHistoryRepository()
    return _history_repo
