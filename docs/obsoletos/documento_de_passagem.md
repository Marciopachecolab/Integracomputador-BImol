# Documento de Passagem

Handoff transitorio entre agentes (Claude Code -> Codex CLI ou equivalente). Use este documento para retomar trabalho no projeto IntegRAGal sem refazer auditoria.

Data desta passagem: 2026-05-15.

> **Nota de leitura:** Este documento e um log cronologico de handoff. Secoes datadas de 2026-05-13 e 2026-05-14 refletem o estado **naquele momento** e podem listar DHPs como pendentes que ja foram resolvidas depois. O estado canonico atual deve ser lido nas secoes mais recentes (§7.2, §23 em diante) e confirmado em `AGENTS.md §15` e `docs/specs/tasks.md §10`.

## 1. Objetivo da sessao

Consolidar a governanca multiagente apos a auditoria SDD READ-ONLY (Fase 1 - 2026-05-12), a reescrita documental (Fase 2 - 2026-05-13) e a sincronizacao SDD pre-higienizacao (2026-05-14). A sessao atual atualizou apenas documentacao Markdown permitida para refletir tarefas tecnicas ja executadas, corrigir divergencias sobre DT-001/pandas e registrar lacunas UI-AUD/HIG antes da auditoria de higienizacao. Nenhuma alteracao de codigo, teste, configuracao operacional, CSV, DB, snapshot, report ou log foi realizada.

## 2. Estado atual do trabalho

- Fase 1 (auditoria SDD READ-ONLY): concluida em 2026-05-12. Produziu `structure.map` + Relatorio de Divergencias com D-01..D-12, L-T01..L-T05, R-T1..R-T5, DH-01..DH-09. Resultado: PRONTO PARA FASE 2.
- Fase 2 (reescrita SDD): concluida em 2026-05-13. Atualizou `docs/specs/requirements.md`, `docs/specs/design.md` e `docs/specs/tasks.md`. Checagem confirmou escopo respeitado: PRONTO PARA FASE 3.
- Fase 3 (governanca multiagente): executada nesta rodada (2026-05-13).
- Codigo: nao alterado em nenhuma das tres rodadas.
- `config.json`: nao alterado nas tres primeiras rodadas; corrigido posteriormente em T-AUD-008-CFG apenas para remover chave vazia e corrigir mojibake, preservando template/local runtime.
- Sincronizacao SDD pre-higienizacao (2026-05-14): concluida em Markdown. Incorporou `SDD-20260514-001`, `SDD-20260514-002`, `SDD-20260514-003`, `UI-AUD-002`, `UI-AUD-001`, `UI-AUD-003`, `HIG-001` e `HIG-002`; corrigiu referencias antigas em `design.md`, `AGENTS.md` e `CLAUDE.md`.
- Atualizacao documental pos-auditoria multiusuario/instalacao (2026-05-15): concluida em Markdown. Registrou multiusuario como **APTO COM RESTRICOES**, instalacao como **FUNCIONAL COM RESTRICOES**, e criou backlog CONC/INST sem alterar codigo, testes, `config.json` ou artefatos.

## 3. Arquivos atualizados nesta rodada documental

- `docs/specs/tasks.md` - tarefas recentes de 2026-05-14 e lacunas UI-AUD/HIG registradas.
- `docs/specs/design.md` - DT-001/pandas corrigida para status resolvido; semanticas recentes documentadas.
- `AGENTS.md` - listas antigas de T-AUD pendentes corrigidas; tarefas concluidas marcadas como nao repetir.
- `CLAUDE.md` - sincronizado, identico a `AGENTS.md` (regra canonica do projeto).
- `documento_de_passagem.md` - atualizado para continuidade em Claude Code/Codex CLI sem reabrir tarefas concluidas.
- `notas_de_passagem.md` - entrada curta adicionada com resumo da sincronizacao.
- `inventario_de_lixo.md` - candidatos HIG recentes registrados sem autorizacao de remocao.
- `docs/specs/ui_inventory.md` - esqueleto curto criado; inventario completo ainda a elaborar.
- `docs/specs/higienizacao_implantacao.md` - esqueleto curto criado; auditoria de higienizacao ainda nao executada.

## 4. Fontes da verdade atuais

- `docs/specs/requirements.md` - fonte de requisitos, CA-01..CA-12, CA-R01..CA-R10, GAP/BUG/TEST/DEC.
- `docs/specs/design.md` - fonte de arquitetura, fluxos, DT-001..DT-003, LIM-001..LIM-003.
- `docs/specs/tasks.md` - plano rastreavel com T01..T24, E01..E07, R01..R10 e T-AUD-001..T-AUD-013.
- `docs/specs/equipment_legacy_deprecation.md` - **fonte canonica da deprecacao controlada** dos legados de equipamentos (DEC-006 resolvida na microfase 3.1).
- `docs/specs/plano_equipamentos_sdd.md` - **documento historico-orientador** das fases SDD de equipamentos, subordinado a `docs/specs/tasks.md §7` (DEC-006 resolvida na microfase 3.1).
- `AGENTS.md` / `CLAUDE.md` - bussola operacional para agentes de IA.

## 5. Principais achados consolidados

Resumo operacional, agrupado por tema. Detalhes completos em `requirements.md §10`, `design.md §§3.6-3.7, 8-10` e `tasks.md §10`.

- **Arquitetura**: `domain/ct_rules.py` nao importa mais `pandas` apos T-AUD-001; `services/` concentra dezenas de modulos com alto custo cognitivo (DT-002 / R-T3).
- **Configuracao**: DEC-001 resolveu que `config.json` versionado e template/local runtime nao pronto para producao; ambientes produtivos exigem configuracao local validada com `shared_storage.root`, `data_root` e `allowed_roots` preenchidos. T-AUD-008-CFG foi concluida: chave vazia removida de `general`, mojibake de `lab_responsible` corrigido, JSON/UTF-8 validado e template/local runtime preservado sem dados reais sensiveis.
- **GAL**: dual-key (legada 4 campos + escopo 4+N) confirmada em codigo. Cenario "match apenas pela chave legada" (CA-11 / D-07 / L-T01) coberto por teste equivalente pre-existente validado em T-AUD-007.
- **Equipamentos**: E01..E07 marcadas concluidas. Decisao operacional sobre legado e "deprecacao controlada" documentada em `equipment_legacy_deprecation.md`. Arquivos `banco/equipamentos.csv`, `banco/equipamentos_metadata.csv`, `banco/profiles/equipment_profiles.json` permanecem fisicamente presentes (LIM-003 / D-11).
- **Autenticacao**: DEC-003 resolveu que `core/authentication/user_manager.py` e modulo legado em deprecacao controlada. O fluxo ativo reconhecido e `autenticacao/auth_service.py` + `autenticacao/login.py`, com matriz de autorizacao em `application/access_control.py`. T-AUD-004B neutralizou a execucao direta do legado sem remocao fisica.
- **Higiene de repositorio**: `snapshots/encoding_backup_*` contem >12 diretorios historicos de backup/encoding classificados por DEC-004; `relatorio_final_corrida_*.json` na raiz do projeto foi classificado por DEC-005 (D-05 / D-06). Nenhum desses artefatos entra no release operacional.
- **Documentacao humana**: `README.md` humano e operacional criado na raiz em 2026-05-15 conforme DEC-007.
- **Testes/Configuracao**: lacunas L-T01, L-T02, L-T03, L-T05 e L-T06 foram fechadas por T-AUD-007, T-AUD-003, T-AUD-008, T-AUD-008-CFG e T-AUD-014. T-AUD-004A concluiu o guardiao de nao uso runtime de `core.authentication.user_manager`; T-AUD-004B concluiu a neutralizacao do `__main__`; L-T04 ainda tem seguimento em T-AUD-013 complementar.
- **Analise/Relatorios (2026-05-14)**: relatorio final pre-GAL passou a diferenciar analise concluida de envio pendente (`selecionado_pendente_envio`, `status_envio_gal=pendente_envio`, `analise_concluida_envio_pendente`); VR1e2 placa cheia tem protecao de completude com 48 grupos esperados e `AnalysisCompletenessError`; extrator contratual normaliza aliases `bem/amostra/alvo/ct` para `Well/Sample/Target/Ct`.
- **UI (2026-05-14)**: `Reaplicar Selecao` usa regra estrita de aptidao operacional (`Sugestao_de_repeticao=Nao`, `Res_RP_1=Valido`, `Res_RP_2=Valido`, `Status_Placa=Valida`, sem CN/CP/controles). Inventario UI completo e plano de modernizacao seguem pendentes.
- **Higienizacao (2026-05-15)**: auditoria READ-ONLY executada com classificacao **ATENCAO**. A pasta nao esta pronta para empacotamento direto. Foram classificados `.tmp/pytest_tmp`, `.env.txt`, `reports/`, `relatorios/`, `logs/`, `snapshots/encoding_backup_*`, `relatorio_final_corrida_*.json`, `test_history.csv`, `banco/*` e scripts de limpeza, sem abertura de segredos e sem remocao/movimentacao. Baseline informado pelo usuario: `integragal_baseline_pre_higienizacao_2026-05-15.zip`.
- **Multiusuario/Instalacao (2026-05-15)**: auditoria READ-ONLY classificou multiusuario como APTO COM RESTRICOES e Instalacao Inicial como FUNCIONAL COM RESTRICOES. Decisao humana registrada: implantacao inicial em piloto controlado com 3 a 5 usuarios. Para ampliar a 10 usuarios, priorizar CONC-002, CONC-003 e INST-001.

