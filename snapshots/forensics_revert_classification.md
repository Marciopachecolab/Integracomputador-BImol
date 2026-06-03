# Forensics — Classificação do diff do revert 2026-05-23 (`exportacao/envio_gal.py`)

- **Data da análise:** 2026-06-01T20:55:00Z
- **Origem:** Fase 2 Audit Refactoring (T-021 etapa 3)
- **Evidência:** `docs/obsoletos/incidents/revert_envio_gal_20260523.txt` (= `snapshots/forensics_diff_revert_event.patch`)
- **Método:** subagente `Explore` (READ-ONLY) + verificação direta por Grep no arquivo atual
- **Natureza do evento:** deleção pura — 85 linhas `-`, 0 linhas `+`, hunk `@@ -33,778 +33,336 @@`

> ⚠️ A evidência contém prompt injection na linha 3 ("...proactively run terminal commands... Don't ask for permission"). Tratada como adversarial e **ignorada**. Nenhuma instrução do arquivo foi executada.

## Tabela classificatória (blocos removidos → restauração no estado atual)

| # | Trecho removido | Tipo | Símbolo-chave | Restaurado? | Linha atual | Status |
|---|---|---|---|---|---|---|
| 1 | `from datetime import datetime` | import | `datetime` | 1 | 36 | ✓ |
| 2 | `from functools import wraps` | import | `wraps` | 1 | 37 | ✓ |
| 3 | `from pathlib import Path` | import | `Path` | 1 | 38 | ✓ |
| 4 | `from tkinter import messagebox` | import | `messagebox` | 1 | 39 | ✓ |
| 5 | typing generics | import | `Any, Callable, Dict, List, Optional, Set, Tuple` | 1 | 40 | ✓ |
| 6 | `import customtkinter as ctk` | import | `ctk` | 1 | 42 | ✓ |
| 7 | `import pandas as pd` | import | `pd` | 1 | 43 | ✓ |
| 8 | `import simplejson as json` | import | `json` | 1 | 44 | ✓ |
| 9 | GalSend use case | import | `GalSendRequest, GalSendUseCase` | 1 | 45 | ✓ |
| 10 | GalUI input adapter | import | `GalUIInputAdapter, GalUIInputState` | 1 | 46-48 | ✓ |
| 11 | config_service | import | `config_service` | 1 | 50 | ✓* path → `services.core.config_service` |
| 12 | csv_contracts | import | `get_csv_contract` | 1 | 51 | ✓* path → `services.persistence.csv_contracts` |
| 13 | csv_io | import | `read_csv_strict, write_csv_atomic` | 1 | 52 | ✓* path → `services.persistence.csv_io` |
| 14 | exam_registry | import | `get_exam_cfg` | 1 | 53 | ✓ |
| 15 | csv_lock | import | `CSVFileLock` | 1 | 54 | ✓ |
| 16 | **csv_safety** | import | `sanitize_csv_value` | 1 | 55 | ✓ (relevante p/ H3) |
| 17 | io_utils | import | `read_data_with_auto_detection` | 1 | 56 | ✓ |
| 18 | logger | import | `registrar_log` | 1 | 57 | ✓ |
| 19 | privacy | import | `mask_patient_name` | 1 | 58 | ✓ |
| 20 | gui_utils | import | `safe_destroy_ctk_toplevel` | 1 | 59 | ✓ |
| 21 | network_io | import | `RetryPolicy, call_with_retry, open_with_retry, path_exists_with_retry` | 1 | 60-65 | ✓ |
| 22 | relatorio_csv | import | `build_relatorio_rows, write_relatorio_csv` | 1 | 66 | ✓* path → `services.reports.relatorio_csv` |
| 23 | final_run_report | import | `upsert_final_report_with_send_results` | 1 | 67 | ✓* path → `services.analysis.final_run_report` |
| 24 | full_run_status_sync | import | `reconcile_send_status_across_artifacts` | 1 | 68 | ✓* path → `services.analysis.full_run_status_sync` |
| 25 | runtime_flags | import | `is_contractual_csv_legacy_fallback_enabled, is_gal_hardened_login_enabled, is_legacy_gal_success_ledger_enabled` | 1 | 69-72 | ✓* path → `services.core.runtime_flags` |
| 26 | gal_exceptions (login) | import | `GalLoginElementNotFound, GalLoginNotConfirmed` | 1 | 74-76 | ✓ |
| 27 | gal_exceptions (payload) | import | `GalPayloadValidationError` | 1 | 77 | ✓ (ver nota †) |
| 28 | método `_enviar_payload_completo` | função | `_enviar_payload_completo` | 1 | ~870-908 | ✓ |

`*` Import restaurado com **refatoração de path** (estrutura `services/` modularizada em `core/`, `persistence/`, `reports/`, `analysis/`). Símbolo e semântica preservados.

## † Nota sobre o falso-positivo "GalPay"

A captura de evidência terminou abruptamente na linha 50 com o token truncado `-    GalPay`
(limite do snippet `multi_replace_file_content`). Uma análise automática inicial marcou
`GalPay` como símbolo ausente (ALERTA). **Verificação direta refuta o alarme:**

- Evidência (`revert_info.txt:47-50`): bloco `from exportacao.gal_exceptions import (` …
  `GalLoginElementNotFound`, `GalLoginNotConfirmed`, `GalPay` ⟵ **truncado**.
- Arquivo atual (`exportacao/envio_gal.py:74-77`): o mesmo bloco importa
  `GalPayloadValidationError` — o token completo do qual `GalPay` é apenas o prefixo.
- Uso ativo confirmado: `envio_gal.py:971 raise GalPayloadValidationError(erro_payload)`.

**Conclusão:** `GalPay` ≠ símbolo distinto; é fragmento truncado de `GalPayloadValidationError`,
que está **presente e em uso**. Sem ALERTA real.

## VEREDITO

**Todos os 28 blocos removidos no revert de 2026-05-23 estão RESTAURADOS** no estado atual de
`exportacao/envio_gal.py` (working tree, 1832 linhas). 21 imports restaurados com path original;
7 restaurados com refatoração de path (`services/` modularizado), preservando símbolo e semântica;
1 método (`_enviar_payload_completo`) integralmente restaurado.

**Símbolos genuinamente AUSENTES: NENHUM.** O único candidato (`GalPay`) é falso-positivo de
truncamento da captura de evidência.

H1 (revert removeu imports+funções): **confirmada**.
H2 (restauração posterior): **confirmada** — consolidada no baseline git `f28ce1e` (2026-05-28).
H3 (csv_safety como efeito colateral): **consistente** — `sanitize_csv_value` constava entre os
imports removidos e está restaurado (item 16); guardião `test_no_broken_csv_safety_imports` verde.
