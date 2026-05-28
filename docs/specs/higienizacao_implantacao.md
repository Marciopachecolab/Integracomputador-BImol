# Higienizacao para Implantacao - Plano Formal

Status: plano formal documentado; nenhuma higienizacao executada.
Criado em: 2026-05-14, na sincronizacao SDD pre-higienizacao.
Atualizado em: 2026-05-15, apos Auditoria READ-ONLY de Higienizacao para Implantacao.

## 1. Estado atual da auditoria

- Classificacao da auditoria HIG READ-ONLY: **ATENCAO**.
- A pasta atual nao esta pronta para empacotamento direto.
- Estado Git observado na auditoria: 0 arquivos rastreados e 2586 arquivos nao rastreados.
- Baseline informado pelo usuario: `integragal_baseline_pre_higienizacao_2026-05-15.zip`.
- RELEASE-001 esta concluida por registro documental do baseline informado; isso nao autoriza limpeza automatica.
- Scripts de limpeza em `scripts/` foram classificados como potencialmente destrutivos e permanecem bloqueados para execucao nesta fase.
- Nenhuma limpeza, movimentacao, remocao, execucao de script, teste, aplicacao ou Selenium/GAL foi executada. HIG-004 atualizou apenas `.gitignore` para bloquear rastreamento futuro de artefatos runtime e sensiveis.

## 2. Regras de seguranca

- Nao executar scripts de limpeza sem auditoria propria, autorizacao explicita, baseline validado e decisoes DHP aplicaveis.
- Nao remover, mover, renomear ou compactar arquivos sem rodada propria autorizada.
- Alteracoes futuras em `.gitignore` exigem rodada propria; HIG-004 foi a atualizacao controlada autorizada em 2026-05-15.
- Nao abrir `banco/*`, bancos `.db`/`.sqlite`, `.env.txt`, logs, reports ou arquivos potencialmente sensiveis para leitura de conteudo.
- Nao expor credenciais, usuarios, senhas, tokens, chaves, dados laboratoriais ou caminhos sensiveis alem do necessario para classificacao.
- Nao remover `banco/*` sem resolucao de DHP-02/DHP-09.
- O pacote de release nao deve conter `logs/`, `reports/`, `relatorios/`, `.tmp/`, `.venv/`, `banco/*`, `.env.txt`, caches, bancos locais ou dados laboratoriais gerados.

## 3. Fases HIG

| Fase | Objetivo | Acoes futuras permitidas somente em rodada propria | Criterio de aceite |
|---|---|---|---|
| H0 | Baseline e backup | Validar disponibilidade do baseline `integragal_baseline_pre_higienizacao_2026-05-15.zip`; se necessario, criar novo baseline autorizado antes de qualquer acao. | Baseline localizado, restauravel e registrado; nenhuma limpeza sem ponto de retorno. |
| H1 | Atualizacao controlada de `.gitignore` | HIG-004 aplicada em 2026-05-15 com regras explicitas para artefatos runtime/sensiveis. | `.gitignore` cobre `.env*`, caches, `.tmp`, `pytest_tmp`, `reports/`, `relatorios/`, logs, snapshots `encoding_backup_*`, bancos locais e dumps runtime sem bloquear arquivos essenciais. |
| H2 | Separacao de artefatos runtime | Separar runtime gerado de codigo/release; definir diretorios runtime vazios para o pacote. | Release nao inclui artefatos gerados, mas a aplicacao tem locais definidos para cria-los no ambiente alvo. |
| H3 | Retencao/arquivamento de logs, reports e relatorios | Definir politica de retencao, mascaramento e arquivamento para `logs/`, `reports/` e `relatorios/`. | Politica aprovada; nenhum dado operacional entra no release; retencao preserva rastreabilidade necessaria. |
| H4 | Auditoria dos scripts de limpeza | Revisar `scripts/limpeza_logs_reports.ps1`, `scripts/limpeza_prioridade_alta.ps1` e scripts correlatos; exigir dry-run/WhatIf quando aplicavel. | Scripts classificados como autorizados, bloqueados ou obsoletos; nenhum script destrutivo executado sem aprovacao. |
| H5 | Tratamento de legados bloqueados por DHP | Resolver DHP-02/DHP-09 antes de qualquer acao sobre `banco/*`; aplicar DEC-004 para snapshots e DEC-005 para dumps de corrida em rodadas proprias. | Decisoes humanas registradas; acoes futuras rastreadas; nenhum legado ou artefato removido sem DEC. |
| H6 | Montagem do pacote de release | Manifest documental criado por HIG-008; script de whitelist criado por REL-004 (`scripts/build_release_whitelist.ps1`); montagem fisica do pacote permanece para rodada propria com `-Execute`. | Pacote futuro deve conter apenas runtime necessario, config template, assets e docs operacionais aprovados. |
| H7 | Validacao pos-higienizacao | Executar validacoes autorizadas apos higienizacao: estrutura, smoke tests, verificacao de ausencia de dados sensiveis. | Checklist de release aprovado; testes autorizados passam; pacote e reproduzivel. |