## 6. Decisoes ja tomadas (confirmadas pela documentacao)

- Exames ativos: somente `VR1e2 Biomanguinhos 7500` e `ZDC BioManguinhos`.
- `Resultado_geral`: prioridade Invalido > Indeterminado > Detectavel > Nao Detectavel.
- Idempotencia GAL: dual-key 4 campos + 4+N campos, com normalizacao lowercase + strip.
- Guard de escopo: registry real fail-closed; stubs de teste podem retornar `True` por contrato canonico (CA-09 / CA-10).
- `ui/menu_handler.py::abrir_busca_extracao` delega para `extraction_plate_mapping`.
- Postgres dedicado: fora de escopo (`enabled=false` em `config.json:29-37`).
- E07 deprecacao controlada: fontes legadas em `banco/*` permanecem para rollback com marcadores de runtime (`legacy_equipment_csv` etc.).
- `AGENTS.md` e `CLAUDE.md` sao identicos por contrato canonico.

## 7. Decisoes humanas - status

Conforme `tasks.md §10` e `requirements.md §10`.

### 7.1 Resolvidas na microfase 3.1 (2026-05-13)

- **DHP-06 / DEC-006**: status canonico dos docs acessorios. **RESOLVIDA**: `equipment_legacy_deprecation.md` = fonte canonica da deprecacao controlada; `plano_equipamentos_sdd.md` = documento historico-orientador subordinado a `tasks.md §7`. T-AUD-012 marcada `[Concluido]`.
- **DHP-08 / DEC-008**: aprovacao do teste-guardiao de imports em `domain/`. **RESOLVIDA**: T-AUD-008 e executavel sem bloqueio formal. Cria apenas teste automatizado em `tests/`, **nao altera codigo de producao**. Deve preceder T-AUD-001.
- **DHP-01 / DEC-001**: status de `config.json` versionado. **RESOLVIDA**: `config.json` versionado e template/local runtime nao pronto para producao. Ambientes produtivos exigem configuracao local validada com `shared_storage.root`, `data_root` e `allowed_roots` preenchidos; a aplicacao nao deve operar em producao com `shared_storage.required=true` e caminhos vazios.
- **DHP-03 / DEC-003**: destino de `core/authentication/user_manager.py`. **RESOLVIDA**: modulo legado em deprecacao controlada; fluxo ativo = `autenticacao/auth_service.py` + `autenticacao/login.py` + `application/access_control.py`; sem remocao fisica neste momento.

### 7.2 Pendentes (4 itens apos DEC-003)

Nenhuma resolvida nas Fases 1, 2, 3 ou no restante destas DHPs.

- **DHP-02 / DHP-09 / DEC-002**: **RESOLVIDA em 2026-05-15** - `banco/*` mantido fisicamente em dev/runtime como fallback operacional controlado; conteudo sensivel nao aberto; manifest HIG-008 exclui do release; nenhuma exclusao, movimentacao, arquivamento ou migracao fisica autorizada; tarefas futuras nao bloqueantes: PRIV-001, GIG-001, HIG-009. T-AUD-011 concluida. HIG-005 concluida documentalmente (Opcao A). Ver `documento_de_passagem.md §35`.
- **DHP-04 / DEC-004**: **RESOLVIDA em 2026-05-15**. `snapshots/encoding_backup_*` sao artefatos historicos de backup/encoding para rastreabilidade e eventual recuperacao; nao entram no release operacional e devem ser tratados por retencao, arquivamento externo ou exclusao controlada em rodada propria apos baseline/backup. Nenhuma exclusao automatica autorizada.
- **DHP-05 / DEC-005**: **RESOLVIDA em 2026-05-15**. `relatorio_final_corrida_*.json` na raiz e artefato runtime/transitorio, nao entra no release operacional e deve ser tratado por retencao, realocacao ou `.gitignore` em rodada propria. Nenhuma exclusao automatica autorizada.
- **DHP-07 / DEC-007**: **RESOLVIDA em 2026-05-15**. `README.md` humano e operacional criado na raiz como ponto de entrada para operadores, administradores e equipe tecnica; nao substitui a documentacao SDD.

## 8. Tarefas prioritarias para Codex CLI (ou proximo agente)

Ordem operacional sugerida. Antes de executar qualquer item, validar em `tasks.md §10` que nao esta `[Bloqueado por DHP]`.

1. Verificar `tasks.md` para confirmar lista atualizada.
2. Escolher uma tarefa T-AUD nao bloqueada por vez.
3. Priorizar testes necessarios antes de alterar codigo.
4. Nao executar tarefas bloqueadas por DHP/DEC.
5. Nao alterar `config.json` sem rodada especifica.
6. Nao remover artefatos sem decisao humana.

Status das Tarefas T-AUD recentes e tarefa ainda disponivel:

- **T-AUD-008** (TN) - **Concluida**: criado `tests/test_domain_pure_imports.py`; guardiao de imports em `domain/` passou apos T-AUD-001.
- **T-AUD-003** (TN) - **Concluida**: criado `tests/test_shared_storage_precondition_required.py`; fail-closed de `shared_storage.required=true` com `data_root`/`allowed_roots` vazios validado sem usar `config.json` real.
- **T-AUD-007** (TN) - **Concluida por cobertura existente**: `tests/test_phase_u3_gal_send_use_case.py::test_u3_use_case_still_skips_legacy_success_key_with_scoped_request` passou e cobre match apenas pela chave legada na dual-key GAL.
- **T-AUD-001** (DT) - **Concluida**: removido `pandas` de `domain/ct_rules.py`; checagem nativa com `math.isnan`; guardiao e recorte CT passaram.
- **T-AUD-008-CFG** (RD) - **Concluida**: `config.json` valido/UTF-8, chave vazia removida, mojibake corrigido, template/local runtime preservado sem dados reais sensiveis.
- **T-AUD-004A** (TN) - **Concluida**: criado `tests/test_auth_legacy_user_manager_no_runtime_imports.py`; guardiao AST varre areas runtime e bloqueia imports de `core.authentication.user_manager`; allowlist inicial vazia; `python -m pytest tests/test_auth_legacy_user_manager_no_runtime_imports.py -q --tb=short` passou com `1 passed`.
- **T-AUD-004B** (DT/TN) - **Concluida**: bloco `if __name__ == "__main__"` de `core/authentication/user_manager.py` deixou de chamar `inicializar_sistema()`; execucao direta agora exibe mensagem segura de deprecacao controlada e encerra com `SystemExit(2)`. Guardiao T-AUD-004A passou com `1 passed`. Ressalva externa por `U+FEFF` em `ui/user_management.py` foi resolvida por T-AUD-014.
- **T-AUD-014** (DT/TN) - **Concluida**: correcao pontual de encoding/parsing em `ui/user_management.py`; removido apenas BOM UTF-8 inicial `EF BB BF`; `ast.parse` retornou `parse ok`; teste B2 que falhava passou.
- **T-AUD-010** (DT/RD) - inventario de `services/` para futuro split (apenas inventario; sem refatoracao).

### 8.1 Atualizacao de status T-AUD (2026-05-13)

Rodada de codigo/teste SDD concluida antes desta atualizacao documental:

- **T-AUD-008 concluida**: `tests/test_domain_pure_imports.py` criado; guardiao AST de imports proibidos em `domain/` passou.
- **T-AUD-001 concluida**: `domain/ct_rules.py` deixou de importar `pandas`; `pd.isna` substituido por checagem nativa com `math.isnan`; guardiao passou e recorte CT especifico passou (`131 passed`). Um teste H05 relacionado a `ui/janela_analise_completa.py` permaneceu fora do escopo da tarefa.
- **T-AUD-003 concluida**: `tests/test_shared_storage_precondition_required.py` criado; validacao fail-closed de `shared_storage.required=true` com `data_root` vazio e `allowed_roots` vazio passou, usando configuracao em memoria e sem tocar `config.json`.
- **T-AUD-007 concluida por cobertura existente**: `tests/test_phase_u3_gal_send_use_case.py::test_u3_use_case_still_skips_legacy_success_key_with_scoped_request` passou; cobre match apenas pela chave legada de 4 campos, bloqueio como `duplicado` e nao aciona Selenium, navegador ou GAL real.

Arquivos de codigo, `config.json`, documentacao fora desta rodada, CSV/DB, snapshots, `banco/*`, `reports/*` e `relatorios/*` nao devem ser considerados alterados por esta atualizacao documental.

## 9. Tarefas que o proximo agente NAO deve executar sem autorizacao

- Remover ou mover `banco/*` (conforme DEC-002 Opcao A: `banco/*` nao deve ser removido, movido ou aberto sem tarefa futura especifica — PRIV-001, GIG-001 ou HIG-009 autorizadas em rodada propria).
- Excluir `snapshots/encoding_backup_*` sem rodada propria. DEC-004 desbloqueou planejamento futuro de retencao/arquivamento/exclusao controlada, mas nao autoriza movimentacao ou exclusao automatica.
- Mover ou apagar `relatorio_final_corrida_*.json` sem rodada propria. DEC-005 desbloqueou planejamento futuro de retencao/realocacao/`.gitignore`, mas nao autoriza movimentacao ou exclusao automatica.
- Abrir ou expor credenciais (`banco/credenciais.csv`, `banco/test_creds.csv`, `banco/usuarios.csv`).
- Refatorar `services/` amplamente (DT-002 registrado apenas como inventario).
- Remover fisicamente `core/authentication/user_manager.py` sem DEC futura especifica.
- Recriar ou substituir `README.md` sem necessidade rastreavel; DEC-007 ja criou README humano e operacional.
- Alterar `docs/specs/requirements.md`, `design.md` ou `tasks.md` sem necessidade rastreavel a um achado D-xx ou tarefa T-AUD aprovada.

## 10. Ordem sugerida de retomada

Checklist objetivo para inicio de sessao:

1. Ler `AGENTS.md`.
2. Ler `CLAUDE.md` se estiver usando Claude Code (e identico).
3. Ler `docs/specs/requirements.md`.
4. Ler `docs/specs/design.md`.
5. Ler `docs/specs/tasks.md` (especialmente §10).
6. Verificar `git status --short`.
7. Escolher uma tarefa T-AUD nao bloqueada.
8. Criar ou ajustar teste, quando aplicavel.
9. Implementar alteracao minima.
10. Rodar teste especifico.
11. Atualizar documentacao apenas se houver mudanca comportamental.
12. Registrar evidencia em `notas_de_passagem.md` ou `tasks.md`.

## 11. Comandos seguros sugeridos

Apenas comandos nao destrutivos:

```powershell
git status --short
git diff --name-only
git diff --stat
python -m pytest tests/<arquivo_especifico>.py -q --tb=short
python -m pytest -k "<expressao_especifica>" -q --tb=short
```

Para suites canonicas, ver `AGENTS.md §11` (mesmas em `docs/specs/design.md §7`).

NAO executar: `rm`, `del`, `move`, `mv`, `git clean`, `git reset --hard`, `git push --force`, `git checkout -- <arquivo>`, formatadores globais, instaladores ou migracoes.

## 12. Riscos de continuidade

- `config.json` permanece template/local runtime nao pronto para producao por DEC-001; T-AUD-008-CFG ja corrigiu os problemas formais de chave vazia e mojibake sem inserir dados reais sensiveis.
- Arquivos legados em `banco/*` ainda fisicamente presentes (LIM-003).
- `services/` amplo e de alto custo cognitivo (DT-002).
- Autenticacao: `core/authentication/user_manager.py` permanece legado em deprecacao controlada; T-AUD-004A concluiu o guardiao de nao uso runtime e T-AUD-004B neutralizou o bloco `__main__` / bootstrap manual. Ressalva de parsing AST em `ui/user_management.py` foi resolvida por T-AUD-014.
- Higiene de repositorio: `snapshots/encoding_backup_*` (D-05) foi classificado por DEC-004 como artefato historico de backup/encoding — **HIG-006 concluida documentalmente em 2026-05-15 pela Opcao A**: 16 diretorios vazios (0 KB); `.gitignore` ja cobre; manifest HIG-008 exclui do release. `relatorio_final_corrida_*.json` na raiz (D-06) foi classificado por DEC-005 como artefato runtime/transitorio — **HIG-007 concluida documentalmente em 2026-05-15 pela Opcao A**: `.gitignore` ja cobre; arquivos permanecem na raiz sem remocao/movimentacao; manifest HIG-008 os exclui do release. HIG-005 permanece bloqueada por DHP-02/DHP-09; DHP-02/DHP-09 e a unica DHP HIG pendente.
- Documentacao humana: `README.md` criado na raiz conforme DEC-007.
- 1 decisao humana pendente: DHP-02 (=DHP-09). DHP-04/DEC-004, DHP-05/DEC-005 e DHP-07/DEC-007 foram resolvidas em 2026-05-15.
- Decisao humana registrada para multiusuario: implantacao inicial em piloto controlado com 3 a 5 usuarios; 10 usuarios e meta condicionada aos testes CONC/correcoes prioritarias. Decisao DEC-010 registrada: Instalacao Inicial deve ser acessivel por ADMIN e MASTER, com confirmacao forte, log/auditoria e backup previo futuro; INST-004 segue pendente para ajuste de UI/codigo em rodada propria.
- Auditoria HIG observou 0 arquivos rastreados por Git e 2586 arquivos nao rastreados; `git diff` pode ficar vazio porque nao ha baseline Git. RELEASE-001 foi registrado como concluido por baseline manual informado pelo usuario: `integragal_baseline_pre_higienizacao_2026-05-15.zip`.

