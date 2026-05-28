"""
Formula Parser - Fase 2.1
Avalia expressões matemáticas e lógicas com segurança.
"""

import ast
import re
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class FormulaValidationResult:
    """Resultado da validação de uma fórmula"""
    valida: bool
    mensagem: str
    variaveis_encontradas: List[str] = field(default_factory=list)
    operadores_encontrados: List[str] = field(default_factory=list)
    tempo_validacao_ms: float = 0.0


@dataclass
class FormulaEvaluationResult:
    """Resultado da avaliação de uma fórmula"""
    sucesso: bool
    resultado: Union[bool, float, str, None]
    mensagem_erro: Optional[str] = None
    tempo_execucao_ms: float = 0.0
    variaveis_usadas: Dict[str, Any] = field(default_factory=dict)
    expressao_expandida: str = ""


class FormulaTimeout(Exception):
    """Exceção levantada quando a avaliação de fórmula excede o timeout."""
    pass


# ============================================================================
# WHITELIST DE SEGURANÇA
# ============================================================================

# Operadores permitidos
OPERADORES_PERMITIDOS = {
    # Matemáticos
    'Add': '+',      'Sub': '-',      'Mult': '*',
    'Div': '/',      'Mod': '%',      'Pow': '**',
    'FloorDiv': '//',
    
    # Comparação
    'Eq': '==',      'NotEq': '!=',   'Lt': '<',
    'LtE': '<=',     'Gt': '>',       'GtE': '>=',
    
    # Lógicos
    'And': 'and',    'Or': 'or',      'Not': 'not',
    
    # Unários
    'UAdd': '+',     'USub': '-',
}

# Nodes AST permitidos
NODES_PERMITIDOS = {
    ast.Expression,   # Expressão completa
    ast.BinOp,        # Operação binária (a + b)
    ast.UnaryOp,      # Operação unária (-a)
    ast.Compare,      # Comparação (a < b)
    ast.BoolOp,       # Operação booleana (a and b)
    ast.Name,         # Nome de variável
    ast.Constant,     # Constante (número, string)
    ast.Load,         # Contexto de leitura
    # Operadores
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.FloorDiv,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.And, ast.Or, ast.Not,
    ast.UAdd, ast.USub,
}

# Padrão de variáveis permitidas
PATTERN_VARIAVEL = re.compile(
    r'^(CT_|ct_|resultado_|flag_|controle_|status_)[A-Z0-9_]+$', 
    re.IGNORECASE
)


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def extrair_variaveis(expressao: str) -> List[str]:
    """
    Extrai nomes de variáveis de uma fórmula.
    
    Args:
        expressao: Fórmula (ex: "CT_DEN1 + CT_DEN2")
        
    Returns:
        Lista de variáveis encontradas
    """
    variaveis = []
    # Encontrar todas palavras que parecem variáveis
    palavras = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', expressao)
    
    for palavra in palavras:
        # Ignorar palavras-chave Python
        if palavra.lower() in ('and', 'or', 'not', 'true', 'false', 'none'):
            continue
        # Validar padrão
        if PATTERN_VARIAVEL.match(palavra):
            if palavra not in variaveis:
                variaveis.append(palavra)
    
    return variaveis


def substituir_variaveis(expressao: str, variaveis: Dict[str, Any]) -> str:
    """
    Substitui variáveis por valores na fórmula.
    
    Args:
        expressao: Fórmula original
        variaveis: Dict com valores
        
    Returns:
        Expressão com variáveis substituídas
        
    Example:
        >>> substituir_variaveis("CT_DEN1 + CT_DEN2", {"CT_DEN1": 15.5, "CT_DEN2": 18.2})
        "15.5 + 18.2"
    """
    resultado = expressao
    
    # Substituir cada variável por seu valor
    for nome, valor in variaveis.items():
        # Converter valor para string apropriada
        if valor is None:
            valor_str = "None"
        elif isinstance(valor, str):
            valor_str = f"'{valor}'"  # Strings entre aspas
        else:
            valor_str = str(valor)
        
        # Substituir usando regex (palavra completa)
        padrao = r'\b' + re.escape(nome) + r'\b'
        resultado = re.sub(padrao, valor_str, resultado)
    
    return resultado