## 4. Backlog HIG

| ID | Tema | Status atual | Proxima acao |
|---|---|---|---|
| HIG-001 | `.tmp`, caches, `pytest_tmp`, `.env.txt` | Concluida como auditoria READ-ONLY/classificacao | Limpeza/ignore somente em rodada propria; `.env.txt` nao distribuir. |
| HIG-002 | `reports/`, `relatorios/`, `logs/` | Concluida como auditoria READ-ONLY/classificacao | Definir retencao/arquivamento e excluir do release. |
| HIG-003 | Scripts de limpeza | Concluida como classificacao READ-ONLY | Auditoria propria antes de qualquer execucao. |
| HIG-004 | `.gitignore` explicito | Concluida | `.gitignore` atualizado com regras explicitas; nao remove arquivos existentes nem resolve HIG-006/HIG-007/HIG-008. |
| HIG-005 | `banco/*` | Concluida documentalmente (Opcao A, 2026-05-15) | DEC-002 resolvida: `banco/*` mantido fisicamente em dev/runtime como fallback operacional controlado; conteudo sensivel nao aberto; manifest HIG-008 exclui do release integralmente; nenhum arquivo aberto, movido, arquivado ou excluido. Tarefas futuras nao bloqueantes: PRIV-001, GIG-001, HIG-009. |
| HIG-006 | `snapshots/encoding_backup_*` | Concluida documentalmente (Opcao A, 2026-05-15) | 16 diretorios encontrados vazios (0 KB); `.gitignore` ja cobre (HIG-004, linha 936); manifest HIG-008 exclui do release; nenhuma remocao, movimentacao, compactacao ou arquivamento executado; diretorios permanecem fisicamente em `snapshots/`. |
| HIG-007 | `relatorio_final_corrida_*.json` | Concluida documentalmente (Opcao A, 2026-05-15) | `.gitignore` ja cobre o padrao; arquivos permanecem fisicamente na raiz sem remocao/movimentacao; manifest HIG-008 os exclui do pacote de release; presenca fisica nao autoriza inclusao no release. |
| HIG-008 | Manifest/estrutura limpa de release | Concluida como documentacao | Manifest definido neste documento; estrutura ainda nao foi materializada, copiada ou empacotada. |

## 5. Decisoes humanas pendentes

Nenhuma DHP HIG pendente.

## 5.1 Decisoes resolvidas relevantes

