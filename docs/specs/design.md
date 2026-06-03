# Design - SDD Fonte Unica

## 1. Arquitetura em camadas
- `ui/`: telas, eventos e dialogs.
- `application/`: use cases e contratos de orquestracao.
- `domain/`: regras puras (CT, mapeamento, prioridades).
- `services/` e `exportacao/`: adaptadores de infraestrutura.

Regra: comportamento clinico e operacional nao pode ficar duplicado em telas.

## 2. Stack
- Python 3.x
- CustomTkinter/Tkinter
- Pandas/OpenPyXL
- Selenium + seleniumrequests
- CSV/JSON + SQLite-first
- Pytest

## 3. Modulos chave

### 3.1 Analise
- `services.analysis_service`: pipeline de ingestao, classificacao e resultado geral.
- `services.analysis_runtime_contract`: resolve limite de CT por exame/alvo.
- `domain.ct_rules` e `domain.ct_rules_runtime`: regra canonica de classificacao.

### 3.2 Mapeamento
- `application.extraction_plate_mapping_use_case`: calculo puro para preview e retorno.
- `ui/modules/extraction_plate_mapping.py`: visualizacao e confirmacao. Encapsula `ExtractionUseCase` e `TkFileChooser`.
- `ui/menu_handler.py::abrir_busca_extracao`: delega para `abrir_mapeamento_extracao` (T06 promovido; padrao strangler removido).

### 3.3 Cadastro/edicao de exame
- `ui/modules/exam_creator/wizard.py`: entrada item 7 (incluir/editar). Fluxo de 4 passos: (1) Identificacao + equipamento/placa, (2) Alvos por filtro/poco, (3) Faixas de CT, (4) Integracao GAL. Campos GAL capturados no Passo 4: `gal_exame_codigo`, `kit_codigo`, `panel_tests_id`, `export_fields`, `mapa_alvos`. Ver §3.3.1.
- `services.exam_registry.RegistryExamEditor` (em `ui/modules/cadastros_ui.py`): validacao, serializacao e persistencia de `ExamConfig` em `config/exams/<slug>.json`. Avisos nao bloqueantes quando campos GAL estao vazios.
- `services.exam_registry`: fonte de configuracao ativa. Hierarquia de merge: csv < config_json < config_exams < contracts.

### 3.3.1 Contrato do Wizard de Exames (2026-05-30)
Campos obrigatorios para analise e envio GAL plenos:

| Campo | Passo | Consumidor | Consequencia se vazio |
|---|---|---|---|
| `equipamento` | 1 | extrator de arquivo de resultados | default "7500_extended" |
| `tipo_placa_analitica` | 1 | esquema de agrupamento de pocos | default "96" |
| `alvos`, `targets_por_poco`, `limiares_ct_por_alvo_poco` | 2/3 | pipeline de analise CT | sem classificacao |
| `gal_exame_codigo` | 4 | `buscar_metadados` como `codExame` | 0 metadados → falha critica de envio |
| `kit_codigo` | 4 | coluna `kit` do CSV GAL | default "1175" (de VR1e2) |
| `panel_tests_id` | 4 | coluna `painel` do CSV GAL e mapa de testes do submit | default "12" (de VR1e2) |
| `export_fields` | 4 | colunas de analitos do CSV GAL + fallback `testes_do_painel` | analitos de VR1e2 por default |
| `mapa_alvos` (derivado) | 4 | `normalize_target` no formatter para mapear coluna GAL → coluna de resultado | identidade |

Fallback de painel no submit (`exportacao/envio_gal.construir_payload`): quando `panel_tests_id` nao consta em `gal_config.panel_tests`, `testes_do_painel` e derivado de `exam_cfg.export_fields` via `_norm_gal_field`. Exames com painel na config GAL nao sao afetados.

Regra de preservacao ao reeditar: `_build_registry_exam_config` usa `_pick/_pick_list` — novo valor (Passo 4) tem precedencia; se vazio, preserva o valor do registry existente.

### 3.4 Compartilhamento multiusuario
- `services.config_service.configure_shared_storage`: padroniza `data_root/allowed_roots`.
- `services.installation_checks`: valida path, CSV e ACL do compartilhamento.
- Auditoria READ-ONLY de 2026-05-15: classificacao multiusuario **APTO COM RESTRICOES**. Decisao humana posterior definiu implantacao inicial em piloto controlado com 3 a 5 usuarios. O desenho atual nao comprova aptidao plena para 10 usuarios sem backlog CONC adicional.

### 3.5 Envio GAL (atualizado 2026-05-30)

**Arquivos:**
- `application/gal_send_use_case.py` — orquestracao dos 6 passos; closure `_process_row` por amostra.
- `exportacao/envio_gal.py` — `GalService` (login, metadados, payload, envio, relatorios); `IntegrationApp` (UI modal).
- `services/gal/gal_transactions.py` — `build_idempotency_key`, `load_successful_idempotency_keys`, `append_transaction_journal_unique`.
- `services/gal/gal_status_reconciler.py` — `reconcile_gal_status` com lookup por chave e fallback por `codigo_amostra`.
- `exportacao/gal_payload_contract.py` — schema v1.0.0 do payload; validacao de nao-vazio de `codigo`.

