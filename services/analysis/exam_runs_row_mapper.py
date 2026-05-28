# -*- coding: utf-8 -*-
"""Mapeamento de DataFrame para linhas do contrato corridas_<slug_exame>.csv."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from services.core.config_service import config_service
from services.dedupe_keys import (
    DEDUPE_FIELDS as CONTRACT_DEDUPE_FIELDS,
    build_dedupe_key,
)
from services.analysis.full_run_contract import (
    SCHEMA_VERSION_FULL_RUN,
    classify_sample_status,
    normalize_source_column_name,
)
from utils.text_normalizer import repair_mojibake_text

DEDUPE_FIELDS: Tuple[str, str, str, str] = CONTRACT_DEDUPE_FIELDS
CORE_FIELDS: Tuple[str, ...] = (
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
)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    ascii_only = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_only).strip("_")
    return slug or "exame_desconhecido"


def normalize_key(value: object) -> str:
    raw = repair_mojibake_text(value if value is not None else "")
    normalized = unicodedata.normalize("NFKD", str(raw).strip().lower())
    ascii_only = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", ascii_only)


def clean_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return repair_mojibake_text(str(value)).strip()


def to_bool(value: object) -> bool:
    """Converte valores variados de selecao para bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    token = clean_text(value).lower()
    return token in {"1", "true", "yes", "sim", "y", "x", "[x]", "selecionado"}


def normalize_ct(value: object) -> str:
    raw = clean_text(value)
    if not raw:
        return ""
    try:
        return str(float(raw.replace(",", ".")))
    except ValueError:
        return ""


def canonical_target(value: str) -> str:
    target = normalize_key(value).upper()
    if target == "MPV":
        return "HMPV"
    return target


def parse_date_time(value: str) -> Tuple[str, str]:
    raw = clean_text(value)
    now = datetime.now()
    if not raw:
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.strftime("%Y-%m-%d"), parsed.strftime("%H:%M:%S")
        except ValueError:
            continue
    return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")


def pick_column(columns: Sequence[str], aliases: Iterable[str]) -> Optional[str]:
    key_to_col = {normalize_key(col): col for col in columns}
    for alias in aliases:
        candidate = key_to_col.get(normalize_key(alias))
        if candidate:
            return candidate
    return None


