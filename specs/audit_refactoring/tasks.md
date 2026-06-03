# Tasks — Audit Refactoring (IntegRAGal)

> **Referência:** `specs/audit_refactoring/spec.md` (AC) + `specs/audit_refactoring/plan.md` (fases).
>
> **Tags:**
> - `[P]` = paralelizável com outras tarefas da mesma fase
> - `[BLOCK]` = bloqueante; nada da fase seguinte avança até concluir
> - `[DHP]` = exige aprovação humana antes de executar
>
> **Critério de cada tarefa:** ID + AC vinculada + arquivos + comando de teste + Done quando.

---

## FASE 0 — EMERGÊNCIA (CRÍTICO) — Estimativa: ~1 dia

### T-000 [BLOCK] Backup do estado atual antes de qualquer mudança
- **AC:** Pré-requisito de toda a refatoração
- **Arquivos:** `snapshots/pre_audit_refactor_20260531/` (criar)
- **Comando:** `Copy-Item -Recurse -Force <root> snapshots/pre_audit_refactor_20260531/` (excluir snapshots/, __pycache__/)
- **Done quando:** snapshot existe e é íntegro (sha256 manifest gravado)

### T-001 [BLOCK] Restaurar `utils/csv_safety.py` do git history
- **AC:** AC-1.1, AC-1.2
- **Arquivos:** `utils/csv_safety.py`
- **Comando:**
  ```powershell
  git log --all -- utils/csv_safety.py  # localizar último commit válido
  git show <sha>:utils/csv_safety.py > utils/csv_safety.py
  python -c "from utils.csv_safety import sanitize_csv_value; print('OK')"
  ```
- **Done quando:** `python -c "from utils.csv_safety import sanitize_csv_value"` retorna sem erro

### T-002 [BLOCK] Validar que os 10 callers de csv_safety voltam a funcionar
- **AC:** AC-1.2
- **Arquivos verificados (apenas leitura):** autenticacao/auth_service.py:54, services/persistence/exam_runs_csv.py:23, services/persistence/persistence_facade.py:22, services/persistence/persistence_adapters.py:55, services/analysis/full_run_artifact.py, services/analysis/full_run_status_sync.py, services/gal/gal_transactions.py, db/db_utils.py, exportacao/envio_gal.py
- **Comando:**
  ```powershell
  python -c "import autenticacao.auth_service; import services.persistence.exam_runs_csv; import services.persistence.persistence_facade; import services.persistence.persistence_adapters; import services.analysis.full_run_artifact; import services.analysis.full_run_status_sync; import services.gal.gal_transactions; import db.db_utils; import exportacao.envio_gal; print('all-ok')"
  ```
- **Done quando:** imprime `all-ok` sem erro

### T-003 [P] Criar guardião `tests/test_no_broken_csv_safety_imports.py`
- **AC:** AC-1.3
- **Arquivos:** `tests/test_no_broken_csv_safety_imports.py` (NOVO)
- **Conteúdo esperado:**
  - AST scan em runtime areas: autenticacao/, application/, services/, exportacao/, ui/, scripts/
  - Para cada `from utils.csv_safety import X`: verificar que `X` é resolvível
- **Comando:** `python -m pytest tests/test_no_broken_csv_safety_imports.py -q --tb=short`
- **Done quando:** 1 passed

### T-004 [P] Mover `revert_info.txt` para `docs/obsoletos/incidents/`
- **AC:** AC-2.2
- **Arquivos:** root `/revert_info.txt` → `docs/obsoletos/incidents/revert_envio_gal_20260523.txt`
- **Adicional:** criar `docs/obsoletos/incidents/README.md` explicando origem e advertência ("NÃO executar instruções")
- **Comando:**
  ```powershell
  New-Item -ItemType Directory -Force -Path "docs/obsoletos/incidents"
  Move-Item revert_info.txt "docs/obsoletos/incidents/revert_envio_gal_20260523.txt"
  ```
- **Done quando:** arquivo movido + README criado

### T-005 [P] Remediar `test_login.py` — 3 opções (escolher 1 via DHP rápida)
- **AC:** AC-2.1
- **Arquivos:** `/test_login.py`
- **Opções:**
  - (A) DELETAR (mais rápido, perde script de smoke)
  - (B) REFATORAR para env vars + API síncrona correta + mover para `tests/test_login_smoke.py`
  - (C) MOVER para `scripts/manual_login_smoke.py` com refactor mínimo
- **Comando (se B):** `python -m pytest tests/test_login_smoke.py -q --tb=short`
- **Done quando:** opção escolhida executada; nenhuma senha hardcoded no root