**Fluxo de execute() — 6 passos (ordem vigente):**
1. Validar CSV (antes de abrir o browser — falha cedo sem custo de sessao).
2. Carregar `exam_cfg`; avisar se `gal_exame_codigo` vazio (`[S11]`).
3. Iniciar Firefox (headless por default via `gal_integration.headless`).
4. Login GAL; confirmacao explicitada no terminal.
5. Buscar metadados em `/bmh/entrada-resultados/lista/` (janela 15 dias) OU pular se `USE_GAL_ENVIO_SEM_METADADOS` / `gal_integration.envio_sem_metadados` ativos.
6. Envio paralelo (ThreadPoolExecutor 5 workers via `requests.Session` com cookies copiados do Selenium).

**Idempotencia dual-key (vigente):**
- Chave legada (4 campos): `codigo_amostra|kit|lote_kit|data_exame`.
- Chave escopo (4+N): adiciona `corrida|nome_corrida|arquivo_corrida|parte_placa`.
- `inflight_keys` atomicas sob lock: impede envio duplo de linhas identicas no mesmo CSV (race condition intra-lote resolvida — GAL-ROB-007).
- Persistencia imediata por amostra apos sucesso (resiliente a interrupcao).
- Fallback de reconciliacao: quando `kit`/`lote` ausentes em `exam_run`, busca por `codigo_amostra` direto no journal (GAL-ROB-010).

**Modo sem metadados (`USE_GAL_ENVIO_SEM_METADADOS` / `gal_integration.envio_sem_metadados`):**
- Pula `/lista/`; `metas` pre-populados com dicts vazios para cada `codigoAmostra`.
- `construir_payload`: `codigo` = `codigoAmostra` do CSV (fallback implementado — GAL-FEAT-002); `requisicao`/`paciente` ficam vazios.
- O GAL localiza o registro pelo par `codigo + gal_exame_codigo` (ex: VRSRT, PEQZDC).
- Rollback: `enabled=false` na flag ou `false` no config.

**Feature flags de rollback (config/feature_flags.json):**
- `USE_GAL_ENVIO_SEM_METADADOS` — pular metadados (default `false`).
- `USE_GAL_FIREFOX_HEADLESS` — headless por flag de desenvolvedor (default `false`; config tem precedencia menor).
- `USE_GAL_TERMINAL_LOG_POR_AMOSTRA` — log por amostra no terminal (default `true`; `false` reverte para resumo final).

**Terminal de envio:** apos cada amostra, exibe `codigoAmostra → STATUS` com detalhe de erro (ate 70 chars) e cor por nivel (info/warning/error/critical).

**Configuracoes GAL na UI (`tela_configuracoes.py`):**
- "Ocultar navegador durante envio" → `gal_integration.headless`.
- "Enviar sem buscar metadados do GAL" → `gal_integration.envio_sem_metadados`.

**Risco de concorrencia (documentado 2026-05-15, ainda aberto):** a idempotencia dual-key reduz duplicidade em fluxo sequencial, mas ainda exige CONC-003 (claim/lease antes do envio externo) para concorrencia real entre estacoes.

### 3.6 Escopo de exames
Guard de runtime opera em dois modos claramente distintos:
- **Registry carregado em runtime real**: `services.exam_registry.is_active(nome)` consulta a lista `active_exams` configurada, que representa os exames habilitados operacionalmente. Se a lista existir e o exame nao constar, `_analisar_corrida_pipeline()` levanta `domain.exam_scope.ExamForaDoEscopoError` antes de qualquer IO de analise (fail-closed). `active_exams` vazio em registry carregado bloqueia todos os exames. Exames adicionados pelo wizard/registry podem operar quando constarem em `active_exams` e tiverem configuracao/contrato valido.
- **Stubs de teste sem configuracao**: por contrato canonico, `is_active()` pode retornar `True` incondicionalmente para preservar suites que nao configuram `active_exams`. Esse comportamento e exclusivo do contexto de teste e nao afeta o fail-closed do registry real.

Componentes:
- `services.exam_registry`: `is_active(nome)` e `iter_active_exams()` — fonte canonica de consulta de escopo.
- `domain.exam_scope.ExamForaDoEscopoError`: excecao de dominio puro lancada pelo guard em `_analisar_corrida_pipeline()` quando o exame nao esta na lista `active_exams`.

Rastreabilidade: `requirements.md §8` CA-09 e CA-10; auditoria D-12.

### 3.7 Cadastro tecnico de equipamentos (SDD Fases 0-7 concluidas — ver tasks.md §7)
Fonte canonica unica para configuracao de equipamentos de PCR, substituindo CSV/JSON/builtins legados.

- `config/contracts/equipment/*.json`: um arquivo por equipamento ativo. Apenas `7500_extended.json` e `quantstudio.json` tem `active=true` em producao.
- `application.equipment_profile_service.EquipmentProfileService`: facade canonica. Expoe `list_active_profiles()`, `resolve_profile(alias)`, `detect_equipment(path)`, `validate_profile(profile)`, `save_profile(profile, actor)`. Escrita restrita a perfis ADMIN/MASTER.
- `services.contract_catalog.ContractCatalog.list_equipment_profiles()`: ponto de leitura dos perfis; respeita hierarquia `contracts > config_json > csv`.
- `services.equipment_detector.detectar_equipamento()`: detecta equipamento a partir de arquivo XLSX. Detector profile-driven com shadow legacy anexado/logado em divergencia (E05).
- `services/cadastros_diversos.py` (aba Equipamentos): UI de edicao tecnica completa — todos os campos do contrato sao editaveis, incluindo `signature`, `sheet_policy`, `row_policy`, `column_mapping`, `ct_policy` completo, `well_policy`, `extractor_strategy`, `validation_rules`. Escrita via `save_profile()` com backup atomico.

