# Forensics — Verificação GAL-ROB-001..010 em `envio_gal.py` atual

- **Data da análise:** 2026-06-01T20:55:00Z
- **Origem:** Fase 2 Audit Refactoring (T-022 etapa 1)
- **Método:** subagente `Explore` (READ-ONLY) + **verificação direta** (Read/Grep) dos itens contestados
- **Referência canônica:** CLAUDE.md §16 (GAL-ROB-001..010, concluídos 2026-05-30)

## Resultado consolidado (após verificação direta)

| ID | Arquivo:linha | Evidência | Status |
|---|---|---|---|
| GAL-ROB-001 | `exportacao/envio_gal.py:1045-1049` | `except Exception as e:` → `status="erro_critico"` + `resultado["erro"].append(...)` + `self.log(..., "critical")` | **OK** † |
| GAL-ROB-002 | `exportacao/envio_gal.py:683-698` | `failed_pages` acumula erros mas o fluxo NÃO aborta o lote | **OK** |
| GAL-ROB-003 | `exportacao/envio_gal.py:693-697` | `self.log("[S5] AVISO: ... pagina(s) de metadados nao carregaram", "warning")` com `len(failed_pages)` | **OK** |
| GAL-ROB-004 | `application/gal_send_use_case.py:177-198` | `ler_csv_resultados()` chamado ANTES de `driver = self._webdriver_factory()` | **OK** |
| GAL-ROB-005 | `application/gal_send_use_case.py:186-195` | `if exam_cfg and not gal_exame_codigo:` → `_service_log("[S11] AVISO: exame sem gal_exame_codigo", "warning")` | **OK** |
| GAL-ROB-006 | `exportacao/envio_gal.py:1005-1015` | `_SENSITIVE_KEYS = frozenset((...))` + `safe_response = {k: ("***" if k in _SENSITIVE_KEYS else v) ...}` antes do log | **OK** |
| GAL-ROB-007 | `application/gal_send_use_case.py:273-314` | `threading.Lock()` + `inflight_keys: Set[str]` + reserva atômica check-then-send sob `with lock:` (S22) | **OK** ‡ |
| GAL-ROB-008 | `services/gal/gal_status_reconciler.py:29-35,58,88-92` | `_normalize_key_dates()` DD/MM/YYYY→YYYY-MM-DD aplicada simetricamente (carregar journal + construir key) | **OK** |
| GAL-ROB-009 | `exportacao/gal_payload_contract.py:79-90` + `construir_payload` | guard contra `codigo` vazio + fallback `codigoAmostra` | **OK** |
| GAL-ROB-010 | `services/gal/gal_status_reconciler.py:108,115-121` | `codigo_fallback` + match por `codigo_amostra` como segunda chave | **OK** |

## Veredito

**10 OK / 0 PARCIAL / 0 AUSENTE.** Todas as 10 proteções GAL-ROB declaradas em CLAUDE.md §16
estão presentes e semanticamente íntegras no estado atual. **Nenhum `[CRITICAL_FINDING]`.**

## Correções a dois falsos-negativos da varredura automática inicial

O subagente Explore reportou inicialmente GAL-ROB-001 e GAL-ROB-007 como `PARCIAL`. Verificação
direta refuta ambos:

### ‡ GAL-ROB-007 — falso-negativo por arquivo errado
A varredura procurou `inflight_keys` em `exportacao/envio_gal.py` e não encontrou. A implementação
canônica está na **camada de orquestração** (`application/gal_send_use_case.py:273-314`), que é o
local arquiteturalmente correto (application orchestra o caso de uso). Código verificado:
```
273  lock = threading.Lock()
279  inflight_keys: Set[str] = set()
305  with lock:
306-309  if idempotency_key in successful_keys or ... in inflight_keys: -> duplicado
310-314  else: inflight_keys.add(idempotency_key); inflight_keys.add(legacy_idempotency_key)
```
Comentário S22 no código: "Chaves em voo — impede envio duplo de linhas idênticas no mesmo CSV.
O check-then-send é tornado atômico". Corresponde EXATAMENTE à descrição canônica de GAL-ROB-007.
**Status real: OK.**

### † GAL-ROB-001 — definição canônica satisfeita; traceback é follow-up não-bloqueante
A descrição canônica (CLAUDE.md §16) é "exceção de worker registrada estruturadamente". O handler
`envio_gal.py:1045-1049` satisfaz isto: captura `Exception`, registra status estruturado
(`erro_critico`), anexa mensagem ao campo estruturado `resultado["erro"]`, e loga em nível
`critical`. O lote não é derrubado pela exceção (retorna `resultado`). O padrão "traceback completo"
foi um hint adicional do prompt de busca, **não** parte do requisito canônico.
**Status real: OK.**

> **Follow-up não-bloqueante (observação, não achado):** o handler loga apenas `str(e)`, sem
> `traceback.format_exc()`/`exc_info=True`. Diagnóstico de exceções de worker perde o stack trace.
> Melhoria opcional de observabilidade — sugerir para backlog (não bloqueia Fase 2; fora do escopo
> read-only). Não constitui ausência da proteção GAL-ROB-001.
