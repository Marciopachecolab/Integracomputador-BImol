# Tarefas de Refatoração (Brownfield Audit)

Esta é a lista sequencial de tarefas atômicas (WBS) derivadas do `plan.md`, alinhadas com os critérios de aceite do `spec.md`.

## Fase 1: Isolamento e Limpeza (CA-01)
- [ ] **T01-A:** Mover fisicamente o diretório inteiro `analise/` para `docs/obsoletos/analise_legacy_sandbox/`.
- [ ] **T01-B:** Criar teste guardião em `tests/test_analise_package_no_runtime_imports.py` com AST-scan para garantir que nenhum módulo de produção use "import analise" (Import-Ban).

## Fase 2: Desacoplamento da Infraestrutura GAL (CA-03)
- [ ] **T02-A:** Criar o contrato `IdempotencyLockPort` em `application/gal_send_use_case.py` (ou próximo a ele).
- [ ] **T02-B:** Extrair a lógica do `threading.Lock()` e do conjunto `inflight_keys` para um novo arquivo de adapter na infra: `services/gal/idempotency_manager.py`.
- [ ] **T02-C:** Refatorar a função `_process_row` do `GalSendUseCase` para invocar o serviço externo e remover o gerenciamento de thread.

## Fase 3: Purgando Pandas da UI (CA-02)
- [ ] **T03-A [P]:** Criar a estrutura base de Presentation Models em `application/presentation_models/plate_analysis_pm.py`.
- [ ] **T03-B:** Mover os métodos `_normalizar_colunas_df`, `_ordenar_df_por_coluna`, e `_sort_dataframe_by_well` da `janela_analise_completa.py` para o novo Presentation Model de forma encapsulada.
- [ ] **T03-C:** Substituir a chamada na UI para que ela consuma a saída do Presentation Model, em vez de aplicar a lógica massiva inline.
- [ ] **T03-D:** Escrever os testes unitários cobrindo apenas o Presentation Model (não a UI visual), assegurando que o *sort* e a *normalização* preservam os dados originais.

## Fase 4: Restruturação de Diretórios (CA-04)
- [ ] **T04-A [P]:** Reorganizar e varrer módulos órfãos na pasta `services/` migrando utilitários óbvios para subpastas recém-criadas (se não quebrar importações de terceiros de forma abrupta).
- [ ] **T04-B:** Ajustar todos os caminhos de import relativos do projeto (`import services.xxx`) para os novos caminhos agrupados.

## Fase 5: Regressão Final (CA-04, CA-05)
- [ ] **T05:** Rodar suite global de Pytest (`python -m pytest`). Resolver todas as quebras provocadas pela renomeação das pastas e reorganização do Presentation Model.
