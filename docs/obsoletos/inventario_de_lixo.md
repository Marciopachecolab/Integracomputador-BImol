# Inventario de Lixo ROT

Data: 2026-05-10  
Nota operacional (microfase 3.1 - 2026-05-13): ver bloco abaixo.

## Nota operacional (microfase 3.1 - 2026-05-13)

As categorias deste arquivo (`Apagar`, `Manter`, `Desconsiderar`, `Alterar`) sao **classificacoes documentais/historicas** pre-existentes a auditoria SDD de 2026-05-12. Elas NAO autorizam acao automatica por agentes de IA.

**Nenhum item pode ser apagado, movido ou alterado sem decisao humana explicita na rodada atual.** Para qualquer remocao real, consultar:

- `AGENTS.md §9` (regras de seguranca) e `§18` (politica de governanca dos documentos);
- `docs/specs/tasks.md §10` (tarefas T-AUD bloqueadas por DHP);
- `requirements.md §10` (DEC-001..DEC-008).

O catalogo operacional ativo desta rodada e a secao "Candidatos pendentes de decisao humana (auditoria SDD 2026-05-12)" abaixo, onde cada item tem status formal `Pendente de decisao humana` e tarefa T-AUD associada.

## Classificacao

### Apagar
- `relatorio_de_limpeza.md` - relatorio historico da limpeza anterior, redundante com o novo handoff.
- `relatorios/relatorio_final_sdd_t01_t18.md` - relatorio final historico ja consolidado em `docs/specs/tasks.md` e nas notas de passagem.

### Manter
- `AGENTS.md` e `CLAUDE.md` - bussola operacional canonica, devem permanecer identicos.
- `docs/specs/requirements.md` - requisitos SDD oficiais.
- `docs/specs/design.md` - design SDD oficial.
- `docs/specs/tasks.md` - fila SDD oficial.
- `tests/fixtures/README.md` - contrato local das fixtures de teste, ainda util para manutencao.
- `notas_de_passagem.md` - handoff vivo da retomada atual.

### Desconsiderar
- `.agents/skills/*/SKILL.md` - instrucoes locais de ferramentas/agentes, nao sao documentacao funcional do projeto.

### Alterar
- `docs/specs/design.md` - atualizado para registrar o contrato do guard de escopo com stubs sem `active_exams`.
- `docs/specs/tasks.md` - atualizado com T19, a retomada pos-interrupcao.

## Candidatos pendentes de decisao humana (auditoria SDD 2026-05-12)

Itens identificados na auditoria READ-ONLY (Fase 1) com candidatos a limpeza/realocacao. Nenhum arquivo foi removido. Decisoes pendem de DHP correspondente em `docs/specs/tasks.md §10`.

