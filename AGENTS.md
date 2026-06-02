# Projeto - Bussola Arquitetural Canonica

> **AVISO IMPORTANTE (2026-05-22):** O IntegRAGal adotou a metodologia SpecKit (Spec-Driven Development). As regras basilares de governanca deste ficheiro foram destiladas para a `.specify/memory/constitution.md`. Por favor, trate a constituição como a regra suprema caso existam divergências.

Este arquivo e o contrato operacional para agentes de IA (Claude Code, Codex CLI e quaisquer outros) que atuem no repositorio IntegRAGal. Agentes devem trabalhar orientados por SDD, nao por inferencias livres.

`CLAUDE.md` e `AGENTS.md` devem permanecer identicos. Qualquer alteracao em um exige a mesma alteracao no outro.

## 1. Fontes da verdade SDD

- `docs/specs/requirements.md` - requisitos, regras de negocio, pre-condicoes operacionais e criterios de aceite (CA-01..CA-12, CA-R01..CA-R10, GAP/BUG/TEST/DEC).
- `docs/specs/design.md` - arquitetura, fluxos, contratos, dividas tecnicas documentadas (DT-001..DT-003), limitacoes conhecidas (LIM-001..LIM-003) e pendencias documentais.
- `docs/specs/tasks.md` - plano rastreavel: T01..T24, E01..E07, R01..R10 (concluidos) e T-AUD-001..T-AUD-014 (auditoria 2026-05-12 e tarefas derivadas).
- `docs/specs/equipment_legacy_deprecation.md` - **fonte canonica da deprecacao controlada** dos legados de equipamentos (DEC-006 resolvida na microfase 3.1).
- `docs/specs/plano_equipamentos_sdd.md` - **documento historico-orientador** das fases SDD de equipamentos, subordinado ao estado atual de `docs/specs/tasks.md §7` (DEC-006 resolvida na microfase 3.1).

Ler estes documentos antes de agir e consulta-los como fonte primaria para qualquer decisao.

## 2. Escopo ativo

- Exames ativos obrigatorios:
  - `VR1e2 Biomanguinhos 7500`
  - `ZDC BioManguinhos`
- Qualquer outro exame esta fora de escopo operacional e deve falhar fail-closed em runtime real.

## 3. Stack

- Python 3.x
- CustomTkinter/Tkinter (UI)
- Pandas/OpenPyXL
- Selenium + seleniumrequests (integracao GAL)
- Persistencia CSV/JSON com suporte SQLite-first
- Pytest
- Contratos de equipamentos em `config/contracts/equipment/*.json`

## 4. Estrutura principal do projeto

- `domain/` - regras puras de dominio (CT, Resultado_geral, plate_mapping, exam_scope).
- `application/` - casos de uso, DTOs, contratos e orquestracao (gal_send_use_case, extraction_plate_mapping_use_case, equipment_profile_service, reports_query_use_case, access_control).
- `services/` - adapters, persistencia, integracoes, observabilidade e modulos legados/`operacional_*`. Cluster amplo (DT-002 registrada).
- `ui/` e `interface/` - camada de apresentacao CustomTkinter.
- `exportacao/` - formatacao e envio GAL.
- `browser/` - Selenium e global browser.
- `config/` - enums, business_rules, feature_flags, contratos canonicos (`config/contracts/equipment/*.json`).
- `banco/` - fontes legadas CSV/DB/JSON sob deprecacao controlada (E07 / LIM-003); ainda fisicamente presentes para rollback.
- `docs/specs/` - documentacao SDD.
- `tests/` - suite pytest.

## 5. Linguagem ubiqua

Glossario canonico (usar exatamente estes termos):

- Exame, `active_exams`, `ExamForaDoEscopoError`.
- `Resultado_geral` com prioridade Invalido > Indeterminado > Detectavel > Nao Detectavel.
- CT, classificacao por borda (VR1e2: 8.01-35.0 / 35.01-40.0; ZDC: 8.1-38.1 / 38.1-40.0).
- VR1e2 Biomanguinhos 7500, ZDC BioManguinhos.
- Mapeamento de placa, contrato `{mapeamento, parte, numero_extracao, caminho_arquivo}`.
- Equipamento, Contrato de equipamento (`equipment_id`, `aliases`, `signature`, `ct_policy`, `well_policy`, `extractor_strategy`, `validation_rules`, `audit`).
- GAL, Dual-key GAL (chave legada 4 campos + chave com escopo 4+N), `idempotency_key`.
- `shared_storage`, `data_root`, `allowed_roots`.
- `banco/*` legado, deprecacao controlada, rollback controlado.
- DHP (decisao humana pendente), DEC (decisao registrada), T-AUD (tarefa derivada da auditoria).

