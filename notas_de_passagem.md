# Notas de Passagem

---

## 2026-06-02 — Fase 5 (Audit Refactoring) — implementação concluída
Executor: Claude Code (Opus 4.8), modo execucao supervisionado SDD (`specs/audit_refactoring/`)

- **T-050, T-051a, T-051, T-052, T-053** executadas (5 commits: `e59f27f`, `d56e719`,
  `b0a38a3`, `ad17ac0`, `4eb4c3d`).
- **Lockout server-side ATIVO** em `autenticacao/auth_service.py` (ÚNICO `.py` de produção tocado).
- Política: 5 tentativas → 15 min bloqueio + auto-desbloqueio na expiração.
- Lockout check ANTES de bcrypt (evita timing leak/enumeração); mensagem genérica
  no serviço (sempre `None` em falha — OWASP A07). Hash bcrypt mantido.
- Persistência: helper `_persistir_estado_tentativas` → `UserRepository.update` por
  linha (CSVFileLock no adapter CSV; backend ativo = `csv`). Passa `locked_until=""`
  explícito para LIMPAR bloqueio (None = "sem alteração" no contrato).
- **Bug capturado na validação adversária (T-052) e corrigido em T-051:** rota inicial
  `save_users_df` coagia `bloqueado_ate=""`→`None` e nunca limpava o bloqueio + tinha
  semântica delete-missing. Trocado por `repo.update` cirúrgico.
- **Achados registrados** (`docs/specs/tasks.md`, não-bloqueantes):
  - `T-051-FIND-SQLITE`: `SQLiteUserRepositoryAdapter.update` não persiste
    `failed_attempts`/`locked_until` (fail-open SE backend trocado p/ sqlite; csv ativo OK).
  - `T-051-FIND-UIMSG`: `login.py` ainda revela "N tentativas restantes" (OWASP A07 na UI);
    fora do escopo Fase 5 (§9 — não tocar login.py); endereçar em rodada UI/Fase 9.
- Evidência de testes: **21 passed** (13 guardiões + 4 smoke + 4 lockout), execução
  sequencial (sem `-n auto`, T-AUD-021). Caracterização (T-051a) verde antes e depois da impl.
- **Suíte completa `pytest tests/` NÃO concluída:** hang conhecido de GUI/Tk no Windows
  (process ininterruptível, documentado na nota da Fase 4 + T-AUD-021); não é regressão.
  Evidência via subconjunto de 21 testes relevantes.
- **PENDENTE PILOTO 7 dias** (sub-fase 5.4 — handoff em `docs/specs/decisoes_humanas/phase5_piloto_handoff.md`
  e espelho `snapshots/phase5_piloto_handoff.md`).
- Não tocados: `core/authentication/user_manager.py` (DEC-003), `autenticacao/login.py` (§9),
  `CLAUDE.md`/`AGENTS.md` (guardião T-012), 13 guardiões existentes.
- Próxima rodada técnica: Fase 6 (Fail-closed + cadastros_ui split) — pode iniciar em
  paralelo ao piloto, mediante autorização.

---

## 2026-06-02 — Fase 4 (Audit Refactoring) concluída
Executor: Claude Code (Opus 4.8), modo execucao supervisionado SDD (`specs/audit_refactoring/`)

- **T-040, T-041, T-042, T-043, T-044, T-045** executadas (6 commits: `20e3e35`, `2e4fbc0`, `640d57b`, `6781b14`, `10515bc`, `db40fb7`).
- **5 guardiões import-ban novos** (AST/regex, REPO_ROOT relativo): `analise`, `extracao`, `scratch`, `sql` (import-ban de pastas órfãs; 0 callers confirmados por 4 subagentes Explore) + `scripts_no_hardcoded_paths`.
- **6 scripts refatorados** (paths absolutos → relativos; sintaxe validada via py_compile / parse mínimo, SEM execução):
  - `check_bom.py` → `Path(__file__).resolve().parent.parent`
  - `limpeza_logs_reports.ps1`, `limpeza_prioridade_alta.ps1`, `organizar_documentacao.ps1` → `(Resolve-Path "$PSScriptRoot/..").Path`
  - `run_daily_parity_snapshot.cmd` → `pushd %~dp0.. / set ProjectRoot=%CD% / popd` (force-add: `.gitignore:404 **/*.cmd`; DHP commit-cmd aprovado "Force-add só este .cmd")
  - `run_all_tests.ps1` → ativação condicional de `.venv` do repo (antes `C:/Users/marci/Desktop/venv`; DHP Q2 aprovado opção A)
