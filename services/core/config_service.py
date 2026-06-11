# services/config_service.py
"""
ConfigService - API Única para Configurações do Sistema

⚠️ IMPORTANTE: Esta é a ÚNICA forma oficial de acessar configurações.
   NUNCA leia config.json diretamente com open(). Use os métodos desta classe.

API Principal:
    - config_service.get(key, default=None) - Lê configuração
    - config_service.set(key, value) - Escreve configuração
    - config_service.get_db_config() - Config do PostgreSQL
    - config_service.get_gal_config() - Config do GAL
    - config_service.get_paths() - Caminhos do sistema

Exemplo de Uso:
    from services.core.config_service import config_service
    
    # Ler
    laboratorio = config_service.get('laboratorio', 'Padrão')
    
    # Escrever
    config_service.set('laboratorio', 'Novo Nome')

Ver: RELATORIO_REDUNDANCIA_CONFLITOS.md (FASE 3, Etapa 3.3)
"""

import copy
import json
import os
import threading
from typing import Any, Dict
import warnings

# --- Configuração de Paths ---
from services.system_paths import BASE_DIR
from utils.logger import registrar_log

# O único ficheiro de configuração que a aplicação irá conhecer
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# Parametros do lock inter-processo de gravacao do config.json (INST-001 / CONC-004).
# Extraidos para constantes de modulo para permitir ajuste/teste sem alterar a logica.
_CONFIG_LOCK_MAX_ATTEMPTS = 50
_CONFIG_LOCK_SLEEP_SECONDS = 0.1

# Keys de paths que devem ser resolvidas a partir do data_root, quando configurado
_DATA_ROOT_PATH_KEYS = {
    "log_file",
    "credentials_csv",
    "users_csv",
    "processing_history_csv",
    "gal_history_csv",
    "gal_upload_history_csv",
    "default_csv_folder",
    "default_results_folder",
    "reports_dir",
    "logs_dir",
    "historicos_dir",
    "inputs_dir",
}

_SHARED_STORAGE_DEFAULT_RELATIVE_PATHS = {
    "log_file": "logs/sistema.log",
    "credentials_csv": "banco_runtime/usuarios.csv",
    "users_csv": "banco_runtime/usuarios.csv",
    "processing_history_csv": "logs/historico_processos.csv",
    "gal_history_csv": "logs/historico_analises.csv",
    "gal_upload_history_csv": "logs/total_importados_gal.csv",
    "default_csv_folder": "data/inputs",
    "default_results_folder": "reports",
    "reports_dir": "reports",
    "logs_dir": "logs",
    "historicos_dir": "logs",
    "inputs_dir": "data/inputs",
}



# Sistema de monitoramento (opcional, ativado apenas em debug)
_MONITORED_MODE = __debug__

def _warn_direct_config_access():
    """Emite warning se houver acesso direto ao config.json."""
    if _MONITORED_MODE:
        warnings.warn(
            "Leitura direta de config.json detectada. Use config_service.get() em vez disso. "
            "Ver documentação em services/config_service.py",
            DeprecationWarning,
            stacklevel=3
        )





