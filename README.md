# IntegRAGal

## 1. Visao geral

IntegRAGal e uma aplicacao Python desktop para apoiar o fluxo laboratorial de analise RT-PCR e integracao com GAL. O sistema centraliza etapas como configuracao, analise, revisao de resultados, envio ao GAL, relatorios e administracao operacional.

Este README e um ponto de entrada humano para operadores, administradores e equipe tecnica. Ele nao substitui a documentacao SDD em `docs/specs/`, nem as regras de governanca em `AGENTS.md` e `CLAUDE.md`.

## 2. Estado atual de implantacao

- A implantacao inicial deve ser feita como piloto controlado com 3 a 5 usuarios.
- O sistema nao deve ser declarado plenamente apto para 10 usuarios simultaneos nesta fase.
- A ampliacao para 10 usuarios depende dos testes e correcoes CONC pendentes, especialmente concorrencia em CSVs criticos, claim/lease antes de envio GAL e lock/atomicidade em `config.json`.
- A Instalacao Inicial foi classificada como funcional com restricoes.
- O uso operacional exige `shared_storage` configurado e validado.
- `config.json` versionado e template/local runtime; nao e configuracao real de producao.

## 3. Requisitos basicos

- Python 3.x.
- Dependencias Python listadas em `requirements.txt`.
- Ambiente desktop com suporte a Tkinter/CustomTkinter.
- Acesso de leitura/escrita ao armazenamento compartilhado definido na Instalacao Inicial.
- Acesso aos recursos necessarios para integracao GAL quando o envio for autorizado e configurado.

Nao inserir credenciais, senhas, tokens, dados laboratoriais reais ou caminhos de producao diretamente neste README.

## 4. Instalacao inicial

Para preparar um ambiente operacional, use o fluxo de administracao do sistema:

1. Abrir o sistema em ambiente controlado.
2. Acessar o menu `5. Administracao`.
3. Abrir `Instalacao Inicial` ou modulo equivalente.
4. Configurar o armazenamento compartilhado (`shared_storage`).
5. Validar diretorios, permissao de leitura/escrita e raizes permitidas.
6. Confirmar que `data_root` e `allowed_roots` apontam para o mesmo armazenamento aprovado.

Nao operar em producao com `shared_storage.required=true` e caminhos vazios. O `config.json` da raiz deve ser tratado como template/local runtime ate a Instalacao Inicial configurar o ambiente alvo.

## 5. Execucao do sistema

Em ambiente preparado, a aplicacao e iniciada pelo ponto de entrada principal do projeto:

```powershell
python main.py
```

Execute somente em ambiente autorizado, com configuracao local validada e sem expor credenciais ou dados sensiveis. Este README nao executa nem valida o sistema automaticamente.

## 6. Estrutura esperada de release

O pacote operacional deve seguir a estrutura documentada no plano HIG:

```text
release/
  app/
  config_template/
  docs_operacionais/
  assets/
  scripts_autorizados/
  runtime_empty/
```

- `release/app/`: codigo runtime necessario, incluindo `main.py`, `models.py`, `domain/`, `application/`, `services/`, `ui/`, `autenticacao/`, `exportacao/`, `browser/`, `utils/`, `db/`, `config/`, `requirements.txt` e assets necessarios.
- `release/config_template/`: `config.json` como template/local runtime e contratos canonicos em `config/contracts/`.
- `release/docs_operacionais/`: documentacao minima para instalacao, operacao, seguranca e continuidade.
- `release/assets/`: assets realmente usados pela UI.
- `release/scripts_autorizados/`: apenas scripts revisados e autorizados em rodada propria.
- `release/runtime_empty/`: estrutura vazia para runtime, sem dados reais.

Se existir `release/runtime_private/` em uma copia local ou operacional, trate-o como material privado de distribuicao controlada. Esse diretorio e qualquer seed privado de `banco/` nunca devem ser versionados, publicados no GitHub ou compartilhados por canal aberto.

## 7. O que nao deve ser versionado ou publicado

Nao incluir em Git, GitHub ou pacote aberto:

- `release/`, `release/app/banco/`, `release/runtime_private/` e qualquer runtime privado
- `banco/`, `banco_runtime/`, `banco_template/`, `dados/banco/` e bancos locais/runtime
- `.env`, `.env.*`, `.env.txt`
- `logs/`
- `reports/`
- `relatorios/`
- `dados/`, `snapshots/`, `mapas/`, `entrada/`, `saida/` e `exports/`
- `.tmp/`
- caches como `.pytest_cache/`, `.mypy_cache/` e `__pycache__/`
- `relatorio_final_corrida_*.json`
- bancos locais `.db`, `.sqlite`, `.sqlite3`
- credenciais, usuarios, seeds privados e dados reais de pacientes, amostras, exames ou operacao
- scripts de limpeza nao auditados

Scripts de limpeza em `scripts/` nao devem ser executados nem distribuidos como autorizados sem auditoria propria, baseline/backup e aprovacao explicita.

## 8. Restricoes conhecidas

- Multiusuario: classificado como apto com restricoes.
- Piloto inicial: 3 a 5 usuarios.
- 10 usuarios: meta condicionada a testes CONC e correcoes prioritarias.
- `config.json`: lock/atomicidade ja implementados (INST-001) e endurecidos para fail-closed/ownership (FINDING-004); teste de concorrencia entre dois administradores (CONC-004) permanece pendente.
- GAL concorrente: depende de claim/lease antes do envio externo em CONC-003.
- `banco/*`: mantido em dev/runtime como fallback controlado conforme DEC-002; nao imprimir conteudo, nao versionar e nao distribuir por canal aberto. Qualquer seed privado ou runtime privado exige canal controlado fora do Git/GitHub.
- Instalacao Inicial: funcional com restricoes; requer melhorias futuras como dry-run, rollback, log/auditoria e testes adicionais.
- `assets/icon.ico`: ausente fisicamente; aplicacao abre sem erro critico (janela sem icone); ausencia aceita formalmente como ressalva nao bloqueante para o piloto (REL-001 concluida documentalmente em 2026-05-17); providencia de icone oficial e melhoria futura antes de versao final.

## 9. Segurança de dados e versionamento

Nao versionar, compartilhar por canal aberto ou imprimir:

- `release/` materializado ou qualquer `runtime_private/`;
- bancos locais/runtime;
- credenciais;
- usuarios;
- senhas;
- tokens;
- chaves;
- arquivos `.env*`;
- CSVs sensiveis;
- logs reais;
- relatorios reais;
- dados laboratoriais ou de pacientes.

O `.gitignore` deve bloquear esses artefatos por padrao, mas isso nao remove arquivos que ja tenham sido rastreados pelo Git. Antes de qualquer commit ou publicacao, validar `git status --short --ignored`, `git ls-files` e `git check-ignore -v` para exemplos criticos.

Antes de qualquer limpeza, empacotamento ou distribuicao, confirme a existencia de baseline/backup e siga o plano HIG em `docs/specs/higienizacao_implantacao.md`.

## 10. Documentacao tecnica

Referencias principais:

- `docs/specs/requirements.md`: requisitos, regras de negocio e criterios de aceite.
- `docs/specs/design.md`: arquitetura, fluxos, contratos e limitacoes conhecidas.
- `docs/specs/tasks.md`: backlog rastreavel, tarefas concluidas, HIG, CONC, INST e DHPs.
- `docs/specs/higienizacao_implantacao.md`: plano HIG e manifest de release.
- `docs/checklist_pos_instalacao.md`: checklist de validacao pos-instalacao para ambiente piloto (3 a 5 usuarios).
- `docs/procedimento_smoke_test_release.md`: procedimento formal de smoke-test do pacote de release em copia limpa, antes da implantacao (REL-003).
- `scripts/build_release_whitelist.ps1`: script PowerShell de materializacao por whitelist do pacote de release; uso inicial deve ser em modo simulacao (sem `-Execute`); execucao real exige rodada propria autorizada por responsavel tecnico (REL-004).
- `AGENTS.md` e `CLAUDE.md`: contrato operacional para agentes de IA.
- `documento_de_passagem.md`: handoff de continuidade entre agentes.

Para contribuicoes tecnicas, seguir o loop SDD: ler requisitos/design/tasks, identificar tarefa ou decisao relacionada, respeitar DHPs, testar quando aplicavel e atualizar a documentacao somente quando o comportamento real mudar.
