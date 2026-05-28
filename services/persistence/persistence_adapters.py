
# -*- coding: utf-8 -*-
"""
Adapters concretos para os contratos de persistencia.

Mapeia contratos (DTOs/Protocols) para repositorios existentes em CSV e SQLite.
"""

from __future__ import annotations

import csv
import heapq
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from itertools import count
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import pandas as pd

from domain.persistence_contracts import (
    ConflictError,
    ConcurrencyError,
    ExamConfigDTO,
    ExamConfigRepository,
    EquipmentDTO,
    EquipmentRepository,
    HistoryQueryDTO,
    HistoryRecordDTO,
    HistoryRepository,
    NotFoundError,
    PersistenceProvider,
    PersistenceUnitOfWork,
    PlateDTO,
    PlateRepository,
    RuleDTO,
    RuleRepository,
    UserAccessLevel,
    UserCreateDTO,
    UserDTO,
    UserRepository,
    UserStatus,
    UserUpdateDTO,
    ValidationError,
)
from services.core.config_service import config_service
from services.persistence.csv_io import write_csv_atomic
from services.dedupe_keys import DEDUPE_FIELDS, build_dedupe_key
from services.path_resolver import resolve_banco_dir, resolve_users_csv_path
from services.persistence.sqlite_repository import HistoryRepository as SQLiteHistoryRepository
from services.persistence.sqlite_repository import UserRepository as SQLiteUserRepository
from utils.csv_lock import CSVFileLock
from utils.csv_safety import sanitize_csv_value
from utils.logger import registrar_log
from utils.network_io import RetryPolicy, call_with_retry, open_with_retry, path_exists_with_retry


def _normalize_key(value: str) -> str:
    """Normaliza chaves para comparacao case-insensitive."""
    return str(value or "").strip().lower()


def _safe_int(value: object, default: int = 0) -> int:
    """Converte para int com fallback seguro."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_json_load(value: str) -> Dict[str, str]:
    """Converte string JSON em dict, com fallback seguro."""
    try:
        if not value:
            return {}
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _now_iso() -> str:
    """Retorna timestamp ISO local."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_query_datetime(
    value: Optional[str],
    *,
    end_of_day: bool = False,
) -> Optional[datetime]:
    """Converte filtro textual de data/hora para datetime."""
    raw = str(value or "").strip()
    if not raw:
        return None

    formats = (
        ("%Y-%m-%d %H:%M:%S", False),
        ("%Y-%m-%d", True),
        ("%d/%m/%Y %H:%M:%S", False),
        ("%d/%m/%Y", True),
    )
    for fmt, date_only in formats:
        try:
            parsed = datetime.strptime(raw, fmt)
            if date_only and end_of_day:
                return parsed.replace(hour=23, minute=59, second=59)
            return parsed
        except ValueError:
            continue

    raise ValidationError(f"Filtro de data invalido: '{raw}'")


def _coerce_history_datetime(value: object) -> Optional[datetime]:
    """Normaliza datas de historico vindas de CSV/SQLite."""
    raw = str(value or "").strip()
    if not raw:
        return None
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _apply_history_query(df: pd.DataFrame, query: HistoryQueryDTO) -> pd.DataFrame:
    """Aplica filtros/paginacao no DataFrame de historico."""
    filtered = df.copy()
    if filtered.empty:
        return filtered

    if query.exame and "exame" in filtered.columns:
        exame = str(query.exame).strip().lower()
        filtered = filtered[filtered["exame"].astype(str).str.strip().str.lower() == exame]

    if query.usuario:
        user_col = "usuario" if "usuario" in filtered.columns else "usuario_analise"
        if user_col in filtered.columns:
            usuario = str(query.usuario).strip().lower()
            filtered = filtered[
                filtered[user_col].astype(str).str.strip().str.lower() == usuario
            ]

    if query.status_corrida and "status_corrida" in filtered.columns:
        status = str(query.status_corrida).strip().lower()
        filtered = filtered[
            filtered["status_corrida"].astype(str).str.strip().str.lower() == status
        ]

    data_col = "data_hora" if "data_hora" in filtered.columns else "data_hora_analise"
    if data_col in filtered.columns:
        start = _parse_query_datetime(query.data_inicio, end_of_day=False)
        end = _parse_query_datetime(query.data_fim, end_of_day=True)

        parsed_series = filtered[data_col].map(_coerce_history_datetime)
        if start is not None:
            filtered = filtered[parsed_series >= start]
            parsed_series = parsed_series.loc[filtered.index]
        if end is not None:
            filtered = filtered[parsed_series <= end]
            parsed_series = parsed_series.loc[filtered.index]
        if not filtered.empty:
            filtered = filtered.assign(__sort_key=parsed_series)
            filtered = filtered.sort_values("__sort_key", ascending=False, na_position="last")
            filtered = filtered.drop(columns=["__sort_key"])

    offset = max(int(query.offset or 0), 0)
    if offset:
        filtered = filtered.iloc[offset:]

    if int(query.limit or 0) > 0:
        filtered = filtered.iloc[: int(query.limit)]

    return filtered


