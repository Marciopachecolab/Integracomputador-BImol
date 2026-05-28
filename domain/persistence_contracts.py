# -*- coding: utf-8 -*-
"""
Contratos de persistencia (DTOs + Interfaces).

Este modulo define apenas os contratos da camada de persistencia.
Implementacoes concretas (CSV/SQLite/PostgreSQL) devem viver na infraestrutura.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, Optional, Protocol, Sequence


class UserStatus(str, Enum):
    """Status de usuario."""

    ATIVO = "ATIVO"
    INATIVO = "INATIVO"
    BLOQUEADO = "BLOQUEADO"
    EXPIRADO = "EXPIRADO"


class UserAccessLevel(str, Enum):
    """Nivel de acesso do usuario."""

    ADMIN = "ADMIN"
    MASTER = "MASTER"
    DIAGNOSTICO = "DIAGNOSTICO"


@dataclass(frozen=True)
class UserDTO:
    """DTO de usuario persistido."""

    id: str
    username: str
    password_hash: str
    access_level: UserAccessLevel
    status: UserStatus
    created_at: str
    last_access: Optional[str] = None
    failed_attempts: int = 0
    locked_until: Optional[str] = None
    preferences: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class UserCreateDTO:
    """DTO para criacao de usuario."""

    username: str
    password_hash: str
    access_level: UserAccessLevel
    status: UserStatus = UserStatus.ATIVO
    preferences: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class UserUpdateDTO:
    """DTO para atualizacao parcial de usuario."""

    access_level: Optional[UserAccessLevel] = None
    status: Optional[UserStatus] = None
    password_hash: Optional[str] = None
    last_access: Optional[str] = None
    failed_attempts: Optional[int] = None
    locked_until: Optional[str] = None
    preferences: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class HistoryRecordDTO:
    """DTO de registro de historico."""

    record_id: Optional[str]
    data_hora: str
    exame: str
    equipamento: str
    usuario: str
    num_placa: Optional[str]
    status_corrida: str
    total_amostras: int
    total_detectados: int
    total_nao_detectados: int
    total_inconclusivos: int
    total_invalidos: int
    arquivo_corrida: str
    observacoes: Optional[str] = None
    corrida_id: Optional[str] = None
    amostra_codigo: Optional[str] = None
    lote: Optional[str] = None
    data_exame: Optional[str] = None
    nome_corrida: Optional[str] = None
    quem_fez_extracao: Optional[str] = None
    quem_preparou_placa: Optional[str] = None


@dataclass(frozen=True)
class HistoryQueryDTO:
    """DTO para filtros de consulta de historico."""

    exame: Optional[str] = None
    usuario: Optional[str] = None
    status_corrida: Optional[str] = None
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None
    limit: int = 1000
    offset: int = 0


@dataclass(frozen=True)
class ExamConfigDTO:
    """DTO de configuracao de exame."""

    nome_exame: str
    slug: str
    equipamento: str
    tipo_placa_analitica: str
    esquema_agrupamento: str
    kit_codigo: str
    alvos: Sequence[str] = field(default_factory=list)
    mapa_alvos: Dict[str, str] = field(default_factory=dict)
    faixas_ct: Dict[str, float] = field(default_factory=dict)
    rps: Sequence[str] = field(default_factory=list)
    export_fields: Sequence[str] = field(default_factory=list)
    panel_tests_id: str = ""
    controles: Dict[str, Sequence[str]] = field(default_factory=lambda: {"cn": [], "cp": []})
    comentarios: str = ""
    versao_protocolo: str = ""
    pocos_por_amostra: int = 1
    targets_por_poco: Sequence[Dict[str, object]] = field(default_factory=list)
    limiares_ct_por_alvo_poco: Sequence[Dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True)
class EquipmentDTO:
    """DTO de equipamento."""

    nome: str
    modelo: str
    fabricante: str
    observacoes: str = ""


@dataclass(frozen=True)
class PlateDTO:
    """DTO de placa."""

    nome: str
    tipo: str
    num_pocos: str
    descricao: str = ""


@dataclass(frozen=True)
class RuleDTO:
    """DTO de regra."""

    nome_regra: str
    exame: str
    descricao: str
    parametros: str


class PersistenceError(Exception):
    """Erro base da camada de persistencia."""


class NotFoundError(PersistenceError):
    """Recurso nao encontrado."""


class ConflictError(PersistenceError):
    """Conflito de chave unica ou versao."""


class ConcurrencyError(PersistenceError):
    """Falha de concorrencia (lock ou versao)."""


class ValidationError(PersistenceError):
    """Dados invalidos para persistencia."""


class StorageUnavailableError(PersistenceError):
    """Fonte de dados indisponivel."""


class UserRepository(Protocol):
    """Contrato para persistencia de usuarios."""

    def get_by_id(self, user_id: str) -> UserDTO:
        """Retorna usuario por id."""

    def get_by_username(self, username: str) -> UserDTO:
        """Retorna usuario por username."""

    def list(self, status: Optional[UserStatus] = None) -> Sequence[UserDTO]:
        """Lista usuarios com filtro opcional."""

    def create(self, user: UserCreateDTO) -> UserDTO:
        """Cria usuario."""

    def update(self, user_id: str, changes: UserUpdateDTO) -> UserDTO:
        """Atualiza usuario."""

    def delete(self, user_id: str) -> None:
        """Remove usuario."""


class HistoryRepository(Protocol):
    """Contrato para persistencia de historico."""

    def append(self, record: HistoryRecordDTO) -> HistoryRecordDTO:
        """Adiciona registro ao historico."""

    def append_batch(self, records: Iterable[HistoryRecordDTO]) -> int:
        """Adiciona varios registros e retorna quantidade."""

    def list(self, query: HistoryQueryDTO) -> Sequence[HistoryRecordDTO]:
        """Consulta historico com filtros."""

    def update_status(self, record_id: str, status: str, usuario: str) -> None:
        """Atualiza status de um registro."""


class ExamConfigRepository(Protocol):
    """Contrato para configuracoes de exames."""

    def list(self) -> Sequence[ExamConfigDTO]:
        """Lista exames."""

    def get(self, nome_exame: str) -> ExamConfigDTO:
        """Obtém configuracao de exame."""

    def upsert(self, config: ExamConfigDTO) -> ExamConfigDTO:
        """Cria/atualiza configuracao."""

    def delete(self, nome_exame: str) -> None:
        """Remove configuracao."""


class EquipmentRepository(Protocol):
    """Contrato para equipamentos."""

    def list(self) -> Sequence[EquipmentDTO]:
        """Lista equipamentos."""

    def get(self, nome: str) -> EquipmentDTO:
        """Obtém equipamento."""

    def upsert(self, equipamento: EquipmentDTO) -> EquipmentDTO:
        """Cria/atualiza equipamento."""

    def delete(self, nome: str) -> None:
        """Remove equipamento."""


class PlateRepository(Protocol):
    """Contrato para placas."""

    def list(self) -> Sequence[PlateDTO]:
        """Lista placas."""

    def get(self, nome: str) -> PlateDTO:
        """Obtém placa."""

    def upsert(self, placa: PlateDTO) -> PlateDTO:
        """Cria/atualiza placa."""

    def delete(self, nome: str) -> None:
        """Remove placa."""


class RuleRepository(Protocol):
    """Contrato para regras."""

    def list(self) -> Sequence[RuleDTO]:
        """Lista regras."""

    def get(self, nome_regra: str) -> RuleDTO:
        """Obtém regra."""

    def upsert(self, regra: RuleDTO) -> RuleDTO:
        """Cria/atualiza regra."""

    def delete(self, nome_regra: str) -> None:
        """Remove regra."""


class PersistenceUnitOfWork(Protocol):
    """Unidade de trabalho opcional (SQL) ou no-op (CSV)."""

    def __enter__(self) -> "PersistenceUnitOfWork":
        """Inicia unidade de trabalho."""

    def __exit__(self, exc_type, exc, tb) -> None:
        """Encerra unidade de trabalho."""

    def commit(self) -> None:
        """Confirma transacao."""

    def rollback(self) -> None:
        """Desfaz transacao."""


class PersistenceProvider(Protocol):
    """Gateway principal para obter repositorios."""

    def uow(self) -> PersistenceUnitOfWork:
        """Retorna unidade de trabalho."""

    def users(self) -> UserRepository:
        """Retorna repositorio de usuarios."""

    def history(self) -> HistoryRepository:
        """Retorna repositorio de historico."""

    def exams(self) -> ExamConfigRepository:
        """Retorna repositorio de exames."""

    def equipments(self) -> EquipmentRepository:
        """Retorna repositorio de equipamentos."""

    def plates(self) -> PlateRepository:
        """Retorna repositorio de placas."""

    def rules(self) -> RuleRepository:
        """Retorna repositorio de regras."""