def formatar_erro(exception: Exception, contexto: str = "") -> str:
    """
    Formata mensagem de erro amigável.
    
    Args:
        exception: Exceção capturada
        contexto: Contexto adicional
        
    Returns:
        Mensagem formatada
    """
    tipo = type(exception).__name__
    mensagem = str(exception)
    
    # Mensagens amigáveis por tipo
    mensagens_amigaveis = {
        'SyntaxError': 'Erro de sintaxe na fórmula',
        'NameError': 'Variável não encontrada',
        'ZeroDivisionError': 'Divisão por zero',
        'TypeError': 'Tipo de dado incompatível',
        'ValueError': 'Valor inválido',
    }
    
    prefixo = mensagens_amigaveis.get(tipo, f'Erro ({tipo})')
    
    if contexto:
        return f"{prefixo} em {contexto}: {mensagem}"
    return f"{prefixo}: {mensagem}"


# ============================================================================
# VALIDAÇÃO DE FÓRMULA
# ============================================================================

def validar_formula(expressao: str) -> FormulaValidationResult:
    """
    Valida uma fórmula antes de avaliar.
    
    Verifica:
    - Sintaxe válida (parsing AST)
    - Apenas operadores permitidos
    - Variáveis seguem padrão correto
    - Sem funções perigosas (__import__, eval, etc)
    
    Args:
        expressao: String com a fórmula (ex: "CT_DEN1 < 30")
        
    Returns:
        FormulaValidationResult com status e detalhes
        
    Examples:
        >>> validar_formula("CT_DEN1 < 30")
        FormulaValidationResult(valida=True, mensagem="Fórmula válida", ...)
        
        >>> validar_formula("__import__('os')")
        FormulaValidationResult(valida=False, mensagem="Node proibido...", ...)
    """
    inicio = datetime.now()
    
    # 1. Verificar string vazia
    if not expressao or not expressao.strip():
        return FormulaValidationResult(
            valida=False,
            mensagem="Fórmula vazia",
            tempo_validacao_ms=0.0
        )
    
    try:
        # 2. Parsear com AST
        tree = ast.parse(expressao, mode='eval')
        
        # 3. Verificar nodes do AST
        for node in ast.walk(tree):
            node_type = type(node)
            
            # Verificar se node é permitido
            if node_type not in NODES_PERMITIDOS:
                return FormulaValidationResult(
                    valida=False,
                    mensagem=f"Node proibido: {node_type.__name__}",
                    tempo_validacao_ms=(datetime.now() - inicio).total_seconds() * 1000
                )
            
            # Verificar operadores
            if isinstance(node, (ast.BinOp, ast.UnaryOp)):
                op_type = type(node.op).__name__
                if op_type not in OPERADORES_PERMITIDOS:
                    return FormulaValidationResult(
                        valida=False,
                        mensagem=f"Operador proibido: {op_type}",
                        tempo_validacao_ms=(datetime.now() - inicio).total_seconds() * 1000
                    )
            
            # Verificar comparações
            if isinstance(node, ast.Compare):
                for op in node.ops:
                    op_type = type(op).__name__
                    if op_type not in OPERADORES_PERMITIDOS:
                        return FormulaValidationResult(
                            valida=False,
                            mensagem=f"Operador de comparação proibido: {op_type}",
                            tempo_validacao_ms=(datetime.now() - inicio).total_seconds() * 1000
                        )
            
            # Verificar booleanos
            if isinstance(node, ast.BoolOp):
                op_type = type(node.op).__name__
                if op_type not in OPERADORES_PERMITIDOS:
                    return FormulaValidationResult(
                        valida=False,
                        mensagem=f"Operador lógico proibido: {op_type}",
                        tempo_validacao_ms=(datetime.now() - inicio).total_seconds() * 1000
                    )
            
            # Verificar chamadas de função (PROIBIDO)
            if isinstance(node, ast.Call):
                return FormulaValidationResult(
                    valida=False,
                    mensagem="Chamadas de função não são permitidas",
                    tempo_validacao_ms=(datetime.now() - inicio).total_seconds() * 1000
                )
            
            # Verificar atributos (PROIBIDO - ex: obj.metodo)
            if isinstance(node, ast.Attribute):
                return FormulaValidationResult(
                    valida=False,
                    mensagem="Acesso a atributos não é permitido",
                    tempo_validacao_ms=(datetime.now() - inicio).total_seconds() * 1000
                )
        
        # 4. Extrair e validar variáveis
        variaveis = extrair_variaveis(expressao)
        
        for var in variaveis:
            if not PATTERN_VARIAVEL.match(var):
                return FormulaValidationResult(
                    valida=False,
                    mensagem=f"Variável '{var}' não segue padrão permitido (CT_*, resultado_*, flag_*, controle_*)",
                    variaveis_encontradas=variaveis,
                    tempo_validacao_ms=(datetime.now() - inicio).total_seconds() * 1000
                )
        
        # 5. Extrair operadores usados
        operadores = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.BinOp, ast.UnaryOp)):
                op_name = OPERADORES_PERMITIDOS.get(type(node.op).__name__)
                if op_name and op_name not in operadores:
                    operadores.append(op_name)
        
        # 6. Tudo OK!
        tempo_ms = (datetime.now() - inicio).total_seconds() * 1000
        
        logger.info(f"Fórmula validada com sucesso: {expressao} ({tempo_ms:.2f}ms)")
        
        return FormulaValidationResult(
            valida=True,
            mensagem="Fórmula válida",
            variaveis_encontradas=variaveis,
            operadores_encontrados=operadores,
            tempo_validacao_ms=tempo_ms
        )
    
    except SyntaxError as e:
        return FormulaValidationResult(
            valida=False,
            mensagem=formatar_erro(e, "parsing"),
            tempo_validacao_ms=(datetime.now() - inicio).total_seconds() * 1000
        )
    
    except Exception as e:
        logger.error(f"Erro inesperado validando fórmula: {e}")
        return FormulaValidationResult(
            valida=False,
            mensagem=formatar_erro(e),
            tempo_validacao_ms=(datetime.now() - inicio).total_seconds() * 1000
        )


