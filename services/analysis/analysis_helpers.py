"""
Helpers para análise de PCR - Refatoração #4 Fase 2

IMPORTANTE: Estas funções foram EXTRAÍDAS de AnalysisService.analisar_corrida
            para melhorar testabilidade e manutenibilidade.
            
            O método original permanece INTACTO. Estes helpers serão integrados
            na Fase 3 (criação de analisar_corrida_v2).

Data: 2026-01-31
Refatoração: #4 - Fase 2
"""

from typing import Dict, Tuple, Optional, Mapping
from pathlib import Path
import pandas as pd
import numpy as np

# Imports de refatorações anteriores
from utils.text_normalizer import normalize_cyrillic, find_column_by_keywords
from utils.well_sorter import get_rp_type
from utils.dataframe_validator import (
    validate_merge_quality,
    add_data_source_flag,
    log_unmapped_details
)
from utils.logger import registrar_log
from config.business_rules import (
    CT_MIN_DETECTAVEL,
    CT_MAX_DETECTAVEL,
)
from domain.ct_rules import classificar_ct as classificar_ct_domain

CT_COLUMN_BLOCKLIST = ("mean", "sd", "threshold", "automatic", "confidence")
TARGET_ALIAS_DEFAULT: Dict[str, str] = {
    "MPV": "HMPV",
    "ZIKA": "ZK",
    "ZYK": "ZK",
}


# ============================================================================
# HELPER 1: Identificação de Colunas
# ============================================================================

def identificar_colunas_pcr(df: pd.DataFrame) -> Dict[str, str]:
    """
    Identifica colunas Sample, Target, CT, Well do DataFrame PCR.
    
    EXTRAÍDO de: AnalysisService.analisar_corrida (linhas ~320-370)
    REFATORAÇÃO #4 - Fase 2
    
    Regras Críticas:
    - Normalização de cirílico ('Cт' → 'CT')
    - NUNCA usar coluna com 'mean' no nome para CT
    - Priorizar coluna exata 'C' ou 'CT' (sem outras palavras)
    
    Args:
        df: DataFrame bruto do arquivo PCR
    
    Returns:
        Dict com mapeamento de colunas:
        {
            'well': 'Well',
            'sample': 'Sample Name',
            'target': 'Target Name',
            'ct': 'CT'
        }
    
    Raises:
        ValueError: Se colunas essenciais não encontradas
    """
    cols_raw = df.columns.tolist()
    
    # Helper local para buscar coluna
    def find_col(keywords):
        """Wrapper para find_column_by_keywords com normalização"""
        return find_column_by_keywords(cols_raw, keywords, normalize=True)
    
    # Identificar colunas básicas
    col_well = _identificar_coluna_well(cols_raw) or find_col(['well', 'poco', 'poço'])
    col_sample = find_col(['sample', 'amostra'])
    col_target = find_col(['target', 'alvo', 'detector'])
    
    # CRÍTICO: Identificar CT com regras especiais
    col_ct = _identificar_coluna_ct(cols_raw)
    
    # Validar colunas essenciais
    if not (col_well and col_target and col_ct):
        missing = []
        if not col_well:
            missing.append('Well')
        if not col_target:
            missing.append('Target')
        if not col_ct:
            missing.append('CT')
        raise ValueError(f"Colunas essenciais não encontradas: {', '.join(missing)}")
    
    # Log de sucesso
    registrar_log(
        "analysis_helpers",
        f"✅ Colunas identificadas: Well='{col_well}', Sample='{col_sample}', "
        f"Target='{col_target}', CT='{col_ct}'",
        "DEBUG"
    )
    
    return {
        'well': col_well,
        'sample': col_sample,
        'target': col_target,
        'ct': col_ct
    }


def _identificar_coluna_well(cols_raw: list) -> Optional[str]:
    """Prioriza `Well Position` em planilhas Quanti antes de `Well`."""
    exact_priority = ("well position", "well_position")
    for col in cols_raw:
        normalized = normalize_cyrillic(col).replace("_", " ").strip().lower()
        if normalized in exact_priority:
            return col

    for col in cols_raw:
        normalized = normalize_cyrillic(col).replace("_", " ").strip().lower()
        if normalized == "well":
            return col

    return None