Nao inventar nomes alternativos se o codigo usa outro termo canonico.

## 6. Regras de arquitetura

- `domain/` deve permanecer sem dependencias de UI, Selenium ou pacotes pesados de infraestrutura. T-AUD-001 removeu `pandas` de `domain/ct_rules.py`; nao reintroduzir `pandas` ou dependencia equivalente em dominio.
- `application/` orquestra casos de uso com DTOs imutaveis e portas (Protocol).
- `services/` contem adapters, persistencia, integracoes e legado; alteracoes devem ser localizadas e rastreaveis.
- `ui/` e `interface/` nao podem duplicar regra clinica nem prioridade de `Resultado_geral`.
- `config/contracts/equipment/*.json` sao contratos canonicos de equipamentos. Fontes legadas em `banco/*` sao apenas fallback sob deprecacao controlada.
- `active_exams` deve ser respeitado em runtime real; stubs de teste podem retornar `True` por contrato canonico sem contaminar o registry real.
- Idempotencia GAL preservada como dual-key (legada 4 campos + escopo 4+N), verificada antes de cada envio.

## 7. Regras de operacao

- Multiusuario usa compartilhamento unico.
- Auditoria READ-ONLY de 2026-05-15 classificou multiusuario como **APTO COM RESTRICOES**. Decisao humana registrada: implantacao inicial em piloto controlado com 3 a 5 usuarios. Nao declarar aptidao plena para 10 usuarios antes da conclusao das prioridades CONC-002, CONC-003 e INST-001.
- Auditoria READ-ONLY de 2026-05-15 classificou Instalacao Inicial como **FUNCIONAL COM RESTRICOES**. Antes de uso produtivo irrestrito, tratar backlog INST: lock/atomicidade de `config.json`, dry-run, rollback, ajuste ADMIN+MASTER conforme DEC-010, confirmacao forte, log/auditoria, backup previo futuro e teste end-to-end do wizard.
- `shared_storage.required=true` exige `data_root` preenchido, `allowed_roots` com o mesmo root e ACL de leitura/escrita valida.
- `config.json` versionado e tratado como template/local runtime nao pronto para producao ate a Instalacao Inicial (T11) preencher `shared_storage.root`, `data_root` e `allowed_roots`. Ambientes produtivos exigem configuracao local validada; a aplicacao nao deve operar em producao com `shared_storage.required=true` e caminhos vazios (DEC-001 / CA-12).
- Mudanca critica sem teste de regressao e proibida.
- Postgres dedicado nao deve ser usado (provider nao implementado).

## 8. Loop SDD obrigatorio para agentes

1. Ler `requirements.md`, `design.md` e `tasks.md` antes de agir.
2. Identificar o requisito (CA / GAP / BUG / TEST / DEC), tarefa T-AUD ou decisao pendente relacionada.
3. Verificar se a tarefa esta bloqueada por DHP/DEC.
4. Se houver bloqueio, NAO implementar; apenas registrar ou pedir decisao.
5. Criar ou atualizar teste antes de alterar codigo, quando aplicavel.
6. Implementar a menor alteracao necessaria, no escopo declarado.
7. Rodar somente os testes relevantes.
8. Atualizar documentacao apenas se o comportamento real mudou.
9. Registrar pendencia, decisao ou evidencia no documento adequado (tasks.md / notas_de_passagem.md / inventario_de_lixo.md).

## 9. Regras de seguranca

- Nao executar comandos destrutivos sem aprovacao explicita.
- Nao usar `rm -rf`, `git clean -fdx`, `git reset --hard`, `git push --force`, `git checkout --` ou exclusoes recursivas.
- Nao alterar `config.json` sem rodada especifica autorizada. T-AUD-008-CFG foi concluida em rodada propria apenas para remover chave vazia, corrigir mojibake e preservar template/local runtime sem dados reais sensiveis.
- Nao ler, imprimir ou expor segredos, tokens, senhas ou chaves.
- Nao abrir conteudo sensivel de `banco/credenciais.csv`, `banco/test_creds.csv`, `banco/usuarios.csv` ou equivalentes.
- Nao remover snapshots, relatorios, arquivos legados ou artefatos transitorios sem decisao humana.
- Nao transformar decisao pendente em comportamento canonico.
- Nao marcar tarefa como concluida sem alteracao real e evidencia verificavel.
- Nao alterar arquivos fora do escopo da tarefa autorizada.
- Nao usar `--no-verify`, `--no-gpg-sign` ou flags equivalentes para burlar hooks.