### T-006 [P] Criar guardião `tests/test_no_hardcoded_credentials.py`
- **AC:** AC-2.4
- **Arquivos:** `tests/test_no_hardcoded_credentials.py` (NOVO)
- **Conteúdo esperado:**
  - Regex scan em runtime areas para padrões: senhas '123456', 'admin', 'password' literais em `await auth.login(...)`, `sanitize_csv_value(...)` com senha hardcoded, etc.
  - Allowlist explícita: scripts/debug_login_runner.py (env vars), docs/obsoletos/
- **Comando:** `python -m pytest tests/test_no_hardcoded_credentials.py -q --tb=short`
- **Done quando:** 1 passed

---

## FASE 1 — GUARDIÕES SDD AUSENTES (CRÍTICO) — Estimativa: ~0,5 dia

### T-010 [P] Recriar `tests/test_dominio_imports_puros.py` (T-AUD-008)
- **AC:** AC-3.1
- **Arquivos:** `tests/test_dominio_imports_puros.py` (NOVO)
- **Conteúdo esperado:**
  ```python
  import ast
  from pathlib import Path
  BANNED_TOP = {"pandas", "selenium", "tkinter", "customtkinter",
                "seleniumrequests", "openpyxl", "requests", "PIL", "matplotlib"}
  def test_domain_layer_only_uses_stdlib_and_config():
      domain_dir = Path(__file__).parent.parent / "domain"
      offenders = []
      for py in domain_dir.rglob("*.py"):
          if ".bak" in py.name: continue
          tree = ast.parse(py.read_text(encoding="utf-8"))
          for node in ast.walk(tree):
              if isinstance(node, ast.Import):
                  for alias in node.names:
                      top = alias.name.split(".")[0]
                      if top in BANNED_TOP:
                          offenders.append(f"{py}:{node.lineno}: {alias.name}")
              elif isinstance(node, ast.ImportFrom) and node.module:
                  top = node.module.split(".")[0]
                  if top in BANNED_TOP:
                      offenders.append(f"{py}:{node.lineno}: from {node.module}")
      assert not offenders, "Imports proibidos em domain/:\n" + "\n".join(offenders)
  ```
- **Comando:** `python -m pytest tests/test_dominio_imports_puros.py -q --tb=short`
- **Done quando:** 1 passed

### T-011 [P] Recriar `tests/test_auth_legacy_user_manager_no_runtime_imports.py` (T-AUD-004A)
- **AC:** AC-3.2
- **Arquivos:** `tests/test_auth_legacy_user_manager_no_runtime_imports.py` (NOVO)
- **Conteúdo esperado:**
  ```python
  import ast
  from pathlib import Path
  RUNTIME_ROOTS = ["autenticacao", "application", "services", "ui",
                   "interface", "exportacao", "browser", "scripts"]
  BANNED = {"core.authentication.user_manager"}
  ALLOWLIST: set[str] = set()  # vazia por DEC-003
  def test_no_runtime_imports_of_legacy_user_manager():
      repo_root = Path(__file__).parent.parent
      offenders = []
      for root in RUNTIME_ROOTS:
          if not (repo_root / root).exists(): continue
          for py in (repo_root / root).rglob("*.py"):
              if str(py) in ALLOWLIST: continue
              tree = ast.parse(py.read_text(encoding="utf-8"))
              for node in ast.walk(tree):
                  if isinstance(node, ast.ImportFrom) and node.module in BANNED:
                      offenders.append(f"{py}:{node.lineno}")
                  if isinstance(node, ast.Import):
                      for alias in node.names:
                          if alias.name in BANNED:
                              offenders.append(f"{py}:{node.lineno}")
      assert not offenders, "Imports proibidos:\n" + "\n".join(offenders)
  ```
- **Comando:** `python -m pytest tests/test_auth_legacy_user_manager_no_runtime_imports.py -q --tb=short`
- **Done quando:** 1 passed

### T-012 [P] Criar guardião `tests/test_agents_claude_md_sha_match.py`
- **AC:** AC-3.3, AC-16.1
- **Arquivos:** `tests/test_agents_claude_md_sha_match.py` (NOVO)
- **Conteúdo esperado:**
  ```python
  import hashlib
  from pathlib import Path
  def _sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
  def test_agents_claude_md_identical():
      root = Path(__file__).parent.parent
      a = root / "AGENTS.md"; c = root / "CLAUDE.md"
      assert a.exists() and c.exists(), "AGENTS.md ou CLAUDE.md ausente"
      assert _sha(a) == _sha(c), f"sha mismatch: AGENTS={_sha(a)[:8]} CLAUDE={_sha(c)[:8]}"
  ```
- **Comando:** `python -m pytest tests/test_agents_claude_md_sha_match.py -q --tb=short`
- **Done quando:** 1 passed

---

## FASE 2 — INVESTIGAÇÃO FORENSE (CRÍTICO) — Estimativa: ~1 dia

