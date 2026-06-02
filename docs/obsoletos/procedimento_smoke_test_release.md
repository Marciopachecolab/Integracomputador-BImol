# Procedimento de Smoke-Test de Release — IntegRAGal

Versao: 1.0
Data de criacao: 2026-05-17
Status: aprovado como procedimento formal; nao executado nesta rodada.

Este documento define o procedimento formal de smoke-test para validacao do pacote de release do IntegRAGal em copia limpa. O smoke-test deve ser executado futuramente, apos a materializacao de `release/` em rodada propria autorizada. Ele nao substitui o checklist pos-instalacao (`docs/checklist_pos_instalacao.md`), que valida o ambiente instalado; ambos sao complementares.

---

## 1. Identificacao

| Campo | Valor |
|---|---|
| Nome do release | |
| Data do smoke-test | |
| Responsavel pelo smoke-test | |
| Estacao de teste (hostname) | |
| Origem do pacote | |
| Hash / checksum do pacote (quando existir) | |
| Versao do Python no ambiente de teste | |
| Sistema operacional da estacao de teste | |

---

## 2. Objetivo

O smoke-test valida o pacote de release em copia limpa, antes de qualquer instalacao produtiva:

- Confirmar que o pacote pode ser aberto em ambiente zerado, sem dependencia de artefatos do ambiente de desenvolvimento.
- Confirmar que o pacote nao carrega dados sensiveis indevidos, logs reais ou relatorios; o unico banco distribuido e o seed privado autorizado para migracao.
- Confirmar que a estrutura minima do pacote esta presente e correta.
- Confirmar que a aplicacao abre sem erro critico em copia limpa.
- Confirmar que a Instalacao Inicial e acessivel e que exige configuracao antes do uso produtivo.
- Confirmar que o ambiente esta pronto para o checklist pos-instalacao (`docs/checklist_pos_instalacao.md`).

O smoke-test nao substitui o checklist pos-instalacao. Ver secao 10.

---

## 3. Pre-condicoes

Verificar antes de executar o smoke-test:

| Pre-condicao | Status | Observacao |
|---|---|---|
| Pacote de release criado por processo controlado (rodada propria autorizada) | [ ] OK / [ ] Falha | |
| `release/` criado somente em rodada futura autorizada; nao materializado anteriormente | [ ] OK / [ ] Falha | |
| `runtime_private/banco/` e `app/banco/` presentes somente com seed privado autorizado para migracao | [ ] OK / [ ] Falha | |
| `.env*` ausente do pacote | [ ] OK / [ ] Falha | |
| `logs/`, `reports/` e `relatorios/` reais ausentes do pacote | [ ] OK / [ ] Falha | |
| `relatorio_final_corrida_*.json` ausente do pacote | [ ] OK / [ ] Falha | |
| `snapshots/encoding_backup_*` ausente do pacote | [ ] OK / [ ] Falha | |
| `config.json` presente apenas como template/local runtime, sem caminhos reais e sem segredos | [ ] OK / [ ] Falha | |
| `release/app/models.py` presente (RUNTIME OBRIGATORIO) | [ ] OK / [ ] Falha | |
| `release/runtime_empty/data/state/` presente como diretorio vazio | [ ] OK / [ ] Falha | |
| `release/runtime_empty/data/state/window_state.json` ausente (nao distribuir arquivo gerado em uso) | [ ] OK / [ ] Falha | |
| REL-001 concluido documentalmente (2026-05-17): `assets/icon.ico` ausente; ausencia aceita formalmente como ressalva nao bloqueante para piloto; confirmar no smoke-test que aplicacao abre sem erro critico | [ ] Confirmado — sem erro critico / [ ] Falha — erro critico na abertura | |
| Baseline/backup do ambiente de desenvolvimento disponivel antes da execucao | [ ] OK / [ ] Falha | |

---

## 4. Verificacao estrutural do pacote

Confirmar presenca dos itens obrigatorios em `release/`:

| Item | Status | Observacao |
|---|---|---|
| `release/app/main.py` | [ ] Presente / [ ] Ausente | |
| `release/app/models.py` | [ ] Presente / [ ] Ausente | RUNTIME OBRIGATORIO |
| `release/app/domain/` | [ ] Presente / [ ] Ausente | |
| `release/app/application/` | [ ] Presente / [ ] Ausente | |
| `release/app/services/` | [ ] Presente / [ ] Ausente | |
| `release/app/ui/` | [ ] Presente / [ ] Ausente | |
| `release/app/autenticacao/` | [ ] Presente / [ ] Ausente | |
| `release/app/exportacao/` | [ ] Presente / [ ] Ausente | |
| `release/app/browser/` | [ ] Presente / [ ] Ausente | |
| `release/app/utils/` | [ ] Presente / [ ] Ausente | |
| `release/app/db/` | [ ] Presente / [ ] Ausente | |
| `release/app/config/` | [ ] Presente / [ ] Ausente | |
| `release/app/requirements.txt` | [ ] Presente / [ ] Ausente | |
| `release/app/config.json` | [ ] Presente / [ ] Ausente | Template runtime |
| `release/app/banco/credenciais.csv` | [ ] Presente / [ ] Ausente | Seed privado sensivel autorizado |
| `release/app/banco/usuarios.csv` | [ ] Presente / [ ] Ausente | Seed privado sensivel autorizado |
| `release/config_template/config.json` | [ ] Presente / [ ] Ausente | Deve ser template/local runtime |
| `release/config_template/config/contracts/` | [ ] Presente / [ ] Ausente | Contratos canonicos de equipamentos |
| `release/docs_operacionais/README.md` | [ ] Presente / [ ] Ausente | |
| `release/docs_operacionais/checklist_pos_instalacao.md` | [ ] Presente / [ ] Ausente | |
| `release/runtime_empty/logs/` | [ ] Presente / [ ] Ausente | Diretorio vazio |
| `release/runtime_empty/reports/` | [ ] Presente / [ ] Ausente | Diretorio vazio |
| `release/runtime_empty/relatorios/` | [ ] Presente / [ ] Ausente | Diretorio vazio |
| `release/runtime_empty/data/state/` | [ ] Presente / [ ] Ausente | Diretorio vazio; sem window_state.json |
| `release/runtime_private/banco/credenciais.csv` | [ ] Presente / [ ] Ausente | Seed privado sensivel autorizado |
| `release/runtime_private/banco/usuarios.csv` | [ ] Presente / [ ] Ausente | Seed privado sensivel autorizado |

---

## 5. Verificacao de exclusoes obrigatórias

Confirmar ausencia dos itens proibidos em `release/`:

| Item | Status | Observacao |
|---|---|---|
| `banco/` fora de `release/app/banco/` e `release/runtime_private/banco/` | [ ] Ausente / [ ] PRESENTE — BLOQUEIO | |
| Arquivos inesperados dentro dos seeds `banco/` autorizados | [ ] Ausente / [ ] PRESENTE — BLOQUEIO | Permitidos apenas os arquivos definidos pelo script de whitelist |
| `.env`, `.env.*`, `.env.txt` | [ ] Ausente / [ ] PRESENTE — BLOQUEIO | |
| Logs reais em `logs/` | [ ] Ausente / [ ] PRESENTE — BLOQUEIO | |
| Reports reais em `reports/` | [ ] Ausente / [ ] PRESENTE — BLOQUEIO | |
| Relatorios reais em `relatorios/` | [ ] Ausente / [ ] PRESENTE — BLOQUEIO | |
| `snapshots/encoding_backup_*` | [ ] Ausente / [ ] PRESENTE — BLOQUEIO | |
| `relatorio_final_corrida_*.json` | [ ] Ausente / [ ] PRESENTE — BLOQUEIO | |
| `.tmp/`, `pytest_tmp/` | [ ] Ausente / [ ] Presente — Ressalva | |
| `.venv/`, `venv/`, `env/` | [ ] Ausente / [ ] Presente — Ressalva | |
| `__pycache__/`, `.pytest_cache/`, `.mypy_cache/` | [ ] Ausente / [ ] Presente — Ressalva | |
| `tests/`, `test_data/` | [ ] Ausente / [ ] Presente — Ressalva | |
| Scripts de limpeza nao auditados (`scripts/limpeza_*`) | [ ] Ausente / [ ] Presente — Ressalva | |
| Arquivos `.db`, `.sqlite`, `.sqlite3` fora de runtime_empty | [ ] Ausente / [ ] PRESENTE — BLOQUEIO | |
| `release/runtime_empty/data/state/window_state.json` | [ ] Ausente / [ ] Presente — Ressalva | Gerado em uso; nao deve ser distribuido |
| `analise/` | [ ] Ausente / [ ] Presente — Ressalva | Legado sem imports de producao |
| `extracao/` | [ ] Ausente / [ ] Presente — Ressalva | Legado sem imports de producao |
| `interface/` | [ ] Ausente / [ ] Presente — Ressalva | Fachada de teste sem imports de producao |
| `core/` | [ ] Ausente / [ ] Presente — Ressalva | Legado em deprecacao controlada (DEC-003) |
| `debug/` | [ ] Ausente / [ ] Presente — Ressalva | Artefatos de debug Selenium |
| `sql/` | [ ] Ausente / [ ] Presente — Ressalva | DDL PostgreSQL; nao usado |
| `Main.spec` | [ ] Ausente / [ ] Presente — Ressalva | Artefato de build PyInstaller |
| `images/` | [ ] Ausente / [ ] Presente — Verificar | Sem referencias Python confirmadas; confirmar antes da materializacao |
| Credenciais, senhas, tokens, chaves fora do seed privado autorizado | [ ] Ausente / [ ] PRESENTE — BLOQUEIO | |

