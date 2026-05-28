"""
Rules Engine - Fase 2.2
Aplica regras customizadas aos resultados de análise.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

# Importar Formula Parser
from services.formula_parser import avaliar_formula, FormulaEvaluationResult

logger = logging.getLogger(__name__)

# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class Validacao:
    """Resultado de uma validação individual"""
    regra_id: str
    regra_nome: str
    resultado: str  # "passou", "falhou", "aviso", "nao_aplicavel"
    detalhes: str
    impacto: str  # "critico", "alto", "medio", "baixo"
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RulesResult:
    """Resultado completo da aplicação de regras"""
    status: str  # "valida", "invalida", "aviso"
    validacoes: List[Validacao] = field(default_factory=list)
    mensagens_erro: List[str] = field(default_factory=list)
    mensagens_aviso: List[str] = field(default_factory=list)
    detalhes: str = ""
    tempo_execucao_ms: float = 0.0


# ============================================================================
# CONSTANTES
# ============================================================================

TIPO_REGRA = {
    'booleana': 'Regra simples true/false',
    'formula': 'Avaliação de fórmula',
    'condicional': 'Regra if-then',
    'sequencia': 'Alvos obrigatórios',
    'exclusao_mutua': 'Apenas um pode ser positivo',
    'threshold': 'Valor dentro de range',
}

NIVEL_IMPACTO = {
    'critico': 4,
    'alto': 3,
    'medio': 2,
    'baixo': 1,
}


# ============================================================================
# APLICADORES DE REGRAS ESPECÍFICAS
# ============================================================================

def aplicar_regra_booleana(
    nome: str,
    valor: bool,
    resultados: Dict[str, Any]
) -> Validacao:
    """
    Aplica regra booleana simples.
    
    Args:
        nome: Nome da regra (ex: "requer_dois_alvos")
        valor: True/False
        resultados: Dict com resultados da análise
        
    Returns:
        Validacao com resultado
    """
    # Implementar lógica específica por nome de regra
    if nome == "requer_dois_alvos":
        # Contar alvos positivos
        alvos = resultados.get('alvos', {})
        positivos = sum(
            1 for alvo, dados in alvos.items()
            if dados.get('resultado') in ('Detectado', 'Positivo')
        )
        
        passou = (positivos >= 2) == valor
        
        return Validacao(
            regra_id=f"bool_{nome}",
            regra_nome=nome,
            resultado="passou" if passou else "falhou",
            detalhes=f"Alvos positivos: {positivos} (esperado: {'≥2' if valor else '<2'})",
            impacto="alto"
        )
    
    # Regra genérica
    return Validacao(
        regra_id=f"bool_{nome}",
        regra_nome=nome,
        resultado="passou" if valor else "falhou",
        detalhes=f"Regra booleana: {valor}",
        impacto="medio"
    )


def aplicar_regra_formula(
    formula: str,
    resultados: Dict[str, Any],
    formula_parser: Any = None
) -> Validacao:
    """
    Aplica regra baseada em fórmula.
    
    Args:
        formula: Fórmula a avaliar
        resultados: Dict com resultados
        formula_parser: Módulo parser (injetado)
        
    Returns:
        Validacao com resultado
    """
    # Preparar variáveis da fórmula
    variaveis = _preparar_variaveis_formulas(resultados)
    
    # Avaliar fórmula
    if formula_parser:
        resultado = formula_parser.avaliar_formula(formula, variaveis)
    else:
        resultado = avaliar_formula(formula, variaveis)
    
    if not resultado.sucesso:
        return Validacao(
            regra_id=f"formula_{hash(formula)}",
            regra_nome=f"Fórmula: {formula}",
            resultado="falhou",
            detalhes=f"Erro: {resultado.mensagem_erro}",
            impacto="alto"
        )
    
    passou = bool(resultado.resultado)
    
    return Validacao(
        regra_id=f"formula_{hash(formula)}",
        regra_nome=f"Fórmula: {formula}",
        resultado="passou" if passou else "falhou",
        detalhes=f"Resultado: {resultado.resultado} (tempo: {resultado.tempo_execucao_ms:.1f}ms)",
        impacto="alto"
    )


def aplicar_regra_condicional(
    regra: Dict[str, Any],
    resultados: Dict[str, Any],
    formula_parser: Any = None
) -> Validacao:
    """
    Aplica regra if-then.
    
    Args:
        regra: Dict com 'if', 'then', 'descricao', 'impacto'
        resultados: Dict com resultados
        formula_parser: Módulo parser
        
    Returns:
        Validacao com resultado
    """
    condicao_if = regra.get('if', '')
    condicao_then = regra.get('then', '')
    descricao = regra.get('descricao', 'Regra condicional')
    impacto = regra.get('impacto', 'medio')
    
    # Preparar variáveis
    variaveis = _preparar_variaveis_formulas(resultados)
    
    # Avaliar IF
    if formula_parser:
        resultado_if = formula_parser.avaliar_formula(condicao_if, variaveis)
    else:
        resultado_if = avaliar_formula(condicao_if, variaveis)
    
    if not resultado_if.sucesso:
        return Validacao(
            regra_id=f"cond_{hash(descricao)}",
            regra_nome=descricao,
            resultado="nao_aplicavel",
            detalhes=f"Erro avaliando IF: {resultado_if.mensagem_erro}",
            impacto=impacto
        )
    
    # Se IF é False, regra não se aplica
    if not bool(resultado_if.resultado):
        return Validacao(
            regra_id=f"cond_{hash(descricao)}",
            regra_nome=descricao,
            resultado="nao_aplicavel",
            detalhes="Condição IF não satisfeita (regra não aplicada)",
            impacto=impacto
        )
    
    # IF é True, avaliar THEN
    if formula_parser:
        resultado_then = formula_parser.avaliar_formula(condicao_then, variaveis)
    else:
        resultado_then = avaliar_formula(condicao_then, variaveis)
    
    if not resultado_then.sucesso:
        return Validacao(
            regra_id=f"cond_{hash(descricao)}",
            regra_nome=descricao,
            resultado="falhou",
            detalhes=f"Erro avaliando THEN: {resultado_then.mensagem_erro}",
            impacto=impacto
        )
    
    passou = bool(resultado_then.resultado)
    
    return Validacao(
        regra_id=f"cond_{hash(descricao)}",
        regra_nome=descricao,
        resultado="passou" if passou else "falhou",
        detalhes=f"IF={resultado_if.resultado}, THEN={resultado_then.resultado}",
        impacto=impacto
    )


def aplicar_regra_sequencia(
    regra: Dict[str, Any],
    resultados: Dict[str, Any]
) -> Validacao:
    """
    Valida presença de alvos obrigatórios.
    
    Args:
        regra: Dict com 'alvos_obrigatorios', 'descricao'
        resultados: Dict com resultados
        
    Returns:
        Validacao com resultado
    """
    alvos_obrigatorios = regra.get('alvos_obrigatorios', [])
    descricao = regra.get('descricao', 'Alvos obrigatórios')
    
    alvos_presentes = resultados.get('alvos', {})
    alvos_faltando = [a for a in alvos_obrigatorios if a not in alvos_presentes]
    
    passou = len(alvos_faltando) == 0
    
    return Validacao(
        regra_id=f"seq_{hash(descricao)}",
        regra_nome=descricao,
        resultado="passou" if passou else "falhou",
        detalhes=f"Obrigatórios: {alvos_obrigatorios}, Faltando: {alvos_faltando}",
        impacto="alto"
    )


def aplicar_regra_exclusao_mutua(
    regra: Dict[str, Any],
    resultados: Dict[str, Any]
) -> Validacao:
    """
    Valida exclusão mútua entre alvos.
    
    Args:
        regra: Dict com 'alvos', 'descricao'
        resultados: Dict com resultados
        
    Returns:
        Validacao com resultado
    """
    alvos_exclusivos = regra.get('alvos', [])
    descricao = regra.get('descricao', 'Exclusão mútua')
    
    alvos_dados = resultados.get('alvos', {})
    positivos = [
        alvo for alvo in alvos_exclusivos
        if alvo in alvos_dados and alvos_dados[alvo].get('resultado') in ('Detectado', 'Positivo')
    ]
    
    passou = len(positivos) <= 1
    
    return Validacao(
        regra_id=f"excl_{hash(descricao)}",
        regra_nome=descricao,
        resultado="passou" if passou else "falhou",
        detalhes=f"Alvos exclusivos: {alvos_exclusivos}, Positivos: {positivos}",
        impacto="alto"
    )


# ============================================================================
# APLICADOR PRINCIPAL
# ============================================================================

def aplicar_regras(
    regras_dict: Dict[str, Any],
    resultados_dict: Dict[str, Any],
    formula_parser: Any = None
) -> RulesResult:
    """
    Aplica todas as regras aos resultados.
    
    Processo:
    1. Valida estrutura de regras
    2. Aplica cada tipo de regra
    3. Coleta validações
    4. Determina status geral
    5. Gera mensagens
    
    Args:
        regras_dict: Dict com todas regras
        resultados_dict: Dict com resultados da análise
        formula_parser: Módulo parser (opcional, usa padrão se None)
        
    Returns:
        RulesResult com status completo
    """
    inicio = datetime.now()
    validacoes = []
    
    try:
        # 1. Aplicar regras booleanas
        for nome, valor in regras_dict.items():
            if isinstance(valor, bool):
                validacao = aplicar_regra_booleana(nome, valor, resultados_dict)
                validacoes.append(validacao)
        
        # 2. Aplicar fórmulas
        formulas = regras_dict.get('formulas', [])
        for formula in formulas:
            validacao = aplicar_regra_formula(formula, resultados_dict, formula_parser)
            validacoes.append(validacao)
        
        # 3. Aplicar condicionais
        condicoes = regras_dict.get('condicoes', [])
        for condicao in condicoes:
            validacao = aplicar_regra_condicional(condicao, resultados_dict, formula_parser)
            validacoes.append(validacao)
        
        # 4. Aplicar sequência
        sequencia = regras_dict.get('sequencia')
        if sequencia:
            validacao = aplicar_regra_sequencia(sequencia, resultados_dict)
            validacoes.append(validacao)
        
        # 5. Aplicar exclusão mútua
        exclusao = regras_dict.get('exclusao_mutua')
        if exclusao:
            validacao = aplicar_regra_exclusao_mutua(exclusao, resultados_dict)
            validacoes.append(validacao)
        
        # 6. Determinar status geral
        status = determinar_status_geral(validacoes)
        
        # 7. Gerar mensagens
        erros, avisos = gerar_mensagens(validacoes)
        
        # 8. Gerar detalhes
        detalhes = gerar_detalhes_resumo(validacoes)
        
        tempo_ms = (datetime.now() - inicio).total_seconds() * 1000
        
        logger.info(f"Regras aplicadas: {len(validacoes)} validações ({tempo_ms:.2f}ms)")
        
        return RulesResult(
            status=status,
            validacoes=validacoes,
            mensagens_erro=erros,
            mensagens_aviso=avisos,
            detalhes=detalhes,
            tempo_execucao_ms=tempo_ms
        )
    
    except Exception as e:
        logger.error(f"Erro aplicando regras: {e}")
        return RulesResult(
            status="invalida",
            validacoes=validacoes,
            mensagens_erro=[f"Erro fatal: {str(e)}"],
            detalhes=f"Erro ao aplicar regras: {str(e)}",
            tempo_execucao_ms=(datetime.now() - inicio).total_seconds() * 1000
        )


# ============================================================================
# GERADORES DE STATUS E MENSAGENS
# ============================================================================

def determinar_status_geral(validacoes: List[Validacao]) -> str:
    """
    Determina status geral baseado em todas validações.
    
    Regras:
    - Se alguma crítica/alta falhou → "invalida"
    - Se todas passaram → "valida"
    - Se há avisos mas nenhuma falha → "aviso"
    
    Args:
        validacoes: Lista de validações aplicadas
        
    Returns:
        Status: "valida", "invalida", "aviso"
    """
    if not validacoes:
        return "valida"
    
    falhas_criticas = [
        v for v in validacoes
        if v.resultado == "falhou" and v.impacto in ('critico', 'alto')
    ]
    
    if falhas_criticas:
        return "invalida"
    
    falhas = [v for v in validacoes if v.resultado == "falhou"]
    
    if falhas:
        return "aviso"
    
    return "valida"


def gerar_mensagens(validacoes: List[Validacao]) -> tuple:
    """
    Gera mensagens de erro e aviso.
    
    Args:
        validacoes: Lista de validações
        
    Returns:
        Tupla (erros, avisos)
    """
    erros = []
    avisos = []
    
    for v in validacoes:
        if v.resultado == "falhou":
            msg = f"{v.regra_nome}: {v.detalhes}"
            if v.impacto in ('critico', 'alto'):
                erros.append(msg)
            else:
                avisos.append(msg)
    
    return erros, avisos


def gerar_detalhes_resumo(validacoes: List[Validacao]) -> str:
    """
    Gera resumo textual das validações.
    
    Args:
        validacoes: Lista de validações
        
    Returns:
        String com resumo
    """
    if not validacoes:
        return "Nenhuma regra aplicada"
    
    passou = sum(1 for v in validacoes if v.resultado == "passou")
    falhou = sum(1 for v in validacoes if v.resultado == "falhou")
    nao_aplicavel = sum(1 for v in validacoes if v.resultado == "nao_aplicavel")
    
    return f"{passou} passou, {falhou} falhou, {nao_aplicavel} não aplicável (total: {len(validacoes)})"


def _preparar_variaveis_formulas(resultados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepara dict de variáveis para fórmulas.
    
    Args:
        resultados: Dict com alvos e controles
        
    Returns:
        Dict com variáveis prontas (CT_*, resultado_*, etc)
    """
    variaveis = {}
    
    # Adicionar alvos
    alvos = resultados.get('alvos', {})
    for nome_alvo, dados in alvos.items():
        # CT_{ALVO}
        ct = dados.get('ct')
        if ct is not None:
            variaveis[f"CT_{nome_alvo}"] = float(ct)
        
        # resultado_{ALVO}
        resultado = dados.get('resultado', '')
        if resultado:
            variaveis[f"resultado_{nome_alvo}"] = resultado
    
    # Adicionar controles
    controles = resultados.get('controles', {})
    for nome_controle, dados in controles.items():
        # CT_{CONTROLE}
        ct = dados.get('ct')
        if ct is not None:
            variaveis[f"CT_{nome_controle}"] = float(ct)
        
        # controle_{CONTROLE}
        status = dados.get('status', '')
        if status:
            variaveis[f"controle_{nome_controle}"] = status
    
    return variaveis


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == '__main__':
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("EXEMPLO 1: REGRAS BOOLEANAS")
    print("=" * 60)
    
    resultados = {
        'alvos': {
            'DEN1': {'resultado': 'Detectado', 'ct': 15.5},
            'DEN2': {'resultado': 'Detectado', 'ct': 18.2},
            'ZIKA': {'resultado': 'Não Detectado', 'ct': 40.0},
        }
    }
    
    regras = {
        'requer_dois_alvos': True,
    }
    
    resultado = aplicar_regras(regras, resultados)
    print(f"Status: {resultado.status}")
    print(f"Detalhes: {resultado.detalhes}")
    print()
    
    print("=" * 60)
    print("EXEMPLO 2: REGRAS COM FÓRMULAS")
    print("=" * 60)
    
    resultados = {
        'alvos': {
            'DEN1': {'resultado': 'Detectado', 'ct': 15.5},
            'DEN2': {'resultado': 'Detectado', 'ct': 18.2},
        }
    }
    
    regras = {
        'formulas': [
            '(CT_DEN1 + CT_DEN2) / 2 < 33',
            'CT_DEN1 < 30',
        ]
    }
    
    resultado = aplicar_regras(regras, resultados)
    print(f"Status: {resultado.status}")
    print(f"Detalhes: {resultado.detalhes}")
    for v in resultado.validacoes:
        print(f"  - {v.regra_nome}: {v.resultado} ({v.detalhes})")
    print()
    
    print("=" * 60)
    print("EXEMPLO 3: REGRAS CONDICIONAIS")
    print("=" * 60)
    
    resultados = {
        'alvos': {
            'DEN1': {'resultado': 'Detectado', 'ct': 15.5},
            'DEN2': {'resultado': 'Detectado', 'ct': 45.0},
        }
    }
    
    regras = {
        'condicoes': [
            {
                'if': 'CT_DEN1 < 30',
                'then': 'CT_DEN2 < 30',
                'descricao': 'Se DEN1 positivo, DEN2 deve ser positivo',
                'impacto': 'alto'
            }
        ]
    }
    
    resultado = aplicar_regras(regras, resultados)
    print(f"Status: {resultado.status}")
    print(f"Detalhes: {resultado.detalhes}")
    if resultado.mensagens_erro:
        print(f"Erros: {resultado.mensagens_erro}")
    for v in resultado.validacoes:
        print(f"  - {v.regra_nome}: {v.resultado} ({v.detalhes})")
    print()
    
    print("=" * 60)
    print("EXEMPLO 4: EXCLUSÃO MÚTUA")
    print("=" * 60)
    
    resultados = {
        'alvos': {
            'DEN1': {'resultado': 'Detectado', 'ct': 15.5},
            'ZIKA': {'resultado': 'Detectado', 'ct': 18.0},
        }
    }
    
    regras = {
        'exclusao_mutua': {
            'alvos': ['DEN1', 'ZIKA', 'CHIK'],
            'descricao': 'Apenas um arbovirose pode ser positivo'
        }
    }
    
    resultado = aplicar_regras(regras, resultados)
    print(f"Status: {resultado.status}")
    print(f"Detalhes: {resultado.detalhes}")
    if resultado.mensagens_erro:
        print(f"Erros: {resultado.mensagens_erro}")
    for v in resultado.validacoes:
        print(f"  - {v.regra_nome}: {v.resultado} ({v.detalhes})")
    print()
    
    print("=" * 60)
    print("✅ TODOS OS EXEMPLOS CONCLUÍDOS!")
    print("=" * 60)
