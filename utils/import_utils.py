import importlib


def importar_funcao(modulo_funcao):
    """
    Importa e retorna uma função Python a partir de uma string como: 'analise.vr1.analisar_placa_vr1'
    """
    try:
        nome_modulo, nome_funcao = modulo_funcao.rsplit(".", 1)
        modulo = importlib.import_module(nome_modulo)
        funcao = getattr(modulo, nome_funcao)
        return funcao
    except Exception as e:
        raise ImportError(f"Erro ao importar '{modulo_funcao}': {e}")
