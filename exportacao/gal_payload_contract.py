# -*- coding: utf-8 -*-
"""Contrato versionado do payload GAL enviado via endpoint de exame."""

from __future__ import annotations

from typing import Any, Dict, List


GAL_PAYLOAD_SCHEMA_VERSION = "1.0.0"
GAL_PAYLOAD_REQUIRED_FIELDS: tuple[str, ...] = (
    "codigo",
    "requisicao",
    "paciente",
    "exame",
    "metodo",
    "registroInterno",
    "kit",
    "reteste",
    "loteKit",
    "dataProcessamentoIni",
    "dataProcessamentoFim",
    "valorReferencia",
    "observacao",
    "painel",
    "resultados",
)

GAL_PAYLOAD_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "schema_version": GAL_PAYLOAD_SCHEMA_VERSION,
    "title": "gal_payload",
    "type": "object",
    "required": list(GAL_PAYLOAD_REQUIRED_FIELDS),
    "properties": {
        "codigo": {"type": "string"},
        "requisicao": {"type": "string"},
        "paciente": {"type": "string"},
        "exame": {"type": "string"},
        "metodo": {"type": "string"},
        "registroInterno": {"type": "string"},
        "kit": {"type": ["integer", "null"]},
        "reteste": {"type": "string"},
        "loteKit": {"type": "string"},
        "dataProcessamentoIni": {"type": "string"},
        "dataProcessamentoFim": {"type": "string"},
        "valorReferencia": {"type": ["string", "number"]},
        "observacao": {"type": "string"},
        "painel": {"type": ["integer", "string"]},
        "resultados": {"type": "object"},
    },
}


def get_gal_payload_schema() -> Dict[str, Any]:
    """Retorna o schema versionado do payload GAL."""
    return GAL_PAYLOAD_SCHEMA.copy()


def validate_gal_payload(payload: Dict[str, Any]) -> List[str]:
    """Valida minimamente o payload GAL conforme contrato operacional."""
    errors: List[str] = []
    if not isinstance(payload, dict):
        return ["payload deve ser dict"]

    for field in GAL_PAYLOAD_REQUIRED_FIELDS:
        if field not in payload:
            errors.append(f"campo obrigatorio ausente: {field}")

    resultados = payload.get("resultados")
    if "resultados" in payload and not isinstance(resultados, dict):
        errors.append("campo 'resultados' deve ser dict")
    elif isinstance(resultados, dict) and "resultado" not in resultados:
        errors.append("campo 'resultados.resultado' ausente")

    registro = str(payload.get("registroInterno", "") or "").strip()
    if "registroInterno" in payload and not registro:
        errors.append("campo 'registroInterno' vazio")

    # S24: Validar não-vazio de codigo.
    # codigo = codigoAmostra (sempre disponível no CSV) — nunca deve ser vazio.
    # requisicao e paciente são omitidos desta validação: no modo
    # USE_GAL_ENVIO_SEM_METADADOS eles são intencionalmente vazios para que o
    # GAL os localize pelo par codigo+gal_exame_codigo. O endpoint retornará
    # erro claro ("já liberado", "não existe", etc.) se o registro não for
    # encontrado, sem necessidade de validação local antecipada.
    if "codigo" in payload and not str(payload.get("codigo", "") or "").strip():
        errors.append(
            "campo 'codigo' vazio — deve ser igual ao codigoAmostra do CSV "
            "(verifique construir_payload)"
        )

    return errors