| Caminho | Motivo | Evidencia | Risco | Acao recomendada | Status |
|---|---|---|---|---|---|
| `snapshots/encoding_backup_*/` | Artefatos historicos de backup/encoding conforme DEC-004, criados para rastreabilidade e eventual recuperacao durante correcoes de encoding. | Glob lista ~14 diretorios `encoding_backup_<timestamp>Z/` entre 2026-05-03 e 2026-05-12; conteudo nao foi aberto nesta decisao documental. | Inflar tamanho do repositorio; confundir leitura de baselines reais; risco de entrar no release operacional por engano. | Nao incluir no release. Tratar em rodada propria por retencao, arquivamento externo ou exclusao controlada, sempre apos baseline/backup. **Nao remover automaticamente.** | **DHP-04/DEC-004 resolvida. HIG-006 pendente/desbloqueada.** Tarefa associada: T-AUD-005 (HR/HIG). Achado de origem: D-05. |
| `relatorio_final_corrida_last.json` | Artefato runtime/transitorio de execucao conforme DEC-005. | Presente na raiz; ~2.160 bytes; conteudo nao foi aberto. | Poluicao do diretorio raiz; risco de entrar no release operacional por engano. | Nao incluir no release. Nao remover automaticamente. | **DHP-05/DEC-005 resolvida. HIG-007 concluida documentalmente (Opcao A, 2026-05-15): `.gitignore` ja cobre; sem remocao/movimentacao fisica.** |
| `relatorio_final_corrida_vr1.json` | Artefato runtime/transitorio de execucao conforme DEC-005. | Presente na raiz; ~2.160 bytes; conteudo nao foi aberto. | Poluicao do diretorio raiz; risco de entrar no release operacional por engano. | Nao incluir no release. Nao remover automaticamente. | **DHP-05/DEC-005 resolvida. HIG-007 concluida documentalmente (Opcao A, 2026-05-15): `.gitignore` ja cobre; sem remocao/movimentacao fisica.** |
| `.tmp/pytest_tmp/` | Diretorio temporario de testes identificado como candidato para higiene. | Identificado por caminho/nome; conteudo nao foi aberto. Auditoria HIG READ-ONLY 2026-05-15 confirmou volume alto por metadados. | Pode acumular artefatos temporarios, duplicatas ou dados de teste. | Excluir do pacote de release; limpar apenas em rodada propria apos baseline e autorizacao. | **HIG-001 concluida como auditoria READ-ONLY.** Sem remocao automatica. |
| `.env.txt` | Arquivo com nome compativel com ambiente/configuracao local; candidato a revisao de seguranca/higiene sem leitura de conteudo. | Identificado por caminho/nome; conteudo nao foi aberto. Auditoria HIG READ-ONLY 2026-05-15 confirmou classificacao como possivel sensivel. | Possivel conter configuracao local ou segredo; nao expor em chat. | Nao distribuir; revisar politica de ignore/segredos em rodada propria. | **HIG-001 concluida como auditoria READ-ONLY.** Sem remocao automatica. |
| `reports/` | Diretorio de relatorios com grande volume, candidato a politica de retencao. | Auditoria HIG READ-ONLY 2026-05-15 identificou 1789 arquivos por metadados; conteudo nao foi aberto. | Crescimento de repositorio, ambiguidade entre artefato persistente e temporario, possivel dado operacional. | Excluir do release; classificar retencao, mascaramento e padroes de `.gitignore` antes de qualquer acao. | **HIG-002 concluida como auditoria READ-ONLY.** Retencao pendente. |
| `logs/` | Diretorio de logs, candidato a politica de retencao e seguranca. | Auditoria HIG READ-ONLY 2026-05-15 identificou `sistema.log` volumoso e CSVs por metadados; conteudo nao foi aberto. | Logs podem conter dados operacionais, caminhos locais ou mensagens sensiveis. | Excluir do release; definir politica de retencao/rotacao em rodada futura. | **HIG-002 concluida como auditoria READ-ONLY.** Retencao pendente. |
| `test_history.csv` | Historico de testes na raiz, candidato a classificacao de artefato gerado vs evidencia persistente. | Identificado por caminho/nome; conteudo nao foi aberto. Auditoria HIG READ-ONLY 2026-05-15 classificou como artefato gerado/nao distribuir. | Poluicao de raiz ou exposicao de historico local; risco depende de conteudo e finalidade. | Excluir do release; decidir retencao em rodada futura. | **HIG-002 concluida como auditoria READ-ONLY.** Sem remocao automatica. |
| `scripts/limpeza_logs_reports.ps1` | Script de limpeza existente que pode afetar logs/reports. | Auditoria HIG READ-ONLY 2026-05-15 identificou comandos destrutivos; conteudo nao executado. | Execucao prematura pode apagar ou mover artefatos antes de DHP/politica de retencao. | Nao executar sem auditoria propria, baseline/backup e autorizacao explicita. | **HIG-003 concluida como classificacao.** Sem execucao automatica. |
| `scripts/limpeza_prioridade_alta.ps1` | Script de limpeza existente com nome de acao prioritaria. | Auditoria HIG READ-ONLY 2026-05-15 identificou comandos destrutivos; conteudo nao executado. | Execucao prematura pode alterar estado da pasta antes de baseline/backup e DHPs. | Nao executar sem auditoria propria, baseline/backup e autorizacao explicita. | **HIG-003 concluida como classificacao.** Sem execucao automatica. |

