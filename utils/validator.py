"""
Validator - Sistema de Validação de Inputs
Fornece validadores comuns para garantir integridade dos dados
"""

import os
import re
from pathlib import Path
from datetime import datetime, date
from typing import Any, List, Optional, Union
import pandas as pd


class Validator:
    """Classe com métodos estáticos para validação de dados"""
    
    # === VALIDAÇÃO DE ARQUIVOS ===
    
    @staticmethod
    def arquivo_existe(filepath: str) -> bool:
        """
        Verifica se arquivo existe
        
        Args:
            filepath: Caminho do arquivo
            
        Returns:
            True se existe, False caso contrário
        """
        return os.path.isfile(filepath)
    
    @staticmethod
    def diretorio_existe(dirpath: str) -> bool:
        """
        Verifica se diretório existe
        
        Args:
            dirpath: Caminho do diretório
            
        Returns:
            True se existe, False caso contrário
        """
        return os.path.isdir(dirpath)
    
    @staticmethod
    def pode_escrever(filepath: str) -> bool:
        """
        Verifica se pode escrever no arquivo/diretório
        
        Args:
            filepath: Caminho do arquivo
            
        Returns:
            True se tem permissão, False caso contrário
        """
        # Se arquivo existe, verificar permissão de escrita
        if os.path.exists(filepath):
            return os.access(filepath, os.W_OK)
        
        # Se não existe, verificar permissão no diretório pai
        parent_dir = os.path.dirname(filepath) or '.'
        return os.access(parent_dir, os.W_OK)
    
    @staticmethod
    def tem_espaco_disco(filepath: str, tamanho_mb: float = 10) -> bool:
        """
        Verifica se há espaço em disco suficiente
        
        Args:
            filepath: Caminho onde será escrito
            tamanho_mb: Tamanho necessário em MB
            
        Returns:
            True se há espaço, False caso contrário
        """
        try:
            import shutil
            stats = shutil.disk_usage(os.path.dirname(filepath) or '.')
            espaco_livre_mb = stats.free / (1024 * 1024)
            return espaco_livre_mb >= tamanho_mb
        except Exception:
            return True  # Assumir que tem espaço se não conseguir verificar
    
    @staticmethod
    def extensao_valida(filepath: str, extensoes: List[str]) -> bool:
        """
        Verifica se arquivo tem extensão válida
        
        Args:
            filepath: Caminho do arquivo
            extensoes: Lista de extensões permitidas (ex: ['.csv', '.xlsx'])
            
        Returns:
            True se extensão é válida, False caso contrário
        """
        ext = Path(filepath).suffix.lower()
        extensoes_lower = [e.lower() if e.startswith('.') else f'.{e}'.lower() 
                          for e in extensoes]
        return ext in extensoes_lower
    
    # === VALIDAÇÃO DE DADOS ===
    
    @staticmethod
    def dataframe_valido(df: pd.DataFrame, colunas_obrigatorias: List[str] = None) -> bool:
        """
        Verifica se DataFrame é válido
        
        Args:
            df: DataFrame a validar
            colunas_obrigatorias: Lista de colunas que devem existir
            
        Returns:
            True se válido, False caso contrário
        """
        if df is None or not isinstance(df, pd.DataFrame):
            return False
        
        if df.empty:
            return False
        
        if colunas_obrigatorias:
            for col in colunas_obrigatorias:
                if col not in df.columns:
                    return False
        
        return True
    
    @staticmethod
    def lista_nao_vazia(lista: List[Any]) -> bool:
        """
        Verifica se lista não está vazia
        
        Args:
            lista: Lista a validar
            
        Returns:
            True se não vazia, False caso contrário
        """
        return lista is not None and isinstance(lista, list) and len(lista) > 0
    
    @staticmethod
    def string_nao_vazia(texto: str) -> bool:
        """
        Verifica se string não está vazia
        
        Args:
            texto: String a validar
            
        Returns:
            True se não vazia, False caso contrário
        """
        return texto is not None and isinstance(texto, str) and texto.strip() != ''
    
    # === VALIDAÇÃO DE DATAS ===
    
    @staticmethod
    def data_valida(data: Any) -> bool:
        """
        Verifica se data é válida
        
        Args:
            data: Objeto de data (datetime, date, ou string)
            
        Returns:
            True se válida, False caso contrário
        """
        if isinstance(data, (datetime, date)):
            return True
        
        if isinstance(data, str):
            # Tentar parsear string
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y']:
                try:
                    datetime.strptime(data, fmt)
                    return True
                except ValueError:
                    continue
        
        return False
    
    @staticmethod
    def periodo_valido(data_inicio: Any, data_fim: Any) -> bool:
        """
        Verifica se período é válido (início antes do fim)
        
        Args:
            data_inicio: Data de início
            data_fim: Data de fim
            
        Returns:
            True se válido, False caso contrário
        """
        if not Validator.data_valida(data_inicio) or not Validator.data_valida(data_fim):
            return False
        
        # Converter para datetime se necessário
        if isinstance(data_inicio, str):
            data_inicio = Validator.parsear_data(data_inicio)
        if isinstance(data_fim, str):
            data_fim = Validator.parsear_data(data_fim)
        
        return data_inicio <= data_fim
    
    @staticmethod
    def parsear_data(data_str: str) -> Optional[datetime]:
        """
        Converte string para datetime
        
        Args:
            data_str: String de data
            
        Returns:
            datetime ou None se falhar
        """
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y']:
            try:
                return datetime.strptime(data_str, fmt)
            except ValueError:
                continue
        return None
    
    # === VALIDAÇÃO DE VALORES NUMÉRICOS ===
    
    @staticmethod
    def numero_valido(valor: Any, min_val: float = None, max_val: float = None) -> bool:
        """
        Verifica se valor é número válido dentro de range
        
        Args:
            valor: Valor a validar
            min_val: Valor mínimo (opcional)
            max_val: Valor máximo (opcional)
            
        Returns:
            True se válido, False caso contrário
        """
        try:
            num = float(valor)
            
            if min_val is not None and num < min_val:
                return False
            
            if max_val is not None and num > max_val:
                return False
            
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def ct_valido(ct_value: Any) -> bool:
        """
        Verifica se valor de CT é válido
        
        Args:
            ct_value: Valor de CT
            
        Returns:
            True se válido, False caso contrário
        """
        # CT deve ser número entre 0 e 50
        return Validator.numero_valido(ct_value, min_val=0, max_val=50)
    
    # === VALIDAÇÃO DE STRINGS ===
    
    @staticmethod
    def email_valido(email: str) -> bool:
        """
        Verifica se email é válido
        
        Args:
            email: String de email
            
        Returns:
            True se válido, False caso contrário
        """
        if not Validator.string_nao_vazia(email):
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def sanitizar_string(texto: str, permitir_espacos: bool = True) -> str:
        """
        Remove caracteres especiais de string
        
        Args:
            texto: String a sanitizar
            permitir_espacos: Se deve manter espaços
            
        Returns:
            String sanitizada
        """
        if not isinstance(texto, str):
            return ""
        
        # Remover caracteres especiais
        if permitir_espacos:
            pattern = r'[^a-zA-Z0-9\s_-]'
        else:
            pattern = r'[^a-zA-Z0-9_-]'
        
        return re.sub(pattern, '', texto)
    
    # === VALIDAÇÃO DE CSV ===
    
    @staticmethod
    def csv_valido(filepath: str, separador: str = ';') -> bool:
        """
        Verifica se CSV é válido e pode ser lido
        
        Args:
            filepath: Caminho do CSV
            separador: Separador usado no CSV
            
        Returns:
            True se válido, False caso contrário
        """
        if not Validator.arquivo_existe(filepath):
            return False
        
        if not Validator.extensao_valida(filepath, ['.csv']):
            return False
        
        try:
            # Tentar ler primeiras linhas
            df = pd.read_csv(filepath, sep=separador, nrows=5)
            return len(df.columns) > 0
        except Exception:
            return False
    
    @staticmethod
    def excel_valido(filepath: str) -> bool:
        """
        Verifica se arquivo Excel é válido
        
        Args:
            filepath: Caminho do Excel
            
        Returns:
            True se válido, False caso contrário
        """
        if not Validator.arquivo_existe(filepath):
            return False
        
        if not Validator.extensao_valida(filepath, ['.xlsx', '.xls']):
            return False
        
        try:
            # Tentar ler primeiras linhas
            df = pd.read_excel(filepath, nrows=5)
            return len(df.columns) > 0
        except Exception:
            return False


