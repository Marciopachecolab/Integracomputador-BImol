import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from utils.logger import registrar_log

class DataCleaner:
    """
    Responsável por limpar e normalizar dados brutos de arquivos de PCR
    baseado em configurações de perfil de equipamento.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cleaning_rules = config.get("data_cleaning", {})
        self.col_map = config.get("column_mapping", {})

    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica todas as regras de limpeza configuradas."""
        try:
            # 1. Localizar cabeçalho real (se necessário)
            df = self._locate_header(df)
            
            # 2. Normalizar nomes de colunas
            df = self._normalize_columns(df)
            
            # 3. Filtrar colunas relevantes
            required_cols = ["well", "sample_id", "target_name", "ct_value"]
            # filter_dye é opcional se não estiver no mapping
            if "filter_dye" in self.col_map:
                required_cols.append("filter_dye")
            
            # Verificar se colunas cruciais existem
            missing = [c for c in ["well", "target_name", "ct_value"] if c not in df.columns]
            if missing:
                raise ValueError(f"Colunas obrigatórias não encontradas após normalização: {missing}. Colunas disponíveis: {list(df.columns)}")

            # 4. Tratar valores nulos e strings
            df = self._clean_content(df)
            
            return df
            
        except Exception as e:
            registrar_log("DataCleaner", f"Erro na limpeza de dados: {e}", "ERROR")
            raise

    def _locate_header(self, df: pd.DataFrame) -> pd.DataFrame:
        """Localiza a linha de cabeçalho baseada em keywords."""
        strategy = self.cleaning_rules.get("start_row_strategy", "first_row")
        
        if strategy == "first_row":
            return df
            
        if strategy == "search_header":
            keywords = [k.lower() for k in self.cleaning_rules.get("header_keywords", ["well", "target"])]
            
            # Procurar nas primeiras 50 linhas
            for idx, row in df.head(50).iterrows():
                row_str = row.astype(str).str.lower().tolist()
                # Se encontrar pelo menos 2 keywords na linha
                matches = sum(1 for k in keywords if any(k in str(v) for v in row_str))
                if matches >= 2:
                    # Promover esta linha a header
                    new_header = row
                    df = df.iloc[idx + 1:].copy()
                    df.columns = new_header
                    return df.reset_index(drop=True)
                    
        return df

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Renomeia colunas do arquivo para nomes padrão do sistema."""
        reverse_map = {}
        # Criar mapa reverso: "Nome Real" -> "nome_padrao"
        for std_name, aliases in self.col_map.items():
            for alias in aliases:
                reverse_map[alias.lower().strip()] = std_name
        
        # Mapa atual das colunas do DF
        new_cols = {}
        for col in df.columns:
            col_clean = str(col).strip().lower()
            if col_clean in reverse_map:
                new_cols[col] = reverse_map[col_clean]
        
        return df.rename(columns=new_cols)

    def _clean_content(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpa valores de células (trim, nulls, decimais)."""
        null_vals = [n.lower() for n in self.cleaning_rules.get("null_values", [])]
        
        # Helper para limpar strings
        def clean_str(val):
            if pd.isna(val): return None
            s = str(val).strip()
            if s.lower() in null_vals: return None
            return s
            
        # Helper para Ct (float)
        dec_sep = self.cleaning_rules.get("decimal_separator", ".")
        
        def clean_ct(val):
            if pd.isna(val): return None
            s = str(val).strip()
            if s.lower() in null_vals: return None
            
            try:
                if dec_sep == "," and "," in s:
                    s = s.replace(".", "").replace(",", ".")
                return float(s)
            except (ValueError, TypeError) as e:
                # Valor Ct não pode ser convertido para float (formato inválido)
                registrar_log("DataCleaner", f"Valor Ct inválido '{val}': {type(e).__name__}", "DEBUG")
                return None

        # Aplicar limpezas
        if "well" in df.columns:
            df["well"] = df["well"].apply(clean_str)
            
        if "target_name" in df.columns:
            df["target_name"] = df["target_name"].apply(clean_str)
            # Padronizar para UPPERCASE para facilitar matching
            df["target_name"] = df["target_name"].str.upper()
            
        if "sample_id" in df.columns:
            df["sample_id"] = df["sample_id"].apply(clean_str)

        if "ct_value" in df.columns:
            df["ct_value"] = df["ct_value"].apply(clean_ct)
            
        # Remover linhas onde well ou target são nulos (dados inúteis)
        df.dropna(subset=["well", "target_name"], inplace=True)
        
        return df
