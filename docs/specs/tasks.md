# Tasks - SDD Fonte Unica

Status permitido: `[Pendente]`, `[Em Andamento]`, `[Concluido]`

## 1. Core sequencial
- [x] [Concluido] T01 - Validar catalogo ativo (somente VR1e2 e ZDC) em menu e runtime.
- [x] [Concluido] T02 - Executar regressao de CT por borda para os dois exames.
- [x] [Concluido] T03 - Garantir regra unica de `Resultado_geral` (invalido > indeterminado > detectavel > nao detectavel).
- [x] [Concluido] T04 - Garantir que inconclusivo/indeterminado mantenha tag/cor correta na tabela.
- [x] [Concluido] T05 - Validar sincronizacao mapa -> tabela sem sobrescrever edicao manual.
- [x] [Concluido] T06 - Revalidar fluxo completo de mapeamento com preview imediato por kit/parte.

## 2. Item 7 (incluir/editar exame)
- [x] [Concluido] T07 - Confirmar visibilidade do botao `Editar Exame Selecionado` em resolucoes 1366x768 e 1920x1080.
- [x] [Concluido] T08 - Confirmar abertura maximizada do modulo do menu 7.
- [x] [Concluido] T09 - Confirmar formulario completo de edicao abre maior e carrega todos os campos.
- [x] [Concluido] T10 - Confirmar salvamento de edicao recarrega lista e reflete no registry.

## 3. Multiusuario e compartilhamento
- [x] [Concluido] T11 - Configurar compartilhamento unico via `Instalacao Inicial`.
- [x] [Concluido] T12 - Validar `shared_storage.required=true` com `data_root` unico e `allowed_roots` alinhado.
- [x] [Concluido] T13 - Rodar smoke de concorrencia para 5 usuarios em pasta compartilhada.

## 4. GAL e observabilidade
- [x] [Concluido] T14 - Revalidar idempotencia de envio GAL por chave composta.
- [x] [Concluido] T15 - Revisar logs de erro e warning apos suite core.

## 5. Encerramento
- [x] [Concluido] T16 - Atualizar `docs/specs/*` apos qualquer mudanca funcional.
- [x] [Concluido] T17 - Atualizar `CLAUDE.md`, `AGENTS.md`, `notas_de_passagem.md`.
- [x] [Concluido] T18 - Publicar relatorio final de testes executados e pendencias.

## 6. Retomada pos-interrupcao
- [x] [Concluido] T19 - Reconstruir contexto sem handoff do agente anterior, executar ROT documental, validar suites canonicas e ajustar guard de escopo para stubs de teste sem `active_exams`, preservando fail-closed no registry carregado.

## 7. Equipamentos SDD (iniciado 2026-05-11)
- [x] [Concluido] E01 - Fase 0: Baseline com fixtures reais e skip explicito quando ausente (tests/test_phase0_equipment_real_fixture_baseline.py).
- [x] [Concluido] E02 - Fase 1: Contratos JSON canonicos + alias resolution (config/contracts/equipment/7500_extended.json, quantstudio.json).
- [x] [Concluido] E03 - Fase 2: EquipmentProfileService facade com controle de acesso ADMIN/MASTER (application/equipment_profile_service.py).
- [x] [Concluido] E04 - Fase 5 (parcial): UI com todos os campos do contrato editaveis, incluindo sheet_policy, row_policy, ct_policy completo, validation_rules.required_columns (services/cadastros_diversos.py).
- [x] [Concluido] E05 - Fase 3: Detector profile-driven — detector operacional por perfis JSON ativos, shadow legacy anexado/logado em divergencia, required_columns/well_policy bloqueantes e fail-closed para perfis explicitos invalidos.
- [x] [Concluido] E06 - Fase 4: Extracao por contrato — mapear extractor_strategy para extratores existentes, eliminar dependencia do EquipmentRegistry legado em extract_results() e validar fixtures reais dos dois equipamentos ativos.
- [x] [Concluido] E07 - Fase 7: Deprecacao controlada — marcar banco/equipamentos.csv, banco/equipamentos_metadata.csv, banco/profiles/equipment_profiles.json e builtins do registry como legados.

## 8. GAL pos-T14 (2026-05-11)
- [x] [Concluido] T20 - Remover janela de transicao expirada (envio_gal.py:_legacy_build_request e bloco try/except) — janela encerrou em 2026-05-04.
- [x] [Concluido] T21 - Corrigir emit_debug_logs padrao de True para False em formatar_para_gal() (gal_formatter.py).
- [x] [Concluido] T22 - Corrigir testes GAL pre-existentes falhos: test_gal_formatter_layout (coluna stale vr1), test_phase5_gal_reference_structure (skip guard para fixture ausente), test_phase_p3 (normalizacao NaN/vazio).
- [x] [Concluido] T23 - Atualizar tasks.md e design.md com estado de equipamentos SDD e GAL pos-T14.
- [x] [Concluido] T24 - Verificar fixture QuantStudio valida (arquivo com tabela de resultados) para converter test_phase0_equipment_real_fixture_baseline de skip para pass.

