# Checklist de Validacao Pos-Instalacao — IntegRAGal

Versao: 1.0
Data de criacao: 2026-05-16
Status: aprovado para uso piloto (3 a 5 usuarios)

Este checklist e um documento operacional para validacao do ambiente IntegRAGal apos instalacao em estacao de trabalho de piloto controlado. Nao substitui a documentacao SDD em `docs/specs/`. Preencher todos os campos antes de autorizar uso operacional.

---

## 1. Identificacao do Ambiente

| Campo | Valor |
|---|---|
| Estacao / hostname | |
| Responsavel pela instalacao | |
| Data e hora da validacao | |
| Versao / checkpoint do sistema | |
| Modo de implantacao | Piloto controlado — 3 a 5 usuarios |
| Validador (pode ser diferente do instalador) | |

---

## 2. Pre-condicoes

Verificar antes de abrir a aplicacao.

| Item | Status | Observacao |
|---|---|---|
| Python 3.x instalado e acessivel no ambiente | [ ] OK / [ ] Falha | |
| Dependencias de `requirements.txt` instaladas sem erro | [ ] OK / [ ] Falha | |
| Pasta do sistema disponivel com permissao de leitura e escrita | [ ] OK / [ ] Falha | |
| `config.json` tratado como template/local runtime — sem dados reais de producao | [ ] OK / [ ] Falha | |
| `shared_storage` configurado: `data_root` e `allowed_roots` preenchidos | [ ] OK / [ ] Falha | |
| Menu `5. Administracao` acessivel na aplicacao | [ ] OK / [ ] Falha | |
| `Instalacao Inicial` acessivel via menu Administracao | [ ] OK / [ ] Falha | |
| `runtime_private/banco/` e `app/banco/` contem somente o seed privado autorizado para migracao (`credenciais.csv`, `usuarios.csv` e catalogos/metadados permitidos) | [ ] OK / [ ] Falha | |
| Pacote de instalacao produzido por processo controlado (`scripts/build_release_whitelist.ps1 -Execute`) | [ ] OK / [ ] Falha / [ ] N/A — instalacao direta do repositorio |
| `logs/`, `reports/`, `relatorios/` iniciando como runtime vazio ou controlado | [ ] OK / [ ] Falha | |

---

## 3. Validacao da Instalacao Inicial

| Item | Status | Observacao |
|---|---|---|
| Modulo de Instalacao Inicial abre sem erro critico | [ ] OK / [ ] Falha | |
| Perfil ADMIN consegue acessar Instalacao Inicial | [ ] OK / [ ] Falha | |
| Perfil MASTER consegue acessar Instalacao Inicial | [ ] OK / [ ] Falha | |
| Validacao de diretorios apresenta resultado coerente | [ ] OK / [ ] Falha | |
| Validacao de permissoes de leitura/escrita concluida | [ ] OK / [ ] Falha | |
| `shared_storage.root`, `data_root` e `allowed_roots` configurados e validados | [ ] OK / [ ] Falha | |
| Restricoes conhecidas da Instalacao Inicial (INST-001..005) comunicadas ao responsavel | [ ] OK / [ ] Notado | |

---

## 4. Validacao Basica de Abertura

| Item | Status | Observacao |
|---|---|---|
| Aplicacao abre sem erro critico de inicializacao | [ ] OK / [ ] Falha | |
| Tela de autenticacao apresentada corretamente | [ ] OK / [ ] Falha | |
| Autenticacao com usuario autorizado (ADMIN ou MASTER) bem-sucedida | [ ] OK / [ ] Falha | |
| Menu principal acessivel apos autenticacao | [ ] OK / [ ] Falha | |
| Menu `5. Administracao` acessivel a partir do menu principal | [ ] OK / [ ] Falha | |
| `Instalacao Inicial` acessivel a partir de Administracao | [ ] OK / [ ] Falha | |
| Nenhum erro critico ou excecao nao tratada no log de inicializacao | [ ] OK / [ ] Falha | |

---

## 5. Validacao Operacional Minima

