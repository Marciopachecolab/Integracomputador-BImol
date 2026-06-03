# Requirements - SDD Fonte Unica

## 1. Visao geral do sistema
IntegRAGal e um sistema desktop (Windows) para operacao RT-PCR com quatro etapas:
1. mapeamento de placa de extracao;
2. analise de corrida por regras de CT;
3. revisao e ajuste operacional na UI;
4. exportacao e envio para GAL.

## 2. Escopo (faz)
- Carregar arquivo de extracao e gerar preview de mapeamento por kit/parte.
- Executar analise por exame ativo com classificacao por alvo.
- Calcular `Resultado_geral` com prioridade de regras.
- Permitir editar mapa e refletir mudancas na tabela de analise.
- Enviar resultados ao GAL com controle de idempotencia.
- Operar em pasta compartilhada unica com validacao de acesso.

## 3. Fora de escopo (nao faz)
- Nao e aplicacao web.
- Nao e LIMS completo.
- Nao suporta execucao de exames sem configuracao/contrato valido ou sem habilitacao em `active_exams`.
- Nao suporta backend Postgres dedicado (nao implementado no provider atual).

## 4. Escopo de exames habilitados
Em runtime real, o escopo operacional e definido por `exams.active_exams`.

- Todo exame listado em `active_exams` e considerado habilitado, desde que possua configuracao/contrato valido no registry.
- Exame ausente de `active_exams` deve ser bloqueado no fluxo operacional antes de qualquer IO de analise.
- `active_exams` vazio em registry carregado bloqueia todos os exames.
- `VR1e2 Biomanguinhos 7500` e `ZDC BioManguinhos` permanecem exames canonicos de referencia com regras laboratoriais explicitadas em §5, mas nao limitam o catalogo operacional quando outros exames estiverem habilitados.

## 5. Regras laboratoriais (resumo)
### 5.1 VR1e2 Biomanguinhos 7500
Alvos virais: `SC2`, `HMPV`, `INF A`, `INF B`, `ADV`, `RSV`, `HRV`.
Controle interno: `RP`.

Regra viral:
- Detectavel: `8.01 <= CT <= 35.0`
- Indeterminado/Inconclusivo: `35.01 <= CT <= 40.0`
- Nao detectavel: vazio/invalido, `< 8.01` ou `> 40.0`

RP valido: `15.0 <= CT <= 35.0`.

### 5.2 ZDC BioManguinhos
Alvos virais: `ZK`, `CHIK`, `DEN1`, `DEN2`, `DEN3`, `DEN4`.
Controle interno: `RP`.

Regra viral:
- Detectavel: `8.1 <= CT < 38.1`
- Indeterminado/Inconclusivo: `38.1 <= CT <= 40.0`
- Nao detectavel: vazio/invalido, `< 8.1` ou `> 40.0`

RP valido: `8.1 <= CT <= 35.0`.

## 6. Regras de resultado geral
Prioridade obrigatoria:
1. RP invalido -> `Invalido`
2. RP valido + qualquer inconclusivo/indeterminado -> `Indeterminado`
3. RP valido + qualquer detectavel -> `Detectavel para <alvos>`
4. senao -> `Nao Detectavel`

## 7. Requisitos nao funcionais
- Plataforma: Windows.
- UI: CustomTkinter/Tkinter.
- Persistencia: CSV/JSON e suporte SQLite-first.
- Multiusuario: ate 5 usuarios em compartilhamento unico com lock de arquivo.
- Auditoria READ-ONLY de 2026-05-15 classificou multiusuario como **APTO COM RESTRICOES**. Decisao humana posterior: a implantacao inicial adotara piloto controlado com 3 a 5 usuarios; 10 usuarios passa a ser meta condicionada a testes CONC e correcoes prioritarias. Antes de ampliar para 10 usuarios, priorizar CONC-002, CONC-003 e INST-001 em `tasks.md`.
- Logs auditaveis para analise e envio GAL.

### 7.1 Pre-condicoes operacionais
- O `config.json` versionado deve ser tratado como **template/local runtime** ate que a Instalacao Inicial (T11) preencha:
  - `shared_storage.root` (nao vazio);
  - `data_root` (igual a `shared_storage.root` quando aplicavel);
  - `allowed_roots` contendo o mesmo root.
  Decisao DEC-001 (2026-05-13): o `config.json` versionado e template/local runtime nao pronto para producao. Ambientes produtivos exigem configuracao local validada, com `shared_storage.root`, `data_root` e `allowed_roots` preenchidos. A aplicacao nao deve operar em producao com `shared_storage.required=true` e caminhos vazios.
  Confirmado pelo codigo: `config.json:11-16` lista campos vazios. Rastreabilidade: D-02 / DEC-001.
