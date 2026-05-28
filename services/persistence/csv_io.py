from __future__ import annotations

import csv
import os
import uuid
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import pandas as pd

from services.persistence.csv_contracts import CsvContract, get_csv_contract
from services.encoding_policy import get_encoding_policy
from services.shared_io import flush_and_fsync as _shared_flush_and_fsync
from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, call_with_retry, open_with_retry, path_exists_with_retry

UTF8_BOM = b"\xef\xbb\xbf"


def _flush_and_fsync(handle) -> None:
    """Garante persistencia do arquivo temporario antes do rename atomico."""
    _shared_flush_and_fsync(handle)


def _resolve_contract(path: Path, contract_name: str | None) -> CsvContract:
    ref = contract_name or path.name
    contract = get_csv_contract(ref)
    if contract is None:
        raise ValueError(f"CSV contract violation: no contract found for '{ref}'")
    return contract


def _validate_header(path: Path, contract: CsvContract, policy: RetryPolicy) -> None:
    encoding_policy = get_encoding_policy()
    allow_bom = bool(encoding_policy.get("allow_bom", False))

    with open_with_retry(path, "rb", policy=policy) as handle:
        raw = handle.read()
    if not raw:
        raise ValueError(f"CSV contract violation: empty file for '{path.name}'")

    has_bom = raw.startswith(UTF8_BOM)
    if has_bom and not allow_bom and contract.encoding.lower().startswith("utf-8"):
        raise ValueError(
            f"CSV contract violation: BOM detected in '{path.name}' "
            "(encoding policy forbids BOM)"
        )

    decode_encoding = contract.encoding
    if has_bom and allow_bom and contract.encoding.lower() == "utf-8":
        decode_encoding = "utf-8-sig"

    try:
        text = raw.decode(decode_encoding)
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"CSV contract violation: invalid encoding for '{path.name}' "
            f"(expected '{contract.encoding}')"
        ) from exc

    first_line = text.splitlines()[0] if text else ""
    if not first_line:
        raise ValueError(f"CSV contract violation: empty file for '{path.name}'")

    expected = contract.delimiter
    unexpected = ";" if expected == "," else ","
    if first_line.count(expected) == 0 and first_line.count(unexpected) > 0:
        raise ValueError(
            f"CSV contract violation: invalid delimiter for '{path.name}' "
            f"(expected '{expected}')"
        )


def read_csv_strict(
    path: str | Path,
    *,
    contract_name: str | None = None,
    policy: RetryPolicy | None = None,
    **read_kwargs,
) -> pd.DataFrame:
    """Read a contractual CSV with strict delimiter/encoding/header checks."""
    resolved = Path(path)
    retry_policy = policy or RetryPolicy.from_env()
    contract = _resolve_contract(resolved, contract_name)

    if not path_exists_with_retry(resolved, policy=retry_policy):
        raise FileNotFoundError(f"CSV contract violation: file not found '{resolved}'")

    _validate_header(resolved, contract, retry_policy)

    read_encoding = contract.encoding
    if contract.encoding.lower() == "utf-8" and bool(get_encoding_policy().get("allow_bom", False)):
        read_encoding = "utf-8-sig"

    df = call_with_retry(
        lambda: pd.read_csv(
            resolved,
            sep=contract.delimiter,
            encoding=read_encoding,
            **read_kwargs,
        ),
        op_name="read_csv_strict",
        path=resolved,
        policy=retry_policy,
    )
    df.columns = [str(col).strip() for col in df.columns]
    missing = [col for col in contract.required_headers if col not in df.columns]
    if missing:
        raise ValueError(
            f"CSV contract violation: missing required headers in '{resolved.name}': {missing}"
        )
    return df


def write_csv_atomic(
    path: str | Path,
    *,
    rows: Iterable[Mapping[str, object]],
    fieldnames: Sequence[str],
    contract_name: str | None = None,
    policy: RetryPolicy | None = None,
) -> None:
    """Write CSV replacing the target atomically under file lock."""
    resolved = Path(path)
    retry_policy = policy or RetryPolicy.from_env()
    contract = _resolve_contract(resolved, contract_name)

    resolved.parent.mkdir(parents=True, exist_ok=True)
    tmp = resolved.with_name(f"{resolved.name}.{uuid.uuid4().hex}.tmp")

    with CSVFileLock(resolved):
        try:
            with open_with_retry(
                tmp,
                "w",
                encoding=contract.encoding,
                newline="",
                policy=retry_policy,
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=list(fieldnames),
                    delimiter=contract.delimiter,
                )
                writer.writeheader()
                for row in rows:
                    writer.writerow({name: row.get(name, "") for name in fieldnames})
                _flush_and_fsync(handle)
            os.replace(tmp, resolved)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
