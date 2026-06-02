# DHP — Política de Senha e Lockout Server-Side

**Data:** 2026-06-02
**Origem:** Fase 5 Audit Refactoring (T-050)
**Decisão por:** Marciopachecolab (usuário titular)
**Status:** [x] Aprovada

## Contexto

Auditoria 2026-05-31 identificou que `autenticacao/auth_service.py`:
- Schema CSV reserva campos `tentativas_falhas` e `bloqueado_ate`
  (L67-68) — lidos para construir DTO (L520-521) — mas **NUNCA escritos**
  em `autenticar_credenciais` (L667-743).
- Throttling existe APENAS em `autenticacao/login.py` (MAX_TENTATIVAS=3)
  em MEMÓRIA — reset a cada init.
- Resultado: brute-force viável em produção 10 usuários (LIM-004).

## Decisão

Implementar lockout server-side conforme parâmetros abaixo.

## Parâmetros

| Parâmetro | Valor | Constante |
|---|---|---|
| Máximo de tentativas falhas | 5 | `MAX_TENTATIVAS_FALHAS = 5` |
| Duração do bloqueio | 15 minutos | `BLOQUEIO_DURACAO_MINUTOS = 15` |
| Auto-desbloqueio | Sim (após expiração de `bloqueado_ate`) | — |
| Recuperação admin | Via UI (matriz `users.mutate` em access_control) | — |
| Comprimento mínimo de senha | 8 caracteres | já em uso no legado |
| Complexidade extra | Deferida para Fase 9 | — |
| Hash | bcrypt | mantido (sem migração) |
| Feedback UI no bloqueio | Mensagem genérica `"Credenciais inválidas. Verifique usuário e senha."` (OWASP A07) | — |

## Comportamento detalhado

### Em `autenticar_credenciais(usuario, senha_fornecida)`:

1. **Carregar registro do usuário** (`load_users_df`).
2. **Se `bloqueado_ate` > `now()`**: retornar `None` imediatamente
   (sem validar bcrypt — evita timing leak e enumeração).
3. **Validar senha via `bcrypt.checkpw`**:
   - **Sucesso**: zerar `tentativas_falhas = 0`, limpar `bloqueado_ate = ""`,
     atualizar `ultimo_acesso`, persistir sob lock, retornar dict.
   - **Falha**: incrementar `tentativas_falhas += 1`. Se atingir
     `MAX_TENTATIVAS_FALHAS`: setar `bloqueado_ate = now() + BLOQUEIO_DURACAO`.
     Persistir sob lock. Retornar `None`.

### Atomicidade

Toda escrita do estado de tentativas/bloqueio é roteada por
`AuthService.save_users_df(df, system_operation=True)` → contrato de
persistência (`_save_users_df_via_contract`), que persiste via
`CsvUserRepositoryAdapter`/`_CsvStore.write_rows` sob `CSVFileLock`
(ou via backend SQLite quando configurado). O fallback CSV direto
(`_save_users_df_via_csv`) usa `write_csv_atomic` + `CSVFileLock`.
Padrões canônicos já presentes em `services/persistence/`.

> **Nota de design:** a recomendação inicial citava `write_csv_atomic(path, df)`
> direto no helper. A assinatura real de `write_csv_atomic` é
> `(path, *, rows, fieldnames, contract_name, policy)` e bypassaria o backend
> de persistência (quebraria SQLite). Por isso a persistência é roteada pelo
> contrato canônico `save_users_df`, que preserva lock + atomicidade e o
> backend configurado.

### Mensagem UI

Sempre retorna `None` em qualquer falha. A camada UI (`autenticacao/login.py`)
exibe SEMPRE `"Credenciais inválidas. Verifique usuário e senha."` —
independente do motivo (senha errada, usuário inexistente, bloqueio ativo).

## Critérios de aceite

Ver `specs/audit_refactoring/spec.md` US-7 (AC-7.1..5).

## Validação em piloto

Após implementação, validar em piloto 3-5 usuários por ≥ 7 dias antes
de habilitar em produção. Critério: zero incidentes de falso-positivo
(usuário válido bloqueado por engano).

## Reversibilidade

Em caso de falha em piloto, reverter via:
- `git revert <SHA-T-051>` (reverte implementação).
- Re-executar fase com parâmetros ajustados.

## Referências

- specs/audit_refactoring/spec.md US-7
- specs/audit_refactoring/plan.md Fase 5
- docs/specs/tasks.md T-050..T-053
- .specify/memory/constitution.delta.md §3.1 (lockout MUST), §2.1 (OWASP)
- OWASP A07: Identification and Authentication Failures