- Auditoria READ-ONLY de 2026-05-15 classificou o modulo de Instalacao Inicial como **FUNCIONAL COM RESTRICOES**. O modulo existe, mas requer backlog INST antes de uso produtivo irrestrito: lock/atomicidade para `config.json` (INST-001), dry-run/resumo (INST-002), backup/rollback (INST-003), ajuste ADMIN+MASTER com confirmacao forte, log/auditoria e backup previo futuro (INST-004) e teste end-to-end do wizard (INST-005).
- O catalogo de exames ativos (`exams.active_exams`) e a fonte canonica de habilitacao operacional. Novos exames podem operar quando estiverem nessa lista e tiverem configuracao/contrato valido; exames ausentes continuam fail-closed.
- Contratos de equipamentos (`config/contracts/equipment/*.json`) sao a fonte canonica operacional. As fontes legadas em `banco/` permanecem disponiveis apenas para rollback controlado, conforme `docs/specs/equipment_legacy_deprecation.md`. Rastreabilidade: D-11 / DEC-002.

## 8. Criterios de aceite objetivos
- CA-01: menu operacional lista apenas os exames habilitados em `active_exams`.
- CA-02: bordas de CT de VR1e2 e ZDC passam nos testes de classificacao.
- CA-03: linhas inconclusivas/indeterminadas mantem cor/tag correta na tabela.
- CA-04: salvar edicao no mapa nao pode ser sobrescrito por recalculo de CT.
- CA-05: fluxo do item 7 exibe lista rolavel de exames e botao de edicao visivel.
- CA-06: item 7 abre maximizado e formulario de edicao abre em janela ampliada.
- CA-07: `shared_storage.required=true` exige `data_root` unico e ACL leitura/escrita.
- CA-08: envio GAL verifica chave legada (4 campos) e chave com escopo (4+N) antes de cada linha; reenvio de linha com `status=sucesso` e bloqueado; linha com `status=erro` pode ser reenviada.
- CA-09: exame ausente de `active_exams` levanta `ExamForaDoEscopoError` no inicio do pipeline de analise (fail-closed); `active_exams` vazio bloqueia todos os exames quando o registry ja foi carregado.
- CA-10: o guard de escopo deve distinguir registry carregado de stub de teste. Em runtime real, `active_exams` vazio bloqueia todos os exames; em stub de teste sem configuracao, `is_active()` pode retornar `True` por contrato canonico, sem afetar o fail-closed do registry real. Rastreabilidade: D-12.
- CA-11: a verificacao de idempotencia GAL deve detectar tambem o caso em que apenas a chave legada (4 campos) consta no journal e a chave com escopo (4+N) e nova. Esse cenario deve ser bloqueado como `duplicado`. Rastreabilidade: D-07 / L-T01 — exige teste dedicado (ver `tasks.md §10`, T-AUD-007).
- CA-12: a configuracao de `shared_storage` em template incompleto nao caracteriza ambiente pronto para producao. Validacao de instalacao deve falhar fail-closed quando `shared_storage.required=true` e `data_root` ou `allowed_roots` estiverem vazios. Rastreabilidade: D-02 / DEC-001 — exige teste dedicado (ver `tasks.md §10`, T-AUD-003).
- CA-13: a implantacao inicial deve operar como piloto controlado com 3 a 5 usuarios. Aptidao plena para 10 usuarios simultaneos nao deve ser declarada ate conclusao dos controles prioritarios CONC-002, CONC-003 e INST-001, alem dos demais testes CONC aplicaveis. Ate la, 10 usuarios e meta condicionada, nao escopo inicial.
- CA-14: poco vazio (codigo de amostra em branco, apenas "X" ou prefixo "Vazio...") deve sempre resultar em `Resultado_geral = Invalido` e `Selecionado = False`, para todos os exames, impedindo seu envio ao GAL. Rastreabilidade: `domain.resultado_geral.is_amostra_vazia`; guardiao: `tests/test_poco_vazio_invalido.py`.
- CA-15: exame criado pelo wizard deve ser plenamente funcional para envio GAL sem depender de defaults de outro exame. O wizard deve capturar `gal_exame_codigo`, `kit_codigo`, `panel_tests_id` e `export_fields` no Passo 4. O envio GAL deve usar esses campos, com fallback para `export_fields` quando o painel nao consta na config GAL. Rastreabilidade: `design.md §3.3.1`; guardioes: `tests/test_exam_creator_campos_gal.py`.
- CA-16: as analiticas do dashboard (Gestao Clinica e Visao Analitica) devem contar resultados por alvo apenas a partir das colunas canonicas `RES_*`, ignorando snapshots `SRC_RES_*` e controles `RP|CN|CP|GERAL`. Nao deve haver alvo duplicado (ex.: "RES X" e "SRC RES X") nem rotulo com prefixo `RES_`/`SRC_`. As abas que leem do SQLite (`banco_runtime/historico.db`) devem exibir dados mesmo quando o historico CSV do Operacional estiver vazio. Rastreabilidade: DASH-003/004/005/DASH-FIX-001; `design.md §3.8` e §14.2.
- CA-17: o detalhe de uma corrida aberto a partir do dashboard e somente leitura (sem edicao). O "Mapa Definitivo" disponibilizado ao operador deve ser o `.xlsx` `mapa_placa_*` efetivamente gerado pela analise em `<data_root>/mapas`, localizado por correspondencia com o nome da corrida; nunca uma regeneracao divergente. Quando inexistente, informar que deve ser gerado na tela de Analise. Rastreabilidade: DASH-007; `exportacao/mapa_placa_exporter.py`; `design.md §3.8`.