- DHP-02 / DHP-09 / DEC-002: **RESOLVIDA em 2026-05-15** - `banco/*` legados mantidos fisicamente em dev/runtime como fallback operacional controlado, sem abertura de conteudo sensivel nesta decisao. Manifest HIG-008 exclui `banco/*` do release integralmente. Nenhuma exclusao, movimentacao, arquivamento ou migracao fisica autorizada nesta etapa. Tarefas futuras nao bloqueantes: PRIV-001, GIG-001, HIG-009. HIG-005 concluida documentalmente (Opcao A).
- DHP-04 / DEC-004: **RESOLVIDA em 2026-05-15** - diretorios `snapshots/encoding_backup_*` sao artefatos historicos de backup/encoding para rastreabilidade e eventual recuperacao, nao devem entrar no release operacional e devem ser tratados por retencao, arquivamento externo ou exclusao controlada em rodada propria apos baseline/backup, sem exclusao automatica.
- DHP-05 / DEC-005: **RESOLVIDA em 2026-05-15** - arquivos `relatorio_final_corrida_*.json` na raiz sao artefatos runtime/transitorios, nao devem entrar no release operacional e devem ser tratados por retencao, realocacao ou `.gitignore` em rodada propria, sem exclusao automatica.
- DHP-07 / DEC-007: **RESOLVIDA em 2026-05-15** - `README.md` humano e operacional criado na raiz como ponto de entrada para instalacao, execucao, configuracao inicial, restricoes conhecidas, piloto 3-5 usuarios, itens fora do release e alertas de seguranca. Nao substitui a documentacao SDD.

## 6. Manifest documental da estrutura limpa de release

Status HIG-008: **concluida como documentacao**. Este manifest define a estrutura alvo do pacote de implantacao, mas a estrutura ainda **nao foi materializada**: nenhuma pasta `release/` foi criada, nenhum arquivo foi copiado, movido, removido ou empacotado.

**REL-004 concluida (2026-05-17):** Script de materializacao por whitelist criado em `scripts/build_release_whitelist.ps1`. O uso inicial deve ser em modo simulacao (omitir `-Execute`). A execucao real com `-Execute` exige rodada futura autorizada com baseline/backup disponivel. O script NAO foi executado nesta rodada e `release/` NAO foi criada.

```text
release/
  app/
  config_template/
  docs_operacionais/
  assets/
  scripts_autorizados/
  runtime_empty/
```

### 6.1 `release/app/`

Incluir somente runtime necessario para executar o IntegRAGal:

- `main.py`
- `models.py` (RUNTIME OBRIGATORIO — importado por `application/analysis_orchestrator.py`, `services/analysis_service.py`, `services/service_container.py` e `ui/main_window.py`; ausente do manifest original)
- `domain/`
- `application/`
- `services/`
- `ui/`
- `autenticacao/`
- `exportacao/`
- `browser/`
- `utils/`
- `db/`
- `config/`
- `requirements.txt`
- assets necessarios para a UI, preferencialmente consolidados em `release/assets/` quando o empacotador permitir.

Excluir de `release/app/`:

- `tests/`, `test_data/`, fixtures e arquivos de caracterizacao;
- `reports/`, `relatorios/`, `logs/`;
- `.tmp/`, `pytest_tmp/`, `.pytest_cache/`, `__pycache__/`, `.mypy_cache/`;
- `.venv/`, `venv/`, `env/`;
- `snapshots/encoding_backup_*`;
- `banco/*`;
- `.env`, `.env.*`, `.env.txt`;
- `relatorio_final_corrida_*.json`;
- bancos locais `.db`, `.sqlite`, `.sqlite3`;
- scripts de limpeza nao auditados;
- `analise/` (legado; motor real em `services/engine/analysis_engine.py`; confirmado sem imports de producao em REL-002);
- `extracao/` (legado; use case real em `application/extraction_plate_mapping_use_case.py`; confirmado sem imports de producao em REL-002);
- `interface/` (fachada de compatibilidade para testes; re-exports puros de `ui.modules.*`; nenhum import de producao);
- `core/` (legado em deprecacao controlada, DEC-003; `core/authentication/user_manager.py` neutralizado por T-AUD-004A/004B; nenhum import de producao);
- `debug/` (artefatos de debug Selenium: `gal_login_fail.png`, `gal_login_fail.html`);
- `sql/` (DDL PostgreSQL orphaned; Postgres nao e usado, AGENTS.md §7; `sql/requirements.txt` com dependencias orphaned);
- `Main.spec` (artefato de build PyInstaller; `.gitignore` cobre `*.spec`);
- `images/` (sem referencias encontradas em Python, JSON, TOML, INI ou Markdown; excluido por padrao salvo evidencia futura de uso).

