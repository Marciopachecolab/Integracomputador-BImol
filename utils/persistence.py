"""
Sistema de Persistência de Estado do IntegRAGal

Gerencia salvamento e restauração do estado da aplicação:
- Posição e tamanho de janelas
- Abas abertas
- Filtros ativos
- Histórico de navegação
- Estado de componentes
"""

import json
import pickle
import threading
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
import os

from utils.logger import registrar_log
from utils.error_handler import ErrorHandler, safe_operation
from utils.validator import Validator


class PersistenceManager:
    """Gerenciador de persistência de estado"""
    
    # Caminhos
    STATE_DIR = Path("data/state")
    SESSION_FILE = STATE_DIR / "current_session.json"
    WINDOW_STATE_FILE = STATE_DIR / "window_state.json"
    CACHE_DIR = STATE_DIR / "cache"
    
    # Singleton
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Cria diretórios
        self.STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        self.session_data = {}
        self.window_state = {}
        self._initialized = True
    
    # ============================================================================
    # Sessão
    # ============================================================================
    
    @safe_operation(fallback_value={}, context="Carregando sessão")
    def carregar_sessao(self) -> Dict[str, Any]:
        """
        Carrega estado da sessão anterior
        
        Returns:
            Dicionário com estado da sessão
        """
        if not Validator.arquivo_existe(self.SESSION_FILE):
            registrar_log("Persistência", "Nenhuma sessão anterior encontrada", "INFO")
            return {}
        
        with open(self.SESSION_FILE, 'r', encoding='utf-8') as f:
            self.session_data = json.load(f)
        
        registrar_log(
            "Persistência",
            f"Sessão carregada: {len(self.session_data)} itens",
            "INFO"
        )
        
        return self.session_data
    
    @safe_operation(fallback_value=True, context="Salvando sessão")
    def salvar_sessao(self, dados: Optional[Dict[str, Any]] = None) -> bool:
        """
        Salva estado atual da sessão
        
        Args:
            dados: Dados da sessão (usa self.session_data se None)
            
        Returns:
            True se sucesso
        """
        if dados is not None:
            self.session_data = dados
        
        # Adiciona metadata
        self.session_data['_metadata'] = {
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        }
        
        # Salva
        with open(self.SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.session_data, f, indent=2, ensure_ascii=False)
        
        registrar_log(
            "Persistência",
            f"Sessão salva: {len(self.session_data)} itens",
            "INFO"
        )
        
        return True
    
    def set_session_value(self, chave: str, valor: Any):
        """Define valor na sessão"""
        self.session_data[chave] = valor
    
    def get_session_value(self, chave: str, padrao: Any = None) -> Any:
        """Obtém valor da sessão"""
        return self.session_data.get(chave, padrao)
    
    def limpar_sessao(self):
        """Limpa dados da sessão atual"""
        self.session_data = {}
        if self.SESSION_FILE.exists():
            self.SESSION_FILE.unlink()
        
        registrar_log("Persistência", "Sessão limpa", "INFO")
    
    # ============================================================================
    # Estado de Janelas
    # ============================================================================
    
    @safe_operation(fallback_value={}, context="Carregando estado de janelas")
    def carregar_estado_janelas(self) -> Dict[str, Any]:
        """Carrega estado salvo das janelas"""
        if not Validator.arquivo_existe(self.WINDOW_STATE_FILE):
            return {}
        
        with open(self.WINDOW_STATE_FILE, 'r', encoding='utf-8') as f:
            self.window_state = json.load(f)
        
        return self.window_state
    
    @safe_operation(fallback_value=True, context="Salvando estado de janelas")
    def salvar_estado_janelas(self, estados: Optional[Dict[str, Any]] = None) -> bool:
        """Salva estado atual das janelas"""
        if estados is not None:
            self.window_state = estados
        
        with open(self.WINDOW_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.window_state, f, indent=2)
        
        return True
    
    def salvar_geometria_janela(self, janela_id: str, geometria: str):
        """
        Salva geometria de uma janela
        
        Args:
            janela_id: Identificador da janela
            geometria: String de geometria (formato: "WIDTHxHEIGHT+X+Y")
        """
        if janela_id not in self.window_state:
            self.window_state[janela_id] = {}
        
        self.window_state[janela_id]['geometria'] = geometria
        self.salvar_estado_janelas()
    
    def obter_geometria_janela(self, janela_id: str) -> Optional[str]:
        """Obtém geometria salva de uma janela"""
        if janela_id in self.window_state:
            return self.window_state[janela_id].get('geometria')
        return None
    
    def salvar_estado_componente(self, janela_id: str, componente: str, estado: Any):
        """Salva estado de um componente específico"""
        if janela_id not in self.window_state:
            self.window_state[janela_id] = {}
        
        if 'componentes' not in self.window_state[janela_id]:
            self.window_state[janela_id]['componentes'] = {}
        
        self.window_state[janela_id]['componentes'][componente] = estado
        self.salvar_estado_janelas()
    
    def obter_estado_componente(self, janela_id: str, componente: str) -> Optional[Any]:
        """Obtém estado salvo de um componente"""
        if janela_id in self.window_state:
            return self.window_state[janela_id].get('componentes', {}).get(componente)
        return None
    
    # ============================================================================
    # Cache
    # ============================================================================
    
    @safe_operation(fallback_value=None, context="Carregando do cache")
    def carregar_cache(self, chave: str) -> Optional[Any]:
        """
        Carrega dados do cache
        
        Args:
            chave: Chave do cache
            
        Returns:
            Dados cacheados ou None
        """
        cache_file = self.CACHE_DIR / f"{chave}.pkl"
        
        if not Validator.arquivo_existe(cache_file):
            return None
        
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    
    @safe_operation(fallback_value=True, context="Salvando no cache")
    def salvar_cache(self, chave: str, dados: Any, ttl_segundos: Optional[int] = None) -> bool:
        """
        Salva dados no cache
        
        Args:
            chave: Chave do cache
            dados: Dados a cachear
            ttl_segundos: Tempo de vida em segundos (None = sem expiração)
            
        Returns:
            True se sucesso
        """
        cache_file = self.CACHE_DIR / f"{chave}.pkl"
        
        # Cria wrapper com metadata
        wrapper = {
            'dados': dados,
            'timestamp': datetime.now().isoformat(),
            'ttl': ttl_segundos
        }
        
        with open(cache_file, 'wb') as f:
            pickle.dump(wrapper, f)
        
        return True
    
    def limpar_cache(self, chave: Optional[str] = None):
        """
        Limpa cache
        
        Args:
            chave: Se especificado, limpa apenas esta chave. Se None, limpa tudo.
        """
        if chave is not None:
            cache_file = self.CACHE_DIR / f"{chave}.pkl"
            if cache_file.exists():
                cache_file.unlink()
                registrar_log("Persistência", f"Cache '{chave}' limpo", "INFO")
        else:
            # Limpa todo o cache
            for cache_file in self.CACHE_DIR.glob("*.pkl"):
                cache_file.unlink()
            registrar_log("Persistência", "Todo o cache foi limpo", "INFO")
    
    def verificar_cache_expirado(self, chave: str) -> bool:
        """
        Verifica se cache está expirado
        
        Returns:
            True se expirado ou não existe
        """
        cache_file = self.CACHE_DIR / f"{chave}.pkl"
        
        if not cache_file.exists():
            return True
        
        try:
            with open(cache_file, 'rb') as f:
                wrapper = pickle.load(f)
            
            if wrapper.get('ttl') is None:
                return False  # Sem expiração
            
            timestamp = datetime.fromisoformat(wrapper['timestamp'])
            idade = (datetime.now() - timestamp).total_seconds()
            
            return idade > wrapper['ttl']
            
        except Exception:
            return True
    
    def obter_tamanho_cache(self) -> int:
        """Retorna tamanho total do cache em bytes"""
        total = 0
        for cache_file in self.CACHE_DIR.glob("*.pkl"):
            total += cache_file.stat().st_size
        return total
    
    # ============================================================================
    # Histórico
    # ============================================================================
    
    def adicionar_historico(self, tipo: str, item: Dict[str, Any]):
        """
        Adiciona item ao histórico
        
        Args:
            tipo: Tipo de histórico (ex: 'navegacao', 'busca', 'exportacao')
            item: Item a adicionar
        """
        chave_historico = f"historico_{tipo}"
        
        if chave_historico not in self.session_data:
            self.session_data[chave_historico] = []
        
        # Adiciona timestamp
        item['timestamp'] = datetime.now().isoformat()
        
        # Adiciona ao início da lista
        self.session_data[chave_historico].insert(0, item)
        
        # Limita tamanho (mantém últimos 100)
        self.session_data[chave_historico] = self.session_data[chave_historico][:100]
    
    def obter_historico(self, tipo: str, limite: int = 10) -> list:
        """
        Obtém histórico de um tipo
        
        Args:
            tipo: Tipo de histórico
            limite: Número máximo de itens
            
        Returns:
            Lista de itens do histórico
        """
        chave_historico = f"historico_{tipo}"
        historico = self.session_data.get(chave_historico, [])
        return historico[:limite]
    
    def limpar_historico(self, tipo: Optional[str] = None):
        """Limpa histórico"""
        if tipo is not None:
            chave_historico = f"historico_{tipo}"
            if chave_historico in self.session_data:
                del self.session_data[chave_historico]
        else:
            # Limpa todos os históricos
            chaves_para_remover = [k for k in self.session_data.keys() if k.startswith('historico_')]
            for chave in chaves_para_remover:
                del self.session_data[chave]
    
    # ============================================================================
    # Utilitários
    # ============================================================================
    
    def obter_info_persistencia(self) -> Dict[str, Any]:
        """Retorna informações sobre persistência"""
        return {
            "sessao_existe": self.SESSION_FILE.exists(),
            "itens_sessao": len(self.session_data),
            "janelas_salvas": len(self.window_state),
            "tamanho_cache_mb": self.obter_tamanho_cache() / (1024 * 1024),
            "arquivos_cache": len(list(self.CACHE_DIR.glob("*.pkl"))),
            "diretorio_estado": str(self.STATE_DIR.absolute())
        }
    
    def limpar_dados_antigos(self, dias: int = 30):
        """
        Limpa dados mais antigos que X dias
        
        Args:
            dias: Número de dias
        """
        limite = datetime.now().timestamp() - (dias * 24 * 60 * 60)
        
        # Limpa cache antigo
        for cache_file in self.CACHE_DIR.glob("*.pkl"):
            if cache_file.stat().st_mtime < limite:
                cache_file.unlink()
        
        registrar_log(
            "Persistência",
            f"Dados mais antigos que {dias} dias foram removidos",
            "INFO"
        )
    
    @safe_operation(fallback_value=True, context="Criando backup de estado")
    def criar_backup_estado(self) -> bool:
        """Cria backup do estado atual"""
        backup_dir = self.STATE_DIR / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Backup da sessão
        if self.SESSION_FILE.exists():
            backup_file = backup_dir / f"session_backup_{timestamp}.json"
            import shutil
            shutil.copy2(self.SESSION_FILE, backup_file)
        
        # Backup do estado de janelas
        if self.WINDOW_STATE_FILE.exists():
            backup_file = backup_dir / f"window_state_backup_{timestamp}.json"
            import shutil
            shutil.copy2(self.WINDOW_STATE_FILE, backup_file)
        
        registrar_log(
            "Persistência",
            f"Backup de estado criado em {backup_dir}",
            "INFO"
        )
        
        # Limpa backups antigos (mantém últimos 5)
        self._limpar_backups_antigos(backup_dir, max_backups=5)
        
        return True
    
    def _limpar_backups_antigos(self, backup_dir: Path, max_backups: int = 5):
        """Remove backups antigos"""
        backups = sorted(
            backup_dir.glob("*_backup_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for backup in backups[max_backups:]:
            backup.unlink()


# Instância global singleton
persistence = PersistenceManager()


# Funções de conveniência
def salvar_estado_aplicacao(session_data: Dict[str, Any], window_states: Dict[str, Any]) -> bool:
    """Salva estado completo da aplicação"""
    sucesso_sessao = persistence.salvar_sessao(session_data)
    sucesso_janelas = persistence.salvar_estado_janelas(window_states)
    return sucesso_sessao and sucesso_janelas


def carregar_estado_aplicacao() -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Carrega estado completo da aplicação"""
    session_data = persistence.carregar_sessao()
    window_states = persistence.carregar_estado_janelas()
    return session_data, window_states


def auto_save_habilitado() -> bool:
    """Verifica se auto-save está habilitado"""
    from config.settings import get_config
    return get_config("sessao.salvar_estado_automaticamente", True)