### 8.1 Contrato Visível de UI — Janela de Análise (Tarefa 9)
- **Gatilho:** Evento `ON_LOAD_SUCCESS` do módulo de análise.
- **Estado Geométrico:** Invocação imediata do estado maximizado do root do sistema.
- **Restrição:** Proibido o uso de dimensões absolutas hardcoded pós-carregamento.

## 9. Feature: Modulo de Relatorios

### 9.1 Objetivo de negocio
Permitir que usuarios autorizados acompanhem a operacao laboratorial por meio de relatorios detalhados e agregados, usando dados ja registrados no historico de analises, historico por exame e journal de integracao GAL.

O modulo deve apoiar tomada de decisao operacional sem alterar regras clinicas, classificacao de CT, envio GAL ou cadastro de exames.

### 9.2 Personas e User Stories
- US-R01: Como coordenador do laboratorio, quero visualizar exames realizados e exames a realizar por periodo, para acompanhar demanda e produtividade.
- US-R02: Como coordenador do laboratorio, quero filtrar relatorios por tipo de exame habilitado, para comparar volumes entre os exames operacionais.
- US-R03: Como analista, quero consultar resultados por positividade, para identificar rapidamente amostras detectaveis, nao detectaveis, indeterminadas e invalidas.
- US-R04: Como supervisor, quero filtrar por data inicial/final, para consolidar producao diaria, semanal ou mensal.
- US-R05: Como supervisor, quero filtrar por analista responsavel, para auditar execucao e distribuicao de trabalho.
- US-R06: Como operador, quero filtrar por kit/lote utilizado, para investigar problemas associados a lote especifico.
- US-R07: Como usuario responsavel pelo GAL, quero distinguir amostras passadas no GAL, nao enviadas, com falha ou nao enviaveis, para priorizar pendencias de integracao.
- US-R08: Como coordenador, quero cruzar filtros relevantes (exame + periodo + positividade + GAL + analista + kit), para responder perguntas operacionais sem manipular planilhas manualmente.
- US-R09: Como auditor, quero exportar o relatorio filtrado e manter criterio de consulta rastreavel, para revisao posterior.

### 9.3 Filtros minimos
- Periodo: `data_inicio`, `data_fim`.
- Tipo de exame: nome/slug do exame ativo.
- Status de realizacao: realizado, a realizar, parcial/pendente quando houver contrato de entrada ainda sem resultado.
- Positividade: detectavel/positivo, nao detectavel/negativo, indeterminado/inconclusivo, invalido.
- Analista responsavel: usuario de analise ou bioquimico registrado no historico.
- Kit/lote: `lote`, `lote_kit` ou `kit_codigo`, conforme fonte disponivel.
- Status GAL: sucesso/enviado, nao enviado, falha/erro, duplicado, nao enviavel.
- Equipamento: apenas quando necessario para auditoria tecnica; nao deve abrir escopo operacional de equipamentos.