def _identificar_coluna_ct(cols_raw: list) -> Optional[str]:
    """
    Identifica coluna CT com regras especiais.
    
    REGRAS CRÍTICAS:
    1. NUNCA coluna com 'mean' no nome
    2. Priorizar coluna exata 'C' ou 'CT' (sem outras palavras)
    3. Fallback: coluna com 'ct' mas sem 'mean', 'sd', 'threshold'
    """
    def _clean_token(value: str) -> str:
        return (
            normalize_cyrillic(value)
            .replace("_", "")
            .replace(" ", "")
            .replace("(", "")
            .replace(")", "")
            .strip()
            .lower()
        )

    # Passo 1: Procurar coluna exata priorizando ct/cq/c(t)
    exact_priority = ("ct", "cq", "ct", "c", "ct")
    exact_matches: Dict[str, str] = {}
    for col in cols_raw:
        col_normalized = _clean_token(str(col))
        col_original = str(col).strip()

        if any(word in col_normalized for word in CT_COLUMN_BLOCKLIST):
            continue
        if col_normalized in ("c", "ct", "cq"):
            exact_matches[col_normalized] = col

    for key in exact_priority:
        if key in exact_matches:
            chosen = exact_matches[key]
            registrar_log(
                "analysis_helpers",
                f"⚠️ Coluna CT-like encontrada (exata): '{chosen}'",
                "DEBUG",
            )
            return chosen

    # Passo 2: Procurar coluna com ct/cq mas SEM palavras proibidas
    candidates: list[str] = []
    for col in cols_raw:
        col_normalized = normalize_cyrillic(col).replace("_", " ").lower()
        if any(word in col_normalized for word in CT_COLUMN_BLOCKLIST):
            continue
        if ("ct" in col_normalized) or ("cq" in col_normalized) or ("c(t)" in col_normalized):
            candidates.append(col)

    if candidates:
        # Heurística estável: coluna com nome menor tende a ser coluna analítica principal.
        candidates.sort(key=lambda item: len(str(item)))
        return candidates[0]

    # Passo 3: Fallback genérico mínimo
    result = find_column_by_keywords(cols_raw, ['ct', 'cq', 'c(t)', 'cт'], normalize=True)

    # VALIDAÇÃO FINAL: NUNCA retornar coluna com 'mean'
    if result and any(word in normalize_cyrillic(result).lower() for word in CT_COLUMN_BLOCKLIST):
        registrar_log(
            "analysis_helpers",
            f"⚠️ Coluna CT candidata '{result}' contém sufixo bloqueado, ignorando",
            "WARNING"
        )
        return None
    
    return result


def canonicalizar_alvo_pcr(target: object, aliases: Optional[Mapping[str, str]] = None) -> str:
    """Normaliza aliases de alvo mantendo um canônico único no domínio."""
    text = str(target or "").strip().upper()
    if not text:
        return ""

    alias_map: Dict[str, str] = {}
    alias_map.update(TARGET_ALIAS_DEFAULT)
    if aliases:
        alias_map.update({str(k).strip().upper(): str(v).strip().upper() for k, v in aliases.items()})
    return alias_map.get(text, text)


# ============================================================================
# HELPER 2: Normalização de Dados
# ============================================================================

def normalizar_dados_pcr(
    df: pd.DataFrame,
    col_map: Dict[str, str]
) -> pd.DataFrame:
    """
    Normaliza DataFrame PCR: CT float, wells padronizados, ordenação.
    
    EXTRAÍDO de: AnalysisService.analisar_corrida (linhas ~400-450)
    REFATORAÇÃO #4 - Fase 2
    
    Normalizações:
    - Renomear colunas para padrão interno
    - Converter CT para float (tratar 'Undetermined', 'N/A', etc como NaN)
    - Padronizar wells (A1 → A01, B10 → B10)
    - Ordenar por wells
    
    Args:
        df: DataFrame bruto
        col_map: Mapeamento de colunas (output de identificar_colunas_pcr)
    
    Returns:
        DataFrame normalizado com colunas:
        - Sample_Raw: Nome da amostra original
        - Target: Nome do alvo
        - CT_Raw: CT original (string)
        - CT: CT convertido para float
        - Well_Raw: Well original
        - Well: Well normalizado (A01, B02, etc)
    """
    df_norm = df.copy()
    
    # Renomear colunas para padrão interno
    rename_map = {
        col_map['well']: 'Well_Raw',
        col_map['target']: 'Target',
        col_map['ct']: 'CT_Raw'
    }
    
    if col_map['sample']:
        rename_map[col_map['sample']] = 'Sample_Raw'
    
    df_norm = df_norm.rename(columns=rename_map)
    df_norm['Target'] = df_norm['Target'].apply(canonicalizar_alvo_pcr)
    
    # Criar Sample_Raw se não existe
    if 'Sample_Raw' not in df_norm.columns:
        df_norm['Sample_Raw'] = ''
    
    # Converter CT para float
    df_norm['CT'] = pd.to_numeric(df_norm['CT_Raw'], errors='coerce')
    
    # Normalizar wells (A1 → A01)
    df_norm['Well'] = df_norm['Well_Raw'].astype(str).str.strip().str.upper()
    df_norm['Well'] = df_norm['Well'].apply(_normalizar_well_id)
    
    # Ordenar por wells (solução local temporária)
    df_norm = df_norm.sort_values('Well').reset_index(drop=True)
    
    registrar_log(
        "analysis_helpers",
        f"✅ Dados normalizados: {len(df_norm)} linhas, {len(df_norm.columns)} colunas",
        "DEBUG"
    )
    
    return df_norm


