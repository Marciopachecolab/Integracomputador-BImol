"""Contratos de consulta para o modulo de relatorios."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable, Mapping, Sequence

from domain.exam_scope import ExamForaDoEscopoError


MAX_LIMIT = 5000
DEFAULT_LIMIT = 500

STATUS_REALIZACAO = ("realizado", "a_realizar", "parcial", "pendente")
POSITIVIDADE = (
    "positivo",
    "negativo",
    "inconclusivo",
    "indeterminado",
    "invalido",
    "detectavel",
    "nao_detectavel",
)
STATUS_GAL = ("enviado", "nao_enviado", "erro", "duplicado", "nao_enviavel", "sem_chave_gal")
GROUP_BY = ("periodo", "exame", "positividade", "analista", "kit", "lote", "status_gal")


class ReportsValidationError(ValueError):
    """Erro de validacao dos contratos de relatorio."""


def _parse_date(value: str | date, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        raise ReportsValidationError(f"{field_name} obrigatoria")
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ReportsValidationError(f"{field_name} deve usar formato YYYY-MM-DD") from exc


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold()


def _dedupe_text(values: Iterable[Any] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return tuple(result)


def _validate_choices(
    field_name: str,
    values: Sequence[str],
    allowed: Sequence[str],
) -> None:
    allowed_set = set(allowed)
    invalid = [value for value in values if value not in allowed_set]
    if invalid:
        raise ReportsValidationError(
            f"{field_name} contem valor invalido: {', '.join(invalid)}"
        )


def _normalize_exams(
    exames: Iterable[Any] | None,
    active_exams: Iterable[str],
) -> tuple[str, ...]:
    active = _dedupe_text(active_exams)
    if not active:
        raise ReportsValidationError("active_exams vazio; consulta fail-closed")

    by_key = {_normalize_key(exam): exam for exam in active}
    requested = _dedupe_text(exames)
    if not requested:
        return active

    normalized: list[str] = []
    for exam in requested:
        canonical = by_key.get(_normalize_key(exam))
        if canonical is None:
            raise ExamForaDoEscopoError(exam)
        normalized.append(canonical)
    return tuple(normalized)


@dataclass(frozen=True)
class ReportsFilterDTO:
    """Filtros normalizados para consultas de relatorios."""

    data_inicio: date
    data_fim: date
    exames: tuple[str, ...]
    status_realizacao: tuple[str, ...] = field(default_factory=tuple)
    positividade: tuple[str, ...] = field(default_factory=tuple)
    analistas: tuple[str, ...] = field(default_factory=tuple)
    kits: tuple[str, ...] = field(default_factory=tuple)
    lotes: tuple[str, ...] = field(default_factory=tuple)
    status_gal: tuple[str, ...] = field(default_factory=tuple)
    agrupar_por: tuple[str, ...] = field(default_factory=tuple)
    limit: int = DEFAULT_LIMIT
    offset: int = 0

    @classmethod
    def from_raw(
        cls,
        *,
        data_inicio: str | date,
        data_fim: str | date,
        active_exams: Iterable[str],
        exames: Iterable[Any] | None = None,
        status_realizacao: Iterable[Any] | None = None,
        positividade: Iterable[Any] | None = None,
        analistas: Iterable[Any] | None = None,
        kits: Iterable[Any] | None = None,
        lotes: Iterable[Any] | None = None,
        status_gal: Iterable[Any] | None = None,
        agrupar_por: Iterable[Any] | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> "ReportsFilterDTO":
        """Cria filtros validados a partir de valores vindos da UI/API."""
        return cls(
            data_inicio=_parse_date(data_inicio, "data_inicio"),
            data_fim=_parse_date(data_fim, "data_fim"),
            exames=_normalize_exams(exames, active_exams),
            status_realizacao=_dedupe_text(status_realizacao),
            positividade=_dedupe_text(positividade),
            analistas=_dedupe_text(analistas),
            kits=_dedupe_text(kits),
            lotes=_dedupe_text(lotes),
            status_gal=_dedupe_text(status_gal),
            agrupar_por=_dedupe_text(agrupar_por),
            limit=int(limit),
            offset=int(offset),
        )

    def __post_init__(self) -> None:
        if self.data_inicio > self.data_fim:
            raise ReportsValidationError("data_inicio nao pode ser maior que data_fim")
        if not self.exames:
            raise ReportsValidationError("exames obrigatorio")
        if self.limit < 1 or self.limit > MAX_LIMIT:
            raise ReportsValidationError(f"limit deve estar entre 1 e {MAX_LIMIT}")
        if self.offset < 0:
            raise ReportsValidationError("offset deve ser maior ou igual a zero")
        _validate_choices("status_realizacao", self.status_realizacao, STATUS_REALIZACAO)
        _validate_choices("positividade", self.positividade, POSITIVIDADE)
        _validate_choices("status_gal", self.status_gal, STATUS_GAL)
        _validate_choices("agrupar_por", self.agrupar_por, GROUP_BY)


@dataclass(frozen=True)
class ReportsPaginationDTO:
    """Metadados de paginacao do relatorio."""

    limit: int
    offset: int
    total_estimado: int

    def __post_init__(self) -> None:
        if self.limit < 1 or self.limit > MAX_LIMIT:
            raise ReportsValidationError(f"limit deve estar entre 1 e {MAX_LIMIT}")
        if self.offset < 0:
            raise ReportsValidationError("offset deve ser maior ou igual a zero")
        if self.total_estimado < 0:
            raise ReportsValidationError("total_estimado deve ser maior ou igual a zero")


@dataclass(frozen=True)
class ReportsGroupDTO:
    """Linha agregada de relatorio."""

    chaves: Mapping[str, str]
    total: int
    positivos: int = 0
    negativos: int = 0
    pendentes_gal: int = 0

    def __post_init__(self) -> None:
        for field_name in ("total", "positivos", "negativos", "pendentes_gal"):
            if getattr(self, field_name) < 0:
                raise ReportsValidationError(
                    f"{field_name} deve ser maior ou igual a zero"
                )


@dataclass(frozen=True)
class ReportsDetailDTO:
    """Linha detalhada de relatorio por amostra/corrida."""

    corrida_id: str
    amostra_codigo: str
    exame: str
    data_exame: date
    analista: str
    kit: str
    lote: str
    resultado_geral: str
    status_gal: str

    def __post_init__(self) -> None:
        if self.status_gal not in STATUS_GAL:
            raise ReportsValidationError(f"status_gal invalido: {self.status_gal}")
        if not isinstance(self.data_exame, date):
            raise ReportsValidationError("data_exame deve ser date")


@dataclass(frozen=True)
class ReportsResultDTO:
    """Resultado completo de uma consulta de relatorio."""

    resumo: Mapping[str, Any]
    agrupamentos: tuple[ReportsGroupDTO, ...]
    detalhes: tuple[ReportsDetailDTO, ...]
    paginacao: ReportsPaginationDTO