---

## 6. Smoke-test funcional minimo

Este procedimento deve ser executado futuramente, apos a materializacao autorizada de `release/`. Nao executar agora.

Passos:

| Passo | Acao | Resultado esperado |
|---|---|---|
| 1 | Abrir terminal na pasta `release/app/` do pacote em copia limpa | Terminal aberto sem erro |
| 2 | Verificar Python disponivel no ambiente de teste: `python --version` | Python 3.x confirmado |
| 3 | Ativar ambiente Python adequado (venv ou ambiente do destino), se aplicavel | Ambiente ativado sem erro |
| 4 | Instalar dependencias, se aplicavel: `pip install -r requirements.txt` | Instalacao sem erro critico |
| 5 | Iniciar aplicacao: `python main.py` | Aplicacao inicia sem erro critico |
| 6 | Verificar tela/login inicial | Tela de autenticacao apresentada corretamente |
| 7 | Autenticar com usuario autorizado de ambiente de teste (perfil ADMIN ou MASTER) | Autenticacao bem-sucedida |
| 8 | Verificar que o menu principal e acessivel | Menu carregado sem erro |
| 9 | Acessar menu `5. Administracao` | Menu Administracao acessivel |
| 10 | Acessar `Instalacao Inicial` | Modulo abre sem erro critico |
| 11 | Verificar que `config.json` esta como template e exige configuracao de `shared_storage` | Campo `data_root` vazio, `allowed_roots` vazio; sistema nao opera em producao sem configuracao |
| 12 | Verificar que `shared_storage` deve ser configurado antes do uso operacional | Validacao de pre-condicao funciona corretamente |
| 13 | Encerrar aplicacao | Aplicacao encerra sem erro critico |
| 14 | Verificar log de inicializacao, se disponivel, por erros criticos | Nenhum erro critico; warnings nao bloqueantes sao aceitaveis |

Observacoes obrigatórias durante o smoke-test:

- Nao configurar `shared_storage` com caminhos reais neste teste.
- Nao enviar nada ao GAL durante este teste.
- Nao usar dados reais de pacientes, amostras ou laboratorio.
- Registrar qualquer aviso, erro ou comportamento inesperado em Observacoes na secao 9.

---

## 7. Criterios de aprovacao

| Criterio | Condicao |
|---|---|
| **Aprovado** | Todos os itens das secoes 3, 4 e 5 satisfeitos; todos os passos da secao 6 concluidos com resultado esperado; nenhum bloqueio ativo; evidencias registradas na secao 9. |
| **Aprovado com ressalvas** | Pelo menos um item de ressalva identificado nas secoes 4 ou 5, mas sem bloqueio ativo; falha nao impede operacao piloto; justificativa registrada em Observacoes; responsavel ciente das restricoes. |
| **Reprovado** | Qualquer bloqueio ativo identificado na secao 5; ou qualquer criterio de reprovacao automatica da secao 8 verificado; ou autenticacao nao funcional; ou Instalacao Inicial inacessivel. |

---

## 8. Criterios de reprovacao automatica

Os itens abaixo causam reprovacao automatica, independente de outros resultados:

| Criterio de reprovacao automatica | Status |
|---|---|
| `banco/` fora das localizacoes autorizadas `app/banco/` e `runtime_private/banco/` | [ ] Verificado — Reprovado / [ ] Ausente — OK |
| `.env*` presente no pacote | [ ] Verificado — Reprovado / [ ] Ausente — OK |
| Credenciais, senhas, tokens ou chaves fora do seed privado autorizado | [ ] Verificado — Reprovado / [ ] Ausente — OK |
| Logs, reports ou relatorios reais presentes no pacote | [ ] Verificado — Reprovado / [ ] Ausente — OK |
| `release/app/models.py` ausente | [ ] Verificado — Reprovado / [ ] Presente — OK |
| `release/config_template/config.json` ausente | [ ] Verificado — Reprovado / [ ] Presente — OK |
| `release/docs_operacionais/README.md` ausente | [ ] Verificado — Reprovado / [ ] Presente — OK |
| `release/docs_operacionais/checklist_pos_instalacao.md` ausente | [ ] Verificado — Reprovado / [ ] Presente — OK |
| Erro critico ao abrir a aplicacao (excecao nao tratada na inicializacao) | [ ] Verificado — Reprovado / [ ] Ausente — OK |
| Tela de autenticacao nao apresentada | [ ] Verificado — Reprovado / [ ] OK |
| Instalacao Inicial inacessivel via menu Administracao | [ ] Verificado — Reprovado / [ ] OK |
| `config.json` com caminhos reais de producao ou dados de ambiente produtivo | [ ] Verificado — Reprovado / [ ] Ausente — OK |
| Arquivos `.db` ou `.sqlite` com dados reais presentes fora de `runtime_empty/` | [ ] Verificado — Reprovado / [ ] Ausente — OK |

