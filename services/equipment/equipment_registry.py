"""
Equipment Registry - Fase 1
Gerencia registro de equipamentos e suas configurações.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import unicodedata

from services.contract_catalog import get_contract_catalog
from services.path_resolver import resolve_banco_dir


logger = logging.getLogger(__name__)


@dataclass
class EquipmentConfig:
    """Configuração de um equipamento de PCR."""
    
    nome: str
    modelo: str
    fabricante: str
    tipo_placa: str  # "96", "384", etc.
    xlsx_estrutura: Dict[str, Any]  # Estrutura do XLSX
    extrator_nome: str  # Nome da função extratora
    formatador_nome: str = "padrao"  # Nome do formatador
    equipment_id: str = ""
    contract_version: str = ""
    ct_like_columns: List[str] = field(default_factory=list)
    ct_like_blocklist: List[str] = field(default_factory=list)
    source_of_truth: str = ""
    
    def __post_init__(self):
        """Validar configuração após inicialização."""
        if not self.nome:
            raise ValueError("Nome do equipamento é obrigatório")
        
        if not isinstance(self.xlsx_estrutura, dict):
            raise ValueError("xlsx_estrutura deve ser um dicionário")
        
        # Validar apenas campos essenciais (linha_inicio é obrigatório)
        if 'linha_inicio' not in self.xlsx_estrutura:
            raise ValueError("xlsx_estrutura deve conter o campo 'linha_inicio'")
        
        # Validar linha_inicio
        linha_inicio = self.xlsx_estrutura.get('linha_inicio')
        if not isinstance(linha_inicio, int) or linha_inicio < 1:
            raise ValueError(f"linha_inicio deve ser int >= 1, recebido: {linha_inicio}")
        
        # Validar que ao menos uma coluna de dados existe
        tem_coluna_dados = any(
            self.xlsx_estrutura.get(campo) is not None
            for campo in ['coluna_well', 'coluna_target', 'coluna_ct']
        )
        if not tem_coluna_dados:
            raise ValueError("xlsx_estrutura deve ter pelo menos uma coluna de dados (well/target/ct)")


class EquipmentRegistry:
    """Registro de equipamentos de PCR."""
    
    def __init__(self, caminho_csv: Optional[str] = None):
        """
        Inicializa o registry.
        
        Args:
            caminho_csv: Caminho para arquivo CSV de equipamentos
        """
        default_path = str(resolve_banco_dir() / "equipamentos.csv")
        self.caminho_csv = caminho_csv or default_path
        self._cache: Dict[str, EquipmentConfig] = {}
        self._carregado = False
        self._legacy_sources_used: set[str] = set()
    
    def load(self) -> None:
        """
        Carrega equipamentos do arquivo CSV.
        
        Formato do CSV:
            nome, modelo, fabricante, tipo_placa, xlsx_config (JSON), extrator_nome, formatador_nome
        """
        caminho = Path(self.caminho_csv)
        
        if not caminho.exists():
            logger.warning(f"Arquivo de equipamentos não encontrado: {caminho}")
            logger.info("Usando apenas padrões built-in")
            self._carregar_padroes_builtin()
            self._carregar_contratos_runtime()
            self._carregado = True
            return
        
        try:
            # Ler CSV com encoding UTF-8 sem BOM
            with open(caminho, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=',')
                
                linhas_validas = 0
                linhas_invalidas = 0
                
                for i, row in enumerate(reader, start=2):  # Linha 2 (após header)
                    try:
                        # Extrair campos
                        nome = row.get('nome', '').strip()
                        modelo = row.get('modelo', '').strip()
                        fabricante = row.get('fabricante', '').strip()
                        tipo_placa = row.get('tipo_placa', '96').strip()
                        xlsx_config_str = row.get('xlsx_config', '').strip()
                        extrator_nome = row.get('extrator_nome', 'generico').strip()
                        formatador_nome = row.get('formatador_nome', 'padrao').strip()
                        
                        if not nome:
                            logger.warning(f"Linha {i}: nome vazio, ignorando")
                            linhas_invalidas += 1
                            continue
                        
                        # Parsear JSON da configuração XLSX ou usar estrutura padrão
                        if xlsx_config_str:
                            try:
                                xlsx_estrutura = json.loads(xlsx_config_str)
                            except json.JSONDecodeError as e:
                                logger.warning(f"Linha {i}: JSON inválido em xlsx_config: {e}, usando padrão")
                                xlsx_estrutura = self._estrutura_padrao()
                        else:
                            # CSV antigo sem xlsx_config: usar estrutura padrão
                            logger.info(f"Linha {i}: xlsx_config ausente para '{nome}', usando estrutura padrão")
                            xlsx_estrutura = self._estrutura_padrao()
                        
                        # Criar configuração
                        config = EquipmentConfig(
                            nome=nome,
                            modelo=modelo,
                            fabricante=fabricante,
                            tipo_placa=tipo_placa,
                            xlsx_estrutura=xlsx_estrutura,
                            extrator_nome=extrator_nome,
                            formatador_nome=formatador_nome,
                            source_of_truth="legacy_equipment_csv",
                        )
                        
                        # Adicionar ao cache
                        chave = self._normalizar_chave(nome)
                        self._cache[chave] = config
                        self._legacy_sources_used.add("legacy_equipment_csv")
                        linhas_validas += 1
                        
                    except Exception as e:
                        logger.warning(f"Linha {i}: erro ao processar: {e}")
                        linhas_invalidas += 1
                        continue
                
                logger.info(f"Equipamentos carregados: {linhas_validas} válidos, {linhas_invalidas} inválidos")
        
        except Exception as e:
            logger.error(f"Erro ao ler arquivo CSV: {e}")
            raise
        
        # Adicionar padrões built-in (se não foram sobrescritos)
        self._carregar_padroes_builtin()
        # Contratos formais possuem precedencia sobre CSV/built-in.
        self._carregar_contratos_runtime()
        
        self._carregado = True
    
    def _estrutura_padrao(self) -> dict:
        """
        Retorna estrutura XLSX padrão para equipamentos sem configuração.
        
        Returns:
            Dicionário com estrutura padrão (compatível com Applied Biosystems 7500)
        """
        return {
            "coluna_well": 0,
            "coluna_sample": 1,
            "coluna_target": 2,
            "coluna_ct": 3,
            "linha_inicio": 5,
            "headers_esperados": ["Well", "Sample Name", "Target", "Cq"]
        }

    def _carregar_contratos_runtime(self) -> None:
        """Carrega perfis de equipamento do catalogo de contratos."""
        try:
            catalog = get_contract_catalog(reload=True)
            for profile in catalog.list_equipment_profiles().values():
                if "source_of_truth" in profile and str(profile.get("source_of_truth")).lower() != "contracts":
                    continue
                nome = str(profile.get("display_name") or profile.get("name") or "").strip()
                if not nome:
                    continue
                estrutura = {
                    "coluna_well": profile.get("coluna_well", 0),
                    "coluna_sample": profile.get("coluna_sample", 1),
                    "coluna_target": profile.get("coluna_target", 2),
                    "coluna_ct": profile.get("coluna_ct", 3),
                    "linha_inicio": profile.get("linha_inicio", 5),
                }
                column_mapping = profile.get("column_mapping")
                if isinstance(column_mapping, dict):
                    estrutura.update(
                        {
                            "well_label": column_mapping.get("well", ""),
                            "sample_label": column_mapping.get("sample", ""),
                            "target_label": column_mapping.get("target", ""),
                            "ct_label": column_mapping.get("ct", ""),
                        }
                    )
                cfg = EquipmentConfig(
                    nome=nome,
                    modelo=str(profile.get("modelo") or profile.get("display_name") or nome),
                    fabricante=str(profile.get("fabricante") or ""),
                    tipo_placa=str(profile.get("tipo_placa") or "96"),
                    xlsx_estrutura=estrutura,
                    extrator_nome=str(profile.get("extrator_nome") or "extrair_generico"),
                    formatador_nome=str(profile.get("formatador_nome") or "padrao"),
                    equipment_id=str(profile.get("equipment_id") or self._normalizar_chave(nome)),
                    contract_version=str(profile.get("contract_version", "")),
                    ct_like_columns=[
                        str(item) for item in profile.get("ct_like_columns", []) if str(item).strip()
                    ],
                    ct_like_blocklist=[
                        str(item) for item in profile.get("ct_like_blocklist", []) if str(item).strip()
                    ],
                    source_of_truth="contracts",
                )
                self._cache[self._normalizar_chave(nome)] = cfg
        except Exception as exc:
            logger.warning(f"Falha ao carregar contratos de equipamento: {exc}")
    
    def _carregar_padroes_builtin(self) -> None:
        """Carrega padrões built-in (hardcoded)."""
        padroes_builtin = [
            EquipmentConfig(
                nome="7500",
                modelo="7500 Real-Time PCR System",
                fabricante="Applied Biosystems",
                tipo_placa="96",
                xlsx_estrutura={
                    "coluna_well": 0,
                    "coluna_sample": 1,
                    "coluna_target": 2,
                    "coluna_ct": 3,
                    "linha_inicio": 5,
                    "headers_esperados": ["Well", "Sample Name", "Target", "Cq"]
                },
                extrator_nome="extrair_7500",
                source_of_truth="legacy_builtin_registry",
            ),
            EquipmentConfig(
                nome="CFX96",
                modelo="CFX96 Touch Real-Time PCR",
                fabricante="Bio-Rad",
                tipo_placa="96",
                xlsx_estrutura={
                    "coluna_well": 0,
                    "coluna_sample": 1,
                    "coluna_target": 4,
                    "coluna_ct": 5,
                    "linha_inicio": 3,
                    "headers_esperados": ["Well", "Content", "Target", "Cq"]
                },
                extrator_nome="extrair_cfx96",
                source_of_truth="legacy_builtin_registry",
            ),
            EquipmentConfig(
                nome="QuantStudio",
                modelo="QuantStudio Real-Time PCR",
                fabricante="Thermo Fisher",
                tipo_placa="96",
                xlsx_estrutura={
                    "coluna_well": 1,
                    "coluna_sample": 2,
                    "coluna_target": 3,
                    "coluna_ct": 4,
                    "linha_inicio": 8,
                    "headers_esperados": ["Well Position", "Sample Name", "Target Name", "CT"]
                },
                extrator_nome="extrair_quantstudio",
                source_of_truth="legacy_builtin_registry",
            ),
            EquipmentConfig(
                nome="7500_Extended",
                modelo="7500 Real-Time PCR System (Extended Format)",
                fabricante="Applied Biosystems",
                tipo_placa="96",
                xlsx_estrutura={
                    "coluna_well": 0,  # Coluna A
                    "coluna_sample": 1,  # Coluna B
                    "coluna_target": 2,  # Coluna C - Target Name
                    "coluna_ct": 6,  # Coluna G - Cт (valor real, não Ct Mean)
                    "linha_inicio": 9,  # Linha 9 (após metadados nas linhas 1-7)
                    "headers_esperados": ["Well", "Sample Name", "Target Name", "Cт"],
                    "keywords": ["sds7500", "7500", "Applied Biosystems"],
                    "skip_sheets": ["extração", "extracao", "extraction"]  # Ignorar abas com esses nomes
                },
                extrator_nome="extrair_7500_extended",
                source_of_truth="legacy_builtin_registry",
            ),
            EquipmentConfig(
                nome="CFX96_Export",
                modelo="CFX96 Touch Real-Time PCR (Export Format)",
                fabricante="Bio-Rad",
                tipo_placa="96",
                xlsx_estrutura={
                    "coluna_well": 0,
                    "coluna_sample": 1,
                    "coluna_target": 4,
                    "coluna_ct": 6,
                    "linha_inicio": 2,
                    "headers_esperados": ["Well", "Sample", "Target", "Cq"]
                },
                extrator_nome="extrair_cfx96_export",
                source_of_truth="legacy_builtin_registry",
            )
        ]
        
        for config in padroes_builtin:
            chave = self._normalizar_chave(config.nome)
            # Não sobrescrever se já existe no CSV
            if chave not in self._cache:
                self._cache[chave] = config
                self._legacy_sources_used.add("legacy_builtin_registry")
    
    def get(self, nome: str) -> Optional[EquipmentConfig]:
        """
        Obtém configuração de equipamento por nome.
        
        Args:
            nome: Nome do equipamento
            
        Returns:
            EquipmentConfig ou None se não encontrado
        """
        if not self._carregado:
            self.load()
        
        chave = self._normalizar_chave(nome)
        return self._cache.get(chave)
    
    def registrar_novo(self, config: EquipmentConfig) -> None:
        """
        Registra novo equipamento (apenas em memória).
        
        Args:
            config: Configuração do equipamento
            
        Raises:
            ValueError: Se configuração inválida
        """
        # Validar configuração
        if not isinstance(config, EquipmentConfig):
            raise ValueError("config deve ser instância de EquipmentConfig")
        
        # Adicionar ao cache
        chave = self._normalizar_chave(config.nome)
        self._cache[chave] = config
        
        logger.info(f"Equipamento registrado: {config.nome}")

    def list_legacy_sources_used(self) -> List[str]:
        """Lista fontes legadas usadas no carregamento, para auditoria de E07."""
        return sorted(self._legacy_sources_used)
    
    def listar_todos(self) -> List[EquipmentConfig]:
        """
        Lista todas as configurações carregadas.
        
        Returns:
            Lista de EquipmentConfig
        """
        if not self._carregado:
            self.load()
        
        return list(self._cache.values())
    
    def listar_equipamentos(self) -> List[str]:
        """
        Lista apenas os nomes dos equipamentos disponíveis.
        
        Returns:
            Lista de strings com nomes dos equipamentos
        """
        if not self._carregado:
            self.load()
        
        return sorted([config.nome for config in self._cache.values()])
    
    def _normalizar_chave(self, nome: str) -> str:
        """
        Normaliza nome para usar como chave (case-insensitive, sem acentos).
        
        Args:
            nome: Nome original
            
        Returns:
            Nome normalizado
        """
        # Remover acentos
        sem_acentos = ''.join(
            c for c in unicodedata.normalize('NFD', nome)
            if unicodedata.category(c) != 'Mn'
        )
        
        # Lowercase e remover espaços extras
        normalizado = sem_acentos.lower().strip()
        normalizado = '_'.join(normalizado.split())
        
        return normalizado


# Instância global (singleton)
_registry_instance: Optional[EquipmentRegistry] = None


def get_registry() -> EquipmentRegistry:
    """Obtém instância global do registry."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = EquipmentRegistry()
        _registry_instance.load()
    return _registry_instance


# API pública
__all__ = [
    'EquipmentConfig',
    'EquipmentRegistry',
    'get_registry'
]