Notas:

- Esta secao registra candidatos, nao executa exclusao.
- `banco/*` legados (equipamentos.csv, equipamentos_metadata.csv, profiles/equipment_profiles.json) sao tratados em decisao separada (DHP-02 / DHP-09, achado D-11, tarefa T-AUD-011) e nao constam aqui porque seguem sob deprecacao controlada conforme `docs/specs/equipment_legacy_deprecation.md`.
- `config.json` tinha anomalias formais (LIM-002 / D-08), mas e arquivo operacional e nao candidato a limpeza; T-AUD-008-CFG foi concluida em rodada propria sem inserir dados reais sensiveis.
- `config.json` ainda tem lacuna residual de encoding em campo nao funcional (`CONFIG-ENC-001`, `_comentario`), a tratar em rodada especifica de configuracao/encoding; este inventario nao autoriza edicao do arquivo.
- Baseline/backup rastreavel foi registrado por informacao do usuario (`RELEASE-001`): `integragal_baseline_pre_higienizacao_2026-05-15.zip`. Antes de qualquer limpeza/deploy, validar disponibilidade do baseline e autorizacao humana.

## Atualizacao pos-auditoria HIG READ-ONLY (2026-05-15)

A Auditoria READ-ONLY de Higienizacao para Implantacao classificou a pasta como **ATENCAO** e confirmou que ela nao esta pronta para empacotamento direto. Nenhum arquivo foi removido, movido, aberto quando sensivel, limpo ou alterado.

Baseline informado pelo usuario para RELEASE-001: `integragal_baseline_pre_higienizacao_2026-05-15.zip`. Este registro nao autoriza limpeza automatica.

Plano formal HIG: `docs/specs/higienizacao_implantacao.md` define fases H0..H7, criterios de aceite, regras de seguranca e estrutura proposta de release. Este inventario continua sendo catalogo de candidatos; nao autoriza remocao, movimentacao, execucao de scripts ou alteracao de `.gitignore`.

HIG-004 concluida em 2026-05-15: `.gitignore` foi atualizado para impedir rastreamento futuro dos artefatos catalogados como runtime/temporarios/sensiveis. Esta atualizacao nao remove, move ou altera arquivos existentes. HIG-006 concluida documentalmente (Opcao A, 2026-05-15). HIG-007 concluida documentalmente (Opcao A, 2026-05-15).

HIG-008 concluida em 2026-05-15 como manifest documental de release: `docs/specs/higienizacao_implantacao.md` define a estrutura alvo `release/` e os itens fora do pacote. Nenhuma pasta `release/` foi criada, nenhum arquivo foi copiado, movido, removido ou empacotado; este inventario continua sendo catalogo de candidatos e nao autoriza limpeza.