## 13. Como validar que o proximo agente nao saiu do escopo

Criterios objetivos:

- Referenciou tarefa T-AUD ou requisito (CA / GAP / BUG / TEST / DEC) em `tasks.md` ou `requirements.md`.
- Nao alterou arquivos proibidos (`.py`, `config.json`, CSV, DB, snapshots, `banco/*`, `reports/`, `relatorios/`).
- Nao apagou artefatos.
- Nao expos credenciais.
- Nao corrigiu `config.json` sem autorizacao explicita do operador.
- Nao executou tarefa bloqueada por DHP.
- Rodou teste especifico (e nao formatadores ou suites globais nao recomendadas).
- Manteve rastreabilidade entre alteracao -> achado -> tarefa.

## 14. Checklist de retomada

Curto e objetivo:

- [ ] Li `AGENTS.md` / `CLAUDE.md`?
- [ ] Li `docs/specs/requirements.md`, `design.md`, `tasks.md`?
- [ ] Identifiquei uma tarefa T-AUD nao bloqueada por DHP?
- [ ] Tenho um plano de teste antes do codigo?
- [ ] Confirmei que minha alteracao nao afeta arquivos proibidos?
- [ ] Tenho como registrar evidencia da execucao?

Se qualquer item acima for "nao", pare e revise o handoff antes de seguir.

## 15. Atualizacao DEC-001 / DHP-01

Data: 2026-05-13.

- DHP-01 / DEC-001 resolvida: config.json versionado deve ser tratado como template/local runtime nao pronto para producao.
- Ambientes produtivos exigem configuracao local validada, com shared_storage.root, data_root e allowed_roots preenchidos.
- A aplicacao nao deve operar em producao com shared_storage.required=true e caminhos vazios.
- T-AUD-008-CFG foi concluida em rodada propria: chave vazia removida, mojibake corrigido, JSON/UTF-8 validado e config.json preservado como template/local runtime sem dados reais sensiveis.
- DHPs ainda pendentes: DHP-02 (=DHP-09), DHP-04, DHP-05 e DHP-07.

## 16. Atualizacao T-AUD-008-CFG

Data: 2026-05-13.

- T-AUD-008-CFG concluida: correcao controlada de config.json executada sem alterar codigo, testes ou documentacao na rodada de configuracao.
- Evidencias: config.json permaneceu JSON valido; leitura UTF-8 validada; chave vazia removida; lab_responsible sem mojibake; shared_storage.root, data_root e allowed_roots permaneceram vazios.
- config.json permanece template/local runtime nao pronto para producao; nenhum dado real sensivel foi inserido.
- DHPs ainda pendentes: DHP-02 (=DHP-09), DHP-04, DHP-05 e DHP-07.

## 17. Atualizacao DEC-003 / DHP-03

Data: 2026-05-13.

- DHP-03 / DEC-003 resolvida: `core/authentication/user_manager.py` e legado em deprecacao controlada.
- Fluxo ativo de autenticacao: `autenticacao/auth_service.py` + `autenticacao/login.py`, com matriz de autorizacao em `application/access_control.py`.
- Nenhuma remocao fisica de `core/authentication/user_manager.py` foi autorizada ou executada.
- Tarefas: T-AUD-004A concluida (teste guardiao de nao uso runtime), T-AUD-004B concluida (neutralizacao do bloco `__main__` / bootstrap manual) e T-AUD-014 concluida (encoding/parsing em `ui/user_management.py`).
- DHPs ainda pendentes: DHP-02 (=DHP-09), DHP-04, DHP-05 e DHP-07.

## 18. Atualizacao T-AUD-004A

Data: 2026-05-13

- **T-AUD-004A concluida**: criado `tests/test_auth_legacy_user_manager_no_runtime_imports.py`.
- Evidencia objetiva: o teste usa AST, varre areas runtime, bloqueia imports de `core.authentication.user_manager` e opera com allowlist inicial vazia.
- Comando executado na rodada tecnica: `python -m pytest tests/test_auth_legacy_user_manager_no_runtime_imports.py -q --tb=short`.
- Resultado: `1 passed`.
- `core/authentication/user_manager.py` continua legado em deprecacao controlada e nao foi alterado.
- **T-AUD-004B concluida em rodada posterior**: o bloco `__main__` nao chama mais `inicializar_sistema()` e encerra com mensagem segura de deprecacao controlada + `SystemExit(2)`.
- **T-AUD-014 concluida em rodada posterior**: BOM UTF-8 inicial removido de `ui/user_management.py`; `ast.parse` e teste B2 afetado passaram.
- DHPs ainda pendentes: DHP-02 (=DHP-09), DHP-04, DHP-05 e DHP-07.

## 19. Atualizacao T-AUD-004B

Data: 2026-05-13

- **T-AUD-004B concluida**.
- `core/authentication/user_manager.py` foi preservado fisicamente e continua legado em deprecacao controlada.
- O bloco `if __name__ == "__main__"` nao chama mais `inicializar_sistema()`.
- Execucao direta agora exibe mensagem segura de deprecacao controlada e encerra com `SystemExit(2)`, sem bootstrap, criacao de usuario padrao ou persistencia.
- Evidencia: `python -m pytest tests/test_auth_legacy_user_manager_no_runtime_imports.py -q --tb=short` passou com `1 passed`.
- Recorte de autenticacao inicial teve `19 passed` e `1 failed`; a falha era externa ao escopo de T-AUD-004B e foi resolvida por T-AUD-014.
- **T-AUD-014 concluida**: correcao pontual de encoding/parsing em `ui/user_management.py` por `SyntaxError: invalid non-printable character U+FEFF` em `ast.parse`.
- DHPs ainda pendentes: DHP-02 (=DHP-09), DHP-04, DHP-05 e DHP-07.

## 20. Atualizacao T-AUD-014

Data: 2026-05-13

- **T-AUD-014 concluida**.
- Correcao tecnica: removido apenas o BOM UTF-8 inicial `EF BB BF` de `ui/user_management.py`, antes da docstring inicial.
- Escopo preservado: nenhuma logica, indentacao, import, funcao, permissao, persistencia ou UI foi alterada.
- Validacao de parsing: `python -c "import ast, pathlib; p=pathlib.Path('ui/user_management.py'); ast.parse(p.read_text(encoding='utf-8'), filename=str(p)); print('parse ok')"` retornou `parse ok`.
- Teste que falhava: `python -m pytest tests/test_phase_b2_auth_actor_required.py::test_b2_user_management_uses_strict_auth_api -q --tb=short` passou com `1 passed`.
- Suite especifica: `python -m pytest tests/test_phase_b2_auth_actor_required.py -q --tb=short` passou com `3 passed`.
- Ressalva externa da T-AUD-004B resolvida por T-AUD-014.
- DHPs ainda pendentes: DHP-02 (=DHP-09), DHP-04, DHP-05 e DHP-07.