class ConfigService:

    """

    Classe singleton para gerir todas as configurações da aplicação a partir de um único ficheiro.

    """



    _instance = None

    _config: Dict[str, Any] = {}

    _lock = threading.Lock()

    def __new__(cls):

        if cls._instance is None:

            with cls._lock:

                if cls._instance is None:

                    cls._instance = super(ConfigService, cls).__new__(cls)

                    cls._instance._initialize()

        return cls._instance



    def _initialize(self):



        """Carrega a configuracao ou cria um ficheiro padrao."""



        if not self._config:  # Carrega apenas uma vez



            self._load_config()



    def _load_config(self):



        """Recarrega configuracoes do disco."""



        if not os.path.exists(CONFIG_PATH):



            registrar_log(



                "ConfigService",



                f"Ficheiro de configuracao nao encontrado. A criar '{CONFIG_PATH}' padrao.",



                "WARNING",



            )



            self._config = self._get_default_config()



            self._save_config()



        else:



            try:



                with open(CONFIG_PATH, "r", encoding="utf-8") as f:



                    self._config = json.load(f)

                # Fallback para shared storage vazio - forca local isolation
                if not self._config.get("data_root"):
                    from services.system_paths import BASE_DIR
                    fallback_dir = os.path.join(BASE_DIR, "dados")
                    self._config["data_root"] = fallback_dir
                    self._config["allowed_roots"] = [fallback_dir]
                    try:
                        os.makedirs(fallback_dir, exist_ok=True)
                    except Exception:
                        pass

                registrar_log(

                    "ConfigService", "Configuracoes carregadas com sucesso.", "INFO"

                )



            except json.JSONDecodeError as e:



                registrar_log(



                    "ConfigService",



                    f"Erro ao ler o config.json: {e}. A carregar configuracao padrao.",



                    "ERROR",



                )



                self._config = self._get_default_config()



            except Exception as e:



                registrar_log(



                    "ConfigService",



                    f"Erro inesperado ao carregar config: {e}",



                    "CRITICAL",



                )



                self._config = self._get_default_config()



        self._validate_paths()
        self._warn_credentials_path_mismatch()



    def get(self, key: str, default: Any = None) -> Any:

        """Obtém uma chave de configuração de alto nível."""

        return self._config.get(key, default)




    def get_all(self) -> Dict[str, Any]:




        """Retorna uma copia de toda a configuracao."""




        return copy.deepcopy(self._config)
    
    def set(self, key: str, value: Any):
        """
        Define uma chave de configuração de alto nível.
        
        Args:
            key: Chave da configuração
            value: Valor a ser definido
        
        Nota: Não salva automaticamente. Use save() para persistir.
        """
        self._config[key] = value
        registrar_log(
            "ConfigService",
            f"Configuração '{key}' atualizada para: {value}",
            "INFO"
        )
    
    
    def save(self):
        """
        Salva as configurações atuais no arquivo config.json.
        
        Returns:
            bool: True se salvou com sucesso, False caso contrário
        """
        return self._save_config()

    def configure_shared_storage(self, shared_root: str) -> tuple[bool, str]:
        """
        Padroniza o uso de armazenamento compartilhado para todos os terminais.

        Regras aplicadas:
        - data_root = shared_root
        - allowed_roots = [shared_root]
        - paths de dados passam a ser relativos padronizados
        - shared_storage.required = True
        """
        root = self._normalize_root_path(shared_root)
        if not root:
            return False, "Informe um caminho de compartilhamento válido."

        try:
            os.makedirs(root, exist_ok=True)
        except Exception as exc:
            return False, f"Não foi possível criar/acessar o diretório: {exc}"

        if not os.access(root, os.R_OK | os.W_OK):
            return False, "Sem permissão de leitura/escrita no compartilhamento informado."

        self._config["data_root"] = root
        self._config["allowed_roots"] = [root]

        paths = dict(self._config.get("paths") or {})
        for key, default_value in _SHARED_STORAGE_DEFAULT_RELATIVE_PATHS.items():
            current = str(paths.get(key) or "").strip()
            paths[key] = self._coerce_relative_path_for_shared_root(
                current_value=current,
                shared_root=root,
                default_value=default_value,
            )
        self._config["paths"] = paths

        shared_cfg = dict(self._config.get("shared_storage") or {})
        shared_cfg["required"] = True
        shared_cfg["root"] = root
        self._config["shared_storage"] = shared_cfg

        if not self._save_config():
            return (
                False,
                "Outro processo esta gravando a configuracao (lock ativo). "
                "Nenhuma alteracao foi gravada. Tente novamente em instantes.",
            )
        registrar_log(
            "ConfigService",
            f"Compartilhamento padronizado com sucesso: {root}",
            "INFO",
        )
        return True, "Compartilhamento padronizado com sucesso."

    def get_shared_storage_status(self) -> Dict[str, Any]:
        """Retorna diagnóstico objetivo do estado de compartilhamento atual."""
        data_root_cfg = self.get("data_root")
        allowed_roots_cfg = self.get("allowed_roots")
        data_root = self._normalize_root_path(data_root_cfg)

        normalized_allowed: list[str] = []
        if isinstance(allowed_roots_cfg, (list, tuple, set)):
            for item in allowed_roots_cfg:
                root = self._normalize_root_path(item)
                if root and root not in normalized_allowed:
                    normalized_allowed.append(root)
        elif allowed_roots_cfg:
            root = self._normalize_root_path(allowed_roots_cfg)
            if root:
                normalized_allowed.append(root)

        read_write_ok = bool(data_root and os.path.isdir(data_root) and os.access(data_root, os.R_OK | os.W_OK))
        same_root_policy = bool(data_root and normalized_allowed == [data_root])
        required = bool(dict(self.get("shared_storage", {}) or {}).get("required", False))

        return {
            "required": required,
            "data_root": data_root or "",
            "allowed_roots": normalized_allowed,
            "read_write_ok": read_write_ok,
            "same_root_policy": same_root_policy,
            "ready": (not required) or (bool(data_root) and read_write_ok and same_root_policy),
        }



    def get_db_config(self) -> Dict[str, Any]:

        """Retorna a secção de configuração da base de dados."""

        return self.get("postgres", {})




    def get_storage_backend(self) -> str:




        """



        Retorna o backend de storage configurado.



        Valores suportados: "csv", "sqlite", "postgres".



        """




        backend = str(self.get("storage_backend", "") or "").strip().lower()




        if backend in ("csv", "sqlite", "postgres"):




            return backend




        if self.get_db_config().get("enabled", False):




            return "postgres"




        return "csv"

    def _normalize_root_path(self, root: Any) -> str:
        if not root:
            return ""
        try:
            root_str = os.path.expandvars(os.path.expanduser(str(root))).strip()
        except Exception:
            return ""
        if not root_str:
            return ""
        if not os.path.isabs(root_str):
            root_str = os.path.join(BASE_DIR, root_str)
        return os.path.normpath(root_str)

    def _coerce_relative_path_for_shared_root(
        self,
        *,
        current_value: str,
        shared_root: str,
        default_value: str,
    ) -> str:
        """
        Garante path relativo estável para o compartilhamento padronizado.
        """
        candidate = str(current_value or "").strip()
        if not candidate:
            return default_value.replace("\\", "/")

        try:
            if os.path.isabs(candidate):
                candidate_norm = os.path.normpath(candidate)
                shared_norm = os.path.normpath(shared_root)
                if os.path.normcase(candidate_norm).startswith(os.path.normcase(shared_norm)):
                    rel = os.path.relpath(candidate_norm, shared_norm)
                    return rel.replace("\\", "/")
                return default_value.replace("\\", "/")
        except Exception:
            return default_value.replace("\\", "/")

        return candidate.replace("\\", "/")


    def get_gal_config(self) -> Dict[str, Any]:

        """Retorna a secção de configuração do GAL."""

        return self.get("gal_integration", {})

    def get_contract_hierarchy(self) -> list[str]:
        """Retorna a hierarquia oficial de resolucao dos contratos de runtime."""
        default = ["contracts", "config_exams", "config_json", "csv"]
        cfg = self.get("contracts", {}) or {}
        hierarchy = cfg.get("hierarchy", default)
        if not isinstance(hierarchy, list):
            return list(default)

        normalized: list[str] = []
        for item in hierarchy:
            token = str(item).strip().lower()
            if token in default and token not in normalized:
                normalized.append(token)

        for token in default:
            if token not in normalized:
                normalized.append(token)
        return normalized

    def get_encoding_policy(self) -> Dict[str, Any]:
        """
        Retorna politica central de encoding para toda a aplicacao.

        Regras:
        - UTF-8 como padrao interno.
        - BOM bloqueado por padrao (validacao externa/scanner).
        - Fallback de encoding permitido somente em ingestao legada.
        """
        defaults = {
            "default": "utf-8",
            "allow_bom": False,
            "strict_mode": False,
            "legacy_fallback_on_ingest_only": True,
            "fallback_encodings": ["utf-8-sig", "cp1252", "latin-1"],
        }
        raw = self.get("encoding_policy", {}) or {}
        if not isinstance(raw, dict):
            return defaults

        policy = dict(defaults)
        for key in ("default", "allow_bom", "strict_mode", "legacy_fallback_on_ingest_only"):
            if key in raw:
                policy[key] = raw[key]

        fallback = raw.get("fallback_encodings")
        if isinstance(fallback, (list, tuple)):
            normalized = [str(item).strip() for item in fallback if str(item).strip()]
            if normalized:
                policy["fallback_encodings"] = normalized
        return policy



    def get_paths(self) -> Dict[str, str]:
        """
        Retorna dicionario com todos os caminhos do sistema.

        SECURITY FIX (R1): Valida todos os paths para prevenir Path Traversal.
        Paths fora das raizes permitidas levantarao SecurityError.

        Returns:
            Dict com paths validados e seguros

        Raises:
            SecurityError: Se algum path esta fora das raizes permitidas
        """
        from utils.secure_path import get_secure_path_validator, SecurityError

        paths = self.get("paths", {}).copy()
        data_root_cfg = self.get("data_root") or paths.get("data_root")
        allowed_roots_cfg = self.get("allowed_roots") or paths.get("allowed_roots")

        def _normalize_root(root):
            if not root:
                return None
            try:
                root_str = os.path.expandvars(os.path.expanduser(str(root))).strip()
            except Exception:
                return None
            if not root_str:
                return None
            if not os.path.isabs(root_str):
                root_str = os.path.join(BASE_DIR, root_str)
            return os.path.normpath(root_str)

        data_root = _normalize_root(data_root_cfg)
        allowed_roots = []

        if isinstance(allowed_roots_cfg, (list, tuple, set)):
            items = list(allowed_roots_cfg)
        elif allowed_roots_cfg:
            items = [allowed_roots_cfg]
        else:
            items = []

        for item in items:
            root_norm = _normalize_root(item)
            if root_norm:
                allowed_roots.append(root_norm)

        if data_root:
            allowed_roots.append(data_root)

        output_base = data_root or (allowed_roots[0] if allowed_roots else BASE_DIR)
        if output_base and not os.path.exists(output_base):
            try:
                os.makedirs(output_base, exist_ok=True)
            except OSError as e:
                registrar_log(
                    "ConfigService",
                    f"Falha ao criar o diretorio base configurado '{output_base}': {e}",
                    "ERROR"
                )
                from utils.secure_path import SecurityError
                raise SecurityError(
                    f"Nao foi possivel acessar ou criar o diretorio base: {output_base}. "
                    f"Verifique se o 'data_root' no config.json esta correto para este PC "
                    f"ou se voce tem permissoes de escrita. Erro original: {e}"
                ) from e
        validator_output = get_secure_path_validator(
            allowed_roots=allowed_roots, base_dir=output_base
        )
        validator_base = get_secure_path_validator(allowed_roots=None, base_dir=BASE_DIR)
        validated_paths = {}

        for key, value in paths.items():
            if key in ("data_root", "allowed_roots"):
                continue
            if not value:
                continue

            try:
                value_str = os.path.expandvars(os.path.expanduser(str(value)))

                # Se nao eh absoluto, torna-lo relativo ao root correto
                if not os.path.isabs(value_str):
                    if data_root and key in _DATA_ROOT_PATH_KEYS:
                        full_path = os.path.join(data_root, value_str)
                    else:
                        full_path = os.path.join(BASE_DIR, value_str)
                else:
                    full_path = value_str

                # Validar path (cria diret?rios se necess?rio)
                validator = (
                    validator_output if key in _DATA_ROOT_PATH_KEYS else validator_base
                )
                safe_path = validator.validate(full_path, create_parents=True)
                validated_paths[key] = str(safe_path)

            except SecurityError as e:
                registrar_log(
                    "ConfigService",
                    f"SECURITY: Path traversal blocked for '{key}': {value}",
                    "ERROR",
                )
                raise SecurityError(
                    f"Invalid path for '{key}': {value}. Path must be within allowed roots."
                ) from e

        return validated_paths

    def _save_config(self) -> bool:
        """Salva a configuração no JSON com escrita atômica e lock inter-processo.

        Fail-closed (FINDING-004 / CONC-004): se o lock não for adquirido dentro
        do timeout, NÃO grava e retorna False — evitando escrita concorrente
        (lost update) entre administradores. O lock só é removido por quem o
        adquiriu (não remove lock alheio).

        Returns:
            bool: True se gravou; False se não conseguiu o lock (não gravou).
        """
        import tempfile
        import shutil
        import time

        lock_path = CONFIG_PATH + ".lock"

        acquired = False
        for _ in range(_CONFIG_LOCK_MAX_ATTEMPTS):
            try:
                fd_lock = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.close(fd_lock)
                acquired = True
                break
            except FileExistsError:
                time.sleep(_CONFIG_LOCK_SLEEP_SECONDS)

        if not acquired:
            registrar_log(
                "ConfigService",
                "Timeout aguardando lock de escrita do config.json. Gravacao abortada "
                "(fail-closed) para evitar escrita concorrente. Tente novamente.",
                "ERROR",
            )
            return False

        try:
            if os.path.exists(CONFIG_PATH):
                shutil.copy2(CONFIG_PATH, CONFIG_PATH + ".bak")

            dir_name = os.path.dirname(CONFIG_PATH) or "."
            fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix="config_", suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_path, CONFIG_PATH)
            return True
        except Exception as e:
            registrar_log(
                "ConfigService",
                f"Não foi possível salvar o ficheiro de configuração atomicamente: {e}",
                "CRITICAL",
            )
            try:
                if 'tmp_path' in locals() and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except OSError:
                pass
            return False
        finally:
            # Ownership: só remove o lock que NÓS criamos (nunca lock alheio).
            if acquired:
                try:
                    if os.path.exists(lock_path):
                        os.unlink(lock_path)
                except OSError:
                    pass


    def restore_backup(self) -> tuple[bool, str]:
        """Restaura o config.json a partir do config.json.bak."""
        bak_path = CONFIG_PATH + ".bak"
        if not os.path.exists(bak_path):
            return False, "Arquivo de backup não encontrado."
        try:
            import shutil
            shutil.copy2(bak_path, CONFIG_PATH)
            self._load_config()
            registrar_log("ConfigService", "Backup do config.json restaurado com sucesso.", "INFO")
            return True, "Backup restaurado com sucesso."
        except Exception as e:
            registrar_log("ConfigService", f"Erro ao restaurar backup do config.json: {e}", "ERROR")
            return False, f"Erro ao restaurar backup: {e}"

    def create_installation_backup(self) -> tuple[bool, str]:
        """Cria um backup de baseline antes de aplicar alterações da Instalação Inicial."""
        baseline_path = CONFIG_PATH + ".baseline.bak"
        try:
            import shutil
            if os.path.exists(CONFIG_PATH):
                shutil.copy2(CONFIG_PATH, baseline_path)
                registrar_log("ConfigService", "Backup baseline de instalação criado com sucesso.", "INFO")
                return True, "Backup baseline criado."
            return False, "config.json não existe para fazer backup."
        except Exception as e:
            registrar_log("ConfigService", f"Erro ao criar backup baseline: {e}", "ERROR")
            return False, f"Erro ao criar backup baseline: {e}"

    def restore_installation_backup(self) -> tuple[bool, str]:
        """Restaura o config.json a partir do baseline de instalação."""
        baseline_path = CONFIG_PATH + ".baseline.bak"
        if not os.path.exists(baseline_path):
            return False, "Arquivo de backup baseline não encontrado."
        try:
            import shutil
            shutil.copy2(baseline_path, CONFIG_PATH)
            self._load_config()
            registrar_log("ConfigService", "Backup baseline restaurado com sucesso.", "INFO")
            return True, "Backup baseline restaurado com sucesso."
        except Exception as e:
            registrar_log("ConfigService", f"Erro ao restaurar backup baseline: {e}", "ERROR")
            return False, f"Erro ao restaurar backup baseline: {e}"

    def _validate_paths(self):
        """Verifica se os caminhos configurados são acessíveis e loga avisos."""
        try:
            paths = self.get_paths()
            for key, path in paths.items():
                # Tenta verificar se o caminho existe
                # Se for arquivo, verifica o dir pai
                target_check = path
                if os.path.splitext(path)[1]:  # Tem extensao, assume arquivo
                    target_check = os.path.dirname(path)

                if target_check and not os.path.exists(target_check):
                    registrar_log(
                        "ConfigService",
                        f"AVISO: Caminho para '{key}' não encontrado ou inacessível: {path}",
                        "WARNING",
                    )
        except Exception as e:
            registrar_log("ConfigService", f"Erro ao validar caminhos: {e}", "ERROR")

    def _warn_credentials_path_mismatch(self) -> None:
        """Alerta se credentials_csv aponta para local diferente do esperado."""
        try:
            paths = self.get_paths()
            actual = paths.get("credentials_csv")
            if not actual:
                return

            expected = paths.get("users_csv") or os.path.join(
                BASE_DIR, "banco_runtime", "usuarios.csv"
            )
            actual_norm = os.path.normpath(actual)
            expected_norm = os.path.normpath(expected)

            if os.path.normcase(actual_norm) != os.path.normcase(expected_norm):
                registrar_log(
                    "ConfigService",
                    f"ALERTA: credentials_csv aponta para '{actual_norm}', diferente do esperado '{expected_norm}'.",
                    "WARNING",
                )
        except Exception as exc:
            registrar_log(
                "ConfigService",
                f"Falha ao validar credentials_csv: {exc}",
                "ERROR",
            )

    def _get_default_config(self) -> Dict[str, Any]:

        """Retorna a estrutura de configuração padrão completa."""

        return {

            "feature_flags": {
                "ui_single_window": True,
            },

            "ui_single_window": True,

            "data_root": "",

            "allowed_roots": [],

            "storage_backend": "csv",

            "shared_storage": {
                "required": False,
                "root": "",
            },

            "contracts": {
                "source_of_truth": "contracts",
                "hierarchy": ["contracts", "config_exams", "config_json", "csv"],
            },

            "encoding_policy": {
                "default": "utf-8",
                "allow_bom": False,
                "strict_mode": False,
                "legacy_fallback_on_ingest_only": True,
                "fallback_encodings": ["utf-8-sig", "cp1252", "latin-1"],
            },

            "retencao": {
                "ativada": True,
                "logs_dias": 180,
                "reports_dias": 365,
                "relatorios_dias": 365,
                "logs_max_total_mb": 512,
                "reports_max_total_mb": 2048,
                "relatorios_max_total_mb": 2048,
                "log_file_max_mb": 50,
            },

            "paths": {

                "log_file": "logs/sistema.log",

                "exams_catalog_csv": "banco_runtime/exames_config.csv",

                "credentials_csv": "banco_runtime/usuarios.csv",
                "users_csv": "banco_runtime/usuarios.csv",
                "processing_history_csv": "logs/historico_processos.csv",

                "gal_history_csv": "logs/total_importados_gal.csv",

            },

            "postgres": {

                "enabled": False,

                "dbname": "integragal",

                "user": "postgres",

                "password": "your_password_here",

                "host": "localhost",

                "port": 5432,

            },

            "gal_integration": {

                "base_url": "https://gal.saude.sc.gov.br",

                "login_ids": {

                    "username": "usuario",

                    "password": "senha",

                    "module_button": "ext-gen17",

                    "lab_button": "ext-gen25",

                    "login_button": "ext-gen29",

                },

                "api_endpoints": {

                    "metadata": "/bmh/entrada-resultados/lista/",

                    "submit": "/bmh/entrada-resultados/gravar/",

                },

                "retry_settings": {"max_retries": 3, "backoff_factor": 0.5},

                "panel_tests": {

                    "1": [

                        "influenzaa",

                        "influenzab",

                        "coronavirusncov",

                        "coronavirus229e",

                        "coronavirusnl63",

                        "coronavirushku1",

                        "coronavirusoc43",

                        "adenovirus",

                        "vsincicialresp",

                        "metapneumovirus",

                        "rinovirus",

                        "bocavirus",

                        "enterovirus",

                        "parainflu_1",

                        "parainflu_2",

                        "parainflu_3",

                        "parainflu_4",

                    ]

                },

            },

        }





# Instância única para ser usada em toda a aplicação

config_service = ConfigService()

