# -*- coding: utf-8 -*-
"""
config/business_rules.py

Definições centralizadas de Regras de Negócio do IntegRAGal.
Fonte única da verdade para parâmetros críticos de análise.

Protocolo: Biomanguinhos VR1e2
Criado em: 09/02/2026 (Refatoração de Segurança)
"""

# ============================================================================
# THRESHOLDS DE DETECÇÃO (CT)
# ============================================================================

# Valor mínimo para ser considerado Detectável
# CTs abaixo deste valor são considerados ruído ou negativo
CT_MIN_DETECTAVEL = 8.0

# Valor minimo usado especificamente na etapa de aplicacao de regras
# do fluxo PCR (helpers de analise). Mantem compatibilidade com testes
# que esperam limite inferior em 13.0.
CT_MIN_DETECTAVEL_ANALISE = 13.0

# Intervalo considerado Detectável (Válido)
# 8.0 <= CT < 35.0
CT_MAX_DETECTAVEL = 35.0

# Intervalo considerado Indeterminado (Requer Repetição)
# 35.0 <= CT <= 40.0
CT_MIN_INDETERMINADO = 35.0
CT_MAX_INDETERMINADO = 40.0

# Acima de 40.0 é considerado Não Detectável

# ============================================================================
# REGRAS DE CONTROLE INTERNO (RP)
# ============================================================================

CT_MIN_RP_VALIDO = 15.0
CT_MAX_RP_VALIDO = 35.0
