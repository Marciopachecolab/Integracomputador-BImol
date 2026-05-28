# -*- coding: utf-8 -*-
"""Persistencia de presets e estado da consulta operacional por usuario (F8)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional

from services.shared_paths import resolve_logs_dir as _shared_resolve_logs_dir
from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, open_with_retry, path_exists_with_retry
from utils.logger import registrar_log

_DEFAULT_STATE: Dict[str, object] = {
    "view": "corridas",
    "periodo_inicio": "",
    "periodo_fim": "",
    "exame": "",
    "status": "",
    "operador": "",
    "busca_textual": "",
    "sort_by": "",
    "sort_direction": "desc",
    "page": 1,
    "page_size": 100,
}


class OperationalViewerProfileStore:
    """Store JSON leve para presets e estado de consulta por usuario."""

    def __init__(self, *, logs_dir: Optional[str | Path] = None, file_name: str = "operational_viewer_profiles.json") -> None:
        self.path = self._resolve_logs_dir(logs_dir) / file_name

    @staticmethod
    def _resolve_logs_dir(logs_dir: Optional[str | Path]) -> Path:
        return _shared_resolve_logs_dir(logs_dir)

    def get_user_state(self, user_id: str) -> Dict[str, object]:
        payload = self._load_all()
        token = self._safe_user(user_id)
        user_payload = payload.get("users", {}).get(token, {})
        state = user_payload.get("state", {}) if isinstance(user_payload, dict) else {}
        merged = dict(_DEFAULT_STATE)
        if isinstance(state, dict):
            merged.update(state)
        return merged

    def save_user_state(self, user_id: str, state: Dict[str, object]) -> None:
        payload = self._load_all()
        token = self._safe_user(user_id)
        payload.setdefault("users", {}).setdefault(token, {})["state"] = {
            **dict(_DEFAULT_STATE),
            **(state or {}),
        }
        self._save_all(payload)

    def list_presets(self, user_id: str) -> Dict[str, Dict[str, object]]:
        payload = self._load_all()
        token = self._safe_user(user_id)
        user_payload = payload.get("users", {}).get(token, {})
        presets = user_payload.get("presets", {}) if isinstance(user_payload, dict) else {}
        if not isinstance(presets, dict):
            return {}
        safe: Dict[str, Dict[str, object]] = {}
        for key, value in presets.items():
            name = str(key or "").strip()
            if not name or not isinstance(value, dict):
                continue
            safe[name] = dict(value)
        return safe

    def save_preset(self, user_id: str, name: str, state: Dict[str, object]) -> None:
        preset_name = str(name or "").strip()
        if not preset_name:
            raise ValueError("nome do preset obrigatorio")
        payload = self._load_all()
        token = self._safe_user(user_id)
        user = payload.setdefault("users", {}).setdefault(token, {})
        presets = user.setdefault("presets", {})
        if not isinstance(presets, dict):
            presets = {}
            user["presets"] = presets
        presets[preset_name] = {
            **dict(_DEFAULT_STATE),
            **(state or {}),
        }
        self._save_all(payload)

    def delete_preset(self, user_id: str, name: str) -> None:
        payload = self._load_all()
        token = self._safe_user(user_id)
        user_payload = payload.get("users", {}).get(token, {})
        if not isinstance(user_payload, dict):
            return
        presets = user_payload.get("presets")
        if not isinstance(presets, dict):
            return
        presets.pop(str(name or "").strip(), None)
        self._save_all(payload)

    @staticmethod
    def _safe_user(user_id: str) -> str:
        token = str(user_id or "").strip()
        return token or "anonimo"

    def _load_all(self) -> Dict[str, object]:
        policy = RetryPolicy.from_env()
        if not path_exists_with_retry(self.path, policy=policy):
            return {"users": {}}
        try:
            with open_with_retry(self.path, "r", encoding="utf-8", policy=policy) as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                payload.setdefault("users", {})
                return payload
        except Exception as exc:
            registrar_log("ViewerProfile", f"Falha ao ler perfil: {exc}", "WARNING")
        return {"users": {}}

    def _save_all(self, payload: Dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        policy = RetryPolicy.from_env()
        text = json.dumps(payload, ensure_ascii=False, indent=2)

        with CSVFileLock(self.path):
            fd, tmp_name = tempfile.mkstemp(
                prefix=f"{self.path.name}.",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            os.close(fd)
            tmp = Path(tmp_name)
            try:
                with open_with_retry(tmp, "w", encoding="utf-8", policy=policy) as handle:
                    handle.write(text)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp, self.path)
            finally:
                if tmp.exists():
                    try:
                        tmp.unlink()
                    except Exception:
                        pass


__all__ = ["OperationalViewerProfileStore"]