**Contrato minimo de perfil (`equipment_id`, `display_name`, `aliases`, `active`, `signature`, `sheet_policy`, `row_policy`, `column_mapping`, `ct_policy`, `well_policy`, `extractor_strategy`, `confidence_threshold`, `validation_rules`, `audit`).**

**Estado das fases (referencia `tasks.md §7` — E01..E07 `[Concluido]` em 2026-05-11):**
- Fase 0 (Baseline com fixtures reais), Fase 1 (Contratos JSON canonicos + aliases), Fase 2 (Facade `EquipmentProfileService`), Fase 3 (Detector profile-driven com shadow legacy), Fase 4 (Extracao por contrato sem fallback legado silencioso), Fase 5 parcial (UI tecnica completa), Fase 6 (Integracao UI com deteccao automatica) e Fase 7 (Deprecacao controlada) estao todas marcadas concluidas em `tasks.md`.
- **Decisao operacional sobre legado** (E07): conforme `docs/specs/equipment_legacy_deprecation.md`, `banco/equipamentos.csv`, `banco/equipamentos_metadata.csv`, `banco/profiles/equipment_profiles.json` e built-ins de `services/equipment_registry.py` permanecem **fisicamente presentes** para rollback controlado, com marcadores de origem em runtime (`legacy_equipment_csv`, `legacy_equipment_metadata_csv`, `legacy_equipment_profiles_json`, `legacy_builtin_registry`). **Remocao fisica nao foi executada nesta rodada e depende de DEC-002** (ver `requirements.md §10`).
- Documentacao auxiliar canonica:
  - `docs/specs/plano_equipamentos_sdd.md` — plano original das fases (referencia historica/canonica).
  - `docs/specs/equipment_legacy_deprecation.md` — decisao operacional E07.

Sem dividas residuais de fase aberta. Pendencias documentais e de codigo agregadas em `tasks.md §10`.

Rastreabilidade: auditoria D-03, D-10, D-11.

### 3.8 Módulo de relatórios e dashboard (atualizado 2026-05-30)

**Relatórios (`ui/modules/reports.py`):**
- `application/reports_query_use_case.py`: orquestra filtros, `ReportsSQLiteRepository` e reconciliacao GAL sem depender de UI.
- `application/reports_contracts.py`: DTOs `ReportsFilterDTO`, `ReportsResultDTO`, `ReportsDetailDTO`.
- `services/reports/reports_repository.py`: consultas SQLite-first sobre `banco_runtime/historico.db`.
- `services/gal/gal_status_reconciler.py`: `reconcile_gal_status(rows, journal_path)` — lookup por `chave_idempotencia` (normalizada com datas ISO) com fallback por `codigo_amostra` quando `kit`/`lote` ausentes.
- Status GAL exibido: `enviado`, `nao_enviado`, `erro`, `duplicado`, `sem_chave_gal`.

**Dashboard (`ui/modules/dashboard.py`) — 3 abas:**
- Fonte primaria (2026-05-30): `ExamRunsSQLiteRepository().list_rows()` (`banco_runtime/historico.db`) com `status_gal` por amostra via `reconcile_gal_status`. Fallback: `HistoryReportService` (CSV) → `db_utils` (legado). As abas Gestao Clinica e Visao Analitica leem do SQLite e sao atualizadas em `_finalizar_carregamento` independentemente do CSV do Operacional (nao ficam zeradas quando `df_historico` esta vazio).
- **Aba Operacional**: cards de resumo, grafico de analises/dia e tabela "Corridas Recentes". Barra de filtros (`_criar_barra_filtros`) com Periodo (7/30/180), Exame e intervalo De/Ate (DD/MM/AAAA, com botao de calendario `SimpleCalendar`); `_df_operacional()` aplica o filtro a cards, grafico e tabela. A tabela tem coluna "Corrida" (`nome_corrida`), ordenacao por clique no cabecalho (`_ordenar_tabela`: 1o clique asc, 2o desc) e barra de rolagem ancorada ao lado da lista.
- **Aba Gestao Clinica**: `DashboardAnalyticsService.obter_estatisticas_gestao(period_days, exame_filtro, data_inicio, data_fim)`. Quadro "Doencas Mais Positivas" com barra (Top 10, rotulos de dados), radar e pizza (Top 8, restante agregado em "Outros") numa unica `Figure`, mais tabela-resumo lateral (Alvo/Positivos/%). Rotulos em negrito.
- **Aba Visao Analitica** (nova): `DashboardAnalyticsService.obter_painel_analitico(exame_filtro)`. KPIs (Volume 15d, Volume/dia, Positividade %, Pendentes GAL), heatmap dia x doenca (janela de 15 dias) e tabela interativa de Ct medio (janelas fixas de 15/7/3 dias com setas de tendencia ▲▼➖ e % de variacao 7d vs 15d e 3d vs 7d). Clicar num alvo na tabela destaca-o no heatmap e atualiza a positividade do alvo (`_selecionar_alvo`). Apenas o filtro de Exame atua nesta aba (Periodo/datas ficam inativos, pois a tabela de Ct e por definicao 15/7/3 dias).
- **Detalhe da corrida (read-only)**: duplo-clique numa corrida abre `_abrir_detalhes_corrida` — janela `Treeview` (sem edicao) com Amostra/Poco/Resultado_Geral/Status_Placa + colunas canonicas `Res <alvo>`/`Ct <alvo>` (descarta `SRC_*` e metadados). Botao "Abrir Mapa Definitivo (Excel)" usa `_localizar_mapa_definitivo` para abrir o `.xlsx` `mapa_placa_*` gerado na analise em `<data_root>/mapas` (match normalizado por `nome_corrida`/arquivo de origem; usa o mais recente).
- `services/reports/dashboard_analytics.py`:
  - `obter_estatisticas_gestao`: aceita `data_inicio`/`data_fim` (ignora `period_days` e zera deltas quando fornecidos). Conta apenas colunas canonicas `RES_*` (ignora snapshots `SRC_RES_*` e controles `RP|CN|CP|GERAL`), eliminando a duplicacao "RES X" + "SRC RES X" e corrigindo a Positividade. Rotulos limpos via `limpar_nome_alvo` (remove prefixo `RES_`).
  - `obter_painel_analitico`: KPIs + `heatmap` + `ct_table` + `positividade_por_alvo` + `unique_exams`. Ct medio por alvo usa `parse_ct` sobre `CT_<alvo>` das amostras detectaveis. Pendentes GAL = amostras nao-controle com status reconciliado != `enviado`/`duplicado` (`_contar_pendentes_gal`).
