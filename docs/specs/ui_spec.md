# Interface Specification (UI Spec) - IntegRAGal

**Status:** Migrated

Este documento centraliza o inventário visual e a hierarquia dos ecrãs (janelas) implementados com a framework `CustomTkinter`.

## 1. Visão Arquitetónica da UI

O sistema obedece a uma abordagem de navegação modular, onde a `MainWindow` orquestra os painéis via um `MenuHandler`. Todos os painéis são despoletados em caixas ou abas (`CTkToplevel`, `CTkTabview`, `CTkFrame`).

### 1.1. Hierarquia de Módulos (Caminho Físico: `ui/modules/`)

*   **`dashboard.py`**: O painel central operativo e resumos vitais (Ecrã de aterragem).
*   **`tela_configuracoes.py`**: Gestão administrativa de definições globais, templates GAL e propriedades do laboratório.
*   **`sistema_alertas.py`**: Visualização flutuante ou empotrada de mensagens críticas e notificações do serviço de validação.
*   **`historico_operacional.py`**: Ecrã de *logs* de auditoria interativo e de eventos sistémicos.
*   **`historico_analises.py`**: Consulta e reemissão de relatórios e verificações de exames anteriores.
*   **`visualizador_exame.py` e `plate_viewer.py`**: Interface principal e de detalhe para visualização interativa do mapeamento de placas de PCR (96 poços/384 poços).
*   **`extraction_plate_mapping.py`**: Dialog e interface para gerir matrizes de poços vindas do extrator.
*   **`exportacao_relatorios.py` e `reports.py`**: Ecrãs para emissão e personalização de relatórios.
*   **`cadastros_diversos.py`**: Módulo administrativo de dados básicos auxiliares (CRUDs mínimos).
*   **`graficos_qualidade.py`**: Representação de métricas laboratoriais e de QC (Quality Control).
*   **`exam_creator/`**: Submódulo focado na parametrização assistida (Wizard) para criação e ativação de novos protocolos de exame.

## 2. Padrões de Interface e Regras

1.  **Redimensionamento de Janelas e Diálogos**: Conforme o Bloco 4 da intervenção arquitetural, os diálogos interativos (ex: metadados do GAL) devem adequar-se de modo flexível à resolução do utilizador sem cortar inputs vitais. (Utiliza-se sempre a estratégia `CTkToplevel` acompanhada da instrução `geometry()` ajustada aos monitores hospitalares padrão).
2.  **Validação In-Place**: Cada ecrã deve implementar a checagem imediata de pré-requisitos antes de invocar os `use cases` em `application/`. Exemplo: No envio GAL, o *Dialog* verifica primeiro a URL e os IDs obrigatórios de *worklist*.
3.  **Segregação Visual**: As regras de domínio não residem nos widgets. A UI comunica estritamente através dos adaptadores para interrogar serviços ou orquestrar envios.

## 3. Lacunas Mapeadas (Gap Analysis)
- Faltam testes unitários nativos para os elementos do Tkinter/CustomTkinter (limitado pela renderização do SO).
- Não há uma lista consolidada dos identificadores semânticos de CSS/Theme usados entre as vistas. (Potencial área de melhoria em rodadas futuras).