def _normalizar_well_id(well: str) -> str:
    """Normaliza ID de well: A1 → A01, B10 → B10"""
    if not well or len(well) < 2:
        return well
    
    # Extrair letra e número
    letra = well[0]
    numero = well[1:].strip()
    
    try:
        num_int = int(numero)
        return f"{letra}{num_int:02d}"  # Pad com zero à esquerda
    except ValueError:
        return well  # Retornar original se não conseguir converter


# ============================================================================
# HELPER 3: Integração com Gabarito
# ============================================================================

def integrar_gabarito_pcr(
    df: pd.DataFrame,
    gabarito_path: Optional[Path],
    app_state=None
) -> pd.DataFrame:
    """
    Integra gabarito ao DataFrame PCR com validação de merge.
    
    EXTRAÍDO de: AnalysisService.analisar_corrida (linhas ~460-588)
    REFATORAÇÃO #4 - Fase 2
    INTEGRA: Refatoração #3 (validação de merge)
    
    Funcionalidades:
    - Se sem gabarito → fallback para Sample_Raw
    - Carregar gabarito (Excel/CSV) ou pegar do app_state
    - Expandir 48→96 poços (A1→A1+A2)
    - Merge com validação (validate_merge_quality)
    - Adicionar Data_Source flag
    - Filtrar poços vazios ('X')
    
    Args:
        df: DataFrame normalizado com Well, Sample_Raw, Target, CT
        gabarito_path: Caminho opcional do gabarito
        app_state: AppState opcional (para pegar df_gabarito_extracao)
    
    Returns:
        DataFrame com 'Sample' e 'Data_Source'
    """
    df_result = df.copy()
    
    # Tentar obter gabarito do app_state primeiro
    gabarito = None
    if app_state and hasattr(app_state, 'df_gabarito_extracao') and app_state.df_gabarito_extracao is not None:
        gabarito = app_state.df_gabarito_extracao.copy()
        registrar_log("analysis_helpers", f"✅ Gabarito do app_state: {len(gabarito)} linhas", "DEBUG")
    elif gabarito_path and Path(gabarito_path).exists():
        try:
            if str(gabarito_path).endswith(('.xlsx', '.xls')):
                gabarito = pd.read_excel(gabarito_path)
            else:
                gabarito = pd.read_csv(gabarito_path)
            registrar_log("analysis_helpers", f"✅ Gabarito carregado de arquivo: {len(gabarito)} linhas", "DEBUG")
        except Exception as e:
            registrar_log("analysis_helpers", f"❌ Erro ao carregar gabarito: {e}", "ERROR")
    
    # Se não tem gabarito, usar fallback
    if gabarito is None or gabarito.empty:
        registrar_log("analysis_helpers", "⚠️ Gabarito NÃO disponível, fallback", "WARNING")
        df_result['Sample'] = df_result['Sample_Raw']
        df_result['Data_Source'] = 'FALLBACK'
        return df_result
    
    # Identificar coluna de poço no gabarito
    col_poco_gab = None
    for col in gabarito.columns:
        if any(word in str(col).lower() for word in ['poco', 'poço', 'well']):
            col_poco_gab = col
            break
    
    if not col_poco_gab:
        registrar_log("analysis_helpers", "⚠️ Gabarito sem coluna Poco/Well", "WARNING")
        df_result['Sample'] = df_result['Sample_Raw']
        df_result['Data_Source'] = 'FALLBACK'
        return df_result
    
    # CRÍTICO: Expandir gabarito 48→96 poços
    # Gabarito original: A1, A3, A5... (ímpares)
    # Cada poço mapeia para ele + próximo: A1→A1+A2, A3→A3+A4
    gabarito_expandido = []
    for _, row in gabarito.iterrows():
        poco_orig = str(row[col_poco_gab]).strip().upper()
        
        if len(poco_orig) >= 2:
            try:
                letra = poco_orig[0]
                numero = int(poco_orig[1:])
                
                # Poço original
                row1 = row.copy()
                row1[col_poco_gab] = poco_orig
                gabarito_expandido.append(row1)
                
                # Poço adjacente (número + 1)
                poco2 = f"{letra}{numero + 1}"
                row2 = row.copy()
                row2[col_poco_gab] = poco2
                gabarito_expandido.append(row2)
            except ValueError:
                gabarito_expandido.append(row)
        else:
            gabarito_expandido.append(row)
    
    gabarito = pd.DataFrame(gabarito_expandido)
    registrar_log("analysis_helpers", f"✅ Gabarito expandido: {len(gabarito)} poços", "INFO")
    
    # Normalizar wells do gabarito
    gabarito['Well_Gab'] = gabarito[col_poco_gab].astype(str).str.strip().str.upper()
    
    # Merge com DataFrame PCR
    merge_cols = ['Well_Gab']
    if 'Amostra' in gabarito.columns:
        merge_cols.append('Amostra')
    if 'Codigo' in gabarito.columns:
        merge_cols.append('Codigo')
    
    df_result = df_result.merge(
        gabarito[merge_cols],
        left_on='Well',
        right_on='Well_Gab',
        how='left'
    )
    
    # Validar qualidade do merge (Refatoração #3)
    indicator_col = 'Amostra' if 'Amostra' in df_result.columns else merge_cols[-1]
    validation_result = validate_merge_quality(
        df_result,
        merge_key='Well',
        indicator_column=indicator_col,
        min_mapping_rate=0.50,
        max_unmapped_to_log=20
    )
    
    log_unmapped_details(validation_result, logger_func=registrar_log, context="analysis_helpers")
    
    # Adicionar Data_Source flag
    df_result = add_data_source_flag(
        df_result,
        source_column=indicator_col,
        flag_column_name='Data_Source'
    )
    
    # Criar coluna Sample final (com fallback)
    df_result['Sample'] = df_result[indicator_col].fillna(df_result['Sample_Raw'])
    
    # Filtrar poços vazios ('X')
    df_result = df_result[df_result['Sample'] != 'X'].copy()
    df_result = df_result[df_result['Sample'].notna()].copy()
    
    registrar_log(
        "analysis_helpers",
        f"✅ Integração: {validation_result.mapped_rows} mapeados, "
        f"{validation_result.unmapped_rows} fallback ({validation_result.mapping_rate:.1%})",
        "INFO"
    )
    
    return df_result


