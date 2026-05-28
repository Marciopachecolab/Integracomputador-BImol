from __future__ import annotations


def safe_str_trim(value: object) -> str:
    """Normalize any value to a trimmed string."""
    return str(value or "").strip()


def safe_str_no_strip(value: object) -> str:
    """Normalize to string without trimming whitespace."""
    return str(value) if value is not None else ""


def safe_str_pandas_strip(value: object) -> str:
    """Normalize values with pandas NA/NaN awareness and trim output."""
    if value is None:
        return ""
    try:
        import pandas as pd

        if pd.isna(value):  # type: ignore[arg-type]
            return ""
    except Exception:
        pass
    return str(value).strip()


def safe_str(value: object) -> str:
    """Normalize any value to a trimmed string, preserving legacy semantics."""
    return safe_str_trim(value)


__all__ = [
    "safe_str",
    "safe_str_trim",
    "safe_str_no_strip",
    "safe_str_pandas_strip",
]
