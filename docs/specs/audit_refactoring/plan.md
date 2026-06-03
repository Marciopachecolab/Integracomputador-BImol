# Plano de Refatoração (Brownfield Audit)

## Arquitetura Alvo

O sistema passará de uma estrutura parcialmente "Onion" com vazamentos, para uma Strict Clean Architecture:
1. **Camada de Apresentação (UI):** Componentes CustomTkinter totalmente desidratados. Recebem `ViewModels` estritos.
2. **Camada de Aplicação:** Casos de uso orquestram o fluxo e `Presentation Models` mapeiam os objetos de Domínio/Repositório para `ViewModels`.
3. **Camada de Infraestrutura:** Detalhes de frameworks (Selenium, SQLite, multithreading locks) ficam isolados nos *Adapters*.

## Resolução das Dívidas Técnicas Encontradas

### 1. Pacote Órfão `analise/`
Foi diagnosticado no ADR `AUDITORIA.md` que esta camada duplicava `services/reports`. 
**Solução (Strangler Fig):** Implementar a DHP-13 (Opção A). O diretório inteiro será movido para o arquivamento seguro `docs/obsoletos/analise_legacy_sandbox/`. Inserir um guardião Pytest que garanta que o sistema inteiro funciona perfeitamente sem ele e proíba sua reintrodução.

### 2. Acoplamento de UI e Dados (`janela_analise_completa.py`)
**Problema:** O arquivo tem +1900 linhas contendo rotinas massivas de limpeza de dataframes e sort functions.
**Solução:** 
- Criar `application/presentation_models/plate_analysis_pm.py`.
- Esta classe consumirá os DataFrames e produzirá instâncias tipadas (`List[RowViewModel]`) ou um DTO processado para a UI.
- O `janela_analise_completa.py` será refatorado para apenas "printar" esses DTOs na tela e amarrar os botões aos callbacks.

### 3. Vazamento de Concorrência no Use Case (`gal_send_use_case.py`)
**Problema:** O Use Case instancia `threading.Lock()` para controlar a checagem dupla das chaves de idempotência (`inflight_keys`).
**Solução:** 
- Ampliar a porta `GalSendServicePort` ou criar `IdempotencyLockPort`.
- A implementação concreta desse lock (seja em memória, seja no SQLite) ficará em `services/gal/idempotency_manager.py`.
- O Use Case fará algo semântico: `if not idempotency_port.acquire_lock(id_key): return DUPLICADO`.

### 4. Fragmentação da God Directory (`services/`)
**Problema:** A pasta `services/` é um cluster caótico de módulos e responsabilidades mistas.
**Solução:**
Rearranjar os arquivos internos em "namespaces" claros:
- `services/database/` (Tudo relacionado a SQLite e paths de banco)
- `services/gal/` (Integração Selenium, requests, payload builders)
- `services/reports/` (Extração, planilhas)
- `services/core/` (Logs, Event Bus)

## Estratégia Técnica (Zero Quebras em Produção)
Para manter o sistema estável, cada fase deverá ser acompanhada de uma suite de regressão. Como estamos apenas mudando coisas físicas de lugar ou encapsulando em classes, o comportamento fim-a-fim não pode mudar. Trabalharemos um pacote por vez.
