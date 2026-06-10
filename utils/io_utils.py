# FileName: /Integragal/utils/io_utils.py
from __future__ import annotations

import os
from typing import Optional

import warnings

import pandas as pd

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

from services.encoding_policy import get_ingest_encodings
from utils.logger import registrar_log
from utils.network_io import (
    RetryPolicy,
    call_with_retry,
    open_with_retry,
    path_exists_with_retry,
)

# CSV files that should skip header detection to avoid noisy warnings.
CSV_SKIP_HEADER_DETECTION = {
    "usuarios.csv",
    "gal_last_exame.csv",
}


def _read_lines_with_encoding_fallback(filepath: str, *, max_lines: int) -> list[str]:
    """Read text lines using ingest encoding policy."""
    policy = RetryPolicy.from_env()
    last_exc: Exception | None = None

    for enc in get_ingest_encodings():
        try:
            lines: list[str] = []
            with open_with_retry(filepath, "r", encoding=enc, policy=policy) as handle:
                for _ in range(max_lines):
                    line = handle.readline()
                    if not line:
                        break
                    lines.append(line)
            return lines
        except UnicodeDecodeError as exc:
            last_exc = exc
            registrar_log(
                "IO Utils",
                (
                    f"Decode failed for '{os.path.basename(filepath)}' with '{enc}'. "
                    "Trying ingest fallback encoding."
                ),
                level="WARNING",
            )
        except Exception as exc:
            last_exc = exc
            registrar_log(
                "IO Utils",
                f"Error reading '{os.path.basename(filepath)}' with '{enc}': {exc}",
                level="DEBUG",
            )

    if last_exc is not None:
        raise last_exc
    return []


def detectar_separador_csv(filepath: str) -> str:
    """
    Detect separator by inspecting first lines.
    Prefers ';' over ',' when ambiguous.
    """
    try:
        for line in _read_lines_with_encoding_fallback(filepath, max_lines=5):
            if ";" in line and "," not in line:
                registrar_log(
                    "IO Utils",
                    f"Separador detectado para '{os.path.basename(filepath)}': ';'",
                    level="DEBUG",
                )
                return ";"
            if "," in line and ";" not in line:
                registrar_log(
                    "IO Utils",
                    f"Separador detectado para '{os.path.basename(filepath)}': ','",
                    level="DEBUG",
                )
                return ","
            if ";" in line and "," in line:
                selected = ";" if line.count(";") > line.count(",") else ","
                registrar_log(
                    "IO Utils",
                    f"Separador detectado para '{os.path.basename(filepath)}': '{selected}'",
                    level="DEBUG",
                )
                return selected

        registrar_log(
            "IO Utils",
            (
                f"Separador padrao ',' usado para '{os.path.basename(filepath)}' "
                "(nao detectado claramente)."
            ),
            level="WARNING",
        )
        return ","
    except Exception as exc:
        registrar_log(
            "IO Utils",
            (
                f"Erro ao detectar separador para '{os.path.basename(filepath)}': "
                f"{exc}. Usando padrao ','."
            ),
            level="ERROR",
        )
        return ","


def _resolver_sheet_resultados(filepath: str):
    """Resolve a aba a usar na leitura generica de resultados.

    Equipamentos diferem no nome da aba de dados: o QuantStudio usa "Results",
    mas o export do 7500 (e outros) usa outro nome. Estrategia:
      1. se existir aba cujo nome normalizado == "results", usa ela (QuantStudio);
      2. senao, usa a primeira aba que NAO seja de extracao (nome com "extra");
      3. fallback: primeira aba do arquivo.
    Em caso de falha ao listar abas, retorna "Results" (comportamento legado).
    """
    try:
        with pd.ExcelFile(filepath) as xls:
            sheets = list(xls.sheet_names)
    except Exception as exc:
        registrar_log(
            "IO Utils",
            f"Nao foi possivel listar abas de '{os.path.basename(filepath)}': {exc}. "
            "Usando 'Results'.",
            level="WARNING",
        )
        return "Results"

    if not sheets:
        return 0

    for nome in sheets:
        if str(nome).strip().casefold() == "results":
            return nome

    def _eh_extracao(nome: object) -> bool:
        return "extra" in str(nome).strip().casefold()

    candidatos = [s for s in sheets if not _eh_extracao(s)]
    escolhida = (candidatos or sheets)[0]
    registrar_log(
        "IO Utils",
        f"Aba 'Results' ausente em '{os.path.basename(filepath)}'; usando aba '{escolhida}'.",
        level="DEBUG",
    )
    return escolhida


