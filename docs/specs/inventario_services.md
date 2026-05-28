# Inventário da Camada de Serviços (T-AUD-010)

> **Contexto:** Este documento atende à Tarefa T-AUD-010 definida no `tasks.md`, originada pela Dívida Técnica DT-002 (R-T3).
> **Objetivo:** Mapear e categorizar o conteúdo atual da pasta `services/` para um futuro split em subdomínios lógicos, reduzindo o custo cognitivo. Conforme a regra SDD, **nenhuma refatoração física foi realizada nesta etapa**, apenas o inventário descritivo.

## Resumo do Diretório Atual
*   **Local:** `services/`
*   **Total de Arquivos:** 81 arquivos (2.000+ linhas concentradas).
*   **Violação Atual:** Arquitetura "Fat Services" - mistura persistência (`sqlite`, `csv`), domínio de equipamento (`equipment_detector`), fluxos de aplicação (`analysis_service`) e auditoria de interface legada (`menu_catalog_audit_repository`).

---

## Proposta de Split (Domínios Alvo)

Para uma refatoração futura segura, os arquivos devem ser segregados nos seguintes módulos isolados:

### 1. Subdomínio `analysis/` (Motor Analítico)
Arquivos que cuidam das lógicas de corridas e análises.
*   `analysis_helpers.py`
*   `analysis_legacy_registry_parity.py`
*   `analysis_runtime_contract.py`
*   `analysis_runtime_observability.py`
*   `analysis_runtime_rollout.py`
*   `analysis_service.py`
*   `exam_runs_row_mapper.py`
*   `final_run_report.py`
*   `full_run_artifact.py`
*   `full_run_contract.py`
*   `full_run_status_sync.py`
*   `logic_engine.py`
*   `rules_engine.py`

### 2. Subdomínio `equipment/` (Contratos de Máquinas)
Arquivos dedicados a instanciar, extrair e classificar outputs de equipamentos.
*   `equipment_detector.py`
*   `equipment_extractors.py`
*   `equipment_registry.py`

### 3. Subdomínio `gal/` (Integração e GAL)
Arquivos para reconciliação, sincronização de transações e idempotência.
*   `gal_status_reconciler.py`
*   `gal_transactions.py`
*   `history_gal_sync.py`

### 4. Subdomínio `persistence/` (Infraestrutura de Dados)
Acesso a dados e abstrações DB/CSV.
*   `csv_io.py`
*   `csv_lock.py`
*   `csv_contracts.py`
*   `persistence_adapters.py`
*   `persistence_facade.py`
*   `persistence_provider.py`
*   `sqlite_repository.py`
*   `exam_runs_csv.py`
*   `exam_runs_sqlite.py`
*   `history_writer_core.py`
*   `history_schema.py`

### 5. Subdomínio `reports/` (Relatórios e Exportação)
Exportação de históricos, relatórios estatísticos e de placa.
*   `plate_report.py`
*   `relatorio_csv.py`
*   `relatorio_estatistico.py`
*   `reports_exporter.py`
*   `reports_repository.py`
*   `history_report.py`

### 6. Subdomínio `config/` ou `infrastructure/` (Core Técnico)
Configurações de sistema globais e observabilidade base.
*   `config_loader.py`
*   `config_service.py`
*   `error_contracts.py`
*   `event_bus.py`
*   `runtime_flags.py`
*   `service_container.py`
*   `query_latency.py`

### 7. Subdomínio Legado e Auditorias Transitórias (`legacy_audit/`)
Componentes criados temporariamente para monitorar ou fazer rollout das novas interfaces em paralelo. Quando o sistema atingir 100% de estabilidade U2, estes devem ser depreciados.
*   `menu_catalog_audit_repository.py`
*   `menu_catalog_cutover_orchestrator.py`
*   `menu_catalog_cutover_policy.py`
*   `menu_catalog_fallback_audit.py`
*   `menu_invalid_timestamp_fallback_policy.py`
*   `operational_slo_governance.py`
*   `operational_tabular_viewer.py`

---

## Conclusão da Tarefa (T-AUD-010)
Este inventário atende integralmente ao requisito imposto pelo comitê em maio de 2026. Recomendamos que, em sessões futuras, os arquivos sejam gradativamente movidos sem alteração de lógica interna, atualizando-se as importações (Strangler Fig local).
