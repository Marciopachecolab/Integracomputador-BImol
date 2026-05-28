# utils/logger.py
import csv
import getpass
import os
import socket
from datetime import datetime
from functools import lru_cache
from typing import Dict, Optional

# --- Bloco de Configuração Inicial ---
# Define o diretório base do projeto de forma robusta
from services.system_paths import BASE_DIR
from services.persistence.csv_contracts import get_csv_contract
from utils.network_io import RetryPolicy, open_with_retry
from utils.text_normalizer import repair_mojibake_text

STRANGLER_EXTRACTION_LEGACY = "STRANGLER_EXTRACTION_LEGACY"
STRANGLER_CT_DIVERGENCE = "STRANGLER_CT_DIVERGENCE"
STRANGLER_APPSTATE_TOUCH = "STRANGLER_APPSTATE_TOUCH"
STRANGLER_GAL_BYPASS = "STRANGLER_GAL_BYPASS"

LOG_FILE_FALLBACK = os.path.join(BASE_DIR, "logs", "sistema.log")
LOG_FILE_PATH: str | None = None
_log_path_cache: str | None = None
_resolving_log_path = False
_LOG_CONTRACT = get_csv_contract("sistema.log")
_LOG_ENCODING = _LOG_CONTRACT.encoding if _LOG_CONTRACT else "utf-8"
_LOG_DELIMITER = _LOG_CONTRACT.delimiter if _LOG_CONTRACT else ";"


def _resolve_log_path() -> str:
    """Resolve o caminho do log priorizando config_service, com fallback seguro."""
    global _log_path_cache, _resolving_log_path
    if LOG_FILE_PATH:
        return LOG_FILE_PATH
    if _log_path_cache:
        return _log_path_cache
    if _resolving_log_path:
        return LOG_FILE_FALLBACK

    _resolving_log_path = True
    try:
        try:
            from services.core.config_service import config_service
            paths = config_service.get_paths()
            log_path = paths.get("log_file")
            if log_path:
                _log_path_cache = log_path
        except Exception:
            pass
    finally:
        _resolving_log_path = False

    return _log_path_cache or LOG_FILE_FALLBACK


@lru_cache(maxsize=1)
def _get_ad_user() -> str:
    """Return AD user as DOMAIN\\USER when available, fallback to local user."""
    domain = os.getenv("USERDOMAIN") or os.getenv("USERDNSDOMAIN") or ""
    username = os.getenv("USERNAME") or getpass.getuser() or ""
    if domain and username:
        return f"{domain}\\{username}"
    return username or "UNKNOWN"


@lru_cache(maxsize=1)
def _get_local_ip() -> str:
    """Return the local IP address used for outbound connections."""
    hostname = socket.gethostname()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip_addr = sock.getsockname()[0]
            if ip_addr:
                return ip_addr
    except OSError:
        pass

    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return "127.0.0.1"


def _get_log_metadata() -> Dict[str, str]:
    """Collect mandatory metadata for operational logs."""
    return {
        "ad_user": _get_ad_user(),
        "ip_address": _get_local_ip(),
    }


def _normalize_error_code(
    *,
    erro_codigo: Optional[str] = None,
    error_code: Optional[str] = None,
) -> str:
    """Normaliza codigo de erro aceitando aliases pt/en."""
    raw = (error_code or erro_codigo or "").strip()
    return repair_mojibake_text(raw) if raw else ""


def _sanitize_log_text(value: str) -> str:
    """Normaliza texto de log para manter uma entrada por linha no CSV."""
    repaired = repair_mojibake_text(value)
    return repaired.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")


def registrar_log(
    acao: str,
    detalhes: str,
    level: str = "INFO",
    *,
    erro_codigo: Optional[str] = None,
    error_code: Optional[str] = None,
) -> None:
    """
    Regista uma entrada de log no ficheiro CSV centralizado.
    Cria o diretório do log se ele não existir.

    Args:
        acao (str): Ação que está a ser logada (ex: "Login", "Análise").
        detalhes (str): Detalhes específicos sobre a ação.
        level (str): Nível do log (INFO, WARNING, ERROR, CRITICAL, DEBUG).
    """
    try:
        log_path = _resolve_log_path()
        acao_clean = _sanitize_log_text(acao)
        detalhes_clean = _sanitize_log_text(detalhes)
        # Garante que o diretório do log exista
        log_dir = os.path.dirname(log_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            # Log para a consola na primeira criação do diretório
            print(f"[LOGGER] Diretório de log criado: {log_dir}")

        metadata = _get_log_metadata()
        normalized_error_code = _normalize_error_code(
            erro_codigo=erro_codigo,
            error_code=error_code,
        )

        # Abre o ficheiro em modo de adição ('a') com codificação UTF-8
        # Usa lock para evitar corrupção em ambiente multiusuário
        from utils.csv_lock import CSVFileLock
        policy = RetryPolicy.from_env()
        with CSVFileLock(log_path):
            with open_with_retry(
                log_path, "a", newline="", encoding=_LOG_ENCODING, policy=policy
            ) as f:
                writer = csv.writer(f, delimiter=_LOG_DELIMITER)
                writer.writerow(
                    [
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        getpass.getuser(),
                        metadata["ip_address"],
                        acao_clean,
                        detalhes_clean,
                        level.upper(),
                        metadata["ad_user"],
                        normalized_error_code,
                    ]
                )
    except Exception as e:
        # Se o logging falhar, imprime o erro na consola para não passar despercebido.
        print("--- ERRO CRÍTICO NO LOGGER ---")
        print("Não foi possível registar o log:")
        print(f"Ação: {acao}, Detalhes: {detalhes}, Nível: {level}")
        print(f"Erro: {e}")
        print("--- FIM DO ERRO DO LOGGER ---")