### T-020 [DHP] Registrar T-AUD-016 (forensics revert) em `tasks.md`
- **AC:** AC-2.3
- **Arquivos:** `docs/specs/tasks.md`
- **Conteúdo:** entrada nova T-AUD-016 documentando descoberta do revert_info.txt
- **Done quando:** entrada existe + linkada com `docs/obsoletos/incidents/`

### T-021 [BLOCK] Análise de git log e diff
- **AC:** AC-21.1, AC-21.2
- **Arquivos:** documentar em `snapshots/forensics_envio_gal_20260523.md`
- **Comando:**
  ```powershell
  git log --all --since=2026-05-22 --until=2026-05-25 -- exportacao/envio_gal.py | Out-File snapshots/forensics_git_log.txt
  git log --all --since=2026-05-22 --until=2026-05-25 -p -- exportacao/envio_gal.py | Out-File snapshots/forensics_git_diff.txt
  ```
- **Done quando:** ambos arquivos existem; análise humana confirma sequência de eventos

### T-022 [BLOCK] Confirmar GAL-ROB-001..010 íntegros em envio_gal.py atual
- **AC:** AC-21.3
- **Arquivos:** revisão manual de `exportacao/envio_gal.py`
- **Comando:** checklist visual contra CLAUDE.md §16 (10 itens GAL-ROB)
- **Done quando:** todos os 10 verificados; resultado em `snapshots/forensics_gal_rob_check.md`

---

## FASE 3 — HOUSEKEEPING ROOT (ALTO) — Estimativa: ~1 dia

### T-030 [P] Remover `requirements.txt` psycopg2 + criar guardião
- **AC:** AC-10.1, AC-10.3
- **Arquivos:** `requirements.txt`, `tests/test_no_psycopg2_imports.py` (NOVO)
- **Comando:**
  ```powershell
  # Editar requirements.txt: remover linhas 21-22 (comentário + psycopg2-binary)
  python -m pytest tests/test_no_psycopg2_imports.py -q --tb=short
  ```
- **Done quando:** requirements.txt sem psycopg2; guardião passa

### T-031 [P] [DHP] Mover/remover `battery-report.html`
- **AC:** AC-11.1
- **Arquivos:** root `/battery-report.html`
- **Comando:** `Remove-Item battery-report.html` ou `Move-Item ... docs/obsoletos/runtime_artifacts/`
- **Done quando:** removido do root

### T-032 [P] [DHP] Renomear `.env.txt` para `pythonpath.env` (ou mover para pyproject.toml)
- **AC:** AC-11.2
- **Arquivos:** root `/.env.txt`
- **Comando:** `Rename-Item .env.txt pythonpath.env`
- **Done quando:** arquivo renomeado; conftest.py/main.py não usam .env.txt diretamente

### T-033 [P] [DHP] Mover `config.json.bak` para `config/backups/`
- **AC:** AC-11.1
- **Arquivos:** root `/config.json.bak` → `config/backups/config_root_pre_merge.json`
- **Done quando:** movido

### T-034 [P] [DHP] Inspecionar `testedb.csv` (PRIV-001) e decidir destino
- **AC:** AC-11.3
- **Arquivos:** root `/testedb.csv` (810 KB)
- **Comando:** inspeção em ambiente LGPD-controlado; decidir mover para `tests/fixtures/` ou arquivar
- **Done quando:** decisão documentada em DHP + arquivo movido

### T-035 [P] [DHP] Mover 2x `relatorio_final_corrida_*.json` para `snapshots/runtime_artifacts/`
- **AC:** AC-11.1
- **Arquivos:** root `/relatorio_final_corrida_vr1.json` + `/relatorio_final_corrida_last.json`
- **Done quando:** movidos

### T-036 [P] Corrigir `pytest.ini` (remove arquivo inexistente)
- **AC:** AC-11.4
- **Arquivos:** `/pytest.ini`
- **Comando:** editar linha 5: `testpaths = tests` (remover `test_feature_flag_toggle.py`)
- **Done quando:** `pytest --collect-only` não emite warnings sobre testpath ausente

### T-037 [P] Criar guardião `tests/test_no_bak_files_in_runtime.py`
- **AC:** AC-12.3
- **Arquivos:** `tests/test_no_bak_files_in_runtime.py` (NOVO)
- **Conteúdo esperado:**
  ```python
  from pathlib import Path
  RUNTIME = ["domain", "application", "services", "ui", "exportacao", "autenticacao", "browser", "utils", "config", "scripts"]
  def test_no_bak_files():
      root = Path(__file__).parent.parent
      offenders = []
      for r in RUNTIME:
          if not (root/r).exists(): continue
          for p in (root/r).rglob("*"):
              if any(s in p.name for s in [".bak", ".bak.", ".orig", ".swp"]):
                  offenders.append(str(p))
      assert not offenders, f"Arquivos .bak em runtime: {offenders}"
  ```