| Caminho | Motivo | Evidencia | Risco | Acao recomendada | Status |
|---|---|---|---|---|---|
| `.tmp/pytest_tmp/` | Artefatos temporarios de testes. | Auditoria HIG contou volume alto em `.tmp` por metadados/nome. | Inflar pasta e confundir release. | Excluir do pacote; limpar apenas em rodada HIG apos baseline. | **HIG-001 concluida como auditoria READ-ONLY; limpeza nao executada.** |
| `.env.txt` | Possivel configuracao local/segredo. | Arquivo identificado por nome/metadados; conteudo nao lido. | Exposicao de segredo/config local. | Nao distribuir; manter protegido por ignore/politica futura. | **HIG-001 concluida como auditoria READ-ONLY; nao aberto.** |
| `reports/` | Relatorios e saidas geradas volumosas. | 1789 arquivos identificados por metadados. | Dados operacionais, volume, pacote indevido. | Excluir do release; definir retencao. | **HIG-002 concluida como auditoria READ-ONLY; retencao pendente.** |
| `relatorios/` | XLSX/PDF gerados. | 23 arquivos identificados por metadados. | Possivel dado laboratorial e poluicao de release. | Excluir do release; classificar retencao. | **HIG-002 concluida como auditoria READ-ONLY; retencao pendente.** |
| `logs/` | Logs e CSVs operacionais. | `sistema.log` volumoso e multiplos CSVs por metadados. | Dados operacionais/sensiveis. | Excluir do release; definir rotacao/retencao. | **HIG-002 concluida como auditoria READ-ONLY; retencao pendente.** |
| `scripts/limpeza_logs_reports.ps1` | Script de limpeza de logs/reports. | Auditoria identificou comandos destrutivos como `Remove-Item`. | Remocao prematura de evidencias/dados. | Nao executar sem auditoria propria e autorizacao. | **HIG-003 concluida como classificacao; execucao proibida nesta fase.** |
| `scripts/limpeza_prioridade_alta.ps1` | Script de limpeza ampla. | Auditoria identificou comandos destrutivos como `Remove-Item -Force`. | Alteracao destrutiva antes de DHP/baseline. | Nao executar sem auditoria propria e autorizacao. | **HIG-003 concluida como classificacao; execucao proibida nesta fase.** |
| `banco/*` | Dados locais/legados/possivelmente sensiveis. | Arquivos listados por metadados; conteudo sensivel nao aberto. | Exposicao/corrupcao se distribuido ou limpo. | Nao distribuir; manifest HIG-008 exclui do release integralmente. | **HIG-005 concluida documentalmente (Opcao A, 2026-05-15): `banco/*` mantido fisicamente em dev/runtime como fallback operacional controlado; conteudo sensivel nao aberto nesta decisao; nenhum arquivo aberto, movido, arquivado ou excluido. Tarefas futuras nao bloqueantes: PRIV-001, GIG-001, HIG-009.** |
| `snapshots/encoding_backup_*` | Artefatos historicos de backup/encoding conforme DEC-004. | 16 diretorios identificados por metadados; todos vazios (0 KB); conteudo nao aberto. | Inflar pasta, confundir baselines, entrar no release por engano. | Nao incluir no release; diretorios permanecem fisicamente em `snapshots/` sem rastreamento Git; nenhuma exclusao automatica. | **DHP-04/DEC-004 resolvida. HIG-006 concluida documentalmente (Opcao A, 2026-05-15): 16 diretorios vazios (0 KB); `.gitignore` ja cobre (linha 936); manifest HIG-008 exclui do release; sem remocao/movimentacao fisica.** |
| `relatorio_final_corrida_*.json` | Artefatos runtime/transitorios de execucao conforme DEC-005. | Dois arquivos na raiz (~2.160 bytes cada); conteudo nao aberto; nenhum em reports/relatorios/logs. | Dados gerados e poluicao de release. | Nao incluir no release; `.gitignore` ja cobre; sem exclusao automatica. | **DHP-05/DEC-005 resolvida; HIG-007 concluida documentalmente (Opcao A, 2026-05-15).** |

## Decisao DHP-05 / DEC-005 (2026-05-15)

- `relatorio_final_corrida_*.json` localizado na raiz e artefato runtime/transitorio de execucao.
- Nao deve entrar no pacote de release operacional.
- Tratamento futuro permitido apenas em rodada propria: politica de retencao, realocacao ou regra de `.gitignore`.
- Nenhuma exclusao automatica esta autorizada.

## Classificacao de itens ambiguos — mapeamento de release (REL-001/REL-002, 2026-05-15)