## 21. Sincronizacao SDD pre-higienizacao

Data: 2026-05-14

- Auditoria READ-ONLY de sincronizacao SDD identificou que a documentacao ainda nao estava pronta para higienizacao: `design.md`, `AGENTS.md` e `CLAUDE.md` continham referencias antigas sobre DT-001/pandas e listas antigas de T-AUD ja concluidas.
- Atualizacao documental executada nesta rodada corrigiu essas divergencias e registrou as mudancas tecnicas recentes:
  - **SDD-20260514-001**: relatorio final pre-GAL diferencia pendencia de envio GAL de falha de analise.
  - **SDD-20260514-002**: VR1e2 com placa cheia tem validacao de completude de 48 grupos e erro fail-closed (`AnalysisCompletenessError`).
  - **SDD-20260514-003**: extrator contratual normaliza `bem/amostra/alvo/ct` para `Well/Sample/Target/Ct`.
  - **UI-AUD-002**: `Reaplicar Selecao` seleciona apenas amostras aptas operacionalmente e exclui CN/CP/controles.
- Lacunas ainda pendentes:
  - **UI-AUD-001**: elaborar inventario UI canonico.
  - **UI-AUD-003**: elaborar plano de modernizacao UI apos inventario.
  - **HIG-001/HIG-002**: auditoria READ-ONLY de higienizacao executada em 2026-05-15 para `.tmp/pytest_tmp`, `.env.txt`, `reports/`, `relatorios/`, `logs` e demais artefatos candidatos; nenhuma limpeza executada.
- DHPs ainda pendentes e nao resolvidas nesta rodada: DHP-02/DHP-09 e DHP-07. DHP-04/DEC-004 e DHP-05/DEC-005 foram resolvidas em 2026-05-15.
- Este `documento_de_passagem.md` esta apto para continuidade no Claude Code/Codex CLI apos esta sincronizacao. A auditoria READ-ONLY de higienizacao ja foi executada em 2026-05-15; proxima etapa recomendada: plano HIG formal/rodada documental ou decisoes DHP antes de qualquer limpeza.

## 22. Microatualizacao requirements pre-higienizacao

Data: 2026-05-14

- Auditoria READ-ONLY posterior identificou duas divergencias residuais em `docs/specs/requirements.md`: T-AUD-008-CFG ainda descrita como pendente/nao corrigida e DEC-003 ainda descrita como pendente.
- Microatualizacao documental corrigiu `requirements.md`:
  - **SDD-REQ-20260514-001**: T-AUD-008-CFG registrada como concluida; `config.json` segue template/local runtime, com `shared_storage.root`, `data_root` e `allowed_roots` vazios.
  - **SDD-REQ-20260514-002**: DEC-003 registrada como resolvida; `core/authentication/user_manager.py` e legado em deprecacao controlada; fluxo ativo = `autenticacao/auth_service.py` + `autenticacao/login.py` + `application/access_control.py`.
- Novas lacunas registradas sem execucao:
  - **CONFIG-ENC-001**: mojibake residual em `_comentario` de `config.json`; nao corrigir sem rodada especifica de configuracao/encoding.
  - **HIG-003**: scripts de limpeza em `scripts/` foram classificados como potencialmente destrutivos na auditoria HIG 2026-05-15; nao executar `scripts/limpeza_logs_reports.ps1` nem `scripts/limpeza_prioridade_alta.ps1` sem auditoria propria e autorizacao.
  - **RELEASE-001**: baseline/backup rastreavel registrado por informacao do usuario: `integragal_baseline_pre_higienizacao_2026-05-15.zip`.
- Proxima etapa recomendada: elaborar plano HIG formal e resolver DHPs aplicaveis antes de qualquer limpeza, alteracao de `.gitignore` ou empacotamento.

## 23. Atualizacao pos-auditoria multiusuario e instalacao

Data: 2026-05-15

- Auditoria READ-ONLY - Capacidade Multiusuario e Modulo de Instalacao classificou:
  - **Multiusuario**: APTO COM RESTRICOES.
  - **Instalacao Inicial**: FUNCIONAL COM RESTRICOES.
- Estado documentado:
  - Implantacao inicial definida como piloto controlado com 3 a 5 usuarios.
  - A aptidao para 10 usuarios ainda nao esta comprovada e fica condicionada aos testes CONC e correcoes prioritarias.
  - O modulo de Instalacao Inicial existe e valida parte das pre-condicoes, mas precisa de lock/atomicidade em `config.json`, dry-run, rollback, ajuste ADMIN+MASTER conforme DEC-010 e testes adicionais.
- Backlog criado em `docs/specs/tasks.md`:
  - CONC-001..CONC-006.
  - INST-001..INST-005.
- Prioridades antes de ampliacao para 10 usuarios:
  - **CONC-002**: teste multiprocess 10 usuarios em CSVs criticos.
  - **CONC-003**: claim/lease GAL antes do envio.
  - **INST-001**: lock/atomic write para `config.json`.
- Proxima acao recomendada: manter escopo de piloto 3-5 na implantacao inicial e executar INST-004 em rodada propria para ajustar UI/codigo caso a aba de Instalacao Inicial ainda restrinja acesso apenas a ADMIN.

## 25. Decisao perfil Instalacao Inicial (2026-05-15)

- **DEC-010 registrada**: a Instalacao Inicial deve ser acessivel por ADMIN e MASTER.
- Acesso deve ser protegido por confirmacao forte, log/auditoria com ator e, futuramente, backup previo antes de aplicar configuracao.
- **INST-004 permanece pendente**: ajustar UI/codigo em rodada propria caso a aba de Instalacao Inicial ainda restrinja acesso apenas a ADMIN.
- Esta rodada foi apenas documental; nenhum codigo, teste, `config.json`, `banco/*` ou artefato operacional deve ser alterado por esta decisao.

## 26. Auditoria HIG READ-ONLY e baseline pre-higienizacao (2026-05-15)

- Auditoria READ-ONLY de Higienizacao para Implantacao classificou a pasta como **ATENCAO**.
- A pasta atual nao esta pronta para empacotamento direto.
- Evidencia estrutural: 0 arquivos rastreados por Git e 2586 arquivos nao rastreados.
- Artefatos classificados: `reports/` (1789 arquivos), `relatorios/` (23 arquivos), `logs/` com `sistema.log` volumoso, `.tmp/pytest_tmp`, `.env.txt`, `banco/*`, `snapshots/encoding_backup_*`, `relatorio_final_corrida_*.json` e `test_history.csv`.
- Scripts `scripts/limpeza_logs_reports.ps1` e `scripts/limpeza_prioridade_alta.ps1` permanecem **nao executaveis nesta fase** sem auditoria propria, baseline/backup, autorizacao explicita e decisao sobre DHPs relacionadas.
- RELEASE-001 registrado como concluido por informacao do usuario: baseline manual `integragal_baseline_pre_higienizacao_2026-05-15.zip`.
- HIG-001, HIG-002 e HIG-003 foram registradas como concluidas apenas na dimensao READ-ONLY/classificacao; HIG-004 foi concluida por atualizacao controlada de `.gitignore`; HIG-008 foi concluida como manifest documental de release; HIG-006 e HIG-007 permanecem pendentes, e HIG-005 permanece bloqueada por DHP conforme `tasks.md`.
- `docs/specs/higienizacao_implantacao.md` foi transformado em plano formal HIG por fases H0..H7, incluindo criterios de aceite, regras de seguranca, estrutura proposta de release e decisoes humanas pendentes. Nenhuma fase foi executada nesta rodada documental.

