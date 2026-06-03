# Forensics — Segunda opinião arquitetural (GAL-ROB-001..010)

- **Data:** 2026-06-01T20:55:00Z
- **Origem:** Fase 2 Audit Refactoring (T-022 etapa 3) — skill `architect-review`
- **Insumo:** `snapshots/forensics_gal_rob_check.md` + leitura direta do código
- **Impacto arquitetural avaliado:** Baixo (verificação read-only; nenhuma mudança)

## Confirmações semânticas (não apenas palavra-chave)

Verifiquei por leitura direta que cada proteção implementa a *semântica* declarada:

- **ROB-002/003** (`envio_gal.py:683-698`): `failed_pages` coleta exceções de futures; o
  laço **não propaga** falha — segue para o log de finalização. Aviso `[S5]` inclui contagem e
  amostra de até 3 erros. Resiliência (degradação graciosa) correta.
- **ROB-006** (`envio_gal.py:1006-1015`): `_SENSITIVE_KEYS` mascara `paciente/nome/_raw` com `***`
  por compreensão de dict antes do log; guard `isinstance(response, dict)`. Privacidade no ponto
  de log — correto (S14).
- **ROB-007** (`gal_send_use_case.py:273-314`): padrão *check-then-act atômico* sob `threading.Lock`
  com reserva de `inflight_keys` antes de liberar o lock. Elimina corrida entre workers para a
  mesma amostra (dual-key: escopo + legada). Implementação canônica de concorrência — correta.
  Localização na camada `application/` está **arquiteturalmente adequada** (orquestração do caso
  de uso, não no adapter).
- **ROB-008** (`gal_status_reconciler.py:33-34,58,92`): `_normalize_key_dates` aplicada
  **simetricamente** na leitura do journal e na construção da chave por linha (S23). Sem a simetria,
  amostras com data DD/MM/YYYY falhariam o match — a proteção fecha exatamente esse gap.
- **ROB-009** (`gal_payload_contract.py:86-90`): guard S24 contra `codigo` vazio, com semântica
  documentada (`codigo == codigoAmostra`) e exceção consciente para modo sem-metadados. Correto.
- **ROB-010** (`gal_status_reconciler.py:108,117-119`): fallback por `codigo_amostra` quando a
  chave kit/lote não é construível, evitando falso `sem_chave_gal`. Segunda-chave coerente.

## Discrepâncias semânticas

**Nenhuma.** Os dois `PARCIAL` da varredura automática foram falsos-negativos (ROB-007 buscado no
arquivo errado; ROB-001 medido contra um padrão de busca mais estrito que o requisito canônico).
Contra a definição de CLAUDE.md §16, **10/10 íntegros**.

## Follow-ups (não-bloqueantes, fora do escopo read-only da Fase 2)

1. **ROB-001 — observabilidade:** o handler de worker (`envio_gal.py:1045-1049`) loga só `str(e)`.
   Acrescentar `traceback.format_exc()`/`exc_info=True` melhoraria o diagnóstico. Sugestão de
   backlog; **não** é ausência da proteção.
2. **ROB-007 — coesão:** considerar centralizar a reserva de idempotência (inflight + successful)
   atrás de um pequeno serviço/port, facilitando teste sem Selenium (correlato a GAL-PEND-002).

## Veredito arquitetural

GAL-ROB-001..010 **consistentes e semanticamente íntegros**. Sem regressão atribuível ao incidente
2026-05-23. Nenhum `[CRITICAL_FINDING]`. Fase 2 pode prosseguir.
