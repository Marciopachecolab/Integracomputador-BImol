"""
Equipment Extractors - Fase 1.3
Extratores específicos para cada tipo de equipamento PCR.
Normalizam dados de Excel para formato padrão: (bem, amostra, alvo, ct)
"""

import pandas as pd
import openpyxl
import xlrd
from pathlib import Path
from typing import Optional, Dict, Any, List
import re
from dataclasses import dataclass


@dataclass
class EquipmentConfig:
    """Configuração de um equipamento (deve ser compatível com equipment_registry.py)"""
    nome: str
    xlsx_estrutura: Dict[str, Any]  # {coluna_well, coluna_sample, coluna_target, coluna_ct, linha_inicio}


class ExtratorError(Exception):
    """Erro durante extração de dados"""
    pass


def _validar_config(config: EquipmentConfig) -> None:
    """
    Valida se a config tem os campos necessários.
    Lança ExtratorError se faltar algo.
    """
    estrutura = config.xlsx_estrutura
    
    # Campos obrigatórios
    if 'linha_inicio' not in estrutura or estrutura['linha_inicio'] <= 0:
        raise ExtratorError(f"Config do equipamento '{config.nome}': linha_inicio inválida ou ausente")
    
    # Coluna well é obrigatória
    if 'coluna_well' not in estrutura or estrutura['coluna_well'] is None:
        raise ExtratorError(f"Config do equipamento '{config.nome}': coluna_well não especificada")
    
    # CT também é obrigatória
    if 'coluna_ct' not in estrutura or estrutura['coluna_ct'] is None:
        raise ExtratorError(f"Config do equipamento '{config.nome}': coluna_ct não especificada")


def _processar_ct(valor: Any) -> Optional[float]:
    """
    Converte valor de CT para float.
    Aceita: números, strings numéricas, "Undetermined", "N/A", "No Amp"
    Retorna None para valores não determináveis.
    """
    if pd.isna(valor):
        return None
    
    if isinstance(valor, (int, float)):
        return float(valor)
    
    if isinstance(valor, str):
        valor_upper = valor.strip().upper()
        
        # Valores que indicam não determinado
        if valor_upper in ("UNDETERMINED", "N/A", "NA", "NO AMP", "N/D", "-", ""):
            return None
        
        # Tentar converter para float
        try:
            return float(valor.replace(",", "."))
        except (ValueError, AttributeError):
            return None
    
    return None


def _validar_formato_well(well: str, formato_esperado: str = 'A01') -> bool:
    """
    Valida formato do well.
    formato_esperado: 'A01' (com zero) ou 'A1' (sem zero)
    """
    if not well or not isinstance(well, str):
        return False
    
    well = well.strip().upper()
    
    if formato_esperado == 'A01':
        # Formato A01-H12 (com zero à esquerda)
        pattern = r'^[A-H](0[1-9]|1[0-2])$'
    else:
        # Formato A1-H12 (sem zero à esquerda)
        pattern = r'^[A-H]([1-9]|1[0-2])$'
    
    return bool(re.match(pattern, well))


def _normalizar_well(well: str) -> str:
    """
    Normaliza formato do well para padrão A01-H12.
    Converte A1 -> A01, a01 -> A01, etc.
    """
    if not well or not isinstance(well, str):
        return ""
    
    well = well.strip().upper()
    
    # Se já está no formato A01, retorna
    if re.match(r'^[A-H](0[1-9]|1[0-2])$', well):
        return well
    
    # Se está no formato A1, adiciona zero à esquerda
    match = re.match(r'^([A-H])([1-9]|1[0-2])$', well)
    if match:
        letra = match.group(1)
        numero = int(match.group(2))
        return f"{letra}{numero:02d}"
    
    return well  # Retorna como está se não conseguiu normalizar


