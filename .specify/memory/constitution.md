# Constitution - IntegRAGal

## Project Principles

Estes princípios regem a contribuição de agentes autônomos (Claude Code, SpecKit, etc.) e desenvolvimento humano no projeto. Eles foram extraídos do contrato arquitetural canónico (anteriormente definido estritamente em `AGENTS.md` e `CLAUDE.md`).

### 1. Fontes de Verdade (Docs) e Stack (MUST)
- MUST usar sempre a pasta `docs/specs/` como a Fonte de Verdade da engenharia de requisitos.
- A stack tecnológica é: Python 3.x, CustomTkinter (UI), Pandas/OpenPyXL (Dados), Selenium (GAL), SQLite/CSV (Persistência).
- Qualquer inserção de dependências pesadas (`pandas`, `selenium`) na diretoria `domain/` é estritamente proibida.

### 2. Comportamentos Destrutivos e Segurança (MUST)
- MUST NOT executar comandos destrutivos sem aprovação explícita (ex: `rm -rf`, `git reset --hard`, `git push --force`).
- MUST NOT alterar o `config.json` base sem rodada específica, nem injetar dados sensíveis no repositório de controlo de versão.
- MUST NOT ler, imprimir no terminal ou expor credenciais dos *seeds* do sistema (`credenciais.csv`, `usuarios.csv`).

### 3. Falha em Tempo de Execução e Escopo (MUST)
- MUST operar num esquema `fail-closed` para exames fora do escopo. Os ativos atuais obrigatórios são `VR1e2 Biomanguinhos 7500` e `ZDC BioManguinhos`.
- MUST verificar e respeitar as condições de `shared_storage` e configurações da *Instalação Inicial* antes de invocar rotinas na base de dados em ambiente produtivo.
- MUST normalizar chaves de idempotência (ex: *dual-key GAL*) como lowercase/strip, nunca embutindo timestamps nas chaves para fugir à idempotência.

### 4. Ciclo Operacional SDD (SHOULD)
- O fluxo de trabalho SHOULD sempre passar por uma fase de ingestão (`speckit-brownfield-scan`), validação de artefactos e especificação antes de mexer em `main.py` ou serviços.
- Modificações na infraestrutura DEV/Runtime (arquivos passados para `docs/obsoletos`, por exemplo) só podem ocorrer via aprovação em Fases formais de Higienização (HIG).

### 5. Idioma (MUST)
- Todos os agentes MUST usar a variante de Português exigida no prompt de *system* em vigor para o seu loop (PT-BR ou PT-PT), especialmente ao criar mensagens, comentários para o utilizador, relatórios estruturados ou justificações de arquitetura. O código (variáveis, classes e commits) SHOULD acompanhar os padrões do projeto (mistura de PT/EN).
### 6. Design System e Interface (MUST)
- Fonte Única de Verdade: O arquivo `ui/theme.py` será a única fonte de design tokens (cores, tipografia, dimensões). É proibido o uso de hex codes, estilos ou fontes hardcoded espalhados pelos componentes CustomTkinter.
- Separação de Responsabilidades (UI Burra): A interface serve apenas para renderização. Nenhum componente do frontend pode possuir lógicas de negócio complexas ou acessar o domínio/backend diretamente. Os dados devem transitar via controladores ou callbacks.