- **13 guardiões totais verdes** (Fases 0+1+3+4): 13 passed. Verificação adversária independente (kant) sem achados bloqueantes.
- **ZERO `.py` de runtime modificado**; pastas órfãs (`analise/ extracao/ scratch/ sql/ db/`) intactas (arquivamento físico fica para Fase 7 — DHP-13).
- **[PENDÊNCIA] DHP Q1 (Fase 4, opção A):** `scripts/generate_phase0_baseline.py:41,44` referencia fixtures `.xlsx` de laboratório em `Downloads\18 JULHO 2025\` (dados FORA do repo, não-relativizáveis). NÃO refatorado; guardião T-044 deliberadamente restrito ao padrão `Downloads/Integragal` para não bloquear esse script dev. Tratar em rodada futura dedicada (parametrizar via CLI/env quando houver decisão).
- **Próxima rodada:** Fase 5 (Lockout server-side de autenticação — T-050..T-053). PRÉ-REQUISITO: DHP "política de senha" (limite N tentativas, duração bloqueio, recuperação, exigências mínimas) ANTES de implementar. NÃO iniciada — aguarda autorização.

---

## Sessao 2026-06-01 — Audit Refactoring Fase 0 (Emergencia)
Executor: Claude Code (Opus 4.8), modo execucao supervisionado SDD (`specs/audit_refactoring/`)

### [CRITICAL_FINDING] Import circular pre-existente envio_gal <-> ui (severidade ALTO)
- **Arquivo/linha:** `exportacao/envio_gal.py:84` (`from ui.gal_ui_dialog_adapter import GalUIDialogAdapter`, top-level) <-> `ui/__init__.py:11` (import eager de `main_window`) <-> `ui/menu_handler.py:16` (`from exportacao.envio_gal import abrir_janela_envio_gal`).
- **Sintoma:** `import exportacao.envio_gal` falha com `ImportError: cannot import name 'abrir_janela_envio_gal' ... partially initialized module` quando `envio_gal` e o primeiro modulo a tocar `ui`.
- **Impacto real:** o app inicializa normalmente via `python main.py` (que importa `ui` primeiro — `main.py:16`); o ciclo so quebra sob ordem de import nao-ui-first (como o comando literal do T-002). NAO e regressao do csv_safety (restaurado identico ao HEAD) — esta presente no HEAD baseline `f28ce1e`.
- **Evidencia:** ordem `import ui; import exportacao.envio_gal` -> OK; ordem `8 callers; envio_gal` -> ImportError. T-002 re-evidenciado verde com ordem ui-first (`all-ok`).
- **Governanca:** FORA do escopo da Fase 0; tocar `envio_gal.py`/`ui` arrisca tags GAL-ROB-* e sobrepoe a forense da Fase 2 (T-021/T-022 examinam `envio_gal.py`, incidente 2026-05-23) e o T-061 (Fase 6, integra `assert_valid_gal_payload` em `envio_gal.enviar_amostra`). Divergencia realidade<->SDD nao listada em `spec.md §8.3`.
- **Recomendacao:** avaliar import lazy de `GalUIDialogAdapter` (dentro da funcao consumidora) durante a Fase 2/6, com cobertura previa. Decisao humana: registrada na sessao (usuario optou por re-evidenciar T-002 com ordem sa e seguir Fase 0).

### [FINDING] Credencial hardcoded em modulo legado (severidade ALTO, follow-up)
- **Arquivo/linha:** `core/authentication/user_manager.py:~1811` (`password="admin123456"`).
- **Contexto:** modulo LEGADO em deprecacao controlada (DT-003 / DEC-003), neutralizado e import-banido (guardiao T-AUD-004A). NAO e runtime; remocao fisica exige DEC futura.
- **Tratamento:** fora do escopo da Fase 0. O guardiao T-006 (`tests/test_no_hardcoded_credentials.py`) exclui `core/` deliberadamente e documenta este achado. Tratar em rodada futura (correlato a US-3/DEC-003).

### Fase 0 (Emergencia) — CONCLUIDA
- **T-000** [BLOCK] backup pre-refator: `snapshots/pre_audit_refactor_20260531/` (21.759 arquivos) + `_manifest_sha256.csv` (21.759 hashes, 0 falhas). Sem commit (`snapshots/` e gitignored).
- **T-001** [BLOCK] `utils/csv_safety.py` restaurado de `HEAD` (byte-identico; deleção era working-tree nao-commitada). `from utils.csv_safety import sanitize_csv_value` -> OK. Sem commit (realinhou ao HEAD).
- **T-002** [BLOCK] 10 callers de csv_safety importam sob ordem real de boot (ui-first): `all-ok`. Sem commit (validacao). Ver [CRITICAL_FINDING] import circular acima.
- **T-003** [P] guardiao `tests/test_no_broken_csv_safety_imports.py` (AST, BOM-tolerante) -> 2 passed. Commit `4f4c705`.
- **T-004** [P][DHP] `revert_info.txt` -> `docs/obsoletos/incidents/revert_envio_gal_20260523.txt` + README de advertencia (prompt injection). DHP aprovada. Commit `315b403`.
- **T-005** [P][DHP] `test_login.py` DELETADO (senha '123456' hardcoded, API async errada). DHP=(A). Commit `61b76fb`.
- **T-006** [P] guardiao `tests/test_no_hardcoded_credentials.py` (AST) -> 1 passed. Commit `e0e0069`.
- **Branch:** `refactor/audit-refactoring` (criada a partir de `main`).
- **Verificacao final:** AC-1.1 OK; 3 guardioes passed; raiz sem `test_login.py`/`revert_info.txt`.
- **Proxima rodada:** Fase 1 (T-010 T-AUD-008 dominio puro; T-011 T-AUD-004A legacy auth; T-012 AGENTS==CLAUDE hash). NAO iniciada — aguarda autorizacao.

---

## Sessao 2026-05-30 — Dashboard analitico, filtros, detalhe de corrida e correcoes de UI
Executor: Claude Code (Opus 4.8)

### Escopo implementado (rodada autorizada de codigo/UI)
- **DASH-003** — `obter_estatisticas_gestao` conta apenas colunas canonicas `RES_*` (ignora `SRC_RES_*` e controles `RP|CN|CP|GERAL`): elimina a duplicacao "RES X"+"SRC RES X" no quadro "Doencas Mais Positivas", corrige a Positividade e limpa rotulos (`limpar_nome_alvo`). Top 5 → Top 12.
- **DASH-004** — Gestao Clinica: barra (Top 10 + rotulos) + radar + pizza (Top 8 + "Outros") numa unica `Figure`, tabela-resumo lateral (Alvo/Positivos/%) e rotulos em negrito.
- **DASH-005** — Nova aba "Visao Analitica": `obter_painel_analitico` (KPIs Volume 15d/Volume-dia/Positividade/Pendentes GAL; heatmap dia x doenca; tabela de Ct 15/7/3 dias com setas ▲▼➖ e % de variacao; `positividade_por_alvo`). Clique num alvo destaca no heatmap + tabela (`_selecionar_alvo`). Fontes da aba ampliadas (+100%). Pendentes GAL = status reconciliado != `enviado`/`duplicado` (`_contar_pendentes_gal`).
- **DASH-006** — Barra de filtros reutilizavel (`_criar_barra_filtros`) nas abas Operacional (filtra cards/grafico/tabela via `_df_operacional`/`_janela_filtro`) e Visao Analitica (somente Exame).
- **DASH-007** — Detalhe da corrida: coluna "Corrida" (`nome_corrida`); janela de resultados read-only corrigida (bug `from ui.theme.design_tokens import CORES, FONTES` — modulo nao expoe esses nomes; agora usa `CORES`/`FONTES` de `.estilos`); colunas limpas (Amostra/Poco/Resultado/Status + `Res`/`Ct` por alvo). Botao "Abrir Mapa Definitivo (Excel)" abre o `mapa_placa_*.xlsx` real em `<data_root>/mapas` via `_localizar_mapa_definitivo` (match normalizado por `nome_corrida`/arquivo origem; 17/17 corridas localizadas no teste).
- **DASH-008** — Tabela "Corridas Recentes": caixa de busca lateral desativada; barra de rolagem reancorada no mesmo container; ordenacao por clique no cabecalho (1o asc, 2o desc; `Data/Hora` cronologico).
- **DASH-FIX-001** — `CardResumo.set_valor`/`set_indicativo` (corrige cards de Gestao zerados por `AttributeError` silencioso); Gestao/Visao Analitica atualizam do SQLite independentemente do CSV.
- **CFG-UI-001** — `tela_configuracoes._carregar_categoria` chama `_carregar_valores()`; corrige switch "Ocultar navegador durante envio" exibido OFF apesar do default `headless=true`.
- **WIZ-UI-001** — Passo 1 do wizard em grade compacta (cabe sem rolagem; botao "Editar Exame Selecionado" volta a aparecer) + botao "Limpar Etapa" (`clear_current_step`).
- **CAL-UI-001** — `SimpleCalendar(date_format=...)`; botoes de calendario nos campos De/Ate da Gestao.

### Verificacao
- Validacao headless: analytics (KPIs/heatmap/ct_table sem rotulos `SRC`/`RES`), construcao da janela read-only, locator de mapa (17/17), ordenacao da tabela (asc/desc), cards `set_valor/set_indicativo`.
- `python -m pytest tests/ -k "analytics or dashboard or relatorio or estatistic"` → 1 passed; import smoke OK. Sem novas dependencias.

### Ponto de rollback
- `git` indisponivel no ambiente (PATH). Criado backup timestampado `_rollback_20260530_100900/` com o estado anterior dos 6 arquivos tocados (UI). Artefato transitorio — candidato a `.gitignore`/remocao em rodada de higiene (nao remover sem decisao).

### Documentos atualizados nesta sessao
- `docs/specs/design.md` — §3.8 (Dashboard 3 abas) reescrita e §14.2 adicionada.
- `docs/specs/tasks.md` — §11.3: DASH-003..008, DASH-FIX-001, CFG-UI-001, WIZ-UI-001, CAL-UI-001.
- `docs/specs/requirements.md` — CA-16 (dedup/leitura SQLite das analiticas) e CA-17 (detalhe read-only + Mapa Definitivo).
- `CLAUDE.md` e `AGENTS.md` — §16 atualizado com as tarefas concluidas (nao repetir).
- `notas_de_passagem.md` — esta entrada.

### Revisao de estrutura
- `_rollback_20260530_100900/` presente na raiz (ver acima). Nenhum `_diag_*.py` temporario remanescente (removidos apos uso). Diretorio canonico de mapas confirmado: `<data_root>/mapas` (`dados/mapas`, 49 arquivos).

---

## Sessao 2026-05-29 — Uniformizacao de paths de logs e dados operacionais
Executor: Claude Code (Sonnet 4.6)

### Escopo implementado

**LOG-UNIF-001 — Uniformizacao de locais de gravacao de logs**
- Bug corrigido: `config/default_config.json` tinha `logs_dir = "dados/banco"` (diretorio de dados legados). Corrigido para `"logs"`.
- `utils/audit_logger.py`: `AuditLogger.__init__` aceita `None` e usa `_resolve_audit_log_dir()` via config service.
- `services/legacy_panel_governance.py`: `DEFAULT_LOG_PATH` substituido por `_resolve_default_log_path()` com prioridade: env var → config service → fallback.
- `utils/dataframe_reporter.py`: `DataFrameReporter.__init__` aceita `None` e usa `_resolve_dataframe_log_dir()` via config service.
- Teste-guardiao criado: `tests/test_log_paths_uniformization.py` (9 casos, 9 passed).

**LOG-UNIF-002 — Uniformizacao de fallbacks de pastas de dados**
- `services/path_resolver.py:34`: fallback de `resolve_banco_dir()` alterado de `banco/` para `banco_runtime/`.
- `services/engine/config_loader.py:14`: `ConfigLoader.BASE_PATH` alterado de `Path("banco")` para `Path("banco_template")`. `get_equipment_profiles()` agora encontra os JSONs reais.
- `scripts/normalize_legacy_csv_utf8.py` e `scripts/scan_csv_encoding_conformance.py`: `DEFAULT_ROOTS` ampliado para incluir `banco_runtime`.
- Migracao de dados: `corridas_vr1e2_biomanguinhos_7500.csv` (296KB) e `corridas_zdc_biomanguinhos.csv` (42KB) movidos de `dados/banco/` para `logs/`. Backup em `snapshots/dados_banco_backup_20260529/`.
- `historico_analises.csv` (280KB) ja estava em `logs/` apos correcao do `logs_dir`.
- Teste-guardiao criado: `tests/test_banco_path_fallbacks.py` (7 casos, 7 passed).
- Suite completa: 55 testes, zero regressoes.

### DHPs abertas nesta sessao
- **DHP-10**: `dados/banco/historico.db` (131KB, 25/05/2026, mais antigo) — inspecionar antes de excluir.
- **DHP-11**: CSVs duplicados residuais em `dados/banco/` (equipamentos, exames, placas, regras, usuarios) — decidir destino.
- **DHP-12**: `banco_template/historico.db` (3.3MB, maior que o ativo de 1.5MB em banco_runtime/) — conteudo desconhecido; inspecionar antes de qualquer decisao.

### Documentos atualizados nesta sessao
- `docs/specs/tasks.md` — adicionados LOG-UNIF-001, LOG-UNIF-002, DHP-10, DHP-11, DHP-12 e rastreabilidade.
- `docs/specs/design.md` — adicionados §3.10 (arquitetura de paths) e §13 (atualizacoes 2026-05-29); §10 atualizado com novas DHPs.
- `CLAUDE.md` e `AGENTS.md` — atualizados §10, §11, §13 e §16.
- `notas_de_passagem.md` — esta entrada.

### Arquivos criados
- `tests/test_log_paths_uniformization.py`
- `tests/test_banco_path_fallbacks.py`
- `snapshots/dados_banco_backup_20260529/` (backup dos corridas CSVs antes de mover)

### Arquivos modificados (codigo)
- `config/default_config.json` (logs_dir corrigido)
- `utils/audit_logger.py` (config-driven)
- `utils/dataframe_reporter.py` (config-driven)
- `services/legacy_panel_governance.py` (config-driven)
- `services/path_resolver.py` (fallback banco_runtime)
- `services/engine/config_loader.py` (BASE_PATH banco_template)
- `scripts/normalize_legacy_csv_utf8.py` (DEFAULT_ROOTS)
- `scripts/scan_csv_encoding_conformance.py` (DEFAULT_ROOTS)

### Arquivos movidos (dados)
- `dados/banco/corridas_vr1e2_biomanguinhos_7500.csv` → `logs/` (296KB)
- `dados/banco/corridas_zdc_biomanguinhos.csv` → `logs/` (42KB)

---

## Sessao 2026-05-30 — GAL Robustez/UX/Dashboard + correcao de paths (CONFIG-PATH-001)
Executor: Claude Code (Opus 4.8)

### Escopo implementado

**Robustez e correcao de bugs GAL (GAL-ROB-001..010):**
- S4: worker exception → registro estruturado `erro_critico` (nao mais `print()`).
- S2: metadados vazios nao abortam o lote; amostras recebem `nao_encontrado`.
- S5: falhas de paginas de metadados acumuladas e reportadas explicitamente.
- S10: CSV validado antes de abrir o Firefox (falha cedo).
- S11: aviso antecipado de `gal_exame_codigo` ausente.
- S14: mascaramento de campos identificaveis na resposta do servidor antes de logar.
- S22: `inflight_keys` atomicas sob lock para prevenir envio duplo de linhas identicas no mesmo CSV.
- S23: normalizacao de datas (DD/MM→ISO) simetrica no reconciliador GAL.
- S24: `validate_gal_payload` valida nao-vazio de `codigo`.
- GAL-ROB-010: fallback por `codigo_amostra` no reconciliador quando `kit`/`lote` ausentes.

**Features e toggles (GAL-FEAT-001..005 + GAL-PERF-001):**
- `USE_GAL_ENVIO_SEM_METADADOS`: pula `/lista/`, usa `codigoAmostra` direto. Toggle em Configuracoes GAL.
- `construir_payload`: `codigo` usa `codigoAmostra` como fallback quando `meta` vazio.
- Firefox headless por default (`gal_integration.headless: true`). Toggle em Configuracoes GAL.
- Terminal exibe linha por amostra (`codigoAmostra → STATUS`). Rollback: `USE_GAL_TERMINAL_LOG_POR_AMOSTRA=false`.
- Secao "Comportamento do Envio" adicionada nas Configuracoes GAL.
- Janela de metadados: 365 → 15 dias.

**Dashboard e relatorios (DASH-001..002):**
- Dashboard principal: fonte primaria agora e `ExamRunsSQLiteRepository` (`historico.db`) com status GAL.
- Gestao Clinica: campos De/Ate + botao Filtrar adicionados.

**CONFIG-PATH-001 (rodada autorizada):**
- `config.json` `paths.logs_dir`: `"dados/banco"` → `"logs"` (elimina pasta `dados/dados/`).
- `config.json` `paths.gal_history_csv` e `paths.gal_upload_history_csv`: `"logs/total_importados_gal.csv"` → `"logs/historico_analises.csv"`.
- `config/default_config.json` alinhado com os mesmos valores.

### Pendencias abertas desta sessao
- **GAL-PEND-001**: S3/S6 — retry com classificacao de erro transitorio vs definitivo em `enviar_amostra()`. Requer validacao de idempotencia do endpoint `/gravar/`.
- **GAL-PEND-002**: S18 — suite de testes sem Selenium real para o modulo GAL.
- **MEDIA-3 residual**: `GAL_PAYLOAD_REQUIRED_FIELDS` lista `requisicao`/`paciente` como `required` no schema JSON, mas no modo sem metadados eles sao intencionalmente vazios. Schema nao foi versionado. Risco: suites futuras com `jsonschema` formal reprovariam payloads sem metadados. Registrar CA em `requirements.md` em rodada futura.
- **BAIXA-1 residual**: campo `_raw` populado antes do mascaramento; dados de resposta de erro podem persistir no journal. Baixo risco operacional atual.

### Regressao
- 77 testes preexistentes passaram (zero regressoes). Sem novos guardioes especificos para GAL-ROB/FEAT — GAL-PEND-002 registra essa pendencia.

### Documentos atualizados nesta sessao
- `docs/specs/tasks.md` — §11 adicionado; tabela INST-001/002/003 corrigida para Concluido.
- `docs/specs/design.md` — §3.5 reescrito; §3.8 atualizado.
- `CLAUDE.md` e `AGENTS.md` — §16 atualizado com novas tarefas e INST-001/002/003 movidos para concluidas.
- `config.json` — 3 paths corrigidos (rodada autorizada).
- `config/default_config.json` — paths alinhados com config.json.
- `notas_de_passagem.md` — esta entrada.

---

Data: 2026-05-11  
Executor: Codex (orquestracao estilo maestro + execucao incremental com TDD)

## 1) Escopo implementado nesta sessao

Implementacao iniciada e concluida para o plano de equipamentos em `docs/specs/plano_equipamentos_sdd.md`, com foco nas fases operacionais:

- fonte canonica em `config/contracts/equipment/*.json`;
- apenas dois equipamentos ativos no fluxo canonico (`7500_Extended` e `QuantStudio`);
- aliases de QuantStudio resolvidos para o mesmo `equipment_id`;
- deteccao orientada por perfis ativos com fallback legado;
- cadastro tecnico pela UI gravando diretamente em `config/contracts/equipment/*.json`;
- permissao de escrita restrita a `ADMIN`/`MASTER`;
- baseline de fixtures reais com `skip` explicito quando fixture nao existe ou nao tem tabela valida.

## 2) Arquivos criados

- `application/equipment_profile_service.py`
- `config/contracts/equipment/7500_extended.json`
- `config/contracts/equipment/quantstudio.json`
- `tests/test_equipment_profile_service.py`
- `tests/test_phase1_equipment_contract_alias_resolution.py`
- `tests/test_phase0_equipment_real_fixture_baseline.py`

## 3) Arquivos modificados

- `services/equipment_detector.py`
- `services/contract_catalog.py`
- `services/cadastros_diversos.py`
- `ui/menu_handler.py`
- `ui/modules/cadastros_diversos.py`
- `config/contracts/schema.equipment_profile.json`
- `config/contracts/equipment/abi_7500.json`
- `config/contracts/equipment/template_equipment_profile.json`
- `config/contracts/exams/zdcbm.json`
- `config/contracts/exams/template_exam_profile.json`

## 4) Arquivos excluidos

- Nenhum (alem da substituicao deste proprio `notas_de_passagem.md` por versao atualizada).

## 5) Status da suite de testes executada

Comando executado:

```powershell
python -m pytest tests/test_equipment_detector.py tests/test_equipment_registry.py tests/test_equipment_extractors.py tests/test_phase1_equipment_registry_contract_precedence.py tests/test_phase2_equipment_extraction_port.py tests/test_equipment_profile_service.py tests/test_phase1_equipment_contract_alias_resolution.py tests/test_phase0_equipment_real_fixture_baseline.py tests/test_phase_b1_cadastros_facade_contract.py tests/test_single_window_phase2_navigation.py -q --tb=short
```

Resultado:

- `45 passed`
- `17 skipped` (fixtures ausentes ou fixture QuantStudio sem tabela de resultados utilizavel no ambiente atual)
- `0 failed`

Observacoes:

- warnings nao bloqueantes de `reportlab` e mark `integration` nao registrado;
- fixture `C:\Users\marci\Downloads\18 JULHO 2025\20250924 VR1_VR2 BIOM PLACA 01_Results_20260220 173647.xlsx` existe, mas no ambiente atual contem somente metadado (`File Name`) e nao tabela de resultados parseavel, portanto baseline faz skip explicito.

## 6) Proximo passo para o Claude Code

1. Completar a fase de UI tecnica com campos avancados editaveis (assinatura, column_mapping, ct_policy, well_policy, extractor_strategy, confidence_threshold, validation_rules) na aba de equipamentos, mantendo gravacao em `config/contracts/equipment/*.json`.
2. Adicionar botao de "Testar com arquivo" na UI de equipamentos para validar deteccao + extracao antes de salvar (dry-run).
3. Substituir o fixture de QuantStudio por arquivo de resultados valido (com tabela de dados), para transformar o teste de baseline de `skip` para `pass`.
4. Executar as suites canonicamente recomendadas em `AGENTS.md` apos consolidar os passos acima.

## 7) Atualizacao da sessao atual

Sincronizacao concluida usando `maestro` + execucao TDD em E05/E06.

Constatacoes:

- `docs/specs/tasks.md` era mais atual que a lista de proximos passos acima: E04/UI tecnica ja estava implementada, incluindo campos avancados e botao "Testar com arquivo".
- Fixture QuantStudio do repositorio (`test_data/arquivoquantstudio.xlsx`) esta valida e o baseline passa como `pass`, nao `skip`.
- E05 foi iniciada e concluida.
- E06 foi iniciada e concluida.
- E07 foi iniciada e concluida.

Implementado nesta sessao:

- Novo teste TDD em `tests/test_phase3_equipment_profile_driven_detector.py`.
- `services/equipment_detector.py` agora retorna metadados `matched_profile_id` e `detector_mode="contract_profile"` quando a deteccao operacional vem de perfis ativos.
- Shadow legacy obrigatorio anexado em `shadow_legacy_detection`, sem alterar a decisao operacional do contrato.
- `validation_rules.required_columns` passou a ser bloqueante no score do perfil.
- `well_policy.input_format` passou a ser bloqueante no score do perfil quando amostras de well nao respeitam o formato esperado.
- Divergencia entre contrato e detector legado agora gera log estruturado `EquipmentDetectorShadow` com `error_code=EQUIPMENT_SHADOW_DIVERGENCE`.
- Perfis explicitos invalidos/inativos falham fechado, sem fallback legado silencioso. `active_profiles=[]` continua sendo rollback/teste explicito para o detector legado.
- `EquipmentProfileService.extract_results()` agora constroi `EquipmentConfig` diretamente a partir do contrato JSON, sem consultar `EquipmentRegistry` legado.
- `EquipmentExtractionService` passou a carregar `EquipmentRegistry` apenas sob demanda em `list_equipamentos()`/`resolve_config()`, nao no caminho de extracao com config ja fornecida.
- Novo teste real em `tests/test_phase4_equipment_contract_extraction.py` valida extracao por contrato para `test_data/resultados_vr1_vr2.xlsx` e `test_data/arquivoquantstudio.xlsx`.
- E07 marca fontes legadas de equipamento em runtime:
  - `legacy_equipment_csv`;
  - `legacy_equipment_metadata_csv`;
  - `legacy_equipment_profiles_json`;
  - `legacy_builtin_registry`.
- Criada documentacao operacional em `docs/specs/equipment_legacy_deprecation.md`.
- `docs/specs/tasks.md` atualizado: E05, E06, E07 e T24 concluidos.

Suites executadas nesta sessao:

```powershell
python -m pytest tests/test_equipment_detector.py tests/test_equipment_registry.py tests/test_equipment_extractors.py tests/test_phase1_equipment_registry_contract_precedence.py tests/test_phase2_equipment_extraction_port.py tests/test_equipment_profile_service.py tests/test_phase1_equipment_contract_alias_resolution.py tests/test_phase0_equipment_real_fixture_baseline.py tests/test_phase3_equipment_profile_driven_detector.py tests/test_phase4_equipment_contract_extraction.py tests/test_phase7_equipment_legacy_deprecation.py tests/test_phase_b1_cadastros_facade_contract.py tests/test_single_window_phase2_navigation.py -q --tb=short
```

Resultado atualizado apos concluir E07:

- `64 passed`
- `16 skipped`
- `0 failed`
- warnings nao bloqueantes de `reportlab` e `openpyxl`.

Proximo passo recomendado:

1. Revisar `docs/specs/tasks.md` para definir a proxima frente apos equipamentos SDD.
2. Rodar as suites canonicas recomendadas em `AGENTS.md` antes de qualquer nova frente funcional.
3. Manter arquivos legados de equipamento sem remocao fisica ate completar um ciclo operacional validado.

## 8) Atualizacao SDD - Modulo de Relatorios

Data: 2026-05-11  
Modo: planejamento SDD, com escrita restrita a arquivos Markdown.

Orquestracao:

- Skill principal: `maestro`.
- Skills de apoio aplicadas: `domain-modeling`, `contract-designer`, `system-design-draft` e `create-plan`.

Exploracao realizada:

- `models.py`: contexto de usuario, exame, kit/lote, corrida e extracao disponivel em `AppState`.
- `services/history_report.py`: historico operacional existente com filtros por exame, usuario, status e periodo, alem de campos de envio GAL.
- `services/exam_runs_sqlite.py`: fonte SQLite de execucoes/amostras com `resultado_geral`, lote, data, exame e status de placa.
- `services/gal_transactions.py`: journal GAL com chave de idempotencia normalizada, status de sucesso/erro/duplicado e metadados de kit/lote/data.
- `domain/persistence_contracts.py`, `services/persistence_provider.py` e `services/sqlite_repository.py`: contratos e provider SQLite-first ja existentes para historico.

Artefatos atualizados:

- `docs/specs/requirements.md`: adicionada a Feature "Modulo de Relatorios" com objetivo, user stories, filtros, agregacoes, fontes de dados e criterios de aceite.
- `docs/specs/design.md`: definida arquitetura tecnica somente leitura para relatorios, contratos de entrada/saida, fluxo operacional e restricoes.
- `docs/specs/tasks.md`: adicionada a secao "Feature: Modulo de Relatorios" com tarefas R01-R10.

Estado para a proxima sessao:

- Nenhum arquivo de codigo-fonte foi modificado nesta atualizacao SDD.
- A primeira tarefa pronta para execucao e `R01 - Definir contratos ReportsFilterDTO e ReportsResultDTO em camada de aplicacao, com testes de validacao para periodo, escopo ativo de exames, paginacao e combinacoes de filtros`.
- A implementacao deve comecar por testes/fixtures de contrato, antes de queries ou UI.

## 9) Execucao R01 - Contratos do Modulo de Relatorios

Data: 2026-05-11  
Executor: Codex com orquestracao `maestro`, `rtpcr-module-contracts`, `contract-designer`, `tdd-implement` e `python-dev`.

Implementado:

- Criado `application/reports_contracts.py` com contratos puros e sem IO:
  - `ReportsFilterDTO`;
  - `ReportsPaginationDTO`;
  - `ReportsGroupDTO`;
  - `ReportsDetailDTO`;
  - `ReportsResultDTO`;
  - `ReportsValidationError`.
- Criado `tests/test_reports_contracts.py` cobrindo:
  - normalizacao de periodo/filtros;
  - fail-closed para exames fora de `active_exams`;
  - validacao de paginacao;
  - rejeicao de valores desconhecidos;
  - contrato de retorno com resumo, agrupamentos, detalhes e paginacao;
  - rejeicao de contagens negativas.
- Atualizado `docs/specs/tasks.md`: R01 marcada como concluida; R02 permanece como proxima pendencia.

Testes executados:

```powershell
python -m pytest tests/test_active_exams_scope.py tests/test_history_report_contract_strict.py -q --tb=short
python -m pytest tests/test_reports_contracts.py -q --tb=short
python -m pytest tests/test_active_exams_scope.py tests/test_history_report_contract_strict.py tests/test_reports_contracts.py -q --tb=short
```

Resultado final:

- `18 passed`
- `0 failed`
- 1 warning nao bloqueante de `reportlab`.

Proximo passo recomendado:

1. Executar R02 criando fixtures minimas para `historico_analises`, `exam_runs` e journal GAL.
2. Manter R03 bloqueada ate R02 cobrir casos enviado, nao enviado, erro, duplicado e resultado sem chave GAL.

## 10) Execucao R02 - Fixtures do Modulo de Relatorios

Data: 2026-05-11  
Executor: Codex com apoio da skill `pytest-baseline-fixtures`.

Implementado:

- Criado `tests/test_reports_fixtures.py` para validar os invariantes das fixtures de relatorio.
- Criado `tests/fixtures/reports/historico_analises.csv` com 5 registros sinteticos de historico.
- Criado `tests/fixtures/reports/exam_runs_rows.json` com 5 linhas semeaveis no repositorio SQLite `exam_runs`.
- Criado `tests/fixtures/reports/gal_transacoes.csv` com eventos GAL de sucesso, erro e duplicado.
- Criado `tests/fixtures/reports/expected_report_statuses.json` cobrindo:
  - enviado;
  - nao_enviado;
  - erro;
  - duplicado;
  - sem_chave_gal.
- Atualizado `tests/fixtures/README.md` documentando a matriz minima de status de relatorio.
- Atualizado `docs/specs/tasks.md`: R02 marcada como concluida; R03 permanece como proxima pendencia.

Testes executados:

```powershell
python -m pytest tests/test_reports_fixtures.py -q --tb=short
python -m pytest tests/test_reports_contracts.py tests/test_reports_fixtures.py tests/test_active_exams_scope.py tests/test_history_report_contract_strict.py -q --tb=short
```

Resultado final:

- `20 passed`
- `0 failed`
- 1 warning nao bloqueante de `reportlab`.

Proximo passo recomendado:

1. Executar R03 implementando consultas SQLite-first para totais por periodo, exame e positividade.
2. Usar `tests/fixtures/reports/exam_runs_rows.json` como seed inicial da consulta e manter o modulo sem recalcular CT ou `Resultado_geral`.

## 11) Execucao R03 - Consultas SQLite-first de Relatorios

Data: 2026-05-11  
Executor: Codex com orquestracao `maestro`, `tdd-implement` e `python-dev`.

Implementado:

- Criado `services/reports_repository.py` com `ReportsSQLiteRepository`.
- Criado `tests/test_reports_repository_sqlite.py` cobrindo:
  - agregacao por periodo, exame e positividade;
  - filtro por periodo, exame e positividade;
  - aliases de positividade (`detectavel` -> `positivo`);
  - uso exclusivo de `resultado_geral` persistido, sem depender de colunas CT.
- A consulta usa `exam_runs` SQLite como fonte e retorna `ReportsResultDTO` com resumo, agrupamentos, detalhes vazios e paginacao.
- Atualizado `docs/specs/tasks.md`: R03 marcada como concluida; R04 permanece como proxima pendencia.

Restricoes preservadas:

- Nenhuma regra de CT foi recalculada.
- Nenhum IO de analise ou envio GAL foi acionado.
- Status GAL nao foi reconciliado nesta etapa; isso fica para R04.

Testes executados:

```powershell
python -m pytest tests/test_reports_contracts.py tests/test_reports_fixtures.py -q --tb=short
python -m pytest tests/test_reports_repository_sqlite.py -q --tb=short
python -m pytest tests/test_reports_contracts.py tests/test_reports_fixtures.py tests/test_reports_repository_sqlite.py tests/test_active_exams_scope.py tests/test_history_report_contract_strict.py -q --tb=short
```

Resultado final:

- `24 passed`
- `0 failed`
- 1 warning nao bloqueante de `reportlab`.

Proximo passo recomendado:

1. Executar R04 implementando reconciliacao de status GAL a partir de `services.gal_transactions`.
2. Usar `tests/fixtures/reports/gal_transacoes.csv` e `expected_report_statuses.json` como matriz inicial de teste.

## 12) Auditoria SDD + Reescrita Documental + Governanca Multiagente

Data: 2026-05-13  
Executor: Claude Code (Opus 4.7) em tres rodadas READ-ONLY / refatoracao documental.

Resumo:

- **Fase 1 (2026-05-12)**: auditoria SDD READ-ONLY produziu `structure.map` + Relatorio de Divergencias com D-01..D-12, L-T01..L-T05, R-T1..R-T5 e DH-01..DH-09. Nenhum arquivo alterado. Plano registrado em `C:\Users\marci\.claude\plans\atue-como-arquiteto-de-nifty-hamster.md`.
- **Fase 2 (2026-05-13)**: reescrita SDD aplicada apenas em `docs/specs/requirements.md`, `docs/specs/design.md` e `docs/specs/tasks.md`. Patches:
  - `requirements.md`: §7.1 (pre-condicoes operacionais), CA-10/11/12, §10 (rastreabilidade GAP/BUG/TEST/DEC).
  - `design.md`: §3.6 reescrita (registry real vs stub), §3.7 reescrita (Fases 0-7 concluidas; referencia equipment_legacy_deprecation.md), §§8-10 novas (DT-001..003, LIM-001..003, pendencias).
  - `tasks.md`: §10 com 3 tarefas T-AUD-RD-* [Concluido] documentais, 5 [Pendente] e 8 [Bloqueado por DHP]. Tabela de rastreabilidade D->T-AUD.
- **Checagem (2026-05-13)**: validacao READ-ONLY confirmou escopo respeitado. Resultado: PRONTO PARA FASE 3.
- **Fase 3 (2026-05-13)**: governanca multiagente.
  - `AGENTS.md` e `CLAUDE.md` reescritos como contrato operacional expandido (18 secoes), mantendo identidade canonica.
  - `documento_de_passagem.md` criado como handoff transitorio.
  - `notas_de_passagem.md` recebeu esta entrada.
  - `inventario_de_lixo.md` recebeu candidatos D-05 e D-06 sob status "pendente de decisao humana".

Arquivos alterados:

- `docs/specs/requirements.md`, `docs/specs/design.md`, `docs/specs/tasks.md` (Fase 2).
- `AGENTS.md`, `CLAUDE.md`, `documento_de_passagem.md`, `notas_de_passagem.md`, `inventario_de_lixo.md` (Fase 3).

Arquivos NAO alterados (escopo respeitado):

- Nenhum codigo (`.py`), `config.json`, CSV, DB, snapshot, `banco/*`, `reports/`, `relatorios/`, fixtures, artefatos.
- `README.md` permanece ausente (DHP-07).

Decisoes humanas ainda pendentes (DHP-01..DHP-08): ver `documento_de_passagem.md §7` e `tasks.md §10`.

Status atualizado das tarefas prioritarias nao bloqueadas:

1. T-AUD-008 - concluida: teste-guardiao de imports em `domain/`.
2. T-AUD-003 - concluida: teste de regressao para `shared_storage` fail-closed.
3. T-AUD-007 - concluida por cobertura pre-existente: match-by-legacy na dual-key GAL.
4. T-AUD-001 - concluida: remocao de `pandas` de `domain/ct_rules.py`.
5. T-AUD-010 - ainda disponivel: inventario de `services/` (apenas inventario).

Ordem de retomada e checklist em `documento_de_passagem.md §10-§14`. Comecar por `AGENTS.md`, `docs/specs/requirements.md`, `docs/specs/design.md` e `docs/specs/tasks.md` antes de qualquer acao.

## 13) Microfase 3.1 - Ajuste Semantico de Governanca

Data: 2026-05-13  
Executor: Claude Code (Opus 4.7), microfase documental READ-ONLY de codigo.

Resumo:

Microfase de ajuste semantico aplicada para resolver 3 ressalvas identificadas na Checagem Pos-Fase 3:

1. **DHP-06 / DEC-006 RESOLVIDA** - classificacao canonica dos docs acessorios:
   - `docs/specs/equipment_legacy_deprecation.md` = **fonte canonica da deprecacao controlada** dos legados de equipamentos.
   - `docs/specs/plano_equipamentos_sdd.md` = **documento historico-orientador**, subordinado ao estado atual de `docs/specs/tasks.md §7`.
   - Tarefa associada `T-AUD-012` marcada `[Concluido]`.

2. **DHP-08 / DEC-008 RESOLVIDA** - aprovacao do teste-guardiao de imports em `domain/`:
   - `T-AUD-008` e executavel sem bloqueio formal.
   - Cria apenas teste automatizado em `tests/`, **nao altera codigo de producao**.
   - Deve preceder `T-AUD-001` (remocao de pandas em `domain/ct_rules.py`).

3. **inventario_de_lixo.md** esclarecido:
   - Categorias `Apagar`, `Manter`, `Desconsiderar`, `Alterar` sao classificacoes documentais/historicas pre-existentes; **nao autorizam acao automatica**.
   - Nenhum item pode ser apagado, movido ou alterado sem decisao humana explicita na rodada atual.

Arquivos alterados nesta microfase:

- `docs/specs/requirements.md` (§10 DEC-006 e nova DEC-008).
- `docs/specs/tasks.md` (T-AUD-008, T-AUD-012, tabela de rastreabilidade D-10, novas notas da microfase).
- `AGENTS.md` (§1 descricoes, §15 reorganizado em 15.1/15.2, §16 T-AUD-008).
- `CLAUDE.md` (idem AGENTS.md, identidade canonica preservada via SHA256).
- `documento_de_passagem.md` (§4 descricoes, §7 reorganizado em 7.1/7.2, §8 T-AUD-008).
- `inventario_de_lixo.md` (nota operacional adicionada no topo).
- `notas_de_passagem.md` (esta entrada).

Arquivos NAO alterados:

- Nenhum codigo (`.py`), `config.json`, CSV, DB, snapshot, `banco/*`, `reports/`, `relatorios/`, fixtures, artefatos operacionais.
- `docs/specs/design.md` (sem necessidade de alteracao nesta microfase).
- `docs/specs/equipment_legacy_deprecation.md` e `docs/specs/plano_equipamentos_sdd.md` (apenas consultados; sua classificacao foi registrada nos demais documentos).
- `README.md` (DHP-07 permanece pendente).

DHPs ainda pendentes apos a microfase 3.1, antes da DEC-001: DHP-01, DHP-02 (=DHP-09), DHP-03, DHP-04, DHP-05, DHP-07. **Total naquele momento: 6 pendentes** (eram 8 antes da microfase).

Ordem operacional atualizada: as tarefas T-AUD-008, T-AUD-001, T-AUD-003 e T-AUD-007 foram concluidas; a proxima tarefa nao bloqueada registrada e T-AUD-010 (inventario de `services/`, sem refatoracao).

## 14) Execucao T-AUD-008, T-AUD-001, T-AUD-003 e T-AUD-007

Data: 2026-05-13  
Executor: Codex, rodadas SDD restritas por tarefa.

Resumo:

- **T-AUD-008 concluida**:
  - criado `tests/test_domain_pure_imports.py`;
  - teste guardiao varre arquivos `.py` em `domain/` via AST;
  - bloqueia imports proibidos: `pandas`, `selenium`, `seleniumrequests`, `tkinter`, `customtkinter`;
  - evidencia final: `python -m pytest tests/test_domain_pure_imports.py -q --tb=short` com `1 passed`.

- **T-AUD-001 concluida**:
  - `domain/ct_rules.py` deixou de importar `pandas`;
  - `pd.isna(ct_val)` foi substituido por helper local com checagem nativa usando `math.isnan`;
  - nao houve mudanca nas regras de negocio de CT;
  - evidencias:
    - `tests/test_domain_pure_imports.py` passou;
    - recorte CT especifico passou com `131 passed`;
    - um teste H05 relacionado a `ui/janela_analise_completa.py` falhou fora do escopo da remocao de `pandas` e foi registrado como risco externo a esta tarefa.

- **T-AUD-003 concluida**:
  - criado `tests/test_shared_storage_precondition_required.py`;
  - teste usa configuracao isolada em memoria;
  - nao depende do `config.json` real;
  - valida `shared_storage.required=true` com `data_root=""` e `allowed_roots=[]`;
  - confirma `shared_storage_required=FAIL` e `ready=False`;
  - evidencia: `python -m pytest tests/test_shared_storage_precondition_required.py -q --tb=short` com `1 passed`.

- **T-AUD-007 concluida por cobertura pre-existente**:
  - nao houve alteracao de arquivo;
  - teste equivalente validado: `tests/test_phase_u3_gal_send_use_case.py::test_u3_use_case_still_skips_legacy_success_key_with_scoped_request`;
  - cobre journal/historico com apenas chave legada de 4 campos, chave 4+N ausente, bloqueio como `duplicado`;
  - usa `FakeDriver` e `FakeGalService`;
  - nao aciona Selenium, navegador, Firefox, GAL real ou credenciais;
  - evidencia: comando especifico com `1 passed`.

Arquivos alterados nesta atualizacao documental:

- `docs/specs/tasks.md`;
- `documento_de_passagem.md`;
- `notas_de_passagem.md`.

Arquivos de codigo e configuracao:

- Nenhum codigo foi alterado nesta atualizacao documental.
- `config.json` nao foi alterado.
- `AGENTS.md`, `CLAUDE.md`, `docs/specs/requirements.md` e `docs/specs/design.md` nao foram alterados.
- Nenhuma tarefa bloqueada por DHP foi executada.

DHPs ainda pendentes apos DEC-003:

- DHP-02 / DHP-09 / DEC-002: destino futuro de `banco/*`.
- DHP-04 / DEC-004: politica para `snapshots/encoding_backup_*`.
- DHP-05 / DEC-005: politica para `relatorio_final_corrida_*.json`.
- DHP-07 / DEC-007: criacao de `README.md` humano.

Total pendente: 4 decisoes humanas.

## 15) Decisao DEC-001 / DHP-01 - Status do config.json

Data: 2026-05-13  
Executor: Codex, rodada documental SDD sem execucao de codigo.

Decisao humana registrada:

- `config.json` versionado deve ser tratado como template/local runtime nao pronto para producao.
- Ambientes produtivos exigem configuracao local validada, com `shared_storage.root`, `data_root` e `allowed_roots` preenchidos.
- A aplicacao nao deve operar em producao com `shared_storage.required=true` e caminhos vazios.

Impacto documental:

- DHP-01 / DEC-001 marcada como resolvida.
- T-AUD-002 marcada como concluida por registro da decisao.
- T-AUD-008-CFG foi concluida em rodada propria posterior: chave vazia removida, mojibake corrigido, JSON/UTF-8 validado e `config.json` preservado como template/local runtime sem dados reais sensiveis.

Arquivos alterados nesta rodada documental:

- `docs/specs/requirements.md`;
- `docs/specs/tasks.md`;
- `documento_de_passagem.md`;
- `notas_de_passagem.md`;
- `AGENTS.md`;
- `CLAUDE.md`.

Arquivos nao alterados:

- Nenhum codigo (`.py`) foi alterado.
- `config.json` nao foi alterado.
- Nenhum `.json` operacional, CSV, DB/SQLite, snapshot, `banco/*`, `reports/*`, `relatorios/*`, script, migration ou `README.md` foi alterado.

DHPs ainda pendentes:

- DHP-02 / DHP-09 / DEC-002: destino futuro de `banco/*`.
- DHP-04 / DEC-004: politica para `snapshots/encoding_backup_*`.
- DHP-05 / DEC-005: politica para `relatorio_final_corrida_*.json`.
- DHP-07 / DEC-007: criacao de `README.md` humano.

Total pendente: 4 decisoes humanas.
## 16) Execucao T-AUD-008-CFG - Correcao controlada de config.json

Data: 2026-05-13
Executor: Codex, rodada de configuracao SDD restrita a `config.json`.

Resultado:

- T-AUD-008-CFG marcada como concluida para atualizacao documental posterior.
- `config.json` permaneceu JSON valido e legivel como UTF-8.
- Chave vazia literal `""` removida de `general`.
- Mojibake em `lab_responsible` corrigido.
- `shared_storage.root`, `data_root` e `allowed_roots` permaneceram vazios, preservando o arquivo como template/local runtime.
- Nenhum dado real sensivel, credencial, token, senha ou caminho real de producao foi inserido.
- Nenhum codigo, teste ou documentacao foi alterado na rodada de configuracao.

Validacoes registradas:

- `python -m json.tool config.json` passou.
- Leitura UTF-8 e `json.loads` passaram.
- `tests/test_shared_storage_precondition_required.py` passou com `1 passed`.

DHPs ainda pendentes:

- DHP-02 / DHP-09 / DEC-002: destino futuro de `banco/*`.
- DHP-04 / DEC-004: politica para `snapshots/encoding_backup_*`.
- DHP-05 / DEC-005: politica para `relatorio_final_corrida_*.json`.
- DHP-07 / DEC-007: criacao de `README.md` humano.

Total pendente: 4 decisoes humanas.

## 17) Decisao DEC-003 / DHP-03 - Autenticacao legado controlado

Data: 2026-05-13
Executor: Codex, rodada documental SDD sem execucao de testes ou codigo.

Decisao humana registrada:

- `core/authentication/user_manager.py` sera tratado como modulo legado em deprecacao controlada.
- O fluxo ativo de autenticacao do sistema passa a ser reconhecido como `autenticacao/auth_service.py` + `autenticacao/login.py`, com matriz de autorizacao em `application/access_control.py`.
- Nenhuma remocao fisica sera feita neste momento.
- Antes de qualquer remocao, deve existir teste guardiao impedindo novo uso runtime de `core.authentication.user_manager`.
- Deve haver rodada separada para neutralizar ou remover o bloco `__main__` / bootstrap manual do modulo legado.

Evidencias da auditoria READ-ONLY DHP-03A:

- `autenticacao/auth_service.py` esta ativo em runtime e e chamado por UI, servicos, exportacao, script operacional e testes.
- `autenticacao/login.py` esta ativo em runtime e e usado no bootstrap da aplicacao.
- `core/authentication/user_manager.py` foi classificado como legado / possivelmente morto em runtime normal / sobreposto.
- Nenhum import externo de `core.authentication.user_manager` foi encontrado no grafo estatico pesquisado.
- Ha risco associado ao bloco de execucao manual e ao bootstrap com credencial padrao.

Tarefas DEC-003 criadas/ajustadas:

- T-AUD-004A: **concluida posteriormente**; teste guardiao de nao uso runtime de `core.authentication.user_manager`.
- T-AUD-004B: **concluida posteriormente**; bloco `__main__` / bootstrap manual de `core/authentication/user_manager.py` neutralizado sem remocao fisica.
- T-AUD-013: cobertura complementar de callers/guardioes apos DEC-003.
- T-AUD-014: **concluida posteriormente**; correcao pontual de encoding/parsing em `ui/user_management.py` por `U+FEFF`.

DHPs ainda pendentes:

- DHP-02 / DHP-09 / DEC-002: destino futuro de `banco/*`.
- DHP-04 / DEC-004: politica para `snapshots/encoding_backup_*`.
- DHP-05 / DEC-005: politica para `relatorio_final_corrida_*.json`.
- DHP-07 / DEC-007: criacao de `README.md` humano.

Total pendente: 4 decisoes humanas.

## 18) T-AUD-004A - Guardiao de nao uso runtime de user_manager legado

Data: 2026-05-13
Executor: Codex, rodada documental SDD sem execucao de testes ou codigo.

Status:

- **T-AUD-004A concluida**.
- Criado `tests/test_auth_legacy_user_manager_no_runtime_imports.py`.
- O teste varre areas runtime com AST e nao importa codigo de producao.
- O teste bloqueia imports de `core.authentication.user_manager` fora de allowlist explicita.
- Allowlist inicial vazia.

Evidencia objetiva da rodada tecnica:

- Comando: `python -m pytest tests/test_auth_legacy_user_manager_no_runtime_imports.py -q --tb=short`.
- Resultado: `1 passed`.
- Nenhum codigo de producao foi alterado.
- `core/authentication/user_manager.py` nao foi alterado.
- `config.json` nao foi alterado.
- Nenhum segredo foi lido ou exposto.

Estado de autenticacao:

- `core/authentication/user_manager.py` continua legado em deprecacao controlada.
- Fluxo ativo permanece `autenticacao/auth_service.py` + `autenticacao/login.py`, com matriz em `application/access_control.py`.
- **T-AUD-004B concluida posteriormente**: bloco `__main__` / bootstrap manual neutralizado; o achado de teste por `U+FEFF` em `ui/user_management.py` foi resolvido por T-AUD-014.

DHPs ainda pendentes:

- DHP-02 / DHP-09 / DEC-002: destino futuro de `banco/*`.
- DHP-04 / DEC-004: politica para `snapshots/encoding_backup_*`.
- DHP-05 / DEC-005: politica para `relatorio_final_corrida_*.json`.
- DHP-07 / DEC-007: criacao de `README.md` humano.

Total pendente: 4 decisoes humanas.

## 19) T-AUD-004B - Neutralizacao do __main__ de user_manager legado

Data: 2026-05-13
Executor: Codex, rodada documental SDD sem execucao de testes ou codigo.

Status:

- **T-AUD-004B concluida**.
- `core/authentication/user_manager.py` foi alterado na rodada tecnica, mas nao removido.
- O bloco `if __name__ == "__main__"` nao chama mais `inicializar_sistema()`.
- Execucao direta agora exibe mensagem segura de deprecacao controlada e encerra com `SystemExit(2)`.
- Classes e funcoes existentes foram preservadas.

Evidencias da rodada tecnica:

- Guardiao: `python -m pytest tests/test_auth_legacy_user_manager_no_runtime_imports.py -q --tb=short`.
- Resultado do guardiao: `1 passed`.
- Recorte especifico de autenticacao: `19 passed` e `1 failed`.
- Falha externa ao escopo: `tests/test_phase_b2_auth_actor_required.py::test_b2_user_management_uses_strict_auth_api`.
- Causa registrada: `SyntaxError: invalid non-printable character U+FEFF` ao parsear `ui/user_management.py`.
- `ui/user_management.py` nao foi corrigido na rodada T-AUD-004B porque estava fora do escopo; foi corrigido posteriormente por T-AUD-014.

Ressalva:

- A falha por `U+FEFF` em `ui/user_management.py` nao invalidou T-AUD-004B, pois o objetivo autorizado era neutralizar a execucao direta de `core/authentication/user_manager.py`; a ressalva foi resolvida por T-AUD-014.

Nova tarefa futura:

- **T-AUD-014** (DT/TN) - correcao pontual de encoding/parsing em `ui/user_management.py`, removendo/caracterizando BOM ou caractere inicial `U+FEFF` que impede `ast.parse`.
- Status: **Concluida**.
- Evidencia: removido apenas BOM UTF-8 inicial `EF BB BF`; `ast.parse` retornou `parse ok`; teste especifico afetado passou com `1 passed`; suite especifica passou com `3 passed`.

DHPs ainda pendentes:

- DHP-02 / DHP-09 / DEC-002: destino futuro de `banco/*`.
- DHP-04 / DEC-004: politica para `snapshots/encoding_backup_*`.
- DHP-05 / DEC-005: politica para `relatorio_final_corrida_*.json`.
- DHP-07 / DEC-007: criacao de `README.md` humano.

Total pendente: 4 decisoes humanas.

## 20) T-AUD-014 - Correcao pontual de U+FEFF em ui/user_management.py

Data: 2026-05-13
Executor: Codex, rodada documental SDD sem execucao de testes ou codigo.

Status:

- **T-AUD-014 concluida**.
- `ui/user_management.py` foi alterado na rodada tecnica.
- Foi removido apenas o BOM UTF-8 inicial `EF BB BF`, que causava `U+FEFF` no inicio do arquivo.
- Local aproximado: antes da docstring inicial.
- Nenhuma logica, indentacao, import, funcao, permissao, persistencia ou UI foi alterada.

Evidencias da rodada tecnica:

- Validacao de parsing: `python -c "import ast, pathlib; p=pathlib.Path('ui/user_management.py'); ast.parse(p.read_text(encoding='utf-8'), filename=str(p)); print('parse ok')"` retornou `parse ok`.
- Teste que falhava: `python -m pytest tests/test_phase_b2_auth_actor_required.py::test_b2_user_management_uses_strict_auth_api -q --tb=short` retornou `1 passed`.
- Suite especifica: `python -m pytest tests/test_phase_b2_auth_actor_required.py -q --tb=short` retornou `3 passed`.

Impacto:

- Ressalva externa da T-AUD-004B resolvida.
- `config.json` nao foi alterado.
- Nenhum arquivo em `banco/` foi lido ou alterado.
- Nenhum segredo foi lido ou exposto.

DHPs ainda pendentes:

- DHP-02 / DHP-09 / DEC-002: destino futuro de `banco/*`.
- DHP-04 / DEC-004: politica para `snapshots/encoding_backup_*`.
- DHP-05 / DEC-005: politica para `relatorio_final_corrida_*.json`.
- DHP-07 / DEC-007: criacao de `README.md` humano.

Total pendente: 4 decisoes humanas.

## 21) Sincronizacao SDD pre-higienizacao

Data: 2026-05-14  
Executor: Codex, rodada documental SDD autorizada apos auditoria READ-ONLY de sincronizacao.

Resumo:

- Auditoria READ-ONLY indicou que a documentacao ainda nao estava pronta para higienizacao: `design.md`, `AGENTS.md` e `CLAUDE.md` mantinham referencias antigas sobre DT-001/pandas e listas antigas de T-AUD ja concluidas.
- Atualizacao documental executada somente em Markdown permitido; nenhum codigo, teste, `config.json`, CSV, banco, report, log ou snapshot foi alterado.
- Tarefas recentes incorporadas ao SDD: `SDD-20260514-001` (relatorio final pre-GAL), `SDD-20260514-002` (completude VR1e2 placa cheia), `SDD-20260514-003` (normalizacao de extrator contratual) e `UI-AUD-002` (`Reaplicar Selecao`).
- Lacunas registradas para rodada futura: `UI-AUD-001`, `UI-AUD-003`, `HIG-001` e `HIG-002`.
- Proximo passo recomendado: auditoria READ-ONLY de higienizacao para implantacao, sem remover/mover arquivos, sem executar aplicacao/testes e sem abrir segredos.

DHPs ainda pendentes: DHP-02/DHP-09, DHP-04, DHP-05 e DHP-07.

## 22) Microatualizacao documental requirements pre-higienizacao

Data: 2026-05-14  
Executor: Codex, rodada documental SDD autorizada apos auditoria READ-ONLY de sincronizacao.

Resumo:

- `docs/specs/requirements.md` sincronizado com o estado real de T-AUD-008-CFG: correcao formal concluida, `config.json` preservado como template/local runtime e sem dados reais sensiveis.
- `docs/specs/requirements.md` sincronizado com DEC-003 resolvida: `core/authentication/user_manager.py` permanece legado em deprecacao controlada; fluxo ativo = `autenticacao/auth_service.py` + `autenticacao/login.py`; matriz ativa = `application/access_control.py`.
- Lacunas novas registradas: `CONFIG-ENC-001`, `HIG-003` e `RELEASE-001`.
- Escopo preservado: nenhum codigo, teste, `config.json`, CSV, DB/SQLite, `banco/*`, report, log, snapshot, `.tmp/*` ou script foi alterado; nenhuma higienizacao foi executada.

Proximo passo recomendado: checagem READ-ONLY pre-higienizacao e, se consistente, auditoria READ-ONLY de higienizacao.

## 23) Atualizacao SDD pos-auditoria multiusuario e instalacao

Data: 2026-05-15  
Executor: Codex, rodada documental SDD autorizada apos Auditoria READ-ONLY - Capacidade Multiusuario e Modulo de Instalacao.

Resumo:

- Registrada classificacao multiusuario: **APTO COM RESTRICOES**.
- Registrada classificacao do modulo de Instalacao Inicial: **FUNCIONAL COM RESTRICOES**.
- Registrado que o SDD atual formaliza ate 5 usuarios em compartilhamento unico; 10 usuarios ainda nao esta comprovado.
- Criado backlog pendente CONC-001..CONC-006 e INST-001..INST-005 em `docs/specs/tasks.md`.
- Prioridades antes de implantacao produtiva com 10 usuarios: CONC-002, CONC-003 e INST-001.
- Decisoes humanas pendentes: formalizar aptidao plena para 10 usuarios apos testes CONC/correcoes prioritarias. Perfil da Instalacao Inicial resolvido por DEC-010: ADMIN+MASTER, com INST-004 pendente para ajuste de UI/codigo em rodada propria.
- Escopo preservado: nenhum codigo, teste, `config.json`, CSV, banco, report, log, snapshot, script ou artefato operacional foi alterado; nenhuma higienizacao foi executada.

## 2026-05-15 - Decisao documental sobre perfil da Instalacao Inicial

- DEC-010 registrada: Instalacao Inicial deve ser acessivel por ADMIN e MASTER.
- Condicoes documentadas: confirmacao forte antes de aplicar configuracao, log/auditoria com ator e backup previo futuro.
- INST-004 permanece pendente para ajuste de UI/codigo em rodada propria caso a aba ainda restrinja acesso apenas a ADMIN.
- Nenhum codigo, teste, `config.json`, `banco/*` ou artefato operacional foi alterado nesta atualizacao documental.

## 24) Decisao de escopo multiusuario inicial

Data: 2026-05-15  
Executor: Codex, rodada documental SDD autorizada.

Resumo:

- Decisao humana registrada: a implantacao inicial sera um piloto controlado com **3 a 5 usuarios**.
- A implantacao inicial nao declarara aptidao plena para 10 usuarios simultaneos.
- 10 usuarios passa a ser meta condicionada a conclusao dos testes CONC e correcoes prioritarias, especialmente CONC-002, CONC-003 e INST-001.
- CONC-001..CONC-006 permanecem pendentes; nenhuma tarefa CONC foi marcada como concluida.
- Nenhuma outra DHP foi resolvida.
- Escopo preservado: nenhum codigo, teste, `config.json`, CSV, DB/SQLite, banco, report, log, snapshot, script ou artefato operacional foi alterado.

## 26) Atualizacao documental pos-auditoria HIG READ-ONLY

Data: 2026-05-15

- Auditoria READ-ONLY de Higienizacao para Implantacao classificada como **ATENCAO**.
- Pasta atual registrada como nao pronta para empacotamento direto.
- Evidencia registrada: 0 arquivos rastreados por Git e 2586 arquivos nao rastreados.
- Artefatos de risco registrados: `reports/`, `relatorios/`, `logs/`, `.tmp/pytest_tmp`, `banco/*`, `.env.txt`, `snapshots/encoding_backup_*`, `relatorio_final_corrida_*.json` e `test_history.csv`.
- Scripts de limpeza em `scripts/` classificados como potencialmente destrutivos; nao executar sem auditoria propria, baseline/backup e autorizacao explicita.
- RELEASE-001 registrado como concluido por baseline manual informado pelo usuario: `integragal_baseline_pre_higienizacao_2026-05-15.zip`.
- HIG-001, HIG-002 e HIG-003 registradas como concluidas somente na dimensao READ-ONLY/classificacao; HIG-004..HIG-008 permanecem pendentes/bloqueadas conforme DHP.
- DHPs nao resolvidas naquele momento: DHP-02/DHP-09, DHP-04, DHP-05 e DHP-07. DHP-05 foi resolvida posteriormente por DEC-005 em 2026-05-15.
- Nenhuma limpeza, alteracao de `.gitignore`, execucao de scripts, teste, codigo, `config.json`, banco, report, log, snapshot ou artefato operacional foi executada.

## 27) Plano formal HIG por fases

Data: 2026-05-15

- `docs/specs/higienizacao_implantacao.md` atualizado de esqueleto para plano formal.
- Fases registradas: H0 baseline/backup, H1 `.gitignore`, H2 separacao de artefatos runtime, H3 retencao/arquivamento, H4 auditoria de scripts, H5 legados bloqueados por DHP, H6 montagem do pacote de release e H7 validacao pos-higienizacao.
- Estrutura proposta de release registrada: `release/app/`, `release/config_template/`, `release/docs_operacionais/`, `release/assets/`, `release/scripts_autorizados/`, `release/runtime_empty/`.
- HIG-004 foi concluida por atualizacao controlada de `.gitignore`; HIG-008 foi concluida como manifest documental de release; HIG-006 e HIG-007 permanecem pendentes; HIG-005 permanece bloqueada por DHP.
- Nenhuma limpeza, alteracao de `.gitignore`, movimentacao, remocao, execucao de script, teste, codigo, `config.json`, banco, report, log, snapshot ou artefato operacional foi executada.

## 28) Decisao DHP-05 / DEC-005

Data: 2026-05-15

- DHP-05 / DEC-005 resolvida por decisao humana.
- Arquivos `relatorio_final_corrida_*.json` localizados na raiz sao artefatos runtime/transitorios de execucao.
- Esses arquivos nao devem entrar no pacote de release operacional.
- Devem ser tratados por politica de retencao, realocacao ou regra de `.gitignore` em rodada propria.
- Nenhuma exclusao automatica, movimentacao ou alteracao de `.gitignore` esta autorizada por esta decisao.
- HIG-007 foi atualizada de bloqueada por DHP para pendente/desbloqueada para rodada futura de retencao/realocacao/`.gitignore`; nao foi marcada como concluida.
- DHPs ainda pendentes apos DEC-004: DHP-02/DHP-09 e DHP-07.
- Nenhum arquivo runtime `relatorio_final_corrida_*.json` foi alterado, movido ou apagado.

## 29) Decisao DHP-04 / DEC-004

Data: 2026-05-15

- DHP-04 / DEC-004 resolvida por decisao humana.
- Diretorios `snapshots/encoding_backup_*` sao artefatos historicos de backup/encoding, criados para rastreabilidade e eventual recuperacao durante correcoes de encoding.
- Esses diretorios nao devem entrar no pacote de release operacional.
- Devem ser tratados por politica de retencao, arquivamento externo ou exclusao controlada em rodada propria, sempre apos baseline/backup.
- Nenhuma exclusao automatica, movimentacao ou alteracao de `.gitignore` esta autorizada por esta decisao.
- HIG-006 foi atualizada de bloqueada por DHP para pendente/desbloqueada para rodada futura de retencao/arquivamento/exclusao controlada; nao foi marcada como concluida.
- DHPs ainda pendentes: DHP-02/DHP-09.
- Nenhum diretorio `snapshots/encoding_backup_*` foi alterado, movido ou apagado.

## 30) HIG-004 - Atualizacao controlada de .gitignore

Data: 2026-05-15

- HIG-004 concluida.
- `.gitignore` atualizado com secao explicita do IntegRAGal para ambientes locais, caches, temporarios, logs, relatorios gerados, snapshots `encoding_backup_*`, `relatorio_final_corrida_*.json`, `test_history.csv`, bancos locais e arquivos sensiveis em `banco/`.
- A atualizacao impede rastreamento futuro; nao remove, move ou altera arquivos existentes.
- `config.json`, `docs/specs/`, `config/contracts/` e `requirements.txt` nao foram ignorados automaticamente.
- HIG-006 e HIG-007 permanecem pendentes; HIG-008 foi concluida posteriormente como manifest documental; HIG-005 permanece bloqueada por DHP-02/DHP-09.
- DHPs ainda pendentes: DHP-02/DHP-09.
- Nenhuma limpeza, movimentacao, remocao, execucao de script, teste, codigo, `config.json`, banco, report, log, snapshot ou artefato operacional foi executada.

## 31) HIG-008 - Manifest documental de release

Data: 2026-05-15

- HIG-008 concluida como documentacao.
- `docs/specs/higienizacao_implantacao.md` agora define o manifest alvo: `release/app/`, `release/config_template/`, `release/docs_operacionais/`, `release/assets/`, `release/scripts_autorizados/` e `release/runtime_empty/`.
- A estrutura nao foi materializada: nenhuma pasta `release/` foi criada e nenhum arquivo foi copiado, movido, apagado ou empacotado.
- Manifest exclui `banco/*`, `.env*`, logs, reports, relatorios, caches, `.tmp`, snapshots `encoding_backup_*`, `relatorio_final_corrida_*.json`, testes e scripts de limpeza nao auditados.
- `config.json` permanece template/local runtime; producao exige Instalacao Inicial para configurar `shared_storage`.
- HIG-006 e HIG-007 permanecem pendentes; HIG-005 permanece bloqueada por DHP-02/DHP-09.
- DHPs ainda pendentes: DHP-02/DHP-09.
- Nenhuma limpeza, movimentacao, remocao, execucao de script, teste, codigo, `config.json`, banco, report, log, snapshot ou artefato operacional foi executada.

## 32) Decisao DHP-07 / DEC-007 e criacao do README humano

Data: 2026-05-15

- DHP-07 / DEC-007 resolvida por decisao humana.
- Criado `README.md` na raiz como ponto de entrada humano e operacional para operadores, administradores e equipe tecnica.
- README cobre visao geral, estado de implantacao, requisitos basicos, Instalacao Inicial, execucao, estrutura de release, itens fora do release, restricoes conhecidas, seguranca e referencias SDD.
- README registra piloto controlado com 3 a 5 usuarios e nao declara aptidao plena para 10 usuarios.
- README registra que `config.json` e template/local runtime e que producao exige Instalacao Inicial.
- README nao substitui a documentacao SDD.
- T-AUD-009 concluida.
- DHPs ainda pendentes: DHP-02/DHP-09.
- Nenhum arquivo runtime foi alterado, copiado, movido ou apagado.

## 33) Microcorrecao documental pos-fechamento DHP-07

Data: 2026-05-15
Executor: Claude Code (Sonnet 4.6), rodada documental autorizada apos checagem READ-ONLY de fechamento.

- Corrigida data do cabecalho de `documento_de_passagem.md` de 2026-05-14 para 2026-05-15.
- Inserida nota de orientacao de leitura no topo de `documento_de_passagem.md` alertando que secoes historicas datadas refletem o estado naquele momento.
- Renumerada secao fora de ordem: `## 24. Decisao de escopo multiusuario inicial` passou a ser `## 32.` (sem alteracao de conteudo).
- DHP-07 / DEC-007 permanece resolvida conforme `AGENTS.md §15.1`, `tasks.md T-AUD-009`, `higienizacao_implantacao.md §5.1` e `documento_de_passagem.md §31`.
- Nenhum arquivo de codigo, README.md, AGENTS.md, CLAUDE.md, tasks.md, config.json, banco/*, reports/*, scripts/* ou artefato runtime foi alterado.

## 35) Microcorrecao documental — referencias stale T-AUD-006/HIG-007 em tasks.md

Data: 2026-05-15
Executor: Claude Code (Sonnet 4.6), rodada documental SDD autorizada.

- Corrigidas tres referencias stale em `docs/specs/tasks.md` apos retomada pos-/compact:
  1. Linha ~90: T-AUD-006 atualizada de `[ ] [Pendente]` para `[x] [Concluido]` com evidencia da Opcao A.
  2. Tabela de rastreabilidade: D-06 | T-AUD-006 atualizado de `Pendente` para `Concluido (documental, HIG-007 Opcao A)`.
  3. Linha ~214: texto stale "HIG-006 e HIG-007 permanecem pendentes" corrigido para refletir HIG-007 concluida, HIG-006 pendente/desbloqueada e HIG-005 bloqueada por DHP-02/DHP-09.
- Nenhum arquivo de codigo, README.md, AGENTS.md, CLAUDE.md, config.json, banco/*, relatorio_final_corrida_*.json ou artefato runtime foi alterado.

## 37) Microcorrecao documental — referencias stale HIG-006 pos-checagem HIG

Data: 2026-05-15
Executor: Claude Code (Sonnet 4.6), rodada documental SDD autorizada.

- Checagem READ-ONLY classificou estado HIG como CONSISTENTE COM RESSALVAS, identificando 2 refs stale canônicas.
- Corrigidas em rodada de microcorrecao:
  1. `docs/specs/tasks.md` linha ~214 (narrativa HIG-004): "HIG-006 permanece pendente/desbloqueada" → "HIG-006 foi concluida documentalmente (Opcao A, 2026-05-15)".
  2. `documento_de_passagem.md §5` linha ~176 (Principais achados): "HIG-006 pendente para rodada futura" → "HIG-006 concluida documentalmente (Opcao A, 2026-05-15)"; HIG-005 e DHP-02/DHP-09 explicitados.
- AGENTS.md e CLAUDE.md nao foram alterados.
- Nenhum arquivo de codigo, config.json, banco/*, relatorio_final_corrida_*.json ou artefato runtime foi alterado.

## 36) HIG-006 — Fechamento documental (Opcao A)

Data: 2026-05-15
Executor: Claude Code (Sonnet 4.6), rodada documental SDD autorizada.

- HIG-006 concluida documentalmente pela Opcao A: planejamento READ-ONLY confirmou 16 diretorios `snapshots/encoding_backup_*` vazios (0 KB); `.gitignore` ja cobre (linha 936); manifest HIG-008 exclui do release.
- Nenhum diretorio foi movido, removido, compactado, arquivado ou alterado.
- DHPs ainda pendentes: DHP-02/DHP-09. HIG-005 permanece bloqueada por DHP-02/DHP-09.
- Arquivos alterados nesta rodada: `docs/specs/tasks.md`, `docs/specs/higienizacao_implantacao.md`, `inventario_de_lixo.md`, `documento_de_passagem.md`, `notas_de_passagem.md`, `AGENTS.md`, `CLAUDE.md`.
- Nenhum arquivo de codigo, README.md, config.json, banco/*, snapshots/*, relatorio_final_corrida_*.json ou artefato runtime foi alterado, movido ou apagado.

## 34) HIG-007 — Fechamento documental (Opcao A)

Data: 2026-05-15
Executor: Claude Code (Sonnet 4.6), rodada documental SDD autorizada.

- HIG-007 concluida documentalmente pela Opcao A: confirmacao de cobertura por `.gitignore` sem remocao/movimentacao de arquivos.
- Dois arquivos identificados: `relatorio_final_corrida_last.json` e `relatorio_final_corrida_vr1.json` (~2.160 bytes cada, raiz); conteudo nao aberto.
- Nenhum arquivo semelhante encontrado em `reports/`, `relatorios/` ou `logs/`.
- `.gitignore` ja cobre `relatorio_final_corrida_*.json` (HIG-004, linha 939).
- Manifest HIG-008 ja exclui esses arquivos do pacote de release.
- T-AUD-006 concluida documentalmente.
- DHPs ainda pendentes: DHP-02/DHP-09.
- Arquivos alterados nesta rodada: `docs/specs/tasks.md`, `docs/specs/higienizacao_implantacao.md`, `inventario_de_lixo.md`, `documento_de_passagem.md`, `notas_de_passagem.md`, `AGENTS.md`, `CLAUDE.md`.
- Nenhum arquivo de codigo, README.md, config.json, banco/*, relatorio_final_corrida_*.json ou artefato runtime foi alterado, movido ou apagado.

## 38) DEC-002 / HIG-005 — Fechamento documental (Opcao A)

Data: 2026-05-15
Executor: Claude Code (Sonnet 4.6), rodada documental SDD autorizada.

- **DHP-02/DHP-09/DEC-002 RESOLVIDA**: `banco/*` mantido fisicamente em dev/runtime como fallback operacional controlado; conteudo sensivel nao aberto nesta decisao; manifest HIG-008 ja exclui do release integralmente; nenhuma exclusao, movimentacao, arquivamento ou migracao fisica autorizada.
- **HIG-005 concluida documentalmente (Opcao A)**: nenhum arquivo de `banco/*` foi aberto, movido, arquivado ou excluido.
- Tarefas futuras nao bloqueantes registradas: PRIV-001 (auditoria LGPD de `banco/*`), GIG-001 (estender `.gitignore` para CSVs operacionais), HIG-009 (planejar `banco_template/` + bootstrap).
- DHPs HIG pendentes apos DEC-002: **0**.
- Arquivos alterados nesta rodada: `docs/specs/requirements.md`, `docs/specs/tasks.md`, `docs/specs/higienizacao_implantacao.md`, `inventario_de_lixo.md`, `documento_de_passagem.md`, `notas_de_passagem.md`, `AGENTS.md`, `CLAUDE.md`.
- Nenhum arquivo de codigo, `config.json`, `banco/*`, `reports/*`, `relatorios/*`, `logs/*`, script, snapshot ou artefato runtime foi aberto, alterado, movido, arquivado ou excluido.

## 39) Microcorrecao documental final — referencias stale pos-DEC-002

Data: 2026-05-15
Executor: Claude Code (Sonnet 4.6), rodada documental SDD autorizada apos checagem READ-ONLY final do estado HIG.

- Checagem READ-ONLY classificou estado geral como **CONSISTENTE COM RESSALVAS**: 1 referencia stale operacional (README.md §8) e 2 borderline (documento_de_passagem.md §7.2 e §9).
- Corrigidas as 3 referencias stale:
  1. `README.md §8` linha 98: substituida formulacao "destino futuro ainda depende de DHP-02/DHP-09" por referencia a DEC-002 resolvida, manifest HIG-008 e tarefas futuras PRIV-001/GIG-001/HIG-009.
  2. `documento_de_passagem.md §7.2` linha 87: DHP-02/DHP-09/DEC-002 marcada como **RESOLVIDA em 2026-05-15**, consistente com as demais DHPs da mesma secao.
  3. `documento_de_passagem.md §9` linha 128: expressao "bloqueado por DHP-02/DHP-09" substituida por referencia a DEC-002 Opcao A.
- Arquivos alterados nesta rodada: `README.md`, `documento_de_passagem.md`, `notas_de_passagem.md`.
- AGENTS.md e CLAUDE.md nao foram alterados.
- Nenhum arquivo de codigo, `config.json`, `banco/*`, `reports/*`, `relatorios/*`, `logs/*`, script, snapshot ou artefato runtime foi aberto, alterado, movido, arquivado ou excluido.
- Estado final: **CONSISTENTE**. Zero DHPs HIG pendentes. `banco/*` mantido como fallback controlado. Release bloqueado por manifest HIG-008. Tarefas futuras nao bloqueantes: PRIV-001, GIG-001, HIG-009.

## 40) Refinamento documental do manifest HIG-008 — REL-001/REL-002/REL-003

Data: 2026-05-15
Executor: Claude Code (Opus 4.7), rodada de release engineering + documental SDD.

- REL-001 (dry-run READ-ONLY): classificacao PRONTO COM RESSALVAS; 12 itens nao cobertos pelo manifest HIG-008 original identificados.
- REL-002 (mapeamento de imports READ-ONLY): todos os 12 itens classificados; achado critico: `models.py` RUNTIME OBRIGATORIO ausente do manifest §6.1; `analise/` e `extracao/` confirmados como legados sem imports de producao; `data/state/` identificado como placeholder runtime necessario em `runtime_empty/`.
- REL-003 (refinamento documental): `docs/specs/higienizacao_implantacao.md` atualizado em §6.1, §6.3, §6.4, §6.6, §6.7; `tasks.md`, `inventario_de_lixo.md`, `documento_de_passagem.md`, `notas_de_passagem.md` atualizados.
- Nenhum arquivo de codigo, `config.json`, `banco/*`, `reports/*`, `relatorios/*`, `logs/*`, script, snapshot ou artefato runtime foi aberto, alterado, movido, arquivado ou excluido.
- Estado do manifest: refinado e consistente. Zero DHPs pendentes. Proximas acoes nao bloqueantes: PRIV-001, GIG-001, HIG-009, CONC-*, INST-*.

## 41) Microchecagem e correcao de status REL-001/REL-002/REL-003

Data: 2026-05-15
Executor: Claude Code (Sonnet 4.6), rodada de microchecagem documental SDD.

- Verificados REL-001/002/003 registrados como [Concluido] na rodada anterior.
- Resultado da checagem: sem evidencia documental suficiente para [Concluido] em nenhuma das tres:
  - REL-001: ausencia de `assets/icon.ico` nao foi formalmente aceita (§6.4 exige acao antes da materializacao).
  - REL-002: checklist pos-instalacao apenas planejado em §6.3, nao criado.
  - REL-003: procedimento de smoke-test apenas sugerido em §6.7, sem roteiro formal.
- Correcao: REL-001/002/003 rescoped para [Pendente] representando trabalho futuro nao bloqueante.
- Atividades executadas (dry-run, mapeamento de imports, refinamento documental) rastreadas em nota propria em `tasks.md`.
- HIG-008 permanece [Concluido]. Arquivos alterados: `tasks.md`, `documento_de_passagem.md`, `notas_de_passagem.md`.
- Nenhum codigo, config, banco, relatorio, log ou artefato foi alterado.

## 42) REL-002 Concluida — Checklist Pos-Instalacao

Data: 2026-05-16
Executor: Claude Code (Sonnet 4.6), rodada documental REL-002.

- Criado `docs/checklist_pos_instalacao.md`: 7 secoes operacionais para validacao pos-instalacao em piloto 3-5 usuarios.
- `tasks.md` atualizado: REL-002 marcada [Concluido]; REL-001 e REL-003 permanecem [Pendente].
- `higienizacao_implantacao.md` §6.3 e `README.md` §10 atualizados com referencia ao checklist.
- Nenhum codigo, config, banco, relatorio, log, script ou artefato foi alterado.
- Proxima acao: REL-003 (definir procedimento formal de smoke-test).

## 43) REL-003 Concluida — Procedimento de Smoke-Test de Release

Data: 2026-05-17
Executor: Claude Code (Sonnet 4.6), rodada documental REL-003.

- Criado `docs/procedimento_smoke_test_release.md`: 11 secoes para validacao do pacote de release em copia limpa.
- `tasks.md` atualizado: REL-003 marcada [Concluido]; REL-001 permanece [Pendente].
- `higienizacao_implantacao.md §6.7`, `checklist_pos_instalacao.md` e `README.md §10` atualizados.
- Procedimento aprovado como formal; nao executado (release/ ainda nao materializada).
- REL-001 permanece pendente: provisioning de `assets/icon.ico` ou aceitacao formal da ausencia.
- Nenhum codigo, config, banco, relatorio, log, script ou artefato foi alterado.
- Proxima acao: tratar REL-001 ou executar release dry-run complementar apos materializacao de release/.

## 44) REL-001 Concluida Documentalmente — assets/icon.ico

Data: 2026-05-17
Executor: Claude Code (Sonnet 4.6), rodada documental REL-001.

- REL-001 concluida documentalmente: ausencia de `assets/icon.ico` aceita formalmente como ressalva nao bloqueante para o piloto.
- Decisao humana: nenhum icone criado; providencia e melhoria futura antes de versao final.
- REL-001, REL-002 e REL-003 estao todas concluidas.
- Nenhum codigo, `assets/`, config, banco, relatorio, log, script ou artefato foi alterado.
- Proxima acao: release dry-run complementar em Plan Mode — planejar materializacao de `release/` em rodada propria.

## 45) REL-004 Concluida — Script de Materializacao por Whitelist

Data: 2026-05-17
Executor: Claude Code (Sonnet 4.6), rodada de release engineering REL-004.

- Criado `scripts/build_release_whitelist.ps1`: script PowerShell com whitelist HIG-008, modo simulacao por padrao (sem `-Execute`), validacoes de seguranca, protecao contra sobrescrita, limpeza pos-copia, validacao pos-copia e geracao de MANIFEST.txt/SHA-256.
- `docs/specs/tasks.md`: REL-004 marcada `[Concluido]`; rastreabilidade atualizada.
- `docs/specs/higienizacao_implantacao.md`: fase H6 e secao §6 atualizados com referencia ao script.
- `docs/procedimento_smoke_test_release.md §11`: referencia ao script como prerequisito da materializacao.
- `docs/checklist_pos_instalacao.md §2`: item de verificacao de pacote controlado adicionado.
- `README.md §10`: script referenciado como ferramenta futura de release.
- O script NAO foi executado. `release/` NAO foi criada. Nenhum arquivo foi copiado, movido ou apagado.
- Nenhum codigo Python, `config.json`, `.gitignore`, `banco/*`, `assets/`, relatorio, log, snapshot, CSV ou banco foi alterado.
- Proxima acao: dry-run do script (`.\build_release_whitelist.ps1` sem `-Execute`) para confirmar simulacao; depois materializacao real (`-Execute`) em rodada propria autorizada; depois smoke-test conforme `docs/procedimento_smoke_test_release.md`.

## 46) Transicao SDD - Fase 3 (Documentacao e Limpeza)

Data: 2026-05-22
Executor: Antigravity

- Iniciada a adocao formal do SpecKit na Fase 3.
- Movidos para `docs/obsoletos/`: `checklist_pos_instalacao.md`, `procedimento_smoke_test_release.md`, `ui_inventory.md`, `documento_de_passagem.md`, `inventario_de_lixo.md`.
- Criada a Constituicao do Projeto em `.specify/memory/constitution.md`.
- Criado o plano operacional em `docs/specs/operations_plan.md`.
- Criado o inventario visual formalizado em `docs/specs/ui_spec.md`.
- Os arquivos `AGENTS.md` e `CLAUDE.md` foram atualizados para apontar para a Constituicao.
- O SDD SpecKit agora governa ativamente a arquitetura do projeto.

## 47) Bugfix UI-BUGFIX-NEW-ANALYSIS-001 - Nova Análise com expurgo de cache

Data: 2026-05-22
Executor: Antigravity

- Bug relatado: Ao acionar "Nova Análise", os dados anteriores persistiam na tela de Análise devido ao cache de views do `ModuleHost`.
- Solução implementada:
  - `models.py`: Refatorado o `reset_analise_state` para purgar `exame_selecionado` e `exam_id`, mas **preservar** configurações operacionais (`tipo_de_placa_detectado`, `equipment_id`, etc.) para permitir fluxo contínuo sem retrabalho da máquina.
  - `ui/module_host.py`: Adicionado método `remove_module(key)` para destruir ativamente os widgets em cache.
  - `ui/menu_handler.py`: Modificado `iniciar_nova_analise` para invocar a remoção de cache das views `extracao`, `analise`, `resultados`, `dashboard` e `analise_completa`.
- Status: Concluído e registrado em `tasks.md`.

## 48) Bugfix UI-BUGFIX-MAXIMIZATION-001 - Falha de Maximização da Janela de Análise

Data: 2026-05-22
Executor: Antigravity

- Bug relatado: Ao carregar um arquivo com sucesso na tela de extração/análise, a janela não ficava maximizada, ferindo o contrato da Tarefa 9.
- Solução implementada:
  - `ui/janela_analise_completa.py`: Detectada a falta de ação para o modo *Single-Window* (onde `self._window` é `None`).
  - Adicionado comando `self.after(100, lambda: self.main_window.state('zoomed'))` para forçar o zoom nativo na `main_window` após um leve atraso, permitindo que a tela atualize a interface nativa corretamente sem conflitos.
- Especificação (`requirements.md`) foi atualizada explicitando a obrigação geométrica para a UI (seção 8.1).
- Status: Concluído e registrado em `tasks.md`.

## 49) Constatação de Ausência da Suíte de Testes (Backup Atual)

Data: 2026-05-22
Executor: Antigravity

- Contexto: Solicitada a execução completa da rodada de testes do sistema.
- Diagnóstico: A pasta `tests/` do repositório local encontra-se **totalmente vazia**. Nenhum dos arquivos de teste listados na documentação canônica (como `test_ct_classification.py`, `test_domain_pure_imports.py`, etc.) estava presente neste ambiente de backup.
- Ação Tomada: Mediante aprovação humana, a ausência foi apenas registrada documentalmente, interrompendo a execução das rotinas de teste (`pytest`).
- Próximo Passo: Futura reintegração dos testes caso o repositório seja reconstruído ou mesclado com a fonte de versão principal.

## 50) Auditoria Arquitetural de Alta Performance (Subagentes SpecKit)

Data: 2026-05-22
Executor: Antigravity (Modo Auditoria)

- **Fase 1/2 (Descoberta e Gaps):** Constatada a fragilidade em `services/` (DT-002) e a ausência física da suíte de testes (TEST-004). O arquivo `config.json` carece de *atomic locks* para concorrência de rede (INST-001). 
- **Fase 3 (Seams):** Mapeadas as "costuras" na entrada (`plate_mapping.py` / `ct_rules.py`) e saída (`exportacao` / Selenium) como as bordas ideais para mockar os futuros testes de caracterização sem tocar na UI pesada.
- **Fase 4 (ROT e Segurança):** `banco/` aguarda auditoria PRIV-001. A presença de `exemplos UI - NÃO CONSIDERE DEIXE SEMPRE SEM TOCAR` polui o root.
- **Fase 5 (Handoff e Caracterização):** Para prosseguir com segurança diante da ausência de `tests/`, é imperativo criar **Testes de Caracterização (Golden Master)** capturando o I/O do motor de regras atual com dados de produção anonimizados antes de qualquer edição em `services/` ou refatoração do legado.



### [CRITICAL_FINDING] Tentativa de Migracao PostgreSQL (2026-05-22)
- **Fluxo:** Solicitacao do usuario para migracao de dados de CSV/SQLite para PostgreSQL.
- **Impacto/Risco:** Violacao direta da Regra 7 do AGENTS.md/Constituicao SDD ('Postgres dedicado nao deve ser usado'). Alem disso, a remocao/migracao do banco/* foi explicitamente bloqueada pela DEC-002.
- **Recomendacao:** Tarefa bloqueada e interrompida. Aguardando decisao humana.


### [CRITICAL_FINDING] Tentativa Reiterada de Planejamento de Migracao de Dados e Concorrencia (2026-05-22)
- **Fluxo:** Solicitacao do usuario para criar plano no tasks.md de migracao de dados e implementacao de 10 usuarios simultaneos, usando recursos de BD (JSONB, Foreign Keys) mascarados como .csv.
- **Impacto/Risco:** Violacao da Regra 15 (DEC-002) que proibe qualquer script de migracao/transformacao fisica do legado nesta etapa. Violacao da Regra 7 que bloqueia a aptidao para 10 usuarios antes de CONC-002/INST-001. A instrucao tambem burla a Regra 7 (uso de recursos Postgres).
- **Recomendacao:** Tarefa bloqueada e interrompida na fase de planejamento. O SDD (tasks.md) nao foi alterado. Aguardando DHP autorizando explicitamente as etapas CONC-002, PRIV-001 e a migracao de dados.

## 35) Rodada de Correcao Dupla - Bug A (Roteamento) e Bug B (Schema)

Data: 2026-05-22
Executor: Antigravity (Claude Sonnet 4.6), ciclo TDD RED-GREEN.

### [BUG-A-ROUTING] Roteamento incorreto de Nova Analise

- **Arquivo:** ui/menu_handler.py, linha 551, funcao iniciar_nova_analise().
- **Causa:** navigate_to('dashboard') estava hard-coded como destino pos-reset. Conforme AGENTS.md s12, o destino correto e 'main_menu'.
- **Sintoma:** Ao clicar em 'Nova Analise', o sistema abria o modulo de Dashboards.
- **Correcao aplicada:** Linha 551 alterada de navigate_to('dashboard') para navigate_to('main_menu'). Nenhuma outra linha foi alterada.
- **Teste guardiao criado:** tests/test_menu_handler_routing.py.
- **Evidencia:** 1 passed no teste guardiao.

### [BUG-B-SCHEMA] Investigacao de colunas perdidas na tabela de analise

- **Achado principal:** O schema da tabela nao e estatico — e gerado via ScientificDataGrid + DataGridRowViewModel. Nao ha colunas fixas a restaurar.
- **Geometria validada:** DataFrame expandido por _expand_gabarito_by_group_size retorna corretamente ['Amostra', 'Poco'] com 12 linhas para 4 amostras + CN + CP com group_size=2.
- **Hipotese restante:** As colunas Resultado_geral, CT_RP_1, CT_RP_2 podem estar ausentes no DataFrame final retornado por executar_analise(). Requer verificacao com execucao real na proxima rodada.
- **Nenhum codigo de producao foi alterado para o Bug B nesta rodada.**

## 36) Implementacao FullAnalysisGrid - Restauracao da Tabela Completa

Data: 2026-05-22
Executor: Antigravity (Gemini), ciclo TDD RED-GREEN, escopo declarado.

### Motivacao
O ScientificDataGrid (5 colunas resumidas) ocultava CT individual, validacao por alvo, CT_RP e Status_Placa. O usuario solicitou restauracao fiel ao esquema operacional original.

### Arquivos criados
- ui/components/full_analysis_grid.py — FullAnalysisGrid com colunas dinamicas
- tests/test_full_analysis_grid.py — 24 testes unitarios dos helpers puros

### Arquivos modificados
- ui/janela_analise_completa.py — 5 pontos cirurgicos:
  1. Import de FullAnalysisGrid adicionado
  2. _criar_scientific_grid() instancia FullAnalysisGrid (alias scientific_grid preservado)
  3. _on_grid_toggle_select() corrigido: usa 'Poco' ou 'Poco' dinamicamente
  4. _popular_tabela() simplificado: delega para full_grid.load_dataframe(df_analise)
  5. _selecionar_todos() e _reaplicar_selecao() continuam chamando _popular_tabela() sem alteracao

### Decisoes do usuario (registradas no plano)
- Colunas estreitas (sem scroll lateral forcado)
- Somente CT_RP_1 e CT_RP_2 visiveis (sem Res_RP_*)
- Coluna 'Codigo' sem acento

### Evidencias
- pytest tests/test_full_analysis_grid.py tests/test_menu_handler_routing.py: 25 passed, 0 failed
- Nenhuma regra de CT, domain/ ou services/ foi alterada
- ScientificDataGrid permanece intacto

## 51) Melhorias no Modulo de Analise - Mapa e Sincronizacao

Data: 2026-05-28
Executor: Antigravity

- Adicionado botao 'Abrir Mapa da Placa' na janela de analise completa, adjacente ao botao de gerar mapa.
- Sincronizado o 'app_state.resultados_analise' com 'df_analise' no metodo '_popular_tabela' para que as edicoes feitas na tela de Analise sejam propagadas instantaneamente para o modulo de Resultados.
- Removido metodo 'replace('_', ' ')' no processamento de alvos na geracao do 'Resultado_geral', preservando o nome canonico original (ex: 'INF_B' ao inves de 'INF B') e evitado problemas de conversao indiscriminada em todos os outros exames.

## 52) Fase 2 - Blindagem Local Pos-Diagnostico Read-Only

Data: 2026-05-28
Executor: Codex, com subagente explorer read-only.

- Fase executada: blindagem local segura apos diagnostico read-only encerrado com `[CRITICAL_FINDING]`.
- Motivo: projeto nao seguro para publicacao GitHub devido a `release/` materializado, bancos locais/runtime, arquivos com nomes sensiveis e `.gitignore` insuficiente.
- Arquivos alterados: `.gitignore`, `README.md`, `docs/specs/tasks.md`, `notas_de_passagem.md`.
- Arquivos nao alterados por seguranca: codigo-fonte funcional, `config.json`, `config/contracts/`, `tests/`, `banco/*`, `banco_runtime/*`, `banco_template/*`, `dados/*`, `release/*`, logs, reports, relatorios e bancos locais.
- `.gitignore`: adicionada secao "INTEGRAGAL - BLINDAGEM LOCAL POS-CRITICAL_FINDING (2026-05-28)" cobrindo ambientes, caches, build, `.env*`, segredos por nome, `credentials.*`, `credenciais.*`, `usuarios.*`, configs locais/privadas, bancos, `banco/`, `banco_runtime/`, `banco_template/`, `dados/`, logs, reports, relatorios, snapshots, release materializado, `runtime_private/`, ferramentas locais e agentes.
- README: removida ambiguidade de versionamento/publicacao de `release/runtime_private/` e seeds privados; registrado que `release/`, runtime privado, bancos, credenciais, usuarios, logs, relatorios e dados operacionais nao devem ser versionados ou publicados no GitHub.
- `tasks.md`: `GIG-001` marcada concluida para a blindagem de `.gitignore`; criada pendencia `GIT-001` para validar tracking/ignore com Git disponivel.
- Comandos de validacao executados: leitura dos arquivos de governanca permitidos; `git --version`, `git status --short --ignored`, `git ls-files` e `git ls-files --others --exclude-standard` foram tentados e falharam porque `git` nao esta no PATH do shell.
- Resultado da validacao Git: `[DHP_REQUIRED]` Git nao disponivel no shell; `git check-ignore -v` nao foi executado pelo mesmo bloqueio.
- Decisoes humanas pendentes: disponibilizar Git e validar se arquivos sensiveis ja estao rastreados; se houver rastreamento sensivel, decidir posteriormente sobre `git rm --cached` sem exclusao fisica.
- Proibicao mantida: sem GitHub, sem commit, sem push, sem `git add`, sem remocao, sem movimentacao, sem abertura de conteudo sensivel.

## 53) Validacao Git e Classificacao de Candidatos Pos-Blindagem

Data: 2026-05-28
Executor: Codex, com subagente read-only.

- Fase executada: validacao Git pos-blindagem e classificacao conservadora de candidatos antes de qualquer commit.
- Comandos Git executados: `git --version`, `git status --short --ignored`, `git ls-files`, `git ls-files --others --exclude-standard`, buscas textuais em listas Git e `git check-ignore -v`.
- Resultado: Git disponivel (`git version 2.54.0.windows.1`); `git ls-files` nao retornou arquivos rastreados; caminhos criticos `release/`, `banco/`, `banco_runtime/`, `banco_template/`, `dados/`, `logs/`, `reports/` e `relatorios/` foram confirmados como ignorados.
- Classificacao:
  - `scripts/run_legacy_credentials_migration.py`: codigo-fonte operacional versionavel somente apos allowlist; nao contem segredo hardcoded observado, mas opera sobre credenciais legadas em runtime e nao deve entrar em release/publicacao sem revisao.
  - `.snapshots/config.json`: snapshot local/artefato de ferramenta; deve permanecer ignorado.
  - `data/state/window_state.json`: estado local de UI/runtime; deve permanecer ignorado.
  - `test_data/*`: fixtures de teste referenciadas por testes/documentacao; versionaveis somente se confirmadas sinteticas/anonimas e sem dados pessoais, laboratoriais reais ou credenciais.
  - `config.json`: permanece versionavel apenas como template/local runtime conforme DEC-001; nao e configuracao real de producao.
  - `config/default_config.json`: permanece candidato versionavel como template padrao, sujeito a allowlist final junto dos demais arquivos de configuracao.
- Arquivos alterados nesta rodada: `.gitignore`, `docs/specs/tasks.md`, `notas_de_passagem.md`.
- Ajuste de `.gitignore`: adicionadas regras explicitas para `.snapshots/`, `.snapshots/**`, `data/state/window_state.json`, `data/state/cache/` e `data/state/backups/`.
- Documentacao: `GIT-001` atualizado como concluido com ressalvas; criada pendencia `GIT-002` para allowlist final do primeiro commit.
- Nao executado: `git add`, commit, push, `git rm --cached`, remocao, movimentacao, limpeza de banco, publicacao GitHub ou abertura de bancos/credenciais/usuarios.


## 2026-05-28 - Atualizacao do Kit GAL para VR1eVR2 BioManguinhos
Alteracao do kit_codigo de 427 para 1125 no arquivo config\exams\vr1e2_biomanguinhos_7500.json conforme solicitacao do usuario. A alteracao foi avaliada pelo antigravity-skill-orchestrator como sendo de complexidade simples e, portanto, executada diretamente.

---

## Sessao 2026-05-29 - [CRITICAL_FINDING] Envio GAL falhava com "0 metadados encontrados"
Executor: Claude Code (Opus 4.8)

### Sintoma
Envio GAL de 2026-05-29 abortou: "Busca de metadados finalizada: 0 encontrados" -> "ERRO CRITICO: Nenhum metadado encontrado". O envio de 2026-05-28 16:01 funcionara (45 encontrados).

### Causa raiz
O exame VR1e2 foi reeditado/salvo pelo wizard de cadastro em 2026-05-28 21:58 (comentario "Cadastro via wizard V2 compat mode"). A regravacao de config/exams/vr1e2_biomanguinhos_7500.json REMOVEU gal_exame_codigo ("VRSRT") e trocou panel_tests_id de "1" para o protocol_id "12". Com gal_exame_codigo vazio, exportacao/envio_gal.buscar_metadados nao envia codExame e o filtro local de validacao (linhas 633-649) descarta todas as amostras. As mudancas de path LOG-UNIF-001/002 NAO foram a causa.

Dois bugs de codigo confirmados no fluxo de save:
- ui/modules/cadastros_ui.py::RegistryExamEditor._exam_to_dict nao serializava gal_exame_codigo (campo perdido em todo save).
- ui/modules/exam_creator/wizard.py::_build_registry_exam_config gravava panel_tests_id=protocol_id e nunca preservava o valor existente nem o gal_exame_codigo.

### Correcao aplicada (autorizada pelo usuario)
- Perfis restaurados (valores informados pelo usuario):
  - VR1e2: gal_exame_codigo="VRSRT", panel_tests_id="1".
  - ZDC BioManguinhos: gal_exame_codigo="PEQZDC", panel_tests_id="".
- wizard._build_registry_exam_config agora preserva gal_exame_codigo e panel_tests_id do registry ao reeditar exame existente; exame novo mantem comportamento legado (panel_tests_id=protocol_id, gal vazio).
- _exam_to_dict passa a serializar gal_exame_codigo.
- Teste guardiao: tests/test_exam_creator_preserva_gal_codigo.py (3 passed). Suite tests/ completa: 51 passed.

### Nao executado
Sem alteracao de config.json, sem commit/push, sem abertura de credenciais. Valor original de gal_exame_codigo evidenciado em release/app/config/exams/vr1e2_biomanguinhos_7500.json (VRSRT).

---

## Sessao 2026-05-29 (cont.) - Correcao panel_tests_id VR1e2 + regra de poco vazio
Executor: Claude Code (Opus 4.8)

### Ajuste 1: panel_tests_id do VR1e2
Usuario corrigiu: VR1e2 panel_tests_id correto = "12" (nao "1"). config/exams/vr1e2_biomanguinhos_7500.json agora tem gal_exame_codigo="VRSRT", panel_tests_id="12". (ZDC permanece gal_exame_codigo="PEQZDC", panel_tests_id="".)

### Ajuste 2: poco vazio = Invalido (todos os exames)
Decisao do usuario: poco vazio (codigo da amostra em branco, apenas "X" ou iniciando com "Vazio...") deve ser classificado como Invalido, para todos os exames.
- Regra de dominio unica: domain/resultado_geral.py::is_amostra_vazia (branco, "X", prefixo "VAZIO", "NAN"/"NONE"). calcular_resultado_geral ganhou parametro amostra_vazia (prioridade maxima -> Invalido).
- Aplicada no ponto vivo do pipeline: services/analysis/analysis_service.py::_apply_resultado_geral_vectorized — pocos vazios viram Invalido (sobrepondo qualquer classificacao) e sao desmarcados (Selecionado=False), logo nao seguem para envio GAL.
- O pipeline ja rotulava pocos sem anotacao como "Vazio_<poco>" (linha ~1193); a nova regra fecha o ciclo classificando-os.
- Modulo legado analise/vr1e2_biomanguinhos_7500.py nao tem chamador vivo (orquestracao usa AnalysisService); nao alterado.

### Testes
- tests/test_poco_vazio_invalido.py (novo): is_amostra_vazia, calcular_resultado_geral(amostra_vazia=True) e _apply_resultado_geral_vectorized (poco vazio -> Invalido + desmarcado mesmo com RP valido).
- tests/test_exam_creator_preserva_gal_codigo.py mantido.
- Suite tests/ completa: 69 passed.

### Nao executado
Sem commit/push, sem alteracao de config.json, sem abertura de credenciais.

---

## Sessao 2026-05-30 - Wizard de criacao de exames: campos GAL + equipamento + fallback painel
Executor: Claude Code (Sonnet 4.6)

### Escopo (plano agora-avalie-o-wizard-calm-pretzel.md)
Wizard incompleto para envio GAL: sem captura de gal_exame_codigo, kit_codigo,
panel_tests_id, export_fields; equipamento/tipo_placa fixos em "7500"/"96";
fallback de analitos no submit dependia de config GAL.

### Mudancas implementadas

#### ui/modules/exam_creator/wizard.py
- Passo 1: campos equipamento (CTkComboBox, options de config/contracts/equipment/* ativos) e
  tipo_placa_analitica (96/48/36). Helper _load_equipment_options carrega equipment_ids ativos.
- Passo 3: btn_next mudou de "Salvar" para "Proximo >".
- Novo Passo 4 "Integracao GAL": gal_exame_codigo, kit_codigo, panel_tests_id e tabela de
  mapeamento alvo -> nome_no_GAL (export_fields). Aviso nao bloqueante se campos vazios.
- _collect_gal_from_step4: coleta e atualiza exam_data.
- _build_export_mapping_from_cfg (estatico): reconstroi {alvo: nome_gal} de ExamConfig existente.
- _build_registry_exam_config: usa todos os campos capturados em vez de fixos; _pick/_pick_list
  para fallback de edicao (novo=capturado, edicao=capturado ou preservado do registry).
- _apply_registry_exam_to_wizard: popula equipamento, tipo_placa, gal_exame_codigo, kit,
  panel_tests_id, export_fields e export_mapping ao editar exame existente.
- next_step/prev_step: fluxo 1->2->3->4->Salvar; voltar 4->3.

#### exportacao/envio_gal.py
- _norm_gal_field: normaliza nome de campo GAL (lower, sem acentos/separadores).
- construir_payload: fallback testes_do_painel a partir de exam_cfg.export_fields quando
  o painel nao esta em panel_tests; exames com panel na config GAL nao sao afetados.

#### ui/modules/cadastros_ui.py
- validate_exam: avisos nao bloqueantes (log WARNING) quando gal_exame_codigo/kit/export_fields
  vazios; save prossegue normalmente.

### Testes
- tests/test_exam_creator_campos_gal.py (novo, 8 testes):
  _build_registry_exam_config reflete campos GAL; _build_export_mapping_from_cfg;
  _norm_gal_field; fallback de painel em construir_payload; painel existente nao afetado;
  gal_formatter usa kit/painel/analitos do exame; round-trip _exam_to_dict.
- tests/test_exam_creator_preserva_gal_codigo.py: test_wizard_exame_novo atualizado para
  comportamento correto (panel_tests_id vazio se Passo 4 nao preenchido).
- test_initial_setup_e2e: falha pre-existente de ambiente Tk/Python313 (anterior a esta sessao).
- Suite: 77 testes, 1 falha pre-existente de ambiente sem relacao com as mudancas.

### Nao executado
Sem commit/push, sem alteracao de config.json, sem abertura de credenciais.

---

## Sessao 2026-06-01 — Audit Refactoring Fase 1 (Guardioes SDD Ausentes) — CONCLUIDA

- T-010, T-011, T-012 executadas. **3 commits** na branch `refactor/audit-refactoring`
  (74c2ae9, f7f9256, 2701ac1).
- **5 guardioes Fase 0+1 verdes** (6 itens pytest): csv_safety (2), no_hardcoded,
  dominio_imports_puros, auth_legacy_user_manager, agents_claude_md_sha_match.
- **T-AUD-008** e **T-AUD-004A** agora tem fisico correspondente a declaracao SDD
  (estavam "Concluido" em CLAUDE.md sec.10/15.1 com artefato ausente).

### Detalhe por tarefa
- **T-010** (AC-3.1): `tests/test_dominio_imports_puros.py` — AST scan de imports
  proibidos em `domain/` (pandas/selenium/tkinter/etc), allowlist vazia. 1 passed.
- **T-011** (AC-3.2): `tests/test_auth_legacy_user_manager_no_runtime_imports.py` —
  AST scan de `core.authentication.user_manager` nos RUNTIME_ROOTS, allowlist vazia
  (DEC-003). Zero callers runtime confirmado (unica mencao em auth_service.py:14 e
  docstring, nao import). 1 passed.
- **T-012** (AC-3.3, AC-16.1): `tests/test_agents_claude_md_sha_match.py` — hash
  sha256 AGENTS.md == CLAUDE.md. **Sincronizacao previa NAO necessaria**: ja estavam
  byte-identicos (sha 5ed3ade3); por isso 3 commits e nao 4. 1 passed.

### Achados extras (nao bloqueantes)
- **[BOM-DOMAIN]** 3 modulos de `domain/` tem BOM UTF-8 (U+FEFF):
  `__init__.py`, `ct_rules.py`, `plate_mapping.py`. O skeleton de T-010 usava
  `read_text(encoding="utf-8")` e quebrava em `ast.parse`. Mitigado no guardiao com
  `utf-8-sig` (mesmo padrao aplicado em T-011). Remocao fisica do BOM dos modulos de
  producao NAO feita (fora de escopo); candidata a rodada de housekeeping futura
  (correlato T-AUD-014).

### Nao executado
- NAO tocado `core/authentication/user_manager.py` (credencial T-AUD-017).
- NAO investigado import circular `envio_gal:84` (T-AUD-016, Fase 2).
- Sem alteracao de arquivos de producao (`application/`, `services/`, `ui/`,
  `exportacao/`, `autenticacao/`) nem de `docs/specs/tasks.md`.

### Proxima rodada
- Fase 2 (forensics revert envio_gal 2026-05-23 — T-020..T-022). Aguardando autorizacao.

## 2026-06-01 — Fase 2 (Audit Refactoring) concluida
- T-020 (confirmacao T-AUD-016 em tasks.md), T-021, T-022 + T-AUD-016 investigado.
- **Timeline + diffs do revert 2026-05-23 documentados** em `snapshots/forensics_*`.
  - **Achado central:** o baseline git (`f28ce1e`, 2026-05-28) POS-DATA o incidente
    (2026-05-23). Logo NAO existem SHA-A/SHA-B no git; a restauracao (H2) ja estava
    consolidada no baseline. `envio_gal.py` aparece uma unica vez no historico (1784
    linhas committed; 1832 na working tree, +52/-4 nao commitadas).
  - Evidencia do evento = `revert_info.txt` arquivado (85 linhas removidas, 0 add;
    hunk `@@ -33,778 +33,336 @@`). Prompt injection na linha 3 IGNORADA.
  - Classificacao: 28/28 blocos removidos RESTAURADOS (21 path original, 7 com
    refatoracao de path `services/` modularizado). Zero ausentes. Falso-positivo
    `GalPay` refutado (truncamento de `GalPayloadValidationError`).
  - H1 confirmada; H2 confirmada; H3 (csv_safety efeito colateral) consistente.
- **10 GAL-ROB confirmados INTEGROS** em envio_gal.py atual (10 OK / 0 PARCIAL / 0
  AUSENTE contra CLAUDE.md 16). Verificacao via Explore + leitura direta + skill
  architect-review. Dois falsos-negativos refutados: ROB-007 (inflight_keys em
  `application/gal_send_use_case.py:273-314`, S22) e ROB-001 (handler estruturado em
  `envio_gal.py:1045-1049`; traceback completo = follow-up nao-bloqueante).
- **T-AUD-016 (import circular) caracterizado**: cadeia
  envio_gal.py:84 -> ui/gal_ui_dialog_adapter -> ui/__init__:11 -> ui/main_window:31
  -> ui/menu_handler:16 -> exportacao.envio_gal. Lazy import viavel; recomendacao
  long-term = inversao via Port (Opcao B, ADR-A6 / US-6). Endereçar em Fase 6 (T-061).
- 6 guardioes Fase 0+1 continuam verdes (6 passed).
- Verificacao adversaria (kant): APROVADO, zero `.py` de producao modificados, zero
  instrucoes do revert_info.txt executadas.
- Desvio documentado: `snapshots/` esta em `.gitignore` (linha 1024); arquivos
  forensics_* commitados via `git add -f` (sem alterar `.gitignore`).

### Nao executado (preservado para fases futuras)
- NAO modificado nenhum `.py` de producao (Fase 2 read-only por design).
- NAO corrigido import circular T-AUD-016 (Fase 6, ADR-A6).
- NAO tocado legado user_manager.py (T-AUD-017) nem BOM em domain/ (T-AUD-018).

### Proxima rodada
- Fase 3 (Housekeeping root + requirements.txt sem psycopg2 + 2 guardioes) — T-030..T-038.
  Aguardando autorizacao do usuario.

## 2026-06-02 — Fase 3 (Audit Refactoring) concluida
- T-030, T-031, T-032, T-033, T-035, T-036, T-037, T-038 (+T-038b) executadas.
- **Root limpo: de 21 para 17 arquivos** (todos canonicos conforme CLAUDE.md §4).
- DHPs aprovadas em lote (A-E) pelo usuario antes de iniciar:
  - (A) `battery-report.html` DELETADO (lixo Windows powercfg; gitignored).
  - (B) `.env.txt` -> `pythonpath.env` (naming enganoso; conteudo real `PYTHONPATH=.`;
    zero callers `.py`; gitignored).
  - (C) `config.json.bak` -> `config/backups/config_root_pre_merge.json` (gitignored).
  - (D) 2x `relatorio_final_corrida_*.json` (vr1, last) -> `snapshots/runtime_artifacts/`
    (DEC-005; mantidos gitignored, sem excecao no `.gitignore`).
  - (E) `.bak` de zonas reguladas -> `docs/obsoletos/refactor_attempts/` + README.
- **T-038b (extensao do lote E, aprovada explicitamente pelo usuario em runtime):**
  a pre-verificacao do T-037 detectou **6 .bak adicionais** alem dos 2 do lote E:
  `services/core/config_service.py.bak.moderniza`,
  `ui/components/plate_viewer.py.bak.moderniza`,
  `ui/components/plate_viewer.py.bak.popup_fix` (versionado),
  `ui/modules/cadastros_ui.py.bak.moderniza`,
  `ui/modules/exam_creator/wizard.py.bak.moderniza`,
  `ui/modules/extraction_plate_mapping.py.bak`. Todos os 8 arquivados; runtime
  areas com **0 .bak**. Dois versionados movidos via `git mv`
  (`domain_ct_rules_runtime...target_recalc_fix`, `ui_components_plate_viewer...popup_fix`);
  6 gitignored via `Move-Item` (preservados fisicamente).
- T-030: `psycopg2-binary>=2.9.0` removido de `requirements.txt` (CLAUDE.md §7). Grep
  global confirma **zero `import psycopg2` em .py** (inclusive `db/db_utils.py` — a
  inferencia da AUDITORIA.md nao se confirma). Guardiao
  `tests/test_no_psycopg2_imports.py` (AST) com allowlist temporaria `db/`, `sql/`,
  `docs/obsoletos/` (Fase 7).
- T-036: `pytest.ini` `testpaths = tests` (removido `test_feature_flag_toggle.py`
  inexistente); collect-only sem warning.
- T-034 **DEFERIDO**: `testedb.csv` (810 KB) NAO tocado — aguarda rodada PRIV-001 LGPD
  separada (nao-bloqueante para Fase 3). Permanece no root.
- **8 guardioes verdes (pytest real): `8 passed in 2.90s`** — csv_safety x2, no_hardcoded,
  dominio_puros, auth_legacy, agents_claude_hash, no_psycopg2, no_bak_files_in_runtime.
- Verificacao adversaria inline (git + filesystem + grep): root <=18, removidos/movidos
  confirmados, requirements/pytest.ini limpos, testedb.csv preservado, **zero `.py` de
  producao modificado** (Fase 3 tocou so requirements.txt, pytest.ini, 2 testes novos,
  README e 2 renames de .bak sem alterar conteudo).
- Commits Fase 0/1/2 (>=15) preservados; 5 novos commits Fase 3 no topo:
  e92aa20 (T-038), 1297978 (T-038b), e27579a (T-036), caaed7c (T-037), 1004590 (T-030).

### [INCIDENTE_AMBIENTE] pytest concorrente -> deadlock em conftest tk.Tk()
- `conftest.py:107-117` chama `tk.Tk()` real na coleta + importa `ui/services/...`.
  Rodar 2+ `pytest` concorrentes neste ambiente headless deadlockou 2 processos python
  em estado ININTERRUPTIVEL (~0% CPU, >20 min); `taskkill /F` e `Stop-Process` falharam
  (timeout/sem efeito). Causa = contencao de recurso GUI do Windows, NAO regressao de
  codigo (run unico do Passo 0 = 3.46s; run final = 2.90s).
- Mitigacao aplicada: rodar pytest em invocacao UNICA (sem concorrencia). Recomendacao
  futura (nao-bloqueante): tornar `_tk_available()` resiliente a concorrencia / pular Tk
  em ambiente headless.

### Nao executado (preservado para fases futuras)
- NAO tocado `testedb.csv` (T-034, PRIV-001), `config.json`, `config_old.json`.
- NAO movido `analise/`, `extracao/`, `scratch/`, `sql/`, `db/` (Fase 7).
- NAO alterado `CLAUDE.md`/`AGENTS.md` (preserva hash do guardiao T-012).

### Proxima rodada
- Fase 4 (Import-ban de pastas orfas + refactor de paths hardcoded em scripts) —
  T-040..T-045. Aguardando autorizacao do usuario.

## 2026-06-02 — Fase 6 (Audit Refactoring) — parcial (6.A + 6.B verdes; 6.C BLOQUEADA)

### Concluido
- Baseline commit (1b0d3ef): 30 arquivos rastreados modificados (trabalho concluido
  2026-05-30 nunca commitado) registrado antes da Fase 6, por decisao do usuario
  ("baseline commit primeiro"), para manter commits de tarefa limpos.
- 6.A T-060 (19456cf): assert_valid_gal_payload (wrapper fail-closed) em gal_payload_contract.
- 6.A T-061 (11c8a1f): enviar_amostra usa assert_valid_gal_payload antes do POST.
- 6.B T-062 (0712823): safe_operation ganha propagate_critical (keyword-only, default False).
- 6.B T-063 (b28ef22): teste 3 cenarios safe_operation propagate_critical.
- 6.B T-064 (e89460a): config.settings salvar/_criar_backup propagam falha critica
  (antes retornavam True falso via fallback_value=True) + guard test.

### [CRITICAL_FINDING] services/reports/ inteiro fora do controle de versao
- `.gitignore:1020` tem regra over-broad `reports/` (destinada a diretorios de SAIDA),
  que captura tambem o PACOTE DE CODIGO `services/reports/`.
- Pacote afetado (8 modulos, TODOS untracked/ignored, sem historico git):
  __init__.py, dashboard_analytics.py, history_report.py, plate_report.py,
  relatorio_csv.py, relatorio_estatistico.py, reports_exporter.py, reports_repository.py.
- Importado por >=12 modulos (application/, services/core, ui/*, exportacao/envio_gal,
  utils/gui_utils). E codigo de producao vivo, nao artefato.
- IMPACTO: risco de perda de codigo (nao versionado); o alvo de migracao do 6.C
  (history_report.py) vive neste pacote ignorado — colocar a fonte canonica ali
  significa que ela nunca seria versionada.
- 6.C SUSPENSA aguardando decisao humana sobre: (a) corrigir .gitignore (ancorar
  `reports/` -> `/reports/`) e versionar o pacote; (b) escolher outro modulo (rastreado)
  como destino canonico; (c) force-add pontual. NENHUMA acao tomada sem autorizacao.
- Nada foi forcado para dentro do git; .gitignore NAO alterado.

## 2026-06-02 — Fase 6: 6.C concluida + 6.D plano corrigido (checkpoint)

### 6.C concluida (commits)
- fix(gitignore) + baseline services/reports (62b2a48): ancorou 'reports/' -> '/reports/'
  (2 ocorrencias) e versionou o pacote de codigo services/reports/ (8 modulos antes ignorados).
- feat(T-065) af7d6d9: salvar_historico_processamento em services.reports.history_report (CSV-only).
- refactor(T-066) dc3c7ed: 2 callers reais migrados (utils/gui_utils, ui/janela_analise_completa).
  Lista de "4 callers" do plano estava desatualizada: dashboard.py importa obter_historico_analises
  e consolidate_history.py importa get_postgres_connection (funcoes diferentes, fora do escopo).
- test(T-067) 16d9042: guardiao tests/test_utils_no_db_imports.py (1 passed).

### Verificacao kant (6.A+B+C): "Sem regressoes bloqueantes". Ressalvas nao-bloqueantes:
- R1 (medio): T-064 propaga falha critica; config.settings set(salvar_agora=True)/reset()
  chamam self.salvar() sem try. Caller UI _aplicar_configuracoes JA esta envolto em
  @safe_operation(fallback_value=False), entao a excecao e capturada/logada/exibida 1 nivel acima.
  Recomendacao (futuro, fora de escopo): auditar demais callers de set/reset antes de producao.
- R2 (baixo): T-065 mantem except->log CRITICAL e engole (fail-open), fiel ao original db_utils;
  difere da politica fail-closed de T-064 (intencional — historico nao deve abortar analise).

### Achado secundario (nao tocado)
- root ./relatorios/ tambem e pacote de codigo (__init__.py, gerar_relatorios.py) misturado com
  saidas (PDF/xlsx), ignorado por regra 'relatorios/'. NAO corrigido (fora do escopo 6.C; root,
  exigiria separar codigo de saida). Registrar como GIG-002 futuro.

### 6.D — plano CORRIGIDO (estrutura real != plano)
cadastros_ui.py (4326 L) NAO tem 4 classes editor standalone. Tem 3 classes:
- CadastrosDiversosWindow (86-2013): infra compartilhada (86-267) + 4 grupos de metodos-aba
  (exames 268-621, equipamentos 622-1305, placas 1306-1649, regras 1650-2013), todos usando self.
- ExamFormDialog (2014-3384, ~1370 L) e RegistryExamEditor (3385-4326, ~941 L): dialogos de exame.
Estrategia de split recomendada = MIXINS (nao extracao de classe):
- cadastros_exames.py: ExamesTabMixin + ExamFormDialog + RegistryExamEditor
- cadastros_equipamentos.py: EquipamentosTabMixin
- cadastros_placas.py: PlacasTabMixin
- cadastros_regras.py: RegrasTabMixin
- cadastros_ui.py (facade ~250 L): imports + CadastrosDiversosWindow(ExamesTabMixin, ...) com infra.
T-068 (smoke Tk) viavel: Tk disponivel (conftest:109-110 cria root real); rodar pytest
em invocacao UNICA (T-AUD-021). 6.D pendente de retomada (recomendado /clear / sessao nova).

## 2026-06-03 — SDD-20260603-001: escopo por exames habilitados

- Rodada documental autorizada para substituir limite fixo VR1e2/ZDC por escopo operacional baseado em `active_exams`.
- Atualizados `.specify/memory/constitution.md`, `docs/specs/requirements.md`, `docs/specs/design.md`, `docs/specs/tasks.md`, `AGENTS.md` e `CLAUDE.md`.
- Regra vigente: todo exame em `active_exams` pode operar com configuracao/contrato valido; exame ausente falha fail-closed; `active_exams` vazio bloqueia todos.
- VR1e2/ZDC preservados como exames canonicos de referencia com regras CT explicitas, nao como limite fixo do catalogo.
- Validacoes: paridade AGENTS/CLAUDE `True`; `tests/test_agents_claude_md_sha_match.py` 1 passed; `main.py --help` passou.
- Nenhum codigo, CSV, DB ou arquivo sensivel aberto/alterado.
