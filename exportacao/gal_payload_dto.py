"""DTO leve para normalizacao do payload GAL em compatibilidade legado."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class GalPayloadDTO:
    codigo: str = ""
    requisicao: str = ""
    paciente: str = ""
    exame: str = ""
    metodo: str = ""
    registro_interno: str = ""
    kit: int | None = None
    reteste: str = ""
    lote_kit: str = ""
    data_processamento_ini: str = ""
    data_processamento_fim: str = ""
    valor_referencia: str | int | float = ""
    observacao: str = ""
    painel: int = 1
    resultados: dict[str, Any] = field(default_factory=lambda: {"resultado": None})

    @classmethod
    def from_legacy_payload(cls, payload: Mapping[str, Any] | None) -> "GalPayloadDTO":
        raw = dict(payload) if isinstance(payload, Mapping) else {}
        registro_interno = str(
            raw.get("registroInterno") or raw.get("codigoAmostra") or ""
        ).strip()

        return cls(
            codigo=str(raw.get("codigo", "") or ""),
            requisicao=str(raw.get("requisicao", "") or ""),
            paciente=str(raw.get("paciente", "") or ""),
            exame=str(raw.get("exame", "") or ""),
            metodo=str(raw.get("metodo", "") or ""),
            registro_interno=registro_interno,
            kit=cls._coerce_optional_int(raw.get("kit")),
            reteste=str(raw.get("reteste", "") or ""),
            lote_kit=str(raw.get("loteKit", "") or ""),
            data_processamento_ini=str(raw.get("dataProcessamentoIni", "") or ""),
            data_processamento_fim=str(raw.get("dataProcessamentoFim", "") or ""),
            valor_referencia=cls._normalize_valor_referencia(raw.get("valorReferencia", "")),
            observacao=str(raw.get("observacao", "") or ""),
            painel=cls._coerce_painel(raw.get("painel", 1)),
            resultados=cls._normalize_resultados(raw.get("resultados")),
        )

    def to_legacy_payload(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "requisicao": self.requisicao,
            "paciente": self.paciente,
            "exame": self.exame,
            "metodo": self.metodo,
            "registroInterno": self.registro_interno,
            "kit": self.kit,
            "reteste": self.reteste,
            "loteKit": self.lote_kit,
            "dataProcessamentoIni": self.data_processamento_ini,
            "dataProcessamentoFim": self.data_processamento_fim,
            "valorReferencia": self.valor_referencia,
            "observacao": self.observacao,
            "painel": self.painel,
            "resultados": dict(self.resultados),
        }

    @staticmethod
    def _coerce_optional_int(value: Any) -> int | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            raw = value.strip()
            if raw.isdigit():
                return int(raw)
        return None

    @staticmethod
    def _coerce_painel(value: Any) -> int:
        if isinstance(value, bool):
            return 1
        if isinstance(value, int):
            return value if value > 0 else 1
        if isinstance(value, float) and value.is_integer():
            coerced = int(value)
            return coerced if coerced > 0 else 1
        if isinstance(value, str):
            raw = value.strip()
            if raw.isdigit():
                parsed = int(raw)
                return parsed if parsed > 0 else 1
        return 1

    @staticmethod
    def _normalize_valor_referencia(value: Any) -> str | int | float:
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            return value
        return ""

    @classmethod
    def _normalize_resultados(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            return {"resultado": None}

        normalized: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key or "").strip()
            if not key:
                continue
            normalized[key] = cls._normalize_result_value(raw_value)

        normalized.setdefault("resultado", None)
        return normalized

    @staticmethod
    def _normalize_result_value(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, bool):
            return "DETECTADO" if value else "NAO_DETECTADO"
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            return value
        return None