- Componente `ui/modules/componentes/card_resumo.py`: `CardResumo` ganhou `set_valor`/`set_indicativo` (alias de `atualizar_valor` + criacao sob demanda do label de indicativo) — usado pelas abas Gestao/Visao Analitica.

**Principios comuns:**
- Modulos somente leitura: nenhum IO de analise, GAL ou configuracao.
- Equipamentos tratados como metadado opcional de auditoria.
- Relatorios operacionais priorizam exame, periodo, analista, kit/lote, positividade e status GAL.

### 3.9 Padronizacao Visual e Sistema de Design (UI)
O sistema adota um Design System centralizado inspirado em interfaces web institucionais, implementado via `CustomTkinter` para garantir alta performance sem dependência de navegadores.

- **Fundações:** 
  - Fundo principal: Cinza claro (`#F4F6FA`).
  - Cards e Paineis: Branco (`#FFFFFF`) com borda solida de separacao (`#E2E8F0`), evitando o uso de sombras complexas (que degradam performance no Tkinter).
  - Acoes Primarias: Azul institucional (`#1A56DB`).
- **Estados Clinicos e Cores Canonicas:**
  - `Não Detectável` / Sucesso: Verde (`#16A34A`).
  - `Indeterminado` / Aviso: Amarelo/Laranja (`#CA8A04`).
  - `Detectável` / Inválido / Falha: Vermelho (`#DC2626`).
- **Arquitetura UI:** 
  - Paradigma de Navegacao: "Janela Unica" (Single Window Context). Uso de MainFrame com Sidebars ao inves da criacao de Toplevels multiplos.
  - Componentes basicos (Botoes, Entradas, Badges, Cards) devem ser isolados em classes reutilizaveis dentro de `ui/components/`. 
  - A UI apenas reflete as regras de dominio (DTOs de entrada), sendo estritamente proibido duplicar lógicas clínicas em eventos de tela.

### 3.10 Arquitetura de paths — logs e dados operacionais (2026-05-29)

**Root canônico de logs**: `logs/`
Todos os componentes de gravacao de log devem resolver via `config_service.get_paths()["logs_dir"]` com fallback para `"logs"`. Nenhum componente deve usar path hardcoded sem consultar o config service.

Componentes e seus mecanismos de resolucao:
- `utils/logger.py` (`sistema.log`): lê `log_file` do config service; fallback `logs/sistema.log`.
- `utils/audit_logger.py` (`audit/audit.log`): `_resolve_audit_log_dir()` lê `logs_dir` do config service; fallback `logs/audit`.
- `utils/dataframe_reporter.py` (`dataframe_reports/`): `_resolve_dataframe_log_dir()` lê `logs_dir`; fallback `logs/dataframe_reports`.
- `services/legacy_panel_governance.py` (`legacy_panel_rollout.csv`): `_resolve_default_log_path()` consulta env var → config service → fallback `logs/legacy_panel_rollout.csv`.
- `services/gal/gal_transactions.py` (journals GAL): lê `logs_dir` via paths do config service.
- `exportacao/exportar_resultados.py` (`resultados_por_amostra.txt`): lê `logs_dir` → fallback `dirname(log_file)`.
- `services/persistence/exam_runs_csv.py` (`corridas_<slug_exame>.csv`): recebe `logs_root` do chamador, que resolve via `logs_dir`.

**Estrutura canônica de `logs/`:**
```
logs/
├── sistema.log                       # log centralizado CSV (;)
├── audit/audit.log                   # auditoria JSON RotatingFileHandler
├── corridas_<slug_exame>.csv         # historico por exame (SQLite-first com CSV mirror)
├── historico_analises.csv            # historico GAL (gal_history_csv)
├── gal_transacoes.csv                # journal unificado GAL
├── gal_transacoes_sucesso.csv        # ledger de sucessos GAL
├── gal_upload_history.csv            # historico de uploads
├── relatorio.csv                     # relatorio estruturado de envios
├── resultados_por_amostra.txt        # detalhamento de resultados
├── legacy_panel_rollout.csv          # governanca do painel legado
├── historico_processos.csv           # fallback CSV quando SQLite offline
└── dataframe_reports/                # diagnosticos de DataFrames
```