## 10. Regras de teste minimo

- CT por borda para VR1e2 e ZDC.
- `Resultado_geral` com prioridade correta.
- Cores/tags da tabela para indeterminado/detectavel/nao detectavel.
- Mapeamento com preview e contrato de retorno.
- Sincronizacao mapa -> tabela sem perder edicao manual.
- Idempotencia GAL por chave composta (dual-key: legada 4 campos + escopo 4+N).
- Fail-closed de escopo: exame fora de `active_exams` levanta `ExamForaDoEscopoError` antes de qualquer IO de analise.

Testes guardioes e pendencias registradas (T-AUD em `tasks.md`):

- T-AUD-003 (L-T02 / CA-12): **Concluido** - `shared_storage.required=true` com `data_root`/`allowed_roots` vazios falha fail-closed em teste isolado.
- T-AUD-007 (L-T01 / CA-11): **Concluido por cobertura pre-existente** - match apenas pela chave legada na dual-key GAL bloqueia como `duplicado`.
- T-AUD-008 (L-T03): **Concluido** - teste-guardiao de imports em `domain/` proibe `pandas`, `selenium`, `tkinter`, `customtkinter`, `seleniumrequests`.
- T-AUD-001 (D-01): **Concluido** - `domain/ct_rules.py` usa checagem nativa com `math.isnan`, sem `pandas`.
- T-AUD-004A (L-T04 / DEC-003): **Concluido** - teste guardiao de nao uso runtime de `core.authentication.user_manager` criado em `tests/test_auth_legacy_user_manager_no_runtime_imports.py`; evidencia `1 passed`.
- T-AUD-004B (DEC-003): **Concluido** - bloco `__main__` / bootstrap manual de `core/authentication/user_manager.py` neutralizado sem remocao fisica; ressalva externa resolvida por T-AUD-014.
- T-AUD-013 (L-T04): cobertura complementar de callers/guardioes de autenticacao apos DEC-003.
- T-AUD-014: **Concluido** - correcao pontual de encoding/parsing em `ui/user_management.py` por `U+FEFF`; removido apenas BOM UTF-8 inicial e teste B2 afetado passou.
- SDD-20260514-001/002/003: **Concluidos** - relatorio final pre-GAL, completude VR1e2 placa cheia e normalizacao de extrator contratual documentados em `tasks.md`.
- UI-AUD-002: **Concluido** - `Reaplicar Selecao` usa aptidao operacional estrita; inventario UI completo continua pendente em UI-AUD-001.
- LOG-UNIF-001: **Concluido** - uniformizacao de locais de gravacao de logs para `logs/`; bug `logs_dir = "dados/banco"` corrigido; `AuditLogger`, `DataFrameReporter` e `legacy_panel_governance` passaram a usar config service; guardiao `tests/test_log_paths_uniformization.py` (9 passed).
- LOG-UNIF-002: **Concluido** - fallback de `resolve_banco_dir()` corrigido para `banco_runtime/`; `ConfigLoader.BASE_PATH` corrigido para `banco_template/`; `DEFAULT_ROOTS` dos scripts inclui `banco_runtime`; corridas CSVs migradas de `dados/banco/` para `logs/`; guardiao `tests/test_banco_path_fallbacks.py` (7 passed).

## 11. Suites recomendadas

```powershell
python -m pytest tests/test_ct_classification.py tests/test_vr1_vr2_inconclusivo_runtime.py -q --tb=short
python -m pytest tests/test_analysis_service_phase6_vectorization.py tests/test_classificacao_cores_caracterizacao_h03.py -q --tb=short
python -m pytest tests/test_extraction_plate_mapping_use_case.py tests/test_mapeamento_extracao_caracterizacao_h04.py -q --tb=short
python -m pytest tests/test_0260325_exam_creator_registry_rollout.py tests/test_shared_storage_standardization.py -q --tb=short
python -m pytest tests/test_t14_gal_idempotency_revalidation.py tests/test_extraction_caracterizacao_t14.py -q --tb=short
# Guardioes de uniformizacao de paths (LOG-UNIF-001/002):
python -m pytest tests/test_log_paths_uniformization.py tests/test_banco_path_fallbacks.py -q --tb=short
```

## 12. Decisoes arquiteturais canonicas (pos-T06)

