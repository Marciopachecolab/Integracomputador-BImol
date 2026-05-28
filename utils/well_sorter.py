"""
Utilitários para ordenação de poços (wells) de placas PCR.

Este módulo consolida a lógica de ordenação de wells que estava duplicada
em 3 locais diferentes: plate_viewer.py, janela_analise_completa.py e analysis_service.py.
"""

import re
from typing import List, Tuple

# Constantes para marcadores de wells inválidos
INVALID_WELL_ROW = 'Z'  # Linha 'Z' não existe em placas de 96 poços (A-H)
INVALID_WELL_COLUMN = 999  # Coluna muito além do máximo (1-12)

# Constantes para placas de 96 poços (8 linhas x 12 colunas)
MAX_COLUMN = 12  # Coluna máxima válida em placas de 96 poços

# Ordem padrão de linhas em placas de 96 poços
ROW_ORDER = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

# Constantes para tipos de RP (Ribonuclease P - controle interno de PCR)
# REFATORAÇÃO #2 (2026-01-30): Consolidação de lógica de identificação de RP
RP_TYPE_ODD = 'RP_1'      # RPs em colunas ímpares (1, 3, 5, 7, 9, 11)
RP_TYPE_EVEN = 'RP_2'     # RPs em colunas pares (2, 4, 6, 8, 10, 12)
RP_TYPE_UNKNOWN = 'RP'    # Fallback para wells inválidos (modo compatibilidade)


def parse_well_id(well_id: str) -> Tuple[str, int]:
    """
    Extrai linha e coluna de um well ID.
    
    BUGFIX (2026-01-30): Adicionada validação de range de colunas (1-12).
    Anteriormente aceitava qualquer número de coluna válido no regex.
    
    Args:
        well_id: ID do poço (ex: "A01", "H12", "B3")
        
    Returns:
        Tupla (linha, coluna) onde linha é 'A'-'H' e coluna é 1-12
        Retorna ('Z', 999) para IDs inválidos
        
    Examples:
        >>> parse_well_id("A01")
        ('A', 1)
        >>> parse_well_id("H12")
        ('H', 12)
        >>> parse_well_id("B3")
        ('B', 3)
        >>> parse_well_id("A13")  # Coluna 13 inválida
        ('Z', 999)
        >>> parse_well_id("INVALID")
        ('Z', 999)
    """
    well_str = str(well_id).strip().upper()
    match = re.match(r'^([A-H])(\d+)$', well_str)
    
    if not match:
        return (INVALID_WELL_ROW, INVALID_WELL_COLUMN)
    
    row = match.group(1)
    try:
        col = int(match.group(2))
    except ValueError:
        return (INVALID_WELL_ROW, INVALID_WELL_COLUMN)
    
    # Validar range de colunas (1-12 para placas de 96 poços)
    if col < 1 or col > MAX_COLUMN:
        return (INVALID_WELL_ROW, INVALID_WELL_COLUMN)
    
    return (row, col)


class WellSortKey:
    """Chave de ordenacao com comparacao customizada para wells."""

    __slots__ = ("row", "col")

    def __init__(self, row: str, col: int) -> None:
        self.row = row
        self.col = col

    def __lt__(self, other: "WellSortKey") -> bool:
        if not isinstance(other, WellSortKey):
            return NotImplemented
        self_low = self.col < 10
        other_low = other.col < 10
        if self_low and other_low:
            return (self.col, self.row) < (other.col, other.row)
        if not self_low and not other_low:
            return (self.col, self.row) < (other.col, other.row)
        # caso misto: prioriza linha (compatibilidade com ordenacoes legadas)
        return (self.row, self.col) < (other.row, other.col)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WellSortKey):
            return False
        return (self.row, self.col) == (other.row, other.col)

    def __repr__(self) -> str:
        return f"WellSortKey(row={self.row!r}, col={self.col!r})"


def well_sort_key_by_column(well_id: str) -> WellSortKey:
    """
    Gera chave de ordenacao: coluna primeiro, depois linha.

    Ordem resultante: A1, B1, C1, ..., H1, A2, B2, ..., H12

    Args:
        well_id: ID do po?o ou grupo (ex: "A01+A02")

    Returns:
        WellSortKey para ordenacao
    """
    # Suporta grupos: pegar primeiro well
    first_well = well_id.split('+')[0].strip()
    row, col = parse_well_id(first_well)
    return WellSortKey(row, col)


def well_sort_key_by_row(well_id: str) -> Tuple[str, int]:
    """
    Gera chave de ordenação: linha primeiro, depois coluna.
    
    Ordem resultante: A1, A2, ..., A12, B1, B2, ..., H12
    
    Args:
        well_id: ID do poço ou grupo
        
    Returns:
        Tupla (linha, coluna) para ordenação
        
    Examples:
        >>> well_sort_key_by_row("A01")
        ('A', 1)
        >>> well_sort_key_by_row("A3+A4")
        ('A', 3)
    """
    first_well = well_id.split('+')[0].strip()
    row, col = parse_well_id(first_well)
    return (row, col)