**Root canônico de dados operacionais**: `banco_runtime/`
- `services/path_resolver.py::resolve_banco_dir()`: lê `exams_catalog_csv` do config service; fallback `banco_runtime/`.
- `config/paths.py::BANCO_DIR`: `BASE_DIR / "banco_runtime"`.
- `services/persistence/exam_runs_sqlite.py::default_exam_runs_db_path()`: `resolve_banco_dir() / "historico.db"`.

**Root canônico de templates/esquemas**: `banco_template/`
- `services/engine/config_loader.py::ConfigLoader.BASE_PATH`: `Path("banco_template")`.
- Contém: `profiles/equipment_profiles.json`, `protocols/analysis_protocols.json`, `protocols/analysis_rules.json`, e CSVs de metadados (schema completo).
- Somente leitura em runtime. Nao deve ser gravado pela aplicacao.

**`banco/` (legado — DEC-002)**: mantido fisicamente como fallback operacional controlado. Nao ha escrita ativa para esta pasta. Remocao fisica depende de DEC-002 resolvida. Ver `tasks.md §10` DHP-10/DHP-11/DHP-12 para itens residuais pendentes de decisao humana.

**`dados/banco/` (residuo extinto)**: existia como consequencia do bug `logs_dir = "dados/banco"` (corrigido em LOG-UNIF-001). Arquivos unicos migrados para `logs/` em LOG-UNIF-002. Itens residuais pendentes de DHP-11.

Guardiao de regressao: `tests/test_log_paths_uniformization.py` (9 casos) e `tests/test_banco_path_fallbacks.py` (7 casos).

## 4. Contratos obrigatorios

### 4.1 Retorno de mapeamento
```python
{
  "mapeamento": DataFrame,
  "parte": int,
  "numero_extracao": str,
  "caminho_arquivo": str,
}
```

### 4.2 Profile de CT por exame/alvo
```python
{
  "default_rule": {...},
  "by_target": {"ALVO": {...}},
  "rp_min": float,
  "rp_max": float,
}
```

### 4.3 Chave de idempotencia GAL
Esquema dual (ambas verificadas antes do envio; ambas adicionadas ao conjunto em memoria apos sucesso):
- **Chave legada (4 campos)**: `codigo_amostra|kit|lote_kit|data_exame`
- **Chave com escopo (4+N campos)**: `codigo_amostra|kit|lote_kit|data_exame|campo=valor...`

Somente linhas com `status=sucesso` no journal bloqueiam reenvio. `status=erro` e `status=duplicado` permitem retry.
Dedup intra-batch via conjunto em memoria (`successful_keys`) — sem acesso adicional ao journal por linha.

### 4.4 Consulta de relatorios
Contrato de entrada minimo:
```python
{
  "data_inicio": "YYYY-MM-DD",
  "data_fim": "YYYY-MM-DD",
  "exames": ["<exame habilitado>", "..."],
  "status_realizacao": ["realizado", "a_realizar"],
  "positividade": ["positivo", "negativo", "inconclusivo", "invalido"],
  "analistas": ["usuario"],
  "kits": ["kit"],
  "lotes": ["lote"],
  "status_gal": ["enviado", "nao_enviado", "erro", "duplicado"],
  "agrupar_por": ["periodo", "exame", "positividade", "analista", "kit", "status_gal"],
  "limit": 500,
  "offset": 0,
}
```

Contrato de saida minimo:
```python
{
  "resumo": {...},
  "agrupamentos": [
    {"chaves": {...}, "total": 0, "positivos": 0, "negativos": 0, "pendentes_gal": 0}
  ],
  "detalhes": [
    {
      "corrida_id": "...",
      "amostra_codigo": "...",
      "exame": "...",
      "data_exame": "YYYY-MM-DD",
      "analista": "...",
      "kit": "...",
      "lote": "...",
      "resultado_geral": "...",
      "status_gal": "enviado|nao_enviado|erro|duplicado",
    }
  ],
  "paginacao": {"limit": 500, "offset": 0, "total_estimado": 0},
}
```

Filtros de exame devem respeitar `ExamRegistry.active_exams`. Exame fora de escopo deve falhar antes de qualquer leitura pesada ou exportacao.

## 5. Fluxos

### 5.1 Fluxo de analise
1. Selecionar exame + arquivo de corrida + contexto de extracao.
2. Classificar alvos por CT.
3. Consolidar `Resultado_geral`.
4. Mostrar tabela e cores/tags.
5. Permitir ajuste de mapa e sincronizar tabela.

### 5.2 Fluxo item 7 (incluir/editar)
1. Abrir modulo maximizado.
2. Exibir lista rolavel de exames cadastrados.
3. Selecionar exame e abrir formulario completo de edicao.
4. Salvar em registry e recarregar catalogo.

### 5.3 Fluxo de compartilhamento
1. ADMIN ou MASTER define compartilhamento unico no modulo de instalacao inicial, com confirmacao forte antes de aplicar configuracao e registro em log/auditoria.
2. Sistema aplica `data_root` e `allowed_roots` unificados.
3. Checklist valida ACL leitura/escrita.
4. Antes de uso produtivo irrestrito, instalacao deve cobrir backlog INST: lock/atomic write de `config.json`, dry-run, backup/rollback, ajuste ADMIN+MASTER conforme DEC-010 e teste end-to-end do wizard.

