"""Catalogo de contratos de runtime (fase 1).

Objetivo:
- formalizar perfis de exame/equipamento/regras/GAL/storage;
- aplicar hierarquia unica de resolucao de configuracao;
- manter compatibilidade com fontes legadas durante transicao.
"""

from __future__ import annotations

import csv
import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from services.core.config_service import config_service
from services.path_resolver import resolve_banco_dir
from services.system_paths import BASE_DIR
from utils.logger import registrar_log
from utils.network_io import RetryPolicy, open_with_retry, path_exists_with_retry

_DEFAULT_HIERARCHY = ["contracts", "config_exams", "config_json", "csv"]
_SCHEMA_BY_PROFILE_KIND = {
    "exam_profile": "schema.exam_profile.json",
    "equipment_profile": "schema.equipment_profile.json",
    "analysis_rules_profile": "schema.analysis_rules_profile.json",
    "gal_profile": "schema.gal_profile.json",
    "storage_profile": "schema.storage_profile.json",
}
_PROFILE_LOADERS = {
    "exam_profile": ("exams", ("exam_id", "slug", "nome_exame")),
    "equipment_profile": ("equipment", ("equipment_id", "name", "display_name")),
    "analysis_rules_profile": ("analysis_rules", ("profile_id", "id", "protocol_id")),
    "gal_profile": ("gal", ("profile_id", "id", "exam_id")),
    "storage_profile": ("storage", ("profile_id", "id", "name")),
}


def _normalize_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.replace("_", " ").split())


def _slug(value: Any) -> str:
    return _normalize_key(value).replace(" ", "_")


def _safe_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


@dataclass(frozen=True)
class RuntimeContractBundle:
    exam_profile: Dict[str, Any]
    equipment_profile: Dict[str, Any]
    analysis_rules_profile: Dict[str, Any]
    gal_profile: Dict[str, Any]
    storage_profile: Dict[str, Any]
    versions: Dict[str, str]