def _ler_xlsx_generico(caminho: str, linha_inicio: int, max_rows: int = 1000) -> pd.DataFrame:
    """
    Lê arquivo XLSX/XLS de forma genérica.
    linha_inicio: primeira linha de dados (1-indexed)
    Retorna DataFrame com todas as colunas.
    """
    caminho_path = Path(caminho)
    
    if not caminho_path.exists():
        raise ExtratorError(f"Arquivo não encontrado: {caminho}")
    
    extensao = caminho_path.suffix.lower()
    
    try:
        if extensao == '.xls':
            # Usar xlrd para .xls
            wb = xlrd.open_workbook(caminho)
            ws = wb.sheet_by_index(0)
            
            # Ler headers da linha anterior à linha_inicio
            header_row = linha_inicio - 2 if linha_inicio > 1 else 0
            headers = [str(ws.cell_value(header_row, col)) for col in range(ws.ncols)]
            
            # Ler dados
            dados = []
            for row_idx in range(linha_inicio - 1, min(ws.nrows, linha_inicio - 1 + max_rows)):
                row_data = [ws.cell_value(row_idx, col) for col in range(ws.ncols)]
                dados.append(row_data)
            
            df = pd.DataFrame(dados, columns=headers)
        else:
            # Usar openpyxl para .xlsx/.xlsm
            df = pd.read_excel(
                caminho,
                engine='openpyxl',
                header=linha_inicio - 2 if linha_inicio > 1 else 0,
                nrows=max_rows
            )
        
        return df
    
    except Exception as e:
        raise ExtratorError(f"Erro ao ler arquivo '{caminho}': {str(e)}")


def extrair_7500(caminho: str, config: EquipmentConfig) -> pd.DataFrame:
    """
    Extrator para Applied Biosystems 7500 (formato padrão).
    
    Estrutura esperada:
    - Headers: Well, Sample Name, Target Name, Cq
    - Colunas: A-D (0-3)
    - Linha início: 5
    - Formato well: A1 (sem zero)
    
    Retorna DataFrame normalizado: ['bem', 'amostra', 'alvo', 'ct']
    """
    _validar_config(config)
    
    estrutura = config.xlsx_estrutura
    linha_inicio = estrutura['linha_inicio']
    col_well = estrutura['coluna_well']
    col_sample = estrutura.get('coluna_sample')
    col_target = estrutura.get('coluna_target')
    col_ct = estrutura['coluna_ct']
    
    # Ler arquivo
    df = _ler_xlsx_generico(caminho, linha_inicio)
    
    if df.empty:
        raise ExtratorError("Arquivo vazio ou sem dados")
    
    # Mapear colunas por índice
    colunas = list(df.columns)
    
    if col_well >= len(colunas):
        raise ExtratorError(f"Coluna well (índice {col_well}) não existe no arquivo")
    if col_ct >= len(colunas):
        raise ExtratorError(f"Coluna CT (índice {col_ct}) não existe no arquivo")
    
    # Extrair dados
    dados_normalizados = []
    
    for idx, row in df.iterrows():
        well = str(row.iloc[col_well]).strip() if col_well < len(row) else ""
        sample = str(row.iloc[col_sample]).strip() if col_sample is not None and col_sample < len(row) else ""
        target = str(row.iloc[col_target]).strip() if col_target is not None and col_target < len(row) else ""
        ct_raw = row.iloc[col_ct] if col_ct < len(row) else None
        
        # Validar well
        if not well or well.upper() in ('NAN', 'NONE', ''):
            continue
        
        # Validar formato do well (A1-H12)
        if not _validar_formato_well(well, formato_esperado='A1'):
            continue
        
        # Normalizar well para A01
        well_norm = _normalizar_well(well)
        
        # Processar CT
        ct_valor = _processar_ct(ct_raw)
        
        # Target não pode ser vazio
        if not target or target.upper() in ('NAN', 'NONE', ''):
            continue
        
        dados_normalizados.append({
            'bem': well_norm,
            'amostra': sample,
            'alvo': target,
            'ct': ct_valor
        })
    
    if not dados_normalizados:
        raise ExtratorError("Nenhum dado válido encontrado após extração")
    
    return pd.DataFrame(dados_normalizados)


def extrair_7500_extended(caminho: str, config: EquipmentConfig) -> pd.DataFrame:
    """
    Extrator para Applied Biosystems 7500 Extended (com metadados, usa Cт cirílico).
    
    Estrutura esperada:
    - Headers: Well, Sample Name, Target Name, Cт
    - Colunas: A, B, C, G (0, 1, 2, 6)
    - Linha início: 9
    - Formato well: A1 (sem zero)
    
    Retorna DataFrame normalizado: ['bem', 'amostra', 'alvo', 'ct']
    """
    # Mesma lógica do 7500 padrão, apenas difere na posição das colunas
    return extrair_7500(caminho, config)


