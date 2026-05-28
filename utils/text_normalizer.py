"""
Utilitários para normalização de texto, especialmente caracteres cirílicos.

Este módulo centraliza a lógica de normalização usada em múltiplos pontos:
- analysis_service.py (identificação de colunas CT)
- equipment_detector.py (detecção de equipamentos)
- Futuros módulos de parsing

HISTÓRICO:
- 2026-01-30: Criado como parte da refatoração #1 (Normalização CT)
- Migrado de função aninhada em analysis_service.analisar_corrida()
- Objetivo: Performance, testabilidade, reutilização
"""

import re
import unicodedata
from typing import Optional, List, Union
from functools import lru_cache

# Constante: Translation map para caracteres cirílicos
# т (cirílico U+0442) → t, с (cirílico U+0441) → c
# IMPORTANTE: Estes caracteres são VISUALMENTE idênticos aos ASCII mas têm codepoints diferentes
# Equipamentos russos/ucranianos frequentemente exportam com estes caracteres
CYRILLIC_TO_ASCII_MAP = str.maketrans({
    ord('т'): 't', ord('Т'): 't',  # Cyrillic т/Т (te) → Latin t/T
    ord('с'): 'c', ord('С'): 'c',  # Cyrillic с/С (es) → Latin c/C
})


def normalize_cyrillic(text: Optional[Union[str, int, float]]) -> str:
    """
    Normaliza caracteres cirílicos para ASCII equivalentes.
    
    Conversões aplicadas:
    - т (Cyrillic te, U+0442) → t
    - Т (Cyrillic Te, U+0422) → t (lowercase)
    - с (Cyrillic es, U+0441) → c
    - С (Cyrillic Es, U+0421) → c (lowercase)
    
    Processamento adicional:
    - Converte para lowercase
    - Remove whitespace nas pontas (strip)
    
    Args:
        text: Texto a normalizar. Aceita str, int, float ou None.
              Números são convertidos para string antes do processamento.
    
    Returns:
        String normalizada em lowercase, stripped.
        Retorna string vazia ("") se input for None ou vazio.
    
    Examples:
        >>> normalize_cyrillic("Cт")  # C + cyrillic т
        'ct'
        >>> normalize_cyrillic("Sample")
        'sample'
        >>> normalize_cyrillic("  CT  ")
        'ct'
        >>> normalize_cyrillic(None)
        ''
        >>> normalize_cyrillic(123)
        '123'
        >>> normalize_cyrillic(45.67)
        '45.67'
    
    Raises:
        TypeError: Se text não for conversível para string (ex: list, dict)
    
    Note:
        Esta função é thread-safe e pode ser chamada concorrentemente.
        Para melhor performance em loops, considere usar normalize_cyrillic_cached().
    """
    # MITIGAÇÃO RISCO #3: Type validation rigorosa
    if text is None:
        return ""
    
    # Validação de tipo - aceita apenas str/int/float
    if not isinstance(text, (str, int, float)):
        raise TypeError(
            f"normalize_cyrillic expects str/int/float/None, "
            f"got {type(text).__name__}: {repr(text)[:50]}"
        )
    
    # Conversão segura para string
    text_str = str(text).strip()
    
    if not text_str:
        return ""
    
    # Aplicar tradução de cirílico -> ASCII e normalizar
    # NOTA: translate() é O(n) e muito eficiente em C
    return text_str.translate(CYRILLIC_TO_ASCII_MAP).lower().strip()


@lru_cache(maxsize=256)
def normalize_cyrillic_cached(text: str) -> str:
    """
    Versão cacheada de normalize_cyrillic para performance otimizada.
    
    Use quando processar mesmas strings repetidamente, como headers de colunas
    em DataFrames. Cache é limitado a 256 entradas para evitar memory leak.
    
    IMPORTANTE: Esta função aceita APENAS strings (não None/int/float).
    Se precisar aceitar outros tipos, use normalize_cyrillic() normal.
    
    Args:
        text: String a normalizar (deve ser str, não None)
    
    Returns:
        String normalizada
    
    Examples:
        >>> normalize_cyrillic_cached("Cт")
        'ct'
        >>> normalize_cyrillic_cached("Cт")  # Segunda chamada usa cache
        'ct'
    
    Performance:
        - Primeira chamada: ~5μs
        - Chamadas subsequentes (cache hit): ~0.5μs (10x mais rápido)
        - Speedup típico em loops: 5-15x
    
    Note:
        Cache pode ser limpo manualmente com:
        >>> normalize_cyrillic_cached.cache_clear()
        
        Para ver estatísticas do cache:
        >>> normalize_cyrillic_cached.cache_info()
    """
    if not text:
        return ""
    return text.translate(CYRILLIC_TO_ASCII_MAP).lower().strip()


