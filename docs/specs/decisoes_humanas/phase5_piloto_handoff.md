# Handoff — Validação em Piloto da Fase 5 (Lockout Server-Side)

> Cópia canônica versionada. Uma cópia espelho (não versionada) existe em
> `snapshots/phase5_piloto_handoff.md` para leitura local.

## Implementação concluída

- **Branch:** refactor/audit-refactoring
- **Commits Fase 5:**
  - `e59f27f` docs(T-050): DHP politica senha/lockout aprovada
  - `d56e719` test(T-051a): cobertura previa auth_service (caracterizacao)
  - `b0a38a3` feat(T-051): lockout server-side em auth_service
  - `ad17ac0` test(T-052): persistencia de lockout (4 cenarios)
- **Mudança em produção:** `autenticacao/auth_service.py` (único `.py` de produção tocado)
- **Comportamento:** lockout server-side persistente (5 tentativas → 15 min, auto-desbloqueio)
- **Backend ativo:** `csv` (`config.json: storage_backend="csv"`) — suporta os campos
  `tentativas_falhas`/`bloqueado_ate`.

## Para o usuário titular

### 1. Smoke test manual

```powershell
git checkout refactor/audit-refactoring
python main.py  # tentar login com sua conta
```

Verificar:
- [ ] Login normal funciona.
- [ ] 5 senhas erradas em sequência bloqueiam a conta.
- [ ] Durante o bloqueio, mesmo a senha correta é recusada (mensagem genérica).
- [ ] Após 15 min, login com senha correta volta a funcionar (auto-desbloqueio).
- [ ] Admin consegue resetar tentativas_falhas de outro usuário via UI (matriz `users.mutate`).

### 2. Piloto (≥ 7 dias)

- Deploy em ambiente de piloto 3-5 usuários.
- Monitorar logs (`logs/`): linhas "Conta bloqueada por 15min..." e "Resultado da autenticacao: Falha".
- Critério de sucesso: **zero falsos-positivos** (usuário válido bloqueado por engano).

### 3. Após piloto verde

- Atualizar T-053 em `docs/specs/tasks.md` como `[x] Concluído`.
- Merge da branch em `main`.

## Limitações conhecidas a observar

- **T-051-FIND-SQLITE:** se `storage_backend` for trocado para `sqlite`, o lockout
  vira no-op (o adapter SQLite não persiste `failed_attempts`/`locked_until`).
  Manter `csv` até o adapter SQLite ser estendido. Ver `docs/specs/tasks.md`.
- **Concorrência (CONC/Fase 9):** incremento de contador não é totalmente atômico
  entre processos (possível undercount sob corrida). Aceitável no piloto 3-5;
  reavaliar em CONC-002..006.

## Rollback

Se o piloto detectar problema crítico:

```powershell
# Reverte testes e implementacao (ordem segura)
git revert ad17ac0   # T-052 testes
git revert b0a38a3   # T-051 implementacao
git revert d56e719   # T-051a caracterizacao
# (T-050 / e59f27f e' apenas documentacao da DHP; pode ser mantido)
```
