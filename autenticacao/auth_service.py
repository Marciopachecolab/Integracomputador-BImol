# autenticacao/auth_service.py

"""
Camada de autenticacao de interface do IntegraGAL.

Papel:
- Expor uma API simples de login para a camada de UI (dialogs, telas de autenticacao).
- Verificar credenciais a partir do arquivo canonico de usuarios (usuarios.csv),
  usando hashing seguro de senhas (bcrypt).
- Manter compatibilidade com credenciais legadas (credenciais.csv) apenas para
  migracao/sincronizacao.
- No desenho de arquitetura, o AuthService e a "porta de entrada" da autenticacao
  e pode, em evolucoes futuras, delegar a gestao completa de usuarios para
  core.authentication.user_manager.UserManager.
"""

from __future__ import annotations

import csv
import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import bcrypt  # Nova dependencia - adicione 'bcrypt' ao requirements.txt
import pandas as pd

from application.access_control import (
    AuthorizationDeniedError,
    ensure_operation_allowed,
    is_privileged,
    normalize_access_level,
)
from domain.persistence_contracts import (
    PersistenceProvider,
    UserAccessLevel,
    UserCreateDTO,
    UserDTO,
    UserRepository,
    UserStatus,
    UserUpdateDTO,
)
from domain.error_codes import ErrorCode
from services.persistence.persistence_provider import get_persistence_provider
from services.persistence.csv_io import read_csv_strict, write_csv_atomic
from services.core.error_contracts import build_error_result
from services.path_resolver import (
    resolve_credentials_csv_path,
    resolve_users_csv_path,
)
from utils.csv_lock import CSVFileLock
from utils.csv_safety import sanitize_csv_value
from utils.logger import registrar_log
from utils.network_io import RetryPolicy, call_with_retry, open_with_retry, path_exists_with_retry


USER_COLUMNS = [
    "id",
    "usuario",
    "senha_hash",
    "nivel_acesso",
    "status",
    "data_criacao",
    "ultimo_acesso",
    "tentativas_falhas",
    "bloqueado_ate",
    "preferencias",
]

_USER_COLUMN_CANONICAL = {col.lower(): col for col in USER_COLUMNS}
_USER_COLUMN_ALIASES = {
    "senha": "senha_hash",
    "senha_hash": "senha_hash",
    "nivel": "nivel_acesso",
    "nivelacesso": "nivel_acesso",
    "nivel acesso": "nivel_acesso",
    "nivel_acesso": "nivel_acesso",
}

_USER_DEFAULTS = {
    "nivel_acesso": "DIAGNOSTICO",
    "status": "ATIVO",
    "data_criacao": "",
    "ultimo_acesso": "",
    "tentativas_falhas": "0",
    "bloqueado_ate": "",
    "preferencias": "{}",
}


# === Politica de lockout server-side (DHP Fase 5) ===
# Fonte: docs/specs/decisoes_humanas/DHP-senha-lockout.md
# Constituicao: .specify/memory/constitution.delta.md §3.1 (lockout MUST)
MAX_TENTATIVAS_FALHAS = 5
BLOQUEIO_DURACAO_MINUTOS = 15


def _normalize_username(value: object) -> str:
    """Normaliza o nome de usuario para comparacoes (case-insensitive)."""
    return str(value or "").strip().lower()


