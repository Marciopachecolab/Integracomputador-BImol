# Refactor Attempts Arquivados

Arquivos `.bak` movidos de zonas reguladas (`domain/`, `ui/`) para
preservar evidência histórica conforme política DEC-002/DEC-004.

## Conteúdo

| Arquivo | Origem | Tamanho | Motivo |
|---|---|---:|---|
| `ui_menu_handler.py.bak.moderniza` | `ui/menu_handler.py.bak.moderniza` | 71 KB | Backup de refactor "moderniza" abandonado. Não integrado ao build. |
| `domain_ct_rules_runtime.py.bak.target_recalc_fix` | `domain/ct_rules_runtime.py.bak.target_recalc_fix` | ~3 KB | Versão anterior simplificada de `_lookup_rule()`. |

Movidos por **T-038** (Fase 3 Audit Refactoring) — guardião
`tests/test_no_bak_files_in_runtime.py` (T-037) impede reincidência.

> O arquivo `ui_menu_handler.py.bak.moderniza` permanece ignorado pelo
> `.gitignore` (`**/*.mod*`); preservado fisicamente no disco. O arquivo
> `domain_*.bak.target_recalc_fix` era versionado e foi movido via `git mv`.
