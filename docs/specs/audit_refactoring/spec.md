# Especificação de Refatoração (Brownfield Audit)

## Contexto e Motivação
A recente auditoria baseada no fluxo do Spec Kit (e documentada em `docs/adr/AUDITORIA.md`) revelou que o IntegraGal, embora possua separações bem definidas em várias camadas, apresenta dívidas técnicas arquiteturais significativas (God Classes na UI, um pacote órfão paralelo `analise/`, e um diretório `services/` saturado). 
Esta especificação foca em resolver esses problemas sem alterar o comportamento funcional (produção). O objetivo é garantir "UI Burra", alta coesão e fácil testabilidade.

## Requisitos Funcionais / Histórias de Usuário
- **US-01 (Limpeza de Código Morto):** Como mantenedor do sistema, quero que o pacote órfão `analise/` seja formalmente removido ou isolado, para evitar risco de uso acidental de uma segunda fonte de relatórios (DHP-13 Opção A).
- **US-02 (UI Burra):** Como desenvolvedor, quero que as interfaces CustomTkinter (notadamente `janela_analise_completa.py`) recebam os dados já formatados via ViewModels, de forma a não dependerem de operações da biblioteca `pandas` em seus métodos internos.
- **US-03 (Isolamento de Infraestrutura):** Como arquiteto, quero que a orquestração do envio GAL (`gal_send_use_case.py`) delegue o controle de acesso simultâneo (os *locks* de `inflight_keys`) para uma Porta específica do Repositório de Transações, limpando o *Use Case* de lógica de concorrência.
- **US-04 (Coesão de Serviços):** Como desenvolvedor, quero que a pasta `services/` seja agrupada logicamente (ex: `services/gal`, `services/database`, etc.), fragmentando a God Directory atual.

## Critérios de Aceite (Acceptance Criteria)
- **CA-01:** O pacote `analise/` está movido para `docs/obsoletos/analise/` e/ou um teste automatizado (`test_analise_package_no_runtime_imports.py`) garante import-ban deste pacote.
- **CA-02:** `ui/janela_analise_completa.py` teve tamanho reduzido consideravelmente. Manipulação de `pd.DataFrame` como `_normalizar_colunas_df` foi migrada para a camada `application/`.
- **CA-03:** `gal_send_use_case.py` usa um repositório para idempotência concorrente, removendo o uso direto de `threading.Lock()` de dentro da closure `_process_row`.
- **CA-04:** Nenhum teste existente quebra após a refatoração (Regressão Zero).
- **CA-05:** Os testes recém-criados devem rodar com sucesso via pytest sem dependência de Selenium (em modo Unitário puro).

## Fora de Escopo
- Mudanças no comportamento visual ou novas funcionalidades (feature freeze).
- Substituição total do framework CustomTkinter.
- Remoção do pacote de legacy `banco/` (que obedece a outras DHPs como HIG-005).