def extract_target_columns(columns: Sequence[str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    ct_map: Dict[str, str] = {}
    res_map: Dict[str, str] = {}
    for col in columns:
        name = clean_text(col).upper()
        ct_target = None
        res_target = None

        match = re.match(r"^CT[\s_\-]*(.+)$", name)
        if match:
            ct_target = match.group(1)
        match = re.match(r"^RES[\s_\-]*(.+)$", name)
        if match:
            res_target = match.group(1)
        match = re.match(r"^RESULTADO[\s_\-]*(.+)$", name)
        if match:
            res_target = match.group(1)
        match = re.match(r"^(.+?)\s*-\s*CT$", name)
        if match:
            ct_target = match.group(1)
        match = re.match(r"^(.+?)\s*-\s*R$", name)
        if match:
            res_target = match.group(1)

        if ct_target:
            canonical = canonical_target(ct_target)
            if canonical and canonical != "GERAL":
                ct_map[canonical] = col
        if res_target:
            canonical = canonical_target(res_target)
            if canonical and canonical != "GERAL":
                res_map[canonical] = col
    return ct_map, res_map


def ordered_dynamic_columns(columns: Iterable[str]) -> List[str]:
    col_set = set(columns)
    targets = set()
    extras: List[str] = []
    for col in col_set:
        if col.startswith("CT_"):
            targets.add(col[3:])
        elif col.startswith("RES_"):
            targets.add(col[4:])
        else:
            extras.append(col)

    ordered: List[str] = []
    for target in sorted(targets):
        ct_col = f"CT_{target}"
        res_col = f"RES_{target}"
        if ct_col in col_set:
            ordered.append(ct_col)
        if res_col in col_set:
            ordered.append(res_col)
    ordered.extend(sorted(set(extras)))
    return ordered


def resolve_logs_dir(logs_dir: Optional[Path | str]) -> Path:
    if logs_dir:
        return Path(logs_dir)
    paths = config_service.get_paths()
    if paths.get("logs_dir"):
        return Path(paths["logs_dir"])
    return Path(paths.get("gal_history_csv", "logs/historico_analises.csv")).parent


def dedupe_key(row: Dict[str, str]) -> Optional[Tuple[str, str, str, str]]:
    raw_key = build_dedupe_key(row, fields=DEDUPE_FIELDS)
    if raw_key is None:
        return None
    return (
        raw_key[0],
        raw_key[1],
        raw_key[2],
        raw_key[3],
    )


def build_rows(
    *,
    df: pd.DataFrame,
    exame: str,
    lote: str,
    data_exame: str,
    corrida_id: Optional[str],
    equipamento_id: str,
    equipamento_modelo: str,
    arquivo_corrida: str,
    usuario_execucao: str = "",
    nome_corrida: str = "",
    quem_fez_extracao: str = "",
    quem_preparou_placa: str = "",
    observacoes: str = "",
    timestamp_execucao: str = "",
) -> Tuple[str, List[Dict[str, str]]]:
    exame_slug = slugify(exame)
    data_iso, hora_iso = parse_date_time(data_exame)
    corrida_value = clean_text(corrida_id)
    if not corrida_value:
        corrida_value = f"{exame_slug}|{clean_text(lote)}|{data_iso}|{Path(str(arquivo_corrida)).name}"

    amostra_col = pick_column(df.columns, ("amostra_codigo", "codigo", "code"))
    pocos_col = pick_column(df.columns, ("poco", "pocos", "poco_s", "pocos_s"))
    resultado_col = pick_column(df.columns, ("resultado_geral", "resultado geral"))
    status_col = pick_column(df.columns, ("status_placa", "status placa"))
    equipamento_id_col = pick_column(df.columns, ("equipamento_id",))
    equipamento_modelo_col = pick_column(df.columns, ("equipamento_modelo", "equipamento"))
    selecionado_col = pick_column(df.columns, ("selecionado",))
    envio_status_col = pick_column(df.columns, ("status_gal", "status_envio", "envio_status"))

    ct_map, res_map = extract_target_columns(df.columns)
    targets = sorted(set(ct_map.keys()) | set(res_map.keys()))

    rows: List[Dict[str, str]] = []
    for _, src in df.iterrows():
        amostra = clean_text(src.get(amostra_col, "")) if amostra_col else ""
        lote_value = clean_text(lote)
        if not (amostra and lote_value and corrida_value and data_iso):
            continue

        row: Dict[str, str] = {
            "corrida_id": corrida_value,
            "exame_slug": exame_slug,
            "equipamento_id": clean_text(src.get(equipamento_id_col, "")) if equipamento_id_col else clean_text(equipamento_id),
            "equipamento_modelo": clean_text(src.get(equipamento_modelo_col, "")) if equipamento_modelo_col else clean_text(equipamento_modelo),
            "data_exame": data_iso,
            "hora_exame": hora_iso,
            "lote": lote_value,
            "amostra_codigo": amostra,
            "pocos": clean_text(src.get(pocos_col, "")) if pocos_col else "",
            "resultado_geral": clean_text(src.get(resultado_col, "")) if resultado_col else "",
            "status_placa": clean_text(src.get(status_col, "")) if status_col else "",
            "schema_version": SCHEMA_VERSION_FULL_RUN,
            "usuario_execucao": clean_text(usuario_execucao),
            "nome_corrida": clean_text(nome_corrida),
            "quem_fez_extracao": clean_text(quem_fez_extracao),
            "quem_preparou_placa": clean_text(quem_preparou_placa),
            "observacoes_corrida": clean_text(observacoes),
            "timestamp_execucao": clean_text(timestamp_execucao),
        }

        selecionado = to_bool(src.get(selecionado_col, False)) if selecionado_col else False
        envio_status = clean_text(src.get(envio_status_col, "")) if envio_status_col else ""
        row["status_amostra_corrida"] = classify_sample_status(
            codigo=amostra,
            selecionado=selecionado,
            envio_status=envio_status,
        )

        for target in targets:
            ct_col = ct_map.get(target)
            res_col = res_map.get(target)
            row[f"CT_{target}"] = normalize_ct(src.get(ct_col, "")) if ct_col else ""
            row[f"RES_{target}"] = clean_text(src.get(res_col, "")) if res_col else ""

        # Propaga todas as colunas de origem da UI para rastreabilidade completa.
        seen_src_keys: Dict[str, int] = {}
        for col in df.columns:
            normalized = normalize_source_column_name(col)
            base_key = f"SRC_{normalized}"
            if base_key not in seen_src_keys:
                seen_src_keys[base_key] = 1
                key = base_key
            else:
                seen_src_keys[base_key] += 1
                key = f"{base_key}_{seen_src_keys[base_key]}"
            if key in row:
                continue
            row[key] = clean_text(src.get(col, ""))
        rows.append(row)
    return exame_slug, rows
