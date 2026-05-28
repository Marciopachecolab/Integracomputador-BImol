# Operations Plan - IntegRAGal

**Status:** Migrated from legacy procedures (Smoke Test e Checklist Pos-Instalacao)

Este documento funde e substitui os antigos procedimentos avulsos de validação do ambiente. Serve como fonte canónica para a validação de *releases* (smoke-test) e para a validação *in loco* (checklist pós-instalação).

## 1. Contexto

A validação operacional do IntegRAGal ocorre em duas fases distintas e complementares:
1. **Smoke-test de Release:** Validação estrutural do pacote gerado em cópia limpa, garantindo a ausência de ficheiros não autorizados ou dados sensíveis que não pertençam ao `seed` privado autorizado.
2. **Checklist Pós-Instalação:** Validação *in loco* da aplicação no ambiente do utilizador final, validando parametrizações como o `shared_storage` e conectividade.

## 2. Procedimento de Smoke-Test de Release

O *smoke-test* de release assegura que a pasta `release/` foi materializada de forma segura. Nenhuma implantação deve avançar se este teste reprovar.

### 2.1. Critérios de Reprovação Automática (Bloqueios)
Qualquer dos itens abaixo resulta em falha imediata e anula a *release*:
- Presença da diretoria `banco/` fora das localizações autorizadas (`app/banco/` e `runtime_private/banco/`).
- Presença de credenciais reais ou bases de dados em `relatórios/`, `reports/`, `logs/` ou `.sqlite`/`.db` populados.
- Ausência de `release/app/models.py`.
- Erros não tratados (exceções fatais) na inicialização por `python main.py`.
- Ficheiro `config.json` populado com caminhos reais de produção.

### 2.2. Procedimento de Execução Limpa
1. Abrir terminal em `release/app/`.
2. Verificar versão do Python (`python --version` >= 3.x).
3. Instalar dependências a partir do `requirements.txt`.
4. Executar `python main.py`. A aplicação deve carregar sem exceção fatal.
5. Iniciar sessão com um perfil ADMIN/MASTER da base de dados *seed* (teste).
6. Verificar que a *Instalação Inicial* no menu de Administração abre. O `shared_storage` deve estar vazio (indicando ser um template).

## 3. Checklist Pós-Instalação

Aplica-se ao sistema acabado de instalar na máquina laboratorial do utilizador.

### 3.1. Validação de Pré-Requisitos e Armazenamento
- O `config.json` inicial do utilizador deve ser configurado via *Instalação Inicial*, fornecendo as propriedades corretas a `data_root` e `allowed_roots`.
- O diretório apontado como `shared_storage` tem de possuir permissões de leitura/escrita.

### 3.2. Validação Operacional
- O ecrã de autenticação aceita as credenciais (que devem ter sido migradas com segurança).
- Os fluxos principais (ex: Menu Central, Pesquisa de Extração, Envio GAL) abrem perfeitamente.
- A aplicação não expõe credenciais nos `logs/` gerados.
- **Restrição Piloto**: A infraestrutura atualmente permite o uso em piloto para 3 a 5 utilizadores concorrentes.

## 4. Histórico e Gaps (Lacunas a resolver)
- *INST-001*: Atomicidade na gravação do `config.json` não implementada.
- *CONC-002*: Faltam testes massivos de 10 processos concorrentes em ficheiros CSV vitais.
- A aplicação não falha catastroficamente se o ficheiro `assets/icon.ico` faltar (ressalva não bloqueante, abre janela base sem ícone personalizado).