def _normalize_users_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Garante o schema completo de usuarios.csv e normaliza colunas conhecidas.

    Args:
        df: DataFrame carregado de usuarios.csv (ou legado).

    Returns:
        DataFrame normalizado com colunas canonicas.
    """
    df = df.copy()
    rename_map: Dict[str, str] = {}
    for col in df.columns:
        key = str(col).strip().lower()
        if key in _USER_COLUMN_ALIASES:
            rename_map[col] = _USER_COLUMN_ALIASES[key]
        elif key in _USER_COLUMN_CANONICAL:
            rename_map[col] = _USER_COLUMN_CANONICAL[key]
    if rename_map:
        df = df.rename(columns=rename_map)

    for col in USER_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    if "usuario" in df.columns:
        df["usuario"] = df["usuario"].astype(str).str.strip()
    if "nivel_acesso" in df.columns:
        df["nivel_acesso"] = df["nivel_acesso"].astype(str).str.upper()

    for col, default in _USER_DEFAULTS.items():
        if col in df.columns:
            df[col] = df[col].fillna(default)

    if "id" in df.columns:
        mask = df["id"].isna() | (df["id"].astype(str).str.strip() == "")
        if mask.any():
            df.loc[mask, "id"] = [uuid.uuid4().hex[:8] for _ in range(mask.sum())]

    ordered = USER_COLUMNS + [c for c in df.columns if c not in USER_COLUMNS]
    return df[ordered]


def _build_user_record(usuario: str, senha_hash: str, nivel_acesso: str) -> Dict[str, str]:
    """
    Cria um registro de usuario com schema completo e defaults seguros.

    Args:
        usuario: Nome do usuario.
        senha_hash: Hash da senha (bcrypt ou legado).
        nivel_acesso: Nivel de acesso desejado.

    Returns:
        Dict com todas as colunas de usuarios.csv preenchidas.
    """
    now_date = datetime.now().strftime("%Y-%m-%d")
    return {
        "id": uuid.uuid4().hex[:8],
        "usuario": str(usuario).strip(),
        "senha_hash": str(senha_hash).strip(),
        "nivel_acesso": str(nivel_acesso).upper(),
        "status": "ATIVO",
        "data_criacao": now_date,
        "ultimo_acesso": "",
        "tentativas_falhas": "0",
        "bloqueado_ate": "",
        "preferencias": "{}",
    }


def _resolve_legacy_credentials_path() -> Optional[Path]:
    """Resolve o caminho do credenciais.csv legado (quando diferente do users_csv)."""
    return resolve_credentials_csv_path(allow_same=False)


def _resolve_users_path() -> Path:
    """Resolve o caminho do arquivo de usuarios via path_resolver."""
    return resolve_users_csv_path()


def _read_credentials_df(path: Optional[Path]) -> Optional[pd.DataFrame]:
    """Le credenciais legadas com parsing deterministico de delimitador/encoding."""
    if path is None:
        return None
    policy = RetryPolicy.from_env()
    if not path_exists_with_retry(path, policy=policy):
        return None

    required_candidates = {"usuario", "user", "login"}
    secret_candidates = {"senha", "senha_hash", "senha hash"}
    for sep in (";", ","):
        for enc in ("utf-8", "latin-1"):
            op_name = f"read_credentials[{sep},{enc}]"
            try:
                df = call_with_retry(
                    lambda: pd.read_csv(path, sep=sep, encoding=enc),
                    op_name=op_name,
                    path=path,
                    policy=policy,
                )
            except Exception:
                continue

            if df is None or df.empty:
                continue

            normalized = {str(col).strip().lower() for col in df.columns}
            if not (normalized & required_candidates):
                continue
            if not (normalized & secret_candidates):
                continue

            return df

    return None


def _coerce_access_level(value: object) -> UserAccessLevel:
    """Converte texto para UserAccessLevel com fallback seguro."""
    normalized = str(value or "").strip().upper()
    try:
        return UserAccessLevel(normalized)
    except ValueError:
        return UserAccessLevel.DIAGNOSTICO


def _coerce_user_status(value: object) -> UserStatus:
    """Converte texto para UserStatus com fallback seguro."""
    normalized = str(value or "").strip().upper()
    try:
        return UserStatus(normalized)
    except ValueError:
        return UserStatus.ATIVO


def _parse_preferences(value: object) -> Dict[str, str]:
    """Normaliza preferencias de usuario vindas de CSV/DTO."""
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}

    text = str(value or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(k): str(v) for k, v in payload.items()}


def _safe_int(value: object, default: int = 0) -> int:
    """Converte valor para inteiro com fallback."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _dto_to_row(dto: UserDTO) -> Dict[str, str]:
    """Converte UserDTO para schema canonico de usuarios.csv."""
    return {
        "id": str(dto.id or ""),
        "usuario": str(dto.username or ""),
        "senha_hash": str(dto.password_hash or ""),
        "nivel_acesso": dto.access_level.value,
        "status": dto.status.value,
        "data_criacao": str(dto.created_at or ""),
        "ultimo_acesso": str(dto.last_access or ""),
        "tentativas_falhas": str(dto.failed_attempts),
        "bloqueado_ate": str(dto.locked_until or ""),
        "preferencias": json.dumps(dto.preferences or {}, ensure_ascii=False),
    }


def _has_changes(changes: UserUpdateDTO) -> bool:
    """Indica se houve alteracoes no payload de update."""
    return any(
        getattr(changes, attr) is not None
        for attr in (
            "access_level",
            "status",
            "password_hash",
            "last_access",
            "failed_attempts",
            "locked_until",
            "preferences",
        )
    )


