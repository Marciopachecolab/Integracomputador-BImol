from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.encoding_policy import get_ingest_encodings
from utils.logger import registrar_log


class ConfigLoader:
    """Load profiles/protocols/rules with encoding-hardening for legacy ingest."""

    BASE_PATH = Path("banco_template")

    @staticmethod
    def _read_header_with_policy(file_path: str, max_chars: int = 4000) -> str:
        """Read textual header with strict decode and controlled fallback."""
        encodings = get_ingest_encodings()
        first = encodings[0] if encodings else "utf-8"

        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as handle:
                    content = handle.read(max_chars)
                if enc != first:
                    registrar_log(
                        "ConfigLoader",
                        f"Fallback de encoding aplicado em assinatura: {file_path} ({enc})",
                        "WARNING",
                    )
                return content
            except (OSError, UnicodeDecodeError, IOError, PermissionError):
                continue

        registrar_log(
            "ConfigLoader",
            f"Leitura de header falhou (assinatura): {file_path}",
            "DEBUG",
        )
        return ""

    @staticmethod
    def load_json_file(subdir: str, filename: str) -> List[Dict]:
        path = ConfigLoader.BASE_PATH / subdir / filename
        try:
            if not path.exists():
                registrar_log("ConfigLoader", f"Arquivo nao encontrado: {path}", "WARNING")
                return []

            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as e:
            registrar_log("ConfigLoader", f"Erro ao ler {path}: {e}", "ERROR")
            return []

    @staticmethod
    def get_equipment_profiles() -> List[Dict]:
        profiles = ConfigLoader.load_json_file("profiles", "equipment_profiles.json")
        marked: List[Dict] = []
        for profile in profiles:
            item = dict(profile)
            item.setdefault("source_of_truth", "legacy_equipment_profiles_json")
            item.setdefault("legacy_deprecation", "E07")
            marked.append(item)
        return marked

    @staticmethod
    def get_protocols() -> List[Dict]:
        return ConfigLoader.load_json_file("protocols", "analysis_protocols.json")

    @staticmethod
    def get_analysis_rules() -> List[Dict]:
        return ConfigLoader.load_json_file("protocols", "analysis_rules.json")

    @staticmethod
    def get_profile_by_signature(file_path: str) -> Optional[Dict]:
        """Try to identify equipment profile based on filename/header signatures."""
        profiles = ConfigLoader.get_equipment_profiles()
        fname = str(file_path).lower()
        header_content = ConfigLoader._read_header_with_policy(file_path, max_chars=4000)

        for prof in profiles:
            score = 0
            signatures = prof.get("file_signatures", [])
            required_checks = len(signatures)

            for sig in signatures:
                check_type = sig.get("check")
                val = sig.get("value")

                if check_type == "filename_extension":
                    exts = val if isinstance(val, list) else [val]
                    if any(fname.endswith(str(ext).lower()) for ext in exts):
                        score += 1

                elif check_type in {"contains_header", "contains_column"}:
                    if str(val or "") in header_content:
                        score += 1

            if score == required_checks and required_checks > 0:
                return prof

        return None
