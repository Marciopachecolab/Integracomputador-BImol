#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
services/history_gal_sync.py

Módulo para sincronizar status de envio GAL com o histórico CSV.
Fornece funções para:
- Atualizar status após envio bem-sucedido
- Registrar falhas de envio
- Consultar estado de registros
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import pandas as pd

# Garante que o diretório raiz está no path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from utils.csv_lock import CSVFileLock
from utils.logger import registrar_log
from utils.network_io import RetryPolicy, call_with_retry, path_exists_with_retry
from application.access_control import (
    AuthorizationDeniedError,
    ensure_operation_allowed,
    normalize_access_level,
)
from autenticacao.auth_service import AuthService
from domain.error_codes import ErrorCode
from services.core.error_contracts import build_error_result


class HistoricoGALSync:
    """
    Gerenciador de sincronização entre análises e envio GAL.
    Atualiza histórico CSV com status de envio.
    """
    
    def __init__(self, csv_path: str = None):
        """
        Inicializa o sincronizador.
        
        Args:
            csv_path: Caminho do arquivo histórico
        """
        if csv_path is None:
            from services.core.config_service import config_service
            resolved_csv_path = config_service.get_paths()["gal_history_csv"]
        else:
            resolved_csv_path = csv_path
        
        self.csv_path = Path(resolved_csv_path)
        self._valida_arquivo()

    def _resolve_actor_access_level(
        self,
        *,
        actor_username: Optional[str],
        actor_access_level: Optional[str],
    ) -> str:
        """Resolve nivel canonico do ator (prioriza usuario persistido)."""
        actor = str(actor_username or "").strip()
        if actor:
            user = AuthService().obter_usuario(actor)
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
            registrar_log("Historico GAL Sync", str(exc), "WARNING")
            return False
    
    def _valida_arquivo(self) -> None:
        """Valida se arquivo existe e tem estrutura correta."""
        policy = RetryPolicy.from_env()
        if not path_exists_with_retry(self.csv_path, policy=policy):
            raise FileNotFoundError(f"Arquivo nao encontrado: {self.csv_path}")

        try:
            df = self._read_csv(nrows=1)

            campos_obrigatorios = [
                "id_registro",
                "status_gal",
                "data_hora_envio",
                "usuario_envio",
                "sucesso_envio",
                "detalhes_envio",
                "atualizado_em"
            ]

            campos_faltando = [c for c in campos_obrigatorios if c not in df.columns]
            if campos_faltando:
                raise ValueError(
                    f"Campos faltando no CSV: {campos_faltando}. "
                    f"Execute migracao primeiro: scripts/migrate_historical_csv.py"
                )
        except Exception as e:
            raise ValueError(f"Erro ao validar CSV: {e}")

    def _read_csv(self, nrows: Optional[int] = None, _already_locked: bool = False) -> pd.DataFrame:
        """Le CSV com retry/backoff para uso em ambiente de rede."""
        policy = RetryPolicy.from_env()
        if not path_exists_with_retry(self.csv_path, policy=policy):
            raise FileNotFoundError(f"Arquivo nao encontrado: {self.csv_path}")

        def _read() -> pd.DataFrame:
            if _already_locked:
                return pd.read_csv(
                    self.csv_path,
                    sep=";",
                    encoding="utf-8",
                    nrows=nrows,
                )
            with CSVFileLock(self.csv_path):
                return pd.read_csv(
                    self.csv_path,
                    sep=";",
                    encoding="utf-8",
                    nrows=nrows,
                )

        return call_with_retry(
            _read,
            op_name="read_history_csv",
            path=self.csv_path,
            policy=policy,
        )

    def marcar_enviado(
        self,
        id_registros: List[str],
        usuario_envio: str,
        detalhes: str = "Enviado com sucesso para GAL",
        *,
        actor_access_level: Optional[str] = None,
        system_operation: bool = False,
    ) -> Dict[str, Any]:
        """
        Marca registros como enviados com sucesso.
        
        Args:
            id_registros: Lista de IDs (UUIDs) dos registros
            usuario_envio: Quem fez o envio
            detalhes: Mensagem descritiva
        
        Returns:
            Dict com estatísticas da atualização
        """
        
        return self._atualizar_registros(
            id_registros=id_registros,
            status_gal="enviado",
            sucesso=True,
            usuario_envio=usuario_envio,
            detalhes=detalhes,
            actor_username=usuario_envio,
            actor_access_level=actor_access_level,
            system_operation=system_operation,
        )
    
    def marcar_falha_envio(
        self,
        id_registros: List[str],
        usuario_envio: str,
        erro: str,
        *,
        actor_access_level: Optional[str] = None,
        system_operation: bool = False,
    ) -> Dict[str, Any]:
        """
        Marca registros como falha no envio.
        
        Args:
            id_registros: Lista de IDs (UUIDs) dos registros
            usuario_envio: Quem tentou fazer o envio
            erro: Mensagem de erro do servidor/sistema
        
        Returns:
            Dict com estatísticas da atualização
        """
        
        return self._atualizar_registros(
            id_registros=id_registros,
            status_gal="falha no envio",
            sucesso=False,
            usuario_envio=usuario_envio,
            detalhes=f"Erro: {erro}",
            actor_username=usuario_envio,
            actor_access_level=actor_access_level,
            system_operation=system_operation,
        )
    
    def _atualizar_registros(
        self,
        id_registros: List[str],
        status_gal: str,
        sucesso: bool,
        usuario_envio: str,
        detalhes: str,
        *,
        actor_username: Optional[str],
        actor_access_level: Optional[str],
        system_operation: bool,
    ) -> Dict[str, Any]:
        """
        Atualiza registros no CSV com informações de envio.
        
        Args:
            id_registros: Lista de IDs
            status_gal: Novo status
            sucesso: True/False para resultado
            usuario_envio: Quem fez o envio
            detalhes: Detalhes do envio/erro
        
        Returns:
            Estatísticas da atualização
        """
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not self._is_operation_allowed(
            operation="history.gal.write",
            actor_username=actor_username,
            actor_access_level=actor_access_level,
            system_operation=system_operation,
        ):
            return build_error_result(
                code=ErrorCode.HISTORY_ACCESS_DENIED,
                message="Acesso negado para operacao de escrita no historico GAL",
                source="history_gal_sync._atualizar_registros",
                registros_atualizados=0,
                registros_nao_encontrados=id_registros,
            )
        
        try:
            # 0. Adquire lock para garantir atomicidade da transação (Leitura -> Modificação -> Escrita)
            from services.persistence.csv_lock import csv_lock
            if not csv_lock.acquire(str(self.csv_path)):
                raise TimeoutError(f"Não foi possível adquirir lock para {self.csv_path}")

            try:
                # 1. Lê o CSV completo (lock já adquirido pelo csv_lock.acquire acima)
                df = self._read_csv(_already_locked=True)
                # Evita warning/falha futura de dtype ao atualizar colunas textuais/booleanas.
                for col in (
                    "data_hora_envio",
                    "usuario_envio",
                    "sucesso_envio",
                    "detalhes_envio",
                    "atualizado_em",
                ):
                    if col in df.columns:
                        df[col] = df[col].astype("object")
                
                registros_atualizados = 0
                registros_nao_encontrados = []
                
                # 2. Para cada ID fornecido
                for id_reg in id_registros:
                    mask = df["id_registro"] == id_reg
                    
                    if not mask.any():
                        registros_nao_encontrados.append(id_reg)
                        continue
                    
                    # 3. Atualiza campos de envio
                    df.loc[mask, "status_gal"] = status_gal
                    df.loc[mask, "data_hora_envio"] = timestamp
                    df.loc[mask, "usuario_envio"] = usuario_envio
                    df.loc[mask, "sucesso_envio"] = sucesso
                    df.loc[mask, "detalhes_envio"] = detalhes
                    df.loc[mask, "atualizado_em"] = timestamp
                    
                    registros_atualizados += 1
                
                # 4. Escreve de volta (usando write_locked_dataframe pois já temos o lock)
                csv_lock.write_locked_dataframe(df, str(self.csv_path), sep=";", index=False, encoding="utf-8")
                
                # 5. Prepara resposta
                resultado = {
                    "sucesso": True,
                    "registros_atualizados": registros_atualizados,
                    "registros_nao_encontrados": registros_nao_encontrados,
                    "timestamp": timestamp,
                    "status": status_gal,
                    "usuario": usuario_envio,
                    "erro_codigo": "",
                }
                
                # Log
                mensagem = (
                    f"Atualizado histórico: {registros_atualizados} registros com status "
                    f"'{status_gal}', enviados por {usuario_envio}"
                )
                if registros_nao_encontrados:
                    mensagem += f" ({len(registros_nao_encontrados)} não encontrados)"
                
                registrar_log("Histórico GAL Sync", mensagem, "INFO")
                
                return resultado

            finally:
                # Libera o lock
                csv_lock.release(str(self.csv_path))
        
        except Exception as e:
            mensagem = f"Erro ao atualizar registros: {e}"
            registrar_log("Histórico GAL Sync", mensagem, "ERROR")

            return build_error_result(
                code=ErrorCode.HISTORY_WRITE_FAILED,
                message=str(e),
                source="history_gal_sync._atualizar_registros",
                registros_atualizados=0,
                registros_nao_encontrados=id_registros,
            )
    
    def obter_nao_enviados(
        self,
        exame: Optional[str] = None,
        limite: int = 100,
        *,
        actor_username: Optional[str] = None,
        actor_access_level: Optional[str] = None,
        system_operation: bool = False,
    ) -> pd.DataFrame:
        """
        Obtém registros que ainda não foram enviados para GAL.
        
        Args:
            exame: Filtrar por exame (opcional)
            limite: Máximo de registros a retornar
        
        Returns:
            DataFrame com registros não enviados
        """
        
        if not self._is_operation_allowed(
            operation="history.gal.read",
            actor_username=actor_username,
            actor_access_level=actor_access_level,
            system_operation=system_operation,
        ):
            return pd.DataFrame()

        try:
            df = self._read_csv()
            
            # Filtra por status
            mask = df["status_gal"] == "não enviado"
            
            # Filtra por exame se especificado
            if exame:
                mask = mask & (df["exame"] == exame)
            
            resultado = df[mask].head(limite)
            
            return resultado
        
        except Exception as e:
            registrar_log(
                "Histórico GAL Sync",
                f"Erro ao obter não enviados: {e}",
                "ERROR"
            )
            return pd.DataFrame()
    
    def obter_por_id(
        self,
        id_registro: str,
        *,
        actor_username: Optional[str] = None,
        actor_access_level: Optional[str] = None,
        system_operation: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Obtém detalhes de um registro pelo ID.
        
        Args:
            id_registro: UUID do registro
        
        Returns:
            Dict com dados do registro ou None se não encontrado
        """
        
        if not self._is_operation_allowed(
            operation="history.gal.read",
            actor_username=actor_username,
            actor_access_level=actor_access_level,
            system_operation=system_operation,
        ):
            return None

        try:
            df = self._read_csv()
            
            mask = df["id_registro"] == id_registro
            if not mask.any():
                return None
            
            linha = df[mask].iloc[0]
            return linha.to_dict()
        
        except Exception as e:
            registrar_log(
                "Histórico GAL Sync",
                f"Erro ao obter registro {id_registro}: {e}",
                "ERROR"
            )
            return None
    
    def obter_status_lote(
        self,
        ids: List[str],
        *,
        actor_username: Optional[str] = None,
        actor_access_level: Optional[str] = None,
        system_operation: bool = False,
    ) -> Dict[str, Any]:
        """
        Obtém resumo de status para múltiplos registros.
        
        Args:
            ids: Lista de IDs
        
        Returns:
            Dict com contagem por status
        """
        
        if not self._is_operation_allowed(
            operation="history.gal.read",
            actor_username=actor_username,
            actor_access_level=actor_access_level,
            system_operation=system_operation,
        ):
            return {"total": 0, "erro": "Acesso negado para leitura do historico GAL"}

        try:
            df = self._read_csv()
            
            df_filtro = df[df["id_registro"].isin(ids)]
            
            resultado = {
                "total": len(df_filtro),
                "não enviado": (df_filtro["status_gal"] == "não enviado").sum(),
                "não enviável": (df_filtro["status_gal"] == "não enviável").sum(),
                "enviado": (df_filtro["status_gal"] == "enviado").sum(),
                "falha no envio": (df_filtro["status_gal"] == "falha no envio").sum(),
                "registros": df_filtro[["id_registro", "status_gal", "codigo", "amostra"]].to_dict(orient="records")
            }
            
            return resultado
        
        except Exception as e:
            registrar_log(
                "Histórico GAL Sync",
                f"Erro ao obter status do lote: {e}",
                "ERROR"
            )
            return {"total": 0, "erro": str(e)}
    
    def reabrir_para_envio(
        self,
        id_registros: List[str],
        *,
        usuario_envio: str = "",
        actor_access_level: Optional[str] = None,
        system_operation: bool = False,
    ) -> Dict[str, Any]:
        """
        Reabre registros que falharam, para tentar enviar novamente.
        
        Args:
            id_registros: Lista de IDs que falharam
        
        Returns:
            Estatísticas
        """
        
        return self._atualizar_registros(
            id_registros=id_registros,
            status_gal="não enviado",
            sucesso=None,  # Volta ao estado inicial
            usuario_envio=usuario_envio,
            detalhes="Reabertura para retentativa",
            actor_username=usuario_envio,
            actor_access_level=actor_access_level,
            system_operation=system_operation,
        )


# Instância global para facilitar uso
_sync = None


def get_gal_sync(csv_path: str = None) -> HistoricoGALSync:
    """Factory para obter instância do sincronizador (singleton)."""
    if csv_path is None:
        from services.core.config_service import config_service
        csv_path = config_service.get_paths()["gal_history_csv"]
    global _sync
    if _sync is None:
        _sync = HistoricoGALSync(csv_path)
    return _sync


# Funções de conveniência
def marcar_enviados(
    id_registros: List[str],
    usuario: str,
    csv_path: str = "logs/historico_analises.csv",
    *,
    actor_access_level: Optional[str] = None,
    system_operation: bool = False,
) -> Dict[str, Any]:
    """
    Marca um lote de registros como enviados com sucesso.
    
    Args:
        id_registros: Lista de UUIDs
        usuario: Quem fez o envio
        csv_path: Caminho do histórico
    
    Returns:
        Resultado da operação
    """
    sync = get_gal_sync(csv_path)
    return sync.marcar_enviado(
        id_registros=id_registros,
        usuario_envio=usuario,
        detalhes="Enviado com sucesso para GAL",
        actor_access_level=actor_access_level,
        system_operation=system_operation,
    )


def marcar_falha(
    id_registros: List[str],
    usuario: str,
    erro: str,
    csv_path: str = "logs/historico_analises.csv",
    *,
    actor_access_level: Optional[str] = None,
    system_operation: bool = False,
) -> Dict[str, Any]:
    """
    Marca um lote de registros como falha no envio.
    
    Args:
        id_registros: Lista de UUIDs
        usuario: Quem tentou fazer o envio
        erro: Mensagem de erro
        csv_path: Caminho do histórico
    
    Returns:
        Resultado da operação
    """
    sync = get_gal_sync(csv_path)
    return sync.marcar_falha_envio(
        id_registros=id_registros,
        usuario_envio=usuario,
        erro=erro,
        actor_access_level=actor_access_level,
        system_operation=system_operation,
    )


if __name__ == "__main__":
    # Exemplo de uso
    sync = HistoricoGALSync()
    
    # Obtém registros não enviados
    df_nao_enviados = sync.obter_nao_enviados(
        limite=10,
        actor_access_level="MASTER",
    )
    print(f"Registros não enviados: {len(df_nao_enviados)}")
    print(df_nao_enviados[["id_registro", "exame", "codigo", "status_gal"]])
