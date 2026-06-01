# Forensics — Timeline de commits em `exportacao/envio_gal.py` (2026-05-20 a 2026-05-31)

- **Data da análise:** 2026-06-01T20:55:00Z
- **Origem:** Fase 2 Audit Refactoring (T-021 etapa 1)
- **Branch:** `refactor/audit-refactoring`
- **Método:** subagente `Explore` (READ-ONLY) + verificação direta via `git log --all --numstat`

## 1. Commits que tocaram `exportacao/envio_gal.py` (histórico completo)

| SHA | Data ISO (author) | Autor | +linhas | -linhas | Operação | Mensagem |
|---|---|---|---|---|---|---|
| `f28ce1e` | 2026-05-28T08:35:51-03:00 | Marcio Pacheco de Andrade | 1784 | 0 | **Added (A)** | chore: establish secure repository baseline |

> **O arquivo aparece UMA ÚNICA VEZ no histórico git**: criado integralmente (`A`, 1784 linhas, 0 removidas) no commit baseline `f28ce1e`. Nenhum commit posterior tocou o arquivo na forma commitada.

## 2. Comparação de estados disponíveis

| Estado | Origem | Linhas | Observação |
|---|---|---|---|
| Baseline committed | `f28ce1e:exportacao/envio_gal.py` | 1784 | Estado inicial do repositório git |
| HEAD committed | `HEAD:exportacao/envio_gal.py` | 1784 | **Idêntico** ao baseline (diffstat vazio) |
| Working tree (atual) | `exportacao/envio_gal.py` (disco) | 1832 | Edições **não commitadas**: +52 / -4 vs HEAD |

Snapshots correspondentes:
- `snapshots/forensics_envio_gal_baseline_f28ce1e.py`
- `snapshots/forensics_envio_gal_HEAD.py`
- `snapshots/forensics_envio_gal_WORKTREE.py`
- `snapshots/forensics_diff_post_revert_recovery.patch` (HEAD → working tree, +52/-4)

## 3. ACHADO FORENSE CENTRAL — o revert de 2026-05-23 NÃO está no histórico git

**Por quê:** O incidente capturado em `revert_info.txt` ocorreu em **2026-05-23T05:06:41Z–05:07:08Z**.
O baseline git do repositório foi estabelecido em **2026-05-28** (`f28ce1e`), **5 dias DEPOIS** do incidente.

Consequências para o protocolo T-021 etapa 2 (desvio documentado):

- **NÃO existem** os commits `SHA-A` (pré-revert) nem `SHA-B` (pós-revert) previstos no plano.
- Não é possível executar `git show <SHA-A>` / `git show <SHA-B>` nem `git diff <SHA-A> <SHA-B>`.
- A **única evidência** do evento de revert é o arquivo arquivado
  `docs/obsoletos/incidents/revert_envio_gal_20260523.txt`
  (copiado para `snapshots/forensics_diff_revert_event.patch`).
- A **restauração (hipótese H2)** dos imports/funções removidos **já estava consolidada** no
  primeiro commit git (`f28ce1e`, 2026-05-28): o baseline já contém 1784 linhas com todos os
  imports presentes. Logo a recuperação ocorreu entre 2026-05-23 e 2026-05-28, **fora** do
  alcance do versionamento git (em working tree, antes do baseline).

## 4. Janela cronológica reconstruída (linha do tempo lógica)

| Momento | Evento | Fonte |
|---|---|---|
| 2026-05-23T05:06:41Z | Início da operação `multi_replace_file_content` (ferramenta não-SDD) | revert_info.txt:1 |
| 2026-05-23T05:07:08Z | Fim da operação — 85 linhas `-`, 0 `+` (deleção pura); hunk `@@ -33,778 +33,336 @@` | revert_info.txt:2,4 |
| 2026-05-23 → 2026-05-28 | **Janela cega do git**: restauração dos imports/funções (working tree, não versionado) | inferência (H2) |
| 2026-05-28T08:35:51-03:00 | Baseline git `f28ce1e` com `envio_gal.py` já restaurado (1784 linhas) | git log |
| 2026-05-28 → 2026-06-01 | Edições adicionais não commitadas no working tree (+52/-4 → 1832 linhas) | git diff HEAD |
| 2026-06-01 | Fase 0 detecta import circular T-AUD-016 e arquiva evidência (T-004) | tasks.md:153 |

## 5. Correlação com H3 (deleção de `utils/csv_safety.py`)

O diff de evidência remove explicitamente `from utils.csv_safety import sanitize_csv_value`
(revert_info.txt, bloco de imports). Isto é **consistente** com H3: o mesmo evento de revert
que removeu os imports de `envio_gal.py` pode ter sido o efeito colateral que motivou a
correção `csv_safety` da Fase 0 (T-001/T-003). No estado atual (working tree + baseline),
`from utils.csv_safety import sanitize_csv_value` está **presente** em `envio_gal.py`
(restaurado), e o guardião `tests/test_no_broken_csv_safety_imports.py` está verde.
