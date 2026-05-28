"""
Sistema de Feature Flags para Integragal

Permite gerenciar rollout gradual de features em produção.
Refatoração #4 - Fase 5
"""

from typing import Dict, Any, List, Optional
import logging
from pathlib import Path
import json


class FeatureFlags:
    """
    Gerenciador de feature flags com suporte a rollout gradual.
    
    Permite ativar/desativar features em runtime sem necessidade de deploy,
    com capacidade de rollout percentual e controle fino por usuário.
    """
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Inicializa sistema de feature flags.
        
        Args:
            config_file: Caminho para arquivo JSON de configuração (opcional)
        """
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file
        
        # Configuração padrão
        self._flags: Dict[str, Dict[str, Any]] = {
            'USE_ANALISAR_CORRIDA_V2': {
                'enabled': True,
                'rollout_percentage': 100,
                'force_users': [],
                'exclude_users': [],
                'description': 'Usar metodo refatorado analisar_corrida_v2 (ativado C.1)',
                'created_at': '2026-01-31',
                'owner': 'team-dev'
            },
            'USE_CONTRACT_PARSER_ROUTING': {
                'enabled': False,
                'rollout_percentage': 0,
                'force_users': [],
                'exclude_users': [],
                'description': 'Ativa roteamento de parser por contrato (faseada)',
                'created_at': '2026-03-03',
                'owner': 'team-dev'
            },
            'USE_CONTRACT_ANALYSIS_RUNTIME': {
                'enabled': False,
                'rollout_percentage': 0,
                'force_users': [],
                'exclude_users': [],
                'description': 'Ativa runtime de analise por contrato (faseada)',
                'created_at': '2026-03-03',
                'owner': 'team-dev'
            },
            'USE_GAL_LEGACY_PANEL_CSV': {
                'enabled': False,
                'rollout_percentage': 0,
                'force_users': [],
                'exclude_users': [],
                'description': 'Permite writer legado painel_*_exame.csv (rollback)',
                'created_at': '2026-03-03',
                'owner': 'team-dev'
            },
            'USE_GAL_LEGACY_SUCCESS_LEDGER': {
                'enabled': False,
                'rollout_percentage': 0,
                'force_users': [],
                'exclude_users': [],
                'description': 'Permite escrita do ledger legado gal_transacoes_sucesso.csv',
                'created_at': '2026-03-08',
                'owner': 'team-dev'
            },
            'USE_CONTRACTUAL_CSV_LEGACY_FALLBACK': {
                'enabled': False,
                'rollout_percentage': 0,
                'force_users': [],
                'exclude_users': [],
                'description': 'Permite fallback permissivo para leitura de CSV contratual legado',
                'created_at': '2026-03-08',
                'owner': 'team-dev'
            },
            'USE_EXAM_RUNS_CSV_WRITER': {
                'enabled': True,
                'rollout_percentage': 100,
                'force_users': [],
                'exclude_users': [],
                'description': 'Ativa writer contratual corridas_<slug_exame>.csv (rollback por flag)',
                'created_at': '2026-03-03',
                'owner': 'team-dev'
            },
            'USE_EXAM_RUNS_SQLITE_FIRST': {
                'enabled': True,
                'rollout_percentage': 100,
                'force_users': [],
                'exclude_users': [],
                'description': 'Ativa persistencia SQLite-first para historico por exame com fallback CSV',
                'created_at': '2026-03-04',
                'owner': 'team-dev'
            },
            'USE_PLATE_SYNC_USE_CASE': {
                'enabled': True,
                'rollout_percentage': 100,
                'force_users': [],
                'exclude_users': [],
                'description': 'Ativa sync_plate_to_analysis extraido da UI com rollback por flag',
                'created_at': '2026-03-09',
                'owner': 'team-dev'
            },
            'USE_GAL_LOGIN_HARDENED': {
                'enabled': False,
                'rollout_percentage': 0,
                'force_users': [],
                'exclude_users': [],
                'description': 'Ativa login GAL endurecido com fallback legado por flag para rollback imediato',
                'created_at': '2026-03-09',
                'owner': 'team-dev'
            },
            'USE_OPERATIONAL_TABULAR_VIEWER': {
                'enabled': False,
                'rollout_percentage': 0,
                'force_users': [],
                'exclude_users': [],
                'description': 'Ativa visualizador tabular operacional na rota Historico com fallback legado',
                'created_at': '2026-03-12',
                'owner': 'team-dev'
            },
            'USE_EXAM_CREATOR_REGISTRY_SAVE': {
                'enabled': False,
                'rollout_percentage': 0,
                'force_users': [],
                'exclude_users': [],
                'description': 'Ativa persistencia do wizard de exame via RegistryExamEditor com rollback legado',
                'created_at': '2026-03-26',
                'owner': 'team-dev'
            },
            'USE_ANALYSIS_EXAMS_REGISTRY_READ': {
                'enabled': True,
                'rollout_percentage': 100,
                'force_users': [],
                'exclude_users': [],
                'description': 'Ativa leitura canonica de exames via ExamRegistry (ativado C.2)',
                'created_at': '2026-03-26',
                'owner': 'team-dev'
            },
            'USE_ANALYSIS_RUNTIME_REGISTRY_RULES': {
                'enabled': True,
                'rollout_percentage': 100,
                'force_users': [],
                'exclude_users': [],
                'description': 'Ativa consumo canonico de regras/limiares via ExamRegistry V2 (ativado C.2)',
                'created_at': '2026-03-26',
                'owner': 'team-dev'
            },
            'USE_ANALYSIS_RUNTIME_PROMOTION_GATE_ENFORCEMENT': {
                'enabled': False,
                'rollout_percentage': 0,
                'force_users': [],
                'exclude_users': [],
                'description': 'Ativa enforce de promocao do runtime canonico somente com gate operacional aprovado',
                'created_at': '2026-03-26',
                'owner': 'team-dev'
            },
            'USE_ANALYSIS_RUNTIME_STAGED_ROLLOUT': {
                'enabled': False,
                'rollout_percentage': 0,
                'force_users': [],
                'exclude_users': [],
                'description': 'Ativa rollout canario por estagios (10/25/50/100) para reduzir fallback legado de forma progressiva',
                'created_at': '2026-03-26',
                'owner': 'team-dev'
            },
            'USE_MENU_ANALYSIS_LEGACY_COMPAT': {
                'enabled': True,
                'rollout_percentage': 100,
                'force_users': [],
                'exclude_users': [],
                'description': 'Mantem fallback legado de catalogo no menu; canario OFF governado por arquivo operacional/env',
                'created_at': '2026-03-27',
                'owner': 'team-dev'
            },
        }
        
        # Carregar configuração de arquivo se existir
        if config_file and config_file.exists():
            self._load_from_file()
    
    def is_enabled(
        self, 
        flag_name: str, 
        user_id: Optional[str] = None
    ) -> bool:
        """
        Verifica se feature flag está habilitada para um usuário.
        
        Lógica de decisão:
        1. Se flag não existe â†’ False
        2. Se user_id em force_users â†’ True (sempre)
        3. Se user_id em exclude_users â†’ False (nunca)
        4. Se enabled=False â†’ False (desabilitada globalmente)
        5. Se rollout_percentage >= 100 â†’ True (100% rollout)
        6. Senão â†’ Baseado em hash determinístico do user_id
        
        Args:
            flag_name: Nome da feature flag
            user_id: ID do usuário (opcional, para rollout percentual)
            
        Returns:
            bool: True se feature habilitada, False caso contrário
        """
        if flag_name not in self._flags:
            self.logger.warning(f"Feature flag '{flag_name}' não existe")
            return False
        
        flag = self._flags[flag_name]
        
        # 1. Usuários forçados (sempre v2)
        if user_id and user_id in flag.get('force_users', []):
            self.logger.info(
                f"âœ… Feature {flag_name} FORÇADA para user {user_id}"
            )
            return True
        
        # 2. Usuários excluídos (sempre v1)
        if user_id and user_id in flag.get('exclude_users', []):
            self.logger.info(
                f"âŒ Feature {flag_name} EXCLUÃDA para user {user_id}"
            )
            return False
        
        # 3. Flag desabilitada globalmente
        if not flag.get('enabled', False):
            self.logger.debug(f"Feature {flag_name} desabilitada globalmente")
            return False
        
        # 4. Rollout 100%
        rollout = flag.get('rollout_percentage', 0)
        if rollout >= 100:
            self.logger.debug(f"Feature {flag_name} em 100% rollout")
            return True
        
        # 5. Rollout parcial (determinístico baseado em user_id)
        if user_id:
            # Hash determinístico usando SHA256
            # Garante que o mesmo user_id sempre caia no mesmo bucket (0-99)
            # independente de restarts do servidor/código
            import hashlib
            
            # Salt opcional para variar distribuição por flag se necessário
            # (aqui usando apenas o nome da flag como sal)
            hash_input = f"{user_id}:{flag_name}".encode('utf-8')
            hash_hex = hashlib.sha256(hash_input).hexdigest()
            
            # Pega os primeiros 8 caracteres e converte para int
            # Modulo 100 para ter 0-99
            hash_val = int(hash_hex[:8], 16) % 100
            
            enabled = hash_val < rollout
            
            self.logger.debug(
                f"Feature {flag_name} para user {user_id}: "
                f"hash={hash_val}, rollout={rollout}%, enabled={enabled}"
            )
            return enabled
        
        # 6. Sem user_id e rollout < 100%: não habilitar
        self.logger.debug(
            f"Feature {flag_name}: sem user_id, rollout {rollout}% - não habilitado"
        )
        return False
    
    def get_flag_status(self, flag_name: str) -> Dict[str, Any]:
        """
        Retorna status completo de uma feature flag.
        
        Args:
            flag_name: Nome da flag
            
        Returns:
            Dicionário com configuração completa da flag
        """
        return self._flags.get(flag_name, {})
    
    def list_all_flags(self) -> Dict[str, Dict[str, Any]]:
        """Retorna todas as flags e seus status"""
        return self._flags.copy()
    
    def set_rollout_percentage(self, flag_name: str, percentage: int):
        """
        Atualiza percentual de rollout.
        
        Args:
            flag_name: Nome da flag
            percentage: Percentual 0-100
        """
        if flag_name not in self._flags:
            self.logger.error(f"Flag '{flag_name}' não existe")
            return
        
        # Garantir valor entre 0-100
        percentage = max(0, min(100, percentage))
        self._flags[flag_name]['rollout_percentage'] = percentage
        
        self.logger.info(f"ðŸ“Š Rollout {flag_name} â†’ {percentage}%")
        self._save_to_file()
    
    def enable_flag(self, flag_name: str):
        """Habilita flag globalmente (ainda respeita rollout_percentage)"""
        if flag_name not in self._flags:
            self.logger.error(f"Flag '{flag_name}' não existe")
            return
        
        self._flags[flag_name]['enabled'] = True
        self.logger.info(f"âœ… Flag {flag_name} HABILITADA")
        self._save_to_file()
    
    def disable_flag(self, flag_name: str):
        """Desabilita flag globalmente (rollback completo)"""
        if flag_name not in self._flags:
            self.logger.error(f"Flag '{flag_name}' não existe")
            return
        
        self._flags[flag_name]['enabled'] = False
        self.logger.warning(f"ðŸš¨ Flag {flag_name} DESABILITADA (ROLLBACK)")
        self._save_to_file()
    
    def add_force_user(self, flag_name: str, user_id: str):
        """Adiciona usuário Ã  lista de forçados (sempre v2)"""
        if flag_name not in self._flags:
            return
        
        if user_id not in self._flags[flag_name]['force_users']:
            self._flags[flag_name]['force_users'].append(user_id)
            self.logger.info(f"âž• User {user_id} adicionado a force_users de {flag_name}")
            self._save_to_file()
    
    def remove_force_user(self, flag_name: str, user_id: str):
        """Remove usuário da lista de forçados"""
        if flag_name not in self._flags:
            return
        
        if user_id in self._flags[flag_name]['force_users']:
            self._flags[flag_name]['force_users'].remove(user_id)
            self.logger.info(f"âž– User {user_id} removido de force_users de {flag_name}")
            self._save_to_file()
    
    def _load_from_file(self):
        """Carrega configuração de arquivo JSON"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_flags = json.load(f)
                self._flags.update(loaded_flags)
                self.logger.info(f"ðŸ“‚ Configuração carregada de {self.config_file}")
        except Exception as e:
            self.logger.error(f"âŒ Erro ao carregar config: {e}")
    
    def _save_to_file(self):
        """Salva configuração atual em arquivo JSON"""
        if not self.config_file:
            return
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._flags, f, indent=2, ensure_ascii=False)
                self.logger.debug(f"ðŸ’¾ Configuração salva em {self.config_file}")
        except Exception as e:
            self.logger.error(f"âŒ Erro ao salvar config: {e}")


# Instância global (singleton)
_feature_flags_instance: Optional[FeatureFlags] = None


def get_feature_flags() -> FeatureFlags:
    """
    Retorna instância singleton de FeatureFlags.
    
    Carrega configuração de arquivo se existir.
    """
    global _feature_flags_instance
    
    if _feature_flags_instance is None:
        config_path = Path(__file__).parent / 'feature_flags.json'
        _feature_flags_instance = FeatureFlags(config_file=config_path)
    
    return _feature_flags_instance


# Atalho para uso direto
feature_flags = get_feature_flags()

