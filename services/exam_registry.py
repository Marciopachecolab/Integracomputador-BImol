"""

ExamRegistry híbrido: consolida metadados de exames a partir dos CSVs da pasta

`banco/` e, quando houver, sobrescreve/complementa com arquivos JSON/YAML em

`config/exams/`.



Campos expostos por exame (ExamConfig):

    nome_exame, slug, equipamento,

    tipo_placa_analitica, esquema_agrupamento, kit_codigo,

    alvos, mapa_alvos, faixas_ct, rps,

    export_fields, panel_tests_id, controles,

    comentarios, versao_protocolo.



Regras de merge:

    - Carrega todos os exames dos CSVs (base mínima).

    - Se existir JSON/YAML em config/exams/ com o mesmo nome_exame/slug, ele

      sobrescreve/complementa os dados do CSV.

    - Helpers para normalizar target_name e descobrir o tamanho de bloco a partir

      do esquema_agrupamento (ex.: 96->48 => bloco 2; 96->36 => bloco 3).

"""



from __future__ import annotations



import json

from dataclasses import dataclass, field

from pathlib import Path

from typing import Any, Dict, List, Optional

from services.contract_catalog import get_contract_catalog
from services.core.config_service import config_service
from services.path_resolver import resolve_banco_dir
from utils.logger import registrar_log
from utils.network_io import RetryPolicy, call_with_retry, open_with_retry, path_exists_with_retry


try:

    import yaml  # type: ignore

    HAS_YAML = True

except Exception:

    HAS_YAML = False



BASE_DIR = Path(__file__).resolve().parent.parent

EXAMS_DIR = BASE_DIR / "config" / "exams"


def _banco_dir() -> Path:
    """Resolve o diretorio base dos CSVs de exame."""
    return resolve_banco_dir()





def _norm_exame(nome: str) -> str:

    """Normaliza nome do exame: lowercase, remove acentos, strip"""

    import unicodedata

    

    # Strip e lowercase

    normalized = str(nome).strip().lower()

    

    # Remover acentos (NFKD + ASCII)

    normalized = unicodedata.normalize('NFKD', normalized)

    normalized = normalized.encode('ASCII', 'ignore').decode('ASCII')

    

    return normalized





def _safe_float(val: Any, default: float) -> float:

    try:

        return float(val)

    except Exception:

        return default


def _safe_int(val: Any, default: int) -> int:
    try:
        return int(val)
    except Exception:
        return default


def _safe_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}





@dataclass

