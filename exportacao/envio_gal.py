"""
MÓDULO DE ENVIO GAL - Automação de Envio de Resultados
======================================================================

RESPONSABILIDADES:
------------------
✅ Automação de envio de resultados para sistema GAL via Selenium
✅ Gerenciamento de sessão e autenticação no GAL
✅ Preenchimento de formulários de resultados
✅ Validação e retry de envios
✅ Interface gráfica para seleção e envio de amostras

ARQUITETURA:
-----------
- Usa: exportacao/gal_formatter.py para formatar dados
- Depende de: browser/global_browser.py para gerenciar navegador
- Configuração: services/config_service.py (credenciais e endpoints)

FLUXO DE ENVIO:
--------------
1. Carregar resultados formatados (via gal_formatter)
2. Autenticar no sistema GAL
3. Navegar para formulário de entrada
4. Preencher campos com resultados
5. Submeter e validar resposta
6. Registrar histórico de envio

Ver: ANALISE_TECNICA_FUNCIONAMENTO.md (Seção 4 - Exportação GAL)
"""

# exportacao/envio_gal.py
import os
import sys
import threading
import time
from datetime import datetime
from functools import wraps
from pathlib import Path
from tkinter import messagebox
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import customtkinter as ctk
import pandas as pd
import simplejson as json
from application.gal_send_use_case import GalSendRequest, GalSendUseCase
from application.gal_ui_input_adapter import (
    GalUIInputAdapter,
    GalUIInputState,
)
from services.core.config_service import config_service
from services.persistence.csv_contracts import get_csv_contract
from services.persistence.csv_io import read_csv_strict, write_csv_atomic
from services.exam_registry import get_exam_cfg
from utils.csv_lock import CSVFileLock
from utils.csv_safety import sanitize_csv_value
from utils.io_utils import read_data_with_auto_detection
from utils.logger import registrar_log
from utils.privacy import mask_patient_name
from utils.gui_utils import safe_destroy_ctk_toplevel
from utils.network_io import (
    RetryPolicy,
    call_with_retry,
    open_with_retry,
    path_exists_with_retry,
)
from services.reports.relatorio_csv import build_relatorio_rows, write_relatorio_csv
from services.analysis.final_run_report import upsert_final_report_with_send_results
from services.analysis.full_run_status_sync import reconcile_send_status_across_artifacts
from services.core.runtime_flags import (
    is_contractual_csv_legacy_fallback_enabled,
    is_gal_hardened_login_enabled,
    is_legacy_gal_success_ledger_enabled,
)
from exportacao.gal_exceptions import (
    GalLoginElementNotFound,
    GalLoginNotConfirmed,
    GalPayloadValidationError,
)
from exportacao.gal_payload_contract import (
    GAL_PAYLOAD_SCHEMA_VERSION,
    validate_gal_payload,
)
from exportacao.gal_payload_dto import GalPayloadDTO
from ui.gal_ui_dialog_adapter import GalUIDialogAdapter
from services.gal.gal_transactions import (
    append_transaction_journal_unique,
    append_success_transactions,
    build_idempotency_key,
    build_success_transaction_rows,
    build_transaction_journal_rows,
    default_transaction_journal_path,
    default_success_transactions_path,
    load_successful_idempotency_keys,
    reconcile_legacy_success_into_journal,
)

from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from autenticacao.auth_service import AuthService

# --- Configuração de Paths e Imports ---
# Garante que o diretório raiz do projeto (onde ficam os pacotes `services`, `utils`, etc.)
# esteja no sys.path, mesmo quando este módulo é executado diretamente.
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Linha comentada devido a alerta do ruff (E402): import em nível de módulo não posicionado no topo do arquivo.
# from services.core.config_service import config_service
# Linha comentada devido a alerta do ruff (E402): import em nível de módulo não posicionado no topo do arquivo.
# from services.system_paths import BASE_DIR
# Linha comentada devido a alerta do ruff (E402): import em nível de módulo não posicionado no topo do arquivo.
# from utils.io_utils import read_data_with_auto_detection
# Linha comentada devido a alerta do ruff (E402): import em nível de módulo não posicionado no topo do arquivo.
# from utils.logger import registrar_log

# --- Configurações Carregadas do Serviço Centralizado ---
GAL_CONFIG = config_service.get_gal_config()
PATHS_CONFIG = config_service.get_paths()
_GAL_UPLOAD_HISTORY_CONTRACT_NAME = "gal_upload_history.csv"
_GAL_UPLOAD_HISTORY_CONTRACT = get_csv_contract(_GAL_UPLOAD_HISTORY_CONTRACT_NAME)
_GAL_UPLOAD_HISTORY_DELIMITER = (
    _GAL_UPLOAD_HISTORY_CONTRACT.delimiter if _GAL_UPLOAD_HISTORY_CONTRACT else ";"
)
_GAL_UPLOAD_HISTORY_ENCODING = (
    _GAL_UPLOAD_HISTORY_CONTRACT.encoding if _GAL_UPLOAD_HISTORY_CONTRACT else "utf-8"
)

# --- Painéis padrão (compatíveis com scripts antigos) ---
DEFAULT_PANEL_TESTS = {
    "1": [
        "influenzaa",
        "influenzab",
        "coronavirusncov",
        "adenovirus",
        "vsincicialresp",
        "metapneumovirus",
        "rinovirus",
    ]
}


def _norm_gal_field(val: str) -> str:
    """Normaliza nome de campo GAL: minúsculas, sem acentos, sem separadores.

    Replica a regra de exportacao.gal_formatter._normalize_export_column_name
    sem importar aquele módulo (evita dependência circular).
    """
    import unicodedata as _ud

    return (
        _ud.normalize("NFKD", str(val)).encode("ASCII", "ignore").decode("ASCII")
        .replace(" ", "").replace("-", "").replace("_", "").lower()
    )


# ==============================================================================
# 1. DECORATOR DE RETENTATIVA
# ==============================================================================
def retry_with_backoff(
    retries=int(GAL_CONFIG.get("retry_settings", {}).get("max_retries", 3)),
    backoff_in_seconds=float(
        GAL_CONFIG.get("retry_settings", {}).get("backoff_factor", 1.0)
    ),
):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            attempts = 0
            last_exception = None
            while attempts < retries:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    attempts += 1
                    sleep_time = backoff_in_seconds * (2 ** (attempts - 1))
                    log_msg = f"Tentativa {attempts}/{retries} falhou para '{f.__name__}': {e}. Aguardando {sleep_time:.2f}s."
                    if args and hasattr(args[0], "log"):
                        args[0].log(log_msg, "warning")
                    else:
                        registrar_log("Retry Decorator", log_msg, "WARNING")
                    time.sleep(sleep_time)
            raise last_exception

        return wrapper

    return decorator