- `ui/menu_handler.py::abrir_busca_extracao` delega para `ui/modules/extraction_plate_mapping.py::abrir_mapeamento_extracao`. Nao referenciar `ExtractionUseCase` ou `TkFileChooser` diretamente no menu_handler.
- Chave de idempotencia GAL e normalizada (lowercase + strip) antes de qualquer comparacao. Nunca incluir timestamp na chave.
- `is_active()` no ExamRegistry usa lista `active_exams` separada, nao o dicionario `exams`. Em runtime real, `active_exams` vazio bloqueia todos os exames; stubs de teste sem configuracao podem retornar `True` por contrato canonico sem afetar o fail-closed do registry real (CA-10).
- Fluxo ativo de autenticacao e `autenticacao/auth_service.py` + `autenticacao/login.py`, com matriz de autorizacao em `application/access_control.py`. `core/authentication/user_manager.py` e legado em deprecacao controlada; T-AUD-004A concluiu o guardiao de nao uso runtime e T-AUD-004B neutralizou a execucao direta; nao remover sem DEC futura especifica.

## 13. Dividas tecnicas registradas (auditoria 2026-05-12)

- **DT-001 (D-01) - RESOLVIDA**: `domain/ct_rules.py` nao importa mais `pandas` e usa checagem nativa com `math.isnan`. Guardiao T-AUD-008 e correcao T-AUD-001 concluidos. Nao reintroduzir dependencias pesadas em `domain/`.
- **DT-002 (R-T3)**: `services/` concentra dezenas de modulos. Alto custo cognitivo, sem violacao funcional. Apenas inventario nesta fase (T-AUD-010).
- **DT-003 (D-04 / DEC-003)**: `core/authentication/user_manager.py` e legado em deprecacao controlada. Fluxo ativo de autenticacao: `autenticacao/auth_service.py` + `autenticacao/login.py`, com matriz de autorizacao em `application/access_control.py`. Nenhuma remocao fisica autorizada; T-AUD-004A concluiu o guardiao de nao uso runtime e T-AUD-004B neutralizou a execucao direta; antes de remover, obter DEC futura.

## 14. Limitacoes conhecidas

- **LIM-001 (D-02 / DEC-001)**: `config.json` versionado e template/local runtime nao pronto para producao - `shared_storage.required=true` com `data_root=""` e `allowed_roots=[]`. Instalacao Inicial/configuracao local validada e obrigatoria para producao; a aplicacao nao deve operar em producao com caminhos vazios.
- **LIM-002 (D-08)**: problemas formais de `config.json:4-5` corrigidos por T-AUD-008-CFG: chave literal vazia `""` removida e mojibake de `lab_responsible` corrigido. `config.json` permanece template/local runtime nao pronto para producao; nenhum dado real sensivel foi inserido.
- **LIM-003 (D-11)**: `banco/*` legados permanecem fisicamente presentes apos E07. Remocao depende de DHP-02 / DHP-09 (T-AUD-011).

## 15. Decisoes humanas - status

Conforme `tasks.md §10` e `requirements.md §10`.

### 15.1 Resolvidas (2026-05-13)

- **DHP-06 / DEC-006**: status canonico de docs acessorios. **RESOLVIDA**: `equipment_legacy_deprecation.md` = fonte canonica da deprecacao controlada; `plano_equipamentos_sdd.md` = documento historico-orientador subordinado a `tasks.md §7`. T-AUD-012 marcada `[Concluido]`.
- **DHP-08 / DEC-008**: aprovacao do teste-guardiao de imports em `domain/`. **RESOLVIDA**: T-AUD-008 e executavel sem bloqueio formal. Cria apenas teste automatizado em `tests/`, **nao altera codigo de producao**. Deve preceder T-AUD-001.
- **DHP-01 / DEC-001**: status de `config.json` versionado. **RESOLVIDA**: `config.json` versionado e template/local runtime nao pronto para producao. Ambientes produtivos exigem configuracao local validada, com `shared_storage.root`, `data_root` e `allowed_roots` preenchidos. A aplicacao nao deve operar em producao com `shared_storage.required=true` e caminhos vazios. T-AUD-008-CFG foi concluida posteriormente sem inserir dados reais sensiveis.
- **DHP-03 / DEC-003**: destino de `core/authentication/user_manager.py`. **RESOLVIDA**: modulo legado em deprecacao controlada; fluxo ativo = `autenticacao/auth_service.py` + `autenticacao/login.py` + matriz `application/access_control.py`; sem remocao fisica neste momento.
- **DHP-04 / DEC-004**: politica para `snapshots/encoding_backup_*`. **RESOLVIDA**: diretorios `snapshots/encoding_backup_*` sao artefatos historicos de backup/encoding para rastreabilidade e eventual recuperacao, nao entram no pacote de release operacional e devem ser tratados por retencao, arquivamento externo ou exclusao controlada em rodada propria apos baseline/backup. Nenhuma exclusao automatica autorizada.
- **DHP-05 / DEC-005**: politica para `relatorio_final_corrida_*.json` na raiz. **RESOLVIDA**: arquivos `relatorio_final_corrida_*.json` localizados na raiz sao artefatos runtime/transitorios de execucao, nao entram no pacote de release operacional e devem ser tratados por politica de retencao, realocacao ou `.gitignore` em rodada propria. Nenhuma exclusao automatica autorizada.
- **DHP-07 / DEC-007**: criacao de `README.md` humano. **RESOLVIDA**: README operacional criado na raiz para instalacao, execucao, configuracao inicial, restricoes conhecidas, piloto 3-5 usuarios, itens fora do release e alertas de seguranca. README nao substitui SDD.
- **DHP-02 / DHP-09 / DEC-002**: destino de `banco/*` legados. **RESOLVIDA em 2026-05-15**: `banco/*` mantido fisicamente em dev/runtime como fallback operacional controlado; conteudo sensivel nao aberto nesta decisao; manifest HIG-008 ja exclui `banco/*` do release integralmente; nenhuma exclusao, movimentacao, arquivamento ou migracao fisica autorizada nesta etapa; tarefas futuras nao bloqueantes registradas: PRIV-001, GIG-001 e HIG-009. HIG-005 concluida documentalmente (Opcao A).