def _row_matches_history_query(
    row: Dict[str, object],
    query: HistoryQueryDTO,
    *,
    start: Optional[datetime],
    end: Optional[datetime],
) -> bool:
    """Valida se um registro CSV atende aos filtros do HistoryQueryDTO."""
    exame = str(query.exame or "").strip().lower()
    if exame and str(row.get("exame", "")).strip().lower() != exame:
        return False

    usuario = str(query.usuario or "").strip().lower()
    if usuario:
        row_user = str(
            row.get("usuario")
            or row.get("usuario_analise")
            or ""
        ).strip().lower()
        if row_user != usuario:
            return False

    status = str(query.status_corrida or "").strip().lower()
    if status and str(row.get("status_corrida", "")).strip().lower() != status:
        return False

    if start is not None or end is not None:
        dt = _coerce_history_datetime(row.get("data_hora") or row.get("data_hora_analise"))
        if dt is None:
            return False
        if start is not None and dt < start:
            return False
        if end is not None and dt > end:
            return False

    return True


def _stream_filter_history_rows(
    csv_path: Path,
    query: HistoryQueryDTO,
    policy: RetryPolicy,
) -> List[Dict[str, object]]:
    """
    Filtra historico em streaming.

    Para consultas paginadas (`limit > 0`), mantém apenas os K registros mais
    recentes em heap (K = offset + limit), evitando carregar tudo em memória.
    """
    start = _parse_query_datetime(query.data_inicio, end_of_day=False)
    end = _parse_query_datetime(query.data_fim, end_of_day=True)
    limit = int(query.limit or 0)
    offset = max(int(query.offset or 0), 0)
    k = limit + offset if limit > 0 else 0
    sequence = count()

    if k > 0:
        top_rows: List[tuple[float, int, Dict[str, object]]] = []
        with open_with_retry(csv_path, "r", encoding="utf-8", newline="", policy=policy) as handle:
            reader = csv.DictReader(handle, delimiter=";")
            for row in reader:
                if not _row_matches_history_query(row, query, start=start, end=end):
                    continue
                dt = _coerce_history_datetime(row.get("data_hora") or row.get("data_hora_analise"))
                sort_key = dt.timestamp() if dt is not None else float("-inf")
                item = (sort_key, next(sequence), dict(row))
                if len(top_rows) < k:
                    heapq.heappush(top_rows, item)
                elif item > top_rows[0]:
                    heapq.heapreplace(top_rows, item)

        top_rows.sort(reverse=True)
        sliced = [row for _, __, row in top_rows]
        return sliced[offset : offset + limit]

    matched: List[Dict[str, object]] = []
    with open_with_retry(csv_path, "r", encoding="utf-8", newline="", policy=policy) as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            if not _row_matches_history_query(row, query, start=start, end=end):
                continue
            matched.append(dict(row))

    matched.sort(
        key=lambda row: _coerce_history_datetime(row.get("data_hora") or row.get("data_hora_analise")
        ) or datetime.min,
        reverse=True,
    )
    return matched[offset:]


def _build_history_dedupe_key(record: HistoryRecordDTO) -> Optional[tuple[str, str, str, str]]:
    """Monta chave de deduplicacao contratual para historico."""
    key = build_dedupe_key(
        {
            "corrida_id": record.corrida_id or "",
            "amostra_codigo": record.amostra_codigo or "",
            "lote": record.lote or "",
            "data_exame": record.data_exame or "",
        },
        fields=DEDUPE_FIELDS,
    )
    if key is None:
        return None
    return (key[0], key[1], key[2], key[3])


@dataclass(frozen=True)
class _CsvConfig:
    path: Path
    delimiter: str
    headers: Sequence[str]


class _CsvStore:
    """Helper para leitura/escrita CSV com lock e retry."""

    def __init__(self, cfg: _CsvConfig) -> None:
        self.cfg = cfg
        self.cfg.path.parent.mkdir(parents=True, exist_ok=True)

    def _ensure(self) -> None:
        policy = RetryPolicy.from_env()
        if path_exists_with_retry(self.cfg.path, policy=policy):
            return
        try:
            with CSVFileLock(self.cfg.path):
                with open_with_retry(
                    self.cfg.path, "w", encoding="utf-8", newline="", policy=policy
                ) as f:
                    writer = csv.writer(f, delimiter=self.cfg.delimiter)
                    writer.writerow(self.cfg.headers)
        except Exception as exc:  # pragma: no cover
            registrar_log("CsvStore", f"Erro ao criar {self.cfg.path}: {exc}", "ERROR")

    def read_rows(self) -> List[Dict[str, str]]:
        """Le todas as linhas do CSV."""
        policy = RetryPolicy.from_env()
        if not path_exists_with_retry(self.cfg.path, policy=policy):
            return []
        try:
            with open_with_retry(
                self.cfg.path, "r", encoding="utf-8", newline="", policy=policy
            ) as f:
                reader = csv.DictReader(f, delimiter=self.cfg.delimiter)
                return [
                    {h: (row.get(h) or "") for h in self.cfg.headers} for row in reader
                ]
        except Exception as exc:  # pragma: no cover
            registrar_log("CsvStore", f"Erro ao ler {self.cfg.path}: {exc}", "ERROR")
            return []

    def write_rows(self, rows: List[Dict[str, str]]) -> None:
        """Grava todas as linhas no CSV."""
        policy = RetryPolicy.from_env()
        try:
            with CSVFileLock(self.cfg.path):
                with open_with_retry(
                    self.cfg.path, "w", encoding="utf-8", newline="", policy=policy
                ) as f:
                    writer = csv.DictWriter(
                        f, fieldnames=self.cfg.headers, delimiter=self.cfg.delimiter
                    )
                    writer.writeheader()
                    for row in rows:
                        writer.writerow(
                            {h: sanitize_csv_value(row.get(h, "")) for h in self.cfg.headers}
                        )
        except Exception as exc:  # pragma: no cover
            registrar_log("CsvStore", f"Erro ao salvar {self.cfg.path}: {exc}", "ERROR")
            raise ConcurrencyError(str(exc))