### 5.4 Fluxo de relatorios
1. Usuario abre o modulo de relatorios.
2. Sistema carrega opcoes de filtros a partir de fontes canonicas e do escopo ativo.
3. Usuario informa periodo e filtros opcionais.
4. Use case valida escopo e normaliza filtros.
5. Repositorio executa consultas SQLite-first e reconcilia status GAL pelo journal.
6. UI exibe resumo, agrupamentos e detalhes paginados.
7. Usuario exporta CSV/XLSX com metadados dos filtros aplicados quando necessario.

## 6. Restricoes
- Somente exames habilitados em `active_exams` podem operar em producao; exames ausentes continuam fail-closed.
- Postgres dedicado nao deve ser usado (provider nao implementado).
- Mudanca critica sem teste de regressao e proibida.
- Quebra de schema CSV exige migracao explicita.
- Relatorios nao podem recalcular classificacao de CT nem duplicar prioridade de `Resultado_geral`; devem consumir resultados persistidos.
- Consultas de relatorio devem ser somente leitura e nao podem acionar IO de analise, envio GAL ou alteracao de historico.

## 7. Diretriz de testes
Executar pelo menos:
```powershell
python -m pytest tests/test_ct_classification.py tests/test_vr1_vr2_inconclusivo_runtime.py -q --tb=short
python -m pytest tests/test_analysis_service_phase6_vectorization.py tests/test_classificacao_cores_caracterizacao_h03.py -q --tb=short
python -m pytest tests/test_extraction_plate_mapping_use_case.py tests/test_mapeamento_extracao_caracterizacao_h04.py -q --tb=short
python -m pytest tests/test_0260325_exam_creator_registry_rollout.py tests/test_shared_storage_standardization.py -q --tb=short
```

## 8. Dividas tecnicas documentadas
Achados estruturais identificados na auditoria SDD 2026-05-12 (READ-ONLY). Esta secao registra dividas para tratamento em rodadas proprias de codigo.

- **DT-001 (D-01) - RESOLVIDA**: `domain/ct_rules.py` nao importa mais `pandas` e nao usa mais `pd.isna`. A regra de CT passou a usar checagem nativa com `math.isnan`, mantendo `domain/` livre de dependencias pesadas de infraestrutura. Evidencias registradas em `tasks.md`: T-AUD-008 (`tests/test_domain_pure_imports.py`) e T-AUD-001 concluidas; recorte CT validado. Nova orientacao: nao reintroduzir `pandas`, UI, Selenium ou dependencias equivalentes em `domain/`.
- **DT-002 (R-T3)**: `services/` concentra dezenas de modulos e arquivos individuais grandes (`cadastros_diversos.py`, `analysis_service.py`). Alto custo cognitivo, sem violacao funcional. Tratamento: inventario para futuro split por subdominio (analysis/, equipment/, gal/, reports/, persistence/). Refatoracao ampla NAO esta autorizada nesta rodada. Tarefa: T-AUD-010.
- **DT-003 (D-04)**: `core/authentication/user_manager.py` (~1900 LOC) coexiste com `autenticacao/auth_service.py`. Nao caracterizado como dead code sem verificacao de callers. Tratamento: auditar callers reais e decidir consolidacao ou deprecacao. Tarefa: T-AUD-004 / T-AUD-013.

## 9. Limitacoes conhecidas
- **LIM-001 (D-02 / DEC-001)**: `config.json` versionado nao esta pronto para producao — `shared_storage.required=true` com `data_root=""` e `allowed_roots=[]`. Instalacao Inicial (T11) e obrigatoria antes do primeiro uso. Ver `requirements.md §7.1` e CA-12.
- **LIM-002 (D-08) - RESOLVIDA COMO CORRECAO FORMAL, MANTIDA COMO LIMITACAO OPERACIONAL**: T-AUD-008-CFG removeu a chave literal vazia `""` e corrigiu o mojibake de `lab_responsible` sem inserir dados reais sensiveis. `config.json` permanece template/local runtime nao pronto para producao; `shared_storage.root`, `data_root` e `allowed_roots` seguem vazios ate a Instalacao Inicial/configuracao local validada.
- **LIM-003 (D-11)**: arquivos legados em `banco/*` (`equipamentos.csv`, `equipamentos_metadata.csv`, `profiles/equipment_profiles.json`) permanecem fisicamente presentes apos E07. Remocao depende de DEC-002. Fallback documentado em `equipment_legacy_deprecation.md`.
- **LIM-004 (2026-05-15)**: capacidade para 10 usuarios simultaneos nao comprovada. Estado atual: APTO COM RESTRICOES; implantacao inicial aprovada como piloto controlado com 3 a 5 usuarios. CONC-002, CONC-003 e INST-001 sao prioritarias antes de ampliar para 10 usuarios.
- **LIM-005 (2026-05-15)**: modulo de Instalacao Inicial funcional com restricoes. Falta lock/atomicidade de `config.json`, dry-run, rollback, ajuste ADMIN+MASTER conforme DEC-010 e teste end-to-end do wizard.

## 10. Pendencias documentais e decisoes humanas
Consolidadas em `tasks.md` (tarefas T-AUD, SDD-20260514, UI-AUD, HIG, LOG-UNIF). Referencia cruzada para `requirements.md` (DEC-001 a DEC-007). Todas as DHP anteriores foram resolvidas. DHPs abertas em 2026-05-29: DHP-10 (`dados/banco/historico.db`, 131KB, mais antigo — verificar antes de excluir), DHP-11 (CSVs duplicados residuais em `dados/banco/` apos migracao — decidir destino), DHP-12 (`banco_template/historico.db`, 3.3MB, conteudo desconhecido — verificar antes de qualquer decisao).