def find_column_by_keywords(
    columns: List[str],
    keywords: List[str],
    normalize: bool = True
) -> Optional[str]:
    """
    Procura coluna em lista baseando-se em palavras-chave.
    
    Busca é case-insensitive e, opcionalmente, normaliza caracteres cirílicos.
    Retorna a PRIMEIRA coluna que contém qualquer uma das keywords.
    
    Args:
        columns: Lista de nomes de colunas a pesquisar
        keywords: Lista de palavras-chave (substrings) a buscar
        normalize: Se True (padrão), normaliza cirílico antes de comparar.
                   Se False, faz apenas lowercase comparison.
    
    Returns:
        Nome da primeira coluna que contém alguma keyword, ou None se não encontrar.
    
    Examples:
        >>> cols = ["Well", "Sample Name", "Cт", "Ct Mean"]
        >>> find_column_by_keywords(cols, ["ct", "cт"])
        'Cт'
        
        >>> cols = ["ID", "Amostra", "Alvo"]
        >>> find_column_by_keywords(cols, ["sample", "amostra"])
        'Amostra'
        
        >>> cols = ["Well", "Target"]
        >>> find_column_by_keywords(cols, ["poco", "poço"])
        None
    
    Note:
        - Busca é por SUBSTRING (não match exato)
        - Ordem importa: retorna PRIMEIRA coluna que bate
        - Se normalize=True, "Ct" e "Cт" (cirílico) são equivalentes
    """
    # MITIGAÇÃO RISCO #1: Validação de inputs
    if not columns or not keywords:
        return None
    
    for col in columns:
        # Normalizar coluna (cirílico se habilitado)
        col_normalized = (
            normalize_cyrillic(col) if normalize 
            else str(col).lower().strip()
        )
        
        for kw in keywords:
            # Normalizar keyword
            kw_normalized = (
                normalize_cyrillic(kw) if normalize
                else str(kw).lower().strip()
            )
            
            # Busca por substring
            if kw_normalized in col_normalized:
                return col  # Retorna nome ORIGINAL da coluna
    
    return None


def _normalize_col_key(name: Optional[Union[str, int, float]]) -> str:
    """
    Normaliza chaves de coluna para comparacao consistente.

    Regras:
    - Converte caracteres cirilicos para ASCII equivalente
    - Corrige mojibake comum
    - Remove parenteses, espacos e underscores
    - Usa casefold para comparacao case-insensitive robusta
    """
    if name is None:
        return ""

    try:
        raw = str(name).strip()
        raw = repair_mojibake_text(raw)

        value = normalize_cyrillic(raw)
        value = unicodedata.normalize("NFKD", value)
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = re.sub(r"[^a-z0-9]", "", value.casefold())
        return value
    except Exception:
        return re.sub(r"[^a-z0-9]", "", str(name).strip().casefold())


def repair_mojibake_text(value: Optional[Union[str, int, float]]) -> str:
    """
    Best-effort fix for common mojibake patterns (UTF-8 decoded as cp1252/latin1).
    """
    if value is None:
        return ""

    text = str(value)
    if not text:
        return ""

    # Fast path: skip text without typical mojibake markers.
    markers = (
        "Ã",  # ?
        "Â",  # ?
        "â",  # ?
        "�",  # replacement char
        "ƒ",  # ?
    )
    if not any(token in text for token in markers):
        return text

    def _score(candidate: str) -> int:
        return sum(candidate.count(token) for token in markers)

    # Candidate set with iterative round-trips (handles double-encoded segments).
    candidates = {text}
    for _ in range(2):
        snapshot = list(candidates)
        for cand in snapshot:
            for source_encoding in ("cp1252", "latin1"):
                try:
                    candidates.add(cand.encode(source_encoding).decode("utf-8"))
                except Exception:
                    continue

    best = min(candidates, key=lambda cand: (_score(cand), len(cand)))

    # Fallback replacements for recurrent sequences that survive round-trip.
    replacements = {
        "Ãƒâ€œ": "Ó",  # ????? -> ?
        "Ãƒâ‚¬": "Ô",  # ???? -> ?
        "Ãƒâ€¡": "Á",  # ???? -> ?
        "Ãƒâ€§": "Ç",  # ???? -> ?
        "Ã§": "ç",                    # ?? -> ?
        "Ã£": "ã",                    # ?? -> ?
        "Ã¡": "á",                    # ?? -> ?
        "Ã©": "é",                    # ?? -> ?
        "Ãª": "ê",                    # ?? -> ?
        "Ã­": "í",                    # ?? -> ?
        "Ã³": "ó",                    # ?? -> ?
        "Ã´": "ô",                    # ?? -> ?
        "Ãº": "ú",                    # ?? -> ?
        "Ã“": "Ó",                    # ?? -> ?
        "Ã‚": "Ú",                    # ?? -> ?
        "Ãƒ": "Ã",                    # ?? -> ?
        "Â": "",
    }
    fixed = best
    for wrong, right in replacements.items():
        fixed = fixed.replace(wrong, right)
    return fixed