### 15.2 Pendentes - nao implementar sem resolucao

- **DHP-10** (2026-05-29): verificar conteudo de `dados/banco/historico.db` (131KB, 25/05/2026, mais antigo dos 4) antes de exclusao ou arquivamento. Pode ser DB inicial vazio ou snapshot. Nao excluir sem inspecao humana. Ver PRIV-001.
- **DHP-11** (2026-05-29): decidir destino dos CSVs duplicados residuais em `dados/banco/` apos migracao das corridas (`equipamentos.csv`, `exames_config.csv`, `placas.csv`, `regras.csv`, `usuarios.csv` — todos desatualizados). Conteudo de `usuarios.csv` nao deve ser aberto sem ambiente controlado.
- **DHP-12** (2026-05-29): verificar conteudo de `banco_template/historico.db` (3.3MB, maior que o ativo de 1.5MB em `banco_runtime/`). Suspeito — pode ser dados de desenvolvimento ou snapshot salvo erroneamente. Inspecionar antes de qualquer decisao.

Total pendente: 3 decisoes humanas (DHP-10, DHP-11, DHP-12).

## 16. Tarefas e lacunas priorizadas

Tarefas concluidas abaixo **nao devem ser repetidas** por agentes:

- **T-AUD-008** - concluida: teste-guardiao de imports em `domain/`.
- **T-AUD-003** - concluida: teste shared_storage fail-closed.
- **T-AUD-007** - concluida por cobertura pre-existente: dual-key GAL match-by-legacy.
- **T-AUD-001** - concluida: remocao de `pandas` de `domain/ct_rules.py`.
- **T-AUD-004A** - concluida: teste guardiao de nao uso runtime de `core.authentication.user_manager` em `tests/test_auth_legacy_user_manager_no_runtime_imports.py`; allowlist inicial vazia; evidencia `1 passed`.
- **T-AUD-004B** - concluida: bloco `__main__` / bootstrap manual de `core/authentication/user_manager.py` neutralizado sem remocao fisica; ressalva `U+FEFF` em `ui/user_management.py` resolvida por T-AUD-014.
- **T-AUD-014** - concluida: correcao pontual de encoding/parsing em `ui/user_management.py`; removido apenas BOM UTF-8 inicial; `ast.parse` e teste B2 afetado passaram.
- **T-AUD-008-CFG** - concluida: correcao limitada de `config.json` removeu chave vazia, corrigiu mojibake, preservou template/local runtime e nao inseriu dados reais sensiveis.
- **T-AUD-009** - concluida: `README.md` humano e operacional criado na raiz conforme DEC-007.
- **T-AUD-006** - concluida documentalmente: politica operacional para `relatorio_final_corrida_*.json` registrada como HIG-007 (Opcao A); `.gitignore` ja cobre; sem remocao/movimentacao fisica.
- **HIG-006** - concluida documentalmente (Opcao A, 2026-05-15): 16 diretorios `snapshots/encoding_backup_*` confirmados vazios (0 KB); `.gitignore` ja cobre (linha 936, HIG-004); manifest HIG-008 exclui do release; nenhum diretorio foi movido, removido, compactado ou arquivado. Nao repetir.
- **SDD-20260514-001/002/003** - concluidas: semantica de relatorio final pre-GAL, completude VR1e2 placa cheia e normalizacao de extrator contratual.
- **UI-AUD-002** - concluida: regra estrita de `Reaplicar Selecao`.
- **HIG-005** - concluida documentalmente (Opcao A, 2026-05-15): `banco/*` mantido fisicamente em dev/runtime; conteudo sensivel nao aberto; manifest HIG-008 exclui do release; nenhum arquivo aberto, movido, arquivado ou excluido. DEC-002 resolvida. Nao repetir.
- **REL-004** - concluida (2026-05-17): `scripts/build_release_whitelist.ps1` criado com whitelist HIG-008, modo simulacao por padrao (sem `-Execute`), validacoes de seguranca e validacao pos-copia. O script NAO foi executado; `release/` NAO foi criada. Nao recriar o script sem rodada especifica autorizada.
- **LOG-UNIF-001** - concluida (2026-05-29): uniformizacao de locais de gravacao de logs para root unico `logs/`. Bug corrigido em `config/default_config.json` (`logs_dir = "dados/banco"` → `"logs"`). Componentes `AuditLogger`, `DataFrameReporter` e `_resolve_default_log_path()` passaram a consultar config service. Guardiao: `tests/test_log_paths_uniformization.py` (9 passed). Nao repetir.
- **LOG-UNIF-002** - concluida (2026-05-29): uniformizacao de fallbacks de pastas de dados. `path_resolver.resolve_banco_dir()` cai em `banco_runtime/` (antes `banco/`). `ConfigLoader.BASE_PATH` = `banco_template/` (antes `banco/`). `DEFAULT_ROOTS` dos scripts inclui `banco_runtime`. Corridas CSVs migradas de `dados/banco/` para `logs/`. Guardiao: `tests/test_banco_path_fallbacks.py` (7 passed). Nao repetir.
- **WIZ-GAL-01..07** - concluidas (2026-05-30): wizard de criacao de exames agora captura todos os campos necessarios para analise e envio GAL plenos. Passo 1 inclui `equipamento`/`tipo_placa_analitica`; novo Passo 4 captura `gal_exame_codigo`, `kit_codigo`, `panel_tests_id`, `export_fields` e mapeamento alvo→nome_GAL. `envio_gal.construir_payload` ganha fallback de `testes_do_painel` a partir de `export_fields`. `validate_exam` emite avisos nao bloqueantes para campos GAL vazios. Guardioes: `tests/test_exam_creator_campos_gal.py` (8 passed). Ver `design.md §3.3.1`. Nao repetir.
- **POCO-VAZIO** - concluida (2026-05-29): poco vazio = Invalido + Selecionado=False em todos os exames. Regra em `domain.resultado_geral.is_amostra_vazia` + `analysis_service._apply_resultado_geral_vectorized`. CA-14 criado em `requirements.md`. Guardiao: `tests/test_poco_vazio_invalido.py` (18 passed). Nao repetir.
- **GAL-CODIGO-FIX** - concluida (2026-05-29): bug de perda de `gal_exame_codigo`/`panel_tests_id` ao reeditar exame corrigido. Perfis VR1e2 (VRSRT, panel 12) e ZDC (PEQZDC, panel vazio) restaurados. `_exam_to_dict` serializa `gal_exame_codigo`. Guardiao: `tests/test_exam_creator_preserva_gal_codigo.py` (3 passed). Nao repetir.
- **GAL-ROB-001..010** - concluidas (2026-05-30): robustez do modulo de envio GAL — excecao de worker registrada estruturadamente; lote nao abortado por metadados vazios; aviso de paginas de metadados falhando; CSV validado antes do browser; aviso de `gal_exame_codigo` ausente; mascaramento de resposta do servidor; `inflight_keys` atomicas contra envio duplo intra-CSV; normalizacao simetrica de datas no reconciliador; validacao de `codigo` nao-vazio; fallback de reconciliacao por `codigo_amostra`. Arquivos: `application/gal_send_use_case.py`, `exportacao/envio_gal.py`, `exportacao/gal_payload_contract.py`, `services/gal/gal_status_reconciler.py`. Nao repetir.
- **GAL-FEAT-001..005 + GAL-PERF-001** - concluidas (2026-05-30): feature flag `USE_GAL_ENVIO_SEM_METADADOS` (pular `/lista/`, usar `codigoAmostra` direto); fallback `codigo` = `codigoAmostra` em `construir_payload`; Firefox headless por default (`gal_integration.headless: true`) com toggle em Configuracoes GAL; terminal exibe linha por amostra com rollback `USE_GAL_TERMINAL_LOG_POR_AMOSTRA`; toggles "Ocultar navegador" e "Enviar sem metadados" em `ui/modules/tela_configuracoes.py`; janela de metadados reduzida de 365 para 15 dias. Nao repetir.
- **DASH-001** - concluida (2026-05-30): dashboard principal usa `ExamRunsSQLiteRepository` (`banco_runtime/historico.db`) como fonte primaria com `status_gal` por amostra; fallbacks CSV mantidos. Arquivo: `ui/modules/dashboard.py`. Nao repetir.
- **DASH-002** - concluida (2026-05-30): Gestao Clinica com campos De/Ate (DD/MM/AAAA) + botao Filtrar; `DashboardAnalyticsService` aceita `data_inicio`/`data_fim`. Arquivos: `ui/modules/dashboard.py`, `services/reports/dashboard_analytics.py`. Nao repetir.
- **DASH-003..008 + DASH-FIX-001** - concluidas (2026-05-30): evolucao do dashboard. DASH-003 dedup "Doencas Mais Positivas" (apenas `RES_*`, sem `SRC_RES_*`; corrige Positividade; Top 12; rotulos limpos). DASH-004 Gestao com barra+radar+pizza numa figura + tabela lateral + negrito. DASH-005 nova aba "Visao Analitica" (`obter_painel_analitico`: KPIs, heatmap dia x doenca, tabela de Ct 15/7/3 dias interativa com setas/percentuais e destaque por alvo; fontes +100%). DASH-006 barra de filtros reutilizavel (Operacional filtra cards/grafico/tabela; Visao Analitica so Exame). DASH-007 detalhe de corrida read-only (coluna "Corrida", fix import `ui.theme.design_tokens`) + botao "Abrir Mapa Definitivo (Excel)" via `_localizar_mapa_definitivo` em `<data_root>/mapas`. DASH-008 tabela Corridas Recentes (busca desativada, scrollbar reancorada, ordenacao por clique asc/desc). DASH-FIX-001 `CardResumo.set_valor/set_indicativo` + Gestao/Visao Analitica desacopladas do CSV. Arquivos: `services/reports/dashboard_analytics.py`, `ui/modules/dashboard.py`, `ui/modules/componentes/card_resumo.py`. Ver `design.md §3.8`/§14.2 e CA-16/CA-17. Nao repetir.
- **CFG-UI-001 / WIZ-UI-001 / CAL-UI-001** - concluidas (2026-05-30): CFG-UI-001 `tela_configuracoes._carregar_categoria` chama `_carregar_valores()` (corrige switch "Ocultar navegador" exibido OFF apesar do default `headless=true`). WIZ-UI-001 Passo 1 do wizard em grade compacta (sem rolagem) + botao "Limpar Etapa" (`clear_current_step`). CAL-UI-001 `SimpleCalendar(date_format=...)` + botoes de calendario nos campos De/Ate. Arquivos: `ui/modules/tela_configuracoes.py`, `ui/modules/exam_creator/wizard.py`, `ui/modules/reports.py`, `ui/modules/dashboard.py`. Nao repetir.
- **CONFIG-PATH-001** - concluida (2026-05-30, rodada autorizada): `config.json` `paths.logs_dir`: `"dados/banco"` → `"logs"` (elimina `dados/dados/`); `paths.gal_history_csv` e `paths.gal_upload_history_csv`: `"logs/total_importados_gal.csv"` → `"logs/historico_analises.csv"`. `config/default_config.json` alinhado. Nao repetir.
- **INST-001** - concluida: lock e escrita atomica para `config.json` implementados em `services/core/config_service.py::_save_config`. Nao repetir.
- **INST-002** - concluida: dry-run e resumo antes de aplicar instalacao implementados. Nao repetir.
- **INST-003** - concluida: backup/rollback da instalacao implementados. Nao repetir.