### 6.2 `release/config_template/`

- Incluir `config.json` apenas como template/local runtime versionado.
- Incluir contratos canonicos em `config/contracts/`, especialmente `config/contracts/equipment/*.json`.
- Nao inserir caminhos reais, credenciais, usuarios, senhas, tokens, dados laboratoriais ou valores de ambiente produtivo.
- Producao exige execucao/validacao da Instalacao Inicial para preencher `shared_storage.root`, `data_root` e `allowed_roots` no ambiente alvo.
- `CONFIG-ENC-001` permanece pendente para rodada propria de config/encoding; este manifest nao corrige `config.json`.

### 6.3 `release/docs_operacionais/`

Incluir documentacao minima para operacao e continuidade:

- `README.md` (ponto de entrada operacional; ja existe na raiz; deve ser incluido como documento nomeado);
- `docs/checklist_pos_instalacao.md` (checklist de validacao pos-instalacao; criado em 2026-05-16; aprovado para piloto; cobre identificacao, pre-condicoes, Instalacao Inicial, abertura, operacional minima, restricoes conhecidas e resultado);
- nota ou secao com restricoes INST/CONC conhecidas aplicaveis ao ambiente de destino: piloto 3-5 usuarios, backlog CONC-002, CONC-003, INST-001 e outros que afetam a implantacao.

Nao incluir todo o SDD por padrao; o SDD e documentacao de desenvolvimento, nao de operacao. Backlog tecnico, tarefas de auditoria, notas de sessao e decisoes de arquitetura nao devem entrar no pacote.

### 6.4 `release/assets/`

Incluir somente assets realmente necessarios em runtime, como imagens, icones e recursos usados pela UI. Duplicidades e assets obsoletos devem ser revisados antes da materializacao do pacote.

Achados do mapeamento de release (REL-002, 2026-05-15):

- `assets/icon.ico`: referenciado por `ui/main_window.py:256` via `os.path.join(BASE_DIR, "assets", "icon.ico")`, mas o diretorio `assets/` nao existe fisicamente no repositorio. A aplicacao trata a ausencia de forma silenciosa (janela sem icone). **REL-001 concluida documentalmente em 2026-05-17**: a ausencia de `assets/icon.ico` e aceita formalmente como ressalva nao bloqueante para o release piloto (3 a 5 usuarios), desde que o sistema abra sem erro critico no smoke-test. Nenhum arquivo de icone foi criado. A providencia de um icone oficial permanece como melhoria futura antes de versao final/distribuicao ampla.
- `images/` (pasta raiz com `INTEGRAGAL.jpg`, `logolacen.jpg`, `grace_hopper.jpg`): sem referencias encontradas em Python, JSON, TOML, INI ou Markdown. Excluido por padrao do pacote de release. Confirmar antes da materializacao se ha referencia em fluxo nao inspecionado.

### 6.5 `release/scripts_autorizados/`

Nenhum script de limpeza deve entrar no release ate auditoria propria H4. Scripts administrativos so podem ser incluidos se forem explicitamente revisados, autorizados e documentados em rodada futura.

### 6.6 `release/runtime_empty/`

Estrutura vazia sugerida para o ambiente alvo, sem dados reais:

```text
runtime_empty/
  logs/
  reports/
  relatorios/
  data/
    state/
```

Esses diretorios sao placeholders de runtime. O pacote nao deve carregar historico, logs, relatorios reais, snapshots ou dumps de execucao.

`data/state/` e criado automaticamente em runtime por `utils/persistence.py` (`STATE_DIR = Path("data/state")`, `STATE_DIR.mkdir(parents=True, exist_ok=True)`). O diretorio deve existir como placeholder vazio no pacote; o arquivo `data/state/window_state.json` e gerado pelo sistema em uso e nao deve ser copiado para o release (identificado em REL-002, 2026-05-15).