## 11. Atualizacoes de desenho registradas em 2026-05-14

Estas regras refletem comportamento ja implementado e documentado para evitar que agentes reabram diagnosticos concluidos antes da auditoria de higienizacao.

- **Relatorio final pre-GAL**: analise concluida com envio GAL ainda nao executado e estado operacional valido. Deve ser registrada como `status_execucao=analise_concluida_envio_pendente`, `status_envio_gal=pendente_envio` e `status_item=selecionado_pendente_envio`, nao como falha de analise.
- **Completude VR1e2 com placa cheia**: para contrato VR1e2 com 96 pocos e agrupamento de 2 pocos/amostra, a saida esperada e 48 grupos. Perda de grupos por mapeamento/gabarito ausente ou malformado deve falhar fail-closed com erro claro (`AnalysisCompletenessError`) antes de relatorio parcial.
- **Extrator por contrato**: saidas com aliases contratuais (`bem`, `amostra`, `alvo`, `ct`) devem ser normalizadas para o vocabulario esperado pelo pipeline (`Well`, `Sample`, `Target`, `Ct`) antes da identificacao de colunas PCR.
- **Tela de Analise / Reaplicar Selecao**: a selecao automatica deve depender das colunas ja calculadas de aptidao operacional: `Sugestao_de_repeticao=Nao`, `Res_RP_1=Valido`, `Res_RP_2=Valido`, `Status_Placa=Valida`, excluindo CN, CP e controles.
- **UI-AUD e HIG**: inventario UI, plano de modernizacao UI e auditoria de higienizacao seguem pendentes; esta secao nao autoriza execucao de limpeza, remocao, migracao ou refatoracao.

## 13. Atualizacoes de desenho registradas em 2026-05-29

Estas regras refletem as correcoes de uniformizacao de paths implementadas em LOG-UNIF-001 e LOG-UNIF-002. Nao autorizam alteracao de `config.json` runtime, banco de dados, scripts de limpeza ou qualquer acao fora do escopo das tarefas concluidas.

- **Root unificado de logs**: `logs/` e o unico root canônico para gravacao de logs e arquivos de saida de corridas. O bug `logs_dir = "dados/banco"` foi corrigido em `config/default_config.json`. Todos os componentes de log agora consultam `config_service.get_paths()["logs_dir"]` com fallback para `"logs"`.
- **Componentes de log configuráveis**: `AuditLogger`, `DataFrameReporter` e `_resolve_default_log_path()` de `legacy_panel_governance` passaram a aceitar path `None` e consultar o config service. Path hardcoded era o comportamento anterior.
- **Fallback de `resolve_banco_dir()`**: alterado de `banco/` (pasta legada) para `banco_runtime/` (pasta ativa). O codigo legado que resolvia para `banco/` sem configuracao agora cai em `banco_runtime/`, alinhando com `config.json`, `config/paths.py` e `ExamRunsSQLiteRepository`.
- **`ConfigLoader.BASE_PATH`**: alterado de `Path("banco")` para `Path("banco_template")`. Agora `get_equipment_profiles()`, `get_protocols()` e `get_analysis_rules()` encontram os JSONs reais em `banco_template/profiles/` e `banco_template/protocols/`.
- **`DEFAULT_ROOTS` dos scripts de encoding**: `scripts/normalize_legacy_csv_utf8.py` e `scripts/scan_csv_encoding_conformance.py` agora incluem `banco_runtime` alem de `banco` (legado mantido por compatibilidade).
- **Migracao de corridas CSVs**: `corridas_vr1e2_biomanguinhos_7500.csv` (296KB) e `corridas_zdc_biomanguinhos.csv` (42KB) movidos de `dados/banco/` para `logs/` — local correto conforme `exam_runs_csv.py` que usa `logs_root`. Backup em `snapshots/dados_banco_backup_20260529/`.
- **`dados/banco/` extinto como destino ativo**: apos migracao dos arquivos unicos e correcao do `logs_dir`, nenhum componente ativo grava em `dados/banco/`. Itens residuais (historico.db obsoleto, CSVs duplicados) aguardam DHP-10/DHP-11.
- **`banco_template/historico.db`**: 3.3MB, conteudo desconhecido — aguarda DHP-12 antes de qualquer decisao.
- **Guardioes de regressao criados**: `tests/test_log_paths_uniformization.py` (9 casos) e `tests/test_banco_path_fallbacks.py` (7 casos). Suite completa: 55 testes, zero falhas.

## 14. Atualizacoes de desenho registradas em 2026-05-30