| Item | Status | Observacao |
|---|---|---|
| Telas principais carregam sem erro critico | [ ] OK / [ ] Falha | |
| Exames ativos disponiveis: `VR1e2 Biomanguinhos 7500` e `ZDC BioManguinhos` | [ ] OK / [ ] Falha | |
| Configuracoes de equipamentos (contratos JSON em `config/contracts/equipment/`) carregadas | [ ] OK / [ ] Falha | |
| Historico de analises acessivel sem erro | [ ] OK / [ ] Falha | |
| Nenhum dado real distribuido indevidamente fora do seed privado autorizado em `runtime_private/banco/` e `app/banco/`; `logs/`, `reports/` e `relatorios/` permanecem vazios/controlados | [ ] OK / [ ] Falha | |
| Modo piloto de 3 a 5 usuarios confirmado com responsavel operacional | [ ] OK / [ ] Confirmado | |

---

## 6. Restricoes Conhecidas do Ambiente

Registrar ciencia das restricoes antes de autorizar uso operacional. Estas restricoes nao impedem o piloto, mas devem ser comunicadas aos usuarios.

| Restricao | Ciencia |
|---|---|
| Multiusuario classificado como APTO COM RESTRICOES — piloto 3 a 5 usuarios | [ ] Ciente |
| Aptidao plena para 10 usuarios NAO declarada (aguarda CONC-002, CONC-003, INST-001) | [ ] Ciente |
| INST-001 pendente: lock/atomicidade de `config.json` nao implementado (risco em administracao concorrente) | [ ] Ciente |
| INST-002 pendente: dry-run de instalacao nao disponivel | [ ] Ciente |
| INST-003 pendente: backup/rollback de instalacao nao implementado | [ ] Ciente |
| INST-004 pendente: ajuste ADMIN+MASTER na Instalacao Inicial nao implementado | [ ] Ciente |
| INST-005 pendente: teste end-to-end do wizard de instalacao nao concluido | [ ] Ciente |
| CONC-002 pendente: teste multiprocess com 10 usuarios em CSVs criticos | [ ] Ciente |
| CONC-003 pendente: claim/lease GAL antes do envio externo | [ ] Ciente |
| PRIV-001 pendente: auditoria LGPD de `banco/*` nao concluida | [ ] Ciente |
| Override de migracao: `banco/credenciais.csv` e `banco/usuarios.csv` entram no pacote privado por decisao humana explicita; nao imprimir conteudo, nao versionar e distribuir apenas por canal controlado | [ ] Ciente |
| REL-001 concluido documentalmente (2026-05-17): `assets/icon.ico` ausente fisicamente; ausencia aceita formalmente como ressalva nao bloqueante para o piloto; janela pode abrir sem icone — isso nao e falha critica | [ ] Ciente |
| REL-003 concluido (2026-05-17): procedimento formal de smoke-test definido em `docs/procedimento_smoke_test_release.md`; nao executado ate materializacao de `release/` | [ ] Ciente |

---

## 7. Resultado da Validacao

| Campo | Valor |
|---|---|
| Resultado | [ ] Aprovado / [ ] Aprovado com ressalvas / [ ] Reprovado |
| Observacoes | |
| Responsavel pela validacao | |
| Data e hora | |
| Registro ou assinatura | |

### Criterios de resultado

- **Aprovado**: todos os itens das secoes 2 a 5 marcados como OK; ciencias da secao 6 registradas; nenhuma falha critica.
- **Aprovado com ressalvas**: pelo menos um item marcado como Falha em secoes 2 a 5, mas a falha nao impede operacao piloto; justificativa registrada em Observacoes; restricoes comunicadas ao responsavel.
- **Reprovado**: qualquer falha critica nas secoes 2, 3 ou 4; ou evidencia de dado real de paciente/laboratorio distribuido indevidamente; ou `shared_storage` nao configurado com `shared_storage.required=true`; ou autenticacao nao funcional.

---

## 8. Relacao com o smoke-test de release

Este checklist valida o **ambiente instalado** apos a implantacao. O procedimento de smoke-test (`docs/procedimento_smoke_test_release.md`) valida o **pacote de release em copia limpa**, antes da instalacao.

O smoke-test deve ser executado e aprovado antes de qualquer implantacao em ambiente produtivo. Um pacote reprovado no smoke-test nao deve ser instalado.

Os dois documentos sao complementares e nao se substituem.

---

Documento criado em 2026-05-16. Aprovado para uso piloto (3 a 5 usuarios).
Atualizado em 2026-05-17: secao 8 adicionada para referencia ao procedimento de smoke-test (REL-003 concluida).
Proxima revisao: apos conclusao de REL-001 (assets/icon.ico) e resolucao das prioridades INST/CONC aplicaveis.
Fonte canonica: `docs/checklist_pos_instalacao.md`.