# ============================================================================
# HELPER 4: Separação RP/Alvos
# ============================================================================

def separar_rp_alvos(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Separa DataFrame em RPs e Alvos.
    
    EXTRAÍDO de: AnalysisService.analisar_corrida (linhas ~590-608)
    REFATORAÇÃO #4 - Fase 2
    INTEGRA: Refatoração #2 (get_rp_type)
    
    Args:
        df: DataFrame normalizado com coluna 'Target'
    
    Returns:
        Tuple (df_rp, df_alvos)
    """
    # Separar RPs de outros alvos
    df_rp = df[df['Target'].str.contains('RP', na=False, case=False)].copy()
    df_alvos = df[~df['Target'].str.contains('RP', na=False, case=False)].copy()
    
    # Adicionar tipo de RP usando get_rp_type (Refatoração #2)
    if not df_rp.empty:
        df_rp['RP_Tipo'] = df_rp['Well'].apply(lambda w: get_rp_type(w, strict=True))
        
        registrar_log(
            "analysis_helpers",
            f"✅ RPs identificados: {len(df_rp)} registros, "
            f"Tipos únicos: {df_rp['RP_Tipo'].unique().tolist()}",
            "DEBUG"
        )
    else:
        registrar_log(
            "analysis_helpers",
            "⚠️  Nenhum RP encontrado no DataFrame",
            "WARNING"
        )
    
    if df_alvos.empty:
        registrar_log(
            "analysis_helpers",
            "⚠️ Nenhum alvo (não-RP) encontrado no DataFrame",
            "WARNING"
        )
    else:
        registrar_log(
            "analysis_helpers",
            f"✅ Alvos identificados: {len(df_alvos)} registros, "
            f"Targets únicos: {df_alvos['Target'].unique().tolist()}",
            "DEBUG"
        )
    
    return df_rp, df_alvos


# ============================================================================
# HELPER 5: Pivot de Dados
# ============================================================================

def pivotar_dados_pcr(
    df_rp: pd.DataFrame,
    df_alvos: pd.DataFrame
) -> pd.DataFrame:
    """
    Pivota dados: 1 linha por amostra com colunas para cada alvo+RP.
    
    EXTRAÍDO de: AnalysisService.analisar_corrida (linhas ~720-800)
    REFATORAÇÃO #4 - Fase 2
    
    Args:
        df_rp: DataFrame com apenas RPs
        df_alvos: DataFrame com apenas alvos
    
    Returns:
        DataFrame pivotado (1 linha = 1 amostra)
    """
    # Pivot alvos: 1 linha por Sample, colunas para cada Target
    pivot_ct_alvos = pd.DataFrame()
    if not df_alvos.empty:
        pivot_ct_alvos = df_alvos.pivot_table(
            index='Sample',
            columns='Target',
            values='CT',
            aggfunc='mean'  # Média de duplicatas (A1+A2)
        )
        registrar_log(
            "analysis_helpers",
            f"✅ Pivot alvos: {pivot_ct_alvos.shape[0]} amostras, {pivot_ct_alvos.shape[1]} alvos",
            "DEBUG"
        )
    
    # Pivot RPs: usar coluna Target_RP ou RP_Tipo se existir
    pivot_ct_rp = pd.DataFrame()
    if not df_rp.empty:
        # Usar RP_Tipo se disponível (RP_1, RP_2), senão Target
        rp_col = 'RP_Tipo' if 'RP_Tipo' in df_rp.columns else 'Target'
        pivot_ct_rp = df_rp.pivot_table(
            index='Sample',
            columns=rp_col,
            values='CT',
            aggfunc='first'  # Primeiro valor (não fazer média de RPs!)
        )
        registrar_log(
            "analysis_helpers",
            f"✅ Pivot RPs: {pivot_ct_rp.shape[0]} amostras, {pivot_ct_rp.shape[1]} tipos de RP",
            "DEBUG"
        )
    
    # Merge alvos + RPs
    if not pivot_ct_alvos.empty and not pivot_ct_rp.empty:
        df_pivotado = pivot_ct_alvos.join(pivot_ct_rp, how='outer')
    elif not pivot_ct_alvos.empty:
        df_pivotado = pivot_ct_alvos
    elif not pivot_ct_rp.empty:
        df_pivotado = pivot_ct_rp
    else:
        registrar_log("analysis_helpers", "⚠️ Nenhum dado para pivotar", "WARNING")
        return pd.DataFrame()
    
    df_pivotado = df_pivotado.reset_index()
    
    registrar_log(
        "analysis_helpers",
        f"✅ Pivot final: {len(df_pivotado)} amostras, {len(df_pivotado.columns)} colunas",
        "INFO"
    )
    
    return df_pivotado


# ============================================================================
# HELPER 6: Validação CN/CP
# ============================================================================

def validar_placa_cn_cp(df: pd.DataFrame) -> Dict:
    """
    Valida controles CN/CP e retorna resultado geral da placa.
    
    EXTRAÍDO de: AnalysisService.analisar_corrida (linhas ~820-900)
    REFATORAÇÃO #4 - Fase 2
    
    Args:
        df: DataFrame pivotado
    
    Returns:
        {
            'cn_valido': bool,
            'cp_valido': bool,
            'resultado_geral': 'APROVADO' | 'REPROVADO',
            'detalhes': str
        }
    """
    # Validação de controles negativos (CN) e positivos (CP)
    # CN deve ter CT alto ou vazio (não detectável)
    # CP deve ter CT detectável (faixa configurada)
    
    cn_valido = True
    cp_valido = True
    detalhes = []
    
    if 'Sample' not in df.columns:
        return {
            'cn_valido': False,
            'cp_valido': False,
            'resultado_geral': 'REPROVADO',
            'detalhes': 'DataFrame sem coluna Sample'
        }
    
    # Procurar CN e CP
    amostras = df['Sample'].tolist()
    df_cn = df[df['Sample'].str.upper().str.contains('CN', na=False)]
    df_cp = df[df['Sample'].str.upper().str.contains('CP', na=False)]
    
    # Validar CN (deve ser não detectável)
    if not df_cn.empty:
        # Procurar colunas de CT (qualquer coluna que comece com 'CT_' ou seja 'CT')
        ct_cols = [c for c in df_cn.columns if c.startswith('CT') or c == 'CT']
        if ct_cols:
            # CN é válido se todos CTs vazios ou fora do range detectável
            for col in ct_cols:
                ct_vals = df_cn[col].dropna()
                if len(ct_vals) > 0:
                    if any(
                        CT_MIN_DETECTAVEL <= v <= CT_MAX_DETECTAVEL
                        for v in ct_vals
                        if isinstance(v, (int, float))
                    ):
                        cn_valido = False
                        detalhes.append(f"CN com CT detectável em {col}")
        detalhes.append(f"CN encontrado: {len(df_cn)} linhas")
    else:
        detalhes.append("CN NÃO encontrado")
    
    # Validar CP (deve ser detectável)
    if not df_cp.empty:
        ct_cols = [c for c in df_cp.columns if c.startswith('CT') or c == 'CT']
        if ct_cols:
            # CP é válido se pelo menos um CT no range detectável
            tem_detectavel = False
            for col in ct_cols:
                ct_vals = df_cp[col].dropna()
                if any(
                        CT_MIN_DETECTAVEL <= v <= CT_MAX_DETECTAVEL
                        for v in ct_vals
                        if isinstance(v, (int, float))
                    ):
                    tem_detectavel = True
                    break
            if not tem_detectavel:
                cp_valido = False
                detalhes.append("CP sem CT detectável")
        detalhes.append(f"CP encontrado: {len(df_cp)} linhas")
    else:
        detalhes.append("CP NÃO encontrado")
    
    resultado_geral = 'APROVADO' if (cn_valido and cp_valido) else 'REPROVADO'
    
    resultado = {
        'cn_valido': cn_valido,
        'cp_valido': cp_valido,
        'resultado_geral': resultado_geral,
        'detalhes': '; '.join(detalhes)
    }
    
    registrar_log(
        "analysis_helpers",
        f"🔍 Validação: {resultado_geral} (CN: {cn_valido}, CP: {cp_valido})",
        "INFO"
    )
    
    return resultado


# ============================================================================
# HELPER 7: Regras de Negócio
# ============================================================================

def aplicar_regras_negocio(
    df: pd.DataFrame,
    validacao: Dict
) -> pd.DataFrame:
    """
    Aplica regras de negócio: médias, detecção, sugestão de repetição.
    
    EXTRAÍDO de: AnalysisService.analisar_corrida (linhas ~900-974)
    REFATORAÇÃO #4 - Fase 2
    
    Args:
        df: DataFrame pivotado
        validacao: Resultado da validação CN/CP
    
    Returns:
        DataFrame final com colunas de resultado
    """
    # Aplicar regras de análise VR1e2 Biomanguinhos
    # Aplicar regras de análise VR1e2 Biomanguinhos
    # Constantes importadas de config.business_rules
    # CT_MIN_DETECTAVEL = 8.0  <-- REMOVED (Centralized)
    
    df_result = df.copy()
    
    # Criar colunas de resultado (Res_*) para cada coluna de CT
    ct_cols = [c for c in df.columns if c.startswith('CT_') and c != 'CT_Raw']
    
    for ct_col in ct_cols:
        target_name = ct_col.replace('CT_', '')
        res_col = f'Res_{target_name}'
        # Aplicar regras centralizadas de detecção (domain.ct_rules)
        df_result[res_col] = df_result[ct_col].apply(
            lambda ct_val: str(classificar_ct_domain(ct_val))
        )
    
    # Adicionar Status_corrida baseado em validação
    df_result['Status_corrida'] = validacao.get('resultado_geral', 'APROVADO')
    
    # Sugestão de repetição (simplificado)
    df_result['Sugestão_de_repetição'] = 'Não'
    
    registrar_log(
        "analysis_helpers",
        f"✅ Regras aplicadas: {len(df_result)} amostras, {len(ct_cols)} alvos analisados",
        "INFO"
    )
    
    return df_result