### 14.1 Wizard de criacao de exames (WIZ-GAL-01..07)
- **Wizard agora captura todos os campos necessarios para analise e envio GAL.** Fluxo expandido para 4 passos: Passo 1 inclui `equipamento` (selecionado dos contratos ativos em `config/contracts/equipment/`) e `tipo_placa_analitica`; novo Passo 4 captura `gal_exame_codigo`, `kit_codigo`, `panel_tests_id` e tabela de mapeamento alvo→nome_no_GAL (gera `export_fields` e `mapa_alvos`). Ver contrato completo em §3.3.1.
- **Regra de preservacao ao reeditar**: `_build_registry_exam_config` preserva campos GAL do registry quando o novo valor vem vazio — evita o bug que zeravam `gal_exame_codigo`/`panel_tests_id` ao reeditar um exame.
- **Fallback de painel no submit**: `exportacao.envio_gal._norm_gal_field` + fallback em `construir_payload` deriva `testes_do_painel` de `exam_cfg.export_fields` quando o painel nao consta na config GAL. Exames com painel na config GAL continuam com o comportamento anterior (sem regressao).
- **Avisos suaves de integracao GAL**: `RegistryExamEditor.validate_exam` emite `WARNING` (nao bloqueia) quando `gal_exame_codigo`, `kit_codigo` ou `export_fields` estao vazios. O save prossegue para nao quebrar exames legados.
- **Regra de dominio — poco vazio = Invalido** (retroativo, implementado em 2026-05-29): `domain.resultado_geral.is_amostra_vazia` define poco vazio como codigo em branco, apenas "X" ou prefixo "Vazio...". `_apply_resultado_geral_vectorized` em `analysis_service` forca `Resultado_geral = Invalido` e `Selecionado = False` para esses pocos, em todos os exames.
- **Guardioes de regressao**: `tests/test_exam_creator_campos_gal.py` (8 casos), `tests/test_exam_creator_preserva_gal_codigo.py` (atualizado), `tests/test_poco_vazio_invalido.py`. Suite acumulada: 77 testes (1 falha de ambiente Tk pre-existente, sem relacao com codigo).

### 14.2 Dashboard analitico, filtros e correcoes de UI (DASH-003..008 + UI-fix)
- **Visao Analitica (DASH-005)**: nova aba com `obter_painel_analitico` (KPIs, heatmap dia x doenca, tabela de Ct 15/7/3 dias interativa com setas/percentuais e destaque por alvo). Ver §3.8.
- **Doencas Mais Positivas (DASH-003/004)**: deduplicacao para colunas canonicas `RES_*` (some "SRC RES X"), Top 12, rotulos limpos; quadro com barra + radar + pizza numa unica figura + tabela-resumo lateral; rotulos em negrito.
- **Filtros (DASH-006)**: barra reutilizavel (Periodo/Exame/De-Ate/Filtrar) nas abas Operacional (filtra cards/grafico/tabela via `_df_operacional`) e Visao Analitica (somente Exame).
- **Corridas Recentes (DASH-007/008)**: coluna "Corrida" (`nome_corrida`); janela de detalhes read-only corrigida (bug de import `ui.theme.design_tokens` -> usa `CORES`/`FONTES` de `.estilos`); botao "Abrir Mapa Definitivo (Excel)" via `_localizar_mapa_definitivo` (`<data_root>/mapas`); caixa de busca lateral desativada; barra de rolagem reancorada no mesmo container; ordenacao por clique no cabecalho (asc/desc).
- **Correcoes de UI associadas**:
  - `CardResumo.set_valor/set_indicativo` (DASH-FIX-001) — corrige os cards de Gestao que ficavam zerados por `AttributeError` silencioso; update de Gestao/Visao Analitica desacoplado do CSV.
  - `tela_configuracoes._carregar_categoria` passou a chamar `_carregar_valores()` (CFG-UI-001) — categorias carregadas sob demanda agora refletem a config; corrige o switch "Ocultar navegador durante envio" exibido OFF apesar do default `gal_integration.headless=true`.
  - `exam_creator/wizard.py` (WIZ-UI-001): Passo 1 reorganizado em grade compacta (cabe sem rolagem; o botao "Editar Exame Selecionado" volta a ficar visivel) e botao "Limpar Etapa" (`clear_current_step`) por passo.
  - `reports.SimpleCalendar` parametrizado com `date_format` (CAL-UI-001); campos De/Ate da Gestao ganham botao de calendario.
- **Verificacao**: validacao headless de analytics/figuras/ordenacao + suite `-k "analytics or dashboard or relatorio or estatistic"` (1 passed) e import smoke OK. Sem novas dependencias (matplotlib/numpy/openpyxl ja presentes).

## 12. Atualizacoes de desenho registradas em 2026-05-15

Estas regras registram a auditoria READ-ONLY de capacidade multiusuario e modulo de instalacao. Nao autorizam alteracao de codigo, `config.json`, banco, scripts, limpeza ou GAL real.

- **Multiusuario**: classificacao operacional atual = `APTO COM RESTRICOES`. Decisao humana registrada: implantacao inicial em piloto controlado com 3 a 5 usuarios.
- **Instalacao Inicial**: classificacao operacional atual = `FUNCIONAL COM RESTRICOES`. O modulo existe, mas precisa do backlog INST antes de uso produtivo irrestrito.
- **Meta condicionada**: 10 usuarios simultaneos depende da conclusao dos testes CONC e correcoes prioritarias.
- **Prioridade antes de ampliar para 10 usuarios**: CONC-002 (teste multiprocess 10 usuarios em CSVs criticos), CONC-003 (claim/lease GAL antes do envio) e INST-001 (lock/atomic write para `config.json`).
- **Decisao registrada em DEC-010**: Instalacao Inicial deve ser acessivel por ADMIN e MASTER, desde que protegida por confirmacao forte, log/auditoria e, futuramente, backup previo. INST-004 permanece pendente para ajuste de UI/codigo em rodada propria caso a aba ainda restrinja acesso apenas a ADMIN.