## 27. Decisao DHP-05 / DEC-005 (2026-05-15)

- DHP-05 / DEC-005 resolvida: arquivos `relatorio_final_corrida_*.json` localizados na raiz sao artefatos runtime/transitorios de execucao.
- Esses arquivos nao devem entrar no pacote de release operacional.
- Tratamento futuro permitido apenas em rodada propria: politica de retencao, realocacao ou regra de `.gitignore`.
- Nenhuma exclusao automatica, movimentacao ou alteracao de `.gitignore` foi autorizada por esta decisao.
- HIG-007 foi desbloqueada para rodada futura, mas permanece pendente.
- DHPs ainda pendentes apos DEC-004: DHP-02/DHP-09 e DHP-07.
- Escopo preservado: nenhum codigo, teste, `config.json`, banco, report, log, snapshot, script ou artefato operacional foi alterado nesta atualizacao documental.

## 28. Decisao DHP-04 / DEC-004 (2026-05-15)

- DHP-04 / DEC-004 resolvida: diretorios `snapshots/encoding_backup_*` sao artefatos historicos de backup/encoding.
- Esses diretorios foram criados para rastreabilidade e eventual recuperacao durante correcoes de encoding.
- Eles nao devem entrar no pacote de release operacional.
- Devem ser tratados por politica de retencao, arquivamento externo ou exclusao controlada em rodada propria, sempre apos baseline/backup.
- Nenhuma exclusao automatica, movimentacao ou alteracao de `.gitignore` foi autorizada por esta decisao.
- HIG-006 foi desbloqueada para rodada futura, mas permanece pendente.
- DHPs ainda pendentes: DHP-02/DHP-09.
- Escopo preservado: nenhum codigo, teste, `config.json`, banco, report, log, snapshot, script ou artefato operacional foi alterado nesta atualizacao documental.

## 29. HIG-004 - Atualizacao controlada de `.gitignore` (2026-05-15)

- HIG-004 concluida: `.gitignore` recebeu regras explicitas para ambientes locais, caches, temporarios, logs, relatorios gerados, snapshots `encoding_backup_*`, `relatorio_final_corrida_*.json`, `test_history.csv`, bancos locais e arquivos sensiveis em `banco/`.
- A atualizacao impede rastreamento futuro e nao remove, move ou altera arquivos existentes.
- `config.json` nao foi ignorado automaticamente e permanece template/local runtime versionado conforme SDD.
- `docs/specs/`, `config/contracts/` e `requirements.txt` nao foram ignorados.
- HIG-006 e HIG-007 seguem pendentes para rodadas futuras de tratamento operacional.
- DHPs ainda pendentes: DHP-02/DHP-09.
- Escopo preservado: nenhum codigo, teste, `config.json`, banco, report, log, snapshot, script ou artefato operacional foi alterado, removido ou movido.

## 30. HIG-008 - Manifest documental de release (2026-05-15)

- HIG-008 concluida como documentacao em `docs/specs/higienizacao_implantacao.md`.
- Manifest definido: `release/app/`, `release/config_template/`, `release/docs_operacionais/`, `release/assets/`, `release/scripts_autorizados/` e `release/runtime_empty/`.
- A estrutura ainda nao foi materializada: nenhuma pasta `release/` foi criada, nenhum arquivo foi copiado, movido, apagado ou empacotado.
- `release/app/` deve conter apenas runtime necessario (`main.py`, camadas de dominio/aplicacao/servicos/UI/integracoes, `config/`, `requirements.txt` e assets necessarios).
- `release/config_template/` deve conter `config.json` como template/local runtime e contratos canonicos; producao exige Instalacao Inicial para configurar `shared_storage`.
- `release/docs_operacionais/` deve conter documentacao minima; README humano existe na raiz e deve ser usado como ponto de entrada operacional.
- `release/scripts_autorizados/` nao deve incluir scripts de limpeza ate auditoria propria.
- `release/runtime_empty/` e apenas estrutura vazia sugerida para logs/reports/relatorios, sem dados reais.
- HIG-006 e HIG-007 permanecem pendentes; HIG-005 permanece bloqueada por DHP-02/DHP-09.
- DHPs ainda pendentes: DHP-02/DHP-09.

## 31. Decisao DHP-07 / DEC-007 (2026-05-15)

- DHP-07 / DEC-007 resolvida.
- `README.md` criado na raiz do projeto.
- README e humano e operacional, voltado a instalacao, execucao, configuracao inicial, restricoes conhecidas, piloto 3-5 usuarios, uso da Instalacao Inicial, itens fora do release e alertas de seguranca.
- README nao substitui `docs/specs/`, `AGENTS.md`, `CLAUDE.md` ou `documento_de_passagem.md`.
- T-AUD-009 concluida.
- DHPs ainda pendentes: DHP-02/DHP-09.

## 32. Decisao de escopo multiusuario inicial

Data: 2026-05-15

- Decisao humana registrada: a implantacao inicial **nao** declarara aptidao plena para 10 usuarios simultaneos.
- Escopo de implantacao inicial: piloto controlado com **3 a 5 usuarios**.
- 10 usuarios simultaneos passa a ser meta condicionada a conclusao dos testes CONC e correcoes prioritarias, especialmente CONC-002, CONC-003 e INST-001.
- CONC-001..CONC-006 permanecem pendentes; nenhuma tarefa CONC foi marcada como concluida por esta decisao.
- Nenhuma outra DHP foi resolvida.

## 34. HIG-006 — Fechamento documental (2026-05-15)

- HIG-006 concluida documentalmente pela Opcao A em 2026-05-15.
- Planejamento READ-ONLY identificou 16 diretorios `snapshots/encoding_backup_*`, todos vazios (0 KB), com datas entre 2026-05-03 e 2026-05-12. Conteudo interno nao foi aberto.
- `.gitignore` ja cobre `snapshots/encoding_backup_*` (linha 936, inserida pela HIG-004).
- Manifest de release HIG-008 exclui explicitamente esses diretorios do pacote operacional.
- Nenhum diretorio foi movido, removido, compactado, arquivado ou alterado.
- Os 16 diretorios permanecem fisicamente em `snapshots/`, sem rastreamento Git futuro e fora do pacote de release.
- DHPs ainda pendentes: DHP-02/DHP-09.
- HIG-005 permanece bloqueada por DHP-02/DHP-09.

## 33. HIG-007 — Fechamento documental (2026-05-15)

- HIG-007 concluida documentalmente pela Opcao A em 2026-05-15.
- Arquivos encontrados na raiz: `relatorio_final_corrida_last.json` (~2.160 bytes) e `relatorio_final_corrida_vr1.json` (~2.160 bytes). Conteudo nao foi aberto.
- Nenhum arquivo semelhante localizado em `reports/`, `relatorios/` ou `logs/`.
- `.gitignore` ja cobre o padrao `relatorio_final_corrida_*.json` (linha 939, inserida pela HIG-004).
- Manifest de release HIG-008 exclui explicitamente esses arquivos do pacote operacional.
- Nenhum arquivo foi movido, removido, alterado ou excluido nesta rodada.
- Arquivos permanecem fisicamente na raiz, sem rastreamento Git futuro e fora do pacote de release.
- T-AUD-006 concluida documentalmente como parte desta rodada.
- DHPs ainda pendentes: DHP-02/DHP-09.
- HIG-006 permanece pendente; HIG-005 concluida documentalmente (Opcao A, 2026-05-15); DEC-002 resolvida.