### 6.7 Criterios de aceite do pacote de release

- Nao contem `banco/*`.
- Nao contem `.env.txt`, `.env`, `.env.*` ou segredos.
- Nao contem `logs/`, `reports/` ou `relatorios/` com dados.
- Nao contem `.tmp/`, `pytest_tmp/`, `.pytest_cache/`, `__pycache__/`, `.mypy_cache/` ou caches similares.
- Nao contem `snapshots/encoding_backup_*`.
- Nao contem `relatorio_final_corrida_*.json`.
- `config.json` permanece template/local runtime, sem caminhos reais e sem segredos.
- Instalacao Inicial deve configurar `shared_storage.root`, `data_root` e `allowed_roots` no ambiente alvo.
- Pacote deve ser validado em copia limpa antes de uso operacional conforme procedimento formal definido em `docs/procedimento_smoke_test_release.md` (REL-003 concluida em 2026-05-17); procedimento aprovado como formal, mas nao executado ate a materializacao de `release/`.
- Scripts de limpeza ficam fora do pacote ate auditoria propria.
- `release/app/models.py` esta presente (RUNTIME OBRIGATORIO; importado por `application/analysis_orchestrator.py`, `services/analysis_service.py`, `services/service_container.py` e `ui/main_window.py`).
- `release/runtime_empty/data/state/` existe como diretorio vazio (placeholder para estado de runtime criado automaticamente por `utils/persistence.py`).
- `release/runtime_empty/data/state/window_state.json` nao esta presente no pacote (arquivo gerado em uso, nao asset estatico).
- `release/app/` nao contem `analise/`, `extracao/`, `interface/`, `core/`, `debug/`, `sql/`, `Main.spec` ou `images/` (legados, fachadas de teste, artefatos de debug/build; confirmados sem imports de producao em REL-002).
- Ausencia de `assets/icon.ico` nao bloqueia o pacote piloto: REL-001 concluida documentalmente em 2026-05-17 com aceitacao formal da ausencia como ressalva nao bloqueante; o smoke-test deve confirmar que a aplicacao abre sem erro critico mesmo sem o icone; providencia de icone oficial e melhoria futura antes de versao final/distribuicao ampla.

## 7. Fora do pacote de release

- `.env.txt`, `.env*` locais e qualquer segredo.
- `banco/*`, salvo decisao futura especifica; status atual: nao distribuir.
- `logs/`, `reports/`, `relatorios/`, `.tmp/`, `.pytest_cache/`, `__pycache__/`, `.venv/`.
- `snapshots/encoding_backup_*` conforme DEC-004: artefatos historicos de backup/encoding; nao entram no release operacional.
- `relatorio_final_corrida_*.json` da raiz, conforme DEC-005: artefatos runtime/transitorios; nao entram no release operacional.
- Scripts de limpeza ate auditoria H4.
- Testes completos e fixtures, salvo pacote tecnico opcional aprovado.

## 8. Gate multiusuario/instalacao

- Auditoria READ-ONLY de 2026-05-15 classificou multiusuario como APTO COM RESTRICOES e Instalacao Inicial como FUNCIONAL COM RESTRICOES.
- Implantacao inicial aprovada apenas como piloto controlado com 3 a 5 usuarios.
- Nao declarar aptidao plena para 10 usuarios antes de CONC-002, CONC-003, INST-001 e demais correcoes prioritarias.
- HIG nao executa instalacao/configuracao e nao corrige `config.json`.

## 9. Criterio de pronto para iniciar execucao HIG

- Baseline confirmado e restauravel.
- DHPs aplicaveis resolvidas ou explicitamente mantidas fora do escopo.
- Plano de `.gitignore` aprovado.
- Manifest de release aprovado por HIG-008.
- Lista de exclusao de dados sensiveis aprovada.
- Scripts destrutivos bloqueados ou auditados com dry-run/WhatIf.