class CsvUserRepositoryAdapter(UserRepository):
    """Adapter CSV para o contrato UserRepository."""

    _headers = [
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

    def __init__(self, csv_path: Optional[str] = None) -> None:
        if csv_path:
            path = Path(csv_path)
        else:
            path = resolve_users_csv_path()
        self._store = _CsvStore(_CsvConfig(path=path, delimiter=",", headers=self._headers))
        self._store._ensure()

    def _row_to_dto(self, row: Dict[str, str]) -> UserDTO:
        return UserDTO(
            id=row.get("id", ""),
            username=row.get("usuario", ""),
            password_hash=row.get("senha_hash", ""),
            access_level=UserAccessLevel(row.get("nivel_acesso", "DIAGNOSTICO")),
            status=UserStatus(row.get("status", "ATIVO")),
            created_at=row.get("data_criacao", ""),
            last_access=row.get("ultimo_acesso") or None,
            failed_attempts=_safe_int(row.get("tentativas_falhas"), 0),
            locked_until=row.get("bloqueado_ate") or None,
            preferences=_safe_json_load(row.get("preferencias", "")),
        )

    def _find_index(self, rows: List[Dict[str, str]], key: str, value: str) -> int:
        for idx, row in enumerate(rows):
            if _normalize_key(row.get(key, "")) == _normalize_key(value):
                return idx
        return -1

    def get_by_id(self, user_id: str) -> UserDTO:
        rows = self._store.read_rows()
        idx = self._find_index(rows, "id", user_id)
        if idx < 0:
            raise NotFoundError(f"Usuario nao encontrado: {user_id}")
        return self._row_to_dto(rows[idx])

    def get_by_username(self, username: str) -> UserDTO:
        rows = self._store.read_rows()
        idx = self._find_index(rows, "usuario", username)
        if idx < 0:
            raise NotFoundError(f"Usuario nao encontrado: {username}")
        return self._row_to_dto(rows[idx])

    def list(self, status: Optional[UserStatus] = None) -> Sequence[UserDTO]:
        rows = self._store.read_rows()
        if status:
            rows = [r for r in rows if r.get("status", "ATIVO") == status.value]
        return [self._row_to_dto(row) for row in rows]

    def create(self, user: UserCreateDTO) -> UserDTO:
        if not user.username:
            raise ValidationError("username vazio")
        rows = self._store.read_rows()
        if self._find_index(rows, "usuario", user.username) >= 0:
            raise ConflictError("usuario ja existe")

        now = datetime.now().strftime("%Y-%m-%d")
        row = {
            "id": uuid.uuid4().hex[:8],
            "usuario": user.username,
            "senha_hash": user.password_hash,
            "nivel_acesso": user.access_level.value,
            "status": user.status.value,
            "data_criacao": now,
            "ultimo_acesso": "",
            "tentativas_falhas": "0",
            "bloqueado_ate": "",
            "preferencias": json.dumps(user.preferences or {}, ensure_ascii=False),
        }
        rows.append(row)
        self._store.write_rows(rows)
        return self._row_to_dto(row)

    def update(self, user_id: str, changes: UserUpdateDTO) -> UserDTO:
        rows = self._store.read_rows()
        idx = self._find_index(rows, "id", user_id)
        if idx < 0:
            raise NotFoundError(f"Usuario nao encontrado: {user_id}")

        row = rows[idx]
        if changes.access_level is not None:
            row["nivel_acesso"] = changes.access_level.value
        if changes.status is not None:
            row["status"] = changes.status.value
        if changes.password_hash is not None:
            row["senha_hash"] = changes.password_hash
        if changes.last_access is not None:
            row["ultimo_acesso"] = changes.last_access
        if changes.failed_attempts is not None:
            row["tentativas_falhas"] = str(changes.failed_attempts)
        if changes.locked_until is not None:
            row["bloqueado_ate"] = changes.locked_until
        if changes.preferences is not None:
            row["preferencias"] = json.dumps(changes.preferences, ensure_ascii=False)

        rows[idx] = row
        self._store.write_rows(rows)
        return self._row_to_dto(row)

    def delete(self, user_id: str) -> None:
        rows = self._store.read_rows()
        idx = self._find_index(rows, "id", user_id)
        if idx < 0:
            raise NotFoundError(f"Usuario nao encontrado: {user_id}")
        rows.pop(idx)
        self._store.write_rows(rows)

class CsvHistoryRepositoryAdapter(HistoryRepository):
    """Adapter CSV para historico (baseado em logs/historico_analises.csv)."""

    _required_headers = [
        "id_registro",
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
    ]
    _legacy_headers = [
        "data_hora_analise",
        "usuario_analise",
        "lote",
    ]
    _default_headers = _required_headers + _legacy_headers

    def __init__(self, csv_path: Optional[str] = None) -> None:
        paths = config_service.get_paths()
        resolved = csv_path or paths.get("gal_history_csv", "logs/historico_analises.csv")
        self.csv_path = Path(resolved)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_header()

    def _ensure_header(self) -> None:
        policy = RetryPolicy.from_env()
        if path_exists_with_retry(self.csv_path, policy=policy):
            self._ensure_contract_columns()
            return
        with CSVFileLock(self.csv_path):
            with open_with_retry(
                self.csv_path, "w", encoding="utf-8", newline="", policy=policy
            ) as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(self._default_headers)

    def _write_history_dataframe(self, df: pd.DataFrame, policy: RetryPolicy) -> None:
        """Persiste historico com escrita atomica contratual."""
        safe_df = df.fillna("").copy()
        rows = [
            {k: sanitize_csv_value(v) for k, v in record.items()}
            for record in safe_df.to_dict(orient="records")
        ]
        write_csv_atomic(
            self.csv_path,
            rows=rows,
            fieldnames=list(safe_df.columns),
            contract_name="historico_analises.csv",
            policy=policy,
        )

    def _read_header(self) -> List[str]:
        policy = RetryPolicy.from_env()
        if not path_exists_with_retry(self.csv_path, policy=policy):
            return []
        with open_with_retry(
            self.csv_path, "r", encoding="utf-8", newline="", policy=policy
        ) as f:
            reader = csv.reader(f, delimiter=";")
            header = next(reader, [])
            return [str(h).strip() for h in header]

    def _ensure_contract_columns(self) -> None:
        header = self._read_header()
        if not header:
            policy = RetryPolicy.from_env()
            with CSVFileLock(self.csv_path):
                with open_with_retry(
                    self.csv_path, "w", encoding="utf-8", newline="", policy=policy
                ) as f:
                    writer = csv.writer(f, delimiter=";")
                    writer.writerow(self._default_headers)
            return

        missing = [col for col in self._default_headers if col not in header]
        if not missing:
            return

        policy = RetryPolicy.from_env()
        try:
            df = call_with_retry(
                lambda: pd.read_csv(self.csv_path, sep=";", encoding="utf-8"),
                op_name="read_csv",
                path=self.csv_path,
                policy=policy,
            )
        except Exception as exc:  # pragma: no cover
            registrar_log(
                "CsvHistoryAdapter",
                f"Falha ao ler CSV para ajustar colunas: {exc}",
                "ERROR",
            )
            return

        for col in missing:
            df[col] = ""

        ordered = list(dict.fromkeys(list(header) + list(self._default_headers)))
        df = df.reindex(columns=ordered)

        self._write_history_dataframe(df, policy)

    def _row_to_dto(self, row: Dict[str, object]) -> HistoryRecordDTO:
        data_hora = row.get("data_hora") or row.get("data_hora_analise") or ""
        usuario = row.get("usuario") or row.get("usuario_analise") or ""
        return HistoryRecordDTO(
            record_id=str(row.get("id_registro") or row.get("id") or ""),
            data_hora=str(data_hora),
            exame=str(row.get("exame") or ""),
            equipamento=str(row.get("equipamento") or ""),
            usuario=str(usuario),
            num_placa=str(row.get("num_placa") or "") or None,
            status_corrida=str(row.get("status_corrida") or ""),
            total_amostras=_safe_int(row.get("total_amostras"), 0),
            total_detectados=_safe_int(row.get("total_detectados"), 0),
            total_nao_detectados=_safe_int(row.get("total_nao_detectados"), 0),
            total_inconclusivos=_safe_int(row.get("total_inconclusivos"), 0),
            total_invalidos=_safe_int(row.get("total_invalidos"), 0),
            arquivo_corrida=str(row.get("arquivo_corrida") or ""),
            observacoes=str(row.get("observacoes") or "") or None,
            nome_corrida=str(row.get("nome_corrida") or "") or None,
            quem_fez_extracao=str(row.get("quem_fez_extracao") or "") or None,
            quem_preparou_placa=str(row.get("quem_preparou_placa") or "") or None,
            corrida_id=str(row.get("corrida_id") or "") or None,
            amostra_codigo=str(row.get("amostra_codigo") or "") or None,
            lote=str(row.get("lote") or "") or None,
            data_exame=str(row.get("data_exame") or "") or None,
        )

    def append(self, record: HistoryRecordDTO) -> HistoryRecordDTO:
        header = self._read_header()
        if not header:
            self._ensure_header()
            header = self._read_header()

        dedupe_key = _build_history_dedupe_key(record)
        if dedupe_key is not None:
            existing = self.list(HistoryQueryDTO(limit=0))
            for current in existing:
                current_key = _build_history_dedupe_key(current)
                if current_key == dedupe_key:
                    registrar_log(
                        "CsvHistoryAdapter",
                        "Registro deduplicado por chave contratual.",
                        "INFO",
                    )
                    return current

        row: Dict[str, str] = {h: "" for h in header}
        record_id = record.record_id or uuid.uuid4().hex[:8]

        mapping = {
            "id_registro": record_id,
            "data_hora_analise": record.data_hora,
            "usuario_analise": record.usuario,
            "exame": record.exame,
            "arquivo_corrida": record.arquivo_corrida,
            "status_corrida": record.status_corrida,
            "observacoes": record.observacoes or "",
            "nome_corrida": record.nome_corrida or "",
            "quem_fez_extracao": record.quem_fez_extracao or "",
            "quem_preparou_placa": record.quem_preparou_placa or "",
            "data_hora": record.data_hora,
            "usuario": record.usuario,
            "equipamento": record.equipamento,
            "num_placa": record.num_placa or "",
            "total_amostras": str(record.total_amostras),
            "total_detectados": str(record.total_detectados),
            "total_nao_detectados": str(record.total_nao_detectados),
            "total_inconclusivos": str(record.total_inconclusivos),
            "total_invalidos": str(record.total_invalidos),
            "corrida_id": record.corrida_id or "",
            "amostra_codigo": record.amostra_codigo or "",
            "lote": record.lote or "",
            "data_exame": record.data_exame or "",
        }
        for key, value in mapping.items():
            if key in row:
                row[key] = sanitize_csv_value(value)

        policy = RetryPolicy.from_env()
        with CSVFileLock(self.csv_path):
            with open_with_retry(
                self.csv_path, "a", encoding="utf-8", newline="", policy=policy
            ) as f:
                writer = csv.DictWriter(f, fieldnames=header, delimiter=";")
                writer.writerow(row)

        return HistoryRecordDTO(**{**record.__dict__, "record_id": record_id})

    def append_batch(self, records: Iterable[HistoryRecordDTO]) -> int:
        count = 0
        for record in records:
            self.append(record)
            count += 1
        return count

    def list(self, query: HistoryQueryDTO) -> Sequence[HistoryRecordDTO]:
        policy = RetryPolicy.from_env()
        if not path_exists_with_retry(self.csv_path, policy=policy):
            return []

        rows = _stream_filter_history_rows(self.csv_path, query, policy)
        return [self._row_to_dto(row) for row in rows]

    def update_status(self, record_id: str, status: str, usuario: str) -> None:
        policy = RetryPolicy.from_env()
        if not path_exists_with_retry(self.csv_path, policy=policy):
            raise NotFoundError("CSV historico nao encontrado")

        df = call_with_retry(
            lambda: pd.read_csv(self.csv_path, sep=";", encoding="utf-8"),
            op_name="read_csv",
            path=self.csv_path,
            policy=policy,
        )
        if "id_registro" not in df.columns:
            raise ValidationError("id_registro ausente no CSV")

        mask = df["id_registro"].astype(str) == str(record_id)
        if not mask.any():
            raise NotFoundError(f"Registro nao encontrado: {record_id}")

        if "status_corrida" in df.columns:
            df.loc[mask, "status_corrida"] = status
        if "usuario_envio" in df.columns:
            df.loc[mask, "usuario_envio"] = usuario
        if "data_hora_envio" in df.columns:
            df.loc[mask, "data_hora_envio"] = _now_iso()

        self._write_history_dataframe(df, policy)

class SQLiteUserRepositoryAdapter(UserRepository):
    """Adapter SQLite para o contrato UserRepository."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path:
            resolved = db_path
        else:
            resolved = str(resolve_banco_dir() / "usuarios.db")
        self._repo = SQLiteUserRepository(resolved)

    def _row_to_dto(self, row: Dict[str, object]) -> UserDTO:
        status = UserStatus.ATIVO if row.get("ativo", 1) else UserStatus.INATIVO
        return UserDTO(
            id=str(row.get("id")),
            username=str(row.get("usuario") or ""),
            password_hash=str(row.get("senha_hash") or ""),
            access_level=UserAccessLevel(str(row.get("nivel_acesso") or "DIAGNOSTICO")),
            status=status,
            created_at=str(row.get("criado_em") or ""),
            last_access=str(row.get("ultimo_login") or "") or None,
            failed_attempts=0,
            locked_until=None,
            preferences={},
        )

    def get_by_id(self, user_id: str) -> UserDTO:
        row = self._repo.fetch_one("SELECT * FROM usuarios WHERE id = ?", (user_id,))
        if not row:
            raise NotFoundError(f"Usuario nao encontrado: {user_id}")
        return self._row_to_dto(row)

    def get_by_username(self, username: str) -> UserDTO:
        row = self._repo.fetch_one(
            "SELECT * FROM usuarios WHERE lower(usuario) = lower(?)",
            (username,),
        )
        if not row:
            raise NotFoundError(f"Usuario nao encontrado: {username}")
        return self._row_to_dto(row)

    def list(self, status: Optional[UserStatus] = None) -> Sequence[UserDTO]:
        if status == UserStatus.ATIVO:
            rows = self._repo.fetch_all("SELECT * FROM usuarios WHERE ativo = 1")
        elif status == UserStatus.INATIVO:
            rows = self._repo.fetch_all("SELECT * FROM usuarios WHERE ativo = 0")
        else:
            rows = self._repo.fetch_all("SELECT * FROM usuarios")
        return [self._row_to_dto(row) for row in rows]

    def create(self, user: UserCreateDTO) -> UserDTO:
        if not user.username:
            raise ValidationError("username vazio")
        created = self._repo.adicionar_usuario(
            usuario=user.username,
            senha_hash=user.password_hash,
            nivel=user.access_level.value,
        )
        if not created:
            raise ConflictError("usuario ja existe")
        return self.get_by_username(user.username)

    def update(self, user_id: str, changes: UserUpdateDTO) -> UserDTO:
        row = self._repo.fetch_one("SELECT * FROM usuarios WHERE id = ?", (user_id,))
        if not row:
            raise NotFoundError(f"Usuario nao encontrado: {user_id}")

        updates: Dict[str, object] = {}
        if changes.access_level is not None:
            updates["nivel_acesso"] = changes.access_level.value
        if changes.password_hash is not None:
            updates["senha_hash"] = changes.password_hash
        if changes.last_access is not None:
            updates["ultimo_login"] = changes.last_access
        if changes.status is not None:
            updates["ativo"] = 1 if changes.status == UserStatus.ATIVO else 0

        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            params = tuple(updates.values()) + (user_id,)
            self._repo.execute(f"UPDATE usuarios SET {set_clause} WHERE id = ?", params)

        return self.get_by_id(user_id)

    def delete(self, user_id: str) -> None:
        row = self._repo.fetch_one("SELECT id FROM usuarios WHERE id = ?", (user_id,))
        if not row:
            raise NotFoundError(f"Usuario nao encontrado: {user_id}")
        self._repo.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))


class SQLiteHistoryRepositoryAdapter(HistoryRepository):
    """Adapter SQLite para o contrato HistoryRepository."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path:
            resolved = db_path
        else:
            resolved = str(resolve_banco_dir() / "historico.db")
        self._repo = SQLiteHistoryRepository(resolved)

    def append(self, record: HistoryRecordDTO) -> HistoryRecordDTO:
        dedupe_key = _build_history_dedupe_key(record)
        if dedupe_key is not None:
            existing = self._repo.fetch_one(
                """
                SELECT id, data_hora
                FROM historico_analises
                WHERE lower(trim(corrida_id)) = ?
                  AND lower(trim(amostra_codigo)) = ?
                  AND lower(trim(lote)) = ?
                  AND lower(trim(data_exame)) = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                dedupe_key,
            )
            if existing:
                return HistoryRecordDTO(
                    **{
                        **record.__dict__,
                        "record_id": str(existing.get("id")),
                        "data_hora": str(existing.get("data_hora") or record.data_hora),
                    }
                )

        data = {
            "data_hora": record.data_hora,
            "exame": record.exame,
            "equipamento": record.equipamento,
            "usuario": record.usuario,
            "num_placa": record.num_placa,
            "status_corrida": record.status_corrida,
            "total_amostras": record.total_amostras,
            "total_detectados": record.total_detectados,
            "total_nao_detectados": record.total_nao_detectados,
            "total_inconclusivos": record.total_inconclusivos,
            "total_invalidos": record.total_invalidos,
            "arquivo_corrida": record.arquivo_corrida,
            "observacoes": record.observacoes,
            "nome_corrida": record.nome_corrida,
            "quem_fez_extracao": record.quem_fez_extracao,
            "quem_preparou_placa": record.quem_preparou_placa,
            "corrida_id": record.corrida_id,
            "amostra_codigo": record.amostra_codigo,
            "lote": record.lote,
            "data_exame": record.data_exame,
        }
        new_id = self._repo.adicionar_registro(data)
        return HistoryRecordDTO(**{**record.__dict__, "record_id": str(new_id)})

    def append_batch(self, records: Iterable[HistoryRecordDTO]) -> int:
        count = 0
        for record in records:
            self.append(record)
            count += 1
        return count

    def list(self, query: HistoryQueryDTO) -> Sequence[HistoryRecordDTO]:
        clauses: List[str] = []
        params: List[object] = []
        if query.exame:
            clauses.append("lower(trim(exame)) = ?")
            params.append(str(query.exame).strip().lower())
        if query.usuario:
            clauses.append("lower(trim(usuario)) = ?")
            params.append(str(query.usuario).strip().lower())
        if query.status_corrida:
            clauses.append("lower(trim(status_corrida)) = ?")
            params.append(str(query.status_corrida).strip().lower())
        start = _parse_query_datetime(query.data_inicio, end_of_day=False)
        if start is not None:
            clauses.append("datetime(data_hora) >= datetime(?)")
            params.append(start.strftime("%Y-%m-%d %H:%M:%S"))
        end = _parse_query_datetime(query.data_fim, end_of_day=True)
        if end is not None:
            clauses.append("datetime(data_hora) <= datetime(?)")
            params.append(end.strftime("%Y-%m-%d %H:%M:%S"))
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        limit_clause = ""
        if int(query.limit or 0) > 0:
            limit_clause = " LIMIT ?"
            params.append(int(query.limit))
        if int(query.offset or 0) > 0:
            if not limit_clause:
                limit_clause = " LIMIT -1"
            limit_clause += " OFFSET ?"
            params.append(int(query.offset))
        rows = self._repo.fetch_all(
            f"SELECT * FROM historico_analises{where} ORDER BY datetime(data_hora) DESC{limit_clause}",
            tuple(params),
        )
        return [
            HistoryRecordDTO(
                record_id=str(row.get("id")),
                data_hora=str(row.get("data_hora") or ""),
                exame=str(row.get("exame") or ""),
                equipamento=str(row.get("equipamento") or ""),
                usuario=str(row.get("usuario") or ""),
                num_placa=str(row.get("num_placa") or "") or None,
                status_corrida=str(row.get("status_corrida") or ""),
                total_amostras=_safe_int(row.get("total_amostras"), 0),
                total_detectados=_safe_int(row.get("total_detectados"), 0),
                total_nao_detectados=_safe_int(row.get("total_nao_detectados"), 0),
                total_inconclusivos=_safe_int(row.get("total_inconclusivos"), 0),
                total_invalidos=_safe_int(row.get("total_invalidos"), 0),
                arquivo_corrida=str(row.get("arquivo_corrida") or ""),
                observacoes=str(row.get("observacoes") or "") or None,
                nome_corrida=str(row.get("nome_corrida") or "") or None,
                quem_fez_extracao=str(row.get("quem_fez_extracao") or "") or None,
                quem_preparou_placa=str(row.get("quem_preparou_placa") or "") or None,
                corrida_id=str(row.get("corrida_id") or "") or None,
                amostra_codigo=str(row.get("amostra_codigo") or "") or None,
                lote=str(row.get("lote") or "") or None,
                data_exame=str(row.get("data_exame") or "") or None,
            )
            for row in rows
        ]

    def update_status(self, record_id: str, status: str, usuario: str) -> None:
        row = self._repo.fetch_one(
            "SELECT id FROM historico_analises WHERE id = ?", (record_id,)
        )
        if not row:
            raise NotFoundError(f"Registro nao encontrado: {record_id}")
        self._repo.execute(
            "UPDATE historico_analises SET status_corrida = ? WHERE id = ?",
            (status, record_id),
        )

class CsvExamConfigRepositoryAdapter(ExamConfigRepository):
    """Adapter CSV para configuracoes de exame (exames_config.csv)."""

    _headers = ["exame", "modulo_analise", "tipo_placa", "numero_kit", "equipamento"]

    def __init__(self, csv_path: Optional[str] = None) -> None:
        paths = config_service.get_paths()
        path = Path(csv_path or paths.get("exams_catalog_csv", "banco_runtime/exames_config.csv"))
        self._store = _CsvStore(_CsvConfig(path=path, delimiter=",", headers=self._headers))
        self._store._ensure()

    def _row_to_dto(self, row: Dict[str, str]) -> ExamConfigDTO:
        nome = row.get("exame", "")
        slug = _normalize_key(nome).replace(" ", "_")
        return ExamConfigDTO(
            nome_exame=nome,
            slug=slug,
            equipamento=row.get("equipamento", ""),
            tipo_placa_analitica=row.get("tipo_placa", ""),
            esquema_agrupamento="",
            kit_codigo=str(row.get("numero_kit", "")),
            alvos=[],
            mapa_alvos={},
            faixas_ct={},
            rps=[],
            export_fields=[],
            panel_tests_id="",
            controles={"cn": [], "cp": []},
            comentarios="",
            versao_protocolo="",
        )

    def list(self) -> Sequence[ExamConfigDTO]:
        return [self._row_to_dto(row) for row in self._store.read_rows()]

    def get(self, nome_exame: str) -> ExamConfigDTO:
        for row in self._store.read_rows():
            if _normalize_key(row.get("exame", "")) == _normalize_key(nome_exame):
                return self._row_to_dto(row)
        raise NotFoundError(f"Exame nao encontrado: {nome_exame}")

    def upsert(self, config: ExamConfigDTO) -> ExamConfigDTO:
        rows = self._store.read_rows()
        idx = -1
        for i, row in enumerate(rows):
            if _normalize_key(row.get("exame", "")) == _normalize_key(config.nome_exame):
                idx = i
                break
        new_row = {
            "exame": config.nome_exame,
            "modulo_analise": "",
            "tipo_placa": config.tipo_placa_analitica,
            "numero_kit": str(config.kit_codigo),
            "equipamento": config.equipamento,
        }
        if idx >= 0:
            rows[idx] = new_row
        else:
            rows.append(new_row)
        self._store.write_rows(rows)
        return self._row_to_dto(new_row)

    def delete(self, nome_exame: str) -> None:
        rows = self._store.read_rows()
        filtered = [
            row
            for row in rows
            if _normalize_key(row.get("exame", "")) != _normalize_key(nome_exame)
        ]
        if len(filtered) == len(rows):
            raise NotFoundError(f"Exame nao encontrado: {nome_exame}")
        self._store.write_rows(filtered)


class _CsvSimpleRepository:
    """Adapter base para CSVs simples (equipamentos/placas/regras)."""

    def __init__(self, path: Path, headers: Sequence[str]) -> None:
        self._store = _CsvStore(_CsvConfig(path=path, delimiter=",", headers=headers))
        self._store._ensure()
        self._headers = headers

    def _read(self) -> List[Dict[str, str]]:
        return self._store.read_rows()

    def _write(self, rows: List[Dict[str, str]]) -> None:
        self._store.write_rows(rows)


class CsvEquipmentRepositoryAdapter(EquipmentRepository):
    """Adapter CSV para equipamentos."""

    _headers = ["nome", "modelo", "fabricante", "observacoes"]

    def __init__(self, csv_path: Optional[str] = None) -> None:
        if csv_path:
            path = Path(csv_path)
        else:
            path = resolve_banco_dir() / "equipamentos.csv"
        self._repo = _CsvSimpleRepository(path, self._headers)

    def list(self) -> Sequence[EquipmentDTO]:
        return [EquipmentDTO(**row) for row in self._repo._read()]

    def get(self, nome: str) -> EquipmentDTO:
        for row in self._repo._read():
            if _normalize_key(row.get("nome", "")) == _normalize_key(nome):
                return EquipmentDTO(**row)
        raise NotFoundError(f"Equipamento nao encontrado: {nome}")

    def upsert(self, equipamento: EquipmentDTO) -> EquipmentDTO:
        rows = self._repo._read()
        idx = -1
        for i, row in enumerate(rows):
            if _normalize_key(row.get("nome", "")) == _normalize_key(equipamento.nome):
                idx = i
                break
        payload = {
            "nome": equipamento.nome,
            "modelo": equipamento.modelo,
            "fabricante": equipamento.fabricante,
            "observacoes": equipamento.observacoes,
        }
        if idx >= 0:
            rows[idx] = payload
        else:
            rows.append(payload)
        self._repo._write(rows)
        return equipamento

    def delete(self, nome: str) -> None:
        rows = self._repo._read()
        filtered = [
            row for row in rows if _normalize_key(row.get("nome", "")) != _normalize_key(nome)
        ]
        if len(filtered) == len(rows):
            raise NotFoundError(f"Equipamento nao encontrado: {nome}")
        self._repo._write(filtered)

class CsvPlateRepositoryAdapter(PlateRepository):
    """Adapter CSV para placas."""

    _headers = ["nome", "tipo", "num_pocos", "descricao"]

    def __init__(self, csv_path: Optional[str] = None) -> None:
        if csv_path:
            path = Path(csv_path)
        else:
            path = resolve_banco_dir() / "placas.csv"
        self._repo = _CsvSimpleRepository(path, self._headers)

    def list(self) -> Sequence[PlateDTO]:
        return [PlateDTO(**row) for row in self._repo._read()]

    def get(self, nome: str) -> PlateDTO:
        for row in self._repo._read():
            if _normalize_key(row.get("nome", "")) == _normalize_key(nome):
                return PlateDTO(**row)
        raise NotFoundError(f"Placa nao encontrada: {nome}")

    def upsert(self, placa: PlateDTO) -> PlateDTO:
        rows = self._repo._read()
        idx = -1
        for i, row in enumerate(rows):
            if _normalize_key(row.get("nome", "")) == _normalize_key(placa.nome):
                idx = i
                break
        payload = {
            "nome": placa.nome,
            "tipo": placa.tipo,
            "num_pocos": placa.num_pocos,
            "descricao": placa.descricao,
        }
        if idx >= 0:
            rows[idx] = payload
        else:
            rows.append(payload)
        self._repo._write(rows)
        return placa

    def delete(self, nome: str) -> None:
        rows = self._repo._read()
        filtered = [
            row for row in rows if _normalize_key(row.get("nome", "")) != _normalize_key(nome)
        ]
        if len(filtered) == len(rows):
            raise NotFoundError(f"Placa nao encontrada: {nome}")
        self._repo._write(filtered)


class CsvRuleRepositoryAdapter(RuleRepository):
    """Adapter CSV para regras."""

    _headers = ["nome_regra", "exame", "descricao", "parametros"]

    def __init__(self, csv_path: Optional[str] = None) -> None:
        if csv_path:
            path = Path(csv_path)
        else:
            path = resolve_banco_dir() / "regras.csv"
        self._repo = _CsvSimpleRepository(path, self._headers)

    def list(self) -> Sequence[RuleDTO]:
        return [RuleDTO(**row) for row in self._repo._read()]

    def get(self, nome_regra: str) -> RuleDTO:
        for row in self._repo._read():
            if _normalize_key(row.get("nome_regra", "")) == _normalize_key(nome_regra):
                return RuleDTO(**row)
        raise NotFoundError(f"Regra nao encontrada: {nome_regra}")

    def upsert(self, regra: RuleDTO) -> RuleDTO:
        rows = self._repo._read()
        idx = -1
        for i, row in enumerate(rows):
            if _normalize_key(row.get("nome_regra", "")) == _normalize_key(regra.nome_regra):
                idx = i
                break
        payload = {
            "nome_regra": regra.nome_regra,
            "exame": regra.exame,
            "descricao": regra.descricao,
            "parametros": regra.parametros,
        }
        if idx >= 0:
            rows[idx] = payload
        else:
            rows.append(payload)
        self._repo._write(rows)
        return regra

    def delete(self, nome_regra: str) -> None:
        rows = self._repo._read()
        filtered = [
            row
            for row in rows
            if _normalize_key(row.get("nome_regra", "")) != _normalize_key(nome_regra)
        ]
        if len(filtered) == len(rows):
            raise NotFoundError(f"Regra nao encontrada: {nome_regra}")
        self._repo._write(filtered)


class CsvPersistenceProvider(PersistenceProvider):
    """Provider para persistencia CSV."""

    def __init__(self) -> None:
        self._users = CsvUserRepositoryAdapter()
        self._history = CsvHistoryRepositoryAdapter()
        self._exams = CsvExamConfigRepositoryAdapter()
        self._equipments = CsvEquipmentRepositoryAdapter()
        self._plates = CsvPlateRepositoryAdapter()
        self._rules = CsvRuleRepositoryAdapter()

    def uow(self) -> PersistenceUnitOfWork:
        return _NoopUnitOfWork()

    def users(self) -> UserRepository:
        return self._users

    def history(self) -> HistoryRepository:
        return self._history

    def exams(self) -> ExamConfigRepository:
        return self._exams

    def equipments(self) -> EquipmentRepository:
        return self._equipments

    def plates(self) -> PlateRepository:
        return self._plates

    def rules(self) -> RuleRepository:
        return self._rules


class SQLitePersistenceProvider(PersistenceProvider):
    """Provider para persistencia SQLite (usuarios/historico)."""

    def __init__(self) -> None:
        self._users = SQLiteUserRepositoryAdapter()
        self._history = SQLiteHistoryRepositoryAdapter()
        self._exams = CsvExamConfigRepositoryAdapter()
        self._equipments = CsvEquipmentRepositoryAdapter()
        self._plates = CsvPlateRepositoryAdapter()
        self._rules = CsvRuleRepositoryAdapter()

    def uow(self) -> PersistenceUnitOfWork:
        return _NoopUnitOfWork()

    def users(self) -> UserRepository:
        return self._users

    def history(self) -> HistoryRepository:
        return self._history

    def exams(self) -> ExamConfigRepository:
        return self._exams

    def equipments(self) -> EquipmentRepository:
        return self._equipments

    def plates(self) -> PlateRepository:
        return self._plates

    def rules(self) -> RuleRepository:
        return self._rules


class _NoopUnitOfWork(PersistenceUnitOfWork):
    """UoW no-op para CSV/SQLite simples."""

    def __enter__(self) -> "PersistenceUnitOfWork":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None