## 35. DHP-02/DHP-09/DEC-002 — HIG-005 Fechamento Documental (Opcao A, 2026-05-15)

- **DHP-02/DHP-09/DEC-002 RESOLVIDA em 2026-05-15** — decisao humana autorizada em rodada documental SDD.
- Texto da decisao: `banco/*` sera mantido fisicamente no ambiente de desenvolvimento/runtime como fallback operacional e legado controlado, sem abertura de conteudo nesta decisao. O diretorio nao deve entrar no pacote de release operacional, conforme manifest HIG-008. Nenhuma exclusao, movimentacao, arquivamento ou migracao fisica esta autorizada nesta etapa. Ficam criadas tarefas futuras para auditoria LGPD, extensao do `.gitignore` e planejamento de estrutura `banco_template/banco_runtime/`.
- **HIG-005 concluida documentalmente (Opcao A)**: `banco/*` mantido fisicamente em dev/runtime; conteudo sensivel nao aberto; nenhum arquivo aberto, movido, arquivado ou excluido.
- Tarefas futuras nao bloqueantes registradas em `tasks.md`: **PRIV-001** (auditoria LGPD de `banco/*`), **GIG-001** (estender `.gitignore` para CSVs operacionais nao cobertos), **HIG-009** (planejar separacao `banco_template/` + bootstrap).
- Arquivos atualizados nesta rodada documental: `docs/specs/requirements.md`, `docs/specs/tasks.md`, `docs/specs/higienizacao_implantacao.md`, `inventario_de_lixo.md`, `documento_de_passagem.md`, `notas_de_passagem.md`, `AGENTS.md`, `CLAUDE.md`.
- Nenhum arquivo de codigo, `config.json`, `banco/*`, `reports/*`, `relatorios/*`, `logs/*`, script, snapshot ou artefato runtime foi aberto, alterado, movido, arquivado ou excluido.
- DHPs HIG pendentes apos DEC-002: nenhuma. Total de DHPs HIG pendentes: 0.

## 36. Refinamento do Manifest HIG-008 — REL-001/REL-002/REL-003 (2026-05-15)

- Rodada de release engineering executada em 2026-05-15 em tres etapas: dry-run READ-ONLY (REL-001), mapeamento de imports (REL-002) e refinamento documental (REL-003).
- REL-001 (dry-run): classificacao PRONTO COM RESSALVAS; 12 itens nao cobertos pelo manifest HIG-008 original: `analise/`, `extracao/`, `interface/`, `core/`, `data/`, `debug/`, `sql/`, `images/`, `models.py`, `config/backups/`, `Main.spec`, `docs/ subset operacional`.
- REL-002 (mapeamento): todos os 12 itens classificados por analise estatica de imports Python e grep de arquivos nao-Python. Achados criticos:
  - `models.py`: RUNTIME OBRIGATORIO; importado por 4 modulos de producao (`analysis_orchestrator`, `analysis_service`, `service_container`, `main_window`); ausente do manifest §6.1 — lacuna critica.
  - `analise/` e `extracao/`: legados sem imports de producao; motores reais sao `services/engine/analysis_engine.py` e `application/extraction_plate_mapping_use_case.py`.
  - `data/state/`: criado automaticamente por `utils/persistence.py:29`; placeholder vazio necessario em `runtime_empty/data/state/`.
  - `images/`: sem referencias em Python ou arquivos nao-Python; excluido por padrao.
  - `assets/icon.ico`: referenciado por `ui/main_window.py:256` mas diretorio `assets/` nao existe fisicamente.
  - `config/backups/`: inexistente fisicamente (Glob vazio); removido da lista de ambiguos.
- REL-003 (refinamento documental): `docs/specs/higienizacao_implantacao.md` atualizado em §6.1 (adicao de `models.py`, exclusoes explicitas de legados/debug/sql), §6.3 (lista minima nomeada de docs operacionais), §6.4 (nota sobre `assets/icon.ico` e `images/`), §6.6 (`data/state/` no runtime_empty) e §6.7 (novos criterios de aceite).
- Arquivos alterados nesta rodada: `docs/specs/higienizacao_implantacao.md`, `docs/specs/tasks.md`, `inventario_de_lixo.md`, `documento_de_passagem.md`, `notas_de_passagem.md`.
- Nenhum arquivo de codigo, `config.json`, `banco/*`, `reports/*`, `relatorios/*`, `logs/*`, script, snapshot ou artefato runtime foi aberto, alterado, movido, arquivado ou excluido.
- Estado do manifest: refinado e consistente. `models.py` adicionado ao §6.1. Legados/debug/sql explicitamente excluidos. `data/state/` adicionado ao §6.6. Criterios de aceite expandidos em §6.7.

## 37. Microchecagem e correcao de status REL-001/REL-002/REL-003 (2026-05-15)

- Microchecagem executada na mesma data para verificar se REL-001/REL-002/REL-003 foram corretamente classificadas como [Concluido] em `docs/specs/tasks.md`.
- Verificacao das evidencias:
  - REL-001: `assets/icon.ico` referenciado por `ui/main_window.py:256` mas ausente fisicamente; §6.4 nota a ausencia e exige acao antes da materializacao — ausencia NAO foi formalmente aceita como OK. Evidencia insuficiente para [Concluido].
  - REL-002: checklist pos-instalacao para `docs_operacionais/` explicitamente marcado em §6.3 como "nao existe fisicamente ainda; deve ser criado em rodada propria". Apenas planejado, nao criado. Evidencia insuficiente para [Concluido].
  - REL-003: procedimento de smoke-test apenas sugerido em §6.7 como criterio generico ("validado em copia limpa") sem roteiro formal definido. Evidencia insuficiente para [Concluido].
- Correcao aplicada: REL-001, REL-002 e REL-003 rescoped para representar o trabalho futuro nao bloqueante e marcadas como [Pendente] em `tasks.md`:
  - REL-001 [Pendente]: formal acceptance/provisioning de `assets/icon.ico`
  - REL-002 [Pendente]: criacao e aprovacao do checklist pos-instalacao para `docs_operacionais/`
  - REL-003 [Pendente]: definicao formal do procedimento de smoke-test em copia limpa
- As atividades executadas na rodada anterior (dry-run, mapeamento de imports, refinamento documental) sao rastreadas na nota "Refinamento do manifest HIG-008 — atividades executadas (2026-05-15)" em `tasks.md`.
- HIG-008 permanece [Concluido] como manifest documental refinado.
- Arquivos alterados: `docs/specs/tasks.md`, `documento_de_passagem.md`, `notas_de_passagem.md`.
- Nenhum arquivo de codigo, `config.json`, `banco/*`, relatorio, log, snapshot, script ou artefato foi alterado.

## 38. REL-002 Concluida — Checklist Pos-Instalacao (2026-05-16)