def extrair_cfx96(caminho: str, config: EquipmentConfig) -> pd.DataFrame:
    """
    Extrator para Bio-Rad CFX96.
    
    Estrutura esperada:
    - Headers: Well, Fluor, Target, Sample, Cq
    - Colunas: Well (0), Fluor (1), Target (2), Sample (4), Cq (5)
    - Linha início: 21
    - Formato well: A01 (com zero)
    
    IMPORTANTE: A coluna Target é OBRIGATÓRIA e deve conter os alvos (genes).
    Se a coluna Target estiver vazia, o arquivo está incompleto e deve ser corrigido.
    
    Retorna DataFrame normalizado: ['bem', 'amostra', 'alvo', 'ct']
    """
    _validar_config(config)
    
    estrutura = config.xlsx_estrutura
    linha_inicio = estrutura['linha_inicio']
    col_well = estrutura['coluna_well']
    col_sample = estrutura.get('coluna_sample')
    col_target = estrutura.get('coluna_target')
    col_ct = estrutura['coluna_ct']
    
    # Ler arquivo
    df = _ler_xlsx_generico(caminho, linha_inicio)
    
    if df.empty:
        raise ExtratorError("Arquivo vazio ou sem dados")
    
    # Validar que coluna Target existe e tem dados
    if col_target is None:
        raise ExtratorError(
            "CFX96: Configuração inválida - coluna Target não especificada. "
            "Verifique a configuração do equipamento."
        )
    
    if col_target >= len(df.columns):
        raise ExtratorError(
            f"CFX96: Coluna Target (índice {col_target}) não existe no arquivo. "
            f"O arquivo possui apenas {len(df.columns)} colunas."
        )
    
    # Verificar se Target tem valores válidos (não NaN, não vazio)
    target_serie = df.iloc[:, col_target]
    target_validos = target_serie.apply(lambda x: pd.notna(x) and str(x).strip().upper() not in ('NAN', 'NONE', ''))
    target_preenchido = target_validos.sum()
    
    if target_preenchido == 0:
        # Target completamente vazio ou só com NaN - arquivo incompleto
        raise ExtratorError(
            "CFX96: Planilha incompleta - coluna 'Target' está vazia ou contém apenas valores NaN. "
            "A coluna Target é obrigatória e deve conter os nomes dos alvos/genes. "
            "Por favor, exporte novamente do equipamento com a coluna Target preenchida ou "
            "complete manualmente os dados de Target no arquivo."
        )
    
    # Extrair dados
    dados_normalizados = []
    
    for idx, row in df.iterrows():
        well = str(row.iloc[col_well]).strip() if col_well < len(row) else ""
        sample = str(row.iloc[col_sample]).strip() if col_sample is not None and col_sample < len(row) else ""
        target = str(row.iloc[col_target]).strip() if col_target < len(row) else ""
        ct_raw = row.iloc[col_ct] if col_ct < len(row) else None
        
        # Validar well
        if not well or well.upper() in ('NAN', 'NONE', ''):
            continue
        
        # Validar formato do well (A01-H12)
        if not _validar_formato_well(well, formato_esperado='A01'):
            continue
        
        # Processar CT
        ct_valor = _processar_ct(ct_raw)
        
        # Target não pode ser vazio
        if not target or target.upper() in ('NAN', 'NONE', ''):
            continue
        
        dados_normalizados.append({
            'bem': well,  # CFX96 já usa formato A01
            'amostra': sample,
            'alvo': target,
            'ct': ct_valor
        })
    
    if not dados_normalizados:
        raise ExtratorError(
            "CFX96: Nenhum dado válido encontrado após extração. "
            "Verifique se o arquivo possui wells válidos (A01-H12) e alvos preenchidos."
        )
    
    return pd.DataFrame(dados_normalizados)


