# Refactor Attempts Arquivados

Arquivos `.bak` movidos de zonas reguladas (`domain/`, `ui/`, `services/`)
para preservar evidência histórica conforme política DEC-002/DEC-004
(preservação favorecida sobre exclusão).

## Conteúdo

### Lote E aprovado (T-038)

| Arquivo | Origem | Tamanho | Motivo |
|---|---|---:|---|
| `ui_menu_handler.py.bak.moderniza` | `ui/menu_handler.py.bak.moderniza` | 71 KB | Backup de refactor "moderniza" abandonado. Não integrado ao build. |
| `domain_ct_rules_runtime.py.bak.target_recalc_fix` | `domain/ct_rules_runtime.py.bak.target_recalc_fix` | ~3 KB | Versão anterior simplificada de `_lookup_rule()`. |

### Extensão do lote E (T-038b — 6 .bak adicionais detectados pela pré-verificação T-037)

| Arquivo | Origem | Tamanho | Motivo |
|---|---|---:|---|
| `services_core_config_service.py.bak.moderniza` | `services/core/config_service.py.bak.moderniza` | 27 KB | Backup de refactor "moderniza" abandonado. |
| `ui_components_plate_viewer.py.bak.moderniza` | `ui/components/plate_viewer.py.bak.moderniza` | 92 KB | Backup de refactor "moderniza" abandonado. |
| `ui_components_plate_viewer.py.bak.popup_fix` | `ui/components/plate_viewer.py.bak.popup_fix` | 92 KB | Backup do fix de popup (era versionado — movido via `git mv`). |
| `ui_modules_cadastros_ui.py.bak.moderniza` | `ui/modules/cadastros_ui.py.bak.moderniza` | 109 KB | Backup de refactor "moderniza" abandonado. |
| `ui_modules_exam_creator_wizard.py.bak.moderniza` | `ui/modules/exam_creator/wizard.py.bak.moderniza` | 41 KB | Backup de refactor "moderniza" abandonado. |
| `ui_modules_extraction_plate_mapping.py.bak` | `ui/modules/extraction_plate_mapping.py.bak` | 17 KB | Backup genérico abandonado. |

Movidos por **T-038** + **T-038b** (Fase 3 Audit Refactoring) — guardião
`tests/test_no_bak_files_in_runtime.py` (T-037) impede reincidência.

> **Nota de versionamento:** a maioria destes `.bak` é ignorada pelo
> `.gitignore` (`**/*.mod*` e `*.bak`); preservados fisicamente no disco.
> Os dois arquivos versionados —
> `domain_ct_rules_runtime.py.bak.target_recalc_fix` e
> `ui_components_plate_viewer.py.bak.popup_fix` — foram movidos via `git mv`.