class ContractCatalog:
    """Carrega e resolve contratos de runtime com fallback legada."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = Path(base_dir or BASE_DIR)
        self.contract_root = self.base_dir / "config" / "contracts"
        self.hierarchy = self._resolve_hierarchy()
        self.exam_profiles: Dict[str, Dict[str, Any]] = {}
        self.equipment_profiles: Dict[str, Dict[str, Any]] = {}
        self.analysis_rules_profiles: Dict[str, Dict[str, Any]] = {}
        self.gal_profiles: Dict[str, Dict[str, Any]] = {}
        self.storage_profiles: Dict[str, Dict[str, Any]] = {}
        self.load()

    def _resolve_hierarchy(self) -> list[str]:
        cfg = config_service.get("contracts", {}) or {}
        hierarchy = cfg.get("hierarchy", _DEFAULT_HIERARCHY)
        if not isinstance(hierarchy, list):
            return list(_DEFAULT_HIERARCHY)
        normalized = []
        for item in hierarchy:
            token = str(item).strip().lower()
            if token in _DEFAULT_HIERARCHY and token not in normalized:
                normalized.append(token)
        for default in _DEFAULT_HIERARCHY:
            if default not in normalized:
                normalized.append(default)
        return normalized

    def load(self) -> None:
        self.hierarchy = self._resolve_hierarchy()
        self.exam_profiles = self._build_exam_profiles()
        self.equipment_profiles = self._build_equipment_profiles()
        self.analysis_rules_profiles = self._build_analysis_rules_profiles()
        self.gal_profiles = self._build_gal_profiles()
        self.storage_profiles = self._build_storage_profiles()

    def list_exam_profiles(self) -> Dict[str, Dict[str, Any]]:
        return dict(self.exam_profiles)

    def list_equipment_profiles(self) -> Dict[str, Dict[str, Any]]:
        return dict(self.equipment_profiles)

    def get_exam_profile(self, exam_name: Any) -> Optional[Dict[str, Any]]:
        key = _normalize_key(exam_name)
        if not key:
            return None
        source_rank = {name: idx for idx, name in enumerate(self.hierarchy)}
        best_profile: Optional[Dict[str, Any]] = None
        best_rank = len(self.hierarchy) + 1
        candidates = []
        direct = self.exam_profiles.get(key)
        if direct:
            candidates.append(direct)
        slug_match = self.exam_profiles.get(_normalize_key(str(exam_name).replace("_", " ")))
        if slug_match:
            candidates.append(slug_match)
        candidates.extend(self.exam_profiles.values())
        for profile in candidates:
            exam_id = _normalize_key(profile.get("exam_id", ""))
            slug = _normalize_key(str(profile.get("slug", "")).replace("_", " "))
            nome_exame = _normalize_key(profile.get("nome_exame", ""))
            if key in {exam_id, slug, nome_exame}:
                rank = source_rank.get(
                    str(profile.get("source_of_truth", "")).strip().lower(),
                    len(self.hierarchy),
                )
                if rank < best_rank:
                    best_profile = dict(profile)
                    best_rank = rank
        return best_profile

    def get_equipment_profile(self, equipment_name: Any) -> Optional[Dict[str, Any]]:
        key = _normalize_key(equipment_name)
        if not key:
            return None
        source_rank = {name: idx for idx, name in enumerate(self.hierarchy)}
        best_profile: Optional[Dict[str, Any]] = None
        best_rank = len(self.hierarchy) + 1
        candidates = []
        direct = self.equipment_profiles.get(key)
        if direct:
            candidates.append(direct)
        candidates.extend(self.equipment_profiles.values())
        for profile in candidates:
            equipment_id = _normalize_key(profile.get("equipment_id", ""))
            name = _normalize_key(profile.get("name", ""))
            display_name = _normalize_key(profile.get("display_name", ""))
            aliases = {
                _normalize_key(alias)
                for alias in _safe_list(profile.get("aliases"))
                if _normalize_key(alias)
            }
            if key in {equipment_id, name, display_name, *aliases}:
                rank = source_rank.get(
                    str(profile.get("source_of_truth", "")).strip().lower(),
                    len(self.hierarchy),
                )
                if rank < best_rank:
                    best_profile = dict(profile)
                    best_rank = rank
        return best_profile

    def list_active_equipment_profiles(self) -> Dict[str, Dict[str, Any]]:
        return {
            key: dict(profile)
            for key, profile in self.equipment_profiles.items()
            if bool(profile.get("active"))
        }

    def get_analysis_rules_profile(self, profile_id: Any) -> Optional[Dict[str, Any]]:
        key = _normalize_key(profile_id)
        if not key:
            return None
        value = self.analysis_rules_profiles.get(key)
        return dict(value) if value else None

    def get_gal_profile(self, profile_id: Any) -> Optional[Dict[str, Any]]:
        key = _normalize_key(profile_id)
        if not key:
            return None
        value = self.gal_profiles.get(key)
        return dict(value) if value else None

    def get_storage_profile(self, profile_id: Any) -> Optional[Dict[str, Any]]:
        key = _normalize_key(profile_id)
        if not key:
            return None
        value = self.storage_profiles.get(key)
        return dict(value) if value else None

    def resolve_runtime_bundle(
        self,
        *,
        exam_name: Any,
        equipment_name: Any = None,
    ) -> RuntimeContractBundle:
        exam = self.get_exam_profile(exam_name) or {}
        equipment_key = equipment_name or exam.get("equipment_id") or exam.get("equipamento")
        equipment = self.get_equipment_profile(equipment_key) or {}

        rules_key = exam.get("analysis_rules_profile_id") or exam.get("exam_id") or exam_name
        gal_key = exam.get("gal_profile_id") or exam.get("exam_id") or exam_name
        storage_key = exam.get("storage_profile_id") or "default"

        rules = self.get_analysis_rules_profile(rules_key) or {}
        gal = self.get_gal_profile(gal_key) or {}
        storage = self.get_storage_profile(storage_key) or {}

        versions = {
            "exam_profile": str(exam.get("contract_version", "")),
            "equipment_profile": str(equipment.get("contract_version", "")),
            "analysis_rules_profile": str(rules.get("contract_version", "")),
            "gal_profile": str(gal.get("contract_version", "")),
            "storage_profile": str(storage.get("contract_version", "")),
        }
        return RuntimeContractBundle(
            exam_profile=exam,
            equipment_profile=equipment,
            analysis_rules_profile=rules,
            gal_profile=gal,
            storage_profile=storage,
            versions=versions,
        )

    @staticmethod
    def _derive_group_size(esquema_agrupamento: Any, pocos_por_amostra: Any) -> int:
        explicit = _safe_int(pocos_por_amostra, 0)
        if explicit > 0:
            return explicit
        raw = str(esquema_agrupamento or "").strip()
        if "->" in raw:
            left, right = raw.split("->", 1)
            orig = _safe_int(left, 0)
            dest = _safe_int(right, 0)
            if orig > 0 and dest > 0:
                return max(1, orig // dest)
        return 1

    def resolve_analysis_contract_decision(
        self,
        *,
        exam_name: Any,
        equipment_name: Any = None,
    ) -> Dict[str, Any]:
        """
        Resolve a decisao canonica para agrupamento/tabela/mapa/regras por exame.

        Mantem fallback deterministico para legado quando contrato do exame estiver ausente.
        """
        bundle = self.resolve_runtime_bundle(exam_name=exam_name, equipment_name=equipment_name)
        exam_profile = dict(bundle.exam_profile or {})
        source_of_truth = str(exam_profile.get("source_of_truth", "")).strip().lower()
        exam_id = str(exam_profile.get("exam_id", "")).strip()

        if source_of_truth and exam_id:
            esquema = str(exam_profile.get("esquema_agrupamento", "")).strip() or "96->96"
            pocos = _safe_int(exam_profile.get("pocos_por_amostra"), 0)
            group_size = self._derive_group_size(esquema, pocos)
            targets_por_poco = [
                item
                for item in _safe_list(exam_profile.get("targets_por_poco", []))
                if isinstance(item, dict)
            ]
            limiares = [
                item
                for item in _safe_list(exam_profile.get("limiares_ct_por_alvo_poco", []))
                if isinstance(item, dict)
            ]
            fallback_mode = "registry_contract"
            fallback_reason = ""
        else:
            source_of_truth = "legacy_builtin_rules"
            exam_id = ""
            esquema = "96->96"
            pocos = 1
            group_size = 1
            targets_por_poco = []
            limiares = []
            fallback_mode = "legacy_builtin_rules"
            fallback_reason = "missing_exam_contract"

        return {
            "exam_name": str(exam_name or ""),
            "exam_id": exam_id,
            "source_of_truth": source_of_truth,
            "esquema_agrupamento": esquema,
            "pocos_por_amostra": pocos,
            "group_size": group_size,
            "targets_por_poco": targets_por_poco,
            "limiares_ct_por_alvo_poco": limiares,
            "parity_contract": {
                "table_columns": "exam_selected_contract",
                "plate_map": "exam_selected_contract",
                "rules": "exam_selected_contract",
                "required_consistency_fields": [
                    "esquema_agrupamento",
                    "pocos_por_amostra",
                    "targets_por_poco",
                    "limiares_ct_por_alvo_poco",
                ],
            },
            "fallback_mode": fallback_mode,
            "fallback_reason": fallback_reason,
        }

    def _build_exam_profiles(self) -> Dict[str, Dict[str, Any]]:
        sources = {
            "contracts": self._load_exam_profiles_from_contracts(),
            "config_exams": self._load_exam_profiles_from_config_exams(),
            "config_json": self._load_exam_profiles_from_config_json(),
            "csv": self._load_exam_profiles_from_csv(),
        }
        return self._merge_by_hierarchy(sources)

    def _build_equipment_profiles(self) -> Dict[str, Dict[str, Any]]:
        sources = {
            "contracts": self._load_equipment_profiles_from_contracts(),
            "config_exams": {},
            "config_json": self._load_equipment_profiles_from_config_json(),
            "csv": self._load_equipment_profiles_from_csv(),
        }
        return self._merge_by_hierarchy(sources)

    def _build_analysis_rules_profiles(self) -> Dict[str, Dict[str, Any]]:
        profile_map = self._load_profiles_from_folder("analysis_rules", id_keys=("profile_id", "id", "protocol_id"))
        if profile_map:
            return profile_map
        legacy_path = resolve_banco_dir() / "protocols" / "analysis_rules.json"
        for item in self._read_json_list(legacy_path):
            key = _normalize_key(item.get("protocol_id") or item.get("id"))
            if not key:
                continue
            profile_map[key] = {
                "profile_id": item.get("protocol_id") or item.get("id"),
                "contract_version": "legacy-v1",
                "rules": item.get("rules", []),
            }
        return profile_map

    def _build_gal_profiles(self) -> Dict[str, Dict[str, Any]]:
        profile_map = self._load_profiles_from_folder("gal", id_keys=("profile_id", "id", "exam_id"))
        if profile_map:
            return profile_map
        for profile in self.exam_profiles.values():
            key = _normalize_key(profile.get("exam_id") or profile.get("slug") or profile.get("nome_exame"))
            if not key:
                continue
            profile_map[key] = {
                "profile_id": profile.get("gal_profile_id") or profile.get("exam_id") or profile.get("slug"),
                "contract_version": "legacy-v1",
                "encoding": "utf-8",
                "export_fields": _safe_list(profile.get("export_fields")),
            }
        return profile_map

    def _build_storage_profiles(self) -> Dict[str, Dict[str, Any]]:
        profile_map = self._load_profiles_from_folder("storage", id_keys=("profile_id", "id", "name"))
        if profile_map:
            return profile_map
        profile_map["default"] = {
            "profile_id": "default",
            "contract_version": "legacy-v1",
            "encoding": "utf-8",
            "dedupe_keys": ["corrida_id", "amostra_codigo", "lote", "data_exame"],
            "retry_enabled": True,
            "lock_enabled": True,
        }
        return profile_map

    def _merge_by_hierarchy(
        self,
        source_maps: Dict[str, Dict[str, Dict[str, Any]]],
    ) -> Dict[str, Dict[str, Any]]:
        merged: Dict[str, Dict[str, Any]] = {}
        for source_name in reversed(self.hierarchy):
            data = source_maps.get(source_name, {})
            for key, profile in data.items():
                current = merged.setdefault(key, {})
                current.update(profile)
                current["source_of_truth"] = source_name
        return merged

    def _load_profiles_from_folder(
        self,
        folder: str,
        *,
        id_keys: Iterable[str],
    ) -> Dict[str, Dict[str, Any]]:
        profiles: Dict[str, Dict[str, Any]] = {}
        target = self.contract_root / folder
        if not target.exists():
            return profiles

        for path in target.glob("*.json"):
            # Arquivos de esquema/template nao fazem parte do runtime.
            if path.name.startswith(("template", "schema")):
                continue
            payload = self._read_json_obj(path)
            if not payload:
                continue
            key_value = ""
            for id_key in id_keys:
                if payload.get(id_key):
                    key_value = str(payload.get(id_key))
                    break
            if not key_value:
                key_value = path.stem
            profiles[_normalize_key(key_value)] = payload
        return profiles

    def _load_exam_profiles_from_contracts(self) -> Dict[str, Dict[str, Any]]:
        return self._load_profiles_from_folder("exams", id_keys=("exam_id", "slug", "nome_exame"))

    def _load_equipment_profiles_from_contracts(self) -> Dict[str, Dict[str, Any]]:
        return self._load_profiles_from_folder("equipment", id_keys=("equipment_id", "name", "display_name"))

    def _load_exam_profiles_from_config_exams(self) -> Dict[str, Dict[str, Any]]:
        profiles: Dict[str, Dict[str, Any]] = {}
        folder = self.base_dir / "config" / "exams"
        if not folder.exists():
            return profiles
        for path in folder.glob("*.json"):
            if path.name.startswith(("schema", "template")):
                continue
            payload = self._read_json_obj(path)
            if not payload:
                continue
            nome = payload.get("nome_exame") or payload.get("exame") or path.stem
            key = _normalize_key(nome)
            if not key:
                continue
            profiles[key] = {
                "exam_id": payload.get("exam_id") or _slug(payload.get("slug") or nome),
                "nome_exame": nome,
                "slug": payload.get("slug") or _slug(nome),
                "equipment_id": payload.get("equipment_id") or payload.get("equipamento", ""),
                "tipo_placa_analitica": payload.get("tipo_placa_analitica", ""),
                "esquema_agrupamento": payload.get("esquema_agrupamento", ""),
                "targets": _safe_list(payload.get("alvos")),
                "target_aliases": _safe_dict(payload.get("mapa_alvos")),
                "ct_thresholds": _safe_dict(payload.get("faixas_ct")),
                "rp_targets": _safe_list(payload.get("rps")),
                "pocos_por_amostra": _safe_int(payload.get("pocos_por_amostra"), 0),
                "targets_por_poco": [
                    item for item in _safe_list(payload.get("targets_por_poco", [])) if isinstance(item, dict)
                ],
                "limiares_ct_por_alvo_poco": [
                    item
                    for item in _safe_list(payload.get("limiares_ct_por_alvo_poco", []))
                    if isinstance(item, dict)
                ],
                "export_fields": _safe_list(payload.get("export_fields")),
                "panel_tests_id": str(payload.get("panel_tests_id", "")),
                "contract_version": payload.get("contract_version") or payload.get("versao_protocolo") or "config-exams-v1",
                "analysis_rules_profile_id": payload.get("analysis_rules_profile_id") or _slug(nome),
                "gal_profile_id": payload.get("gal_profile_id") or _slug(nome),
                "storage_profile_id": payload.get("storage_profile_id") or "default",
            }
        return profiles

    def _load_exam_profiles_from_config_json(self) -> Dict[str, Dict[str, Any]]:
        profiles: Dict[str, Dict[str, Any]] = {}
        exams_cfg = config_service.get("exams", {}) or {}
        configs = exams_cfg.get("configs", {})
        if not isinstance(configs, dict):
            return profiles
        for exam_name, payload in configs.items():
            data = payload if isinstance(payload, dict) else {}
            key = _normalize_key(exam_name)
            if not key:
                continue
            profiles[key] = {
                "exam_id": data.get("exam_id") or _slug(exam_name),
                "nome_exame": data.get("nome_exame") or exam_name,
                "slug": data.get("slug") or _slug(exam_name),
                "equipment_id": data.get("equipment_id") or data.get("equipamento", ""),
                "tipo_placa_analitica": data.get("tipo_placa_analitica", ""),
                "esquema_agrupamento": data.get("esquema_agrupamento", ""),
                "targets": _safe_list(data.get("alvos", [])),
                "target_aliases": _safe_dict(data.get("mapa_alvos", {})),
                "ct_thresholds": _safe_dict(data.get("faixas_ct", {})),
                "rp_targets": _safe_list(data.get("rps", [])),
                "pocos_por_amostra": _safe_int(data.get("pocos_por_amostra"), 0),
                "targets_por_poco": [
                    item for item in _safe_list(data.get("targets_por_poco", [])) if isinstance(item, dict)
                ],
                "limiares_ct_por_alvo_poco": [
                    item
                    for item in _safe_list(data.get("limiares_ct_por_alvo_poco", []))
                    if isinstance(item, dict)
                ],
                "export_fields": _safe_list(data.get("export_fields", [])),
                "panel_tests_id": str(data.get("panel_tests_id", "")),
                "contract_version": data.get("contract_version", "config-json-v1"),
                "analysis_rules_profile_id": data.get("analysis_rules_profile_id") or _slug(exam_name),
                "gal_profile_id": data.get("gal_profile_id") or _slug(exam_name),
                "storage_profile_id": data.get("storage_profile_id") or "default",
            }
        return profiles

    def _load_exam_profiles_from_csv(self) -> Dict[str, Dict[str, Any]]:
        profiles: Dict[str, Dict[str, Any]] = {}
        banco_dir = resolve_banco_dir()
        for row in self._read_csv_rows(banco_dir / "exames_config.csv"):
            nome = row.get("exame", "")
            key = _normalize_key(nome)
            if not key:
                continue
            profiles[key] = {
                "exam_id": _slug(nome),
                "nome_exame": nome,
                "slug": _slug(nome),
                "equipment_id": row.get("equipamento", ""),
                "tipo_placa_analitica": row.get("tipo_placa", ""),
                "esquema_agrupamento": "",
                "targets": [],
                "target_aliases": {},
                "ct_thresholds": {},
                "rp_targets": ["RP_1", "RP_2"],
                "pocos_por_amostra": 0,
                "targets_por_poco": [],
                "limiares_ct_por_alvo_poco": [],
                "export_fields": [],
                "panel_tests_id": "",
                "contract_version": "csv-v1",
                "analysis_rules_profile_id": _slug(nome),
                "gal_profile_id": _slug(nome),
                "storage_profile_id": "default",
            }
        return profiles

    def _load_equipment_profiles_from_config_json(self) -> Dict[str, Dict[str, Any]]:
        profiles: Dict[str, Dict[str, Any]] = {}
        extracao_cfg = config_service.get("extracao", {}) or {}
        default_name = extracao_cfg.get("equipamento_padrao")
        if default_name:
            key = _normalize_key(default_name)
            profiles[key] = {
                "equipment_id": _slug(default_name),
                "name": default_name,
                "display_name": default_name,
                "contract_version": "config-json-v1",
                "ct_like_columns": ["Ct", "Cq", "C(t)", "Cт"],
                "ct_like_blocklist": ["Ct Mean", "Cq Mean", "Cq SD", "Cq Confidence"],
            }
        return profiles

    def _load_equipment_profiles_from_csv(self) -> Dict[str, Dict[str, Any]]:
        profiles: Dict[str, Dict[str, Any]] = {}
        banco_dir = resolve_banco_dir()
        metadata_rows = self._read_csv_rows(banco_dir / "equipamentos_metadata.csv")
        for row in metadata_rows:
            nome = row.get("equipamento", "")
            key = _normalize_key(nome)
            if not key:
                continue
            profiles[key] = {
                "equipment_id": _slug(nome),
                "name": nome,
                "display_name": nome,
                "contract_version": "csv-v1",
                "file_type": row.get("tipo_arquivo", ""),
                "column_mapping": {
                    "well": row.get("coluna_poco", ""),
                    "sample": row.get("coluna_amostra", ""),
                    "target": row.get("coluna_alvo", ""),
                    "ct": row.get("coluna_ct", ""),
                },
                "ct_like_columns": ["Ct", "Cq", "C(t)", "Cт"],
                "ct_like_blocklist": ["Ct Mean", "Cq Mean", "Cq SD", "Cq Confidence"],
            }
        if profiles:
            return profiles
        for row in self._read_csv_rows(banco_dir / "equipamentos.csv"):
            nome = row.get("nome", "")
            key = _normalize_key(nome)
            if not key:
                continue
            profiles[key] = {
                "equipment_id": _slug(nome),
                "name": nome,
                "display_name": nome,
                "contract_version": "csv-v1",
                "ct_like_columns": ["Ct", "Cq", "C(t)", "Cт"],
                "ct_like_blocklist": ["Ct Mean", "Cq Mean", "Cq SD", "Cq Confidence"],
            }
        return profiles

    def _read_json_obj(self, path: Path) -> Dict[str, Any]:
        policy = RetryPolicy.from_env()
        if not path_exists_with_retry(path, policy=policy):
            return {}
        try:
            with open_with_retry(path, "r", encoding="utf-8", policy=policy) as handle:
                payload = json.load(handle)
                return payload if isinstance(payload, dict) else {}
        except Exception as exc:
            registrar_log("ContractCatalog", f"Erro ao ler JSON {path.name}: {exc}", "ERROR")
            return {}

    def _read_json_list(self, path: Path) -> list[dict[str, Any]]:
        policy = RetryPolicy.from_env()
        if not path_exists_with_retry(path, policy=policy):
            return []
        try:
            with open_with_retry(path, "r", encoding="utf-8", policy=policy) as handle:
                payload = json.load(handle)
                if isinstance(payload, list):
                    return [item for item in payload if isinstance(item, dict)]
                return []
        except Exception as exc:
            registrar_log("ContractCatalog", f"Erro ao ler JSON list {path.name}: {exc}", "ERROR")
            return []

    def _read_csv_rows(self, path: Path) -> list[dict[str, Any]]:
        policy = RetryPolicy.from_env()
        if not path_exists_with_retry(path, policy=policy):
            return []
        try:
            with open_with_retry(path, "r", encoding="utf-8", policy=policy) as handle:
                reader = csv.DictReader(handle)
                return [dict(row) for row in reader]
        except Exception as exc:
            registrar_log("ContractCatalog", f"Erro ao ler CSV {path.name}: {exc}", "ERROR")
            return []

    def validate_contract_files(self) -> list[dict[str, Any]]:
        """
        Valida perfis de contrato em `config/contracts/*` contra os schemas locais.

        Retorna lista vazia quando todos os perfis encontrados estao conformes.
        Durante a transicao, tipos de perfil sem schema ou sem perfis ativos sao ignorados.
        """

        issues: list[dict[str, Any]] = []
        for kind, schema_name in _SCHEMA_BY_PROFILE_KIND.items():
            schema = self._read_json_obj(self.contract_root / schema_name)
            if not schema:
                continue

            folder, id_keys = _PROFILE_LOADERS[kind]
            profiles = self._load_profiles_from_folder(folder, id_keys=id_keys)
            for profile_key, payload in profiles.items():
                issues.extend(
                    self._validate_payload_against_schema(
                        profile_kind=kind,
                        profile_key=profile_key,
                        payload=payload,
                        schema=schema,
                    )
                )
        return issues

    def _validate_payload_against_schema(
        self,
        *,
        profile_kind: str,
        profile_key: str,
        payload: Dict[str, Any],
        schema: Dict[str, Any],
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        required_fields = schema.get("required", [])
        if isinstance(required_fields, list):
            for field in required_fields:
                if field not in payload:
                    issues.append(
                        {
                            "profile_kind": profile_kind,
                            "profile_key": profile_key,
                            "field": str(field),
                            "issue": "missing_required",
                        }
                    )

        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            return issues

        for field, meta in properties.items():
            if field not in payload or not isinstance(meta, dict):
                continue
            expected_type = str(meta.get("type", "")).strip().lower()
            if not expected_type:
                continue
            if not self._matches_json_type(payload[field], expected_type):
                issues.append(
                    {
                        "profile_kind": profile_kind,
                        "profile_key": profile_key,
                        "field": str(field),
                        "issue": "type_mismatch",
                        "expected": expected_type,
                        "actual": type(payload[field]).__name__,
                    }
                )
        return issues

    @staticmethod
    def _matches_json_type(value: Any, expected_type: str) -> bool:
        if expected_type == "string":
            return isinstance(value, str)
        if expected_type == "array":
            return isinstance(value, list)
        if expected_type == "object":
            return isinstance(value, dict)
        if expected_type == "boolean":
            return isinstance(value, bool)
        if expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        return True


_catalog_instance: Optional[ContractCatalog] = None


def get_contract_catalog(*, reload: bool = False) -> ContractCatalog:
    global _catalog_instance
    if _catalog_instance is None:
        _catalog_instance = ContractCatalog()
    if reload:
        _catalog_instance.load()
    return _catalog_instance