---

## 9. Registro de evidencia

| Campo | Valor |
|---|---|
| Data e hora do smoke-test | |
| Responsavel pela execucao | |
| Ambiente de teste (hostname, SO, Python) | |
| Versao / checkpoint do pacote testado | |
| Hash / checksum do pacote (quando existir) | |
| Resultado | [ ] Aprovado / [ ] Aprovado com ressalvas / [ ] Reprovado |
| Observacoes | |
| Bloqueios identificados | |
| Prints ou anexos (opcional, sem dados sensiveis) | |
| Caminho do relatorio de validacao, se criado futuramente | |
| Proxima acao apos o smoke-test | |

---

## 10. Relacao com o checklist pos-instalacao

O smoke-test e o checklist pos-instalacao sao complementares e nao se substituem:

| Aspecto | Smoke-test de release | Checklist pos-instalacao |
|---|---|---|
| Quando executar | Antes da implantacao, em copia limpa do pacote | Apos instalacao em ambiente operacional do usuario |
| O que valida | Pacote de release: estrutura, ausencia de dados sensiveis, abertura basica | Ambiente instalado: shared_storage configurado, autenticacao, pre-condicoes operacionais |
| Quem executa | Engenheiro de release ou responsavel pelo pacote | Responsavel pela instalacao ou validador operacional |
| Arquivo de referencia | Este documento | `docs/checklist_pos_instalacao.md` |
| Independencia | Pode ser executado sem ambiente produtivo configurado | Exige `shared_storage` configurado e validado |

O smoke-test deve ser executado e aprovado antes do checklist pos-instalacao. Um pacote reprovado no smoke-test nao deve ser instalado em ambiente produtivo.

---

## 11. Pendencias conhecidas ao criar este procedimento

As restricoes abaixo sao conhecidas no momento da criacao deste procedimento (2026-05-17) e devem ser revisadas antes da execucao do smoke-test:

- **REL-001 concluida documentalmente (2026-05-17)**: `assets/icon.ico` nao existe fisicamente; `ui/main_window.py:256` referencia o arquivo; aplicacao trata ausencia de forma silenciosa (janela sem icone). Ausencia aceita formalmente como ressalva nao bloqueante para o release piloto. O smoke-test deve confirmar que a aplicacao abre sem erro critico (passo 5 da secao 6); se houver erro critico relacionado ao icone ausente, a ausencia deixa de ser ressalva e passa a ser bloqueio. A providencia de um icone oficial permanece como melhoria futura antes de versao final/distribuicao ampla.
- **release/ nao materializada**: o pacote de release ainda nao foi criado. Este procedimento so pode ser executado apos a materializacao autorizada de `release/` em rodada propria. A materializacao deve ser feita pelo script de whitelist `scripts/build_release_whitelist.ps1` com o parametro `-Execute`, em rodada propria autorizada, apos dry-run aprovado. O smoke-test so deve ser executado sobre um pacote gerado por esse processo controlado.
- **INST-001 pendente**: lock/atomicidade de `config.json` nao implementado.
- **INST-004 pendente**: ajuste ADMIN+MASTER na Instalacao Inicial nao implementado; a aba pode exigir exatamente ADMIN.
- Restricoes operacionais completas: ver `docs/checklist_pos_instalacao.md §6`.

---

Documento criado em 2026-05-17 como conclusao de REL-003.
Fonte canonica: `docs/procedimento_smoke_test_release.md`.
Atualizado em 2026-05-17: REL-001 concluida documentalmente; secao 11 e pre-condicao de REL-001 na secao 3 atualizadas para refletir aceitacao formal da ausencia do icone como ressalva nao bloqueante para o piloto.
Proxima revisao: apos materializacao de `release/` em rodada propria e execucao do smoke-test.