def detectar_linha_cabecalho(filepath: str, sep: str = ",") -> int:
    """
    Detect header line for CSV/Excel by common keywords.
    Returns zero-based row index.
    """
    policy = RetryPolicy.from_env()
    try:
        filepath = str(filepath)
        base_name = os.path.basename(filepath).lower()
        if base_name in CSV_SKIP_HEADER_DETECTION:
            registrar_log(
                "IO Utils",
                f"Header detection skipped for '{os.path.basename(filepath)}'. Using row 0.",
                level="DEBUG",
            )
            return 0

        registrar_log(
            "IO Utils",
            f"Detectando linha de cabecalho em: {os.path.basename(filepath)}",
            level="DEBUG",
        )

        if filepath.lower().endswith(".csv"):
            lines = _read_lines_with_encoding_fallback(filepath, max_lines=51)
            for idx, line in enumerate(lines):
                lower = line.lower()
                if all(token in lower for token in ["well", "sample", "target"]):
                    registrar_log(
                        "IO Utils",
                        (
                            f"Cabecalho detectado em CSV '{os.path.basename(filepath)}' "
                            f"na linha {idx}."
                        ),
                        level="DEBUG",
                    )
                    return idx
            registrar_log(
                "IO Utils",
                f"Cabecalho nao detectado em CSV '{os.path.basename(filepath)}'. Usando linha 0.",
                level="WARNING",
            )
            return 0

        if filepath.lower().endswith((".xls", ".xlsx")):
            sheet_alvo = _resolver_sheet_resultados(filepath)
            for skip_rows in range(50):
                try:
                    temp_df = call_with_retry(
                        lambda _sheet=sheet_alvo, _skip=skip_rows: pd.read_excel(
                            filepath,
                            sheet_name=_sheet,
                            skiprows=_skip,
                            engine="openpyxl",
                        ),
                        op_name="read_excel",
                        path=filepath,
                        policy=policy,
                    )
                    temp_df.columns = [str(col).strip() for col in temp_df.columns]
                    if (
                        any("Well" in col for col in temp_df.columns)
                        and any("Sample" in col for col in temp_df.columns)
                        and any("Target" in col for col in temp_df.columns)
                    ):
                        registrar_log(
                            "IO Utils",
                            (
                                f"Cabecalho detectado em Excel '{os.path.basename(filepath)}' "
                                f"na linha {skip_rows} (skiprows)."
                            ),
                            level="DEBUG",
                        )
                        return skip_rows
                except Exception:
                    continue
            registrar_log(
                "IO Utils",
                f"Cabecalho nao detectado em Excel '{os.path.basename(filepath)}'. Usando linha 0.",
                level="WARNING",
            )
            return 0

        registrar_log(
            "IO Utils",
            (
                "Tipo de arquivo desconhecido para deteccao de cabecalho: "
                f"'{os.path.basename(filepath)}'. Usando linha 0."
            ),
            level="WARNING",
        )
        return 0
    except Exception as exc:
        registrar_log(
            "IO Utils",
            (
                f"Erro ao detectar linha de cabecalho para '{os.path.basename(filepath)}': "
                f"{exc}. Usando linha 0."
            ),
            level="ERROR",
        )
        return 0


