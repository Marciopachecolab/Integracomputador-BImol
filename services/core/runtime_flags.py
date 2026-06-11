"""Feature flags de rollout/rollback para mudancas faseadas."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from config.feature_flags import feature_flags

FLAG_CONTRACT_PARSER_ROUTING = "USE_CONTRACT_PARSER_ROUTING"
FLAG_CONTRACT_ANALYSIS_RUNTIME = "USE_CONTRACT_ANALYSIS_RUNTIME"
FLAG_GAL_LEGACY_PANEL_CSV = "USE_GAL_LEGACY_PANEL_CSV"
FLAG_GAL_LEGACY_SUCCESS_LEDGER = "USE_GAL_LEGACY_SUCCESS_LEDGER"
FLAG_CONTRACTUAL_CSV_LEGACY_FALLBACK = "USE_CONTRACTUAL_CSV_LEGACY_FALLBACK"
FLAG_EXAM_RUNS_CSV_WRITER = "USE_EXAM_RUNS_CSV_WRITER"
FLAG_EXAM_RUNS_SQLITE_FIRST = "USE_EXAM_RUNS_SQLITE_FIRST"
FLAG_PLATE_SYNC_USE_CASE = "USE_PLATE_SYNC_USE_CASE"
FLAG_GAL_LOGIN_HARDENED = "USE_GAL_LOGIN_HARDENED"
FLAG_OPERATIONAL_TABULAR_VIEWER = "USE_OPERATIONAL_TABULAR_VIEWER"
FLAG_EXAM_CREATOR_REGISTRY_SAVE = "USE_EXAM_CREATOR_REGISTRY_SAVE"
FLAG_ANALYSIS_EXAMS_REGISTRY_READ = "USE_ANALYSIS_EXAMS_REGISTRY_READ"
FLAG_ANALYSIS_RUNTIME_REGISTRY_RULES = "USE_ANALYSIS_RUNTIME_REGISTRY_RULES"
FLAG_ANALYSIS_RUNTIME_PROMOTION_GATE_ENFORCEMENT = "USE_ANALYSIS_RUNTIME_PROMOTION_GATE_ENFORCEMENT"
FLAG_ANALYSIS_RUNTIME_STAGED_ROLLOUT = "USE_ANALYSIS_RUNTIME_STAGED_ROLLOUT"
FLAG_MENU_ANALYSIS_LEGACY_COMPAT = "USE_MENU_ANALYSIS_LEGACY_COMPAT"
FLAG_GAL_ENVIO_SEM_METADADOS = "USE_GAL_ENVIO_SEM_METADADOS"
FLAG_GAL_FIREFOX_HEADLESS = "USE_GAL_FIREFOX_HEADLESS"
FLAG_GAL_TERMINAL_LOG_POR_AMOSTRA = "USE_GAL_TERMINAL_LOG_POR_AMOSTRA"
FLAG_GAL_CLAIM_LEASE = "USE_GAL_CLAIM_LEASE"

ENV_CONTRACT_PARSER_ROUTING = "INTEGRAGAL_USE_CONTRACT_PARSER_ROUTING"
ENV_CONTRACT_ANALYSIS_RUNTIME = "INTEGRAGAL_USE_CONTRACT_ANALYSIS_RUNTIME"
ENV_GAL_LEGACY_PANEL_CSV = "INTEGRAGAL_USE_GAL_LEGACY_PANEL_CSV"
ENV_GAL_LEGACY_SUCCESS_LEDGER = "INTEGRAGAL_USE_GAL_LEGACY_SUCCESS_LEDGER"
ENV_CONTRACTUAL_CSV_LEGACY_FALLBACK = "INTEGRAGAL_USE_CONTRACTUAL_CSV_LEGACY_FALLBACK"
ENV_EXAM_RUNS_CSV_WRITER = "INTEGRAGAL_USE_EXAM_RUNS_CSV_WRITER"
ENV_EXAM_RUNS_SQLITE_FIRST = "INTEGRAGAL_USE_EXAM_RUNS_SQLITE_FIRST"
ENV_PLATE_SYNC_USE_CASE = "INTEGRAGAL_USE_PLATE_SYNC_USE_CASE"
ENV_GAL_LOGIN_HARDENED = "INTEGRAGAL_USE_GAL_LOGIN_HARDENED"
ENV_OPERATIONAL_TABULAR_VIEWER = "INTEGRAGAL_USE_OPERATIONAL_TABULAR_VIEWER"
ENV_EXAM_CREATOR_REGISTRY_SAVE = "INTEGRAGAL_USE_EXAM_CREATOR_REGISTRY_SAVE"
ENV_ANALYSIS_EXAMS_REGISTRY_READ = "INTEGRAGAL_USE_ANALYSIS_EXAMS_REGISTRY_READ"
ENV_ANALYSIS_RUNTIME_REGISTRY_RULES = "INTEGRAGAL_USE_ANALYSIS_RUNTIME_REGISTRY_RULES"
ENV_ANALYSIS_RUNTIME_PROMOTION_GATE_ENFORCEMENT = "INTEGRAGAL_USE_ANALYSIS_RUNTIME_PROMOTION_GATE_ENFORCEMENT"
ENV_ANALYSIS_RUNTIME_STAGED_ROLLOUT = "INTEGRAGAL_USE_ANALYSIS_RUNTIME_STAGED_ROLLOUT"
ENV_MENU_ANALYSIS_LEGACY_COMPAT = "INTEGRAGAL_USE_MENU_ANALYSIS_LEGACY_COMPAT"
ENV_MENU_COMPAT_OFF_USERS = "INTEGRAGAL_MENU_COMPAT_OFF_USERS"
ENV_MENU_COMPAT_OFF_USERS_FILE = "INTEGRAGAL_MENU_COMPAT_OFF_USERS_FILE"
ENV_MENU_COMPAT_GLOBAL_MAX_USED = "INTEGRAGAL_MENU_COMPAT_GLOBAL_MAX_USED"
ENV_MENU_COMPAT_GLOBAL_MAX_ERRORS = "INTEGRAGAL_MENU_COMPAT_GLOBAL_MAX_ERRORS"
ENV_MENU_COMPAT_GLOBAL_LOOKBACK_DAYS = "INTEGRAGAL_MENU_COMPAT_GLOBAL_LOOKBACK_DAYS"
ENV_MENU_COMPAT_SHUTDOWN_GOV_FILE = "INTEGRAGAL_MENU_COMPAT_SHUTDOWN_GOV_FILE"


def _coerce_bool(value: Optional[str]) -> Optional[bool]:
    """Converte texto de ambiente para bool com tolerancia a variacoes."""
    if value is None:
        return None

    normalized = value.strip().lower()
    if normalized in {"1", "true", "on", "yes", "y"}:
        return True
    if normalized in {"0", "false", "off", "no", "n"}:
        return False
    return None


def _is_enabled_with_env_override(
    *,
    flag_name: str,
    env_var: str,
    user_id: Optional[str],
    default: bool,
) -> bool:
    """Le flag com prioridade para variavel de ambiente."""
    from_env = _coerce_bool(os.getenv(env_var))
    if from_env is not None:
        return from_env

    status = feature_flags.get_flag_status(flag_name)
    if not status:
        return default
    return feature_flags.is_enabled(flag_name, user_id=user_id)


def _parse_user_tokens(raw_value: str | None) -> set[str]:
    if not raw_value:
        return set()
    users: set[str] = set()
    for token in str(raw_value).split(","):
        value = str(token or "").strip()
        if value:
            users.add(value)
    return users


def _load_menu_compat_off_users_from_file() -> set[str]:
    raw_path = os.getenv(ENV_MENU_COMPAT_OFF_USERS_FILE, "").strip()
    if raw_path:
        path = Path(raw_path)
    else:
        path = Path(__file__).resolve().parents[1] / "config" / "menu_compat_canary_governance.json"
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    raw_users = payload.get("menu_analysis_legacy_compat_off_users", [])
    if not isinstance(raw_users, list):
        return set()
    users: set[str] = set()
    for item in raw_users:
        token = str(item or "").strip()
        if token:
            users.add(token)
    return users


def _resolve_menu_compat_off_users() -> set[str]:
    users = _load_menu_compat_off_users_from_file()
    users.update(_parse_user_tokens(os.getenv(ENV_MENU_COMPAT_OFF_USERS)))
    return users


def get_menu_compat_off_users() -> set[str]:
    """Retorna conjunto canonico de usuarios com canario OFF para compat legado."""
    return set(_resolve_menu_compat_off_users())


def get_menu_compat_global_shutdown_policy() -> dict[str, int]:
    """Adapter compativel para modulo dedicado de governanca de shutdown."""
    from services import menu_compat_shutdown_policy

    return menu_compat_shutdown_policy.get_menu_compat_global_shutdown_policy()


def get_menu_compat_global_shutdown_thresholds() -> tuple[int, int]:
    """Adapter compativel para modulo dedicado de governanca de shutdown."""
    from services import menu_compat_shutdown_policy

    return menu_compat_shutdown_policy.get_menu_compat_global_shutdown_thresholds()


def is_contract_parser_enabled(user_id: Optional[str] = None) -> bool:
    """Indica se o roteamento de parser por contrato esta ativo."""
    return _is_enabled_with_env_override(
        flag_name=FLAG_CONTRACT_PARSER_ROUTING,
        env_var=ENV_CONTRACT_PARSER_ROUTING,
        user_id=user_id,
        default=False,
    )


def is_contract_analysis_runtime_enabled(user_id: Optional[str] = None) -> bool:
    """Indica se o runtime de analise contratual esta ativo."""
    return _is_enabled_with_env_override(
        flag_name=FLAG_CONTRACT_ANALYSIS_RUNTIME,
        env_var=ENV_CONTRACT_ANALYSIS_RUNTIME,
        user_id=user_id,
        default=False,
    )


def is_legacy_panel_csv_enabled(user_id: Optional[str] = None) -> bool:
    """Indica se o writer legado painel_* continua permitido."""
    return _is_enabled_with_env_override(
        flag_name=FLAG_GAL_LEGACY_PANEL_CSV,
        env_var=ENV_GAL_LEGACY_PANEL_CSV,
        user_id=user_id,
        default=False,
    )


def is_legacy_gal_success_ledger_enabled(user_id: Optional[str] = None) -> bool:
    """Indica se o CSV legado gal_transacoes_sucesso.csv continua ativo."""
    return _is_enabled_with_env_override(
        flag_name=FLAG_GAL_LEGACY_SUCCESS_LEDGER,
        env_var=ENV_GAL_LEGACY_SUCCESS_LEDGER,
        user_id=user_id,
        default=False,
    )


def is_contractual_csv_legacy_fallback_enabled(user_id: Optional[str] = None) -> bool:
    """Indica se fallback legado e permissivo de CSV contratual continua permitido."""
    return _is_enabled_with_env_override(
        flag_name=FLAG_CONTRACTUAL_CSV_LEGACY_FALLBACK,
        env_var=ENV_CONTRACTUAL_CSV_LEGACY_FALLBACK,
        user_id=user_id,
        default=False,
    )


def is_exam_runs_csv_writer_enabled(user_id: Optional[str] = None) -> bool:
    """Indica se o writer contratual corridas_<slug_exame>.csv esta ativo."""
    return _is_enabled_with_env_override(
        flag_name=FLAG_EXAM_RUNS_CSV_WRITER,
        env_var=ENV_EXAM_RUNS_CSV_WRITER,
        user_id=user_id,
        default=True,
    )


def is_exam_runs_sqlite_first_enabled(user_id: Optional[str] = None) -> bool:
    """Indica se o historico por exame deve persistir em SQLite antes do CSV."""
    return _is_enabled_with_env_override(
        flag_name=FLAG_EXAM_RUNS_SQLITE_FIRST,
        env_var=ENV_EXAM_RUNS_SQLITE_FIRST,
        user_id=user_id,
        default=True,
    )


def is_plate_sync_use_case_enabled(user_id: Optional[str] = None) -> bool:
    """Indica se a sincronizacao de placa usa o use case extraido da UI."""
    return _is_enabled_with_env_override(
        flag_name=FLAG_PLATE_SYNC_USE_CASE,
        env_var=ENV_PLATE_SYNC_USE_CASE,
        user_id=user_id,
        default=True,
    )


def is_gal_hardened_login_enabled(user_id: Optional[str] = None) -> bool:
    """Indica se o login endurecido do GAL esta ativo."""
    return _is_enabled_with_env_override(
        flag_name=FLAG_GAL_LOGIN_HARDENED,
        env_var=ENV_GAL_LOGIN_HARDENED,
        user_id=user_id,
        default=False,
    )


def is_operational_tabular_viewer_enabled(user_id: Optional[str] = None) -> bool:
    """Indica se a consulta operacional tabular (F6/F7) esta ativa na rota de historico."""
    return _is_enabled_with_env_override(
        flag_name=FLAG_OPERATIONAL_TABULAR_VIEWER,
        env_var=ENV_OPERATIONAL_TABULAR_VIEWER,
        user_id=user_id,
        default=False,
    )


def is_exam_creator_registry_save_enabled(user_id: Optional[str] = None) -> bool:
    """Indica se o wizard de exame deve salvar via RegistryExamEditor com fallback legado."""
    return _is_enabled_with_env_override(
        flag_name=FLAG_EXAM_CREATOR_REGISTRY_SAVE,
        env_var=ENV_EXAM_CREATOR_REGISTRY_SAVE,
        user_id=user_id,
        default=False,
    )


def is_analysis_exams_registry_read_enabled(user_id: Optional[str] = None) -> bool:
    """Indica se a listagem de exames para analise usa Registry como fonte canônica."""
    return _is_enabled_with_env_override(
        flag_name=FLAG_ANALYSIS_EXAMS_REGISTRY_READ,
        env_var=ENV_ANALYSIS_EXAMS_REGISTRY_READ,
        user_id=user_id,
        default=False,
    )


def is_analysis_runtime_registry_rules_enabled(user_id: Optional[str] = None) -> bool:
    """Indica se a analise executa regras/limiares pelo contrato canônico do Registry."""
    return _is_enabled_with_env_override(
        flag_name=FLAG_ANALYSIS_RUNTIME_REGISTRY_RULES,
        env_var=ENV_ANALYSIS_RUNTIME_REGISTRY_RULES,
        user_id=user_id,
        default=False,
    )


def is_analysis_runtime_promotion_gate_enforcement_enabled(user_id: Optional[str] = None) -> bool:
    """Indica se promocao do runtime canonico depende de gate aprovado."""
    return _is_enabled_with_env_override(
        flag_name=FLAG_ANALYSIS_RUNTIME_PROMOTION_GATE_ENFORCEMENT,
        env_var=ENV_ANALYSIS_RUNTIME_PROMOTION_GATE_ENFORCEMENT,
        user_id=user_id,
        default=False,
    )


def is_analysis_runtime_staged_rollout_enabled(user_id: Optional[str] = None) -> bool:
    """Indica se rollout canario por estagios (10/25/50/100) esta ativo."""
    return _is_enabled_with_env_override(
        flag_name=FLAG_ANALYSIS_RUNTIME_STAGED_ROLLOUT,
        env_var=ENV_ANALYSIS_RUNTIME_STAGED_ROLLOUT,
        user_id=user_id,
        default=False,
    )


def is_menu_analysis_legacy_compat_enabled(user_id: Optional[str] = None) -> bool:
    """Indica se fallback legado do catalogo de exames na UI permanece habilitado."""
    enabled = _is_enabled_with_env_override(
        flag_name=FLAG_MENU_ANALYSIS_LEGACY_COMPAT,
        env_var=ENV_MENU_ANALYSIS_LEGACY_COMPAT,
        user_id=user_id,
        default=True,
    )
    if not enabled:
        return False
    user_token = str(user_id or "").strip()
    if user_token and user_token in _resolve_menu_compat_off_users():
        return False
    return True