Estado HIG e pendencias sem DHP para rodadas futuras:

- T-AUD-010 - inventario de `services/` (apenas inventario, sem refatoracao).
- T-AUD-013 - cobertura complementar de callers/guardioes de autenticacao.
- UI-AUD-001 - inventario canonico de UI.
- UI-AUD-003 - plano de modernizacao UI apos inventario.
- HIG-001/HIG-002/HIG-003 - concluidas como auditoria/classificacao READ-ONLY em 2026-05-15; nao remover, mover, limpar ou executar scripts sem rodada propria.
- HIG-004 - concluida: `.gitignore` atualizado com regras explicitas para artefatos runtime, temporarios, logs, relatorios, snapshots `encoding_backup_*`, dumps de corrida, bancos locais e arquivos sensiveis; nao remove arquivos existentes.
- HIG-008 - concluida como documentacao: manifest/estrutura limpa de release definido em `docs/specs/higienizacao_implantacao.md`; nenhuma pasta `release/` foi criada e nenhum arquivo foi copiado, movido, removido ou empacotado.
- HIG-005 - concluida documentalmente (Opcao A, 2026-05-15): `banco/*` mantido em dev/runtime; manifest HIG-008 exclui do release; nenhum arquivo aberto, movido ou excluido. Ver lista de concluidas acima. Nao repetir.
- **HIG-006** - concluida documentalmente (Opcao A, 2026-05-15): ver lista de concluidas acima. Nao repetir.
- **HIG-007** - concluida documentalmente (Opcao A, 2026-05-15): `.gitignore` ja cobre `relatorio_final_corrida_*.json`; dois arquivos (~2.160 bytes cada) permanecem fisicamente na raiz sem remocao/movimentacao/exclusao; manifest HIG-008 os exclui do release; nao incluir no pacote operacional. Nao repetir.
- RELEASE-001 - concluida por baseline manual informado pelo usuario: `integragal_baseline_pre_higienizacao_2026-05-15.zip`; nao autoriza limpeza automatica.
- Plano HIG formal em `docs/specs/higienizacao_implantacao.md`: fases H0..H7 documentadas; nenhuma fase pode ser executada sem rodada propria autorizada.
- CONC-001 - rastrear decisao de piloto 3-5 e requisito futuro de 10 usuarios.
- CONC-002 - teste multiprocess 10 usuarios em CSVs criticos.
- CONC-003 - claim/lease GAL antes do envio externo.
- CONC-004 - teste de dois admins aplicando instalacao/config.
- CONC-005 - validar SQLite em compartilhamento.
- CONC-006 - validar logs com 10 processos.
- INST-004 - ajustar Instalacao Inicial para ADMIN+MASTER com confirmacao forte, log/auditoria e backup previo futuro.
- INST-005 - teste end-to-end do wizard de instalacao.
- GAL-PEND-001 - S3/S6: retry com classificacao de erro transitorio vs definitivo em `enviar_amostra()`. Validar idempotencia do endpoint `/gravar/` antes de implementar.
- GAL-PEND-002 - S18: suite de testes sem Selenium real para o modulo GAL.
- PRIV-001 - auditoria LGPD/controlada de `banco/*`; conteudo nao deve ser aberto sem autorizacao formal e ambiente controlado; nao bloqueia outras tarefas HIG.
- GIG-001 - estender `.gitignore` para CSVs operacionais de `banco/` ainda nao cobertos (sessoes.csv, configuracoes_sistema.csv, exames*.csv, placas*.csv, regras*.csv, sas.csv, profiles/*.json, protocols/*.json); executar em rodada propria sem alterar arquivos fisicos.
- HIG-009 - planejar separacao `banco_template/` (esquema/vazio) + `banco_runtime/` (gerado na instalacao) com bootstrap seguro; requer refatoracao de ~18 arquivos `.py`; executar em rodada de codigo separada apos PRIV-001 e GIG-001.
- DHP-10 - verificar `dados/banco/historico.db` (131KB, mais antigo) antes de qualquer exclusao.
- DHP-11 - decidir destino dos CSVs duplicados residuais em `dados/banco/` apos migracao das corridas.
- DHP-12 - verificar `banco_template/historico.db` (3.3MB, suspeito) antes de qualquer decisao.

## 17. Como agir diante de achados criticos

Ao encontrar vulnerabilidade evidente, erro bloqueante, risco de perda/corrupcao de dados ou risco operacional grave:

- Parar a alteracao imediatamente.
- Nao corrigir automaticamente sem autorizacao.
- Registrar o achado com prefixo `[CRITICAL_FINDING]` em `notas_de_passagem.md` ou `tasks.md`.
- Mascarar valores sensiveis; nunca expor segredos.
- Indicar arquivo, fluxo, impacto e recomendacao.
- Aguardar decisao humana se a correcao extrapolar a tarefa atual.

## 18. Politica de governanca dos documentos

- `requirements.md`, `design.md`, `tasks.md`: alteraveis apenas em rodadas SDD especificas.
- `AGENTS.md` e `CLAUDE.md`: identicos; alteraveis em rodadas de governanca.
- `notas_de_passagem.md`: log vivo, recebe entradas curtas por sessao.
- `inventario_de_lixo.md`: catalogo de candidatos a limpeza, nunca remove arquivos.
- `documento_de_passagem.md`: handoff transitorio entre agentes.
- `config.json`, codigo (`.py`), CSV/DB/JSON operacionais, snapshots, relatorios e `banco/*`: nao alterar sem rodada especifica autorizada.