- **Done quando:** ATUALMENTE FALHA (2 ocorrências: domain/.bak + ui/.bak); coordenar com T-038

### T-038 [DHP] Mover .bak para `docs/obsoletos/refactor_attempts/`
- **AC:** AC-12.2
- **Arquivos:** `domain/ct_rules_runtime.py.bak.target_recalc_fix`, `ui/menu_handler.py.bak.moderniza`
- **Comando:**
  ```powershell
  New-Item -ItemType Directory -Force -Path "docs/obsoletos/refactor_attempts"
  Move-Item "domain/ct_rules_runtime.py.bak.target_recalc_fix" "docs/obsoletos/refactor_attempts/"
  Move-Item "ui/menu_handler.py.bak.moderniza" "docs/obsoletos/refactor_attempts/"
  ```
- **Done quando:** ambos movidos; T-037 passa

---

## FASE 4 — IMPORT-BAN DE ÓRFÃOS (ALTO) — Estimativa: ~1 dia (paralelo)

### T-040 [P] Guardião `tests/test_analise_legacy_no_runtime_imports.py`
- **AC:** AC-8.3
- **Arquivos:** `tests/test_analise_legacy_no_runtime_imports.py` (NOVO)
- **Done quando:** 1 passed

### T-041 [P] Guardião `tests/test_extracao_legacy_no_runtime_imports.py`
- **AC:** AC-8.3
- **Done quando:** 1 passed

### T-042 [P] Guardião `tests/test_scratch_no_runtime_imports.py`
- **AC:** AC-8.3
- **Done quando:** 1 passed

### T-043 [P] Guardião `tests/test_sql_no_runtime_imports.py`
- **AC:** AC-8.3
- **Done quando:** 1 passed

### T-044 [P] Guardião `tests/test_scripts_no_hardcoded_paths.py`
- **AC:** AC-13.2
- **Arquivos:** `tests/test_scripts_no_hardcoded_paths.py` (NOVO)
- **Conteúdo:** regex scan em `scripts/**` por literais `Downloads\\Integragal` ou `Downloads/Integragal`
- **Done quando:** ATUALMENTE FALHA (5+ scripts); coordenar com T-045

### T-045 [DHP] Refatorar paths hardcoded em 5+ scripts
- **AC:** AC-13.1
- **Arquivos:** scripts/check_bom.py, scripts/limpeza_logs_reports.ps1, scripts/limpeza_prioridade_alta.ps1, scripts/organizar_documentacao.ps1, scripts/run_daily_parity_snapshot.cmd, scripts/run_all_tests.ps1
- **Comando:** substituir paths absolutos por `Path(__file__).resolve().parent.parent` (Python) ou `$PSScriptRoot/..` (PS) ou `%~dp0..` (CMD)
- **Done quando:** T-044 passa

---

## FASE 5 — POLÍTICA DE SENHA / LOCKOUT (ALTO) — Estimativa: ~3 dias

### T-050 [DHP] Registrar DHP "política de senha/lockout" em `tasks.md` + `decisoes_humanas/`
- **AC:** AC-7.1
- **Arquivos:** `docs/specs/tasks.md` + `docs/specs/decisoes_humanas/DHP-senha-lockout.md`
- **Conteúdo da DHP:** N tentativas (proposta: 5), duração bloqueio (proposta: 15 min), recuperação (admin desbloqueia), exigências mínimas senha (proposta: 8 chars).
- **Done quando:** DHP aprovada

### T-051 [BLOCK] Implementar lockout server-side em `auth_service.autenticar_credenciais`
- **AC:** AC-7.2, AC-7.3, AC-7.4
- **Arquivos:** `autenticacao/auth_service.py:667-743`
- **Comportamento:**
  - Antes de validar bcrypt: ler `tentativas_falhas` e `bloqueado_ate`. Se `bloqueado_ate > now`: retornar `None` imediato (sem revelar se senha estaria correta).
  - Em falha de senha: incrementar `tentativas_falhas` sob `CSVFileLock`. Se atingir N: setar `bloqueado_ate = now + 15min`.
  - Em sucesso: zerar `tentativas_falhas` e `bloqueado_ate`.
- **Done quando:** T-052 passa

### T-052 [BLOCK] Criar `tests/test_auth_lockout_persistence.py`
- **AC:** AC-7.5
- **Arquivos:** `tests/test_auth_lockout_persistence.py` (NOVO)
- **Cenários:** (a) 5 falhas → 6ª retorna None mesmo com senha correta; (b) sucesso reseta tentativas; (c) após 15min, contador zera.
- **Done quando:** 3 passed

### T-053 Validar em ambiente piloto por ≥ 7 dias
- **AC:** AC-7.x
- **Arquivos:** documentação em `snapshots/piloto_lockout_validacao_20260601.md`
- **Done quando:** 7 dias de uso sem regressão; admin confirma comportamento

