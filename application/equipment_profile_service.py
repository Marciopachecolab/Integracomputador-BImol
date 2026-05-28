from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

_EQUIPMENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]{0,62}[a-z0-9]$|^[a-z0-9]$")

from application.access_control import ensure_operation_allowed
from application.equipment_extraction_service import EquipmentExtractionService
from services.equipment.equipment_detector import detectar_equipamento
from services.equipment.equipment_registry import EquipmentConfig
from services.system_paths import BASE_DIR


class EquipmentProfileService:
    """Facade canonica de perfis de equipamento baseados em contratos JSON."""

    def __init__(self, *, base_dir: Optional[Path] = None) -> None:
        self.base_dir = Path(base_dir or BASE_DIR)
        self.contract_root = self.base_dir / "config" / "contracts" / "equipment"
        self.schema_path = self.base_dir / "config" / "contracts" / "schema.equipment_profile.json"
        self._extraction_service: Optional[EquipmentExtractionService] = None

    @staticmethod
    def _normalize_key(value: Any) -> str:
        return str(value or "").strip().lower()

    def _iter_profile_paths(self) -> Iterable[Path]:
        if not self.contract_root.exists():
            return []
        return sorted(
            path
            for path in self.contract_root.glob("*.json")
            if not path.name.startswith(("template", "schema"))
        )

    def _load_profile_file(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        except Exception:
            return None
        return None

    def list_profiles(self) -> list[Dict[str, Any]]:
        profiles: list[Dict[str, Any]] = []
        for path in self._iter_profile_paths():
            payload = self._load_profile_file(path)
            if payload:
                profiles.append(payload)
        profiles.sort(key=lambda item: str(item.get("equipment_id", "")).lower())
        return profiles

    def list_active_profiles(self) -> list[Dict[str, Any]]:
        return [p for p in self.list_profiles() if bool(p.get("active"))]

    def resolve_profile(self, equipment_id_or_alias: str) -> Optional[Dict[str, Any]]:
        key = self._normalize_key(equipment_id_or_alias)
        if not key:
            return None
        for profile in self.list_active_profiles():
            aliases = [self._normalize_key(item) for item in profile.get("aliases", [])]
            candidates = {
                self._normalize_key(profile.get("equipment_id")),
                self._normalize_key(profile.get("display_name")),
                self._normalize_key(profile.get("name")),
                *aliases,
            }
            if key in candidates:
                return profile
        return None

    def validate_profile(self, profile: Dict[str, Any]) -> Tuple[bool, list[str]]:
        errors: list[str] = []
        schema_required = [
            "equipment_id",
            "display_name",
            "aliases",
            "active",
            "contract_version",
            "fabricante",
            "modelo",
            "file_type",
            "signature",
            "sheet_policy",
            "row_policy",
            "column_mapping",
            "ct_policy",
            "well_policy",
            "extractor_strategy",
            "confidence_threshold",
            "validation_rules",
            "audit",
        ]
        for field in schema_required:
            if field not in profile:
                errors.append(f"campo obrigatorio ausente: {field}")

        if "aliases" in profile and not isinstance(profile.get("aliases"), list):
            errors.append("aliases deve ser lista")
        if "active" in profile and not isinstance(profile.get("active"), bool):
            errors.append("active deve ser booleano")
        if "signature" in profile and not isinstance(profile.get("signature"), dict):
            errors.append("signature deve ser objeto")
        if "column_mapping" in profile and not isinstance(profile.get("column_mapping"), dict):
            errors.append("column_mapping deve ser objeto")
        if "ct_policy" in profile and not isinstance(profile.get("ct_policy"), dict):
            errors.append("ct_policy deve ser objeto")
        if "well_policy" in profile and not isinstance(profile.get("well_policy"), dict):
            errors.append("well_policy deve ser objeto")
        if "validation_rules" in profile and not isinstance(profile.get("validation_rules"), dict):
            errors.append("validation_rules deve ser objeto")
        if "audit" in profile and not isinstance(profile.get("audit"), dict):
            errors.append("audit deve ser objeto")
        if "confidence_threshold" in profile:
            try:
                float(profile.get("confidence_threshold"))
            except Exception:
                errors.append("confidence_threshold deve ser numerico")

        equipment_id = str(profile.get("equipment_id", "") or "").strip()
        if equipment_id and not _EQUIPMENT_ID_RE.match(equipment_id):
            errors.append(
                "equipment_id invalido: use apenas letras minusculas, digitos, _ e - "
                "(sem espacos, pontos ou sequencias ../)"
            )

        sig = profile.get("signature")
        if isinstance(sig, dict):
            cols = sig.get("contains_columns")
            if not isinstance(cols, list) or len(cols) == 0:
                errors.append("signature.contains_columns deve ser lista nao vazia")

        return (len(errors) == 0), errors

    def save_profile(
        self,
        *,
        profile: Dict[str, Any],
        actor_username: str,
        actor_access_level: str,
        change_reason: str,
    ) -> Path:
        ensure_operation_allowed(
            "admin.catalog.write",
            actor_access_level,
            actor_username=actor_username,
        )

        valid, errors = self.validate_profile(profile)
        if not valid:
            raise ValueError("; ".join(errors))

        self.contract_root.mkdir(parents=True, exist_ok=True)
        equipment_id = str(profile.get("equipment_id", "")).strip()
        if not equipment_id:
            raise ValueError("equipment_id obrigatorio")

        # Garantir que o path resultante está dentro de contract_root (defesa extra).
        target = self.contract_root / f"{equipment_id}.json"
        try:
            target.resolve().relative_to(self.contract_root.resolve())
        except ValueError:
            raise ValueError(f"equipment_id invalido: path fora de contract_root: {equipment_id!r}")

        # Validar unicidade de aliases entre perfis ativos (excluindo o próprio perfil sendo salvo).
        incoming_aliases = {self._normalize_key(a) for a in profile.get("aliases", [])}
        incoming_aliases.add(self._normalize_key(equipment_id))
        incoming_aliases.add(self._normalize_key(profile.get("display_name", "")))
        for existing in self.list_active_profiles():
            if self._normalize_key(existing.get("equipment_id")) == self._normalize_key(equipment_id):
                continue  # mesmo perfil sendo atualizado
            existing_aliases = {self._normalize_key(a) for a in existing.get("aliases", [])}
            existing_aliases.add(self._normalize_key(existing.get("equipment_id")))
            existing_aliases.add(self._normalize_key(existing.get("display_name", "")))
            collision = incoming_aliases & existing_aliases - {""}
            if collision:
                raise ValueError(
                    f"Alias(es) {sorted(collision)} ja existem no perfil ativo "
                    f"{existing.get('equipment_id')!r}. Remova o conflito antes de salvar."
                )
        if target.exists():
            timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S")
            backup = target.with_name(f"{target.name}.bak.{timestamp}")
            backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")

        payload = dict(profile)
        audit = dict(payload.get("audit") or {})
        audit["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
        audit["updated_by"] = str(actor_username or "").strip()
        audit["change_reason"] = str(change_reason or "").strip()
        payload["audit"] = audit

        tmp_path = target.with_suffix(target.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(target)
        return target

    def detect_equipment(self, file_path: Path) -> Dict[str, Any]:
        return detectar_equipamento(str(file_path), active_profiles=self.list_active_profiles())

    @staticmethod
    def _int_or_default(value: Any, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _extractor_name_for_profile(profile: Dict[str, Any]) -> str:
        explicit = str(profile.get("extrator_nome") or "").strip()
        if explicit:
            return explicit
        strategy = str(profile.get("extractor_strategy") or "").strip()
        return {
            "indexed_table": "extrair_7500_extended",
            "quantstudio_table": "extrair_quantstudio",
            "legacy": "extrair_dados_equipamento",
        }.get(strategy, strategy or "extrair_7500_extended")

    def _build_equipment_config_from_profile(self, profile: Dict[str, Any]) -> EquipmentConfig:
        display_name = str(profile.get("display_name") or profile.get("equipment_id") or "").strip()
        if not display_name:
            raise ValueError("Perfil de equipamento sem identificador.")

        xlsx_estrutura = {
            "coluna_well": self._int_or_default(profile.get("coluna_well"), 0),
            "coluna_sample": self._int_or_default(profile.get("coluna_sample"), 1),
            "coluna_target": self._int_or_default(profile.get("coluna_target"), 2),
            "coluna_ct": self._int_or_default(profile.get("coluna_ct"), 3),
            "linha_inicio": self._int_or_default(profile.get("linha_inicio"), 1),
        }
        ct_policy = profile.get("ct_policy") if isinstance(profile.get("ct_policy"), dict) else {}
        return EquipmentConfig(
            nome=display_name,
            modelo=str(profile.get("modelo") or ""),
            fabricante=str(profile.get("fabricante") or ""),
            tipo_placa=str(profile.get("tipo_placa") or "96"),
            xlsx_estrutura=xlsx_estrutura,
            extrator_nome=self._extractor_name_for_profile(profile),
            formatador_nome=str(profile.get("formatador_nome") or "padrao"),
            equipment_id=str(profile.get("equipment_id") or ""),
            contract_version=str(profile.get("contract_version") or ""),
            ct_like_columns=list(profile.get("ct_like_columns") or ct_policy.get("aliases") or []),
            ct_like_blocklist=list(profile.get("ct_like_blocklist") or ct_policy.get("blocklist") or []),
        )

    def extract_results(self, file_path: Path, profile: Dict[str, Any]):
        display_name = str(profile.get("display_name") or profile.get("equipment_id") or "").strip()
        if not display_name:
            raise ValueError("Perfil de equipamento sem identificador.")
        if not bool(profile.get("active")):
            raise ValueError(f"Equipamento inativo: {display_name}")

        config = self._build_equipment_config_from_profile(profile)

        if self._extraction_service is None:
            self._extraction_service = EquipmentExtractionService()
        return self._extraction_service.extract_results(Path(file_path), config)
