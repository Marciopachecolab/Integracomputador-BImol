from __future__ import annotations

from typing import Any, Dict, List

from services.core.config_service import config_service

DEFAULT_ENCODING_POLICY: Dict[str, Any] = {
    "default": "utf-8",
    "allow_bom": False,
    "strict_mode": False,
    "legacy_fallback_on_ingest_only": True,
    "fallback_encodings": ["utf-8-sig", "cp1252", "latin-1"],
}


def get_encoding_policy() -> Dict[str, Any]:
    """Return merged runtime encoding policy with safe defaults."""
    raw = config_service.get("encoding_policy", {}) or {}
    if not isinstance(raw, dict):
        return dict(DEFAULT_ENCODING_POLICY)

    merged = dict(DEFAULT_ENCODING_POLICY)
    for key in ("default", "allow_bom", "strict_mode", "legacy_fallback_on_ingest_only"):
        if key in raw:
            merged[key] = raw[key]

    fallback = raw.get("fallback_encodings")
    if isinstance(fallback, (list, tuple)):
        normalized = [str(item).strip() for item in fallback if str(item).strip()]
        if normalized:
            merged["fallback_encodings"] = normalized

    return merged


def get_ingest_encodings() -> List[str]:
    """
    Resolve decode order for legacy ingest boundaries.

    Internal runtime should remain UTF-8 strict; fallbacks are allowed only
    when strict_mode is disabled and policy explicitly allows it.
    """
    policy = get_encoding_policy()
    default_enc = str(policy.get("default") or "utf-8").strip()
    strict_mode = bool(policy.get("strict_mode", False))
    allow_fallback = bool(policy.get("legacy_fallback_on_ingest_only", True))

    encodings: List[str] = [default_enc]
    if (not strict_mode) and allow_fallback:
        for enc in policy.get("fallback_encodings", []) or []:
            token = str(enc).strip()
            if token and token not in encodings:
                encodings.append(token)
    return encodings