def read_data_with_auto_detection(filepath: str) -> Optional[pd.DataFrame]:
    """
    Read CSV/Excel with auto-detection for separator and header row.

    Note: fallback encodings are only accepted on ingest boundary and controlled
    by config.encoding_policy.
    """
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(filepath, policy=policy):
        registrar_log("IO Utils", f"Arquivo nao encontrado: {filepath}", level="ERROR")
        return None

    ext = os.path.splitext(filepath)[-1].lower()
    df: Optional[pd.DataFrame] = None

    if ext in [".xls", ".xlsx"]:
        registrar_log(
            "IO Utils",
            f"Tentando ler arquivo Excel: {os.path.basename(filepath)}",
            level="INFO",
        )
        try:
            skip_rows = detectar_linha_cabecalho(filepath)
            sheet_alvo = _resolver_sheet_resultados(filepath)
            df = call_with_retry(
                lambda: pd.read_excel(
                    filepath, sheet_name=sheet_alvo, skiprows=skip_rows, engine="openpyxl"
                ),
                op_name="read_excel",
                path=filepath,
                policy=policy,
            )
            df.columns = [str(col).strip() for col in df.columns]
            registrar_log(
                "IO Utils",
                f"Arquivo Excel '{os.path.basename(filepath)}' lido com sucesso.",
                level="INFO",
            )
        except Exception as exc:
            registrar_log(
                "IO Utils",
                f"Falha ao ler arquivo Excel '{os.path.basename(filepath)}': {exc}",
                level="ERROR",
            )
            return None

    elif ext == ".csv":
        registrar_log(
            "IO Utils",
            f"Tentando ler arquivo CSV: {os.path.basename(filepath)}",
            level="INFO",
        )
        try:
            sep = detectar_separador_csv(filepath)
            skip_rows = detectar_linha_cabecalho(filepath, sep=sep)
            encodings_to_try = get_ingest_encodings()
            last_exception: Exception | None = None

            for enc in encodings_to_try:
                try:
                    df = call_with_retry(
                        lambda: pd.read_csv(filepath, encoding=enc, sep=sep, skiprows=skip_rows),
                        op_name=f"read_csv[{enc}]",
                        path=filepath,
                        policy=policy,
                    )
                    df.columns = [str(col).strip() for col in df.columns]
                    registrar_log(
                        "IO Utils",
                        (
                            f"Arquivo CSV '{os.path.basename(filepath)}' lido com sucesso "
                            f"com codificacao '{enc}'."
                        ),
                        level="INFO",
                    )
                    if enc != encodings_to_try[0]:
                        registrar_log(
                            "IO Utils",
                            (
                                "Fallback de encoding aplicado em ingestao legada "
                                f"('{enc}') para '{os.path.basename(filepath)}'."
                            ),
                            level="WARNING",
                        )
                    break
                except UnicodeDecodeError as exc:
                    last_exception = exc
                    registrar_log(
                        "IO Utils",
                        f"Falha na leitura CSV com codificacao '{enc}': {exc}",
                        level="DEBUG",
                    )
                except Exception as exc:
                    last_exception = exc
                    registrar_log(
                        "IO Utils",
                        f"Erro na leitura CSV com codificacao '{enc}': {exc}",
                        level="ERROR",
                    )

            if df is None:
                registrar_log(
                    "IO Utils",
                    (
                        "Todas as tentativas de leitura CSV falharam para "
                        f"'{os.path.basename(filepath)}'. Ultimo erro: {last_exception}"
                    ),
                    level="ERROR",
                )
                return None

        except Exception as exc:
            registrar_log(
                "IO Utils",
                f"Falha ao ler arquivo CSV '{os.path.basename(filepath)}': {exc}",
                level="ERROR",
            )
            return None
    else:
        registrar_log(
            "IO Utils",
            f"Tipo de arquivo nao suportado para leitura: {ext}",
            level="ERROR",
        )
        return None

    if df is not None:
        try:
            import unicodedata as _ud

            def _norm_col(col):
                if not isinstance(col, str):
                    return col
                original = col.strip()
                ascii_name = _ud.normalize("NFKD", original).encode("ASCII", "ignore").decode("ASCII")
                token = ascii_name.strip().lower()
                token_compact = token.replace(" ", "").replace("_", "")

                if token in {"target name", "target"}:
                    return "Target"
                if token in {"sample name", "sample"}:
                    return "Sample"
                if token in {"well position"}:
                    return "Well Position"
                if token in {"well"}:
                    return "Well"
                if token_compact in {"c", "ct", "cq"} or token in {"c(t)"}:
                    return "CT"
                return original

            df.columns = [_norm_col(c) for c in df.columns]
        except Exception:
            pass

        cols = list(df.columns)
        ct_indexes = [idx for idx, name in enumerate(cols) if name == "CT"]
        if len(ct_indexes) > 1:
            for i, idx in enumerate(ct_indexes[1:], start=1):
                cols[idx] = f"CT_AUX_{i}"
            df.columns = cols

        if "CT" in df.columns and not isinstance(df["CT"], pd.DataFrame):
            df["CT"] = df["CT"].apply(
                lambda x: (
                    round(float(str(x).replace(",", ".").strip()), 2)
                    if pd.notna(x)
                    and str(x).replace(",", ".").strip().replace(".", "", 1).isdigit()
                    else pd.NA
                )
            )
            registrar_log("IO Utils", "Coluna 'CT' convertida para float.", level="DEBUG")

    return df