def extrair_cfx96_export(caminho: str, config: EquipmentConfig) -> pd.DataFrame:
    """
    Extrator para Bio-Rad CFX96 Export (formato com C(t) e múltiplos alvos).
    
    Estrutura esperada:
    - Headers L1: Well, Name, Type...
    - Headers L2: E gene, C(t), RdRP/S gene, C(t)...
    - Linha início: 3
    - Formato well: A01 (com zero)
    - Múltiplas colunas C(t) para diferentes alvos
    
    DESAFIO: Este formato tem múltiplas colunas C(t), cada uma para um alvo diferente.
    Precisamos extrair cada par (alvo, C(t)) separadamente.
    
    Retorna DataFrame normalizado: ['bem', 'amostra', 'alvo', 'ct']
    """
    _validar_config(config)
    
    estrutura = config.xlsx_estrutura
    linha_inicio = estrutura['linha_inicio']
    col_well = estrutura['coluna_well']
    col_sample = estrutura.get('coluna_sample')
    
    # Ler arquivo com headers nas duas primeiras linhas
    caminho_path = Path(caminho)
    extensao = caminho_path.suffix.lower()
    
    # Ler arquivo completo para acessar múltiplos headers
    if extensao == '.xls':
        wb = xlrd.open_workbook(str(caminho_path))
        ws = wb.sheet_by_index(0)
        
        # Headers linha 1 e 2 (índices 0 e 1)
        headers_l1 = [str(ws.cell_value(0, col)) for col in range(ws.ncols)]
        headers_l2 = [str(ws.cell_value(1, col)) for col in range(ws.ncols)]
        
        # Ler dados a partir da linha 3 (índice 2)
        dados = []
        for row_idx in range(2, ws.nrows):
            row_data = [ws.cell_value(row_idx, col) for col in range(ws.ncols)]
            dados.append(row_data)
        
        df = pd.DataFrame(dados)
    else:
        df = pd.read_excel(caminho, engine='openpyxl', header=None)
        headers_l1 = df.iloc[0].tolist()
        headers_l2 = df.iloc[1].tolist()
        df = df.iloc[2:].reset_index(drop=True)  # Dados a partir da linha 3
    
    if df.empty:
        raise ExtratorError("Arquivo vazio ou sem dados")
    
    # Identificar pares (alvo, C(t))
    # Padrão: coluna com nome de alvo (ex: "E gene") seguida de coluna "C(t)"
    pares_alvo_ct = []
    
    for idx in range(len(headers_l2) - 1):
        h1 = str(headers_l1[idx]).strip()
        h2 = str(headers_l2[idx]).strip()
        h_next = str(headers_l2[idx + 1]).strip().upper()
        
        # Se próxima coluna é C(t) ou CT ou Cq, este é um alvo
        if h_next in ('C(T)', 'CT', 'CQ', 'C(T)'):
            alvo = h2 if h2 and h2 != 'nan' else h1
            if alvo and alvo != 'nan':
                pares_alvo_ct.append((idx, idx + 1, alvo))  # (col_alvo, col_ct, nome_alvo)
    
    if not pares_alvo_ct:
        raise ExtratorError("Nenhum par (alvo, C(t)) identificado no arquivo CFX96_Export")
    
    # Extrair dados para cada par
    dados_normalizados = []
    
    for idx, row in df.iterrows():
        well = str(row.iloc[col_well]).strip() if col_well < len(row) else ""
        sample = str(row.iloc[col_sample]).strip() if col_sample is not None and col_sample < len(row) else ""
        
        # Validar well
        if not well or well.upper() in ('NAN', 'NONE', ''):
            continue
        
        if not _validar_formato_well(well, formato_esperado='A01'):
            continue
        
        # Para cada par (alvo, C(t)), criar uma entrada
        for col_alvo, col_ct, nome_alvo in pares_alvo_ct:
            ct_raw = row.iloc[col_ct] if col_ct < len(row) else None
            ct_valor = _processar_ct(ct_raw)
            
            # Apenas adicionar se CT tiver valor (não None)
            if ct_valor is not None:
                dados_normalizados.append({
                    'bem': well,
                    'amostra': sample,
                    'alvo': nome_alvo,
                    'ct': ct_valor
                })
    
    if not dados_normalizados:
        raise ExtratorError("Nenhum dado válido encontrado após extração")
    
    return pd.DataFrame(dados_normalizados)