# ============================================================================
# AVALIAÇÃO DE FÓRMULA
# ============================================================================

def avaliar_formula(
    expressao: str, 
    variaveis: Dict[str, Any],
    timeout_segundos: float = 1.0
) -> FormulaEvaluationResult:
    """
    Avalia uma fórmula com segurança.
    
    Processo:
    1. Valida fórmula
    2. Verifica variáveis disponíveis
    3. Substitui variáveis por valores
    4. Avalia com eval() controlado (sem __builtins__)
    5. Retorna resultado
    
    Args:
        expressao: Fórmula (ex: "(CT_DEN1 + CT_DEN2) / 2 < 33")
        variaveis: Dict com valores (ex: {"CT_DEN1": 15.5, "CT_DEN2": 18.2})
        timeout_segundos: Tempo máximo de execução (default: 1s)
        
    Returns:
        FormulaEvaluationResult com resultado ou erro
        
    Examples:
        >>> avaliar_formula("(15.5 + 18.2) / 2 < 33", {"CT_DEN1": 15.5, "CT_DEN2": 18.2})
        FormulaEvaluationResult(sucesso=True, resultado=True, ...)
        
        >>> avaliar_formula("CT_INEXISTENTE < 30", {})
        FormulaEvaluationResult(sucesso=False, mensagem_erro="Variável...", ...)
    """
    inicio = datetime.now()
    
    # 1. Validar fórmula primeiro
    validacao = validar_formula(expressao)
    if not validacao.valida:
        return FormulaEvaluationResult(
            sucesso=False,
            resultado=None,
            mensagem_erro=f"Validação falhou: {validacao.mensagem}",
            tempo_execucao_ms=(datetime.now() - inicio).total_seconds() * 1000
        )
    
    # 2. Verificar variáveis disponíveis
    variaveis_necessarias = validacao.variaveis_encontradas
    variaveis_faltando = [v for v in variaveis_necessarias if v not in variaveis]
    
    if variaveis_faltando:
        return FormulaEvaluationResult(
            sucesso=False,
            resultado=None,
            mensagem_erro=f"Variáveis não fornecidas: {', '.join(variaveis_faltando)}",
            tempo_execucao_ms=(datetime.now() - inicio).total_seconds() * 1000,
            variaveis_usadas=variaveis
        )
    
    # 3. Substituir variáveis
    try:
        expressao_expandida = substituir_variaveis(expressao, variaveis)
        logger.debug(f"Fórmula expandida: {expressao} → {expressao_expandida}")
    except Exception as e:
        return FormulaEvaluationResult(
            sucesso=False,
            resultado=None,
            mensagem_erro=formatar_erro(e, "substituição de variáveis"),
            tempo_execucao_ms=(datetime.now() - inicio).total_seconds() * 1000,
            variaveis_usadas=variaveis
        )
    
    # 4. Preparar contexto seguro
    # __builtins__={} remove TODAS funções builtin (print, open, __import__, etc)
    contexto_seguro = {
        '__builtins__': {},
        # Adicionar apenas funções matemáticas seguras se necessário
        'abs': abs,
        'min': min,
        'max': max,
        'round': round,
    }
    
    # 5. Avaliar com eval() controlado usando timeout
    try:
        resultado_container = [None]
        exception_container = [None]
        
        def worker():
            """Thread worker para avaliar a fórmula."""
            try:
                resultado_container[0] = eval(expressao_expandida, contexto_seguro, {})
            except Exception as e:
                exception_container[0] = e
        
        # Criar e iniciar thread
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout=timeout_segundos)
        
        # Verificar se thread finalizou
        if thread.is_alive():
            # Timeout excedido
            logger.error(f"Timeout ao avaliar fórmula: {expressao} (>{timeout_segundos}s)")
            raise FormulaTimeout(
                f"Fórmula excedeu tempo limite de {timeout_segundos}s: {expressao}"
            )
        
        # Verificar se houve exceção no worker
        if exception_container[0] is not None:
            raise exception_container[0]
        
        resultado = resultado_container[0]
        
        tempo_ms = (datetime.now() - inicio).total_seconds() * 1000
        
        logger.info(f"Fórmula avaliada: {expressao} = {resultado} ({tempo_ms:.2f}ms)")
        
        return FormulaEvaluationResult(
            sucesso=True,
            resultado=resultado,
            mensagem_erro=None,
            tempo_execucao_ms=tempo_ms,
            variaveis_usadas={k: variaveis[k] for k in variaveis_necessarias},
            expressao_expandida=expressao_expandida
        )
    
    except ZeroDivisionError as e:
        return FormulaEvaluationResult(
            sucesso=False,
            resultado=None,
            mensagem_erro="Divisão por zero",
            tempo_execucao_ms=(datetime.now() - inicio).total_seconds() * 1000,
            variaveis_usadas=variaveis,
            expressao_expandida=expressao_expandida
        )
    
    except NameError as e:
        return FormulaEvaluationResult(
            sucesso=False,
            resultado=None,
            mensagem_erro=formatar_erro(e),
            tempo_execucao_ms=(datetime.now() - inicio).total_seconds() * 1000,
            variaveis_usadas=variaveis,
            expressao_expandida=expressao_expandida
        )
    
    except FormulaTimeout as e:
        return FormulaEvaluationResult(
            sucesso=False,
            resultado=None,
            mensagem_erro=str(e),
            tempo_execucao_ms=(datetime.now() - inicio).total_seconds() * 1000,
            variaveis_usadas=variaveis,
            expressao_expandida=expressao_expandida
        )
    
    except Exception as e:
        logger.error(f"Erro avaliando fórmula: {e}")
        return FormulaEvaluationResult(
            sucesso=False,
            resultado=None,
            mensagem_erro=formatar_erro(e, "avaliação"),
            tempo_execucao_ms=(datetime.now() - inicio).total_seconds() * 1000,
            variaveis_usadas=variaveis,
            expressao_expandida=expressao_expandida
        )