### 9.4 Agregacoes minimas
- Total de exames/corridas por periodo.
- Total de amostras por exame.
- Totais por positividade (`total_detectados`, `total_nao_detectados`, `total_inconclusivos`, `total_invalidos`).
- Taxa de positividade por exame e periodo.
- Total por analista responsavel.
- Total por kit/lote.
- Total por status GAL.
- Lista de pendencias GAL com amostra, exame, lote, data e motivo/status.

### 9.5 Fontes de dados existentes
- Historico de analises via `HistoryReportService` e provider de persistencia.
- SQLite `historico_analises` para resumo de corridas.
- SQLite `exam_runs` para registros por amostra/exame.
- CSV contratual `historico_analises.csv` como fallback/export.
- Journal GAL `gal_transacoes.csv` como trilha unificada de sucesso/falha/duplicado.
- Ledger legado `gal_transacoes_sucesso.csv` apenas para conciliacao historica.

### 9.6 Criterios de aceite do modulo
- CA-R01: relatorio por periodo retorna somente registros dentro do intervalo informado, inclusive limites do dia.
- CA-R02: filtro por exame respeita somente exames habilitados em `active_exams`; exame fora de escopo nao deve aparecer como opcao operacional.
- CA-R03: agregacao por positividade deve usar `Resultado_geral`/contadores persistidos, sem recalcular regra clinica em tela.
- CA-R04: filtro por analista deve aceitar `usuario`, `usuario_analise` ou campo equivalente persistido.
- CA-R05: filtro por kit/lote deve consultar `lote`, `lote_kit` ou `kit_codigo` conforme fonte, documentando campo de origem.
- CA-R06: status GAL deve ser derivado preferencialmente do journal unificado `gal_transacoes.csv`; historico CSV pode ser fallback quando o journal nao tiver correspondencia.
- CA-R07: registros sem envio GAL devem aparecer como pendencia quando forem enviaveis e nao houver sucesso registrado.
- CA-R08: consultas devem funcionar em SQLite-first e manter fallback CSV quando o provider nao estiver disponivel.
- CA-R09: relatorio exportado deve preservar filtros aplicados, timestamp de geracao e usuario solicitante.
- CA-R10: nenhuma implementacao do modulo pode modificar resultados, status GAL ou historico; relatorios sao leitura/exportacao.

## 10. Rastreabilidade de achados (auditoria 2026-05-12)

Esta secao registra os achados estruturais da auditoria SDD READ-ONLY e seu endereçamento documental. Tarefas associadas estao em `tasks.md §10`. Categorias: GAP (lacuna de especificacao), BUG (anomalia identificada), TEST (cobertura necessaria), DEC (decisao humana pendente).