def extrair_quantstudio(caminho: str, config: EquipmentConfig) -> pd.DataFrame:
    """
    Extrator para Thermo Fisher QuantStudio.
    
    Estrutura esperada:
    - Headers: Well, Well Position, Sample, Target, Cq
    - Colunas: Well (0) - número, Well Position (1) - formato A1, Sample (3), Target (4), Cq (12)
    - Linha início: 25
    - Formato well: A1 (sem zero) em Well Position
    
    NOTA: QuantStudio usa coluna "Well" com números (1,2,3) e "Well Position" com formato A1
    
    Retorna DataFrame normalizado: ['bem', 'amostra', 'alvo', 'ct']
    """
    _validar_config(config)
    
    estrutura = config.xlsx_estrutura
    linha_inicio = estrutura['linha_inicio']
    col_sample = estrutura.get('coluna_sample')
    col_target = estrutura.get('coluna_target')
    col_ct = estrutura['coluna_ct']
    
    # QuantStudio: usar Well Position (coluna 1) ao invés de Well (coluna 0)
    col_well = 1  # Well Position tem formato A1
    
    # Ler arquivo
    df = _ler_xlsx_generico(caminho, linha_inicio)
    
    if df.empty:
        raise ExtratorError("Arquivo vazio ou sem dados")
    
    # Extrair dados
    dados_normalizados = []
    
    for idx, row in df.iterrows():
        # Usar Well Position (coluna 1) ao invés de Well (coluna 0)
        well = str(row.iloc[col_well]).strip() if col_well < len(row) else ""
        sample = str(row.iloc[col_sample]).strip() if col_sample is not None and col_sample < len(row) else ""
        target = str(row.iloc[col_target]).strip() if col_target is not None and col_target < len(row) else ""
        ct_raw = row.iloc[col_ct] if col_ct < len(row) else None
        
        # Validar well
        if not well or well.upper() in ('NAN', 'NONE', ''):
            continue
        
        # Validar formato do well (A1-H12 sem zero)
        if not _validar_formato_well(well, formato_esperado='A1'):
            continue
        
        # Normalizar well para A01
        well_norm = _normalizar_well(well)
        
        # Processar CT
        ct_valor = _processar_ct(ct_raw)
        
        # Target não pode ser vazio
        if not target or target.upper() in ('NAN', 'NONE', ''):
            continue
        
        dados_normalizados.append({
            'bem': well_norm,
            'amostra': sample,
            'alvo': target,
            'ct': ct_valor
        })
    
    if not dados_normalizados:
        raise ExtratorError("Nenhum dado válido encontrado após extração")
    
    return pd.DataFrame(dados_normalizados)


def extrair_generico(caminho: str, config: EquipmentConfig) -> pd.DataFrame:
    """
    Extrator genérico para formatos desconhecidos.
    Tenta extrair dados baseado apenas nas posições de colunas da config.
    
    Retorna DataFrame normalizado: ['bem', 'amostra', 'alvo', 'ct']
    """
    return extrair_7500(caminho, config)  # Usa lógica padrão


# Mapeamento de equipamentos para funções extratoras
EXTRACTORS_MAP = {
    '7500': extrair_7500,
    '7500_Extended': extrair_7500_extended,
    'CFX96': extrair_cfx96,
    'CFX96_Export': extrair_cfx96_export,
    'QuantStudio': extrair_quantstudio,
}


def extrair_dados_equipamento(caminho: str, config: EquipmentConfig) -> pd.DataFrame:
    """
    Função principal para extrair dados de um arquivo baseado na config do equipamento.
    
    Args:
        caminho: Caminho para o arquivo XLSX/XLS
        config: EquipmentConfig com informações do equipamento
    
    Returns:
        DataFrame normalizado com colunas ['bem', 'amostra', 'alvo', 'ct']
    
    Raises:
        ExtratorError: Se houver erro na extração
    """
    # Selecionar extrator baseado no nome do equipamento
    extrator = EXTRACTORS_MAP.get(config.nome, extrair_generico)
    
    return extrator(caminho, config)