---

## FASE 6 — FAIL-CLOSED + DECOMPOSIÇÃO cadastros_ui (ALTO) — Estimativa: ~5 dias

### T-060 [P] Criar `gal_payload_contract.assert_valid_gal_payload`
- **AC:** AC-6.1
- **Arquivos:** `exportacao/gal_payload_contract.py` (adicionar função)
- **Comportamento:** Wrapper de `validate_gal_payload`; se `len(errors) > 0`: `raise GalPayloadValidationError(errors)`.
- **Done quando:** assinatura disponível

### T-061 [BLOCK] Integrar `assert_valid_gal_payload` em `envio_gal.enviar_amostra`
- **AC:** AC-6.2
- **Arquivos:** `exportacao/envio_gal.py:946-1049`
- **Comando:** adicionar chamada `assert_valid_gal_payload(payload)` antes do POST
- **Done quando:** teste de regressão GAL passa

### T-062 [P] Endurecer `utils/error_handler.safe_operation`
- **AC:** AC-18.1
- **Arquivos:** `utils/error_handler.py`
- **Comando:** adicionar parâmetro `propagate_critical: bool = False`; se `True`, propaga após log
- **Done quando:** T-063 passa

### T-063 [P] Criar `tests/test_safe_operation_propagates_critical.py`
- **AC:** AC-18.3
- **Done quando:** 1 passed

### T-064 [BLOCK] Refatorar `config/settings.py` salvar/_criar_backup
- **AC:** AC-18.2, AC-6.3
- **Arquivos:** `config/settings.py:182-216`, `config/settings.py:234-261`
- **Comando:** substituir `@safe_operation` por try/except explícito com propagação para UI via Exception
- **Done quando:** falha de save é detectada por usuário (testado manualmente)

### T-065 [P] Migrar `db.db_utils.salvar_historico_processamento` para `services/reports/history_report.py`
- **AC:** AC-19.1, AC-8.4
- **Arquivos:** `services/reports/history_report.py` (adicionar função), `utils/gui_utils.py:13` (atualizar import)
- **Done quando:** T-066 passa

### T-066 [P] Atualizar 3 outros callers de `db.db_utils`
- **AC:** AC-8.4
- **Arquivos:** ui/janela_analise_completa.py:1650, ui/modules/dashboard.py:1195, scripts/consolidate_history.py:24
- **Comando:** substituir `from db.db_utils import salvar_historico_processamento` por `from services.reports.history_report import salvar_historico_processamento`
- **Done quando:** `tests/test_utils_no_db_imports.py` passa (T-067)

### T-067 [P] Criar guardião `tests/test_utils_no_db_imports.py`
- **AC:** AC-19.3
- **Done quando:** 1 passed

### T-068 [BLOCK] Criar cobertura prévia `tests/test_cadastros_smoke_*.py`
- **AC:** AC-5.1
- **Arquivos:** `tests/test_cadastros_smoke_exames.py`, `tests/test_cadastros_smoke_equipamentos.py`, `tests/test_cadastros_smoke_placas.py`, `tests/test_cadastros_smoke_regras.py`
- **Cobertura mínima:** abrir editor, criar item, listar items, deletar item
- **Done quando:** 4 arquivos passados; cobertura ≥ 70% do happy-path

### T-069 [BLOCK] Decompor `ui/modules/cadastros_ui.py` em facade + 4 editores
- **AC:** AC-5.2
- **Arquivos:**
  - `ui/modules/cadastros_ui.py` (facade ≤ 400 L)
  - `ui/modules/cadastros_exames.py` (NOVO)
  - `ui/modules/cadastros_equipamentos.py` (NOVO)
  - `ui/modules/cadastros_placas.py` (NOVO)
  - `ui/modules/cadastros_regras.py` (NOVO)
- **Comando:** strangler pattern — facade delega progressivamente; testes de T-068 continuam passando após cada split
- **Done quando:** T-068 passa após split; facade ≤ 400 L

### T-070 [P] Atualizar `analise/vr1e2_biomanguinhos_7500._validar_corrida` (fail-closed)
- **AC:** AC-6.4
- **Arquivos:** `analise/vr1e2_biomanguinhos_7500.py:113-115`
- **Nota:** Coordenar com Fase 7 (arquivamento de analise/). Se decisão for arquivar, esta tarefa pode ser pulada.
- **Done quando:** se executada, fallback mudou de `"Válida"` para `"Inválida - erro interno"`

---

## FASE 7 — MIGRAÇÃO E ARQUIVAMENTO DE ÓRFÃOS (ALTO) — Estimativa: ~2 dias

### T-080 [DHP] Aprovar DHP-13 coordenada (5 pastas órfãs)
- **AC:** AC-8.1
- **Arquivos:** `docs/specs/decisoes_humanas/DHP-13-orphan-packages.md`
- **Conteúdo:** decisão por pasta: A (mover para docs/obsoletos/) / B (remover) / C (manter como sandbox documentado)
- **Done quando:** DHP-13 aprovada