class ExamConfig:

    nome_exame: str

    slug: str

    equipamento: str

    tipo_placa_analitica: str

    esquema_agrupamento: str

    kit_codigo: Any

    alvos: List[str] = field(default_factory=list)

    mapa_alvos: Dict[str, str] = field(default_factory=dict)

    faixas_ct: Dict[str, float] = field(default_factory=dict)

    rps: List[str] = field(default_factory=list)

    export_fields: List[str] = field(default_factory=list)

    panel_tests_id: str = ""

    gal_exame_codigo: str = ""

    controles: Dict[str, List[str]] = field(default_factory=lambda: {"cn": [], "cp": []})

    comentarios: str = ""

    versao_protocolo: str = ""

    exam_id: str = ""

    equipment_id: str = ""

    analysis_rules_profile_id: str = ""

    gal_profile_id: str = ""

    storage_profile_id: str = ""
    pocos_por_amostra: int = 1
    targets_por_poco: List[Dict[str, Any]] = field(default_factory=list)
    limiares_ct_por_alvo_poco: List[Dict[str, Any]] = field(default_factory=list)



    def normalize_target(self, name: str) -> str:

        s = str(name).strip().upper().replace("_", " ").replace("-", " ")

        # aplica mapa_alvos se existir chave normalizada

        for k, v in self.mapa_alvos.items():

            if s == str(k).strip().upper().replace("_", " ").replace("-", " "):

                return str(v).strip()

        return s



    def bloco_size(self) -> int:

        try:

            parts = self.esquema_agrupamento.split("->")

            if len(parts) == 2:

                orig = int(parts[0])

                dest = int(parts[1])

                if orig and dest:

                    return max(1, orig // dest)

        except Exception:

            pass

        return 1





class ExamRegistry:

    def __init__(self) -> None:

        self.exams: Dict[str, ExamConfig] = {}
        self.active_exams: List[str] = []



    def load(self) -> None:
        # Limpar cache anterior
        self.exams.clear()
        self.active_exams = []

        sources: Dict[str, Dict[str, ExamConfig]] = {
            "csv": self._load_from_csv(),
            "config_json": self._load_from_config_service(),
            "config_exams": self._load_from_json(),
            "contracts": self._load_from_contract_catalog(),
        }
        hierarchy = config_service.get_contract_hierarchy()

        merged: Dict[str, ExamConfig] = {}
        for source_name in reversed(hierarchy):
            source_data = sources.get(source_name, {})
            for key, cfg in source_data.items():
                if key not in merged:
                    merged[key] = cfg
                else:
                    merged[key] = self._merge_configs(merged[key], cfg)

        self.exams = merged

    def get(self, nome_exame: str) -> Optional[ExamConfig]:

        return self.exams.get(_norm_exame(nome_exame))

    def get_active_exams(self) -> List[str]:

        return list(self.active_exams)

    def is_active(self, nome_exame: str) -> bool:
        """Retorna True se o exame estiver na lista de ativos (config.json active_exams)."""
        if not self.active_exams:
            return False
        return _norm_exame(nome_exame) in self.active_exams

    def iter_active_exams(self):
        """Itera sobre os ExamConfig cujo nome_exame esta na lista de ativos."""
        for cfg in self.exams.values():
            if self.is_active(str(getattr(cfg, "nome_exame", ""))):
                yield cfg



    # ------------------------------------------------------------------ #

    # Carregamento dos CSVs                                              #

    # ------------------------------------------------------------------ #

    def _load_from_csv(self) -> Dict[str, ExamConfig]:

        exams: Dict[str, ExamConfig] = {}

        banco_dir = _banco_dir()
        cfg_rows = self._read_csv(banco_dir / "exames_config.csv")

        meta_rows = self._read_csv(banco_dir / "exames_metadata.csv")

        regras_rows = self._read_csv(banco_dir / "regras_analise_metadata.csv")



        meta_idx = {_norm_exame(r.get("exame", "")): r for r in meta_rows}

        regras_idx = {_norm_exame(r.get("exame", "")): r for r in regras_rows}



        for row in cfg_rows:

            nome = row.get("exame", "")

            key = _norm_exame(nome)

            meta = meta_idx.get(key, {})

            regras = regras_idx.get(key, {})



            tipo_placa = str(row.get("tipo_placa", meta.get("tipo_placa", ""))).strip()

            equipamento = str(row.get("equipamento", meta.get("equipamento", ""))).strip()

            kit_codigo = row.get("numero_kit", meta.get("numero_kit", ""))



            alvos = []

            mapa_alvos = {}

            faixas_ct = {}

            rps = []

            export_fields = []

            panel_tests_id = ""

            controles = {"cn": [], "cp": []}



            alvos_str = regras.get("alvos", "")

            if alvos_str:

                alvos = [a.strip() for a in str(alvos_str).split(";") if a.strip()]

            faixas_ct = {

                "detect_max": _safe_float(regras.get("CT_DETECTAVEL_MAX", 38.0), 38.0),

                "inconc_min": _safe_float(regras.get("CT_INCONCLUSIVO_MIN", 38.01), 38.01),

                "inconc_max": _safe_float(regras.get("CT_INCONCLUSIVO_MAX", 40.0), 40.0),

                "rp_min": _safe_float(regras.get("CT_RP_MIN", 15.0), 15.0),

                "rp_max": _safe_float(regras.get("CT_RP_MAX", 35.0), 35.0),

            }



            cfg = ExamConfig(

                nome_exame=nome,

                slug=_norm_exame(nome).replace(" ", "_"),

                equipamento=equipamento,

                tipo_placa_analitica=tipo_placa,

                esquema_agrupamento="",

                kit_codigo=kit_codigo,

                alvos=alvos,

                mapa_alvos=mapa_alvos,

                faixas_ct=faixas_ct,

                rps=rps,

                export_fields=export_fields,

                panel_tests_id=panel_tests_id,

                controles=controles,

                exam_id=_norm_exame(nome).replace(" ", "_"),

                equipment_id=equipamento,

                analysis_rules_profile_id=_norm_exame(nome).replace(" ", "_"),

                gal_profile_id=_norm_exame(nome).replace(" ", "_"),

                storage_profile_id="default",

            )

            exams[key] = cfg



        return exams



    def _load_from_config_service(self) -> Dict[str, ExamConfig]:

        exams_cfg = config_service.get("exams", {}) or {}

        configs = exams_cfg.get("configs", {}) or {}

        active = exams_cfg.get("active_exams", []) or []

        self.active_exams = [
            _norm_exame(item)
            for item in active
            if str(item).strip()
        ]

        if not isinstance(configs, dict):
            return {}

        def _as_list(value):
            if value is None:
                return []
            if isinstance(value, list):
                return value
            return [value]

        def _as_dict(value):
            return value if isinstance(value, dict) else {}

        exams: Dict[str, ExamConfig] = {}

        for nome, data in configs.items():
            if not isinstance(data, dict):
                data = {}
            nome_exame = data.get("nome_exame") or data.get("exame") or nome
            key = _norm_exame(nome_exame)
            cfg = ExamConfig(
                nome_exame=nome_exame,
                slug=str(data.get("slug", key.replace(" ", "_"))),
                equipamento=str(data.get("equipamento", "")).strip(),
                tipo_placa_analitica=str(
                    data.get("tipo_placa_analitica", data.get("tipo_placa", ""))
                ).strip(),
                esquema_agrupamento=str(data.get("esquema_agrupamento", "")).strip(),
                kit_codigo=data.get("kit_codigo", ""),
                alvos=_as_list(data.get("alvos", [])),
                mapa_alvos=_as_dict(data.get("mapa_alvos", {})),
                faixas_ct=_as_dict(data.get("faixas_ct", {})),
                rps=_as_list(data.get("rps", [])),
                export_fields=_as_list(data.get("export_fields", [])),
                panel_tests_id=str(data.get("panel_tests_id", "")).strip(),
                gal_exame_codigo=str(data.get("gal_exame_codigo", "")).strip(),
                controles=_as_dict(data.get("controles", {"cn": [], "cp": []})),
                comentarios=str(data.get("comentarios", "")),
                versao_protocolo=str(data.get("versao_protocolo", "")),
                exam_id=str(data.get("exam_id", "")),
                equipment_id=str(data.get("equipment_id", "")),
                analysis_rules_profile_id=str(data.get("analysis_rules_profile_id", "")),
                gal_profile_id=str(data.get("gal_profile_id", "")),
                storage_profile_id=str(data.get("storage_profile_id", "")),
                pocos_por_amostra=_safe_int(data.get("pocos_por_amostra", 1), 1),
                targets_por_poco=_as_list(data.get("targets_por_poco", [])),
                limiares_ct_por_alvo_poco=_as_list(data.get("limiares_ct_por_alvo_poco", [])),
            )
            exams[key] = cfg

        return exams

    # ------------------------------------------------------------------ #

    # Carregamento dos JSON/YAML                                         #

    # ------------------------------------------------------------------ #

    def _load_from_json(self) -> Dict[str, ExamConfig]:

        exams: Dict[str, ExamConfig] = {}

        if not EXAMS_DIR.exists():

            return exams



        for path in EXAMS_DIR.iterdir():

            if path.name.startswith(("schema", "template")):

                continue

            if path.suffix.lower() not in (".json", ".yaml", ".yml"):

                continue

            data = self._read_structured(path)

            if not data:

                continue

            nome = data.get("nome_exame") or data.get("exame") or path.stem

            key = _norm_exame(nome)

            cfg = ExamConfig(

                nome_exame=nome,

                slug=data.get("slug", key),

                equipamento=str(data.get("equipamento", "")).strip(),

                tipo_placa_analitica=str(data.get("tipo_placa_analitica", "")).strip(),

                esquema_agrupamento=str(data.get("esquema_agrupamento", "")).strip(),

                kit_codigo=data.get("kit_codigo", ""),

                alvos=data.get("alvos", []) or [],

                mapa_alvos=data.get("mapa_alvos", {}) or {},

                faixas_ct=data.get("faixas_ct", {}) or {},

                rps=data.get("rps", []) or [],

                export_fields=data.get("export_fields", []) or [],

                panel_tests_id=str(data.get("panel_tests_id", "")).strip(),

                gal_exame_codigo=str(data.get("gal_exame_codigo", "")).strip(),

                controles=data.get("controles", {}) or {"cn": [], "cp": []},

                comentarios=data.get("comentarios", ""),

                versao_protocolo=data.get("versao_protocolo", ""),

                exam_id=str(data.get("exam_id", "")),

                equipment_id=str(data.get("equipment_id", "")),

                analysis_rules_profile_id=str(data.get("analysis_rules_profile_id", "")),

                gal_profile_id=str(data.get("gal_profile_id", "")),

                storage_profile_id=str(data.get("storage_profile_id", "")),
                pocos_por_amostra=_safe_int(data.get("pocos_por_amostra", 1), 1),
                targets_por_poco=data.get("targets_por_poco", []) or [],
                limiares_ct_por_alvo_poco=data.get("limiares_ct_por_alvo_poco", []) or [],

            )

            exams[key] = cfg

        return exams

    def _load_from_contract_catalog(self) -> Dict[str, ExamConfig]:
        exams: Dict[str, ExamConfig] = {}
        try:
            catalog = get_contract_catalog(reload=True)
            for key, profile in catalog.list_exam_profiles().items():
                if "source_of_truth" in profile and str(profile.get("source_of_truth")).lower() != "contracts":
                    continue
                nome = profile.get("nome_exame") or profile.get("exam_name") or key
                slug = str(profile.get("slug") or _norm_exame(nome).replace(" ", "_"))
                equipment_id = str(profile.get("equipment_id") or profile.get("equipamento") or "")
                ct_thresholds = _safe_dict(profile.get("ct_thresholds"))

                cfg = ExamConfig(
                    nome_exame=str(nome),
                    slug=slug,
                    equipamento=equipment_id,
                    tipo_placa_analitica=str(profile.get("tipo_placa_analitica", "")).strip(),
                    esquema_agrupamento=str(profile.get("esquema_agrupamento", "")).strip(),
                    kit_codigo=profile.get("kit_codigo", ""),
                    alvos=[str(item) for item in _safe_list(profile.get("targets", []))],
                    mapa_alvos={str(k): str(v) for k, v in _safe_dict(profile.get("target_aliases")).items()},
                    faixas_ct={
                        "detect_max": _safe_float(ct_thresholds.get("detect_max", 38.0), 38.0),
                        "inconc_min": _safe_float(ct_thresholds.get("inconc_min", 38.01), 38.01),
                        "inconc_max": _safe_float(ct_thresholds.get("inconc_max", 40.0), 40.0),
                        "rp_min": _safe_float(ct_thresholds.get("rp_min", 15.0), 15.0),
                        "rp_max": _safe_float(ct_thresholds.get("rp_max", 35.0), 35.0),
                    },
                    rps=[str(item) for item in _safe_list(profile.get("rp_targets", []))],
                    export_fields=[str(item) for item in _safe_list(profile.get("export_fields", []))],
                    panel_tests_id=str(profile.get("panel_tests_id", "")),
                    gal_exame_codigo=str(profile.get("gal_exame_codigo", "")),
                    controles=_safe_dict(profile.get("controles", {"cn": [], "cp": []})),
                    comentarios=str(profile.get("comentarios", "")),
                    versao_protocolo=str(profile.get("contract_version", "")),
                    exam_id=str(profile.get("exam_id", slug)),
                    equipment_id=equipment_id,
                    analysis_rules_profile_id=str(
                        profile.get("analysis_rules_profile_id", profile.get("exam_id", slug))
                    ),
                    gal_profile_id=str(profile.get("gal_profile_id", profile.get("exam_id", slug))),
                    storage_profile_id=str(profile.get("storage_profile_id", "default")),
                    pocos_por_amostra=_safe_int(profile.get("pocos_por_amostra", 1), 1),
                    targets_por_poco=[
                        item for item in _safe_list(profile.get("targets_por_poco", [])) if isinstance(item, dict)
                    ],
                    limiares_ct_por_alvo_poco=[
                        item
                        for item in _safe_list(profile.get("limiares_ct_por_alvo_poco", []))
                        if isinstance(item, dict)
                    ],
                )
                exams[_norm_exame(key)] = cfg
        except Exception as exc:
            registrar_log("ExamRegistry", f"Falha ao carregar contratos de exame: {exc}", "ERROR")
        return exams


    # ------------------------------------------------------------------ #

    # Merge CSV + JSON                                                   #

    # ------------------------------------------------------------------ #

    def _merge_configs(self, base: ExamConfig, override: ExamConfig) -> ExamConfig:

        def pick(o: Any, b: Any) -> Any:

            return o if o not in (None, "", [], {}) else b



        merged = ExamConfig(

            nome_exame=pick(override.nome_exame, base.nome_exame),

            slug=pick(override.slug, base.slug),

            equipamento=pick(override.equipamento, base.equipamento),

            tipo_placa_analitica=pick(override.tipo_placa_analitica, base.tipo_placa_analitica),

            esquema_agrupamento=pick(override.esquema_agrupamento, base.esquema_agrupamento),

            kit_codigo=pick(override.kit_codigo, base.kit_codigo),

            alvos=pick(override.alvos, base.alvos),

            mapa_alvos={**base.mapa_alvos, **(override.mapa_alvos or {})},

            faixas_ct={**base.faixas_ct, **(override.faixas_ct or {})},

            rps=pick(override.rps, base.rps),

            export_fields=pick(override.export_fields, base.export_fields),

            panel_tests_id=pick(override.panel_tests_id, base.panel_tests_id),

            gal_exame_codigo=pick(override.gal_exame_codigo, base.gal_exame_codigo),

            controles=pick(override.controles, base.controles),

            comentarios=pick(override.comentarios, base.comentarios),

            versao_protocolo=pick(override.versao_protocolo, base.versao_protocolo),

            exam_id=pick(override.exam_id, base.exam_id),

            equipment_id=pick(override.equipment_id, base.equipment_id),

            analysis_rules_profile_id=pick(
                override.analysis_rules_profile_id, base.analysis_rules_profile_id
            ),

            gal_profile_id=pick(override.gal_profile_id, base.gal_profile_id),

            storage_profile_id=pick(override.storage_profile_id, base.storage_profile_id),
            pocos_por_amostra=_safe_int(pick(override.pocos_por_amostra, base.pocos_por_amostra), 1),
            targets_por_poco=pick(override.targets_por_poco, base.targets_por_poco),
            limiares_ct_por_alvo_poco=pick(
                override.limiares_ct_por_alvo_poco,
                base.limiares_ct_por_alvo_poco,
            ),

        )



        if not merged.esquema_agrupamento:

            blocos = {"48": "96->48", "36": "96->36", "96": "96->96"}

            merged.esquema_agrupamento = blocos.get(merged.tipo_placa_analitica, "")

        return merged



    # ------------------------------------------------------------------ #

    # Utilidades de leitura                                              #

    # ------------------------------------------------------------------ #

    def _read_csv(self, path: Path) -> List[Dict[str, Any]]:

        policy = RetryPolicy.from_env()
        if not path_exists_with_retry(path, policy=policy):

            return []

        import csv



        try:
            with open_with_retry(path, "r", encoding="utf-8", policy=policy) as f:

                reader = csv.DictReader(f)

                return [dict(row) for row in reader]
        except Exception as exc:
            registrar_log(
                "ExamRegistry",
                f"Erro ao ler CSV {path}: {type(exc).__name__}: {exc}",
                "ERROR",
            )
            return []



    def _read_structured(self, path: Path) -> Dict[str, Any]:

        try:

            if path.suffix.lower() == ".json":

                policy = RetryPolicy.from_env()
                content = call_with_retry(
                    lambda: path.read_text(encoding="utf-8"),
                    op_name="read_text",
                    path=path,
                    policy=policy,
                )
                return json.loads(content)

            if path.suffix.lower() in (".yaml", ".yml") and HAS_YAML:

                policy = RetryPolicy.from_env()
                content = call_with_retry(
                    lambda: path.read_text(encoding="utf-8"),
                    op_name="read_text",
                    path=path,
                    policy=policy,
                )
                return yaml.safe_load(content)  # type: ignore

        except Exception as exc:
            registrar_log(
                "ExamRegistry",
                f"Erro ao ler arquivo estruturado {path}: {type(exc).__name__}: {exc}",
                "ERROR",
            )
            return {}

        return {}





# Instância global simples (opcional)

registry = ExamRegistry()

try:

    registry.load()

except Exception:

    pass





def get_exam_cfg(nome_exame: str) -> ExamConfig:

    """

    Helper seguro: obtém ExamConfig do registry; se não existir, devolve um

    ExamConfig mínimo para não quebrar consumidores.

    """

    cfg = registry.get(nome_exame)

    if cfg:

        return cfg

    key = _norm_exame(nome_exame)

    return ExamConfig(

        nome_exame=nome_exame,

        slug=key.replace(" ", "_"),

        equipamento="",

        tipo_placa_analitica="96",

        esquema_agrupamento="96->96",

        kit_codigo="",

        alvos=[],

        mapa_alvos={},

        faixas_ct={"detect_max": 38.0, "inconc_min": 38.01, "inconc_max": 40.0, "rp_min": 15.0, "rp_max": 35.0},

        rps=["RP"],

        export_fields=[],

        panel_tests_id="",

        gal_exame_codigo="",

        controles={"cn": [], "cp": []},

        comentarios="fallback gerado automaticamente",

        versao_protocolo="",

        exam_id=key.replace(" ", "_"),

        equipment_id="",

        analysis_rules_profile_id=key.replace(" ", "_"),

        gal_profile_id=key.replace(" ", "_"),

        storage_profile_id="default",
        pocos_por_amostra=1,
        targets_por_poco=[],
        limiares_ct_por_alvo_poco=[],

    )