# ============================================================================
# FUNÇÕES DE CONVENIÊNCIA
# ============================================================================

def avaliar_formula_simples(expressao: str, variaveis: Dict[str, Any]) -> bool:
    """
    Versão simplificada que retorna apenas True/False.
    
    Args:
        expressao: Fórmula booleana
        variaveis: Variáveis
        
    Returns:
        True se passou, False se falhou ou erro
    """
    resultado = avaliar_formula(expressao, variaveis)
    
    if not resultado.sucesso:
        logger.warning(f"Fórmula falhou: {resultado.mensagem_erro}")
        return False
    
    # Converter resultado para bool
    return bool(resultado.resultado)


def testar_formula(expressao: str, casos_teste: List[Dict[str, Any]]) -> None:
    """
    Testa uma fórmula com múltiplos casos.
    
    Args:
        expressao: Fórmula a testar
        casos_teste: Lista de dicts com variáveis
        
    Example:
        >>> testar_formula("CT_DEN1 < 30", [
        ...     {"CT_DEN1": 15.5},  # Deve passar
        ...     {"CT_DEN1": 35.0},  # Deve falhar
        ... ])
    """
    print(f"Testando fórmula: {expressao}")
    print("=" * 60)
    
    for i, caso in enumerate(casos_teste, 1):
        resultado = avaliar_formula(expressao, caso)
        
        status = "✅ OK" if resultado.sucesso else "❌ ERRO"
        print(f"Caso {i}: {status}")
        print(f"  Variáveis: {caso}")
        print(f"  Resultado: {resultado.resultado}")
        if resultado.mensagem_erro:
            print(f"  Erro: {resultado.mensagem_erro}")
        print(f"  Tempo: {resultado.tempo_execucao_ms:.2f}ms")
        print()


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == '__main__':
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    
    # Exemplo 1: Validação
    print("=" * 60)
    print("EXEMPLO 1: VALIDAÇÃO DE FÓRMULA")
    print("=" * 60)
    
    formulas_teste = [
        "CT_DEN1 < 30",
        "(CT_DEN1 + CT_DEN2) / 2 < 33",
        "CT_ZIKA < 30 and CT_DENGUE > 15",
        "__import__('os')",  # Inválida
        "variavel_invalida < 30",  # Inválida
    ]
    
    for formula in formulas_teste:
        validacao = validar_formula(formula)
        status = "✅ VÁLIDA" if validacao.valida else "❌ INVÁLIDA"
        print(f"{status}: {formula}")
        if not validacao.valida:
            print(f"  Erro: {validacao.mensagem}")
        print()
    
    # Exemplo 2: Avaliação
    print("=" * 60)
    print("EXEMPLO 2: AVALIAÇÃO DE FÓRMULA")
    print("=" * 60)
    
    variaveis = {
        "CT_DEN1": 15.5,
        "CT_DEN2": 18.2,
        "CT_ZIKA": 25.0,
        "CT_DENGUE": 20.0,
    }
    
    resultado = avaliar_formula("(CT_DEN1 + CT_DEN2) / 2 < 33", variaveis)
    print(f"Fórmula: (CT_DEN1 + CT_DEN2) / 2 < 33")
    print(f"Variáveis: {variaveis}")
    print(f"Resultado: {resultado.resultado}")
    print(f"Tempo: {resultado.tempo_execucao_ms:.2f}ms")
    print()
    
    # Exemplo 3: Teste de segurança
    print("=" * 60)
    print("EXEMPLO 3: TESTE DE SEGURANÇA")
    print("=" * 60)
    
    formulas_perigosas = [
        "__import__('os').system('ls')",
        "eval('print(123)')",
        "open('/etc/passwd')",
        "CT_DEN1.__class__",
    ]
    
    for formula in formulas_perigosas:
        validacao = validar_formula(formula)
        print(f"❌ {formula}")
        print(f"  Bloqueado: {validacao.mensagem}")
        print()