### T-081 [BLOCK] Mover `analise/` para `docs/obsoletos/legacy_packages/analise/`
- **AC:** AC-8.2
- **Pré-requisito:** T-040 passa (guardião confirma zero imports)
- **Comando:** `Move-Item analise docs/obsoletos/legacy_packages/`
- **Done quando:** movido; T-040 continua passando

### T-082 [P] Mover `extracao/` para `docs/obsoletos/legacy_packages/extracao/`
- **AC:** AC-8.2
- **Pré-requisito:** T-041 passa
- **Done quando:** movido

### T-083 [P] Mover `scratch/` para `docs/obsoletos/legacy_packages/scratch/`
- **AC:** AC-8.2
- **Pré-requisito:** T-042 passa
- **Done quando:** movido

### T-084 [P] Mover `sql/` para `docs/obsoletos/legacy_packages/sql/`
- **AC:** AC-8.2
- **Pré-requisito:** T-043 passa
- **Done quando:** movido

### T-085 [BLOCK] Mover `db/` para `docs/obsoletos/legacy_packages/db/`
- **AC:** AC-8.2
- **Pré-requisito:** T-065 + T-066 + T-067 concluídas (callers migrados)
- **Done quando:** movido; `tests/test_db_no_runtime_imports.py` passa

### T-086 [P] Atualizar `scripts/consolidate_history.py:10` (comentário PostgreSQL enganoso)
- **AC:** correlato a US-19
- **Arquivos:** `scripts/consolidate_history.py:10`
- **Done quando:** comentário corrigido para refletir CSV como fonte de verdade

---

## FASE 8 — DECOMPOSIÇÃO services/ (ALTO) — Estimativa: ~7 dias

### T-090 [BLOCK] Plano explícito T-AUD-010-FASE-2 em `tasks.md`
- **AC:** AC-14.4
- **Arquivos:** `docs/specs/tasks.md` (adicionar T-AUD-010-FASE-2)
- **Done quando:** plano documentado

### T-091 [BLOCK] Cobertura prévia `tests/test_analysis_service_smoke.py` (happy-path)
- **AC:** AC-14.1
- **Arquivos:** `tests/test_analysis_service_smoke.py`
- **Cobertura:** VR1e2 end-to-end + ZDC end-to-end via fixtures estáveis
- **Done quando:** cobertura ≥ 70% do happy-path validada

### T-092 [BLOCK] Decompor `services/analysis/analysis_service.py` (1 947 L) em ≤ 4 sub-módulos
- **AC:** AC-14.2
- **Arquivos:** `services/analysis/` (novos): `analysis_carga.py`, `analysis_motor.py`, `analysis_estado.py`, `analysis_relatorio.py`. Mantém `analysis_service.py` como facade.
- **Done quando:** T-091 passa após split

### T-093 [P] [BLOCK] Cobertura prévia `tests/test_persistence_adapters_smoke.py`
- **AC:** AC-14.1
- **Done quando:** cobertura ≥ 70%

### T-094 [P] [BLOCK] Decompor `services/persistence/persistence_adapters.py` (1 281 L) em 1 arquivo/contrato
- **AC:** AC-14.3
- **Arquivos:** `services/persistence/adapters/`: `history_adapter.py`, `user_adapter.py`, `exam_config_adapter.py`, `equipment_adapter.py`, `plate_adapter.py`, `rule_adapter.py`. Facade em `persistence_adapters.py`.
- **Done quando:** T-093 passa após split

### T-095 [P] (OPCIONAL) Decompor `services/analysis/full_run_status_sync.py` (1 626 L)
- **AC:** AC-14.x
- **Pré-requisito:** GAL-PEND-002 (suíte sem Selenium) concluído
- **Done quando:** se executada, split em ≤ 3 sub-módulos

---

## FASE 9 — PRÉ-REQUISITOS 10 USUÁRIOS (ALTO) — Estimativa: ~5 dias

### T-100 [P] [BLOCK] CONC-002: teste multiprocess 10 usuários em CSVs críticos
- **AC:** AC-22.1
- **Arquivos:** `tests/test_persistence_multiprocess_10_users.py` (NOVO)
- **Cenário:** 10 processos concorrentes escrevendo em `historico_analises.csv` + `usuarios.csv` sob `CSVFileLock`
- **Done quando:** zero corrupção; tempo aceitável documentado

### T-101 [P] [BLOCK] CONC-003: claim/lease GAL antes do envio externo
- **AC:** AC-22.2
- **Arquivos:** `services/gal/gal_transactions.py` (adicionar claim/lease), `tests/test_gal_claim_lease.py`
- **Comportamento:** antes de enviar amostra, marcar `inflight_keys` como "claimed" persistentemente; se outro processo tentar mesmo key, recusa.
- **Done quando:** teste de regressão multiprocess passa

