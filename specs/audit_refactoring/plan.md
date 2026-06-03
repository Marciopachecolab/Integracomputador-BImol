# Plan — Audit Refactoring (IntegRAGal)

> **Referência:** `specs/audit_refactoring/spec.md` (23 User Stories aprovadas).
>
> **Pré-leitura:** `.specify/memory/constitution.md` + `.specify/memory/constitution.delta.md`.
>
> **Status:** Plano aprovado para `/speckit.tasks`.

---

## 1. Arquitetura alvo (após refator)

### 1.1 Princípios de design

- **Hexagonal estrita**: `domain/` puro; `application/` orquestra com DTOs frozen + Protocols; `services/` adapters; `ui/` UI burra.
- **Single Source of Truth por contexto**: cada conceito (config, design system, taxonomia de resultado) tem um único módulo canônico.
- **Bounded Context em services/**: subpastas por contexto (`gal/`, `persistence/`, `reports/`, `equipment/`, `analysis/`, `engine/`, `core/`, `operational/` (novo), `legacy_audit/` (phase-out)). Top-level `services/*.py` ≤ 15 arquivos.
- **Fail-closed por default**: backups, persistência, validação de payload — exceções propagam para camada de apresentação.
- **Telemetria de deprecação**: workflow padronizado (instrumentar → observar 30 dias → DHP de remoção).

### 1.2 Camadas após refator (mapa-alvo)

```
domain/                                   (PURO — sem alteração estrutural)
application/                              (canônico — sem alteração estrutural)
services/
├─ core/                                  (config_service singleton + runtime_flags + DI)
├─ analysis/                              (analysis_service decomposto: carga, motor, estado, relatório)
├─ engine/                                (analysis_engine, data_cleaner, config_loader hardened)
├─ equipment/                             (DEC-006 — sem alteração)
├─ gal/                                   (GAL-ROB — sem alteração estrutural)
├─ persistence/                           (persistence_adapters decomposto: 1 arquivo/contrato)
├─ reports/                               (DASH — absorve salvar_historico_processamento de db/)
├─ operational/                           (NOVO — consolida 12 operational_* arquivos)
└─ legacy_audit/                          (PHASE-OUT com deadline registrado)

ui/
├─ main_window.py                         (entry point — sem alteração)
├─ modules/
│  ├─ cadastros_ui.py                     (facade ≤ 400 L)
│  ├─ cadastros_exames.py                 (NOVO — ExamCRUDEditor)
│  ├─ cadastros_equipamentos.py           (NOVO — EquipmentCRUDEditor)
│  ├─ cadastros_placas.py                 (NOVO — PlateCRUDEditor)
│  ├─ cadastros_regras.py                 (NOVO — RuleCRUDEditor)
│  └─ ... (demais módulos sem alteração estrutural)
├─ components/                            (canônico)
└─ theme/                                 (Blueprint canônico)

utils/
├─ csv_safety.py                          (RESTAURADO ou substituído por services/persistence/csv_io)
├─ error_handler.py                       (safe_operation com propagate_critical)
├─ logger.py / csv_lock.py / etc.         (sem alteração)
└─ gui_utils.py                           (sem import de db.db_utils)

config/                                   (sem alteração estrutural; tasks médias deferidas)

scripts/                                  (paths refatorados; sem hardcoded Downloads)

tests/
├─ test_dominio_imports_puros.py          (T-AUD-008 RECRIADO)
├─ test_auth_legacy_user_manager_no_runtime_imports.py  (T-AUD-004A RECRIADO)
├─ test_agents_claude_md_sha_match.py     (NOVO — E3 root)
├─ test_no_broken_csv_safety_imports.py   (NOVO — AC-1.3)
├─ test_no_hardcoded_credentials.py       (NOVO — AC-2.4)
├─ test_usuarios_csv_single_canonical_path.py (NOVO — AC-4.3)
├─ test_no_psycopg2_imports.py            (NOVO — AC-10.3)
├─ test_no_bak_files_in_runtime.py        (NOVO — AC-12.3)
├─ test_scripts_no_hardcoded_paths.py     (NOVO — AC-13.2)
├─ test_safe_operation_propagates_critical.py (NOVO — AC-18.3)
├─ test_utils_no_db_imports.py            (NOVO — AC-19.3)
├─ test_initial_setup_wizard_e2e.py       (NOVO — AC-20.2)
├─ test_auth_lockout_persistence.py       (NOVO — AC-7.5)
├─ test_*_import_ban_orphan_packages.py   (5x: analise, extracao, scratch, sql, db — AC-8.3)
├─ test_dados_dados_nao_recriado.py       (NOVO — AC-9.3)
├─ test_cadastros_smoke_*.py              (NOVO — AC-5.1 cobertura prévia)
├─ test_distributable_first_boot.py       (NOVO — AC-23.3)
├─ test_persistence_multiprocess_10_users.py (NOVO — AC-22.1)
├─ test_gal_claim_lease.py                (NOVO — AC-22.2)
└─ ... existentes

docs/obsoletos/                           (DESTINO de pastas órfãs + .bak + revert_info)
├─ legacy_packages/
│  ├─ analise/                            (movido após DHP-13)
│  ├─ extracao/                           (movido)
│  ├─ scratch/                            (movido)
│  ├─ sql/                                (movido)
│  └─ db/                                 (movido após migração de callers)
├─ refactor_attempts/
│  ├─ ui_menu_handler_moderniza.bak       (movido)
│  └─ domain_ct_rules_runtime_target_recalc_fix.bak (movido)
└─ incidents/
   └─ revert_envio_gal_20260523.txt       (movido revert_info.txt + README)

snapshots/
├─ dados_residue_20260531/                (resíduo dados/dados/, dados/logs/ se decidido mover)
├─ sdd_consistency_audit_20260531.md      (resultado US-15)
└─ ...

(root limpo)
├─ main.py / models.py / conftest.py / pytest.ini
├─ requirements.txt (sem psycopg2)
├─ Integragal.spec (ajustado)
├─ README.md / CLAUDE.md / AGENTS.md / notas_de_passagem.md
├─ .gitignore / .gitattributes / .editorconfig
├─ config.json (template — política definida)
└─ pythonpath.env (renomeado de .env.txt)
```

### 1.3 Padrões de design adotados

| Padrão | Aplicação | Onde |
|---|---|---|
| **Guardião AST de import-ban** | Pastas órfãs + dependências proibidas | tests/ — 7 novos guardiões |
| **Guardião AST de pureza de camada** | domain/, utils/ | tests/test_dominio_imports_puros.py + test_utils_no_db_imports.py |
| **Strangler pattern** | Cadastros_ui split (facade delega para editores progressivamente) | ui/modules/cadastros_ui.py |
| **Telemetria de deprecação** | exportar_resultados_gal | já implementado; falta critério de conclusão |
| **DHP coordenada** | Pastas paralelas órfãs (DHP-13) | docs/specs/tasks.md |
| **Write-atomic + lock** | Lockout persistência | autenticacao/auth_service.py (já tem padrão csv_io + CSVFileLock) |
| **Fail-closed assertion** | validate_gal_payload, _validar_corrida | Substituir fallback silencioso por raise |
| **Hash match guardian** | AGENTS.md ≡ CLAUDE.md | tests/test_agents_claude_md_sha_match.py |

### 1.4 Decisões arquiteturais (ADRs implícitas)

- **ADR-A1** — Restaurar `csv_safety.py` em vez de inline-em-cada-caller. Razão: 10 callers + segurança CSV injection + simplicidade.
- **ADR-A2** — Lockout server-side via persistência em `usuarios.csv` (mesmo schema atual). Razão: campos já existem; bcrypt já correto; minimal change.
- **ADR-A3** — Arquivar pastas órfãs em `docs/obsoletos/` (NÃO remover). Razão: política DEC-002/DEC-004 favorece preservação; permite recuperação.
- **ADR-A4** — Decompor cadastros_ui com facade-strangler. Razão: 4 326 L exige refator gradual sem big-bang; facade preserva API pública.
- **ADR-A5** — `services/operational/` como NOVA subpasta. Razão: cluster `operational_*` já existe semanticamente; falta reflexo estrutural.
- **ADR-A6** — Lockout server-side primeiro; modernização UI depois. Razão: segurança > UX em ordem de prioridade.
- **ADR-A7** — `db/db_utils.salvar_historico_processamento` migra para `services/reports/history_report` antes de arquivar `db/`. Razão: 4 callers ativos; migração é pré-requisito de arquivamento.

---

## 2. Estratégia técnica (para não quebrar produção)

### 2.1 Princípio de "ordem de fases"

A refatoração segue 8 fases sequenciais. **Cada fase só inicia após a anterior ter critérios de aceite cumpridos**.

```
Fase 0 — EMERGÊNCIA (CRÍTICO, ~1 dia)
   └→ Restaurar csv_safety + remediar test_login + arquivar revert_info

Fase 1 — GUARDIÕES SDD AUSENTES (CRÍTICO, ~0,5 dia)
   └→ Recriar T-AUD-008 + T-AUD-004A + AGENTS≡CLAUDE

Fase 2 — INVESTIGAÇÃO FORENSE (CRÍTICO, ~1 dia)
   └→ Análise do revert envio_gal + confirmar GAL-ROB íntegros

Fase 3 — HOUSEKEEPING ROOT (ALTO, ~1 dia)
   └→ Limpar root: lixo, .env.txt, .bak, requirements

Fase 4 — IMPORT-BAN DE ÓRFÃOS (ALTO, ~1 dia, paralelo possível)
   └→ Guardiões AST para 5 pastas órfãs

Fase 5 — POLÍTICA DE SENHA/LOCKOUT (ALTO, ~3 dias)
   └→ DHP + implementação + testes + validação em piloto

Fase 6 — FAIL-CLOSED & SUPER-ARQUIVO (ALTO, ~5 dias)
   └→ Endurecer safe_operation + validate_gal_payload + split cadastros_ui

Fase 7 — MIGRAÇÃO DE db/ + ARQUIVAMENTO DE ÓRFÃOS (ALTO, ~2 dias)
   └→ Mover salvar_historico_processamento + arquivar 5 pastas

Fase 8 — DECOMPOSIÇÃO services/ (ALTO, ~7 dias)
   └→ T-AUD-010 fase 2: analysis_service + persistence_adapters

Fase 9 — PRÉ-REQUISITOS 10 USUÁRIOS (ALTO, ~5 dias)
   └→ CONC-002..006 + INST-004/005 + reavaliar LIM-004
```

**Estimativa total agregada:** ~25-30 dias úteis em ritmo focado. Tarefas marcadas `[P]` podem ser executadas em paralelo dentro da mesma fase.

### 2.2 Salvaguardas por fase

| Fase | Salvaguarda principal |
|---|---|
| 0 | Backup do working tree atual em snapshot antes de restaurar csv_safety. |
| 1 | Testes novos passam ANTES de declarar fase concluída. |
| 2 | Documentação forense em `docs/specs/tasks.md` como T-AUD-016 antes de qualquer mudança. |
| 3 | Cada arquivo movido tem backup em snapshot. Lista versionada em `snapshots/root_cleanup_20260531_manifest.md`. |
| 4 | Guardiões com **allowlist explícita** para evitar falsos positivos (ex.: docs/obsoletos/). |
| 5 | Lockout ativado apenas após validação em ambiente isolado; flag de rollback. |
| 6 | Cobertura prévia ≥ 70% do happy-path em smoke tests ANTES de decomposição. Strangler-pattern: facade preserva API. |
| 7 | Migração de db_utils → history_report tem teste de regressão dos 4 callers. |
| 8 | Cada arquivo gigante refatorado mantém imports públicos via `__init__.py` (preservar superfície). |
| 9 | Testes de concorrência em ambiente staging antes de produção. |

### 2.3 Rollback strategy

- **Estado pré-refator:** snapshot completo em `snapshots/pre_audit_refactor_20260531/` (criar antes da Fase 0).
- **Rollback granular por fase:** cada fase tem seu commit gate; reverter fase X é `git revert <commit-fase-X>`.
- **Rollback de DHPs aprovadas:** documentar em `docs/specs/decisoes_humanas/DHP-XX.md` com seção "Reversão" se aplicável.

### 2.4 Comunicação com stakeholders

- **Antes da Fase 0:** alerta ao time sobre estado incoerente do working tree (csv_safety).
- **Após Fase 5:** comunicação sobre nova política de senha/lockout aos usuários piloto.
- **Após Fase 7:** anúncio do arquivamento de `analise/`, `extracao/`, `scratch/`, `sql/`, `db/`.

---

## 3. Mapping AC → componente técnico

| AC | Componente | Tipo de mudança |
|---|---|---|
| AC-1.1, AC-1.2 | utils/csv_safety.py | RESTAURAÇÃO (git checkout HEAD^) |
| AC-1.3 | tests/test_no_broken_csv_safety_imports.py | NOVO guardião |
| AC-2.1 | test_login.py | REMEDIAÇÃO ou DELEÇÃO |
| AC-2.2 | docs/obsoletos/incidents/ | NOVA pasta + MOVE |
| AC-2.3 | docs/specs/tasks.md T-AUD-016 | NOVA tarefa documentada |
| AC-2.4 | tests/test_no_hardcoded_credentials.py | NOVO guardião |
| AC-3.1 | tests/test_dominio_imports_puros.py | NOVO (RECRIA T-AUD-008) |
| AC-3.2 | tests/test_auth_legacy_user_manager_no_runtime_imports.py | NOVO (RECRIA T-AUD-004A) |
| AC-3.3 | tests/test_agents_claude_md_sha_match.py | NOVO |
| AC-4.1 | snapshots/lgpd_audit_usuarios_csv.md | DHP + DOCUMENTO |
| AC-4.2 | snapshots/dados_legacy_20260531/ | MOVE cópias secundárias |
| AC-4.3 | tests/test_usuarios_csv_single_canonical_path.py | NOVO guardião |
| AC-5.1 | tests/test_cadastros_smoke_*.py | NOVO (cobertura prévia) |
| AC-5.2 | ui/modules/cadastros_*.py | SPLIT (facade-strangler) |
| AC-5.3 | Validação manual | TESTE de aceitação |
| AC-6.1 | exportacao/gal_payload_contract.py | NOVA função assert_valid_gal_payload |
| AC-6.2 | exportacao/envio_gal.py | UPDATE chamar assert_valid_* |
| AC-6.3 | config/settings.py | REFACTOR substituir @safe_operation em pontos críticos |
| AC-6.4 | analise/vr1e2_biomanguinhos_7500.py:113-115 | UPDATE return value (mas pasta vai ser arquivada — coordenar) |
| AC-7.x | autenticacao/auth_service.py | MAJOR FEATURE (lockout server-side) |
| AC-8.1 | docs/specs/decisoes_humanas/DHP-13.md | DHP COORDENADA |
| AC-8.2 | docs/obsoletos/legacy_packages/{analise,extracao,scratch,sql,db}/ | MOVE pastas |
| AC-8.3 | tests/test_*_import_ban_orphan_packages.py | 5 NOVOS guardiões |
| AC-8.4 | services/reports/history_report.py | NOVA função salvar_historico_processamento + migração 4 callers |
| AC-9.1-3 | docs/specs/decisoes_humanas/DHP-cleanup-dados.md | DHP + MOVE + guardião |
| AC-10.1-3 | requirements.txt + sql/requirements.txt | UPDATE/DELETE + guardião |
| AC-11.x | root cleanup | MOVE + RENAME |
| AC-12.x | docs/obsoletos/refactor_attempts/ | MOVE .bak |
| AC-13.x | scripts/*.{py,ps1,cmd} | REFACTOR paths |
| AC-14.x | services/analysis/*.py + services/persistence/*.py | SPLIT |
| AC-15.x | snapshots/sdd_consistency_audit_20260531.md | AUDITORIA AUTOMATIZADA |
| AC-16.x | tests/test_agents_claude_md_sha_match.py | NOVO guardião |
| AC-17.x | exportacao/exportar_resultados.py | DELETE bloco morto |
| AC-18.x | utils/error_handler.py | UPDATE safe_operation |
| AC-19.x | services/reports/history_report.py + utils/gui_utils.py | MIGRAÇÃO |
| AC-20.x | ui/admin_initial_setup.py + tests/ | UPDATE + NOVO TESTE |
| AC-21.x | git log analysis + docs/specs/tasks.md | FORENSICS + DOCUMENTAR |
| AC-22.x | tests/test_*_10_users.py | NOVOS TESTES de concorrência |
| AC-23.x | Integragal.spec + tests/test_distributable_first_boot.py | UPDATE + NOVO TESTE |

---

## 4. Critérios de "Done" por fase

### Fase 0 Done quando:
- `python -c "from utils.csv_safety import sanitize_csv_value"` retorna sem erro.
- `test_login.py` ou refatorado ou removido.
- `revert_info.txt` movido para `docs/obsoletos/incidents/`.

### Fase 1 Done quando:
- 3 guardiões novos passam em CI: T-AUD-008, T-AUD-004A, AGENTS≡CLAUDE hash.

### Fase 2 Done quando:
- T-AUD-016 (forensics revert) registrada em `tasks.md`.
- GAL-ROB-001..010 reconfirmados via inspeção de envio_gal.py.

### Fase 3 Done quando:
- Root tem ≤ 18 arquivos (todos em `CLAUDE.md §4`).
- requirements.txt sem psycopg2.
- 2 guardiões: no_hardcoded_credentials + no_psycopg2_imports.

### Fase 4 Done quando:
- 5 guardiões de import-ban passam (analise, extracao, scratch, sql, db).

### Fase 5 Done quando:
- DHP "política de senha/lockout" aprovada.
- `tests/test_auth_lockout_persistence.py` passa.
- Piloto 3-5 usuários validou comportamento por ≥ 7 dias.

### Fase 6 Done quando:
- `assert_valid_gal_payload` integrado em envio_gal.
- `safe_operation` com `propagate_critical=True` em config/settings backup+salvar.
- `cadastros_ui.py` decomposto em ≥ 4 arquivos; cobertura ≥ 70% validada.

### Fase 7 Done quando:
- `salvar_historico_processamento` em `services/reports/history_report.py`; 4 callers migrados.
- 5 pastas órfãs movidas para `docs/obsoletos/legacy_packages/`.
- Guardiões de import-ban da Fase 4 continuam passando.

### Fase 8 Done quando:
- `services/analysis/analysis_service.py` decomposto em ≤ 4 sub-módulos.
- `services/persistence/persistence_adapters.py` decomposto.
- Cobertura mínima por sub-módulo registrada.

### Fase 9 Done quando:
- CONC-002, CONC-003, CONC-005, CONC-006 com testes passando.
- INST-004 + INST-005 concluídos.
- LIM-004 atualizada em `docs/specs/design.md`.

---

## 5. Análise de impacto

### 5.1 Mudanças por superfície

| Camada | Arquivos tocados | Impacto |
|---|---:|---|
| `utils/` | 4 (csv_safety, error_handler, gui_utils, novo) | Médio |
| `autenticacao/` | 1 (auth_service) | Alto (feature lockout) |
| `services/` | 5 (history_report, runtime_flags, error_handler-equivalente, splits) | Alto |
| `application/` | 0 (sem alteração estrutural) | Nenhum |
| `domain/` | 0 (sem alteração estrutural) | Nenhum |
| `ui/` | 5+ (cadastros_ui split, admin_initial_setup) | Alto (decomposição) |
| `exportacao/` | 3 (gal_payload_contract, envio_gal, exportar_resultados) | Médio |
| `config/` | 1 (settings.py — safe_operation) | Baixo |
| `scripts/` | 6+ (paths) | Médio |
| `tests/` | 18+ (todos novos guardiões + smoke) | Alto |
| `docs/` | 3 (specs/tasks, obsoletos/, snapshots/) | Médio |
| Root | 8 (cleanup) | Médio |
| `dados/` | Pasta inteira (movidas/arquivadas) | Alto operacional |

### 5.2 Risco vs benefício

- **Maior risco**: Fase 6 (split cadastros_ui + endurecer safe_operation) — toca UI viva e config crítica.
- **Maior benefício**: Fase 5 (lockout server-side) — desbloqueia produção 10 usuários.
- **Risco aceitável vs valor entregue**: alto em todas as fases — mas a alternativa (manter status quo) carrega risco operacional crescente.

---

## 6. Cronograma indicativo

```
Semana 1: Fases 0-2 (Emergência, Guardiões, Forensics)
Semana 2: Fases 3-4 (Housekeeping root, Import-ban órfãos)
Semana 3: Fase 5 início (Política senha + impl técnica)
Semana 4: Fase 5 conclusão (Piloto validação) + Fase 6 início (fail-closed)
Semana 5: Fase 6 conclusão (cadastros_ui split)
Semana 6: Fases 7-8 início (migração + decomposição services)
Semana 7: Fase 8 conclusão + Fase 9 início (CONC)
Semana 8: Fase 9 conclusão + comunicação produção
```

(Estimativa em ritmo focado; adaptável a equipe disponível e velocidade SDD.)