# ==============================================================================
# 2. CLASSE DE SERVIÇO (LÓGICA DE NEGÓCIO DESACOPLADA DA UI)
# ==============================================================================
class GalService:
    _LOGIN_STAGE_CONFIG_KEYS = {
        "usuario": "username",
        "senha": "password",
        "modulo": "module_button",
        "laboratorio": "lab_button",
        "botao_login": "login_button",
    }
    _LOGIN_STAGE_DEFAULT_IDS = {
        "usuario": ("ext-comp-1008", "usuario", "username"),
        "senha": ("ext-comp-1009", "senha", "password"),
        "modulo": ("ext-comp-1010", "modulo", "module"),
        "laboratorio": ("ext-comp-1011", "laboratorio", "lab"),
        "botao_login": ("ext-gen68", "ext-gen29", "login"),
    }
    _LOGIN_STAGE_XPATHS = {
        "usuario": (
            "//input[contains(@name,'usuario')]",
            "//input[contains(@id,'usuario')]",
        ),
        "senha": (
            "//input[@type='password']",
            "//input[contains(@name,'senha')]",
            "//input[contains(@id,'senha')]",
        ),
        "modulo": (
            "//input[contains(@name,'modulo')]",
            "//input[contains(@id,'modulo')]",
        ),
        "laboratorio": (
            "//input[contains(@name,'lab')]",
            "//input[contains(@id,'lab')]",
        ),
        "botao_login": (
            "//button[contains(translate(.,'LOGINENTRAR','loginentrar'),'entrar')]",
            "//button[contains(translate(.,'LOGINENTRAR','loginentrar'),'login')]",
            "//span[contains(translate(.,'LOGINENTRAR','loginentrar'),'entrar')]/ancestor::button[1]",
        ),
    }

    def __init__(self, logger_callback, runtime_context: Optional[Dict[str, Any]] = None):
        self.log = logger_callback
        
        # Recarregar as configurações dinamicamente para aplicar alterações da UI (ex: GAL_TESTE vs GAL)
        current_gal_config = config_service.get_gal_config()
        self.base_url = current_gal_config.get("base_url")
        self.login_ids = current_gal_config.get("login_ids", {})
        self.endpoints = current_gal_config.get("api_endpoints", {})
        self._runtime_context: Dict[str, Any] = dict(runtime_context or {})
        # Une os painéis configurados com o painel padrão utilizado nos scripts antigos
        configured_panels = GAL_CONFIG.get("panel_tests", {}) or {}
        merged_panels = {}
        # Primeiro aplica os painéis configurados
        for k, v in configured_panels.items():
            merged_panels[str(k)] = list(
                dict.fromkeys(v)
            )  # remove duplicados preservando ordem
        # Em seguida garante que o painel 1 tenha todos os testes clássicos de VR
        for k, v in DEFAULT_PANEL_TESTS.items():
            if k not in merged_panels:
                merged_panels[k] = list(dict.fromkeys(v))
            else:
                merged = list(dict.fromkeys(list(merged_panels[k]) + list(v)))
                merged_panels[k] = merged
        self.panel_tests = merged_panels
        self.timeout = int(GAL_CONFIG.get("request_timeout", 30))

    def set_runtime_context(self, **context: Any) -> None:
        """Atualiza contexto de corrida em runtime para rastreabilidade do relatorio final."""
        for key, value in context.items():
            if value is None:
                continue
            self._runtime_context[key] = value

    @retry_with_backoff()
    def realizar_login(self, driver: WebDriver, usuario: str, senha: str):
        self.log(f"Acedendo a {self.base_url}...", "info")
        login_mode = "hardened" if is_gal_hardened_login_enabled() else "legacy"
        self.log(f"Iniciando login GAL (modo={login_mode}).", "info")
        try:
            if login_mode == "hardened":
                self._realizar_login_hardened(driver, usuario, senha)
            else:
                self._realizar_login_legacy(driver, usuario, senha)
        except (GalLoginElementNotFound, GalLoginNotConfirmed) as exc:
            self.log(f"Falha de login GAL ({login_mode}): {exc}", "error")
            registrar_log(
                "Envio GAL Login",
                f"Falha de login GAL ({login_mode}): {exc}",
                "ERROR",
                error_code=getattr(exc, "error_code", "GAL_LOGIN_ERROR"),
            )
            self._persist_login_debug_artifacts(driver)
            raise
        except Exception:
            self._persist_login_debug_artifacts(driver)
            raise

    def _realizar_login_hardened(
        self, driver: WebDriver, usuario: str, senha: str
    ) -> None:
        """Fluxo endurecido com waits explicitos e erros tipados."""
        driver.get(self.base_url)

        username = self._wait_stage_element(driver, "usuario")
        password = self._wait_stage_element(driver, "senha")
        modulo = self._wait_stage_element(driver, "modulo")
        lab = self._wait_stage_element(driver, "laboratorio")
        login_btn = self._wait_stage_element(driver, "botao_login", clickable=True)

        self._fill_login_field(username, usuario)
        self._fill_login_field(password, senha)
        self._fill_login_field(modulo, "BIOLOGIA MEDICA")
        modulo.send_keys(Keys.TAB)
        self._fill_login_field(lab, "LACEN")
        lab.send_keys(Keys.TAB)
        login_btn.click()

        self.log("Tentativa de login realizada (fluxo endurecido).", "info")
        self._wait_login_confirmation(driver)

    def _realizar_login_legacy(self, driver: WebDriver, usuario: str, senha: str) -> None:
        """Fluxo legado para rollback operacional via feature flag."""
        driver.get(self.base_url)
        username = driver.find_element(By.ID, "ext-comp-1008")
        password = driver.find_element(By.ID, "ext-comp-1009")
        modulo = driver.find_element(By.ID, "ext-comp-1010")
        lab = driver.find_element(By.ID, "ext-comp-1011")
        login = driver.find_element(By.ID, "ext-gen68")

        username.send_keys(usuario)
        password.send_keys(senha)
        modulo.send_keys("BIOLOGIA MEDICA")
        time.sleep(1)
        modulo.send_keys(Keys.TAB)
        time.sleep(1)
        lab.send_keys("LACEN")
        time.sleep(2)
        lab.send_keys(Keys.TAB)
        time.sleep(1)
        login.click()
        time.sleep(1)
        try:
            base_url = self.base_url.rstrip('/')
            driver.get(f"{base_url}/laboratorio/")
        except Exception:
            pass
        time.sleep(1)
        try:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        except Exception:
            pass
        time.sleep(4)
        self.log("Tentativa de login realizada (fluxo legado).", "warning")
        self._wait_login_confirmation(driver)

    def _fill_login_field(self, element: Any, value: str) -> None:
        """Preenche campos de login com limpeza defensiva."""
        try:
            element.clear()
        except Exception:
            pass
        element.send_keys(value)

    def _stage_locators(self, stage: str) -> List[Tuple[str, str]]:
        """Resolve locators por etapa com prioridade para config e fallback seguro."""
        key = self._LOGIN_STAGE_CONFIG_KEYS.get(stage, "")
        configured = self.login_ids.get(key)
        candidates: List[str] = []
        if isinstance(configured, str) and configured.strip():
            candidates.append(configured.strip())
        elif isinstance(configured, (list, tuple)):
            candidates.extend(str(item).strip() for item in configured if str(item).strip())

        for fallback in self._LOGIN_STAGE_DEFAULT_IDS.get(stage, ()):
            fallback_str = str(fallback).strip()
            if fallback_str:
                candidates.append(fallback_str)

        # Dedup preservando ordem.
        seen = set()
        unique_candidates: List[str] = []
        for candidate in candidates:
            normalized = candidate.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            unique_candidates.append(candidate)

        locators: List[Tuple[str, str]] = []
        for candidate in unique_candidates:
            locators.append((By.ID, candidate))
            locators.append((By.NAME, candidate))

        for xpath in self._LOGIN_STAGE_XPATHS.get(stage, ()):
            locators.append((By.XPATH, xpath))
        return locators

    def _wait_stage_element(
        self,
        driver: WebDriver,
        stage: str,
        *,
        clickable: bool = False,
        timeout_seconds: Optional[float] = None,
    ):
        """Aguarda elemento por etapa de login testando locators alternativos."""
        timeout = float(timeout_seconds) if timeout_seconds is not None else float(max(5, int(self.timeout)))
        deadline = time.monotonic() + max(0.1, timeout)
        locators = self._stage_locators(stage)
        last_exception: Optional[Exception] = None

        while time.monotonic() < deadline:
            for by, value in locators:
                try:
                    element = driver.find_element(by, value)
                except Exception as exc:
                    last_exception = exc
                    continue
                try:
                    if hasattr(element, "is_displayed") and not element.is_displayed():
                        continue
                except Exception:
                    continue
                if clickable:
                    try:
                        if hasattr(element, "is_enabled") and not element.is_enabled():
                            continue
                    except Exception:
                        continue
                return element
            time.sleep(0.2)

        locator_debug = ", ".join(f"{by}:{value}" for by, value in locators[:6])
        if len(locators) > 6:
            locator_debug += ", ..."
        raise GalLoginElementNotFound(
            f"Elemento nao encontrado na etapa '{stage}'. locators={locator_debug}"
        ) from last_exception

    def _wait_element(self, wait: WebDriverWait, element_id: str, stage: str):
        try:
            return wait.until(EC.presence_of_element_located((By.ID, element_id)))
        except Exception as exc:
            raise GalLoginElementNotFound(
                f"Elemento '{element_id}' ausente na etapa '{stage}'."
            ) from exc

    def _wait_clickable(self, wait: WebDriverWait, element_id: str, stage: str):
        try:
            return wait.until(EC.element_to_be_clickable((By.ID, element_id)))
        except Exception as exc:
            raise GalLoginElementNotFound(
                f"Elemento clicavel '{element_id}' ausente na etapa '{stage}'."
            ) from exc

    def _wait_login_confirmation(self, driver: WebDriver) -> None:
        """
        Confirma login com polling curto e criterios multiplos.

        Evita espera sequencial longa (ex.: 30s + 30s) quando o shell autenticado
        ja esta visivel, reduzindo latencia operacional sem perder robustez.
        """
        confirmation_timeout = self._get_login_confirmation_timeout_seconds()
        deadline = time.monotonic() + confirmation_timeout

        while time.monotonic() < deadline:
            if self._has_versao_total_marker(driver):
                self.log("Login confirmado (VERSAO-TOTAL).", "success")
                return

            if self._is_authenticated_shell_visible(driver):
                self.log(
                    "Login confirmado por shell autenticado (logout/usuario/menu).",
                    "success",
                )
                return

            if self._is_logged_area_url(driver) and not self._is_login_form_visible(driver):
                self.log("Login presumido via URL de area autenticada.", "success")
                return

            time.sleep(0.25)

        current_url = str(getattr(driver, "current_url", ""))
        login_form_visible = self._is_login_form_visible(driver)
        authenticated_shell = self._is_authenticated_shell_visible(driver)
        has_versao_total = self._has_versao_total_marker(driver)
        raise GalLoginNotConfirmed(
            "Login nao confirmado apos tentativa. "
            f"url='{current_url}' login_form_visible={login_form_visible} "
            f"authenticated_shell={authenticated_shell} "
            f"versao_total={has_versao_total} timeout={confirmation_timeout:.1f}s"
        )

    def _get_login_confirmation_timeout_seconds(self) -> float:
        """Retorna timeout de confirmacao com limite seguro para nao degradar UX."""
        configured_timeout = GAL_CONFIG.get("login_confirmation_timeout")
        if configured_timeout is not None:
            try:
                return max(5.0, float(configured_timeout))
            except (TypeError, ValueError):
                pass
        # request_timeout pode ser alto; limitar para confirmar rapidamente o login.
        return max(8.0, min(20.0, float(max(5, int(self.timeout)))))

    def _has_versao_total_marker(self, driver: WebDriver) -> bool:
        """Verifica marcador clássico de sessão autenticada no GAL."""
        try:
            marker = driver.find_element(By.ID, "VERSAO-TOTAL")
        except Exception:
            return False
        try:
            return not hasattr(marker, "is_displayed") or bool(marker.is_displayed())
        except Exception:
            return True

    def _is_logged_area_url(self, driver: WebDriver) -> bool:
        """Indica se a URL atual e compativel com area autenticada do GAL."""
        current_url = str(getattr(driver, "current_url", "")).lower()
        if not current_url:
            return False
        if any(token in current_url for token in ("/laboratorio", "/biologiamedica")):
            return True
        # Em alguns ambientes o GAL fica no root apos autenticar.
        if "galteste.saude.sc.gov.br" in current_url or "gal.saude.sc.gov.br" in current_url:
            return "login" not in current_url
        return False

    def _is_authenticated_shell_visible(self, driver: WebDriver) -> bool:
        """Detecta shell autenticado do GAL quando marcadores classicos nao existem."""
        page_source = str(getattr(driver, "page_source", "") or "")
        normalized_source = page_source.lower()
        if "sair do sistema" in normalized_source and "menu-panel" in normalized_source:
            return True
        if "usuário:" in normalized_source or "usuÃ¡rio:" in page_source:
            if "sair do sistema" in normalized_source:
                return True
        return False

    def _is_login_form_visible(self, driver: WebDriver) -> bool:
        """Detecta se o formulario de login ainda esta visivel apos tentativa."""
        for stage in ("usuario", "senha"):
            for by, value in self._stage_locators(stage):
                try:
                    element = driver.find_element(by, value)
                except Exception:
                    continue
                try:
                    if hasattr(element, "is_displayed") and element.is_displayed():
                        return True
                except Exception:
                    continue
        return False

    def _persist_login_debug_artifacts(self, driver: WebDriver) -> None:
        """Salva screenshot/html de falha para diagnostico de login."""
        try:
            debug_dirs = [
                os.path.join(BASE_DIR, "debug"),
                os.path.join(BASE_DIR, "exportacao", "debug"),
            ]
            for debug_dir in debug_dirs:
                os.makedirs(debug_dir, exist_ok=True)
                try:
                    driver.save_screenshot(os.path.join(debug_dir, "gal_login_fail.png"))
                except Exception:
                    pass
                try:
                    with open(
                        os.path.join(debug_dir, "gal_login_fail.html"),
                        "w",
                        encoding="utf-8",
                    ) as f:
                        f.write(driver.page_source)
                except Exception:
                    pass
                try:
                    self.log(f"Debug artifacts gravados: {debug_dir}", "info")
                except Exception:
                    pass
        except Exception:
            pass

    @retry_with_backoff()
    def buscar_metadados(
        self, http_client: Any, codigos_amostra_set: Set[str], exam_cfg: Any = None
    ) -> Dict[str, Any]:
        encontrados = {}
        url = self.base_url + self.endpoints.get("metadata")
        limit = 500

        gal_exame_codigo = getattr(exam_cfg, "gal_exame_codigo", "") if exam_cfg else ""
        nome_exame = getattr(exam_cfg, "nome_exame", "") if exam_cfg else ""
        panel_tests_id = str(getattr(exam_cfg, "panel_tests_id", "")) if exam_cfg else ""

        self.log(
            f"Iniciando busca de metadados para {len(codigos_amostra_set)} amostras.",
            "info",
        )
        
        from datetime import datetime, timedelta
        hoje = datetime.now()
        dt_inicio_str = (hoje - timedelta(days=15)).strftime("%d/%m/%Y")
        dt_fim_str = hoje.strftime("%d/%m/%Y")
        
        payload_inicial = {"limit": limit, "start": 0, "dtInicio": dt_inicio_str, "dtFim": dt_fim_str}
        if gal_exame_codigo:
            payload_inicial["codExame"] = gal_exame_codigo

        resp = http_client.request(
            "POST",
            url,
            data=payload_inicial,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        total = data.get("total", 0)

        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        lock = threading.Lock()

        def _process_page(start_idx, page_data=None):
            if page_data is None:
                payload = {"limit": limit, "start": start_idx, "dtInicio": dt_inicio_str, "dtFim": dt_fim_str}
                if gal_exame_codigo:
                    payload["codExame"] = gal_exame_codigo
                
                retries = 3
                for attempt in range(retries):
                    try:
                        r = http_client.request("POST", url, data=payload, timeout=self.timeout)
                        r.raise_for_status()
                        page_data = r.json().get("dados", [])
                        break
                    except Exception as e:
                        if attempt == retries - 1:
                            raise e
                        time.sleep(2)
            
            local_encontrados = {}
            for ex in page_data:
                ca = str(ex.get("codigoAmostra", "")).strip()
                if ca not in codigos_amostra_set:
                    continue

                is_valid_exam = True
                if exam_cfg:
                    exame_retornado = str(ex.get("nomeExame", ex.get("exame", ex.get("descricaoExame", "")))).strip().upper()
                    codigo_retornado = str(ex.get("codExame", ex.get("codigoExame", ""))).strip().upper()
                    painel_retornado = str(ex.get("painel", ex.get("idPainel", ex.get("idPainelTeste", "")))).strip().upper()

                    match_exame = False
                    if gal_exame_codigo and (gal_exame_codigo.upper() == codigo_retornado or gal_exame_codigo.upper() in exame_retornado):
                        match_exame = True
                    elif nome_exame and nome_exame.upper() in exame_retornado:
                        match_exame = True
                    elif panel_tests_id and panel_tests_id.upper() in painel_retornado:
                        match_exame = True

                    if not match_exame and (gal_exame_codigo or nome_exame or panel_tests_id):
                        if exame_retornado != "":
                            is_valid_exam = False

                if is_valid_exam:
                    local_encontrados[ca] = ex

            with lock:
                for ca, ex in local_encontrados.items():
                    if ca not in encontrados or ex.get("codigo", 0) > encontrados[ca].get("codigo", 0):
                        encontrados[ca] = ex

        # Processa a primeira página já carregada
        _process_page(0, page_data=data.get("dados", []))
        
        # Processa as próximas páginas em paralelo
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for start in range(limit, total, limit):
                futures.append(executor.submit(_process_page, start))
                
            # S5: Acumular falhas de páginas para aviso explícito ao final
            failed_pages: list = []
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    failed_pages.append(str(e))

            if failed_pages:
                sample = "; ".join(failed_pages[:3])
                suffix = f"... (+{len(failed_pages) - 3} outras)" if len(failed_pages) > 3 else ""
                self.log(
                    f"[S5] AVISO: {len(failed_pages)} pagina(s) de metadados nao carregaram. "
                    f"Algumas amostras podem aparecer como 'nao_encontrado'. "
                    f"Detalhes: {sample}{suffix}",
                    "warning",
                )

        self.log(
            f"Busca de metadados finalizada: {len(encontrados)} encontrados.", "info"
        )
        return encontrados

    def construir_payload(
        self, meta: Dict, row: pd.Series, observacao_geral: str, exam_cfg: Any = None
    ) -> Dict[str, Any]:
        """
        Monta o payload exatamente no espírito dos scripts antigos:
        - Usa o painel para decidir quais testes entram em `resultados`
        - Converte valores para inteiro quando possível, caso contrário usa None
        - Respeita colunas opcionais `valorReferencia` e `observacao` do CSV, se existirem
        - Combina observação da amostra com observação geral da corrida
        """
        # Painel e lista de testes (preferir metadados do GAL quando disponíveis)
        def _get_meta_value(meta_dict: Dict, keys: List[str]):
            for k in keys:
                if k in meta_dict:
                    val = meta_dict.get(k)
                    if val is not None and str(val).strip() != "":
                        return val
            return None

        def _to_int(val):
            try:
                sval = str(val).strip()
                return int(sval) if sval.isdigit() else None
            except Exception:
                return None

        painel_meta = _get_meta_value(meta, ["painel", "idPainel", "idPainelTeste", "painelTeste"])
        painel_row = row.get("painel", 1)
        painel = _to_int(painel_meta)
        if painel is None or str(painel) not in self.panel_tests:
            painel = _to_int(painel_row) or 1

        testes_do_painel = self.panel_tests.get(str(painel), [])

        # Fallback: quando o painel nao esta na config GAL e o exame tem
        # export_fields definido, deriva os testes a partir dele.
        # Isso garante que exames novos (sem entrada em DEFAULT_PANEL_TESTS /
        # gal_config.panel_tests) enviem os campos corretos sem editar config.json.
        if not testes_do_painel and exam_cfg:
            raw_ef = list(getattr(exam_cfg, "export_fields", []) or [])
            if raw_ef:
                testes_do_painel = [_norm_gal_field(f) for f in raw_ef if str(f).strip()]

        # Montagem de resultados
        resultados: Dict[str, Any] = {"resultado": None}
        for teste in testes_do_painel:
            # As colunas foram normalizadas para minúsculas no carregamento do CSV
            col_name = teste.lower()
            if col_name not in row.index:
                continue  # evita enviar campos não presentes no CSV
            raw = row.get(col_name, None)
            if pd.isna(raw) or str(raw).strip() == "":
                resultados[teste] = None
            else:
                try:
                    resultados[teste] = int(raw)
                except (ValueError, TypeError):
                    resultados[teste] = None

        # Campos de identificação / metadados
        codigo_amostra = str(row.get("codigoamostra", "")).strip()
        metodo = _get_meta_value(meta, ["metodo", "metodologia"]) or "RT-PCR em tempo real"
        
        fallback_exame = getattr(exam_cfg, "nome_exame", "") if exam_cfg else "Vírus Respiratórios"
        exame = _get_meta_value(meta, ["exame", "nomeExame", "descricaoExame"]) or fallback_exame

        # Campos opcionais vindos do CSV, se existirem, com limpeza de NaN
        valor_referencia = row.get("valorreferencia", "")
        if pd.isna(valor_referencia):
            valor_referencia = ""

        obs_csv = row.get("observacao", "")
        if pd.isna(obs_csv):
            obs_csv = ""

        # Política de observação:
        # - se a linha tiver observação, ela é priorizada
        # - a observação geral da corrida é concatenada quando ambas existem
        if obs_csv and observacao_geral:
            observacao_final = f"{str(obs_csv).strip()} | {observacao_geral}"
        elif obs_csv:
            observacao_final = str(obs_csv).strip()
        else:
            observacao_final = observacao_geral

        data_proc = row.get("dataprocessamentofim", None)
        if pd.isna(data_proc) or str(data_proc).strip() == "":
            data_proc_str = datetime.now().strftime("%d/%m/%Y")
        else:
            data_proc_str = str(data_proc)

        kit_val = _get_meta_value(meta, ["kit", "kitCodigo", "kit_codigo"])
        if kit_val is None:
            kit_val = row.get("kit")
        kit_int = (
            int(kit_val)
            if kit_val is not None and str(kit_val).strip().isdigit()
            else None
        )

        # codigo = codigoAmostra quando meta vazio (modo sem metadados ou metadata ausente).
        # O GAL localiza o registro pelo par codigo+gal_exame_codigo — ambos sempre disponíveis.
        _codigo_meta = str(meta.get("codigo", "") or "").strip()
        _codigo_final = _codigo_meta if _codigo_meta else codigo_amostra

        return {
            "codigo": _codigo_final,
            "requisicao": meta.get("requisicao", ""),
            "paciente": meta.get("paciente", ""),
            "exame": exame,
            "metodo": metodo,
            "registroInterno": codigo_amostra,
            "kit": kit_int,
            "reteste": "",  # mantido vazio como nos scripts antigos
            "loteKit": str(row.get("lotekit", "")),
            "dataProcessamentoIni": "",
            "dataProcessamentoFim": data_proc_str,
            "valorReferencia": valor_referencia,
            "observacao": observacao_final,
            "painel": painel,
            "resultados": resultados,
        }

    def _validar_campo(
        self, driver: WebDriver, payload_base: Dict, campo: str, valor: Any
    ) -> Optional[str]:
        """
        Valida um único campo de `resultados`, reproduzindo a lógica dos scripts antigos:
        - Envia somente o campo em questão
        - Considera como sucesso tanto respostas com `status == "sucesso"` quanto `success == True`
        - Em caso de falha, retorna a mensagem de erro
        """
        tmp_payload = payload_base.copy()
        tmp_payload["resultados"] = {"resultado": None, campo: valor}
        url = self.base_url + self.endpoints.get("submit")

        resp = driver.request(
            "POST",
            url,
            data={"exame": json.dumps(tmp_payload, ensure_ascii=False)},
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=self.timeout,
        )

        try:
            data = resp.json()
        except json.JSONDecodeError:
            return f"Resposta inválida do servidor (HTTP {resp.status_code})"

        ok_status = data.get("status") == "sucesso"
        ok_success = data.get("success") is True

        if resp.status_code == 200 and (ok_status or ok_success):
            return None

        motivo = (
            data.get("errorMsg")
            or data.get("message")
            or data.get("mensagem")
            or data.get("error")
            or data.get("erro")
            or f"Erro desconhecido (HTTP {resp.status_code})"
        )
        return motivo

    def _enviar_payload_completo(
        self, driver: WebDriver, payload: Dict
    ) -> Tuple[bool, Any]:
        """
        Envia o payload completo para o GAL.
        Compatível com a lógica dos scripts antigos, que verificavam `success == True`
        na resposta JSON do endpoint de gravação.
        """
        url = self.base_url + self.endpoints.get("submit")
        resp = driver.request(
            "POST",
            url,
            data={"exame": json.dumps(payload, ensure_ascii=False)},
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=self.timeout,
        )
        # Não chamamos raise_for_status aqui para poder inspecionar a resposta mesmo em HTTP 4xx/5xx
        try:
            data = resp.json()
        except json.JSONDecodeError:
            # devolvemos também o corpo bruto para inspeção em log
            return False, {
                "message": "Resposta inválida do servidor (não é JSON)",
                "_http_status": resp.status_code,
                "_raw": resp.text[:500],
            }
        # Acrescenta metadados úteis para diagnóstico
        data.setdefault("_http_status", resp.status_code)
        # Guarda um recorte do corpo bruto para inspeção futura
        try:
            raw_text = resp.text
        except Exception:
            raw_text = ""
        if "_raw" not in data and raw_text:
            data["_raw"] = raw_text[:500]

        # Scripts antigos consideravam sucesso quando `success` era True
        success = bool(data.get("success") is True)
        return success, data

    def _extract_transaction_id(self, response: Dict[str, Any]) -> str:
        """
        Extrai o ID de transacao da resposta do GAL, quando disponivel.

        Args:
            response: JSON de resposta do GAL.

        Returns:
            ID da transacao ou string vazia.
        """
        if not isinstance(response, dict):
            return ""

        candidates: List[Dict[str, Any]] = [response]
        for key in ("data", "dados", "resultado", "result"):
            value = response.get(key)
            if isinstance(value, dict):
                candidates.append(value)

        keys = (
            "idTransacao",
            "id_transacao",
            "transactionId",
            "transaction_id",
            "protocolo",
            "codigo",
            "id",
        )

        for candidate in candidates:
            for key in keys:
                value = candidate.get(key)
                if value is not None and str(value).strip():
                    return str(value)
        return ""

    def enviar_amostra(self, driver: WebDriver, payload: Dict) -> Dict[str, Any]:
        payload_validacao = GalPayloadDTO.from_legacy_payload(payload).to_legacy_payload()

        ca = payload_validacao.get("registroInterno")
        paciente = payload_validacao.get("paciente")
        paciente_masked = mask_patient_name(paciente)
        resultado: Dict[str, Any] = {
            "codigoAmostra": ca,
            "paciente": paciente,
            "status": "",
            "erro": [],
            "campos_invalidos": [],
            "transaction_id": "",
            "ts_sucesso": "",
        }

        try:
            payload_errors = validate_gal_payload(payload_validacao)
            if payload_errors:
                erro_payload = "; ".join(payload_errors)
                self.log(
                    "Payload GAL invalido "
                    f"(schema_version={GAL_PAYLOAD_SCHEMA_VERSION}, amostra={ca}): {erro_payload}",
                    "error",
                )
                raise GalPayloadValidationError(erro_payload)

            self.log(
                f"A enviar payload para {ca} (Paciente: {paciente_masked or '[oculto]'})",
                "info",
            )
            success, response = self._enviar_payload_completo(driver, payload_validacao)

            if success:
                resultado["status"] = "sucesso"
                resultado["transaction_id"] = self._extract_transaction_id(response)
                resultado["ts_sucesso"] = datetime.now().isoformat()
                return resultado

            # Falha no envio: tentar extrair mensagem mais informativa
            msg = (
                response.get("errorMsg")
                or response.get("message")
                or response.get("mensagem")
                or response.get("error")
                or response.get("erro")
            )
            http_status = response.get("_http_status", "desconhecido")
            if not msg:
                msg = f"Erro não especificado (HTTP {http_status})"

            resultado["status"] = "erro"
            resultado["erro"].append(msg)

            # Loga erro principal e resposta completa para diagnóstico
            self.log(
                f"Erro no envio de {ca}: {msg}. A iniciar validação de campos.", "error"
            )
            try:
                # S14: Mascarar campos identificáveis antes de logar resposta do servidor
                _SENSITIVE_KEYS = frozenset(
                    ("paciente", "nomePaciente", "patient", "nome", "_raw")
                )
                safe_response = {
                    k: ("***" if k in _SENSITIVE_KEYS else v)
                    for k, v in response.items()
                } if isinstance(response, dict) else response
                self.log(
                    f"Resposta completa do servidor para {ca}: {safe_response}", "warning"
                )
            except Exception:
                pass

            # Validação campo a campo, como nos scripts antigos
            testes_do_painel = self.panel_tests.get(str(payload_validacao.get("painel", 1)), [])
            for teste in testes_do_painel:
                val = payload_validacao["resultados"].get(teste)
                if val is not None:
                    motivo = self._validar_campo(driver, payload_validacao, teste, val)
                    if motivo:
                        resultado["campos_invalidos"].append(
                            {
                                "campo": teste,
                                "valor": val,
                                "motivo": motivo,
                            }
                        )

            # Log detalhado dos campos inválidos, se houver
            if resultado["campos_invalidos"]:
                self.log(f"Campos inválidos identificados para {ca}:", "warning")
                for problema in resultado["campos_invalidos"]:
                    self.log(
                        f"  - {problema['campo']} = {problema['valor']}: {problema['motivo']}",
                        "warning",
                    )

            return resultado

        except Exception as e:
            resultado["status"] = "erro_critico"
            resultado["erro"].append(f"Erro inesperado no envio: {e}")
            self.log(f"Erro inesperado no envio de {ca}: {e}", "critical")
            return resultado

    def ler_csv_resultados(self, csv_path: str) -> Optional[pd.DataFrame]:
        df = read_data_with_auto_detection(csv_path)
        if df is None or df.empty:
            self.log("Arquivo CSV vazio ou ilegível.", "critical")
            return None

        df.columns = [str(col).strip().replace(" ", "").lower() for col in df.columns]
        required = ["kit", "painel", "dataprocessamentofim", "codigoamostra"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            self.log(
                f"Colunas obrigatórias em falta no CSV: {', '.join(missing)}",
                "critical",
            )
            return None

        df.dropna(subset=[c for c in required if c != "codigoamostra"], inplace=True)
        df["codigoamostra"] = (
            df["codigoamostra"]
            .astype(str)
            .str.strip()
            .str.replace(".0", "", regex=False)
        )
        df.drop(df[df["codigoamostra"] == ""].index, inplace=True)
        self.log(f"CSV lido e validado. {len(df)} registos processáveis.", "info")
        return df

    def build_idempotency_key(
        self,
        *,
        codigo_amostra: str,
        kit: str,
        lote_kit: str,
        data_exame: str,
        corrida_id: str = "",
        nome_corrida: str = "",
        arquivo_corrida: str = "",
        placa: str = "",
        parte_placa: object = "",
    ) -> str:
        """Delega construção da chave de idempotência ao módulo contratual."""
        return build_idempotency_key(
            codigo_amostra=codigo_amostra,
            kit=kit,
            lote_kit=lote_kit,
            data_exame=data_exame,
            corrida_id=corrida_id,
            nome_corrida=nome_corrida,
            arquivo_corrida=arquivo_corrida,
            placa=placa,
            parte_placa=parte_placa,
        )

    def get_transaction_journal_path(self) -> Path:
        """Resolve caminho padrão do journal de transações GAL."""
        log_dir = Path(PATHS_CONFIG.get("log_file", "logs/sistema.log")).parent
        return default_transaction_journal_path(log_dir)

    def load_successful_idempotency_keys(self, journal_path: Path) -> Set[str]:
        """Carrega chaves de idempotência já enviadas com sucesso."""
        try:
            legacy_path = default_success_transactions_path(journal_path.parent)
            reconciliation = reconcile_legacy_success_into_journal(
                journal_path=journal_path,
                legacy_success_path=legacy_path,
                kit_default="",
            )
            if reconciliation["appended_to_journal"] > 0:
                self.log(
                    "Reconciliacao GAL pre-envio aplicada: "
                    f"{reconciliation['appended_to_journal']} eventos legado incorporados.",
                    "info",
                )
            return load_successful_idempotency_keys(journal_path)
        except (OSError, ValueError) as exc:
            self.log(
                f"Falha ao carregar idempotência do journal '{journal_path}': {exc}",
                "warning",
            )
            return set()

    def get_user_access_level(self, username: str) -> Optional[str]:
        """Resolve nivel de acesso atual do usuario no backend de autenticacao."""
        try:
            user = AuthService().obter_usuario(username)
        except Exception as exc:  # noqa: BLE001 - caminho defensivo
            self.log(f"Falha ao resolver nivel de acesso para '{username}': {exc}", "warning")
            return None
        if not user:
            return None
        return str(user.get("nivel_acesso", "") or "").strip().upper() or None

    def append_journal_events(
        self,
        *,
        relatorio_local: List[Dict[str, Any]],
        run_id: str,
        kit_default: str,
    ) -> int:
        """Persiste eventos no journal oficial com dedupe por identidade."""
        journal_rows = build_transaction_journal_rows(
            relatorio_local,
            run_id=run_id,
            kit_default=str(kit_default),
        )
        if not journal_rows:
            return 0
        journal_path = self.get_transaction_journal_path()
        result = append_transaction_journal_unique(journal_path, journal_rows)
        appended = int(result.get("appended_rows", 0))
        skipped = int(result.get("skipped_duplicates", 0))
        if appended > 0:
            self.log(
                f"Journal GAL registrado com {appended} eventos em {journal_path}",
                "info",
            )
        if skipped > 0:
            self.log(
                f"Journal GAL dedupe: {skipped} eventos duplicados ignorados em {journal_path}",
                "debug",
            )
        return appended

    def _append_upload_history_csv(
        self,
        *,
        caminho_historico: str,
        df_sucesso: pd.DataFrame,
        final_cols: List[str],
    ) -> None:
        """Persistencia contratual do historico de upload GAL com escrita atomica."""
        history_path = Path(caminho_historico)
        history_path.parent.mkdir(parents=True, exist_ok=True)
        policy = RetryPolicy.from_env()

        incoming_df = df_sucesso.copy()
        for col in final_cols:
            if col not in incoming_df.columns:
                incoming_df[col] = None
        incoming_df = incoming_df.reindex(columns=final_cols).fillna("")

        if path_exists_with_retry(history_path, policy=policy):
            try:
                existing_df = read_csv_strict(
                    history_path,
                    contract_name=_GAL_UPLOAD_HISTORY_CONTRACT_NAME,
                    policy=policy,
                )
            except Exception as strict_exc:
                if not is_contractual_csv_legacy_fallback_enabled():
                    raise ValueError(
                        "Historico GAL contratual invalido "
                        f"(fallback legado desativado): {strict_exc}"
                    ) from strict_exc
                self.log(
                    f"Historico GAL legado detectado; fallback de leitura habilitado por flag: {strict_exc}",
                    "warning",
                )
                existing_df = call_with_retry(
                    lambda: pd.read_csv(
                        history_path,
                        sep=_GAL_UPLOAD_HISTORY_DELIMITER,
                        encoding=_GAL_UPLOAD_HISTORY_ENCODING,
                    ),
                    op_name="read_gal_upload_history_legacy",
                    path=history_path,
                    policy=policy,
                )

            for col in final_cols:
                if col not in existing_df.columns:
                    existing_df[col] = ""
            existing_df = existing_df.reindex(columns=final_cols).fillna("")
            merged_df = pd.concat([existing_df, incoming_df], ignore_index=True)
        else:
            merged_df = incoming_df

        rows = [
            {col: sanitize_csv_value(record.get(col, "")) for col in final_cols}
            for record in merged_df.to_dict(orient="records")
        ]
        write_csv_atomic(
            history_path,
            rows=rows,
            fieldnames=final_cols,
            contract_name=_GAL_UPLOAD_HISTORY_CONTRACT_NAME,
            policy=policy,
        )

    def salvar_relatorios(
        self,
        relatorio_final: List[Dict],
        relatorio_local: List[Dict],
        usuario: str,
        observacao: str,
        kit: str,
        relatorio_filename: str,
        run_id: Optional[str] = None,
    ):
        log_dir = os.path.dirname(PATHS_CONFIG.get("log_file"))
        os.makedirs(log_dir, exist_ok=True)
        effective_run_id = run_id or datetime.now().strftime("%Y%m%dT%H%M%S")
        relatorio_csv_path = Path(log_dir) / "relatorio.csv"
        journal_path = self.get_transaction_journal_path()

        if relatorio_final:
            df_sucesso = pd.DataFrame(relatorio_final)
            # Garante coluna codigoAmostra preenchida (compatível com histórico antigo)
            if (
                "codigoAmostra" not in df_sucesso.columns
                and "registroInterno" in df_sucesso.columns
            ):
                df_sucesso["codigoAmostra"] = df_sucesso["registroInterno"]
            elif (
                "codigoAmostra" in df_sucesso.columns
                and df_sucesso["codigoAmostra"].isna().any()
                and "registroInterno" in df_sucesso.columns
            ):
                df_sucesso["codigoAmostra"] = df_sucesso["codigoAmostra"].fillna(
                    df_sucesso["registroInterno"]
                )
            caminho_historico = (
                PATHS_CONFIG.get("gal_upload_history_csv")
                or PATHS_CONFIG.get("gal_history_csv")
                or str(Path(log_dir) / "gal_upload_history.csv")
            )
            os.makedirs(os.path.dirname(caminho_historico), exist_ok=True)
            all_cols_base = [
                "codigoAmostra",
                "metodo",
                "registroInterno",
                "kit",
                "reteste",
                "loteKit",
                "dataProcessamentoFim",
                "valorReferencia",
                "observacao",
                "painel",
                "usuario",
                "timestamp",
            ]
            all_tests = set()
            for tests in self.panel_tests.values():
                all_tests.update(tests)
            final_cols = all_cols_base + sorted(list(all_tests))

            for col in final_cols:
                if col not in df_sucesso.columns:
                    df_sucesso[col] = None

            self._append_upload_history_csv(
                caminho_historico=caminho_historico,
                df_sucesso=df_sucesso,
                final_cols=final_cols,
            )
            self.log(f"Histórico de {len(relatorio_final)} sucessos salvo.", "success")

        try:
            rows = build_relatorio_rows(
                relatorio_local=relatorio_local,
                usuario=usuario,
                kit=kit,
                observacao=observacao,
                run_id=effective_run_id,
            )
            write_relatorio_csv(relatorio_csv_path, rows)
            self.log(
                f"Relatorio CSV salvo com {len(rows)} amostras: {relatorio_csv_path}",
                "info",
            )

            journal_rows = build_transaction_journal_rows(
                relatorio_local,
                run_id=effective_run_id,
                kit_default=str(kit),
            )
            result = append_transaction_journal_unique(journal_path, journal_rows)
            appended = int(result.get("appended_rows", 0))
            skipped = int(result.get("skipped_duplicates", 0))
            if appended > 0:
                self.log(
                    f"Journal GAL registrado com {appended} eventos em {journal_path}",
                    "info",
                )
            if skipped > 0:
                self.log(
                    f"Journal GAL dedupe: {skipped} eventos duplicados ignorados em {journal_path}",
                    "debug",
                )

            legacy_success_path = default_success_transactions_path(log_dir)
            reconciliation = reconcile_legacy_success_into_journal(
                journal_path=journal_path,
                legacy_success_path=legacy_success_path,
                kit_default=str(kit),
            )
            if reconciliation["appended_to_journal"] > 0:
                self.log(
                    "Reconciliacao GAL aplicada no journal oficial: "
                    f"{reconciliation['appended_to_journal']} eventos legado incorporados.",
                    "info",
                )

            if is_legacy_gal_success_ledger_enabled():
                success_rows = build_success_transaction_rows(relatorio_local, run_id)
                append_success_transactions(legacy_success_path, success_rows)
                if success_rows:
                    self.log(
                        "Ledger legado gal_transacoes_sucesso.csv atualizado em modo "
                        f"compatibilidade: {len(success_rows)} linhas.",
                        "warning",
                    )
        except (OSError, ValueError) as exc:
            self.log(f"Falha ao salvar relatorio.csv: {exc}", "warning")

        caminho_relatorio = os.path.join(log_dir, relatorio_filename)
        policy = RetryPolicy.from_env()
        with CSVFileLock(caminho_relatorio), open_with_retry(
            caminho_relatorio, "w", encoding="utf-8", policy=policy
        ) as f:
            f.write(
                f"Relatório de Envio ao GAL - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            f.write(f"Usuário: {usuario}\nKit: {kit}\nObservação: {observacao}\n\n")
            for item in relatorio_local:
                paciente_masked = mask_patient_name(item.get("paciente", ""))
                f.write(
                    f"- Amostra: {item['codigoAmostra']} (Paciente: {paciente_masked or '[oculto]'})\n"
                )
                f.write(f"  Status: {item['status']}\n")
                if item.get("erro"):
                    f.write(f"  Erros: {'; '.join(map(str, item['erro']))}\n")
                if item.get("campos_invalidos"):
                    invalidos_str = "; ".join(
                        [
                            f"{inv['campo']}='{inv['valor']}' ({inv['motivo']})"
                            for inv in item["campos_invalidos"]
                        ]
                    )
                    f.write(f"  Campos Inválidos: {invalidos_str}\n")
                f.write("\n")
        self.log(f"Relatório detalhado salvo em: {caminho_relatorio}", "info")
        try:
            upsert_final_report_with_send_results(
                logs_dir=Path(log_dir),
                run_id=effective_run_id,
                relatorio_local=relatorio_local,
                relatorio_csv_path=relatorio_csv_path,
                journal_path=journal_path,
                relatorio_txt_path=Path(caminho_relatorio),
                context=dict(self._runtime_context),
            )
        except Exception as exc:
            self.log(
                f"Falha ao atualizar relatorio final canonico apos envio GAL: {exc}",
                "warning",
            )
        try:
            sync_summary = reconcile_send_status_across_artifacts(
                relatorio_local=relatorio_local,
                context=dict(self._runtime_context),
                logs_dir=Path(log_dir),
            )
            self.log(
                "Sincronizacao pos-envio GAL concluida: "
                f"{sync_summary}",
                "info",
            )
        except Exception as exc:
            self.log(
                f"Falha na sincronizacao pos-envio GAL (fallback seguro): {exc}",
                "warning",
            )


# ==============================================================================
# 3. CLASSE DE INTERFACE GRÁFICA (UI) - COM FEEDBACK MELHORADO
# ==============================================================================
class IntegrationApp(ctk.CTkFrame):
    def __init__(
        self,
        master,
        usuario_logado: str,
        app_state: Optional[Any] = None,
        *,
        host_frame: Optional[ctk.CTkFrame] = None,
        on_close_callback: Optional[Callable[[], None]] = None,
    ):
        # Importar AfterManagerMixin dinamicamente para evitar circular imports
        from utils.after_mixin import AfterManagerMixin
        
        # Atualizar a herança com AfterManagerMixin no __init__
        # Como não podemos alterar a lista de herança aqui, vamos usar composição
        self._after_ids = set()

        self._is_page_mode = host_frame is not None
        self._window: Optional[ctk.CTkToplevel] = None
        self._on_close_callback = on_close_callback

        if self._is_page_mode:
            super().__init__(host_frame)
            self.pack(fill="both", expand=True)
        else:
            self._window = ctk.CTkToplevel(master)
            super().__init__(self._window)
            self.pack(fill="both", expand=True)
            self._window.title("Envio de Resultados para o GAL")
            self._window.geometry("900x800")

        self.usuario_logado = usuario_logado
        self.app_state = app_state
        self.gal_service = GalService(
            self.log_to_textbox,
            runtime_context=self._build_runtime_context(),
        )
        self.gal_send_use_case = GalSendUseCase(self.gal_service)
        self.gal_ui_input_adapter = GalUIInputAdapter(self.log_to_textbox)
        self.gal_ui_dialog_adapter = GalUIDialogAdapter()

        self.current_csv_path: Optional[str] = None
        self.observacao: str = ""
        self.relatorio_filename: str = ""
        
        # Flag para controle de thread em execução
        self._processing = False
        self._thread = None
        
        # Carrega config do exame se disponível
        self.exam_cfg = None
        if self.app_state:
            try:
                exame = getattr(self.app_state, "exame_selecionado", None)
                if exame:
                    self.exam_cfg = get_exam_cfg(exame)
            except Exception:
                self.exam_cfg = None

        self._criar_widgets()
        if self._window is not None:
            self._window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _dialog_parent(self):
        if self._window is not None:
            return self._window
        return self.winfo_toplevel()

    def _build_runtime_context(self) -> Dict[str, Any]:
        app_state = self.app_state
        return {
            "corrida_id": str(getattr(app_state, "corrida_id", "") or ""),
            "exame_id": str(getattr(app_state, "exame_selecionado", "") or ""),
            "lote": str(getattr(app_state, "lote", "") or ""),
            "data_exame": str(getattr(app_state, "data_exame", "") or ""),
            "arquivo_corrida": str(getattr(app_state, "caminho_arquivo_corrida", "") or ""),
            "arquivo_extracao": str(
                getattr(app_state, "caminho_arquivo_extracao", "") or ""
            ),
            "parte_placa": int(getattr(app_state, "parte_placa", 0) or 0),
            "numero_extracao": str(getattr(app_state, "numero_extracao", "") or ""),
            "usuario_execucao": str(self.usuario_logado or ""),
            "observacoes": str(getattr(app_state, "observacoes_corrida", "") or ""),
            "nome_corrida": str(getattr(app_state, "nome_corrida", "") or ""),
            "quem_fez_extracao": str(
                getattr(app_state, "quem_fez_extracao", "") or ""
            ),
            "quem_preparou_placa": str(
                getattr(app_state, "quem_preparou_placa", "") or ""
            ),
        }

    def _criar_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        top_frame = ctk.CTkFrame(self)
        top_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        top_frame.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(top_frame, text="Utilizador:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self.usuario_entry = ctk.CTkEntry(top_frame)
        self.usuario_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(top_frame, text="Senha:").grid(
            row=0, column=2, padx=5, pady=5, sticky="w"
        )
        self.senha_entry = ctk.CTkEntry(top_frame, show="*")
        self.senha_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        self.csv_button = ctk.CTkButton(
            top_frame, text="Selecionar Arquivo CSV", command=self.selecionar_csv
        )
        self.csv_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        self.csv_label = ctk.CTkLabel(top_frame, text="Nenhum arquivo selecionado")
        self.csv_label.grid(row=1, column=2, columnspan=2, padx=5, pady=5, sticky="ew")

        self.start_button = ctk.CTkButton(
            top_frame,
            text="Iniciar Processamento",
            command=self.iniciar_processamento,
            state="disabled",
        )
        self.start_button.grid(
            row=2, column=0, columnspan=4, padx=5, pady=10, sticky="ew"
        )


        progress_frame = ctk.CTkFrame(self)
        progress_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(progress_frame, text="Status: Pronto")
        self.status_label.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        self.progress_bar = ctk.CTkProgressBar(progress_frame, orientation="horizontal")
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")

        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_text = ctk.CTkTextbox(log_frame, wrap="word")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_text.configure(state="disabled")

    def _update_progress(self, text: str, value: float, color: str = "default"):
        def update():
            self.status_label.configure(text=f"Status: {text}")
            self.progress_bar.set(value)
            if color == "green":
                self.progress_bar.configure(progress_color="green")
            elif color == "red":
                self.progress_bar.configure(progress_color="red")
            else:
                self.progress_bar.configure(progress_color=["#3a7ebf", "#1f538d"])

        self.after(0, update)

    def log_to_textbox(self, message: str, level: str = "info"):
        level = level.lower()
        formatted_msg = (
            f"[{datetime.now().strftime('%H:%M:%S')}] {level.upper()}: {message}\n"
        )

        def update_log():
            self.log_text.configure(state="normal")
            color_map = {
                "error": "red",
                "warning": "orange",
                "critical": "darkred",
                "success": "green",
            }
            tag = color_map.get(level)
            if tag and tag not in self.log_text.tag_names():
                self.log_text.tag_config(tag, foreground=tag)

            self.log_text.insert("end", formatted_msg, tag if tag else None)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

        self.after(0, update_log)
        registrar_log("Envio GAL UI", message, level=level.upper())

    def selecionar_csv(self):
        dialog_result = self.gal_ui_dialog_adapter.collect(self._dialog_parent())
        if dialog_result is None:
            return

        path = dialog_result.csv_path
        self.current_csv_path = path
        self.csv_label.configure(text=os.path.basename(path))
        self.observacao = dialog_result.observacao
        self.relatorio_filename = dialog_result.relatorio_filename

        self.start_button.configure(state="normal")
        self.log_to_textbox(
            f"Arquivo '{os.path.basename(path)}' pronto para envio.", "info"
        )

    def iniciar_processamento(self):
        """Valida entradas e inicia o envio em thread separada."""
        usuario = self.usuario_entry.get().strip()
        senha = self.senha_entry.get().strip()
        runtime_context = self._build_runtime_context()
        self.gal_service.set_runtime_context(**runtime_context)
        state = GalUIInputState(
            processing=self._processing,
            csv_path=self.current_csv_path or "",
            usuario=usuario,
            senha=senha,
            usuario_logado=self.usuario_logado,
            usuario_nivel=str(getattr(self.app_state, "nivel_acesso", "") or ""),
            observacao=self.observacao,
            relatorio_filename=self.relatorio_filename,
            corrida_id=str(runtime_context.get("corrida_id", "") or ""),
            exame_id=str(runtime_context.get("exame_id", "") or ""),
            lote=str(runtime_context.get("lote", "") or ""),
            data_exame=str(runtime_context.get("data_exame", "") or ""),
            arquivo_corrida=str(runtime_context.get("arquivo_corrida", "") or ""),
            arquivo_extracao=str(runtime_context.get("arquivo_extracao", "") or ""),
            parte_placa=int(runtime_context.get("parte_placa", 0) or 0),
            numero_extracao=str(runtime_context.get("numero_extracao", "") or ""),
            nome_corrida=str(runtime_context.get("nome_corrida", "") or ""),
            quem_fez_extracao=str(runtime_context.get("quem_fez_extracao", "") or ""),
            quem_preparou_placa=str(
                runtime_context.get("quem_preparou_placa", "") or ""
            ),
            observacoes_corrida=str(runtime_context.get("observacoes", "") or ""),
        )

        issue = self.gal_ui_input_adapter.validate_for_start(state)
        if issue is not None:
            if issue.severity == "info":
                messagebox.showinfo(issue.title, issue.message, parent=self._dialog_parent())
            else:
                messagebox.showwarning(issue.title, issue.message, parent=self._dialog_parent())
            return

        request = self.gal_ui_input_adapter.build_request(state)

        self._processing = True
        self.start_button.configure(state="disabled")
        self.csv_button.configure(state="disabled")
        self._update_progress("Iniciando processamento...", 0.0)
        self.log_to_textbox("Processamento iniciado.", "info")

        self._thread = threading.Thread(
            target=self._processar_em_background, args=(request,), daemon=True
        )
        self._thread.start()



    def _on_close(self):
        """Fecha a janela com seguranca, cancelando callbacks e threads."""
        try:
            # Cancelar todos os callbacks agendados (via AfterManagerMixin pattern)
            for aid in self._after_ids:
                try:
                    self.after_cancel(aid)
                except Exception:
                    pass
            self._after_ids.clear()

            # Avisar se ha processamento em andamento
            if self._processing:
                resposta = messagebox.askyesno(
                    "Processamento em Andamento",
                    "Ha um envio em andamento. Deseja realmente fechar?\n\n"
                    "Nota: O processamento continuara em segundo plano.",
                    parent=self._dialog_parent()
                )
                if not resposta:
                    return

            if self._is_page_mode:
                if self._on_close_callback is not None:
                    self._on_close_callback()
                else:
                    self.destroy()
                return

            if self._window is not None:
                safe_destroy_ctk_toplevel(self._window)
            else:
                safe_destroy_ctk_toplevel(self)
        except Exception as e:
            registrar_log("IntegrationApp", f"Erro ao fechar janela: {e}", "ERROR")
            try:
                if self._window is not None:
                    safe_destroy_ctk_toplevel(self._window)
                else:
                    safe_destroy_ctk_toplevel(self)
            except Exception:
                pass

    def _processar_em_background(self, request: GalSendRequest):
        resumo = ""
        is_sucesso = False
        try:
            result = self.gal_send_use_case.execute(
                request,
                progress_callback=self._update_progress,
            )
            self._update_progress(
                f"Processamento concluído com {result.sucessos} sucesso(s)!",
                1.0,
                "green",
            )
            
            resumo = (
                f"Processo de envio finalizado!\n\n"
                f"Total de Amostras: {result.total_amostras}\n"
                f"Enviadas com Sucesso: {result.sucessos}\n"
                f"Falhas/Erros: {result.total_amostras - result.sucessos}\n"
            )
            is_sucesso = True

        except Exception as e:
            error_message = str(e).split("\n")[0]
            self._update_progress(f"ERRO CRÍTICO: {error_message}", 1.0, "red")
            self.log_to_textbox(f"ERRO CRÍTICO NO PROCESSAMENTO: {e}", "critical")
            resumo = f"O processo foi interrompido por um erro crítico.\n\nDetalhes:\n{e}"
            is_sucesso = False
            
        finally:
            def show_popup():
                popup = ctk.CTkToplevel(self)
                popup.title("Relatório de Envio GAL")
                popup.geometry("400x300")
                popup.grab_set()
                popup.focus_set()
                
                if is_sucesso:
                    lbl = ctk.CTkLabel(popup, text="Envio Concluído!", font=("Helvetica", 16, "bold"), text_color="green")
                else:
                    lbl = ctk.CTkLabel(popup, text="Envio Falhou!", font=("Helvetica", 16, "bold"), text_color="red")
                lbl.pack(pady=10)
                
                txt = ctk.CTkTextbox(popup, width=360, height=150)
                txt.pack(padx=20, pady=10)
                txt.insert("0.0", resumo)
                txt.configure(state="disabled")
                
                btn_ok = ctk.CTkButton(popup, text="OK", command=popup.destroy)
                btn_ok.pack(pady=10)

            self.after(0, show_popup)
            self._processing = False
            self.after(0, lambda: self.usuario_entry.delete(0, "end"))
            self.after(0, lambda: self.senha_entry.delete(0, "end"))
            self.after(0, lambda: self.start_button.configure(state="normal"))
            self.after(0, lambda: self.csv_button.configure(state="normal"))



# ==============================================================================
# 4. PONTO DE ENTRADA
# ==============================================================================
def abrir_janela_envio_gal(master, usuario_logado, app_state: Optional[Any] = None):
    app = IntegrationApp(master, usuario_logado, app_state)
    if getattr(app, "_window", None) is not None:
        app._window.grab_set()
        return app._window
    return app


def create_gal_page(parent: ctk.CTkFrame, main_window) -> ctk.CTkFrame:
    """
    Cria a tela principal de GAL no modo single-window.

    O fluxo permanece hibrido: tela principal em pagina e dialogs modais
    para confirmacoes/credenciais/progresso quando necessario.
    """

    app_state = getattr(main_window, "app_state", None)
    usuario = getattr(app_state, "usuario_logado", "Desconhecido")

    def _go_back() -> None:
        nav = getattr(main_window, "navigation_manager", None)
        if nav and hasattr(nav, "navigate_to"):
            nav.navigate_to("main_menu")

    page = IntegrationApp(
        main_window,
        usuario,
        app_state=app_state,
        host_frame=parent,
        on_close_callback=_go_back,
    )
    return page


if __name__ == "__main__":
    root = ctk.CTk()
    root.withdraw()
    abrir_janela_envio_gal(root, "utilizador_de_teste")
    root.mainloop()