### T-102 [P] CONC-005: validar SQLite em compartilhamento
- **AC:** AC-22.3
- **Arquivos:** `tests/test_sqlite_shared_storage_10_users.py`
- **Done quando:** zero corrupção

### T-103 [P] CONC-006: validar logs com 10 processos simultâneos
- **AC:** AC-22.4
- **Done quando:** zero linhas truncadas/corrompidas em sistema.log

### T-104 [BLOCK] INST-004: ADMIN+MASTER em Instalação Inicial
- **AC:** AC-20.1
- **Arquivos:** `ui/admin_initial_setup.py`
- **Comando:** validar `is_privileged()` no entry da tela
- **Done quando:** acesso negado para usuário não-privilegiado

### T-105 [BLOCK] INST-005: teste end-to-end do wizard de instalação
- **AC:** AC-20.2
- **Arquivos:** `tests/test_initial_setup_wizard_e2e.py`
- **Done quando:** 5 passos cobertos

### T-106 [BLOCK] Atualizar LIM-004 em `design.md`
- **AC:** AC-22.5
- **Arquivos:** `docs/specs/design.md:356`
- **Done quando:** status atualizado com resultados de CONC-002..006

---

## FASE 10 — CLEANUP DADOS RESIDUAIS + INTEGRAGAL.SPEC + LACUNAS FINAIS (ALTO) — Estimativa: ~3 dias

### T-110 [DHP] DHP cleanup de `dados/dados/`, `dados/logs/`, `dados/csv_gal/`
- **AC:** AC-9.1
- **Arquivos:** `docs/specs/decisoes_humanas/DHP-cleanup-dados.md`
- **Done quando:** DHP aprovada

### T-111 [BLOCK] Mover/remover resíduos pós-DHP
- **AC:** AC-9.2
- **Comando:** `Move-Item dados/dados snapshots/dados_residue_20260531/`
- **Done quando:** movidos; tamanho de dados/ cai >70%

### T-112 [P] Criar guardião `tests/test_dados_dados_nao_recriado.py`
- **AC:** AC-9.3
- **Done quando:** 1 passed

### T-113 [DHP] [BLOCK] Resolver drift `usuarios.csv` (3 cópias)
- **AC:** AC-4.1, AC-4.2
- **Arquivos:** `dados/banco/usuarios.csv`, `dados/banco_runtime/usuarios.csv`, `banco_runtime/usuarios.csv` (raiz)
- **Pré-requisito:** PRIV-001 ambiente controlado
- **Done quando:** apenas raiz `banco_runtime/usuarios.csv` permanece; cópias arquivadas

### T-114 [P] Guardião `tests/test_usuarios_csv_single_canonical_path.py`
- **AC:** AC-4.3
- **Done quando:** 1 passed

### T-115 [DHP] Política de `Integragal.spec` (config.json no distributable)
- **AC:** AC-23.1
- **Arquivos:** `docs/specs/decisoes_humanas/DHP-distributable-config.md`
- **Done quando:** decisão aprovada

### T-116 [BLOCK] Ajustar `Integragal.spec` conforme DHP
- **AC:** AC-23.2
- **Done quando:** ajustado

### T-117 [P] Criar `tests/test_distributable_first_boot.py`
- **AC:** AC-23.3
- **Done quando:** 1 passed (boot bloqueia operação até Instalação Inicial)

### T-118 [P] Telemetria final + DHP de remoção de `exportar_resultados_gal`
- **AC:** AC-17.1
- **Comando:** `python scripts/report_exportar_resultados_usage.py --hours 720`
- **Done quando:** janela ≥ 30 dias confirma uso runtime zero

### T-119 [BLOCK] Concluir deprecação de `exportar_resultados_gal`
- **AC:** AC-17.2, AC-17.3
- **Arquivos:** `exportacao/exportar_resultados.py`
- **Comando:** remover linhas 405-1175 (bloco morto); substituir `exportar_resultados_gal` por `raise DeprecationWarning` ou deletar
- **Done quando:** arquivo reduzido em ~880 L; nenhum caller quebra

### T-120 [P] Auditoria automatizada `tests/test_sdd_consistency.py`
- **AC:** AC-15.1, AC-15.2
- **Conteúdo:** parser de `tasks.md` extrai menções a `tests/test_*` e valida existência física
- **Done quando:** relatório em `snapshots/sdd_consistency_audit_20260531.md`

### T-121 [P] Corrigir lacunas detectadas pelo T-120
- **AC:** AC-15.3
- **Done quando:** cada lacuna ou tem artefato recriado ou tem declaração ajustada

---

## Resumo de dependências (DAG)