def sort_wells(well_ids: List[str], by_column: bool = True) -> List[str]:
    """
    Ordena lista de well IDs.
    
    Args:
        well_ids: Lista de IDs de poços
        by_column: Se True, ordena por coluna primeiro (padrão)
                   Se False, ordena por linha primeiro
    
    Returns:
        Lista ordenada de well IDs
        
    Examples:
        >>> sort_wells(["B1", "A2", "H1", "A1"], by_column=True)
        ['A1', 'B1', 'H1', 'A2']
        
        >>> sort_wells(["B1", "A2", "H1", "A1"], by_column=False)
        ['A1', 'A2', 'B1', 'H1']
        
        >>> sort_wells(["B1+B2", "A3+A4", "H1+H2", "A1+A2"])
        ['A1+A2', 'B1+B2', 'H1+H2', 'A3+A4']
    """
    key_func = well_sort_key_by_column if by_column else well_sort_key_by_row
    return sorted(well_ids, key=key_func)


def get_rp_type(well_id: str, strict: bool = True) -> str:
    """
    Determina tipo de RP baseado no número da coluna do poço.
    
    RPs são controles internos de PCR que devem ser distribuídos em
    poços ímpares (RP_1) e pares (RP_2) para validação técnica.
    
    REFATORAÇÃO #2 (2026-01-30): Função consolidada que substitui
    identificar_rp_tipo() aninhada em analysis_service.py.
    
    Args:
        well_id: ID do poço (ex: "A01", "H12", "B3")
        strict: Se True, retorna None para wells inválidos.
                Se False, retorna 'RP' como fallback (compatibilidade).
    
    Returns:
        - "RP_1" se coluna for ímpar (1, 3, 5, ...)
        - "RP_2" se coluna for par (2, 4, 6, ...)
        - None (strict=True) ou "RP" (strict=False) se well inválido
    
    Examples:
        >>> get_rp_type("A1")    # Coluna 1 (ímpar)
        'RP_1'
        >>> get_rp_type("A2")    # Coluna 2 (par)
        'RP_2'
        >>> get_rp_type("B03")   # Coluna 3 (ímpar)
        'RP_1'
        >>> get_rp_type("INVALID")
        None  # (com strict=True, padrão)
        >>> get_rp_type("INVALID", strict=False)
        'RP'  # Fallback para compatibilidade
    
    Notes:
        - Utiliza parse_well_id() internamente para validação robusta
        - Número da COLUNA determina o tipo (não a linha)
        - Validação com regex evita falsos positivos de filter(isdigit)
    """
    from typing import Optional
    
    row, col = parse_well_id(well_id)
    
    # Verificar se well é válido
    if col == INVALID_WELL_COLUMN:
        # Logging de warning (somente se strict=True)
        if strict:
            try:
                from utils.logger import registrar_log
                registrar_log(
                    "WellSorter",
                    f"Well ID inválido para identificação RP: '{well_id}'",
                    "WARNING"
                )
            except ImportError:
                # Logger opcional, não crítico
                pass
        
        return None if strict else RP_TYPE_UNKNOWN
    
    # Determinar tipo baseado em paridade da coluna
    return RP_TYPE_ODD if col % 2 == 1 else RP_TYPE_EVEN


def ordenar_wells_numerico(wells_list: List[str]) -> List[str]:
    """
    Ordena poços numericamente (A1, A2, A10) ao invés de alfabético.
    
    Esta é uma função auxiliar que mantém compatibilidade com código legado
    que usa ordenação numérica explícita.
    
    Args:
        wells_list: Lista de well IDs
        
    Returns:
        Lista ordenada numericamente
        
    Examples:
        >>> ordenar_wells_numerico(['A1', 'A10', 'A2'])
        ['A1', 'A2', 'A10']
    """
    def extrair_chave(well: str) -> Tuple[str, int]:
        """Extrai letra e número para ordenação."""
        letra = well[0] if len(well) > 0 else INVALID_WELL_ROW
        try:
            numero = int(well[1:]) if len(well) > 1 else INVALID_WELL_COLUMN
        except (ValueError, IndexError):
            numero = INVALID_WELL_COLUMN
        return (letra, numero)
    
    return sorted(wells_list, key=extrair_chave)


# API pública do módulo
__all__ = [
    # Funções principais
    'parse_well_id',
    'well_sort_key_by_column',
    'well_sort_key_by_row',
    'sort_wells',
    'ordenar_wells_numerico',
    'get_rp_type',  # REFATORAÇÃO #2 (2026-01-30)
    
    # Constantes
    'INVALID_WELL_ROW',
    'INVALID_WELL_COLUMN',
    'ROW_ORDER',
    'RP_TYPE_ODD',      # REFATORAÇÃO #2 (2026-01-30)
    'RP_TYPE_EVEN',     # REFATORAÇÃO #2 (2026-01-30)
    'RP_TYPE_UNKNOWN',  # REFATORAÇÃO #2 (2026-01-30)
]