- GAP-001 (D-12): documentacao previa sobre `active_exams` era ambigua. Endereçado por CA-10 e por reescrita de `design.md §3.6`.
- GAP-002 (D-02): pre-condicao de instalacao nao estava explicita em requirements. Endereçado por §7.1 e CA-12.
- BUG-001 (D-08): **RESOLVIDO por T-AUD-008-CFG em rodada propria** - `config.json` teve a chave literal vazia `""` removida e `general.lab_responsible` corrigido para UTF-8 legivel. A correcao preservou `config.json` como template/local runtime, sem inserir dados reais sensiveis; `shared_storage.root`, `data_root` e `allowed_roots` permaneceram vazios.
- CONFIG-ENC-001 (2026-05-14): lacuna residual de encoding em `config.json` fora do escopo de T-AUD-008-CFG: o campo `_comentario` ainda pode exibir mojibake, por exemplo `ConfiguraÃ§Ãµes`. **Nao corrigir nesta rodada documental**; tratar apenas em rodada especifica de configuracao/encoding, sem inserir dados reais sensiveis.
- TEST-001 (D-07 / L-T01): cobertura para match apenas pela chave legada na dual-key GAL. Endereçado por CA-11 e tarefa T-AUD-007.
- TEST-002 (L-T03): teste-guardiao de imports em `domain/` (proibir `pandas`, `selenium`, `tkinter`, `customtkinter`, `seleniumrequests`). Tarefa T-AUD-008.
- TEST-003 (L-T02): regressao para `shared_storage.required=true` com `data_root` vazio. Tarefa T-AUD-003.
- TEST-004: Reintegração da suíte de testes completa, atualmente ausente/vazia na cópia de backup do ambiente. Pendente.
- DEC-001 (D-02): **RESOLVIDA em 2026-05-13** - `config.json` versionado deve ser tratado como template/local runtime nao pronto para producao. Ambientes produtivos exigem configuracao local validada, com `shared_storage.root`, `data_root` e `allowed_roots` preenchidos. A aplicacao nao deve operar em producao com `shared_storage.required=true` e caminhos vazios. T-AUD-008-CFG foi concluida posteriormente em rodada propria, limitada a correcao formal de chave vazia e `lab_responsible`, sem inserir dados reais sensiveis e sem transformar `config.json` em configuracao produtiva.
- DEC-002 (D-11): **RESOLVIDA em 2026-05-15** - `banco/*` legados mantidos fisicamente no ambiente de desenvolvimento/runtime como fallback operacional controlado, sem abertura de conteudo sensivel nesta decisao. Nao devem entrar no pacote de release operacional (manifest HIG-008 ja exclui integralmente). Nenhuma exclusao, movimentacao, arquivamento ou migracao fisica esta autorizada nesta etapa. Fallback controlado permanece documentado em `equipment_legacy_deprecation.md` (DEC-006). Tarefas futuras nao bloqueantes registradas: **PRIV-001** (auditoria LGPD/controlada de `banco/*`), **GIG-001** (estender `.gitignore` para CSVs operacionais de `banco/` ainda nao cobertos) e **HIG-009** (planejar separacao `banco_template/` + bootstrap em rodada futura).
- DEC-003 (D-04): **RESOLVIDA em 2026-05-13** - `core/authentication/user_manager.py` e modulo legado em deprecacao controlada, preservado fisicamente para rollback/continuidade. O fluxo ativo de autenticacao e `autenticacao/auth_service.py` + `autenticacao/login.py` (LoginDialog), com matriz de autorizacao em `application/access_control.py`. T-AUD-004A concluiu o guardiao de nao uso runtime; T-AUD-004B neutralizou a execucao direta do legado; T-AUD-014 resolveu a ressalva externa de `U+FEFF` em `ui/user_management.py`. Nenhuma remocao fisica esta autorizada sem DEC futura especifica.
- DEC-004 (D-05): politica para `snapshots/encoding_backup_*` (artefatos transitorios versus baseline intencional). Pendente.
- DEC-005 (D-06): politica para `relatorio_final_corrida_*.json` na raiz (realocar para `reports/` e ajustar `.gitignore`). Pendente.
- DEC-006 (D-10): **RESOLVIDA na microfase 3.1 (2026-05-13)** — `docs/specs/equipment_legacy_deprecation.md` classificado como **fonte canonica da deprecacao controlada** dos legados de equipamentos; `docs/specs/plano_equipamentos_sdd.md` classificado como **documento historico-orientador**, subordinado ao estado atual de `docs/specs/tasks.md §7`. Tarefa T-AUD-012 marcada `[Concluido]`.
- DEC-007 (D-09): criacao de `README.md` humano para LACEN. Pendente.
- DEC-008 (DHP-08): **RESOLVIDA na microfase 3.1 (2026-05-13)** — aprovacao concedida para `T-AUD-008` (teste-guardiao de imports em `domain/`). T-AUD-008 e executavel sem bloqueio formal; cria apenas teste automatizado em `tests/`, **nao altera codigo de producao**; deve preceder T-AUD-001 (remocao de pandas em `domain/ct_rules.py`).
- DEC-009 (2026-05-15): **RESOLVIDA para implantacao inicial** - a implantacao inicial nao declarara aptidao plena para 10 usuarios simultaneos; sera adotado piloto controlado com 3 a 5 usuarios. A ampliacao para 10 usuarios fica condicionada a conclusao dos testes CONC e correcoes prioritarias, especialmente CONC-002, CONC-003 e INST-001. CONC-001 permanece pendente como rastreabilidade/validacao do requisito futuro.
- DEC-010 (2026-05-15): **RESOLVIDA** - a Instalacao Inicial deve ser acessivel por ADMIN e MASTER, desde que protegida por confirmacao forte, log/auditoria e, futuramente, backup previo. `INST-004` permanece pendente para ajustar UI/codigo caso a aba ainda restrinja acesso apenas a ADMIN; executar em rodada propria, sem alterar codigo nesta atualizacao documental.

Rastreabilidade textual confirmada pelo codigo: `domain/ct_rules.py:9`, `application/gal_send_use_case.py:184-204` e `:286-293`, `config.json:4-16`, `config.json:237-256`. Rastreabilidade confirmada pela documentacao: `docs/specs/design.md §3.6, §3.7`, `docs/specs/tasks.md §7-§8`, `docs/specs/equipment_legacy_deprecation.md`.
