"""
Utilitários para debug de DataFrames.
Mantido para compatibilidade com código legado.
"""

from .dataframe_reporter import log_dataframe


def dump_df(tag, df, extra=None, head=5):
    """
    Função legada de debug de DataFrame.
    Agora também registra no sistema de relatórios.
    """
    try:
        print(f"[DFDBG] {tag}: shape={df.shape} cols={list(df.columns)}")
        if extra:
            print(f"[DFDBG] {tag} extra={extra}")
        print(df.head(head))
        
        # Registrar no sistema de relatórios
        metadata = {"extra": extra} if extra else None
        log_dataframe(df, tag, "debug", metadata=metadata, save_sample=True)
        
    except Exception as e:
        print(f"[DFDBG] {tag} erro ao inspecionar DF: {e}")