# Funções de conveniência
def validar_arquivo_existe(filepath: str, tipo: str = "arquivo") -> None:
    """
    Valida se arquivo existe, lança exceção se não
    
    Args:
        filepath: Caminho do arquivo
        tipo: Tipo de arquivo para mensagem de erro
        
    Raises:
        FileNotFoundError: Se arquivo não existe
    """
    if not Validator.arquivo_existe(filepath):
        raise FileNotFoundError(f"{tipo.capitalize()} não encontrado: {filepath}")


def validar_permissao_escrita(filepath: str) -> None:
    """
    Valida permissão de escrita, lança exceção se não tem
    
    Args:
        filepath: Caminho do arquivo
        
    Raises:
        PermissionError: Se não tem permissão
    """
    if not Validator.pode_escrever(filepath):
        raise PermissionError(f"Sem permissão para escrever em: {filepath}")


def validar_dataframe(df: pd.DataFrame, colunas: List[str] = None) -> None:
    """
    Valida DataFrame, lança exceção se inválido
    
    Args:
        df: DataFrame a validar
        colunas: Colunas obrigatórias
        
    Raises:
        ValueError: Se DataFrame inválido
    """
    if not Validator.dataframe_valido(df, colunas):
        msg = "DataFrame inválido"
        if colunas:
            msg += f". Colunas obrigatórias: {', '.join(colunas)}"
        raise ValueError(msg)