## 8b. Wizard de criacao de exames — completude GAL (2026-05-30)
- [x] [Concluido] WIZ-GAL-01 - Adicionar campos equipamento e tipo_placa_analitica ao Passo 1 do wizard, com opcoes carregadas dos contratos ativos em config/contracts/equipment/*.
- [x] [Concluido] WIZ-GAL-02 - Implementar Passo 4 "Integracao GAL" com gal_exame_codigo, kit_codigo, panel_tests_id e tabela de mapeamento alvo->nome_gal (export_fields/mapa_alvos). Aviso nao bloqueante se campos vazios.
- [x] [Concluido] WIZ-GAL-03 - Atualizar _build_registry_exam_config para usar campos capturados (equipamento, tipo_placa, kit, gal_exame_codigo, panel_tests_id, export_fields, mapa_alvos) com fallback de preservacao para edicao.
- [x] [Concluido] WIZ-GAL-04 - Atualizar _apply_registry_exam_to_wizard para popular todos os novos campos ao editar exame existente.
- [x] [Concluido] WIZ-GAL-05 - Implementar fallback testes_do_painel em envio_gal.py: quando painel nao esta em panel_tests, deriva testes de exam_cfg.export_fields via _norm_gal_field. Exames com painel em config GAL nao sao afetados.
- [x] [Concluido] WIZ-GAL-06 - Avisos nao bloqueantes em RegistryExamEditor.validate_exam quando gal_exame_codigo/kit_codigo/export_fields vazios.
- [x] [Concluido] WIZ-GAL-07 - Testes de regressao: tests/test_exam_creator_campos_gal.py (8 testes cobrindo campos GAL, fallback de painel, gal_formatter e round-trip de serializacao).

## 9. Feature: Modulo de Relatorios
- [x] [Concluido] R01 - Definir contratos `ReportsFilterDTO` e `ReportsResultDTO` em camada de aplicacao, com testes de validacao para periodo, escopo ativo de exames, paginacao e combinacoes de filtros.
- [x] [Concluido] R02 - Criar fixtures minimas de relatorio cobrindo `historico_analises`, `exam_runs` e journal GAL, incluindo casos enviado, nao enviado, erro, duplicado e resultado sem chave GAL.
- [x] [Concluido] R03 - Implementar consultas SQLite-first para totais por periodo, exame e positividade, sem recalcular CT ou `Resultado_geral`.
- [x] [Concluido] R04 - Implementar reconciliacao de status GAL a partir de `services.gal_transactions`, com chave normalizada e fallback para campos historicos existentes.
- [x] [Concluido] R05 - Implementar filtros por analista, kit, lote e cruzamentos combinados, preservando performance com indices existentes ou migracao explicita.
- [x] [Concluido] R06 - Criar `ReportsQueryUseCase` para orquestrar filtros, repositorio e regras de escopo, retornando resumo, agrupamentos, detalhes e paginacao.
- [x] [Concluido] R07 - Criar UI desktop do modulo de relatorios com filtros, resumo, tabela detalhada paginada e estados vazios/erro.
- [x] [Concluido] R08 - Implementar exportacao CSV/XLSX dos dados filtrados com metadados de filtros, periodo e usuario emissor.
- [x] [Concluido] R09 - Adicionar testes de regressao para exames realizados vs. a realizar, positividade, periodo, analista, kit/lote e status GAL.
- [x] [Concluido] R10 - Validar release readiness do modulo: somente leitura, sem IO de analise/GAL, respeito a compartilhamento multiusuario e tempo de resposta aceitavel.

## 10. Dividas, pendencias e decisoes (auditoria SDD 2026-05-12)

Esta secao agrega tarefas derivadas do Relatorio de Divergencias SDD (rodada de auditoria 2026-05-12, modo READ-ONLY). Nenhuma alteracao de codigo, configuracao operacional, CSV, DB, snapshot ou artefato gerado foi executada — apenas refatoracao documental dos arquivos `docs/specs/{requirements,design,tasks}.md` foi aplicada.

Categorias:
- **DT** Divida Tecnica Prioritaria
- **RD** Refatoracao Documental
- **EP** Especificacao Pendente
- **TN** Teste Necessario
- **HR** Higiene de Repositorio
- **DHP** Decisao Humana Pendente

Status permitido: `[Pendente]`, `[Em Andamento]`, `[Concluido]`, `[Bloqueado por DHP]`.

### Tarefas

- [x] [Concluido] **T-AUD-RD-DESIGN** (RD) - Sincronizar `design.md §3.7` com `tasks.md §7` sobre fases SDD de Equipamentos. Origem: D-03. Arquivo: `docs/specs/design.md`. Criterio: §3.7 referencia `equipment_legacy_deprecation.md`, remove afirmacao de fases pendentes e diferencia "fase concluida" de "divida residual". Concluido em 2026-05-12.
- [x] [Concluido] **T-AUD-RD-SCOPE** (RD) - Reescrever `design.md §3.6` sobre `active_exams` e stubs de teste; adicionar CA-10 em `requirements.md §8`. Origem: D-12. Arquivos: `docs/specs/design.md`, `docs/specs/requirements.md`. Concluido em 2026-05-12.
- [x] [Concluido] **T-AUD-RD-PRECOND** (RD) - Documentar pre-condicao de `shared_storage` em `requirements.md §7.1` e CA-12; adicionar LIM-001 em `design.md §9`. Origem: D-02. Concluido em 2026-05-12.
- [x] [Concluido] **T-AUD-001** (DT) - Remover `import pandas` de `domain/ct_rules.py` e substituir `pd.isna(ct_val)` por checagem nativa Python. Origem: D-01. Arquivo: `domain/ct_rules.py`. Criterio: dominio sem importacao de pandas; suites canonicas continuam verdes. Dependencias: T-AUD-008. Prioridade: media. Decisao humana: nao. Evidencia: `domain/ct_rules.py` passou a usar `math.isnan` em helper local; `tests/test_domain_pure_imports.py` passou; recorte CT passou com `131 passed` (`tests/test_ct_classification.py`, `tests/test_ct_borda_vr1e2_zdc.py`, `tests/test_logic_engine_classificar_ct.py`, `tests/test_vr1_vr2_inconclusivo_runtime.py`). Observacao: teste H05 de UI fora do escopo permaneceu identificado separadamente.
- [x] [Concluido] **T-AUD-002** (EP/DHP) - Confirmar status de `config.json` versionado (template/runtime local vs configuracao real de producao). Origem: D-02 / DEC-001. Criterio: registro escrito da decisao em CLAUDE.md §4 e em `notas_de_passagem.md`. Decisao humana: DHP-01 resolvida em 2026-05-13. Decisao: `config.json` versionado e template/local runtime nao pronto para producao; ambientes produtivos exigem configuracao local validada com `shared_storage.root`, `data_root` e `allowed_roots` preenchidos; a aplicacao nao deve operar em producao com `shared_storage.required=true` e caminhos vazios.
- [x] [Concluido] **T-AUD-003** (TN) - Adicionar teste de regressao para `shared_storage.required=true` com `data_root` vazio (deve falhar fail-closed em `services/installation_checks.py`). Origem: L-T02 / CA-12 / TEST-003. Arquivos: novo `tests/test_shared_storage_precondition_required.py` ou equivalente. Prioridade: alta antes de release de producao. Decisao humana: nao. Evidencia: criado `tests/test_shared_storage_precondition_required.py`; teste usa configuracao isolada em memoria, nao depende de `config.json`, valida `data_root` vazio, `allowed_roots` vazio e `shared_storage_required=FAIL`; comando especifico passou com `1 passed`.
- [x] [Concluido] **T-AUD-004** (EP/DHP) - Auditar callers de `core/authentication/user_manager.py` versus `autenticacao/auth_service.py`. Origem: D-04 / DEC-003. Evidencia: auditoria READ-ONLY DHP-03A concluiu que `autenticacao/auth_service.py` esta ativo em runtime, `autenticacao/login.py` esta ativo no bootstrap, e nenhum import externo de `core.authentication.user_manager` foi encontrado no grafo estatico pesquisado. Decisao humana DEC-003 resolvida: `core/authentication/user_manager.py` passa a ser legado em deprecacao controlada; fluxo ativo de autenticacao = `autenticacao/auth_service.py` + `autenticacao/login.py` + matriz `application/access_control.py`; nenhuma remocao fisica neste momento.
- [x] [Concluido] **T-AUD-004A** (TN) - Criar teste guardiao de nao uso runtime de `core.authentication.user_manager`. Origem: DEC-003 / DHP-03A. Criterio: teste falha se imports/callers runtime de `core.authentication.user_manager` surgirem fora de allowlist explicita; deve preservar uso apenas como legado documentado ate decisao de remocao. Decisao humana: nao, derivada de DEC-003. Evidencia: criado `tests/test_auth_legacy_user_manager_no_runtime_imports.py`; teste usa AST, varre areas runtime (`main.py`, `autenticacao/`, `application/`, `services/`, `ui/`, `interface/`, `exportacao/`, `browser/`, `scripts/`), bloqueia imports de `core.authentication.user_manager` com allowlist inicial vazia; `python -m pytest tests/test_auth_legacy_user_manager_no_runtime_imports.py -q --tb=short` passou com `1 passed`. `core/authentication/user_manager.py` permanece legado em deprecacao controlada e nao foi alterado.
- [x] [Concluido] **T-AUD-004B** (DT/TN) - Avaliar e neutralizar/remover em rodada separada o bloco `__main__` / bootstrap manual de `core/authentication/user_manager.py`, especialmente criacao de usuario padrao. Origem: DEC-003 / risco DHP-03A. Criterio: abordagem definida e validada sem remover fisicamente o modulo legado nesta etapa. Decisao humana: nao, derivada de DEC-003. Evidencia: `core/authentication/user_manager.py` foi preservado fisicamente; bloco `if __name__ == "__main__"` deixou de chamar `inicializar_sistema()` e passou a emitir mensagem segura de deprecacao controlada com `SystemExit(2)`, sem bootstrap, criacao de usuario padrao ou persistencia. Guardiao `python -m pytest tests/test_auth_legacy_user_manager_no_runtime_imports.py -q --tb=short` passou com `1 passed`. Recorte especifico de autenticacao teve `19 passed` e `1 failed` por ressalva externa: `tests/test_phase_b2_auth_actor_required.py::test_b2_user_management_uses_strict_auth_api` falhou ao parsear `ui/user_management.py` por `SyntaxError: invalid non-printable character U+FEFF`; essa falha nao invalidou T-AUD-004B e foi resolvida posteriormente por T-AUD-014.
- [ ] [Pendente] **T-AUD-005** (HR/HIG) - Politica operacional para `snapshots/encoding_backup_*`. Origem: D-05 / DEC-004. DEC-004 resolvida em 2026-05-15: diretorios `snapshots/encoding_backup_*` sao artefatos historicos de backup/encoding, criados para rastreabilidade e eventual recuperacao durante correcoes de encoding. Eles nao devem entrar no pacote de release operacional e devem ser tratados por politica de retencao, arquivamento externo ou exclusao controlada em rodada propria, sempre apos baseline/backup. **Sem exclusao automatica.**
- [x] [Concluido] **T-AUD-006** (HR/HIG) - Politica operacional para `relatorio_final_corrida_*.json` na raiz. Origem: D-06 / DEC-005. DEC-005 resolvida em 2026-05-15: arquivos `relatorio_final_corrida_*.json` localizados na raiz sao artefatos runtime/transitorios de execucao, nao devem entrar no pacote de release operacional e devem ser tratados por politica de retencao, realocacao ou regra de `.gitignore` em rodada propria. **Sem exclusao automatica.** Concluida documentalmente como HIG-007 (Opcao A, 2026-05-15): `.gitignore` ja cobre o padrao; arquivos permanecem fisicamente na raiz sem remocao/movimentacao; manifest HIG-008 os exclui do release.
- [x] [Concluido] **T-AUD-007** (TN) - Cobertura explicita para match apenas pela chave legada (4 campos) na dual-key GAL. Origem: D-07 / L-T01 / CA-11 / TEST-001. Arquivos: novo `tests/test_gal_dual_key_legacy_match.py` ou ampliacao de `tests/test_t14_gal_idempotency_revalidation.py`. Prioridade: media. Decisao humana: nao. Evidencia: concluida por cobertura equivalente pre-existente, sem alteracao de arquivo; `tests/test_phase_u3_gal_send_use_case.py::test_u3_use_case_still_skips_legacy_success_key_with_scoped_request` passou com `1 passed`, cobrindo chave legada 4 campos presente, chave 4+N ausente, bloqueio como `duplicado`, sem Selenium/navegador/GAL real.
- [x] [Concluido] **T-AUD-008** (TN) - Teste-guardiao de imports em `domain/`: dominio NAO pode importar `pandas`, `selenium`, `tkinter`, `customtkinter`, `seleniumrequests`. Origem: L-T03 / TEST-002. Arquivo: novo `tests/test_domain_pure_imports.py`. **DHP-08 RESOLVIDA na microfase 3.1 (2026-05-13)**: executavel sem bloqueio formal; **cria apenas teste automatizado em `tests/`, nao altera codigo de producao**; deve preceder T-AUD-001 (remocao de pandas em `domain/ct_rules.py`). Evidencia: criado `tests/test_domain_pure_imports.py`; teste AST varre `domain/*.py` e bloqueia imports proibidos; passou apos T-AUD-001 com `1 passed`.
- [x] [Concluido] **T-AUD-008-CFG** (RD) - Corrigir `config.json`: encoding UTF-8 limpo, remover chave vazia `""`, validar conteudo de `lab_responsible`. Origem: D-08 / BUG-001. DHP-01 resolvida previamente. Evidencia: `config.json` permaneceu JSON valido e legivel como UTF-8; chave vazia `""` removida de `general`; mojibake em `lab_responsible` corrigido; `shared_storage.root`, `data_root` e `allowed_roots` permaneceram vazios; nenhum dado real sensivel foi inserido; nenhum codigo foi alterado.
- [x] [Concluido] **T-AUD-009** (RD/DHP) - Criar `README.md` humano para operadores, administradores e equipe tecnica. Origem: D-09 / DEC-007. Decisao humana DHP-07 resolvida em 2026-05-15: README operacional criado na raiz, sem substituir SDD, cobrindo instalacao, execucao, configuracao inicial, restricoes conhecidas, piloto 3-5 usuarios, Instalacao Inicial, itens fora do release e alertas de seguranca.
- [ ] [Pendente] **T-AUD-010** (DT/RD) - Inventario de `services/` para futuro split por subdominio (analysis/, equipment/, gal/, reports/, persistence/). Origem: R-T3 / DT-002. **Apenas inventario nesta tarefa**; refatoracao em rodada propria. Decisao humana: nao.
- [x] [Concluido] **T-AUD-011** (EP/DHP) - Decisao sobre `banco/*` legados: manter como fallback declarado (status atual conforme `equipment_legacy_deprecation.md`) ou planejar remocao controlada apos um ciclo de validacao. Origem: D-11 / DEC-002. **DHP-02/DHP-09/DEC-002 RESOLVIDA em 2026-05-15**: `banco/*` mantido fisicamente no ambiente de desenvolvimento/runtime como fallback operacional controlado; conteudo sensivel nao foi aberto nesta decisao; manifest HIG-008 ja exclui `banco/*` do release integralmente; nenhuma exclusao, movimentacao, arquivamento ou migracao fisica esta autorizada nesta etapa; tarefas futuras nao bloqueantes registradas: PRIV-001, GIG-001 e HIG-009.
- [x] [Concluido] **T-AUD-012** (EP/DHP) - Confirmar classificacao canonica de `docs/specs/plano_equipamentos_sdd.md` e `docs/specs/equipment_legacy_deprecation.md`. Origem: D-10 / DEC-006 / DHP-06. **Resolvido na microfase 3.1 (2026-05-13)**: `equipment_legacy_deprecation.md` e fonte canonica da deprecacao controlada dos legados de equipamentos; `plano_equipamentos_sdd.md` e documento historico-orientador subordinado ao estado atual de `tasks.md §7`. Decisao humana DHP-06 registrada em `requirements.md §10` DEC-006.
- [ ] [Pendente] **T-AUD-013** (TN) - Cobertura complementar para callers/guardioes de autenticacao apos DEC-003, priorizando o bloqueio de novo uso runtime de `core.authentication.user_manager` e preservacao do fluxo ativo `AuthService` + `login.py`. Origem: L-T04. Dependencias: T-AUD-004A e T-AUD-004B. Decisao humana: nao.
- [x] [Concluido] **T-AUD-014** (DT/TN) - Correcao pontual de encoding/parsing em `ui/user_management.py` para remover/caracterizar BOM ou caractere inicial `U+FEFF` que impede `ast.parse`. Origem: ressalva externa identificada na validacao de T-AUD-004B. Criterio: `tests/test_phase_b2_auth_actor_required.py::test_b2_user_management_uses_strict_auth_api` deve conseguir parsear `ui/user_management.py` sem `SyntaxError`, preservando comportamento funcional e sem refatoracao ampla de UI/autenticacao. Decisao humana: nao. Evidencia: removido apenas o BOM UTF-8 inicial `EF BB BF` antes da docstring inicial de `ui/user_management.py`; nenhuma logica, indentacao, import, funcao, permissao, persistencia ou UI foi alterada. Validacao `ast.parse` retornou `parse ok`; `python -m pytest tests/test_phase_b2_auth_actor_required.py::test_b2_user_management_uses_strict_auth_api -q --tb=short` passou com `1 passed`; `python -m pytest tests/test_phase_b2_auth_actor_required.py -q --tb=short` passou com `3 passed`. Ressalva externa da T-AUD-004B resolvida.
- [x] [Concluido] **SDD-20260514-001** (RD/DT) - Registrar semantica correta do relatorio final pre-GAL. Origem: auditoria de sincronizacao SDD 2026-05-14 e diagnostico de VR1/VR2. Arquivo relacionado: `services/final_run_report.py`. Status confirmado pelo codigo/testes existentes: itens analisados e ainda nao enviados ao GAL devem ser classificados como pendencia operacional (`selecionado_pendente_envio`, `status_envio_gal=pendente_envio`, `status_execucao=analise_concluida_envio_pendente`), nao como falha de analise. Evidencia documental: campos `status_analise`, `status_envio_gal` e `motivo_item` incorporados ao modelo de relatorio; falha real de envio permanece distinta de pendencia pre-envio.
- [x] [Concluido] **SDD-20260514-002** (DT/TN) - Registrar completude VR1e2 com placa cheia. Origem: diagnostico da corrida `20250924 VR1_VR2 BIOM PLACA 01_Results_20260220 173647.xlsx`. Arquivo relacionado: `services/analysis_service.py`. Status confirmado pelo codigo/testes existentes: `AnalysisCompletenessError` protege o fluxo fail-closed quando uma placa VR1e2 de 96 pocos deveria produzir 48 grupos e o mapeamento/gabarito perde grupos. Evidencia de teste: `tests/test_0260327_phase2_grouping_contract_runtime.py` cobre os grupos A5+A6, B11+B12, D3+D4, D11+D12, E11+E12 e F11+F12.
- [x] [Concluido] **SDD-20260514-003** (DT/TN) - Registrar normalizacao de saida do extrator por contrato. Origem: auditoria de sincronizacao SDD 2026-05-14. Arquivo relacionado: `services/analysis_service.py`. Status confirmado pelo codigo/testes existentes: `_normalize_contract_extractor_columns` aceita aliases contratuais como `bem`, `amostra`, `alvo` e `ct`, normalizando para os nomes esperados pelo pipeline (`Well`, `Sample`, `Target`, `Ct`) antes de `identificar_colunas_pcr`.
- [x] [Concluido] **UI-AUD-002** (UI-AUD/TN) - Registrar regra estrita do botao `Reaplicar Selecao` na Tela de Analise. Arquivo relacionado: `ui/janela_analise_completa.py`. Status confirmado pelo codigo/testes existentes: selecionar somente amostras nao controle com `Sugestao_de_repeticao=Nao`, `Res_RP_1=Valido`, `Res_RP_2=Valido` e `Status_Placa=Valida`; nao selecionar CN, CP, controles, `SIM` em repeticao ou itens com RP/placa invalido. Evidencia de teste: `tests/test_reaplicar_selecao_aptidao_operacional.py`.
- [ ] [Pendente] **UI-AUD-001** (UI-AUD/RD) - Elaborar inventario canonico de telas, fluxos e acoes UI. Origem: auditoria UI READ-ONLY ainda nao incorporada integralmente ao SDD. Arquivo previsto: `docs/specs/ui_inventory.md`. Status: lacuna documental; esqueleto pode existir, mas inventario completo ainda nao foi executado.
- [ ] [Pendente] **UI-AUD-003** (UI-AUD/RD) - Elaborar plano de modernizacao UI apos inventario canonico. Origem: auditoria UI READ-ONLY. Arquivo previsto em rodada futura: `docs/specs/ui_modernization_plan.md`. Status: nao criar plano completo antes do inventario.
- [ ] [Em Andamento] **UI-AUD-003-A** (UI-AUD/FEATURE) - Implementar novo sistema de design (Tokens e Base Components) baseado no blueprint aprovado. Origem: UI-AUD-003 (Plano de modernizacao UI aprovado via DHP). Escopo: Criar modulo de tema `ui/theme.py`, refatorar componentes base, aplicar fundo geral `#F4F6FA` e substituir Toplevels excessivos pela arquitetura Single Window. Nao alterar regras e comportamentos clinicos.
- [x] [Concluido] **HIG-001** (HIG/RD) - Auditoria READ-ONLY executada para artefatos `.tmp/pytest_tmp` e `.env.txt` como candidatos de higiene/seguranca. Evidencia: auditoria HIG 2026-05-15 classificou `.tmp/pytest_tmp` como temporario/candidato a limpeza e `.env.txt` como possivel arquivo sensivel, sem abrir conteudo, mover, remover ou resolver DHP.
- [x] [Concluido] **HIG-002** (HIG/RD) - Auditoria READ-ONLY executada para volume e politica de retencao de `reports/`, `relatorios/` e `logs/`. Evidencia: auditoria HIG 2026-05-15 classificou `reports/` com 1789 arquivos, `relatorios/` com 23 arquivos e `logs/sistema.log` com ~44 MB como artefatos gerados/nao distribuir, sem abrir conteudo sensivel e sem executar limpeza.
- [x] [Concluido] **SDD-REQ-20260514-001** (RD) - Sincronizar `docs/specs/requirements.md` com T-AUD-008-CFG concluida. Origem: auditoria READ-ONLY de sincronizacao SDD pre-higienizacao. Evidencia: `requirements.md` agora registra que a chave vazia `""` foi removida, `general.lab_responsible` foi corrigido, `shared_storage.root`, `data_root` e `allowed_roots` permaneceram vazios, e `config.json` continua template/local runtime nao pronto para producao. Nenhum arquivo operacional foi alterado nesta microatualizacao documental.
- [x] [Concluido] **SDD-REQ-20260514-002** (RD) - Sincronizar `docs/specs/requirements.md` com DEC-003 resolvida. Origem: auditoria READ-ONLY de sincronizacao SDD pre-higienizacao. Evidencia: `requirements.md` agora registra `core/authentication/user_manager.py` como legado em deprecacao controlada, fluxo ativo `autenticacao/auth_service.py` + `autenticacao/login.py` (LoginDialog), matriz `application/access_control.py`, T-AUD-004A/T-AUD-004B concluidas e ressalva externa resolvida por T-AUD-014. Nenhuma remocao fisica foi autorizada.
- [ ] [Pendente] **CONFIG-ENC-001** (CONFIG/RD) - Lacuna residual de encoding em `config.json`: campo `_comentario` ainda pode apresentar mojibake, por exemplo `ConfiguraÃ§Ãµes`. Origem: auditoria READ-ONLY de sincronizacao SDD pre-higienizacao. Nao corrigir `config.json` sem rodada especifica de configuracao/encoding; nao inserir dados reais sensiveis.
- [x] [Concluido] **HIG-003** (HIG/RD) - Scripts de limpeza classificados antes de qualquer uso, incluindo `scripts/limpeza_logs_reports.ps1` e `scripts/limpeza_prioridade_alta.ps1`. Evidencia: auditoria HIG 2026-05-15 classificou scripts com `Remove-Item`/`Move-Item` como potencialmente destrutivos; status operacional: **nao executar sem auditoria propria, baseline/backup, autorizacao explicita e decisao sobre DHPs relacionadas**.
- [x] [Concluido] **HIG-004** (HIG/RD) - Atualizar `.gitignore` em rodada propria para cobrir artefatos runtime e sensiveis identificados pela auditoria HIG: ambientes locais, caches, `.tmp/`, `pytest_tmp/`, logs, `reports/`, `relatorios/`, credenciais/usuarios, bancos locais, `snapshots/encoding_backup_*`, `relatorio_final_corrida_*.json` e `test_history.csv`, respeitando DEC-004 e DEC-005. Evidencia: `.gitignore` recebeu secao explicita "INTEGRAGAL - RUNTIME, HIGIENE E DADOS LOCAIS" em 2026-05-15. A atualizacao nao remove, move ou altera arquivos existentes e nao ignora `config.json`, `docs/specs/`, `config/contracts/` ou `requirements.txt`.
- [x] [Concluido] **HIG-005** (HIG/DHP) - Classificar destino de `banco/*` para release/higienizacao. Origem: auditoria HIG 2026-05-15. **DHP-02/DHP-09/DEC-002 RESOLVIDA em 2026-05-15 (Opcao A)**: `banco/*` mantido fisicamente em dev/runtime como fallback operacional controlado; conteudo sensivel nao foi aberto; manifest HIG-008 ja exclui `banco/*` do release integralmente; nenhum arquivo foi aberto, movido, arquivado ou excluido nesta rodada documental. Tarefas futuras nao bloqueantes: PRIV-001, GIG-001 e HIG-009.
- [x] [Concluido] **HIG-006** (HIG/RD) - Politica operacional para `snapshots/encoding_backup_*` concluida documentalmente pela Opcao A em 2026-05-15. DEC-004 resolvida. Evidencia: planejamento READ-ONLY identificou 16 diretorios `snapshots/encoding_backup_*` na pasta `snapshots/`, todos vazios (0 KB), com datas entre 2026-05-03 e 2026-05-12; conteudo interno nao aberto. `.gitignore` ja cobre `snapshots/encoding_backup_*` (HIG-004, linha 936); manifest de release HIG-008 exclui explicitamente esses diretorios; nenhum diretorio foi movido, removido, compactado ou arquivado. Os 16 diretorios permanecem fisicamente em `snapshots/` sem rastreamento Git futuro e fora do pacote operacional.
- [x] [Concluido] **HIG-007** (HIG/RD) - Politica operacional para `relatorio_final_corrida_*.json` concluida documentalmente pela Opcao A em 2026-05-15. Evidencia: dois arquivos identificados na raiz (`relatorio_final_corrida_last.json` e `relatorio_final_corrida_vr1.json`, ~2.160 bytes cada, conteudo nao aberto); nenhum arquivo semelhante encontrado em `reports/`, `relatorios/` ou `logs/`; `.gitignore` ja cobre o padrao `relatorio_final_corrida_*.json` (linha 939, HIG-004); manifest de release HIG-008 exclui explicitamente esses arquivos; nenhum arquivo foi movido, removido ou alterado. Arquivos permanecem fisicamente na raiz sem rastreamento Git futuro e fora do pacote operacional.
- [x] [Concluido] **HIG-008** (RELEASE/RD) - Definir manifest/estrutura limpa de release, separando `app/`, `config_template/`, `docs_operacionais/`, `assets/`, `scripts_autorizados/` e `runtime_empty/`. Evidencia: `docs/specs/higienizacao_implantacao.md` registra manifest documental do pacote de implantacao, conteudos permitidos/excluidos, criterios de aceite e ressalva de que a estrutura ainda nao foi materializada. Nenhuma pasta `release/` foi criada, nenhum arquivo foi copiado, movido, apagado ou empacotado.
- [x] [Concluido] **RELEASE-001** (RELEASE/RD) - Baseline/backup rastreavel registrado antes de limpeza/deploy. Evidencia declarada pelo usuario em 2026-05-15: `integragal_baseline_pre_higienizacao_2026-05-15.zip`. Nenhum backup foi criado por agente nesta rodada; nenhum arquivo foi aberto, movido, removido ou empacotado por esta atualizacao documental.
- [ ] [Pendente] **CONC-001** (CONC/RD) - Rastrear decisao de escopo multiusuario e validar requisito futuro. Origem: auditoria READ-ONLY de capacidade multiusuario e modulo de instalacao em 2026-05-15. Decisao humana registrada: implantacao inicial em piloto controlado com 3 a 5 usuarios; 10 usuarios e meta condicionada a CONC-002, CONC-003, INST-001 e demais testes/correcoes CONC aplicaveis. Status permanece pendente porque a aptidao para 10 usuarios ainda nao foi comprovada.
- [ ] [Pendente] **CONC-002** (CONC/TN) - Criar teste multiprocess com 10 usuarios/processos em CSVs criticos compartilhados. Origem: auditoria 2026-05-15. Criterio: validar lock/atomicidade sem perda, corrupcao ou truncamento em arquivos compartilhados. Prioridade: alta antes de implantacao produtiva com 10 usuarios.
- [ ] [Pendente] **CONC-003** (CONC/GAL) - Implementar claim/lease GAL antes do envio externo. Origem: auditoria 2026-05-15. Evidencia: idempotencia dual-key e persistencia imediata reduzem duplicidade, mas ainda ha janela entre carregar chaves, enviar ao GAL e persistir sucesso. Prioridade: critica antes de implantacao produtiva com 10 usuarios.
- [ ] [Pendente] **CONC-004** (CONC/INST) - Testar dois administradores aplicando instalacao/configuracao simultaneamente. Origem: auditoria 2026-05-15. Criterio: `config.json` deve permanecer valido e consistente sob concorrencia administrativa. Depende de INST-001 para mitigacao robusta.
- [ ] [Pendente] **CONC-005** (CONC/DB) - Validar SQLite em compartilhamento. Origem: auditoria 2026-05-15. Evidencia: ha uso de WAL, mas faltam testes em share real/cenario equivalente para 10 usuarios. Criterio: sem erro persistente de lock e com integridade de historico.
- [ ] [Pendente] **CONC-006** (CONC/LOG) - Validar logs com 10 processos simultaneos. Origem: auditoria 2026-05-15. Criterio: todas as linhas de log completas, legiveis e sem intercalacao/corrupcao.
- [x] [Concluido] **INST-001** (INST/CONFIG) - Implementar lock e escrita atomica para `config.json`. Origem: auditoria 2026-05-15. Evidencia: `ConfigService._save_config()` usa escrita direta; risco de corrupcao se dois admins aplicarem configuracao ao mesmo tempo. Prioridade: alta antes de implantacao produtiva com 10 usuarios.
- [x] [Concluido] **INST-002** (INST/UI) - Adicionar dry-run e resumo antes de aplicar instalacao. Origem: auditoria 2026-05-15. Criterio: administrador visualiza alteracoes previstas antes de gravar configuracao ou criar pastas.
- [x] [Concluido] **INST-003** (INST/RELEASE) - Definir e testar backup/rollback da instalacao. Origem: auditoria 2026-05-15. Criterio: configuracao anterior recuperavel e baseline/backup registrado antes de alteracoes; relacionado a RELEASE-001.
- [ ] [Pendente] **INST-004** (INST/UI) - Ajustar UI/codigo da Instalacao Inicial para acesso ADMIN+MASTER conforme DEC-010. Requisitos: confirmacao forte antes de aplicar configuracao, log/auditoria com ator e preparacao para backup previo futuro. Origem: auditoria 2026-05-15. Evidencia: menu Administracao aceita ADMIN/MASTER, mas a aba Instalacao Inicial parece exigir exatamente ADMIN. Decisao humana resolvida em 2026-05-15; nao alterar codigo nesta rodada documental; implementar em rodada propria.
- [ ] [Pendente] **INST-005** (INST/TEST) - Criar teste end-to-end do wizard de instalacao. Origem: auditoria 2026-05-15. Criterio: fluxo com mocks valida abertura, checklist, selecao/padronizacao simulada, resumo, exportacao controlada e bloqueios de perfil sem tocar configuracao real.
- [ ] [Pendente] **PRIV-001** (PRIV/DHP) - Auditoria LGPD/controlada de `banco/*`: revisar tipos de dados em `historico.db`, `usuarios.db`, `credenciais.csv` e equivalentes para classificacao de titulares e bases legais. Origem: DEC-002 (2026-05-15). Requisito: conteudo sensivel nao deve ser aberto sem autorizacao formal e ambiente controlado; seguir politica LGPD aplicavel. Nao bloqueia nenhuma outra tarefa HIG.
- [x] [Concluido] **GIG-001** (GIG/.gitignore) - Estender `.gitignore` para cobrir arquivos operacionais e sensiveis de `banco/` e blindagem ampliada pos-diagnostico GitHub. Executado em 2026-05-28 na Fase 2 de blindagem local apos `[CRITICAL_FINDING]`: adicionada secao defensiva para `banco/`, `banco_runtime/`, `banco_template/`, `dados/`, `logs/`, `reports/`, `relatorios/`, `release/`, `runtime_private/`, `.snapshots/`, `data/state/window_state.json`, credenciais, usuarios, bancos locais, backups, ambientes, caches, build e ferramentas locais/agentes. Nenhum arquivo fisico foi removido, movido, aberto ou compactado.
- [ ] [Pendente] **HIG-009** (HIG/ARQT) - Planejar separacao futura de `banco_template/` (esquema/vazio, distribuivel) e `banco_runtime/` (gerado na instalacao, nao distribuir) com bootstrap seguro. Origem: DEC-002 (2026-05-15). Requer refatoracao de ~18 arquivos `.py` que referenciam `banco/`; executar em rodada de codigo separada apos PRIV-001 e GIG-001. Nao bloqueia nenhuma outra tarefa HIG ou PRIV.
- [x] [Concluido] **LOG-UNIF-001** (LOG/CONFIG) - Uniformizar locais de gravacao de logs para root unico `logs/`. Executado em 2026-05-29. Correcoes: (1) `config/default_config.json`: `logs_dir` corrigido de `"dados/banco"` (bug) para `"logs"`; (2) `utils/audit_logger.py`: `AuditLogger.__init__` passa a aceitar `None` e consulta `config_service.get_paths()` via `_resolve_audit_log_dir()`; (3) `services/legacy_panel_governance.py`: `DEFAULT_LOG_PATH` substituido por `_resolve_default_log_path()` com config service + env var + fallback; (4) `utils/dataframe_reporter.py`: `DataFrameReporter.__init__` passa a aceitar `None` e consulta config service via `_resolve_dataframe_log_dir()`. Teste-guardiao: `tests/test_log_paths_uniformization.py` (9 casos, 9 passed). Regressao: 41 testes preexistentes passaram sem falha.
- [x] [Concluido] **LOG-UNIF-002** (LOG/ARQT) - Uniformizar fallbacks de paths de pastas de dados (banco*, dados/banco). Executado em 2026-05-29. Correcoes de codigo: (1) `services/path_resolver.py`: fallback de `resolve_banco_dir()` alterado de `banco/` para `banco_runtime/`; (2) `services/engine/config_loader.py`: `ConfigLoader.BASE_PATH` alterado de `Path("banco")` para `Path("banco_template")` — `get_equipment_profiles()` agora encontra os JSONs reais em `banco_template/profiles/`; (3) `scripts/normalize_legacy_csv_utf8.py` e `scripts/scan_csv_encoding_conformance.py`: `DEFAULT_ROOTS` ampliado para incluir `banco_runtime`. Migracao de dados: `corridas_vr1e2_biomanguinhos_7500.csv` (296KB) e `corridas_zdc_biomanguinhos.csv` (42KB) movidos de `dados/banco/` para `logs/` (local correto — codigo usa `logs_dir`); backup em `snapshots/dados_banco_backup_20260529/`. `historico_analises.csv` (280KB) ja estava em `logs/` (gravado apos correcao do `logs_dir`). Teste-guardiao: `tests/test_banco_path_fallbacks.py` (7 casos, 7 passed). Regressao: 48 testes preexistentes passaram sem falha. DHPs abertas: DHP-10 (`dados/banco/historico.db`, 131KB, mais antigo), DHP-11 (CSVs duplicados residuais em `dados/banco/` apos migracao), DHP-12 (`banco_template/historico.db`, 3.3MB, conteudo desconhecido).
- [ ] [Pendente] **DHP-10** (DHP/DADOS) - Verificar conteudo de `dados/banco/historico.db` (131KB, 25/05/2026, mais antigo dos 4) antes de qualquer exclusao ou arquivamento. Pode ser DB inicial vazio ou snapshot de desenvolvimento. Nao excluir sem inspecao humana. Requer rodada controlada com ambiente LGPD-adequado (ver PRIV-001).
- [ ] [Pendente] **DHP-11** (DHP/DADOS) - Verificar e decidir destino dos CSVs duplicados residuais em `dados/banco/` apos migracao das corridas: `equipamentos.csv`, `exames_config.csv`, `placas.csv`, `regras.csv`, `usuarios.csv` (todos mais antigos e desatualizados versus `banco_runtime/`). Opcoes: arquivar, ignorar ou excluir em rodada de limpeza autorizada. Conteudo de `usuarios.csv` nao deve ser aberto sem ambiente controlado (PRIV-001).
- [ ] [Pendente] **DHP-12** (DHP/DADOS) - Verificar conteudo de `banco_template/historico.db` (3.3MB, 25/05/2026, o maior dos 4). Tamanho superior ao ativo (`banco_runtime/historico.db`, 1.5MB) e suspeito: pode ser dados de desenvolvimento, snapshot de producao salvo erroneamente na pasta de template, ou dataset de testes. Inspecionar antes de qualquer exclusao, merge ou arquivamento. Nao excluir sem decisao humana documentada.
- [x] [Concluido com ressalvas] **GIT-001** (GIT/SEG) - Validar tracking e ignore com Git disponivel antes de qualquer commit/publicacao. Origem: Fase 1 de diagnostico read-only encerrada com `[CRITICAL_FINDING]` e Fase 2 de blindagem local (2026-05-28). Evidencia em 2026-05-28: `git --version` retornou `git version 2.54.0.windows.1`; `git ls-files` nao retornou arquivos rastreados; caminhos criticos `release/`, `banco/`, `banco_runtime/`, `banco_template/`, `dados/`, `logs/`, `reports/` e `relatorios/` foram confirmados como ignorados por `git check-ignore -v`. Ressalvas: `scripts/run_legacy_credentials_migration.py` e `test_data/*` permanecem candidatos a versionamento e exigem revisao/allowlist antes do primeiro commit; `.snapshots/` e `data/state/window_state.json` foram classificados como artefatos locais/runtime e cobertos pelo `.gitignore`. Nenhum `git add`, commit, push, `git rm --cached`, remocao ou movimentacao foi executado.
- [ ] [Pendente] **GIT-002** (GIT/SEG) - Definir allowlist final de primeiro commit. Antes de qualquer `git add`, revisar explicitamente `scripts/run_legacy_credentials_migration.py`, `test_data/*`, `.claude/`, `.specify/`, `config.json`, `config/default_config.json` e demais candidatos de `git ls-files --others --exclude-standard`. `config.json` e `config/default_config.json` permanecem versionaveis apenas como templates/configuracoes locais sem dados reais conforme DEC-001; `test_data/*` so pode ser versionado se confirmado como fixture sintetico/anônimo, sem dados pessoais, laboratoriais reais ou credenciais.
- [x] [Concluido] **REL-001** (RELEASE/ASSET) - Formal acceptance de `assets/icon.ico` registrada documentalmente em 2026-05-17. Origem: achado do mapeamento READ-ONLY de 2026-05-15: `ui/main_window.py:256` referencia `os.path.join(BASE_DIR, "assets", "icon.ico")` mas o diretorio `assets/` nao existe fisicamente; a aplicacao trata a ausencia de forma silenciosa (janela sem icone). Decisao humana autorizada em 2026-05-17: a ausencia de `assets/icon.ico` e aceita formalmente como ressalva nao bloqueante para o release piloto (3 a 5 usuarios), desde que o sistema abra sem erro critico no smoke-test. Nenhum arquivo de icone foi criado nesta rodada. A providencia de um icone oficial permanece como melhoria futura antes de versao final/distribuicao ampla. Evidencia: `docs/specs/higienizacao_implantacao.md §6.4` e `§6.7` atualizados; `docs/procedimento_smoke_test_release.md §11` atualizado; `docs/checklist_pos_instalacao.md §6` atualizado; README atualizado.
- [x] [Concluido] **REL-002** (RELEASE/DOCS) - Criar e aprovar checklist de validacao pos-instalacao para `release/docs_operacionais/`. Executado em 2026-05-16. Evidencia: `docs/checklist_pos_instalacao.md` criado com 7 secoes (identificacao do ambiente, pre-condicoes, Instalacao Inicial, abertura, operacional minima, restricoes conhecidas e resultado). Aprovado para piloto controlado de 3 a 5 usuarios. Restricoes REL-001 e REL-003 registradas na secao 6. `docs/specs/higienizacao_implantacao.md` §6.3 e `README.md` §10 atualizados.
- [x] [Concluido] **REL-003** (RELEASE/VALID) - Definir formalmente o procedimento de smoke-test em copia limpa para validacao do pacote de release antes da materializacao. Executado em 2026-05-17. Evidencia: `docs/procedimento_smoke_test_release.md` criado com 11 secoes (identificacao, objetivo, pre-condicoes, verificacao estrutural, verificacao de exclusoes, smoke-test funcional, criterios de aprovacao, criterios de reprovacao automatica, registro de evidencia, relacao com checklist pos-instalacao e pendencias conhecidas). `docs/specs/higienizacao_implantacao.md §6.7` atualizado com referencia ao procedimento. `README.md §10` e `docs/checklist_pos_instalacao.md` atualizados. Procedimento aprovado como formal; nao executado nesta rodada. REL-001 permanece pendente.
- [x] [Concluido] **REL-004** (RELEASE/SCRIPT) - Criar script PowerShell de materializacao por whitelist para construcao controlada de `release/`. Executado em 2026-05-17. Evidencia: `scripts/build_release_whitelist.ps1` criado com whitelist explicita do manifest HIG-008 (§6.1-§6.6), suporte a `-WhatIf`/dry-run via parametro `-Execute` (ausencia = simulacao), protecao contra sobrescrita de `release/` existente, validacao de itens proibidos pos-copia, geracao opcional de `MANIFEST.txt` com SHA-256, verificacoes positivas de obrigatorios (`models.py`, `config.json`, `README.md`, `checklist_pos_instalacao.md`) e verificacoes negativas de proibidos (`banco/`, `.env*`, `relatorio_final_corrida_*.json`, `window_state.json`, legados). **O script NAO foi executado nesta rodada. `release/` NAO foi criada. Nenhum arquivo foi copiado, movido ou removido.** Ressalva REL-001 registrada no script (`assets/icon.ico` ausente — nao bloqueante para piloto). Proxima acao: execucao do dry-run com `-WhatIf` em rodada futura autorizada, seguida de execucao real com `-Execute` em rodada propria; em seguida, smoke-test conforme `docs/procedimento_smoke_test_release.md`. PRIV-001, GIG-001, HIG-009, CONC-* e INST-* permanecem pendentes e nao foram afetados.
- [x] [Investigado (Fase 2)] **T-AUD-016** (DT/AUD-REF) - Forensics do import circular `exportacao/envio_gal.py:84` (`from ui.gal_ui_dialog_adapter import GalUIDialogAdapter`, top-level) <-> `ui/__init__.py:11` (import eager de `main_window`) <-> `ui/menu_handler.py:16` (`from exportacao.envio_gal import abrir_janela_envio_gal`). Severidade: Alto. Descoberta: 2026-06-01 (Fase 0 Audit Refactoring, durante T-002 — validacao dos 10 callers de `csv_safety`). O import resolve sob ordem de boot real (ui-first, como `main.py:16`); falha com `ImportError: cannot import name 'abrir_janela_envio_gal' ... partially initialized module` sob ordem nao-ui-first (ex.: comando literal do T-002). Presente no HEAD baseline `f28ce1e` — **nao e regressao do `csv_safety`** (restaurado identico ao HEAD). Coincide com a janela do incidente 2026-05-23 (`docs/obsoletos/incidents/revert_envio_gal_20260523.txt`). Enderecar em: Fase 2 (forensics, T-021/T-022) + Fase 6 (T-061, ao integrar `assert_valid_gal_payload` em `envio_gal.enviar_amostra`). Recomendacao: avaliar import lazy de `GalUIDialogAdapter` na funcao consumidora, com cobertura previa. **Nao-bloqueante** para Fase 1. Ref.: `specs/audit_refactoring/spec.md §8.3` (desvio D-3); `notas_de_passagem.md` (sessao 2026-06-01).
  - **Analise (Fase 2):** cadeia de imports completa + uso real de `GalUIDialogAdapter` (envio_gal.py:84 import, ~1468 instanciacao no `__init__` de `IntegrationApp`, ~1619 uso em `selecionar_csv`) + 3 opcoes de fix avaliadas em `snapshots/forensics_t_aud_016_import_circular.md`. Lazy import viavel (ALTA); recomendacao de longo prazo = inversao via Port/Protocol (Opcao B), convergente com ADR-A6 / Spec US-6.
  - **Proxima acao:** Endereçar em Fase 6 (T-061) — substituir dependencia top-level de UI por injecao via Port (Opcao B preferida; Opcao A lazy como mitigacao intermediaria), com cobertura previa de teste do ciclo (importar `envio_gal` isolado). Conforme ADR-A6 / Spec US-6.
- [ ] [Pendente] **T-AUD-017** (SEG/AUD-REF) - Credencial hardcoded em modulo legado: `core/authentication/user_manager.py:~1811` (`password="admin123456"`). Severidade: Medio (legado import-banido, nao runtime). Descoberta: 2026-06-01 (Fase 0 Audit Refactoring, durante T-006 — guardiao `no_hardcoded_credentials`). Modulo ja em deprecacao controlada (DEC-003) e import-banido em runtime (T-AUD-004A, recriado em T-011/Fase 1). O guardiao `tests/test_no_hardcoded_credentials.py` exclui `core/` deliberadamente e documenta este achado. Enderecar em: rodada futura conjunta com remocao fisica do legado (depende de DEC nova; ver CLAUDE.md §15.2). **Nao-bloqueante** para Fase 1; o guardiao T-011 (allowlist vazia) protege contra reativacao runtime. Ref.: `notas_de_passagem.md` (sessao 2026-06-01).
- [ ] [Pendente] **T-AUD-018** (D-06/L-T07) - BOM UTF-8 em 3 modulos de `domain/`. Severidade: Baixo (mitigado nos guardioes). Descoberta: 2026-06-01 (Fase 1 Audit Refactoring). Origem: achado durante T-010 (criacao do guardiao T-AUD-008). Arquivos afetados: `domain/__init__.py`, `domain/ct_rules.py`, `domain/plate_mapping.py` (todos iniciam com `EF BB BF`, confirmado por inspecao de bytes). O skeleton original de T-010 usava `read_text("utf-8")` e quebrava em `ast.parse` com `SyntaxError: U+FEFF`; mitigado nos guardioes T-010 e T-011 trocando para `utf-8-sig`. `domain/` permanece com BOM fisico. Correlato: T-AUD-014 (BOM removido de `ui/user_management.py`). Enderecar em: rodada housekeeping futura (`utils/remove_bom.py` ja existe para esse fim). **Nao-bloqueante** para Fase 2. Ref.: `notas_de_passagem.md` (sessao 2026-06-01).

### Rastreabilidade

| Achado | Tarefa | Status |
|---|---|---|
| D-01 | T-AUD-001 (depende T-AUD-008) | Concluido |
| D-02 | T-AUD-002 + T-AUD-003 | Concluido/Concluido |
| D-03 | T-AUD-RD-DESIGN | Concluido |
| D-04 | T-AUD-004 + T-AUD-004A + T-AUD-004B + T-AUD-013 | Concluido/Concluido/Concluido/Pendente |
| D-05 | T-AUD-005 | Pendente |
| D-06 | T-AUD-006 | Concluido (documental, HIG-007 Opcao A) |
| D-07 | T-AUD-007 (+ requirements.md CA-11) | Concluido |
| D-08 | T-AUD-008-CFG | Concluido |
| D-09 | T-AUD-009 | Concluido |
| D-10 | T-AUD-012 (classificacao operacional) | **Concluido (microfase 3.1)** |
| D-11 | T-AUD-011 | Concluido (fallback declarado, DEC-002, 2026-05-15) |
| D-12 | T-AUD-RD-SCOPE | Concluido |
| L-T01 | T-AUD-007 | Concluido |
| L-T02 | T-AUD-003 | Concluido |
| L-T03 | T-AUD-008 | Concluido |
| L-T04 | T-AUD-004A + T-AUD-004B + T-AUD-013 | Concluido/Concluido/Pendente |
| L-T06 | T-AUD-014 | Concluido |
| L-T05 | T-AUD-008-CFG | Concluido |
| R-T3 | T-AUD-010 | Pendente |
| SDD-20260514-001 | Semantica de relatorio final pre-GAL | Concluido |
| SDD-20260514-002 | Completude VR1e2 placa cheia | Concluido |
| SDD-20260514-003 | Normalizacao de extrator contratual | Concluido |
| UI-AUD-001 | Inventario UI canonico | Pendente |
| UI-AUD-002 | Reaplicar Selecao por aptidao operacional | Concluido |
| UI-AUD-003 | Plano de modernizacao UI | Pendente |
| HIG-001 | Auditoria `.tmp/pytest_tmp` e `.env.txt` | Concluido |
| HIG-002 | Auditoria `reports/`, `relatorios/` e `logs/` | Concluido |
| SDD-REQ-20260514-001 | Sincronizar `requirements.md` com T-AUD-008-CFG | Concluido |
| SDD-REQ-20260514-002 | Sincronizar `requirements.md` com DEC-003 | Concluido |
| CONFIG-ENC-001 | Mojibake residual em `_comentario` de `config.json` | Pendente |
| HIG-003 | Classificacao de scripts de limpeza | Concluido |
| HIG-004 | Atualizar `.gitignore` em rodada propria | Concluido |
| HIG-005 | Classificar destino de `banco/*` | Concluido (documental, Opcao A, 2026-05-15) |
| HIG-006 | Politica para `snapshots/encoding_backup_*` | Concluido (documental, Opcao A, 2026-05-15) |
| HIG-007 | Politica para `relatorio_final_corrida_*.json` | Concluido (Opcao A, documental) |
| HIG-008 | Manifest/estrutura limpa de release | Concluido |
| RELEASE-001 | Baseline/backup antes de limpeza/deploy | Concluido |
| CONC-001 | Decisao/requisito sobre 10 usuarios ou piloto 3-5 | Pendente |
| CONC-002 | Teste multiprocess 10 usuarios em CSVs criticos | Pendente |
| CONC-003 | Claim/lease GAL antes do envio externo | Pendente |
| CONC-004 | Dois admins aplicando instalacao/config | Pendente |
| CONC-005 | Validar SQLite em compartilhamento | Pendente |
| CONC-006 | Validar logs com 10 processos | Pendente |
| INST-001 | Lock/atomic write para `config.json` | Concluido |
| INST-002 | Dry-run e resumo antes de aplicar instalacao | Concluido |
| INST-003 | Backup/rollback da instalacao | Concluido |
| INST-004 | Ajuste ADMIN+MASTER na Instalacao Inicial | Pendente |
| INST-005 | Teste end-to-end do wizard de instalacao | Pendente |
| PRIV-001 | Auditoria LGPD/controlada de `banco/*` | Pendente |
| GIG-001 | Estender `.gitignore` para CSVs operacionais de `banco/`, artefatos runtime e blindagem local pos-critico | Concluido (2026-05-28) |
| HIG-009 | Planejar separacao `banco_template/` + `banco_runtime/` | Pendente |
| LOG-UNIF-001 | Uniformizar locais de gravacao de logs para root unico `logs/` | Concluido (2026-05-29) |
| LOG-UNIF-002 | Uniformizar fallbacks de paths de pastas de dados (banco*, dados/banco) | Concluido (2026-05-29) |
| DHP-10 | Verificar `dados/banco/historico.db` (131KB, mais antigo) | Pendente |
| DHP-11 | CSVs duplicados residuais em `dados/banco/` apos migracao | Pendente |
| DHP-12 | Verificar `banco_template/historico.db` (3.3MB, suspeito) | Pendente |
| GIT-001 | Validar tracking/ignore com Git disponivel antes de commit/publicacao | Concluido com ressalvas (2026-05-28) |
| GIT-002 | Definir allowlist final de primeiro commit | Pendente |
| REL-001 | Formal acceptance de assets/icon.ico — ausencia aceita como ressalva nao bloqueante para piloto | Concluido (documental, 2026-05-17) |
| REL-002 | Criacao do checklist pos-instalacao (docs_operacionais) | Concluido |
| REL-003 | Definicao formal do procedimento de smoke-test | Concluido |
| REL-004 | Script de materializacao por whitelist (`scripts/build_release_whitelist.ps1`) | Concluido (script criado; release/ nao materializada; 2026-05-17) |
| AUD-REF-F0 (T-002) | T-AUD-016 — forensics import circular envio_gal <-> ui | Investigado (Fase 2; fix em Fase 6/T-061) |
| AUD-REF-F0 (T-006) | T-AUD-017 — credencial hardcoded em legado user_manager | Pendente (rodada futura, DEC nova) |
| AUD-REF-F1 (T-010) | T-AUD-018 — BOM UTF-8 em 3 modulos de domain/ | Pendente (housekeeping futuro) |
| AUD-REF-F4 (T-045) | T-AUD-022 — fixtures externas em generate_phase0_baseline.py | Pendente (housekeeping futuro) |
| Ativ. HIG-008/2026-05-15 | Dry-run, mapeamento de imports e refinamento documental | Concluido (ver notas) |

### T-AUD-022 (DT/L-T11) — generate_phase0_baseline.py referencia fixtures externas

**Descoberta:** Fase 4 Audit Refactoring (T-045 etapa 1, achado extra)
**Severidade:** Baixo
**Status:** [ ] Pendente
**Origem:** Subagente do T-045 detectou que scripts/generate_phase0_baseline.py
referencia fixtures .xlsx externas em `Downloads\18 JULHO 2025\`. NAO
refatorado em T-045 porque o guardião T-044 ficou restrito a literal
`Downloads/Integragal` (escopo Fase 4).
**Recomendação:**
(a) Mover fixtures para `tests/fixtures/phase0_baseline/` (caminho versionado),
    OU
(b) Parametrizar via env var `PHASE0_FIXTURES_DIR` com fallback claro,
    OU
(c) Marcar script como `manual-only` em README + adicionar guard explícito.
**Endereçar em:** rodada housekeeping futura ou junto à formalização de
`tests/fixtures/`. Não-bloqueante para Fases 5+.

### T-050 — DHP "política de senha/lockout" formalizada

**Data:** 2026-06-02
**Severidade:** N/A (decisão humana)
**Status:** [x] Aprovada
**Referência:** docs/specs/decisoes_humanas/DHP-senha-lockout.md
**AC vinculada:** AC-7.1
**Parâmetros:** MAX_TENTATIVAS_FALHAS=5; BLOQUEIO_DURACAO_MINUTOS=15 (auto-desbloqueio);
admin reset via UI (matriz `users.mutate`); senha min 8 chars (mantido do legado);
hash bcrypt mantido; feedback UI genérico (OWASP A07); complexidade extra deferida p/ Fase 9.
Pré-requisito de T-051..T-053 (Fase 5 Audit Refactoring).

### T-051-FIND-SQLITE — Lockout não persiste no backend SQLite

**Data:** 2026-06-02
**Descoberta:** Fase 5 (T-052, validação adversária da persistência)
**Severidade:** Média (fail-open SOMENTE se `storage_backend` for trocado para `sqlite`)
**Status:** [ ] Pendente (não-bloqueante — backend ativo é `csv`)
**Detalhe:** `SQLiteUserRepositoryAdapter.update` (services/persistence/persistence_adapters.py)
mapeia apenas `nivel_acesso/senha_hash/ultimo_login/ativo`; **não** persiste
`failed_attempts`/`locked_until`. Logo, com backend SQLite o lockout server-side
da Fase 5 viraria no-op silencioso (fail-open). O backend ativo
(`config.json: storage_backend="csv"`) suporta os campos corretamente, então o
lockout funciona em produção atual.
**Recomendação:** antes de migrar usuários para SQLite, estender o schema/adapter
SQLite com `tentativas_falhas`/`bloqueado_ate` + mapeamento no `update`.
Coordenar com CONC-005 (validar SQLite em compartilhamento) e Fase 9.

### T-051-FIND-UIMSG — login.py revela "tentativas restantes" (OWASP A07)

**Data:** 2026-06-02
**Descoberta:** Fase 5 (verificação adversária pós-T-052)
**Severidade:** Média (enumeração/leak na camada UI)
**Status:** [ ] Pendente (fora do escopo da Fase 5 por §9 — não tocar login.py)
**Detalhe:** `autenticacao/login.py` ainda exibe `"Credenciais invalidas.
N tentativa(s) restante(s)."` e `"Acesso Bloqueado / Numero maximo de
tentativas excedido!"` (throttle client-side legado em memória, MAX=3). Isso
contradiz o objetivo OWASP A07 da DHP (mensagem **genérica** na UI). A camada
de serviço (`autenticar_credenciais`) já está conforme: retorna `None` uniforme
sem distinguir motivo. A divergência é apenas na apresentação.
**Recomendação:** trocar as mensagens de `login.py` por
`"Credenciais inválidas. Verifique usuário e senha."` (sem contagem nem estado
de bloqueio) e avaliar aposentar o throttle client-side em favor do lockout
server-side. Endereçar em rodada UI/Fase 9 (hardening), com teste-guardião.

### T-AUD-023 (BUG/L-T12) — login.py vaza 'N tentativas restantes' (OWASP A07 UI)

**Descoberta:** Fase 5 Audit Refactoring (T-051, achado pos-impl)
**Severidade:** ALTO (viola DHP politica-senha-lockout recém-aprovada)
**Status:** [x] Fix imediato — mini-tarefa Fase 5 fechamento
**Origem:** DHP politica-senha-lockout especifica mensagem UI
genérica (OWASP A07). Serviço cumpre (sempre retorna None em falha),
MAS autenticacao/login.py:193-197,200-203 ainda exibe:
- "Credenciais invalidas. {N} tentativa(s) restante(s)."
- "Numero maximo de tentativas excedido!"
Ambas vazam informação: contador revela quantas tentativas restam;
mensagem "excedido" revela que conta foi bloqueada.
**Fix:** unificar TODAS as mensagens em
"Credenciais inválidas. Verifique usuário e senha." (mesma do
serviço). Manter sys.exit(1) ao esgotar contador local (UX), mas
sem mensagem específica de "excedido".
**Endereçar:** AGORA (mini-tarefa T-AUD-023 antes da Fase 6).
**Nota:** formaliza/supersede o achado preliminar `T-051-FIND-UIMSG` acima.

### T-AUD-024 (DT/L-T13) — SQLiteUserRepositoryAdapter.update não persiste lockout

**Descoberta:** Fase 5 Audit Refactoring (T-051, review inline)
**Severidade:** Médio (latente; CSV é backend ativo)
**Status:** [ ] Pendente — implementar quando houver decisão de
trocar backend para SQLite.
**Origem:** Helper `_persistir_estado_tentativas` em
autenticacao/auth_service.py usa `repo.update` cirúrgico. Backend CSV
(ativo) tem implementação correta. Backend SQLite
(SQLiteUserRepositoryAdapter.update) ainda não persiste campos
tentativas_falhas/bloqueado_ate — fail-open silencioso se backend
for trocado.
**Recomendação:** Estender SQLiteUserRepositoryAdapter.update para
incluir os 2 campos com transação atômica. Adicionar teste de
paridade tests/test_lockout_persistence_sqlite_parity.py.
**Endereçar em:** dia em que houver DEC de migração de backend para
SQLite. Não-bloqueante hoje (0 callers SQLite).
**Nota:** formaliza/supersede o achado preliminar `T-051-FIND-SQLITE` acima.

### Refinamento do manifest HIG-008 — atividades executadas (2026-05-15)

Rodada de release engineering executada em modo READ-ONLY + documental (anterior ao rescoping de REL-001/002/003):

- Dry-run (simulacao): simulou conteudo do pacote por manifest HIG-008 original; classificacao PRONTO COM RESSALVAS; revelou 12 itens sem classificacao explicita no manifest.
- Mapeamento de imports: analise estatica de imports Python e grep em arquivos nao-Python classificou todos os 12 itens. Achado critico: `models.py` (RUNTIME OBRIGATORIO, importado por 4 modulos de producao) estava ausente do §6.1 — lacuna corrigida. Outros achados: `analise/` e `extracao/` legados; `data/state/` placeholder runtime necessario; `images/` excluido por padrao; `config/backups/` inexistente.
- Refinamento documental: `docs/specs/higienizacao_implantacao.md` atualizado em §6.1, §6.3, §6.4, §6.6, §6.7. Demais documentos: `tasks.md`, `inventario_de_lixo.md`, `documento_de_passagem.md`, `notas_de_passagem.md`.
- Nenhum arquivo de codigo, `config.json`, `banco/*`, relatorio, log, snapshot, script ou artefato foi aberto, alterado, movido, arquivado ou excluido.

### Microchecagem REL-001/REL-002/REL-003 (2026-05-15)

Verificacao de status executada na mesma data para confirmar se [Concluido] estava correto para REL-001/002/003:

- REL-001: ausencia de `assets/icon.ico` nao foi formalmente aceita (§6.4 exige acao antes da materializacao) — evidencia insuficiente para [Concluido].
- REL-002: checklist pos-instalacao marcado em §6.3 como "nao existe fisicamente ainda" — apenas planejado, nao criado — evidencia insuficiente para [Concluido].
- REL-003: procedimento de smoke-test apenas sugerido em §6.7 como criterio generico sem roteiro formal — evidencia insuficiente para [Concluido].
- Resultado: REL-001/002/003 rescoped para representar o trabalho futuro nao bloqueante e marcadas como [Pendente]. Atividades executadas rastreadas na nota "Refinamento do manifest HIG-008 — atividades executadas (2026-05-15)" acima.
- HIG-008 permanece [Concluido] como manifest documental refinado.

## 11. GAL — Robustez, Observabilidade, UX e Dashboard (2026-05-30)

Rodada de melhorias SDD executada sobre o modulo "Enviar para o GAL" e o Dashboard. Todas as alteracoes foram precedidas de analise critica READ-ONLY, testes de regressao (77 passed) e pontos de rollback por feature flag.

### 11.1 Robustez e correcao de bugs criticos

- [x] [Concluido] **GAL-ROB-001** — S4: Excecao de worker registrada estruturadamente (status `erro_critico`, traceback no campo `erro`, entrada no journal) em vez de `print()` silencioso. Arquivo: `application/gal_send_use_case.py`.
- [x] [Concluido] **GAL-ROB-002** — S2: Lote nao abortado quando `buscar_metadados` retorna vazio; aviso `[S2]` emitido e amostras marcadas `nao_encontrado`. Arquivo: `application/gal_send_use_case.py`.
- [x] [Concluido] **GAL-ROB-003** — S5: Falhas de paginas de metadados acumuladas e reportadas explicitamente no terminal ao final da paginacao paralela. Arquivo: `exportacao/envio_gal.py`.
- [x] [Concluido] **GAL-ROB-004** — S10: Leitura e validacao do CSV antecipadas para antes da abertura do Firefox (falha cedo, sem custo de sessao). Arquivo: `application/gal_send_use_case.py`.
- [x] [Concluido] **GAL-ROB-005** — S11: Aviso antecipado `[S11]` quando `gal_exame_codigo` esta ausente no exam_cfg, antes de iniciar sessao GAL. Elimina raiz do bug "0 encontrados". Arquivo: `application/gal_send_use_case.py`.
- [x] [Concluido] **GAL-ROB-006** — S14: Campos identificaveis (`paciente`, `nomePaciente`, `_raw`) mascarados com `***` na resposta do servidor antes de logar. Arquivo: `exportacao/envio_gal.py`.
- [x] [Concluido] **GAL-ROB-007** — S22: `inflight_keys` atomicas sob lock previnem envio duplo de linhas identicas no mesmo CSV (race condition check-then-send resolvida). Arquivo: `application/gal_send_use_case.py`.
- [x] [Concluido] **GAL-ROB-008** — S23: `_build_key_from_row` aplica `_normalize_key_dates` (DD/MM/YYYY → ISO), mesma normalizacao do lado journal; eliminava `nao_enviado` falso para amostras ja enviadas. Arquivo: `services/gal/gal_status_reconciler.py`.
- [x] [Concluido] **GAL-ROB-009** — S24: `validate_gal_payload` valida nao-vazio de `codigo` (sempre derivavel de `codigoAmostra`); `requisicao`/`paciente` excluidos para compatibilidade com modo sem metadados. Arquivo: `exportacao/gal_payload_contract.py`.
- [x] [Concluido] **GAL-ROB-010** — Fallback por `codigo_amostra` no reconciliador quando `kit`/`lote` ausentes em `exam_run`; evita status `sem_chave_gal` para amostras enviadas sem esses campos no `historico.db`. Arquivo: `services/gal/gal_status_reconciler.py`.
- [x] [Concluido] **CONFIG-PATH-001** — `config.json` corrigido: `paths.logs_dir` de `"dados/banco"` para `"logs"` (elimina pasta `dados/dados/`); `paths.gal_history_csv` e `paths.gal_upload_history_csv` de `"logs/total_importados_gal.csv"` para `"logs/historico_analises.csv"` (nome canonico e localizacao consistente). Rodada especifica autorizada. Arquivo: `config.json`.

### 11.2 Features e toggles operacionais

- [x] [Concluido] **GAL-FEAT-001** — Feature flag `USE_GAL_ENVIO_SEM_METADADOS`: pula `/bmh/entrada-resultados/lista/`, usa `codigoAmostra` como `codigo`/`registroInterno`; `requisicao`/`paciente` ficam vazios para o GAL localizar pelo par `codigo+gal_exame_codigo`. Toggle disponivel em Configuracoes GAL (`gal_integration.envio_sem_metadados`). Rollback: `enabled=false`. Arquivos: `config/feature_flags.json`, `application/gal_send_use_case.py`, `exportacao/envio_gal.py`.
- [x] [Concluido] **GAL-FEAT-002** — `construir_payload`: campo `codigo` usa `codigoAmostra` do CSV como fallback quando `meta` esta vazio ou `meta["codigo"]` e vazio; payload nunca enviado com `codigo` vazio. Arquivo: `exportacao/envio_gal.py`.
- [x] [Concluido] **GAL-FEAT-003** — Firefox headless habilitado por default (`gal_integration.headless: true` no `config.json`; `_default_webdriver_factory` usa `.get("headless", True)`). Confirmacao de login explicitada no terminal. Toggle disponivel em Configuracoes GAL. Feature flag `USE_GAL_FIREFOX_HEADLESS` para override de desenvolvedor. Rollback: desativar flag + config. Arquivos: `application/gal_send_use_case.py`, `config/feature_flags.json`, `config.json`.
- [x] [Concluido] **GAL-FEAT-004** — Terminal de envio GAL exibe linha por amostra (`codigoAmostra → STATUS`, com detalhe de erro ate 70 chars, colorido por nivel). Feature flag `USE_GAL_TERMINAL_LOG_POR_AMOSTRA` (`enabled=true` por default; `false` reverte para resumo final apenas). Arquivo: `application/gal_send_use_case.py`.
- [x] [Concluido] **GAL-FEAT-005** — Secao "Comportamento do Envio" adicionada nas Configuracoes GAL com dois toggles: "Ocultar navegador durante envio" e "Enviar sem buscar metadados do GAL". Arquivo: `ui/modules/tela_configuracoes.py`.
- [x] [Concluido] **GAL-PERF-001** — Janela de busca de metadados reduzida de 365 para 15 dias. Arquivo: `exportacao/envio_gal.py`.

### 11.3 Dashboard e relatórios

- [x] [Concluido] **DASH-001** — Dashboard principal usa `ExamRunsSQLiteRepository` (`banco_runtime/historico.db`) como fonte primaria, com status GAL por amostra via `reconcile_gal_status`; fallbacks CSV/db_utils mantidos. Arquivo: `ui/modules/dashboard.py`.
- [x] [Concluido] **DASH-002** — Gestao Clinica: campos "De" / "Ate" (DD/MM/AAAA) + botao "Filtrar" para intervalo de datas especifico. `DashboardAnalyticsService.obter_estatisticas_gestao` aceita `data_inicio`/`data_fim`; period_days ignorado quando datas fornecidas. Arquivos: `ui/modules/dashboard.py`, `services/reports/dashboard_analytics.py`.
- [x] [Concluido] **DASH-FIX-001** (2026-05-30) — `CardResumo.set_valor`/`set_indicativo` adicionados (corrige cards da Gestao zerados por `AttributeError` silencioso); update de Gestao/Visao Analitica desacoplado do CSV do Operacional em `_finalizar_carregamento`. Arquivos: `ui/modules/componentes/card_resumo.py`, `ui/modules/dashboard.py`.
- [x] [Concluido] **DASH-003** (2026-05-30) — "Doencas Mais Positivas" deduplicado: conta apenas colunas canonicas `RES_*` (elimina "SRC RES X" e controles `RP|CN|CP|GERAL`), corrige Positividade, rotulos limpos (`limpar_nome_alvo`), Top 12. Arquivo: `services/reports/dashboard_analytics.py`.
- [x] [Concluido] **DASH-004** (2026-05-30) — Gestao Clinica: quadro com barra (Top 10 + rotulos) + radar + pizza (Top 8 + "Outros") numa unica `Figure`, tabela-resumo lateral (Alvo/Positivos/%) e rotulos em negrito. Arquivo: `ui/modules/dashboard.py`.
- [x] [Concluido] **DASH-005** (2026-05-30) — Nova aba "Visao Analitica": `obter_painel_analitico` (KPIs Volume 15d / Volume-dia / Positividade / Pendentes GAL; heatmap dia x doenca; tabela de Ct 15/7/3 dias com setas ▲▼➖ e % de variacao; positividade por alvo). Clique num alvo destaca no heatmap e na tabela (`_selecionar_alvo`). Fontes ampliadas (+100%). Pendentes GAL = status reconciliado != `enviado`/`duplicado`. Arquivos: `services/reports/dashboard_analytics.py`, `ui/modules/dashboard.py`.
- [x] [Concluido] **DASH-006** (2026-05-30) — Barra de filtros reutilizavel (`_criar_barra_filtros`: Periodo/Exame/De-Ate/Filtrar) nas abas Operacional (filtra cards/grafico/tabela via `_df_operacional`/`_janela_filtro`) e Visao Analitica (somente Exame). Arquivo: `ui/modules/dashboard.py`.
- [x] [Concluido] **DASH-007** (2026-05-30) — Detalhe da corrida read-only: coluna "Corrida" (`nome_corrida`) na lista; janela de resultados (`Treeview`, sem edicao) corrigida — bug de import `ui.theme.design_tokens` substituido por `CORES`/`FONTES` de `.estilos`; colunas limpas (Amostra/Poco/Resultado/Status + `Res`/`Ct` por alvo). Botao "Abrir Mapa Definitivo (Excel)" abre o `mapa_placa_*.xlsx` gerado na analise em `<data_root>/mapas` via `_localizar_mapa_definitivo`. Arquivo: `ui/modules/dashboard.py`.
- [x] [Concluido] **DASH-008** (2026-05-30) — Tabela "Corridas Recentes": caixa de busca lateral desativada; barra de rolagem reancorada no mesmo container da tabela; ordenacao por clique no cabecalho (`_ordenar_tabela`/`_sort_key`: 1o clique ascendente, 2o descendente; `Data/Hora` ordena cronologicamente). Arquivo: `ui/modules/dashboard.py`.
- [x] [Concluido] **CFG-UI-001** (2026-05-30) — `tela_configuracoes._carregar_categoria` chama `_carregar_valores()` ao montar categoria sob demanda; corrige switch "Ocultar navegador durante envio" exibido OFF apesar do default `gal_integration.headless=true`. Arquivo: `ui/modules/tela_configuracoes.py`.
- [x] [Concluido] **WIZ-UI-001** (2026-05-30) — Wizard de exames: Passo 1 reorganizado em grade compacta (cabe sem rolagem; botao "Editar Exame Selecionado" volta a ficar visivel); botao "Limpar Etapa" por passo (`clear_current_step`). Arquivo: `ui/modules/exam_creator/wizard.py`.
- [x] [Concluido] **CAL-UI-001** (2026-05-30) — `reports.SimpleCalendar` parametrizado com `date_format`; campos De/Ate da Gestao ganham botao de calendario (DD/MM/AAAA). Arquivos: `ui/modules/reports.py`, `ui/modules/dashboard.py`.

### 11.4 Pendências desta rodada

- [ ] [Pendente] **GAL-PEND-001** — S3/S6: Retry idempotente com classificacao de erro transitorio vs definitivo em `enviar_amostra()`. Erros definitivos confirmados pelo GAL: "ja liberado", "requisicao nao existe", "invalida". Erros transitorios: timeout, 5xx. Risco moderado — verificar idempotencia do endpoint `/gravar/` antes de implementar.
- [ ] [Pendente] **GAL-PEND-002** — S18: Suite de testes sem Selenium real (mocks de `driver.request()` e `GalService`). Pre-requisito para evolucao segura do modulo GAL.

### Notas de execucao

- Tarefas documentais da auditoria 2026-05-12 (`T-AUD-RD-*`) e da microfase 3.1 (`T-AUD-012`) foram concluidas sem alteracao de codigo, configuracao operacional, CSV, banco, snapshot ou artefato gerado.
- Tarefas de teste/codigo/configuracao pos-microfase 3.1 (`T-AUD-008`, `T-AUD-001`, `T-AUD-003`, `T-AUD-007`, `T-AUD-008-CFG`, `T-AUD-004A`, `T-AUD-004B`, `T-AUD-014`) foram registradas nas notas abaixo com suas evidencias objetivas.
- Tarefas marcadas `[Bloqueado por DHP]` permanecem aguardando decisao humana antes de qualquer acao de codigo ou de documentacao em rodadas subsequentes.
- Nenhuma decisao humana pendente foi resolvida pela execucao pos-microfase 3.1; permanecem pendentes DHP-02 (=DHP-09), DHP-04, DHP-05 e DHP-07.

### Notas de sincronizacao pre-higienizacao (2026-05-14)

Atualizacao documental SDD executada apos auditoria READ-ONLY de sincronizacao. Objetivo: alinhar `tasks.md`, `design.md`, `AGENTS.md`, `CLAUDE.md`, `documento_de_passagem.md`, `notas_de_passagem.md` e `inventario_de_lixo.md` ao estado real antes da auditoria de higienizacao para implantacao.

- **SDD-20260514-001 concluida**: relatorio final pre-GAL distingue analise concluida de envio GAL pendente. Pendencia normal usa `selecionado_pendente_envio` / `status_envio_gal=pendente_envio` / `analise_concluida_envio_pendente`, nao `selecionado_falha`.
- **SDD-20260514-002 concluida**: VR1e2 com placa cheia tem validacao de completude fail-closed; 96 pocos com agrupamento 2 pocos/amostra devem gerar 48 grupos, com `AnalysisCompletenessError` quando o contrato/mapeamento perde grupos.
- **SDD-20260514-003 concluida**: extrator por contrato normaliza aliases `bem/amostra/alvo/ct` para `Well/Sample/Target/Ct` antes do pipeline.
- **UI-AUD-002 concluida**: `Reaplicar Selecao` seleciona apenas itens operacionalmente aptos: repeticao `Nao`, RPs validos, placa valida e exclusao de CN/CP/controles.
- **UI-AUD-001/UI-AUD-003 pendentes**: inventario UI e plano de modernizacao continuam lacunas documentais; nenhum plano completo de UI foi executado nesta rodada.
- **HIG-001/HIG-002 concluidas em 2026-05-15**: auditoria READ-ONLY de higienizacao classificou `.tmp/pytest_tmp`, `.env.txt`, `reports/`, `relatorios/` e `logs/` sem abrir conteudo sensivel e sem executar limpeza.
- **SDD-REQ-20260514-001 concluida**: `requirements.md` sincronizado com T-AUD-008-CFG concluida, preservando `config.json` como template/local runtime.
- **SDD-REQ-20260514-002 concluida**: `requirements.md` sincronizado com DEC-003 resolvida e `user_manager.py` legado em deprecacao controlada.
- **CONFIG-ENC-001 pendente**: mojibake residual em `_comentario` de `config.json`; nao corrigido nesta rodada documental.
- **HIG-003 concluida em 2026-05-15**: scripts de limpeza classificados como potencialmente destrutivos; nao executar sem auditoria propria.
- **HIG-004..HIG-008 registradas**: backlog de `.gitignore`, DHPs de `banco/*` e snapshots, politica DEC-005 para `relatorio_final_corrida_*.json` e manifest de release.
- **RELEASE-001 concluida por evidencia declarada pelo usuario**: baseline `integragal_baseline_pre_higienizacao_2026-05-15.zip` registrado; nenhuma limpeza/deploy executado.

### Plano HIG formal (2026-05-15)

`docs/specs/higienizacao_implantacao.md` foi atualizado como plano formal de higienizacao por fases, sem executar limpeza ou alterar arquivos operacionais. O plano registra:

- Estado atual: classificacao **ATENCAO**, pasta nao pronta para empacotamento direto, baseline informado e scripts de limpeza bloqueados.
- Fases H0..H7: baseline/backup, `.gitignore`, separacao de artefatos runtime, retencao/arquivamento, auditoria de scripts, legados/DHPs, montagem do release e validacao pos-higienizacao.
- Estrutura proposta: `release/app/`, `release/config_template/`, `release/docs_operacionais/`, `release/assets/`, `release/scripts_autorizados/` e `release/runtime_empty/`.
- HIG-004 foi concluida por atualizacao controlada de `.gitignore`; HIG-008 foi concluida como manifest documental; HIG-006 foi concluida documentalmente (Opcao A, 2026-05-15); HIG-007 foi concluida documentalmente (Opcao A, 2026-05-15); HIG-005 permanece bloqueada por DHP-02/DHP-09.

### Decisao DHP-05 / DEC-005 (2026-05-15)

DHP-05 / DEC-005 resolvida: arquivos `relatorio_final_corrida_*.json` localizados na raiz sao artefatos runtime/transitorios de execucao. Eles nao devem entrar no pacote de release operacional. Devem ser tratados por politica de retencao, realocacao ou regra de `.gitignore` em rodada propria. Nenhuma exclusao automatica esta autorizada por esta decisao.

- **HIG-007**: **concluida documentalmente** em 2026-05-15 pela Opcao A; `.gitignore` ja cobre `relatorio_final_corrida_*.json`; arquivos permanecem fisicamente na raiz sem remocao, movimentacao ou exclusao; manifest HIG-008 os exclui do release.
- **T-AUD-006**: **concluida documentalmente** conforme HIG-007; politica operacional registrada.
- DHPs ainda pendentes apos DEC-005: DHP-02/DHP-09, DHP-04 e DHP-07.

### Decisao DHP-04 / DEC-004 (2026-05-15)

DHP-04 / DEC-004 resolvida: diretorios `snapshots/encoding_backup_*` sao artefatos historicos de backup/encoding, criados para rastreabilidade e eventual recuperacao durante correcoes de encoding. Eles nao devem entrar no pacote de release operacional. Devem ser tratados por politica de retencao, arquivamento externo ou exclusao controlada em rodada propria, sempre apos baseline/backup. Nenhuma exclusao automatica esta autorizada por esta decisao.

- **HIG-006**: desbloqueada para rodada futura de retencao/arquivamento/exclusao controlada, mas permanece pendente.
- **T-AUD-005**: desbloqueada e pendente para tratar a politica operacional conforme DEC-004.
- DHPs ainda pendentes apos DEC-004: DHP-02/DHP-09 e DHP-07.

### HIG-004 - Atualizacao controlada de `.gitignore` (2026-05-15)

HIG-004 concluida: `.gitignore` foi atualizado com regras explicitas para ambientes locais, caches, temporarios, logs, relatorios gerados, snapshots `encoding_backup_*`, `relatorio_final_corrida_*.json`, `test_history.csv`, bancos locais e arquivos sensiveis em `banco/`.

- A atualizacao impede rastreamento futuro; nao remove, move ou altera arquivos ja existentes.
- `config.json` permanece nao ignorado por ser template/local runtime versionado conforme SDD.
- `docs/specs/`, `config/contracts/` e `requirements.txt` nao foram ignorados.
- HIG-006 concluida documentalmente (Opcao A, 2026-05-15); HIG-007 concluida documentalmente (Opcao A, 2026-05-15); HIG-005 permanece bloqueada por DHP-02/DHP-09.

### HIG-008 - Manifest documental de release (2026-05-15)

HIG-008 concluida como documentacao: `docs/specs/higienizacao_implantacao.md` define a estrutura alvo `release/app/`, `release/config_template/`, `release/docs_operacionais/`, `release/assets/`, `release/scripts_autorizados/` e `release/runtime_empty/`.

- A estrutura ainda nao foi materializada; nenhuma pasta `release/` foi criada.
- Nenhum arquivo foi copiado, movido, apagado ou empacotado.
- O manifest exclui `banco/*`, `.env*`, logs, reports, relatorios, caches, `.tmp`, snapshots `encoding_backup_*`, `relatorio_final_corrida_*.json`, testes e scripts de limpeza nao auditados.
- `config.json` permanece template/local runtime e a producao exige Instalacao Inicial para configurar `shared_storage`.
- HIG-006 concluida documentalmente (Opcao A, 2026-05-15); HIG-007 concluida documentalmente (Opcao A, 2026-05-15); HIG-005 permanece bloqueada por DHP-02/DHP-09.

### Decisao DHP-07 / DEC-007 (2026-05-15)

DHP-07 / DEC-007 resolvida: criado `README.md` humano e operacional como ponto de entrada para operadores, administradores e equipe tecnica. O README nao substitui a documentacao SDD.

- **T-AUD-009**: concluida por criacao do README na raiz.
- O README registra piloto controlado com 3 a 5 usuarios e nao declara aptidao plena para 10 usuarios.
- O README registra que `config.json` e template/local runtime e que producao exige Instalacao Inicial.
- O README registra que `banco/*`, logs, reports, relatorios, snapshots, `.tmp`, `.env*` e artefatos runtime nao entram no release.
- O README registra que scripts de limpeza nao devem ser executados sem auditoria/autorizacao.
- DHPs ainda pendentes apos DEC-007: DHP-02/DHP-09.

### Notas de capacidade multiusuario e instalacao (2026-05-15)

Atualizacao documental SDD executada apos Auditoria READ-ONLY - Capacidade Multiusuario e Modulo de Instalacao. Nenhum codigo, teste, `config.json`, CSV, banco, report, log, snapshot ou script foi alterado nesta rodada.

- **Classificacao multiusuario**: APTO COM RESTRICOES. Decisao humana registrada: implantacao inicial em piloto controlado com 3 a 5 usuarios. A aptidao para 10 usuarios ainda nao esta comprovada e passa a ser meta condicionada.
- **Classificacao instalacao**: FUNCIONAL COM RESTRICOES. O modulo de Instalacao Inicial existe e valida parte das pre-condicoes, mas precisa de lock/atomicidade em `config.json`, dry-run, rollback, ajuste ADMIN+MASTER conforme DEC-010 e testes adicionais.
- **Prioridades antes de ampliacao para 10 usuarios**: CONC-002, CONC-003 e INST-001.
- **Proxima acao recomendada**: manter escopo de piloto 3-5 na implantacao inicial; executar INST-004 em rodada propria para ajustar UI/codigo caso a aba de Instalacao Inicial ainda restrinja acesso apenas a ADMIN.

### Decisao de escopo multiusuario inicial (2026-05-15)

- **DEC-009 registrada**: a implantacao inicial nao declarara aptidao plena para 10 usuarios simultaneos.
- Escopo aprovado para implantacao inicial: piloto controlado com **3 a 5 usuarios**.
- 10 usuarios simultaneos permanece como meta condicionada a conclusao dos testes CONC e correcoes prioritarias, especialmente CONC-002, CONC-003 e INST-001.
- CONC-001..CONC-006 permanecem pendentes; esta decisao nao encerra os testes de concorrencia nem autoriza declaracao de aptidao plena para 10 usuarios.

### Notas da microfase 3.1 (2026-05-13)

Ajuste semantico de governanca aplicado em arquivos Markdown permitidos. Nenhum codigo, configuracao operacional ou artefato foi alterado.

- **DHP-06 / DEC-006 RESOLVIDA**: `equipment_legacy_deprecation.md` classificado como fonte canonica da deprecacao controlada; `plano_equipamentos_sdd.md` classificado como documento historico-orientador subordinado ao estado atual de `tasks.md §7`. T-AUD-012 marcada `[Concluido]`. Ver `requirements.md §10` DEC-006.
- **DHP-08 / DEC-008 RESOLVIDA**: T-AUD-008 (teste-guardiao de imports em `domain/`) e executavel sem bloqueio formal; cria apenas teste automatizado em `tests/`, **nao altera codigo de producao**; deve preceder T-AUD-001. Ver `requirements.md §10` DEC-008.
- DHPs ainda pendentes apos DEC-003: DHP-02 (=DHP-09), DHP-04, DHP-05, DHP-07. Total: 4 pendentes.
- Demais DHPs nao foram tratadas como resolvidas.

### Notas de execucao pos-microfase 3.1 (2026-05-13)

Execucao SDD restrita e rastreavel das tarefas T-AUD nao bloqueadas:

- **T-AUD-008 concluida**: criado `tests/test_domain_pure_imports.py`; guardiao AST de imports proibidos em `domain/`; evidencia final `python -m pytest tests/test_domain_pure_imports.py -q --tb=short` com `1 passed`.
- **T-AUD-001 concluida**: `domain/ct_rules.py` deixou de importar `pandas`; `pd.isna(ct_val)` substituido por checagem nativa com `math.isnan`; evidencia de regressao CT com `131 passed` no recorte especifico. Nao houve mudanca de regra de negocio.
- **T-AUD-003 concluida**: criado `tests/test_shared_storage_precondition_required.py`; valida fail-closed para `shared_storage.required=true`, `data_root=""` e `allowed_roots=[]`, com configuracao em memoria e sem uso do `config.json` real; evidencia `1 passed`.
- **T-AUD-007 concluida**: cobertura equivalente ja existia em `tests/test_phase_u3_gal_send_use_case.py::test_u3_use_case_still_skips_legacy_success_key_with_scoped_request`; evidencia `1 passed`; cobre match apenas pela chave legada de 4 campos, bloqueio como `duplicado` e ausencia de acionamento real de Selenium/navegador/GAL.
- **T-AUD-004A concluida**: criado `tests/test_auth_legacy_user_manager_no_runtime_imports.py`; guardiao AST varre areas runtime e bloqueia imports de `core.authentication.user_manager` fora de allowlist; allowlist inicial vazia; evidencia `python -m pytest tests/test_auth_legacy_user_manager_no_runtime_imports.py -q --tb=short` com `1 passed`. `core/authentication/user_manager.py` permanece legado em deprecacao controlada.
- **T-AUD-004B concluida**: `core/authentication/user_manager.py` preservado fisicamente; execucao direta neutralizada com mensagem segura de deprecacao controlada e `SystemExit(2)`, sem chamar `inicializar_sistema()`. Guardiao T-AUD-004A passou com `1 passed`. A ressalva externa por `U+FEFF` em `ui/user_management.py` foi resolvida por T-AUD-014.
- **T-AUD-014 concluida**: removido apenas o BOM UTF-8 inicial `EF BB BF` de `ui/user_management.py`; logica preservada; `ast.parse` retornou `parse ok`; teste especifico que falhava passou com `1 passed`; suite especifica `tests/test_phase_b2_auth_actor_required.py` passou com `3 passed`.
- Nenhuma tarefa bloqueada por DHP foi executada. DHPs pendentes permanecem: DHP-02 (=DHP-09), DHP-04, DHP-05, DHP-07.
### Notas DEC-001 / DHP-01 (2026-05-13)

- **DHP-01 / DEC-001 RESOLVIDA**: `config.json` versionado deve ser tratado como template/local runtime nao pronto para producao. Ambientes produtivos exigem configuracao local validada, com `shared_storage.root`, `data_root` e `allowed_roots` preenchidos. A aplicacao nao deve operar em producao com `shared_storage.required=true` e caminhos vazios.
- **T-AUD-002 concluida** por registro documental da decisao.
- **T-AUD-008-CFG concluida em rodada propria posterior**: `config.json` permaneceu JSON valido/UTF-8; chave vazia removida; mojibake de `lab_responsible` corrigido; template/local runtime preservado; nenhum dado real sensivel inserido; nenhum codigo alterado.
- DHPs ainda pendentes: DHP-02 (=DHP-09), DHP-04, DHP-05 e DHP-07.
### Notas T-AUD-008-CFG (2026-05-13)

- **T-AUD-008-CFG concluida**: correcao controlada de `config.json` executada apos DEC-001.
- Evidencias: `python -m json.tool config.json` passou; leitura UTF-8 e `json.loads` passaram; chave vazia `""` removida de `general`; `lab_responsible` sem mojibake; `shared_storage.root`, `data_root` e `allowed_roots` permaneceram vazios; `tests/test_shared_storage_precondition_required.py` passou com `1 passed`.
- Escopo preservado: nenhum codigo, teste ou documentacao foi alterado durante a rodada de configuracao; nenhum dado real sensivel foi inserido; `config.json` permanece template/local runtime.

### Notas DEC-003 / DHP-03 (2026-05-13)

- **DHP-03 / DEC-003 RESOLVIDA**: `core/authentication/user_manager.py` sera tratado como modulo legado em deprecacao controlada.
- Fluxo ativo de autenticacao reconhecido: `autenticacao/auth_service.py` + `autenticacao/login.py`, com matriz de autorizacao em `application/access_control.py`.
- Nenhuma remocao fisica de `core/authentication/user_manager.py` esta autorizada neste momento.
- Antes de qualquer remocao futura, devem existir: T-AUD-004A concluida (teste guardiao de nao uso runtime de `core.authentication.user_manager`) e T-AUD-004B concluida (neutralizacao do bloco `__main__` / bootstrap manual do modulo legado), alem de DEC futura especifica para remocao fisica.
- **T-AUD-004A concluida em rodada tecnica posterior**: `tests/test_auth_legacy_user_manager_no_runtime_imports.py` criado e executado com `1 passed`; allowlist inicial vazia; nenhum codigo de producao, `config.json` ou documentacao foi alterado na rodada tecnica.
- **T-AUD-004B concluida em rodada tecnica posterior**: execucao direta de `core/authentication/user_manager.py` neutralizada; `inicializar_sistema()` nao e mais chamado pelo bloco `__main__`; arquivo legado nao foi removido; ressalva externa de parsing em `ui/user_management.py` resolvida por T-AUD-014.
- **T-AUD-014 concluida em rodada tecnica posterior**: BOM UTF-8 inicial removido de `ui/user_management.py`; `ast.parse` e teste B2 afetado passaram; sem alteracao de logica.
- DHPs ainda pendentes: DHP-02 (=DHP-09), DHP-04, DHP-05 e DHP-07.

## 11. Melhorias UX/UI e Bugfixes
- [x] [Concluido] UI-BUGFIX-NEW-ANALYSIS-001 - Corrigir preservacao indevida de dados na UI apos 'Nova Analise' com expurgo e destruicao do widget (`remove_module`), garantindo limpeza do exame enquanto preserva-se o equipamento selecionado (`AppState`).
- [x] [Concluido] UI-BUGFIX-MAXIMIZATION-001 - Corrigir falha de maximização da Janela de Análise no modo Single-Window injetando o comando `state('zoomed')` com atraso (`.after()`) na `main_window` em vez de tentar aplicar ao CTkToplevel obsoleto.
- [x] [Concluido] UI-BUGFIX-SYNC-001 - Corrigir perda de edições do Mapa da Placa ao navegar para outros módulos e retornar, alterando a sincronização para o `app_state` global (`hasattr(self.main_window, "app_state")`) em vez do `self.master` local que não possuía o estado.

## 12. Feature: Modulo Gestao Dashboard
- [x] [Concluido] GD-01 - Implementation of the new Gestão Dashboard with Clinical Statistics (creates services/reports/dashboard_analytics.py using pandas and modifies ui/modules/dashboard.py without adding pandas to domain/).