```
T-000 (backup) ─── PRÉ-REQUISITO DE TUDO
   │
   ├─ T-001 → T-002 → T-003                    (Fase 0 — csv_safety)
   ├─ T-004                                     (Fase 0 — revert_info)
   ├─ T-005 → T-006                             (Fase 0 — test_login)
   │
   ├─ T-010, T-011, T-012                       (Fase 1 — guardiões SDD, paralelos)
   │
   ├─ T-020 → T-021 → T-022                     (Fase 2 — forensics)
   │
   ├─ T-030..T-038                              (Fase 3 — root, T-037→T-038 ordem)
   │
   ├─ T-040..T-044                              (Fase 4 — import-ban paralelos)
   │     └─ T-045 (refactor scripts)
   │
   ├─ T-050 → T-051 → T-052 → T-053             (Fase 5 — lockout sequencial)
   │
   ├─ T-060 → T-061                             (Fase 6 — assert_valid_gal)
   ├─ T-062 → T-063 → T-064                     (Fase 6 — safe_operation)
   ├─ T-065, T-066 → T-067                      (Fase 6 — migração db→reports)
   ├─ T-068 → T-069                             (Fase 6 — cadastros_ui split)
   ├─ T-070 (opcional, coordenar com Fase 7)
   │
   ├─ T-080 → T-081..T-085                      (Fase 7 — DHP-13 + moves)
   ├─ T-085 depende de T-065+T-066+T-067
   ├─ T-086                                     (Fase 7 — consolidate_history comentário)
   │
   ├─ T-090 → T-091 → T-092                     (Fase 8 — analysis_service)
   ├─ T-093 → T-094                             (Fase 8 — persistence_adapters)
   ├─ T-095 (opcional)
   │
   ├─ T-100, T-101, T-102, T-103                (Fase 9 — CONC paralelos)
   ├─ T-104 → T-105                             (Fase 9 — INST-004/005)
   ├─ T-106                                     (Fase 9 — LIM-004 doc)
   │
   ├─ T-110 → T-111 → T-112                     (Fase 10 — dados/dados/)
   ├─ T-113 → T-114                             (Fase 10 — usuarios.csv drift)
   ├─ T-115 → T-116 → T-117                     (Fase 10 — Integragal.spec)
   ├─ T-118 → T-119                             (Fase 10 — exportar_resultados deprecation)
   └─ T-120 → T-121                             (Fase 10 — SDD consistency)
```

---

## Métricas de progresso

| Fase | Tarefas | Críticas | Paraleláveis | DHPs |
|---|---:|---:|---:|---:|
| 0 | 7 | 7 | 4 | 1 |
| 1 | 3 | 3 | 3 | 0 |
| 2 | 3 | 3 | 0 | 1 |
| 3 | 9 | 4 | 7 | 5 |
| 4 | 6 | 1 | 5 | 1 |
| 5 | 4 | 4 | 0 | 1 |
| 6 | 11 | 7 | 5 | 0 |
| 7 | 7 | 5 | 4 | 1 |
| 8 | 6 | 4 | 2 | 0 |
| 9 | 7 | 4 | 4 | 0 |
| 10 | 12 | 6 | 6 | 3 |
| **TOTAL** | **75** | **48** | **40** | **13** |

---

## Próximos passos após `tasks.md`

1. Executar `T-000` (backup) — **OBRIGATÓRIO ANTES DE QUALQUER MUDANÇA**.
2. Iniciar Fase 0 (T-001..T-006) — desbloqueia working tree.
3. Quando Fase 0 verde, prosseguir Fase 1 (T-010..T-012).
4. A partir daí, ritmo definido pela disponibilidade da equipe; ordem do DAG é rígida.
5. Após cada fase, atualizar `notas_de_passagem.md` com status + linkar tarefas concluídas.

---

## Comando consolidado para CI (após tudo concluído)

```powershell
python -m pytest tests/test_no_broken_csv_safety_imports.py tests/test_dominio_imports_puros.py tests/test_auth_legacy_user_manager_no_runtime_imports.py tests/test_agents_claude_md_sha_match.py tests/test_no_hardcoded_credentials.py tests/test_no_psycopg2_imports.py tests/test_no_bak_files_in_runtime.py tests/test_analise_legacy_no_runtime_imports.py tests/test_extracao_legacy_no_runtime_imports.py tests/test_scratch_no_runtime_imports.py tests/test_sql_no_runtime_imports.py tests/test_scripts_no_hardcoded_paths.py tests/test_safe_operation_propagates_critical.py tests/test_utils_no_db_imports.py tests/test_auth_lockout_persistence.py tests/test_dados_dados_nao_recriado.py tests/test_usuarios_csv_single_canonical_path.py tests/test_distributable_first_boot.py tests/test_sdd_consistency.py -v --tb=short
```

Esperado: 19 testes passados.