Resultado do mapeamento READ-ONLY de imports e classificacao dos itens nao cobertos pelo manifest HIG-008 original. Nenhum arquivo foi removido, movido, alterado ou empacotado.

| Caminho | Classificacao | Evidencia | Recomendacao |
|---|---|---|---|
| `models.py` | RUNTIME OBRIGATORIO | Importado por `application/analysis_orchestrator.py`, `services/analysis_service.py`, `services/service_container.py`, `ui/main_window.py` | Adicionado a `release/app/` — lacuna critica corrigida em HIG-008 §6.1 |
| `analise/` | Legado | Motor real e `services/engine/analysis_engine.py`; campo `modulo_analise` em CSV e metadado string sem dynamic import; testes importam `analise/`, producao nao | Excluir de `release/app/`; manter em dev |
| `extracao/` | Legado | Use case real e `application/extraction_plate_mapping_use_case.py`; sem imports de producao encontrados | Excluir de `release/app/`; manter em dev |
| `interface/` | Fachada de compatibilidade para testes | Re-exports puros de `ui.modules.*`; nenhum import de producao | Excluir de `release/app/`; testes nao entram no release |
| `core/` | Legado em deprecacao controlada (DEC-003) | `core/authentication/user_manager.py` neutralizado (T-AUD-004A/004B); nenhum import de producao | Excluir de `release/app/`; manter em dev por DEC-003 |
| `data/state/` | Estado runtime gerado | `utils/persistence.py:29` cria `STATE_DIR = Path("data/state")` automaticamente via `mkdir(parents=True, exist_ok=True)` | Adicionar `data/state/` como diretorio vazio em `release/runtime_empty/`; nao copiar `window_state.json` |
| `debug/` | Artefatos de debug Selenium | `gal_login_fail.png` e `gal_login_fail.html`; sem imports Python | Excluir de `release/app/` |
| `sql/` | DDL PostgreSQL orphaned | `criar_historico_processos.sql` usa `SERIAL` (PostgreSQL); Postgres nao e usado (AGENTS.md §7); `sql/requirements.txt` contem `psycopg2-binary` e dependencias orphaned | Excluir de `release/app/` |
| `images/` | Excluido por padrao | Sem referencias em Python, JSON, TOML, INI ou Markdown encontradas | Excluir de `release/app/`; verificar antes de confirmar exclusao definitiva |
| `config/backups/` | Inexistente fisicamente | Glob retornou vazio; diretorio nao existe | Remover da lista de ambiguos |
| `Main.spec` | Artefato de build PyInstaller | `.gitignore` cobre `*.spec`; sem uso em runtime | Excluir de `release/app/` |
| `docs/ subset operacional` | Indefinido (resolvido) | Manifest §6.3 nao listava arquivos concretos | Corrigido em HIG-008 §6.3: `README.md` + checklist + nota de restricoes INST/CONC |

Notas:
- Classificacoes acima sao resultado de analise READ-ONLY; nenhum arquivo foi removido ou alterado.
- `assets/icon.ico`: referenciado por `ui/main_window.py:256`, mas o diretorio `assets/` nao existe fisicamente; tratar antes de materializar o release.
- Tarefas REL-001, REL-002 e REL-003 registradas em `tasks.md`; manifest atualizado em `docs/specs/higienizacao_implantacao.md`.

## Decisao DHP-04 / DEC-004 (2026-05-15)

Os diretorios `snapshots/encoding_backup_*` sao artefatos historicos de backup/encoding, criados para rastreabilidade e eventual recuperacao durante correcoes de encoding.

Decisao: nao entram no pacote de release operacional. Devem ser tratados por politica de retencao, arquivamento externo ou exclusao controlada em rodada propria, sempre apos baseline/backup.

Restricao: nenhuma exclusao automatica, movimentacao ou alteracao de `.gitignore` esta autorizada por esta decisao. HIG-006 permanece pendente/desbloqueada para rodada futura.
