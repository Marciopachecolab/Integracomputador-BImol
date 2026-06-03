# Constitution Delta — IntegRAGal (Auditoria 2026-05-31)

> **Status:** Delta complementar à `constitution.md` vigente. Adições/refinamentos derivados de 16 auditorias de pasta concluídas em 2026-05-31. Itens aqui têm a mesma força normativa da constitution principal e devem ser absorvidos na próxima rodada de governança formal.
>
> **Referência:** `specs/audit_refactoring/spec.md` para racionais detalhados.

---

## Adições por princípio

### §1.1 Fontes de Verdade (MUST) — Complemento
- **MUST** sincronizar declarações de "concluído" em SDD com presença física do artefato. Tarefas declaradas concluídas (`T-AUD-004A`, `T-AUD-008`) cujo artefato de teste/código não existe fisicamente no working tree são **violação de constituição** e devem ser tratadas como crítico.
- **MUST** atualizar `CLAUDE.md`/`AGENTS.md` simultaneamente. Guardião automatizado de paridade (hash match) é **MANDATÓRIO** (`tests/test_agents_claude_md_sha_match.py`).

### §2.1 Segurança (MUST) — Complemento
- **MUST NOT** versionar arquivos `.env*` mesmo com conteúdo inócuo. Renomear ou mover para fora do controle de versão.
- **MUST NOT** versionar arquivos `revert_info.txt`, `*.bak.*` ou outros outputs de ferramentas de AI em árvore versionada de produção.
- **MUST NOT** existir senha hardcoded em qualquer arquivo `.py` no repositório, incluindo scripts de smoke/debug. Único caminho permitido: variáveis de ambiente.
- **MUST** existir guardião automatizado contra `import psycopg2` ou `from psycopg2` em runtime (correlato a §3 e à proibição de PostgreSQL).
- **MUST** existir guardião automatizado contra `from analise`, `from extracao`, `from scratch`, `from sql` em runtime (pastas paralelas órfãs ou legados não-canônicos).

### §3.1 Fail-Closed (MUST) — Complemento
- **MUST** implementar lockout server-side (persistência em `usuarios.csv` ou backend equivalente) com política definida em DEC documentada. Lockout apenas client-side é **insuficiente** para produção multiusuário.
- **MUST** lançar exceção tipada em validações de payload GAL críticas (`gal_payload_contract.validate_gal_payload`) em vez de retornar lista de erros silenciosa.
- **MUST NOT** usar `@safe_operation` ou decorators equivalentes de captura genérica em operações de backup, persistência de config ou escrita atômica. Esses fluxos devem propagar exceções para que a camada de apresentação alerte o usuário.

### §4.1 SDD Operacional (SHOULD) — Complemento
- Mudanças em módulos com tag canônica `GAL-ROB-*`, `DASH-*`, `INST-*`, `LOG-UNIF-*` **MUST** ser registradas em `docs/specs/tasks.md` e `notas_de_passagem.md` no mesmo PR. Operações de revert silencioso são proibidas.
- Refactor de qualquer arquivo `>500 linhas` exige **cobertura prévia ≥ 70% do happy-path** registrada como guardião.

### §6.1 Design System UI (MUST) — Complemento
- **`ui/theme/design_tokens.py` é a ÚNICA fonte canônica.** `ui/modules/estilos/{cores,fontes}.py` é legado em deprecação controlada; **PROIBIDO** criar novos consumidores.
- Fallbacks inline de CORES/FONTES (ex.: `ui/modules/sistema_alertas.py:29-50`) **MUST** ser eliminados em rodada de unificação.
- Wildcard imports (`from X import *`) com supressão de linter (`# noqa: F401,F403`) são **PROIBIDOS** em qualquer módulo `ui/`.

### §7.1 Coesão services/ (MUST) — Complemento
- Top-level de `services/` **MUST** ter no máximo **15 arquivos** após T-AUD-010 fase 2. Acima disso, criar subdomínio Bounded Context.
- Cluster `operational_*` (12 arquivos) **MUST** ser consolidado em `services/operational/` em rodada coordenada.
- Arquivos `services/**/*.py` com `>1 000 linhas` **MUST** ter plano de decomposição registrado em `docs/specs/tasks.md` em ≤ 30 dias após detecção.

### §8.1 Deprecação Rigorosa (MUST) — Complemento
- Pastas paralelas órfãs identificadas em 2026-05-31 (`analise/`, `extracao/`, `scratch/`, `sql/`, `db/`) **MUST** receber DHP de destino em rodada conjunta de housekeeping.
- Workflows de deprecação iniciados com telemetria (ex.: `exportar_resultados_gal` + `report_exportar_resultados_usage.py`) **MUST** ter **critério de conclusão** registrado: janela de observação mínima + threshold de uso zero → ação documental + ação física.
- Arquivos `.bak.*` em pastas reguladas (`domain/`, `ui/`) **MUST** ser tratados em rodada de housekeeping com DHP. Política DEC-002/DEC-004 favorece arquivamento sobre exclusão.

### §9 (NOVO) — Higiene do Working Tree (MUST)
- **MUST NOT** existir arquivos no root do projeto sem categoria documentada em `CLAUDE.md §4` (estrutura principal).
- **MUST NOT** existir resíduos físicos de bugs corrigidos por rodadas SDD. Quando `CONFIG-PATH-001`, `LOG-UNIF-001/002` declaram "elimina pasta X", a eliminação física deve ser executada na mesma rodada (com DHP se necessário).
- **MUST NOT** existir cópias duplicadas de credenciais (`usuarios.csv` em múltiplos locais físicos). Drift de identidade é risco crítico.
- **MUST** distinguir entre `banco_template/` (esquema distribuível, versionado) e `banco_runtime/` (gerado, ignorado), conforme HIG-009.

### §10 (NOVO) — Telemetria de Suspected Orphans (MUST)
- Quando uma função é candidata a deprecação, **MUST** ser instrumentada com `log_suspected_orphan_usage` e ter script de auditoria correspondente.
- Após janela de observação ≥ 30 dias com uso runtime zero, **DEVE** ser executada DHP de remoção/arquivamento.

---

## Quadro de severidade dos achados (referência)

| Severidade | Definição | Exemplos |
|---|---|---|
| **CRÍTICO** | Quebra runtime, vazamento de credencial, prompt injection, drift de dados | csv_safety deletado; test_login senha hardcoded; revert_info prompt injection |
| **ALTO** | Bug provável, lacuna SDD declarada-mas-ausente, arquitetura paralela órfã | T-AUD-008 ausente; analise/ órfão; cadastros_ui 4 326L |
| **MÉDIO** | Dívida técnica documentada; duplicação; cobertura insuficiente | 3 design systems; 3 classificadores resultado; .bak em zona regulada |
| **BAIXO** | Limpeza cosmética; naming; comentários | df_debug legado; .env.txt naming |
| **INFORMATIVO** | Observação positiva ou contextual | main.py exemplar; LOG-UNIF cumprido |

---

## Vigência

Este delta vigora a partir de 2026-05-31. Próxima rodada de governança formal deve absorvê-lo em `constitution.md` consolidada e excluir este arquivo.