class AuthService:
    """Encapsula logica de autenticacao e gestao de usuarios."""

    def __init__(self, provider: Optional[PersistenceProvider] = None) -> None:
        self._provider = provider or get_persistence_provider(force_refresh=True)
        self._user_repo = None
        self._garantir_usuarios_csv()

    def _get_user_repo(self) -> UserRepository:
        """Retorna repositorio de usuarios via contrato de persistencia."""
        if self._user_repo is None:
            self._user_repo = self._provider.users()
        return self._user_repo

    def _resolve_actor_access_level(
        self,
        *,
        actor_username: Optional[str],
        actor_access_level: Optional[str],
    ) -> str:
        """Resolve nivel canonico do ator (prioriza fonte persistida)."""
        actor = str(actor_username or "").strip()
        if actor:
            user = self.obter_usuario(actor)
            if user:
                persisted = normalize_access_level(user.get("nivel_acesso", ""))
                if persisted:
                    return persisted
        return normalize_access_level(actor_access_level or "")

    def _is_operation_allowed(
        self,
        *,
        operation: str,
        actor_username: Optional[str],
        actor_access_level: Optional[str],
        system_operation: bool,
    ) -> bool:
        """Valida permissao por operacao na camada de servico."""
        if system_operation:
            return True

        resolved_level = self._resolve_actor_access_level(
            actor_username=actor_username,
            actor_access_level=actor_access_level,
        )
        try:
            ensure_operation_allowed(
                operation,
                resolved_level,
                actor_username=actor_username,
            )
            return True
        except AuthorizationDeniedError as exc:
            registrar_log("AuthService", str(exc), "WARNING")
            return False

    def _garantir_usuarios_csv(self) -> None:
        """Garante que o arquivo usuarios.csv exista com cabecalho."""
        users_path = _resolve_users_path()
        policy = RetryPolicy.from_env()
        users_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with CSVFileLock(users_path):
                if path_exists_with_retry(users_path, policy=policy):
                    return
                with open_with_retry(
                    users_path, "w", newline="", encoding="utf-8", policy=policy
                ) as handle:
                    writer = csv.DictWriter(
                        handle, fieldnames=USER_COLUMNS, delimiter=","
                    )
                    writer.writeheader()
            registrar_log(
                "AuthService",
                f"Arquivo de usuarios criado em: {users_path}",
                "INFO",
            )
        except Exception as exc:
            registrar_log(
                "AuthService",
                f"Falha ao criar arquivo de usuarios: {exc}",
                "CRITICAL",
            )

    def load_users_df(self) -> pd.DataFrame:
        """
        Carrega usuarios.csv com schema normalizado.

        Returns:
            DataFrame com colunas canonicas.
        """
        try:
            users = list(self._get_user_repo().list())
            rows = [_dto_to_row(user) for user in users]
            return _normalize_users_df(pd.DataFrame(rows))
        except Exception as exc:
            registrar_log(
                "AuthService",
                f"Falha ao carregar usuarios via provider. Fallback CSV ativo: {exc}",
                "WARNING",
            )
        return self._load_users_df_via_csv()

    def _load_users_df_via_csv(self) -> pd.DataFrame:
        """Carrega usuarios direto do CSV canonico (fallback legado)."""
        users_path = _resolve_users_path()
        policy = RetryPolicy.from_env()
        if not path_exists_with_retry(users_path, policy=policy):
            self._garantir_usuarios_csv()

        df: Optional[pd.DataFrame]
        try:
            df = call_with_retry(
                lambda: read_csv_strict(users_path, contract_name="usuarios.csv"),
                op_name="read_users",
                path=users_path,
                policy=policy,
            )
        except Exception as exc:
            registrar_log(
                "AuthService",
                f"Falha no contrato de usuarios.csv: {exc}",
                "ERROR",
            )
            df = None

        if df is None:
            df = pd.DataFrame(columns=USER_COLUMNS)

        return _normalize_users_df(df)

    def save_users_df(
        self,
        df: pd.DataFrame,
        *,
        actor_username: Optional[str] = None,
        actor_access_level: Optional[str] = None,
        system_operation: bool = False,
    ) -> bool:
        """
        Persiste usuarios via contrato de repositorio (fallback CSV seguro).

        Args:
            df: DataFrame com usuarios.

        Returns:
            True se persistido com sucesso.
        """
        if not self._is_operation_allowed(
            operation="users.mutate",
            actor_username=actor_username,
            actor_access_level=actor_access_level,
            system_operation=system_operation,
        ):
            return False

        normalized_df = _normalize_users_df(df)
        try:
            self._save_users_df_via_contract(normalized_df)
            return True
        except Exception as exc:
            registrar_log(
                "AuthService",
                f"Falha ao salvar via provider. Fallback CSV ativo: {exc}",
                "WARNING",
            )
            return self._save_users_df_via_csv(normalized_df)

    def save_users_df_actor_required(
        self,
        df: pd.DataFrame,
        *,
        actor_username: Optional[str],
        actor_access_level: Optional[str] = None,
        system_operation: bool = False,
    ) -> bool:
        """
        Persiste usuarios exigindo ator explicito para fluxos interativos novos.

        Mantem compatibilidade: operacoes de sistema continuam permitidas via
        ``system_operation=True``.
        """
        if not system_operation:
            actor = str(actor_username or "").strip()
            level = str(actor_access_level or "").strip()
            if not actor and not level:
                registrar_log(
                    "AuthService",
                    "save_users_df_actor_required bloqueado: ator ausente.",
                    "WARNING",
                )
                return False

        return self.save_users_df(
            df,
            actor_username=actor_username,
            actor_access_level=actor_access_level,
            system_operation=system_operation,
        )

    def _save_users_df_via_contract(self, df: pd.DataFrame) -> None:
        """Sincroniza DataFrame completo com repositorio de usuarios."""
        repo = self._get_user_repo()
        existing_users = list(repo.list())
        by_id = {str(user.id): user for user in existing_users if str(user.id)}
        by_username = {
            _normalize_username(user.username): user for user in existing_users
        }
        seen_ids = set()
        seen_usernames = set()

        for _, row in df.iterrows():
            username = str(row.get("usuario", "")).strip()
            if not username:
                continue
            username_key = _normalize_username(username)
            if username_key in seen_usernames:
                continue

            row_id = str(row.get("id", "")).strip()
            current = by_id.get(row_id) if row_id else None
            if current is None:
                current = by_username.get(username_key)

            access_level = _coerce_access_level(row.get("nivel_acesso"))
            status = _coerce_user_status(row.get("status"))
            password_hash = str(row.get("senha_hash", "") or "").strip()
            last_access = str(row.get("ultimo_acesso", "") or "").strip() or None
            failed_attempts = _safe_int(row.get("tentativas_falhas"), 0)
            locked_until = str(row.get("bloqueado_ate", "") or "").strip() or None
            preferences = _parse_preferences(row.get("preferencias"))

            if current is None:
                created = repo.create(
                    UserCreateDTO(
                        username=username,
                        password_hash=password_hash,
                        access_level=access_level,
                        status=status,
                        preferences=preferences,
                    )
                )
                seen_ids.add(str(created.id))
                seen_usernames.add(_normalize_username(created.username))
                continue

            seen_ids.add(str(current.id))
            seen_usernames.add(_normalize_username(current.username))

            changes = UserUpdateDTO(
                access_level=(
                    access_level if current.access_level != access_level else None
                ),
                status=status if current.status != status else None,
                password_hash=(
                    password_hash if current.password_hash != password_hash else None
                ),
                last_access=(
                    last_access if (current.last_access or None) != last_access else None
                ),
                failed_attempts=(
                    failed_attempts
                    if current.failed_attempts != failed_attempts
                    else None
                ),
                locked_until=(
                    locked_until
                    if (current.locked_until or None) != locked_until
                    else None
                ),
                preferences=(
                    preferences if (current.preferences or {}) != preferences else None
                ),
            )
            if _has_changes(changes):
                repo.update(str(current.id), changes)

        for user in existing_users:
            if str(user.id) in seen_ids or _normalize_username(user.username) in seen_usernames:
                continue
            repo.delete(str(user.id))

    def _save_users_df_via_csv(self, df: pd.DataFrame) -> bool:
        """Salva usuarios.csv de forma segura (lock + retry)."""
        users_path = _resolve_users_path()
        policy = RetryPolicy.from_env()
        users_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            safe_df = _normalize_users_df(df).fillna("")
            rows = [
                {
                    column: sanitize_csv_value(value)
                    for column, value in record.items()
                }
                for record in safe_df.to_dict(orient="records")
            ]
            write_csv_atomic(
                users_path,
                rows=rows,
                fieldnames=list(safe_df.columns),
                contract_name="usuarios.csv",
                policy=policy,
            )
            return True
        except Exception as exc:
            registrar_log(
                "AuthService",
                f"Erro ao salvar usuarios: {exc}",
                "CRITICAL",
            )
            return False


    def gerar_hash_bcrypt(self, senha: str) -> str:


        """


        Gera um hash seguro para a senha usando bcrypt.


        O salt é gerado e incluído automaticamente no hash.


        """


        senha_bytes = senha.encode("utf-8")


        hashed_bytes = bcrypt.hashpw(senha_bytes, bcrypt.gensalt())


        return hashed_bytes.decode("utf-8")


    def obter_usuario(self, username: str) -> Optional[dict]:
        """
        Obtem os dados completos do usuario a partir do arquivo de usuarios.

        Returns:
            dict com dados do usuario (usuario, nivel_acesso, status, etc.) ou None se nao encontrado.
        """
        df = self.load_users_df()
        if df.empty:
            registrar_log(
                "AuthService",
                "usuarios.csv vazio. Migracao legado nao e executada automaticamente no login.",
                "INFO",
            )
            return None

        if "usuario" not in df.columns:
            registrar_log(
                "AuthService",
                "Coluna 'usuario' nao encontrada no arquivo de usuarios.",
                "ERROR",
            )
            return None

        usuario_row = df[df["usuario"].str.strip().str.lower() == username.strip().lower()]
        if usuario_row.empty:
            return None

        row = usuario_row.iloc[0]
        return {
            "usuario": row.get("usuario", ""),
            "nivel_acesso": row.get("nivel_acesso", "DIAGNOSTICO"),
            "status": row.get("status", "ATIVO"),
            "data_criacao": row.get("data_criacao", ""),
            "ultimo_acesso": row.get("ultimo_acesso", ""),
        }

    def _persistir_estado_tentativas(
        self,
        df: pd.DataFrame,
        usuario_norm: str,
        *,
        sucesso: bool,
    ) -> Optional[str]:
        """Persiste tentativas_falhas/bloqueado_ate apos uma tentativa de login.

        Politica de lockout server-side (DHP Fase 5):
        - sucesso=True  -> zera tentativas_falhas, limpa bloqueado_ate e atualiza
          ultimo_acesso.
        - sucesso=False -> incrementa tentativas_falhas; ao atingir
          MAX_TENTATIVAS_FALHAS, define bloqueado_ate = now + BLOQUEIO_DURACAO_MINUTOS.

        A persistencia atualiza APENAS a linha do usuario via
        ``UserRepository.update`` (escrita sob CSVFileLock no adapter CSV; sem
        semantica de delete-missing do snapshot completo). Passa ``""`` em
        ``locked_until`` para LIMPAR o bloqueio (``None`` significaria "sem
        alteracao" no contrato). Nunca registra senha em log.

        Args:
            df: DataFrame de usuarios ja carregado (fonte do id/contador atual).
            usuario_norm: usuario normalizado (strip + lower).
            sucesso: indica se a autenticacao bcrypt teve sucesso.

        Returns:
            Em sucesso, o timestamp ISO de ultimo_acesso gravado; caso contrario None.
        """
        mask = df["usuario"].astype(str).str.strip().str.lower() == usuario_norm
        if not mask.any():
            return None  # usuario sumiu entre leitura e escrita; nada a persistir

        idx = df[mask].index[0]
        repo = self._get_user_repo()
        user_id = str(df.at[idx, "id"] or "").strip()
        if not user_id:
            # Linha legada sem id no df: resolve via repositorio por username.
            try:
                user_id = str(repo.get_by_username(usuario_norm).id or "").strip()
            except Exception:
                user_id = ""
            if not user_id:
                registrar_log(
                    "AuthService",
                    f"Lockout nao persistido (id ausente): {usuario_norm}",
                    "WARNING",
                )
                return None

        if sucesso:
            ultimo_acesso = datetime.now().isoformat()
            repo.update(
                user_id,
                UserUpdateDTO(
                    failed_attempts=0,
                    locked_until="",
                    last_access=ultimo_acesso,
                ),
            )
            return ultimo_acesso

        atual = _safe_int(df.at[idx, "tentativas_falhas"], 0)
        novo = atual + 1
        locked_until: Optional[str] = None
        if novo >= MAX_TENTATIVAS_FALHAS:
            expira = datetime.now() + timedelta(minutes=BLOQUEIO_DURACAO_MINUTOS)
            locked_until = expira.isoformat()
            registrar_log(
                "AuthService",
                f"Conta bloqueada por {BLOQUEIO_DURACAO_MINUTOS}min apos "
                f"{novo} tentativas falhas: {usuario_norm}",
                "WARNING",
            )
        repo.update(
            user_id,
            UserUpdateDTO(failed_attempts=novo, locked_until=locked_until),
        )
        return None

    def autenticar_credenciais(
        self, usuario: str, senha_fornecida: str
    ) -> Optional[dict]:
        """
        Autentica credenciais e retorna dados do usuario em uma unica leitura.

        Este metodo evita duas leituras consecutivas de `usuarios.csv`
        (verificar_senha + obter_usuario), reduzindo latencia no login.

        Aplica lockout server-side (DHP Fase 5): bloqueio temporario apos
        MAX_TENTATIVAS_FALHAS tentativas falhas, com auto-desbloqueio na
        expiracao de bloqueado_ate. Retorna sempre None em qualquer falha
        (mensagem generica na UI - OWASP A07).
        """
        try:
            df = self.load_users_df()
            if df.empty:
                registrar_log(
                    "AuthService",
                    "usuarios.csv vazio. Execute migracao legado por comando operacional.",
                    "WARNING",
                )
                return None

            if df is None or df.empty:
                registrar_log(
                    "AuthService",
                    "Arquivo de usuarios esta vazio ou nao pode ser lido.",
                    "ERROR",
                )
                return None

            if "usuario" not in df.columns or "senha_hash" not in df.columns:
                registrar_log(
                    "AuthService",
                    f"Colunas necessarias nao encontradas. Colunas presentes: {list(df.columns)}",
                    "ERROR",
                )
                return None

            credenciais_usuario = df[
                df["usuario"].str.strip().str.lower() == usuario.strip().lower()
            ]
            if credenciais_usuario.empty:
                registrar_log(
                    "AuthService", f"Usuario '{usuario}' nao encontrado", "WARNING"
                )
                return None

            row = credenciais_usuario.iloc[0]
            usuario_norm = _normalize_username(usuario)

            # === LOCKOUT CHECK (Fase 5 / DHP) ===
            # Avaliado ANTES do bcrypt para evitar timing leak e enumeracao.
            bloqueado_ate_str = str(row.get("bloqueado_ate", "") or "").strip()
            if bloqueado_ate_str:
                try:
                    expira = datetime.fromisoformat(bloqueado_ate_str)
                    if expira > datetime.now():
                        registrar_log(
                            "AuthService",
                            f"Tentativa em conta bloqueada: {usuario_norm}",
                            "WARNING",
                        )
                        return None  # OWASP A07: mensagem generica na UI
                except ValueError:
                    # timestamp malformado: ignora bloqueio e segue validacao normal
                    pass

            hash_armazenado_str = row.get("senha_hash", "")
            hash_armazenado_bytes = (
                hash_armazenado_str.encode("utf-8")
                if isinstance(hash_armazenado_str, str)
                else str(hash_armazenado_str).encode("utf-8")
            )
            senha_fornecida_bytes = senha_fornecida.encode("utf-8")
            try:
                senha_ok = bcrypt.checkpw(senha_fornecida_bytes, hash_armazenado_bytes)
            except ValueError as exc:
                # Hash armazenado malformado (corrupcao de dados): nao conta como
                # tentativa do usuario para evitar bloqueio por defeito de dados.
                registrar_log("AuthService", f"Erro no bcrypt checkpw: {exc}", "ERROR")
                return None

            if not senha_ok:
                # === FALHA: incrementa contador (pode bloquear) ===
                try:
                    self._persistir_estado_tentativas(df, usuario_norm, sucesso=False)
                except Exception as exc:
                    registrar_log(
                        "AuthService",
                        f"Falha ao incrementar contador de tentativas: {exc}",
                        "ERROR",
                    )
                registrar_log("AuthService", "Resultado da autenticacao: Falha", "INFO")
                return None

            # === SUCESSO: reseta contador e atualiza ultimo_acesso ===
            ultimo_acesso_atual = str(row.get("ultimo_acesso", "") or "")
            try:
                novo_ultimo_acesso = self._persistir_estado_tentativas(
                    df, usuario_norm, sucesso=True
                )
                if novo_ultimo_acesso:
                    ultimo_acesso_atual = novo_ultimo_acesso
            except Exception as exc:
                # Falha ao persistir reset nao deve bloquear um login valido.
                registrar_log(
                    "AuthService",
                    f"Falha ao resetar contador em sucesso (login mantido): {exc}",
                    "ERROR",
                )

            registrar_log("AuthService", "Resultado da autenticacao: Sucesso", "INFO")
            return {
                "usuario": row.get("usuario", ""),
                "nivel_acesso": row.get("nivel_acesso", "DIAGNOSTICO"),
                "status": row.get("status", "ATIVO"),
                "data_criacao": row.get("data_criacao", ""),
                "ultimo_acesso": ultimo_acesso_atual,
            }
        except Exception as exc:
            registrar_log(
                "AuthService",
                f"Erro inesperado no autenticar_credenciais: {exc}",
                "ERROR",
            )
            return None

    def verificar_senha(self, usuario: str, senha_fornecida: str) -> bool:
        """
        Verifica se a senha fornecida corresponde ao hash armazenado.
        """
        try:
            df = self.load_users_df()
            if df.empty:
                registrar_log(
                    "AuthService",
                    "usuarios.csv vazio. Execute migracao legado por comando operacional.",
                    "WARNING",
                )
                return False

            if df is None or df.empty:
                registrar_log(
                    "AuthService",
                    "Arquivo de usuarios esta vazio ou nao pode ser lido.",
                    "ERROR",
                )
                return False

            if "usuario" not in df.columns or "senha_hash" not in df.columns:
                registrar_log(
                    "AuthService",
                    f"Colunas necessarias nao encontradas. Colunas presentes: {list(df.columns)}",
                    "ERROR",
                )
                return False

            credenciais_usuario = df[
                df["usuario"].str.strip().str.lower() == usuario.strip().lower()
            ]
            if credenciais_usuario.empty:
                registrar_log("AuthService", f"Usuario '{usuario}' nao encontrado", "WARNING")
                return False

            hash_armazenado_str = credenciais_usuario.iloc[0]["senha_hash"]
            hash_armazenado_bytes = (
                hash_armazenado_str.encode("utf-8")
                if isinstance(hash_armazenado_str, str)
                else str(hash_armazenado_str).encode("utf-8")
            )

            senha_fornecida_bytes = senha_fornecida.encode("utf-8")
            try:
                resultado = bcrypt.checkpw(senha_fornecida_bytes, hash_armazenado_bytes)
            except ValueError as exc:
                registrar_log("AuthService", f"Erro no bcrypt checkpw: {exc}", "ERROR")
                return False

            registrar_log(
                "AuthService",
                f"Resultado da autenticacao: {'Sucesso' if resultado else 'Falha'}",
                "INFO",
            )
            return resultado

        except Exception as exc:
            registrar_log("AuthService", f"Erro inesperado no verificar_senha: {exc}", "ERROR")
            return False

    def salvar_credenciais_seguro(
        self,
        df: pd.DataFrame,
        *,
        actor_username: Optional[str] = None,
        actor_access_level: Optional[str] = None,
        system_operation: bool = False,
    ) -> bool:
        """
        Salva o DataFrame de usuarios de forma segura usando
        File Locking e retry de I/O.
        """
        actor_missing = not str(actor_username or "").strip() and not str(actor_access_level or "").strip()
        # Compatibilidade legado: chamadas antigas deste facade nao informam ator.
        effective_system_operation = system_operation or actor_missing
        return self.save_users_df(
            df,
            actor_username=actor_username,
            actor_access_level=actor_access_level,
            system_operation=effective_system_operation,
        )

    def atualizar_senha(
        self,
        usuario: str,
        nova_senha_hash: str,
        *,
        actor_username: Optional[str] = None,
        actor_access_level: Optional[str] = None,
        system_operation: bool = False,
    ) -> bool:
        """
        Atualiza a senha de um usuario de forma segura (Read-Modify-Write com Lock).
        """
        try:
            df = self.load_users_df()
            if df is None or df.empty:
                registrar_log(
                    "AuthService",
                    "Arquivo de usuarios vazio ou nao encontrado.",
                    "ERROR",
                )
                return False

            if "usuario" not in df.columns or "senha_hash" not in df.columns:
                registrar_log(
                    "AuthService",
                    "Colunas obrigatorias ausentes no arquivo de usuarios.",
                    "ERROR",
                )
                return False

            mask = df["usuario"].str.strip().str.lower() == usuario.strip().lower()
            if not mask.any():
                return False

            if not system_operation:
                actor = str(actor_username or "").strip().lower()
                target = str(usuario or "").strip().lower()
                resolved_level = self._resolve_actor_access_level(
                    actor_username=actor_username,
                    actor_access_level=actor_access_level,
                )
                same_user = bool(actor) and actor == target
                if not (same_user or is_privileged(resolved_level)):
                    registrar_log(
                        "AuthService",
                        (
                            "Acesso negado para atualizar senha. "
                            f"ator='{actor_username or ''}' alvo='{usuario}' "
                            f"nivel='{resolved_level or 'DESCONHECIDO'}'"
                        ),
                        "WARNING",
                    )
                    return False
            else:
                same_user = False

            df.loc[mask, "senha_hash"] = nova_senha_hash
            return self.save_users_df(
                df,
                actor_username=actor_username,
                actor_access_level=actor_access_level,
                system_operation=(system_operation or same_user),
            )
        except Exception as exc:
            registrar_log("AuthService", f"Erro ao atualizar senha segura: {exc}", "ERROR")
            return False

    def unificar_credenciais_legadas(
        self,
        usuario: Optional[str] = None,
        *,
        default_access_level: str = "DIAGNOSTICO",
    ) -> Dict[str, int]:
        """
        Unifica credenciais.csv dentro de usuarios.csv (migracao segura).

        Args:
            usuario: Se informado, limita a migracao a esse usuario.
            default_access_level: Nivel aplicado a novos usuarios sem nivel no legado.

        Returns:
            Dicionario com contagens de criacao/atualizacao.
        """
        summary = {"total": 0, "created": 0, "updated": 0, "skipped": 0}
        cred_path = _resolve_legacy_credentials_path()
        policy = RetryPolicy.from_env()

        if not cred_path or not path_exists_with_retry(cred_path, policy=policy):
            registrar_log(
                "AuthService",
                "credenciais.csv legado ausente ou igual a usuarios.csv. Nenhuma migracao executada.",
                "INFO",
            )
            return summary

        cred_df = _read_credentials_df(cred_path)
        if cred_df is None or cred_df.empty:
            registrar_log(
                "AuthService",
                "credenciais.csv vazio ou ilegivel. Nenhuma migracao executada.",
                "WARNING",
            )
            return summary

        cred_df = cred_df.copy()
        rename_map = {}
        for col in cred_df.columns:
            key = str(col).strip().lower()
            if key in {"usuario", "user", "login"}:
                rename_map[col] = "usuario"
            elif key in {"senha", "senha_hash", "senha hash"}:
                rename_map[col] = "senha_hash"
            elif key in {"nivel", "nivel_acesso", "nivel acesso"}:
                rename_map[col] = "nivel_acesso"
        if rename_map:
            cred_df = cred_df.rename(columns=rename_map)

        if "usuario" not in cred_df.columns or "senha_hash" not in cred_df.columns:
            registrar_log(
                "AuthService",
                "Colunas obrigatorias ausentes em credenciais.csv.",
                "ERROR",
            )
            return summary

        users_df = self.load_users_df()
        users_df = _normalize_users_df(users_df)
        existing = {
            _normalize_username(u): idx
            for idx, u in enumerate(users_df.get("usuario", []))
        }

        for _, row in cred_df.iterrows():
            raw_user = row.get("usuario", "")
            user_norm = _normalize_username(raw_user)
            if not user_norm:
                summary["skipped"] += 1
                continue
            if usuario and user_norm != _normalize_username(usuario):
                continue

            senha_hash = str(row.get("senha_hash", "") or "").strip()
            if not senha_hash:
                summary["skipped"] += 1
                continue

            summary["total"] += 1
            if user_norm in existing:
                idx = existing[user_norm]
                current_hash = str(users_df.at[idx, "senha_hash"] or "")
                if senha_hash and senha_hash != current_hash:
                    users_df.at[idx, "senha_hash"] = senha_hash
                    summary["updated"] += 1

                cred_level = str(row.get("nivel_acesso", "") or "").strip().upper()
                if cred_level and not str(users_df.at[idx, "nivel_acesso"] or "").strip():
                    users_df.at[idx, "nivel_acesso"] = cred_level
                continue

            nivel = str(row.get("nivel_acesso") or default_access_level).strip().upper()
            new_row = _build_user_record(raw_user, senha_hash, nivel)
            users_df = pd.concat([users_df, pd.DataFrame([new_row])], ignore_index=True)
            existing[user_norm] = len(users_df) - 1
            summary["created"] += 1

        if summary["created"] or summary["updated"]:
            if not self.save_users_df(users_df, system_operation=True):
                registrar_log(
                    "AuthService",
                    "Falha ao salvar usuarios durante migracao de credenciais.",
                    "ERROR",
                )

        registrar_log(
            "AuthService",
            f"Migracao credenciais: total={summary['total']}, created={summary['created']}, "
            f"updated={summary['updated']}, skipped={summary['skipped']}",
            "INFO",
        )
        return summary

    def executar_migracao_credenciais_legadas(
        self,
        usuario: Optional[str] = None,
        *,
        default_access_level: str = "DIAGNOSTICO",
    ) -> Dict[str, Any]:
        """
        Comando operacional explicito para migracao de credenciais legadas.

        Este comando deve ser acionado manualmente (admin/script), nunca no fluxo
        implicito de autenticacao.
        """
        try:
            summary = self.unificar_credenciais_legadas(
                usuario=usuario,
                default_access_level=default_access_level,
            )
        except Exception as exc:
            registrar_log(
                "AuthService",
                f"Falha no comando operacional de migracao legado: {exc}",
                "ERROR",
            )
            return build_error_result(
                code=ErrorCode.AUTH_LEGACY_MIGRATION_FAILED,
                message=str(exc),
                source="auth_service.executar_migracao_credenciais_legadas",
                total=0,
                created=0,
                updated=0,
                skipped=0,
            )

        return {
            "sucesso": True,
            "erro": "",
            "erro_codigo": "",
            **summary,
        }

    def sincronizar_usuario_com_credenciais(
        self, usuario: str, *, nivel_acesso: str = "ADMIN"
    ) -> bool:
        """
        Sincroniza o cadastro do usuario em usuarios.csv com credenciais.csv legado.

        Args:
            usuario: Login do usuario a sincronizar.
            nivel_acesso: Nivel de acesso desejado (default: ADMIN).

        Returns:
            True se sincronizado com sucesso, False caso contrario.
        """
        usuario_norm = str(usuario).strip()
        if not usuario_norm:
            registrar_log("AuthService", "Usuario vazio para sincronizacao.", "ERROR")
            return False

        summary = self.unificar_credenciais_legadas(
            usuario=usuario_norm, default_access_level=nivel_acesso
        )
        return (summary.get("created", 0) + summary.get("updated", 0)) > 0