- **REL-002 concluida** em 2026-05-16: checklist de validacao pos-instalacao criado em `docs/checklist_pos_instalacao.md`.
- Conteudo: 7 secoes — identificacao do ambiente, pre-condicoes, validacao da Instalacao Inicial, validacao basica de abertura, validacao operacional minima, restricoes conhecidas e resultado da validacao.
- Checklist aprovado para piloto controlado de 3 a 5 usuarios.
- Restricoes REL-001 e REL-003 registradas explicitamente na secao 6 do checklist.
- `docs/specs/higienizacao_implantacao.md` §6.3 atualizado para referenciar `docs/checklist_pos_instalacao.md`.
- `README.md` §10 atualizado com referencia ao checklist.
- **REL-001 permanece pendente**: formal acceptance ou provisioning de `assets/icon.ico`.
- **REL-003 permanece pendente**: definicao formal do procedimento de smoke-test em copia limpa.
- Proxima acao recomendada: REL-003 (definir roteiro de smoke-test para validacao em copia limpa).
- Arquivos alterados: `docs/checklist_pos_instalacao.md` (novo), `docs/specs/tasks.md`, `docs/specs/higienizacao_implantacao.md`, `README.md`, `documento_de_passagem.md`, `notas_de_passagem.md`.
- Nenhum arquivo de codigo, `config.json`, `banco/*`, relatorio, log, snapshot, script ou artefato foi alterado.

## 39. REL-003 Concluida — Procedimento de Smoke-Test de Release (2026-05-17)

- **REL-003 concluida** em 2026-05-17: procedimento formal de smoke-test criado em `docs/procedimento_smoke_test_release.md`.
- Conteudo: 11 secoes — identificacao, objetivo, pre-condicoes, verificacao estrutural do pacote, verificacao de exclusoes obrigatorias, smoke-test funcional minimo, criterios de aprovacao, criterios de reprovacao automatica, registro de evidencia, relacao com checklist pos-instalacao e pendencias conhecidas.
- Procedimento aprovado como formal; nao executado nesta rodada (release/ ainda nao materializada).
- `docs/specs/higienizacao_implantacao.md §6.7` atualizado com referencia ao procedimento e registro de que o smoke-test esta formalmente definido mas nao executado.
- `docs/checklist_pos_instalacao.md` atualizado com secao 8 referenciando o smoke-test como etapa anterior/complementar.
- `README.md §10` atualizado com referencia a `docs/procedimento_smoke_test_release.md`.
- `docs/specs/tasks.md`: REL-003 marcada `[Concluido]`; REL-001 permanece `[Pendente]`.
- **REL-001 permanece pendente**: formal acceptance ou provisioning de `assets/icon.ico` antes da materializacao do release.
- Proxima acao recomendada: tratar REL-001 (providenciar `assets/icon.ico` ou confirmar formalmente ausencia aceitavel) ou executar release dry-run complementar em rodada propria apos materializacao de `release/`.
- Arquivos alterados: `docs/procedimento_smoke_test_release.md` (novo), `docs/specs/tasks.md`, `docs/specs/higienizacao_implantacao.md`, `docs/checklist_pos_instalacao.md`, `README.md`, `documento_de_passagem.md`, `notas_de_passagem.md`.
- Nenhum arquivo de codigo, `config.json`, `banco/*`, relatorio, log, snapshot, script ou artefato foi alterado.

## 40. REL-001 Concluida Documentalmente — assets/icon.ico (2026-05-17)

- **REL-001 concluida documentalmente** em 2026-05-17 por aceitacao formal da ausencia de `assets/icon.ico`.
- Decisao humana autorizada: `assets/icon.ico` esta referenciado por `ui/main_window.py:256` mas ausente fisicamente no projeto; para o release piloto, a ausencia do icone e aceita formalmente como ressalva nao bloqueante, desde que o sistema abra sem erro critico no smoke-test; nenhum arquivo de icone foi criado nesta rodada; a providencia de um icone oficial permanece como melhoria futura antes de versao final/distribuicao ampla.
- `docs/specs/tasks.md`: REL-001 marcada `[Concluido]`; rastreabilidade atualizada.
- `docs/specs/higienizacao_implantacao.md §6.4` e `§6.7` atualizados.
- `docs/procedimento_smoke_test_release.md §3` e `§11` atualizados.
- `docs/checklist_pos_instalacao.md §6` atualizado.
- `README.md §8` atualizado.
- **REL-001, REL-002 e REL-003 estao todas concluidas.**
- Proxima acao recomendada: release dry-run complementar em Plan Mode — planejar materializacao de `release/` em rodada propria autorizada; em seguida, executar smoke-test conforme `docs/procedimento_smoke_test_release.md` e checklist pos-instalacao conforme `docs/checklist_pos_instalacao.md`.
- Arquivos alterados: `docs/specs/tasks.md`, `docs/specs/higienizacao_implantacao.md`, `docs/procedimento_smoke_test_release.md`, `docs/checklist_pos_instalacao.md`, `README.md`, `documento_de_passagem.md`, `notas_de_passagem.md`.
- Nenhum arquivo de codigo, `config.json`, `banco/*`, `assets/`, relatorio, log, snapshot, script ou artefato foi alterado.

## 41. REL-004 Concluida — Script de Materializacao por Whitelist (2026-05-17)

- **REL-004 concluida** em 2026-05-17: script PowerShell de materializacao por whitelist criado em `scripts/build_release_whitelist.ps1`.
- O script implementa a whitelist do manifest HIG-008 (§6.1-§6.6) e inclui:
  - Modo simulacao por padrao (ausencia de `-Execute` = dry-run seguro; nenhum arquivo criado).
  - Validacao de `SourceRoot` e sentinela de raiz do projeto (`CLAUDE.md`).
  - Protecao contra sobrescrita de `release/` existente (requer `-Force` + confirmacao interativa).
  - Whitelist explicita de runtime obrigatorio (`models.py` incluido como RUNTIME OBRIGATORIO).
  - Exclusoes explicitas de todos os itens proibidos (banco/, .env*, logs/dados, reports/dados, snapshots/, legados, caches, arquivos .db/.sqlite).
  - Limpeza pos-copia de `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.pyc`, bancos dentro de `release/app/`.
  - Validacao pos-copia com verificacoes positivas (obrigatorios presentes) e negativas (proibidos ausentes); falha com `exit 2` se houver violacao.
  - Geracao de `MANIFEST.txt` com SHA-256 por arquivo (executado somente com `-Execute`).
  - Mensagem explicita sobre REL-001 (`assets/icon.ico` ausente — ressalva nao bloqueante).
- **O script NAO foi executado nesta rodada.** `release/` NAO foi criada. Nenhum arquivo foi copiado, movido, removido ou empacotado.
- PRIV-001, GIG-001, HIG-009, CONC-* e INST-* permanecem pendentes e nao foram afetados.
- Arquivos alterados nesta rodada: `scripts/build_release_whitelist.ps1` (novo), `docs/specs/tasks.md`, `docs/specs/higienizacao_implantacao.md`, `docs/procedimento_smoke_test_release.md`, `docs/checklist_pos_instalacao.md`, `README.md`, `documento_de_passagem.md`, `notas_de_passagem.md`.
- Nenhum arquivo de codigo Python, `config.json`, `.gitignore`, `banco/*`, `assets/`, `data/`, relatorio, log, snapshot, CSV, banco ou artefato runtime foi alterado.
- **Proxima acao recomendada:** dry-run do script em rodada futura (`.\build_release_whitelist.ps1` sem `-Execute`) para confirmar a simulacao; em seguida, materializacao real com `-Execute` em rodada propria autorizada; por fim, smoke-test conforme `docs/procedimento_smoke_test_release.md` e checklist pos-instalacao conforme `docs/checklist_pos_instalacao.md`.
