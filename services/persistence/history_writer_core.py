# -*- coding: utf-8 -*-
"""Core isolado de escrita/merge para historico compativel."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

import pandas as pd

from services.dedupe_keys import DEDUPE_FIELDS, normalize_dedupe_value


def build_history_compat_records(
    *,
    df_final: pd.DataFrame,
    exame: str,
    usuario: str,
    lote: str,
    data_exame_default: str,
    corrida_id_default: str,
    arquivo_corrida: str,
    status_corrida_default: str,
    bioquimico_default: str,
    equipamento_default: str = "",
    nome_corrida_default: str = "",
    quem_fez_extracao_default: str = "",
    quem_preparou_placa_default: str = "",
    observacoes_default: str = "",
) -> list[dict[str, Any]]:
    """Transforma dataframe de analise em registros de historico compat."""
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    col_map = {str(c).strip().lower(): c for c in df_final.columns}
    poco_col = col_map.get("poco") or col_map.get("poço") or col_map.get("po?o") or col_map.get("poco(s)") or col_map.get("poço(s)")
    amostra_col = col_map.get("amostra") or col_map.get("sample")
    codigo_col = col_map.get("codigo") or col_map.get("código") or col_map.get("c?digo") or col_map.get("code")
    status_col = col_map.get("status_corrida") or col_map.get("status corrida")
    exame_col = col_map.get("exame")
    equipamento_col = col_map.get("equipamento")
    lote_col = col_map.get("lote")
    data_exame_col = col_map.get("data_exame")
    corrida_id_col = col_map.get("corrida_id")
    nome_corrida_col = col_map.get("nome_corrida") or col_map.get("nome corrida")
    quem_fez_extracao_col = (
        col_map.get("quem_fez_extracao")
        or col_map.get("quem fez extracao")
    )
    quem_preparou_placa_col = (
        col_map.get("quem_preparou_placa")
        or col_map.get("quem preparou placa")
    )
    observacoes_col = col_map.get("observacoes")
    bioquimico_col = col_map.get("bioquimico") or col_map.get("bioquímico")

    records: list[dict[str, Any]] = []
    for _, row in df_final.iterrows():
        exame_value = exame or str(row.get(exame_col, "") or "").strip()
        equipamento_value = (
            str(row.get(equipamento_col, "") or "").strip()
            if equipamento_col
            else str(equipamento_default or "").strip()
        )
        lote_value = (
            str(row.get(lote_col, "") or "").strip() if lote_col else str(lote or "")
        )
        data_exame_value = (
            str(row.get(data_exame_col, "") or "").strip()
            if data_exame_col
            else data_exame_default
        )
        corrida_id_value = (
            str(row.get(corrida_id_col, "") or "").strip()
            if corrida_id_col
            else corrida_id_default
        )
        arquivo_value = (
            Path(str(arquivo_corrida)).name
            if arquivo_corrida
            else str(row.get("arquivo_corrida", "")).strip()
        )
        codigo_value = str(row.get(codigo_col, "")).strip() if codigo_col else ""
        nome_corrida_value = (
            str(row.get(nome_corrida_col, "") or "").strip()
            if nome_corrida_col
            else str(nome_corrida_default or "").strip()
        )
        quem_fez_extracao_value = (
            str(row.get(quem_fez_extracao_col, "") or "").strip()
            if quem_fez_extracao_col
            else str(quem_fez_extracao_default or "").strip()
        )
        quem_preparou_placa_value = (
            str(row.get(quem_preparou_placa_col, "") or "").strip()
            if quem_preparou_placa_col
            else str(quem_preparou_placa_default or "").strip()
        )
        observacoes_value = (
            str(row.get(observacoes_col, "") or "").strip()
            if observacoes_col
            else str(observacoes_default or "").strip()
        )
        if not corrida_id_value:
            corrida_id_value = (
                f"{exame_value}|{lote_value}|{data_exame_value}|{arquivo_value}".strip("|")
            )

        record = {
            "id_registro": uuid4().hex,
            "data_hora": now_iso,
            "data_hora_analise": now_str,
            "usuario_analise": usuario or "",
            "exame": exame_value,
            "equipamento": equipamento_value,
            "lote": lote_value,
            "arquivo_corrida": arquivo_value,
            "poco": str(row.get(poco_col, "")).strip() if poco_col else "",
            "amostra": str(row.get(amostra_col, "")).strip() if amostra_col else "",
            "codigo": codigo_value,
            "amostra_codigo": codigo_value,
            "nome_corrida": nome_corrida_value,
            "quem_fez_extracao": quem_fez_extracao_value,
            "quem_preparou_placa": quem_preparou_placa_value,
            "observacoes": observacoes_value,
            "corrida_id": corrida_id_value,
            "data_exame": data_exame_value,
            "status_corrida": (
                str(row.get(status_col, "")).strip() if status_col else status_corrida_default
            ),
            "status_gal": "",
            "mensagem_gal": "",
            "data_hora_envio": "",
            "usuario_envio": "",
            "sucesso_envio": "",
            "detalhes_envio": "",
            "bioquimico": "",
            "criado_em": now_str,
            "atualizado_em": now_str,
        }

        bioquimico_value = (
            str(row.get(bioquimico_col, "")).strip() if bioquimico_col else ""
        )
        if not bioquimico_value:
            bioquimico_value = str(bioquimico_default).strip()
        record["bioquimico"] = bioquimico_value

        for col in df_final.columns:
            name = str(col).strip()
            name_upper = name.upper()
            value = row.get(col, None)
            if pd.isna(value):
                value = ""

            if name_upper.startswith("RESULTADO_"):
                target = name_upper.replace("RESULTADO_", "").strip()
                record[f"{target} - R"] = value
                continue
            if name_upper.startswith("RES_"):
                target = name_upper.replace("RES_", "").strip()
                record[f"{target} - R"] = value
                continue
            if name_upper.endswith(" - R"):
                record[name] = value
                continue
            if name_upper.startswith("CT_"):
                target = name_upper.replace("CT_", "").strip()
                record[f"{target} - CT"] = value
                continue
            if name_upper.endswith(" - CT"):
                record[name] = value
                continue
            if (
                name_upper.startswith("RP")
                and "CT" not in name_upper
                and "RESULTADO" not in name_upper
                and "RES_" not in name_upper
            ):
                record[f"{name_upper} - CT"] = value
                continue

        records.append(record)

    return records


def merge_history_frames(existing_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    """Faz merge preservando uniao de colunas."""
    union_cols = list(dict.fromkeys(list(existing_df.columns) + list(new_df.columns)))
    old_aligned = existing_df.reindex(columns=union_cols)
    new_aligned = new_df.reindex(columns=union_cols)
    return pd.concat([old_aligned, new_aligned], ignore_index=True)


def dedupe_history_frame(df: pd.DataFrame, *, fields: Iterable[str] = DEDUPE_FIELDS) -> pd.DataFrame:
    """Remove duplicidades por chave contratual mantendo ultimo registro."""
    dedupe_cols = list(fields)
    if not all(col in df.columns for col in dedupe_cols):
        return df

    scope = df.copy()
    for col in dedupe_cols:
        scope[col] = scope[col].map(normalize_dedupe_value)
    valid_mask = scope[dedupe_cols].ne("").all(axis=1)
    duplicates_mask = scope.duplicated(subset=dedupe_cols, keep="last")
    drop_mask = valid_mask & duplicates_mask
    if not bool(drop_mask.any()):
        return df
    return df.loc[~drop_mask].reset_index(drop=True)
