# -*- coding: utf-8 -*-
"""
Audit Logger - Sistema de Auditoria Completo

Registra TODAS as ações do usuário com metadados completos:
- Timestamp preciso
- Usuário que executou
- IP e hostname da máquina
- Ação executada
- Dados antes/depois (quando aplicável)

Formato: JSON estruturado para fácil análise/parsing
"""

import json
import os
import socket
import platform
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import logging
from logging.handlers import RotatingFileHandler


def _resolve_audit_log_dir() -> str:
    """Resolve o diretório de auditoria via config service, com fallback seguro."""
    try:
        from services.core.config_service import config_service
        paths = config_service.get_paths()
        logs_dir = paths.get("logs_dir")
        if logs_dir:
            return os.path.join(logs_dir, "audit")
    except Exception:
        pass
    return "logs/audit"


class AuditLogger:
    """
    Logger de auditoria para rastreamento de ações de usuários.

    Thread-safe e com rotação automática de arquivos.
    """

    def __init__(self, log_dir: str | None = None):
        if log_dir is None:
            log_dir = _resolve_audit_log_dir()
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Criar logger específico para auditoria
        self.logger = logging.getLogger("AuditLogger")
        self.logger.setLevel(logging.INFO)
        
        # Evitar duplicação de handlers
        if not self.logger.handlers:
            # Arquivo de log com rotação (10MB por arquivo, 10 backups)
            log_file = self.log_dir / "audit.log"
            handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=10,
                encoding='utf-8'
            )
            
            # Formato: apenas a mensagem JSON (sem prefixos do logging)
            handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(handler)
        
        # Cache de metadados do sistema (não muda durante execução)
        self._system_metadata = self._get_system_metadata()
    
    def _get_system_metadata(self) -> Dict[str, str]:
        """Coleta metadados do sistema (hostname, IP, SO, etc.)."""
        try:
            hostname = socket.gethostname()
            
            # Tentar obter IP local
            try:
                # Conectar a um servidor externo para descobrir IP local usado
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip_address = s.getsockname()[0]
                s.close()
            except (OSError, socket.error) as e:
                # Falha de rede é esperada em ambientes sem internet
                logging.debug(f"Falha ao obter IP via socket UDP: {e}")
                try:
                    ip_address = socket.gethostbyname(hostname)
                except socket.gaierror as e2:
                    # Fallback final se DNS também falhar
                    logging.debug(f"Falha ao resolver hostname: {e2}")
                    ip_address = "127.0.0.1"
            
            return {
                "hostname": hostname,
                "ip_address": ip_address,
                "os": platform.system(),
                "os_version": platform.version(),
                "machine": platform.machine(),
                "python_version": platform.python_version()
            }
        except Exception as e:
            return {"error": f"Failed to get metadata: {e}"}
    
    def log_action(
        self,
        action: str,
        usuario: str,
        details: Optional[Dict[str, Any]] = None,
        sensitive: bool = False
    ) -> None:
        """
        Registra uma ação de usuário.
        
        Args:
            action: Nome da ação (ex: "LOGIN", "ANALISE_EXECUTADA", "ARQUIVO_DELETADO")
            usuario: Nome do usuário que executou
            details: Dicionário com detalhes específicos da ação
            sensitive: Se True, marca como dado sensível (para compliance LGPD/GDPR)
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "user": usuario,
            "system": self._system_metadata,
            "details": details or {},
            "sensitive": sensitive
        }
        
        # Serializar para JSON (uma linha por registro)
        log_line = json.dumps(log_entry, ensure_ascii=False)
        self.logger.info(log_line)
    
    def log_login(self, usuario: str, success: bool, ip: str = None) -> None:
        """Log de tentativa de login."""
        self.log_action(
            action="LOGIN" if success else "LOGIN_FAILED",
            usuario=usuario,
            details={
                "success": success,
                "ip_origem": ip or self._system_metadata.get("ip_address")
            },
            sensitive=True
        )
    
    def log_logout(self, usuario: str) -> None:
        """Log de logout."""
        self.log_action(
            action="LOGOUT",
            usuario=usuario
        )
    
    def log_analysis(
        self,
        usuario: str,
        exame: str,
        arquivo: str,
        num_amostras: int,
        status: str
    ) -> None:
        """Log de execução de análise."""
        self.log_action(
            action="ANALISE_EXECUTADA",
            usuario=usuario,
            details={
                "exame": exame,
                "arquivo_corrida": arquivo,
                "total_amostras": num_amostras,
                "status_corrida": status
            }
        )
    
    def log_data_modification(
        self,
        usuario: str,
        entity_type: str,
        entity_id: str,
        operation: str,  # CREATE, UPDATE, DELETE
        before: Optional[Dict] = None,
        after: Optional[Dict] = None
    ) -> None:
        """Log de modificação de dados."""
        self.log_action(
            action=f"DATA_{operation}",
            usuario=usuario,
            details={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "before": before,
                "after": after
            }
        )
    
    def log_file_access(
        self,
        usuario: str,
        file_path: str,
        operation: str,  # READ, WRITE, DELETE
        success: bool = True
    ) -> None:
        """Log de acesso a arquivos."""
        self.log_action(
            action=f"FILE_{operation}",
            usuario=usuario,
            details={
                "file": file_path,
                "operation": operation,
                "success": success
            }
        )
    
    def log_export(
        self,
        usuario: str,
        formato: str,
        destino: str,
        num_registros: int
    ) -> None:
        """Log de exportação de dados."""
        self.log_action(
            action="EXPORT",
            usuario=usuario,
            details={
                "formato": formato,
                "destino": destino,
                "total_registros": num_registros
            },
            sensitive=True  # Exportação pode conter dados sensíveis
        )
    
    def log_config_change(
        self,
        usuario: str,
        config_key: str,
        old_value: Any,
        new_value: Any
    ) -> None:
        """Log de mudança de configuração."""
        self.log_action(
            action="CONFIG_CHANGE",
            usuario=usuario,
            details={
                "config_key": config_key,
                "old_value": str(old_value),
                "new_value": str(new_value)
            }
        )
    
    def log_user_management(
        self,
        admin_usuario: str,
        target_usuario: str,
        operation: str,  # CREATE, UPDATE, DELETE, RESET_PASSWORD
        details: Optional[Dict] = None
    ) -> None:
        """Log de gerenciamento de usuários."""
        self.log_action(
            action=f"USER_{operation}",
            usuario=admin_usuario,
            details={
                "target_user": target_usuario,
                **(details or {})
            },
            sensitive=True
        )
    
    def query_logs(
        self,
        usuario: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> list:
        """
        Consulta logs de auditoria.
        
        Args:
            usuario: Filtrar por usuário
            action: Filtrar por ação
            start_date: Data inicial
            end_date: Data final
            limit: Máximo de registros
        
        Returns:
            Lista de entradas de log
        """
        try:
            from utils.logger import registrar_log
            registrar_log(
                "RuntimeUsage",
                (
                    "feature=suspected_orphan "
                    "function=utils.audit_logger.query_logs "
                    "event=invoked "
                    f"limit={int(limit)}"
                ),
                "INFO",
            )
        except Exception:
            pass

        results = []
        log_file = self.log_dir / "audit.log"
        
        if not log_file.exists():
            return results
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if len(results) >= limit:
                        break
                    
                    try:
                        entry = json.loads(line.strip())
                        
                        # Aplicar filtros
                        if usuario and entry.get("user") != usuario:
                            continue
                        
                        if action and entry.get("action") != action:
                            continue
                        
                        if start_date:
                            entry_date = datetime.fromisoformat(entry["timestamp"])
                            if entry_date < start_date:
                                continue
                        
                        if end_date:
                            entry_date = datetime.fromisoformat(entry["timestamp"])
                            if entry_date > end_date:
                                continue
                        
                        results.append(entry)
                        
                    except json.JSONDecodeError:
                        continue
            
            return results
            
        except Exception as e:
            print(f"Erro ao consultar logs: {e}")
            return []


# Singleton global
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Retorna instância singleton do audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# Decorator para auditoria automática de funções
def audit_action(action_name: str, get_user_func=None):
    """
    Decorator para adicionar auditoria automática a funções.
    
    Uso:
        @audit_action("ANALISE_EXECUTADA", get_user_func=lambda: app_state.usuario)
        def executar_analise(...):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_audit_logger()
            usuario = get_user_func() if get_user_func else "SYSTEM"
            
            try:
                result = func(*args, **kwargs)
                logger.log_action(action_name, usuario, {"status": "success"})
                return result
            except Exception as e:
                logger.log_action(
                    action_name,
                    usuario,
                    {"status": "error", "error": str(e)}
                )
                raise
        
        return wrapper
    return decorator
