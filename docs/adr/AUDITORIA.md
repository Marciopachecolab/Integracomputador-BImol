**Ready for review**

Select text to add comments on the plan

**Auditoria SDD READ-ONLY — analise/**

**Contexto.** O usuário solicitou auditoria sênior de código, arquitetura e aderência SDD da pasta C:\Integragal - Backup - 20260128\_151811\analise\. Esta rodada é **READ-ONLY**: nenhum arquivo do projeto foi alterado. O único artefato gravado é este plano/relatório, em ~/.claude/plans/. A descoberta-chave é que analise/ é uma **camada paralela órfã** (0 consumidores externos no repositório) que **duplica responsabilidades já cobertas pela camada canônica services/reports/\*** (15+ consumidores ativos). Esta evidência muda a natureza da auditoria: não é só "como melhorar analise/?", mas também "este pacote deve existir?" (decisão humana — DHP).

-----
**1. Escopo analisado**

**Pasta alvo.** C:\Integragal - Backup - 20260128\_151811\analise\

**Arquivos analisados (6 arquivos, ~102 KB):**

|**Arquivo**|**Linhas**|**Tamanho**|
| :- | :- | :- |
|analise/\_\_init\_\_.py|2|16 B|
|analise/vr1e2\_biomanguinhos\_7500.py|268|10,5 KB|
|analise/relatorios\_operacionais.py|380|11,6 KB|
|analise/relatorios\_auditoria\_dep.py|2 002|22,9 KB|
|analise/relatorios\_gal\_qualidade.py|2 431|27,7 KB|
|analise/relatorios\_qualidade\_gerenciais.py|2 650|29,4 KB|

**Não analisados (e por quê):**

- analise/\_\_pycache\_\_/\*.pyc — bytecode gerado; sem valor de auditoria.
- Conteúdo de banco/credenciais.csv, banco/usuarios.csv, banco/test\_creds.csv — proibido por CLAUDE.md §9 e AGENTS.md §9 (segredos / dados sensíveis).
- \_rollback\_20260530\_100900/ — snapshot de rollback; fora do escopo da pasta analise/.

**Fontes SDD lidas (resumo destilado):**

- CLAUDE.md (raiz, contrato operacional)
- AGENTS.md (idêntico ao CLAUDE.md — §10/§14/§16)
- .specify/memory/constitution.md (regra suprema SpecKit)
- docs/specs/requirements.md (CA-01..CA-17, CA-R01..CA-R10)
- docs/specs/design.md (§3.5, §3.6, §3.8, §13, §14.2)
- docs/specs/tasks.md (R01-R10, DASH-001..008, WIZ-GAL-01..07, GAL-ROB-001..010, LOG-UNIF-001/002, T-AUD-\*)
- notas\_de\_passagem.md (sessões 2026-05-29/30)
-----
**2. Mapa da pasta**

analise/

├─ \_\_init\_\_.py                          (vazio — não exporta API)

├─ vr1e2\_biomanguinhos\_7500.py          (parser XLSX 7500 → DataFrame + status)

├─ relatorios\_operacionais.py           (4 relatórios por corrida, agnóstico de coluna)

├─ relatorios\_auditoria\_dep.py          (6 relatórios: log uso, versão regras, arquivos,

│                                         diff motor, validação CSV)

├─ relatorios\_gal\_qualidade.py          (6 relatórios: pré-envio/exportação/envio GAL,

│                                         controles internos, indicadores CQI, NC)

└─ relatorios\_qualidade\_gerenciais.py   (7 relatórios: controles internos [DUPLICA],

`                                          `indicadores [variante c/ frequência], NC [DUPLICA],

`                                          `produção, positividade, produtividade equip., TAT)

**Responsabilidades percebidas.** Pacote de relatórios analíticos/qualidade/auditoria, com um único parser concreto de equipamento (Applied Biosystems 7500, painel VR1e2). Cinco módulos relatorios\_\* usam um padrão ColumnConfig (@dataclass) que mapeia nomes de coluna de DataFrames externos para nomes lógicos — desacoplamento por convenção, não por contrato.

**Fluxos relevantes.**

- vr1e2\_biomanguinhos\_7500.analisar\_placa\_vr1e2\_7500(xlsx\_path, df\_extracao, parte\_placa) → lê XLSX → normaliza colunas → pivota CT por alvo → cruza com gabarito → classifica via utils.result\_classifier.classificar\_resultado(thresholds=VR1E2\_THRESHOLDS) → \_validar\_corrida(df\_final) → (df\_final, status).
- relatorios\_\*.gerar\_relatorio\_\*(df\_final | df\_historico | df\_log, cols=ColumnConfig, ...) → retorna pd.DataFrame pronto para exportação. Todos puros (sem IO).

**Dependências internas (do projeto):**

|**Importado por analise/**|**Existe?**|**Quem mais usa**|
| :- | :- | :- |
|utils.logger.registrar\_log|sim (utils/logger.py)|amplamente usado|
|config.ct\_thresholds.VR1E2\_THRESHOLDS|sim (config/ct\_thresholds.py)|utils/result\_classifier.py|
|utils.result\_classifier.classificar\_resultado|sim (utils/result\_classifier.py)|analise/ apenas|
|utils.result\_normalizer.normalize\_result\_label|sim (utils/result\_normalizer.py)|analise/ apenas|
|analise.relatorios\_operacionais.ColumnConfig|sim (re-export interno via fallback)|só analise/relatorios\_gal\_qualidade.py:100|

**Dependências externas:** pandas, openpyxl. Nada de selenium, tkinter, customtkinter (compatível com a regra de domínio puro de T-AUD-008 — embora analise/ esteja em services/-equivalente, não em domain/).

**Consumidores externos do pacote analise/:** **ZERO** consumidores de produção.

- Grep from analise / import analise em todo o repositório (excluindo \_\_pycache\_\_, \_rollback\_\*) retorna **1 (uma) ocorrência**, que é interna: analise/relatorios\_gal\_qualidade.py:100 faz from analise.relatorios\_operacionais import ColumnConfig # noqa: F401.
- Camada canônica concorrente: services/reports/\* — 8 módulos (history\_report, dashboard\_analytics, reports\_repository, reports\_exporter, relatorio\_csv, relatorio\_estatistico, plate\_report, \_\_init\_\_) com 15+ pontos de uso confirmados em application/, ui/, exportacao/, services/core/.
-----
**3. Diagnóstico executivo**

**Coerência com SDD.** Parcial. O pacote NÃO é citado em requirements.md, design.md ou tasks.md como camada canônica. R01–R10 (módulo de Relatórios concluído em 2026-05-30) referem-se explicitamente a services/reports/\* e application/reports\_query\_use\_case.py, NÃO a analise/. Há, portanto, **violação implícita da linguagem ubíqua/arquitetura**: existe um segundo "módulo de relatórios" fora do mapa SDD.

**Enxutez.** Insuficiente. Há **duplicação literal de uma dataclass e duas funções inteiras** entre relatorios\_gal\_qualidade.py e relatorios\_qualidade\_gerenciais.py. Algumas funções passam de 500 linhas com .iterrows()/loops manuais que pandas resolveria em poucas linhas vetorizadas.

**Redundância arquitetural.** Alta. relatorios\_gal\_qualidade.py cobre o mesmo domínio que services/reports/reports\_repository.py + services/gal/gal\_status\_reconciler.py + application/reports\_query\_use\_case.py — porém com contratos diferentes (ColumnConfig vs DTOs SDD), o que cria risco de divergência semântica se ambos forem usados em algum momento.

**Bugs prováveis.** Sim, conforme §5: fallback silencioso em \_validar\_corrida (retorna "Válida" quando há exceção), uso de regex "CN|CONTROLE.\*NEG" sem \b (matches falso-positivos em qualquer amostra cujo nome contenha "CN"), iniciar\_fluxo\_analise stub público que erra com NotImplementedError, e auto-import com noqa F401 que esconde acoplamento real.

**Risco arquitetural.** Alto. Se algum desenvolvedor futuro conectar analise/ à UI sem deprecar services/reports/, o projeto terá duas fontes da verdade para indicadores e relatórios — risco operacional grave (sair com dois relatórios divergentes em produção).

**Violação SDD.** Existe, mas é "passiva" (a pasta não está em uso, então não viola CA/DEC em runtime). Se reativada, viola: CA-R01..R10 (sem usar ReportsSQLiteRepository), CA-09/CA-10 (sem fail-closed contra exames fora de active\_exams), DASH-003/CA-16 (sem dedup RES\_\* canônico).

**Recomendação geral.** **Bloquear uso em produção e abrir DHP**.

1. Não integrar nada de analise/ à UI/serviços sem rodada SDD específica.
1. Abrir DHP "**DHP-13** — destino de analise/\*: deprecar/arquivar (Opção A, símil HIG-005/HIG-006), absorver funções úteis em services/reports/\* (Opção B), ou manter como sandbox documentada (Opção C)".
1. Sob nenhuma hipótese remover fisicamente sem DEC humana (segue política de DEC-002/DEC-004 para legados).
-----
**4. Notas 0–10**

|**Aspecto**|**Nota**|**Justificativa**|
| :- | :- | :- |
|Aderência SDD|**3**|Pasta não consta no mapa canônico (design.md §3.8, tasks.md R01-R10). Não há ExamForaDoEscopoError, não há leitura via ReportsSQLiteRepository, não há dedup RES\_\* (CA-16). Único alinhamento é o uso de VR1E2\_THRESHOLDS e classificar\_resultado corretos.|
|Arquitetura|**4**|Boa intenção (DataClasses, funções puras, separação por tema), mas **duplica camada existente** e **duplica símbolos entre módulos do próprio pacote** (QualidadeColumnConfig, gerar\_relatorio\_controles\_internos\_corrida, gerar\_relatorio\_nc\_relacionadas\_corrida). Acoplamento via ColumnConfig é frágil (string-based).|
|Clareza e Enxutez|**4**|Módulos com 2 000–2 650 linhas, funções com 200–500 linhas, iterrows() em vez de vetorização (pre\_envio\_gal:418-526), variáveis mortas comentadas como F841 (relatorios\_qualidade\_gerenciais.py:1849-1852). Estilo verboso para a entrega real.|
|Robustez|**3**|\_validar\_corrida engole exceções e retorna "Válida" (mascaramento crítico). \_processar\_ct é robusto. Regex de identificação de controle é alargado demais. Sem validação de presença de coluna obrigatória antes de acesso direto (df\_final["Amostra"]). Sem fail-closed por exame fora do escopo.|
|Manutenibilidade|**5**|Tipagem básica presente, docstrings curtas. Mas tamanho excessivo dos módulos e duplicação inter-módulo elevam custo de manutenção. Ausência de testes torna qualquer refactor arriscado.|
|Testabilidade|**2**|**Zero testes** no diretório tests/ exercitam funções de analise/\* (validado por grep). Funções puras facilitam teste, mas nada existe. Único módulo com iniciar\_fluxo\_analise() legado quebra ferramentas de discovery.|
|Risco Operacional|**3**|Se conectado em produção sem deprecar services/reports/\*, divergência de indicadores é provável; idempotência GAL não respeitada (CA-11). Mascaramento de erros em \_validar\_corrida pode aceitar corrida inválida. Hoje, o risco está latente (pasta órfã).|
|Prontidão para Evolução|**4**|ColumnConfig permite plug-in de schemas, mas a duplicação interna sinaliza que qualquer evolução exigirá refactor; o pacote não está alinhado às fontes canônicas SDD para evoluir sem retrabalho.|
|**Geral**|**3,5**|Pacote tecnicamente competente em pontos isolados, mas funcionalmente órfão, duplicado, frágil em validação e desalinhado do mapa SDD. **Não recomendado para produção** sem rodada SDD específica que decida deprecação ou absorção.|

-----
**5. Achados detalhados**

**A. Aderência SDD e arquitetura**

-----
[CRÍTICO] Pacote inteiro é uma camada paralela órfã que duplica services/reports/\*

Evidência:

\- analise/\_\_init\_\_.py:1-2 (vazio, sem \_\_all\_\_).

\- Grep "from analise" / "import analise" no repo: 1 ocorrência interna

`  `(analise/relatorios\_gal\_qualidade.py:100) — zero consumidores externos.

\- Camada canônica concorrente: services/reports/\* com 15+ consumidores

`  `(ui/modules/dashboard.py:20-21, application/reports\_query\_use\_case.py:19,

`   `exportacao/envio\_gal.py:66, services/core/service\_container.py:21, etc.).

\- design.md §3.8 / tasks.md R01-R10 e DASH-001..008 documentam services/reports/\*

`  `como camada canônica. analise/ não aparece em nenhum documento SDD.

Problema:

Existe um pacote de relatórios completo, não documentado, paralelo à arquitetura

SDD aprovada. Ninguém o consome, mas ele existe fisicamente, é importável e

pode ser ligado por engano. Viola §16/§12 do CLAUDE.md (decisões arquiteturais

canônicas) e a linguagem ubíqua de "Relatórios".

Impacto:

\- Risco de dois pipelines de relatórios divergentes (operacional grave).

\- Custo cognitivo aumentado para qualquer agente futuro.

\- Risco de quebra de CA-R01..R10, CA-16, CA-17 se reativado sem refactor.

\- Não há DEC/DHP que justifique a permanência.

Recomendação:

NÃO IMPLEMENTAR SEM DECISÃO HUMANA. Abrir DHP-13 ("destino de analise/")

com 3 opções:

`  `(A) deprecar e mover para docs/obsoletos/ (símil HIG-006), com guardião que

`      `proíba imports do pacote;

`  `(B) absorver funções úteis em services/reports/\* via rodada SDD própria;

`  `(C) manter como sandbox interno com README explícito de "não-produção".

Enquanto a DHP não for resolvida, não remover fisicamente nem reativar.

Teste sugerido:

Guardião em tests/test\_analise\_package\_no\_runtime\_imports.py: AST-scan que falhe

se qualquer arquivo em ui/, application/, services/, exportacao/, autenticacao/,

domain/, browser/ ou config/ contiver `from analise` ou `import analise`.

-----
[ALTO] Auto-import com `# noqa: F401` esconde acoplamento real intra-pacote

Evidência:

\- analise/relatorios\_gal\_qualidade.py:100

`  ``from analise.relatorios\_operacionais import ColumnConfig  # noqa: F401`

Problema:

Reexport silencioso de um símbolo do irmão `relatorios\_operacionais.py`,

suprimido pelo `noqa F401`. Cria dependência interna não declarada na docstring

nem no design.md, e oculta que o pacote tem topologia não-trivial.

Impacto:

\- Refactors em `relatorios\_operacionais.py` quebram `relatorios\_gal\_qualidade.py`

`  `silenciosamente.

\- Ferramentas de "find dead code" tendem a marcar incorretamente.

Recomendação:

Se a DHP-13 escolher Opção B (absorver), promover `ColumnConfig` a módulo

neutro (ex.: `analise/\_schema.py` ou, melhor, `services/reports/contracts.py`)

e remover o noqa. Senão, manter — mas documentar em docstring.

Teste sugerido:

Lint rule (ruff `--select F401`) sem allowlist no pacote, ou guardião AST que

exija docstring de "reexport" sempre que houver F401 ignorado.

-----
[ALTO] Duplicação literal de símbolos entre módulos do próprio pacote

Evidência:

\- class QualidadeColumnConfig

`    `- relatorios\_gal\_qualidade.py:1150

`    `- relatorios\_qualidade\_gerenciais.py:109

\- def gerar\_relatorio\_controles\_internos\_corrida

`    `- relatorios\_gal\_qualidade.py:1234

`    `- relatorios\_qualidade\_gerenciais.py:187

\- def gerar\_relatorio\_nc\_relacionadas\_corrida

`    `- relatorios\_gal\_qualidade.py:2290

`    `- relatorios\_qualidade\_gerenciais.py:1369

Problema:

Mesma dataclass e mesmas duas funções coexistem em dois módulos. Sem teste,

qualquer correção feita em um lado fica fora de sincronia com o outro.

Impacto:

\- Bugs assimétricos prováveis ao longo do tempo.

\- Indicadores CQI divergentes entre relatório "GAL/qualidade" e "qualidade gerencial".

\- Viola DRY e o princípio canônico §6 de "não duplicar regra clínica/operacional".

Recomendação:

Após DHP-13 (se Opção B), extrair `QualidadeColumnConfig` e as 2 funções para

um único módulo (`analise/\_qualidade\_compartilhado.py` ou

`services/reports/quality\_metrics.py`). Sem DHP-13 resolvida, não tocar.

Teste sugerido:

Guardião: tests/test\_analise\_no\_duplicate\_symbols.py percorre AST de

analise/\*.py e falha se mesmo nome de classe/função de nível top aparecer

em mais de um arquivo.

-----
**B. Robustez, validação e bugs prováveis**

-----
[CRÍTICO] \_validar\_corrida engole exceção e devolve "Válida" como fallback

Evidência:

\- analise/vr1e2\_biomanguinhos\_7500.py:113-115

`    `except Exception as e:

`        `registrar\_log("Validação", f"Erro ao validar corrida: {e}", "ERROR")

`        `return "Válida"  # Fallback para não bloquear fluxo em caso de erro

Problema:

Qualquer erro inesperado (coluna ausente, tipo inválido, divisão por zero) faz a

função declarar a corrida como VÁLIDA. Comentário admite a intenção

("não bloquear fluxo"). Isto é fail-open onde deveria ser fail-closed.

Impacto:

\- Risco clínico: corrida realmente inválida pode ser tratada como válida e

`  `alimentar GAL com Resultado\_geral indevido.

\- Viola política SDD §6 "fail-closed", CA-09/CA-10 e o princípio §17 sobre

`  `"achados críticos".

Recomendação:

Substituir por `return f"Inválida - erro interno de validação: {type(e).\_\_name\_\_}"`

ou levantar exceção dedicada (ex.: ValidacaoCorridaError) que o caller deve tratar.

NÃO IMPLEMENTAR SEM DECISÃO HUMANA porque o módulo está em pacote órfão e

DHP-13 pode decidir descartar.

Teste sugerido:

tests/test\_validar\_corrida\_fail\_closed.py — mock que injeta KeyError em

df\_final["Amostra"] e assert que status não começa com "Válida".

-----
[ALTO] Regex de identificação de controles é alargada e gera falso-positivo

Evidência:

\- analise/vr1e2\_biomanguinhos\_7500.py:71-72

`    `mask\_cn = df\_final["Amostra"].astype(str).str.upper().str.contains(

`        `"CN|CONTROLE.\*NEG|NEG.\*CONTROL", regex=True, na=False)

`    `mask\_cp = df\_final["Amostra"].astype(str).str.upper().str.contains(

`        `"CP|CONTROLE.\*POS|POS.\*CONTROL", regex=True, na=False)

Problema:

Os pivôs "CN" e "CP" não têm fronteira de palavra. Qualquer nome de amostra que

contenha "CN" (ex.: "CNTR-001", "PACI-CN-42") ou "CP" (ex.: "CPF-44") é

classificado como controle e entra na validação CN/CP.

Impacto:

\- Validação CN/CP pode falsamente reprovar corridas, ou

\- Amostras de paciente podem ser tratadas como controle.

\- Não há teste cobrindo nomes "ruidosos".

Recomendação:

Adotar fronteira: `r"\bCN\b|CONTROLE.\*NEG|NEG.\*CONTROL"` e idem para CP.

Idealmente, identificar controles pela coluna `codigo`/`Codigo` ou por flag

explícita do gabarito, não pelo nome livre. NÃO IMPLEMENTAR SEM DHP-13.

Teste sugerido:

Teste parametrizado: ["CN-1", "CP-1", "CNTR-001", "CPF-99", "PACI-CN-42"]

→ apenas os dois primeiros devem ser classificados como controle.

-----
[ALTO] iniciar\_fluxo\_analise é stub público que sempre levanta NotImplementedError

Evidência:

\- analise/vr1e2\_biomanguinhos\_7500.py:264-267

`    `def iniciar\_fluxo\_analise(\*args, \*\*kwargs):

`        `raise NotImplementedError(

`            `"Fluxo UI não suportado nesta versão simplificada para testes automatizados.")

Problema:

Função exportada de nível top, sem decorator/marcação de deprecation; qualquer

consumidor histórico chamará e quebrará. Reforça a impressão de pacote inacabado.

Impacto:

\- Possíveis quebras em código externo que talvez exista em ramos não-mergeados.

\- Ruído de API pública.

Recomendação:

Decidir junto da DHP-13. Se manter o pacote, remover símbolo; se absorver,

substituir por adaptador real; se deprecar, deixar como está (já sinaliza).

Teste sugerido:

N/A (já é "guardião" implícito).

-----
[MÉDIO] \_processar\_ct trata só vírgula↔ponto; não trata milhar e espaços internos

Evidência:

\- analise/vr1e2\_biomanguinhos\_7500.py:33-45 (especialmente 42:

`    `return float(txt.replace(",", ".")))

Problema:

Não cobre formatos como "1.234,56" (locale pt-BR com milhar), CT com espaço

interno ("  35 ,01"), ou notação científica em string. Em XLSX exportado do

7500 o CT geralmente vem como float, mas o método é o único ponto de

saneamento — vale endurecer.

Impacto:

\- Risco baixo em fluxo normal, mas amostras com CT mal-formatado retornam

`  `None e são tratadas como "sem detecção" → falso negativo silencioso.

Recomendação:

Centralizar parsing em `utils/result\_normalizer.py` ou em

`domain/ct\_parsing.py`, alinhado a `T-AUD-001` (domínio puro com math.isnan).

NÃO IMPLEMENTAR SEM DHP-13.

Teste sugerido:

Parametrizar: ["35,01", "35.01", " 35,01 ", "1.234,56", "UNDETERMINED",

"NA", "", None, 35.01, "3,5e1"] → resultados esperados explícitos.

-----
[MÉDIO] Sem `ExamForaDoEscopoError` no parser VR1e2 → fail-open de escopo

Evidência:

\- analise/vr1e2\_biomanguinhos\_7500.py:140-260 (função analisar\_placa\_vr1e2\_7500)

\- Não importa nem chama domain/exam\_scope ou active\_exams.

\- CA-09/CA-10 (requirements.md) exigem fail-closed.

Problema:

Se o pacote `analise/` for reativado, o parser não recusa execução quando o

exame está fora de `active\_exams`. Viola a constituição e a constituição SDD §6.

Impacto:

Reativação descontrolada → processamento fora de escopo → violação CA-09.

Recomendação:

NÃO IMPLEMENTAR SEM DHP-13. Se reativado, primeira linha do uso-caso deve ser:

`raise\_if\_out\_of\_scope("VR1e2 Biomanguinhos 7500")`.

Teste sugerido:

tests/test\_analise\_fail\_closed\_escopo.py — patch em `active\_exams` vazio e

assert que `analisar\_placa\_vr1e2\_7500` levanta `ExamForaDoEscopoError` antes

de qualquer IO.

-----
**C. Performance e estilo**

-----
[MÉDIO] Uso de .iterrows() em validação de pré-envio GAL (O(n) Python loop)

Evidência:

\- analise/relatorios\_gal\_qualidade.py:418-526 (gerar\_relatorio\_pre\_envio\_gal)

\- analise/relatorios\_qualidade\_gerenciais.py:2047-2149 (indicador\_grupo aninhado)

Problema:

Loop manual sobre linhas para validar campos obrigatórios e classificar

prontidão. Pandas oferece `.apply` vetorizado, `.isna()/.notna()`, máscaras

booleanas — sem mudança semântica.

Impacto:

\- Performance ruim em lotes grandes (> 5 000 amostras).

\- Mais código para manter e testar.

Recomendação:

Refatorar para máscaras booleanas + agregação vetorial. NÃO IMPLEMENTAR SEM

DHP-13. Se Opção B, considerar incorporar no `analysis\_service` que já é

vetorizado (`tests/test\_analysis\_service\_phase6\_vectorization.py`).

Teste sugerido:

Benchmark mínimo (pytest-benchmark) com 10 k linhas; cobrir igualdade

funcional vs versão atual em fixture com casos de borda.

-----
[BAIXO] Variáveis mortas comentadas como "F841" deixadas no código

Evidência:

\- analise/relatorios\_qualidade\_gerenciais.py:1849-1852

\- analise/relatorios\_gal\_qualidade.py:1531-1534, 1849-1852 (citado por subagente)

Problema:

Trechos de código removidos só parcialmente, com comentário do linter.

Indica refactor incompleto.

Impacto:

Limpeza apenas; sem risco operacional.

Recomendação:

Limpar quando DHP-13 escolher A ou B.

Teste sugerido:

N/A (ruff já cobre).

-----
[BAIXO] Módulos muito longos (2 000–2 650 linhas) com múltiplas responsabilidades

Evidência:

\- relatorios\_auditoria\_dep.py = 2 002 linhas, 6 funções públicas, 4 dataclasses

\- relatorios\_gal\_qualidade.py = 2 431 linhas, 6 funções públicas, 5 dataclasses

\- relatorios\_qualidade\_gerenciais.py = 2 650 linhas, 7 funções públicas, 4 dataclasses

Problema:

Cada arquivo combina temas heterogêneos (ex.: "auditoria" + "depuração"; "GAL" +

"qualidade"; "qualidade" + "produtividade" + "TAT"). Dificulta navegação,

revisão e teste.

Impacto:

Manutenibilidade.

Recomendação:

Em rodada de absorção (DHP-13 Opção B), quebrar por tema em `services/reports/`:

`gal\_pre\_envio.py`, `qualidade\_controles.py`, `qualidade\_indicadores.py`,

`produtividade.py`, `tat.py`, `auditoria\_log.py`, `auditoria\_arquivos.py`,

`diff\_motor.py`, `validacao\_csv.py`.

Teste sugerido:

N/A — métrica de tamanho/lint.

-----
**D. Testabilidade e código morto**

-----
[ALTO] Zero cobertura de testes para o pacote inteiro

Evidência:

\- Grep "from analise" / "import analise" em tests/: nenhum match.

\- Subagente Explore confirmou ausência de testes que exercitem qualquer função

`  `pública de analise/\*.

Problema:

~92 KB de código analítico sem nenhum guardião, em pacote já órfão.

Impacto:

Refactor seguro impossível; risco de regressão se reativado.

Recomendação:

NÃO IMPLEMENTAR SEM DHP-13. Caso seja absorvido (Opção B), exigir testes

ANTES da migração de cada função (TDD), seguindo CLAUDE.md §10.

Teste sugerido:

Mínimos por função pública: feliz-caso + caso vazio + caso de erro.

-----
[INFORMATIVO] \_\_init\_\_.py é vazio — pacote não declara API pública

Evidência:

\- analise/\_\_init\_\_.py:1-2 (apenas `# coding: utf-8`).

Problema:

Sem `\_\_all\_\_` nem reexports, qualquer símbolo é "público" por acaso, e

ferramentas de docs (Sphinx, pdoc) não enxergam a superfície.

Impacto:

Inexpressivo — coerente com a natureza órfã do pacote.

Recomendação:

Se Opção C (sandbox), adicionar README + `\_\_all\_\_` explícito.

Se A ou B, irrelevante.

Teste sugerido:

N/A.

-----
**Consolidação dos subagentes simulados**

|**Subagente**|**Veredicto**|
| :- | :- |
|**Arquiteto SDD**|Pacote é paralelo, não-citado, viola implicitamente CA-09/CA-10 e §6/§12 do CLAUDE.md. Pede DHP-13 antes de qualquer mudança.|
|**Bug Hunter**|2 críticos (camada órfã + fail-open em \_validar\_corrida) e 3 altos (regex frouxa, stub público, sem fail-closed de escopo).|
|**Código Morto/Redundância**|Pacote inteiro é candidato a deprecação; duplicação literal entre gal\_qualidade e qualidade\_gerenciais; iniciar\_fluxo\_analise é stub.|
|**Especialista em Testes**|Cobertura zero. Antes de qualquer refactor, criar guardiões: import-ban, no-duplicate-symbols, fail-closed-escopo, \_validar\_corrida fail-closed, regex CN/CP.|
|**Revisor de Enxutez**|Módulos 2 000–2 650 linhas com .iterrows() desnecessários; quebrar por tema reduziria 30–40 % do tamanho.|

-----
**Próximas decisões humanas (resumo)**

1. **DHP-13 — destino de analise/\*.** Opções A (deprecar/arquivar), B (absorver em services/reports/\*), C (manter como sandbox documentada). Sem essa decisão, **nenhuma alteração de código autorizada** nos arquivos da pasta.
1. **Aprovar guardião de import-ban** em tests/test\_analise\_package\_no\_runtime\_imports.py (read-only teste, não muda código de produção) — pode ser executado em rodada própria de teste antes da DHP-13.
-----
**Verificação (como confirmar este relatório)**

- Glob em \*\*/vr1e2\_biomanguinhos\_7500.py retorna 1 caminho (somente analise/).
- Grep "from analise" no repo retorna 1 ocorrência interna.
- Grep "from services.reports" retorna 15+ ocorrências em código de produção.
- Grep "def gerar\_relatorio\_controles\_internos\_corrida" em analise/ retorna 2 definições (linhas confirmadas: relatorios\_gal\_qualidade.py:1234 e relatorios\_qualidade\_gerenciais.py:187).
- Leitura direta de analise/vr1e2\_biomanguinhos\_7500.py:113-115 confirma fallback return "Válida" em except Exception.
- Leitura de analise/\_\_init\_\_.py confirma arquivo vazio.

Nenhum arquivo do projeto foi modificado



. Validação confirmou 2 dos 3 alertas dos subagentes (e descartou 1). Consolidando o relatório agora.

-----
**Auditoria SDD READ-ONLY — application/**

**1. Escopo analisado**

**Pasta alvo:** C:\Integragal - Backup - 20260128\_151811\application\

**Arquivos analisados (17 arquivos, ~96 KB):**

|**Arquivo**|**Linhas**|**Tamanho**|
| :- | :- | :- |
|[**init**.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/__init__.py)|2|39 B|
|[access_control.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/access_control.py)|87|2,9 KB|
|[analysis_orchestrator.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/analysis_orchestrator.py)|121|4,9 KB|
|[analysis_orchestrator_port.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/analysis_orchestrator_port.py)|84|2,5 KB|
|[contracts/ui_view_models.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/contracts/ui_view_models.py)|56|2,2 KB|
|[equipment_extraction_port.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/equipment_extraction_port.py)|63|2,0 KB|
|[equipment_extraction_service.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/equipment_extraction_service.py)|155|6,0 KB|
|[equipment_extraction_use_case.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/equipment_extraction_use_case.py)|58|1,6 KB|
|[equipment_profile_service.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/equipment_profile_service.py)|264|12,1 KB|
|[extraction_plate_mapping_use_case.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/extraction_plate_mapping_use_case.py)|132|4,2 KB|
|[file_chooser_port.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/file_chooser_port.py)|28|0,8 KB|
|[gal_send_use_case.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/gal_send_use_case.py)|565|26,0 KB|
|[gal_ui_input_adapter.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/gal_ui_input_adapter.py)|135|4,8 KB|
|[graph_use_cases.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/graph_use_cases.py)|135|3,7 KB|
|[reports_contracts.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/reports_contracts.py)|231|7,5 KB|
|[reports_query_use_case.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/reports_query_use_case.py)|183|6,6 KB|
|[sync_plate_to_analysis.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/sync_plate_to_analysis.py)|105|3,4 KB|

**Não analisados (e motivo):** \_\_pycache\_\_/\*.pyc (bytecode); nenhum arquivo sensível dentro de application/ (sem credenciais/tokens nesta camada).

**Fontes SDD lidas:** CLAUDE.md, AGENTS.md, .specify/memory/constitution.md, docs/specs/requirements.md, docs/specs/design.md (§3.5/§3.7/§3.8), docs/specs/tasks.md (GAL-ROB-001..010, R01-R10, T-AUD-004, DEC-003/006), notas\_de\_passagem.md.

-----
**2. Mapa da pasta**

application/

├─ \_\_init\_\_.py                                    (namespace vazio)

├─ access\_control.py                              (matriz operação→nível, DEC-003)

├─ analysis\_orchestrator.py                       (impl. AnalysisOrchestratorPort)

├─ analysis\_orchestrator\_port.py                  (Protocol + 5 exceções + 2 DTOs)

├─ contracts/

│  └─ ui\_view\_models.py                           (3 ViewModels para UI sem DataFrame)

├─ equipment\_extraction\_port.py                   (Protocol + DTO EquipmentDetectionResult)

├─ equipment\_extraction\_service.py                (3 adapters: 7500 / Quanti / Legacy)

├─ equipment\_extraction\_use\_case.py               (escolha+parse Excel via FileChooserPort)

├─ equipment\_profile\_service.py                   (DEC-006 - facade canônica de perfis JSON)

├─ extraction\_plate\_mapping\_use\_case.py           (kits 24/32/48/96 - dom. puro)

├─ file\_chooser\_port.py                           (Protocol para diálogo UI)

├─ gal\_send\_use\_case.py                           (U3 - 6 passos, dual-key, threadpool)

├─ gal\_ui\_input\_adapter.py                        (validação UI→GalSendRequest)

├─ graph\_use\_cases.py                             (Figure matplotlib para UI)

├─ reports\_contracts.py                           (5 DTOs frozen, fail-closed de escopo)

├─ reports\_query\_use\_case.py                      (R06 - SQLite+reconciliação GAL)

└─ sync\_plate\_to\_analysis.py                      (sync mapa↔análise, colunas protegidas)

**Responsabilidades percebidas.** Camada de **casos de uso e contratos (DTOs + Ports)** estritamente conforme CLAUDE.md §4/§6. Aderência elevada ao padrão Hexagonal: \*\_port.py define Protocols, \*\_use\_case.py/\*\_service.py orquestra, \*\_contracts.py define DTOs frozen com validação \_\_post\_init\_\_.

**Fluxos relevantes.**

- **Envio GAL (U3, GAL-ROB-001..010):** gal\_ui\_input\_adapter.GalUIInputAdapter valida UI → GalSendUseCase.execute orquestra 6 passos com idempotência dual-key (legacy\_key 4 campos vs nova\_key 4+N) + inflight\_keys thread-safe + persistência por amostra (\_persist\_success\_immediately). Consumido por exportacao/envio\_gal.py:45.
- **Relatórios (R06):** ui/modules/reports.py:215 → ReportsQueryUseCase.execute → ReportsSQLiteRepository.get\_filtered\_rows → reconcile\_gal\_status (journal). Filtros normalizados em reports\_contracts.ReportsFilterDTO.from\_raw.
- **Análise:** services/analysis/analysis\_service.py:465 (lazy) → AnalysisOrchestrator.execute → injeta AnalysisService real, encapsula erros em AnalysisExecutionError.
- **Equipamentos (DEC-006):** UI (ui/modules/cadastros\_ui.py:70, ui/menu\_handler.py:1483/1634) → EquipmentProfileService (CRUD JSON em config/contracts/equipment/\*.json com backup atomic) → EquipmentExtractionService.\_select\_adapter (7500/Quanti/Legacy).

**Dependências internas — entradas.** UI (ui/), exportacao/envio\_gal.py, services/analysis/analysis\_service.py, services/gal/history\_gal\_sync.py, autenticacao/auth\_service.py consomem application/. Não há referências do domain/ para application/ — camadas respeitadas.

**Dependências internas — saídas.** application/ importa apenas de domain.\*, services.\*, config.\*, utils.\*, application.\*. Nenhum import de ui.\*, tkinter, customtkinter, seleniumrequests em código puro (com 1 exceção justificada — gal\_send\_use\_case.py importa seleniumrequests.Firefox como factory padrão de webdriver, ver achado A2).

**Dependências externas.** pandas, seleniumrequests, selenium, requests, matplotlib.figure, concurrent.futures, threading. Concentrados no gal\_send\_use\_case e graph\_use\_cases.

**Consumidores externos (síntese):** sem órfãos. Todos os 17 módulos têm caller de produção identificado.

-----
**3. Diagnóstico executivo**

**Coerência com SDD.** **Alta.** Esta é a camada-modelo do projeto. Todos os módulos são citados no design.md (§3.5/§3.7/§3.8), AGENTS.md §4/§16, tasks.md (GAL-ROB-001..010, R06, T-AUD-004, DEC-003/006). DTOs frozen, Ports/Protocols, validação em \_\_post\_init\_\_, fail-closed em reports\_contracts.\_normalize\_exams → ExamForaDoEscopoError — tudo presente.

**Enxutez.** **Boa, com uma exceção.** [gal_send_use_case.py:156-529](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/application/gal_send_use_case.py#L156-L529) tem método execute com ~374 linhas e closure aninhada \_process\_row de ~165 linhas. É o maior módulo da camada (565 linhas). Os demais 16 módulos estão entre 28 e 264 linhas, bem proporcionados.

**Redundância.** **Mínima.** Nenhuma duplicação literal entre módulos da camada. Há sobreposição funcional pequena entre equipment\_extraction\_use\_case.py e equipment\_extraction\_service.py (ambos relacionados a extração), mas com responsabilidades distintas (use-case = escolha+parse Excel via FileChooserPort; service = adapter dispatcher).

**Bugs prováveis.** Três achados confirmados (Médio/Alto):

1. equipment\_profile\_service.\_load\_profile\_file engole qualquer Exception em parsing JSON, retornando None silenciosamente — perfil de equipamento mal-formado **desaparece** da lista sem log nenhum.
1. reports\_query\_use\_case.\_build\_details faz continue silencioso em ValueError de date.fromisoformat — linhas com data\_exame corrompido somem do detalhamento, sem rastreio.
1. equipment\_extraction\_service faz except Exception em detecção (linha ~79) e em extração (linha ~119), mas pelo menos wrapeia em exceções estruturadas (EquipmentDetectionError, EquipmentExtractionFailure) — risco menor.

O alerta do subagente sobre gal\_send\_use\_case.py:481-509 foi **descartado após leitura direta**: o except Exception é DELIBERADO e correto — registra como erro\_critico no relatório local, loga com nível critical + traceback completo, NÃO silencia. Isto materializa GAL-ROB-001 ("excepção de worker registrada estruturadamente") e GAL-ROB-002 ("lote não abortado por metadados vazios").

**Risco arquitetural.** **Baixo.** Camada estável e bem desenhada. Risco residual está em (a) tamanho do execute do GAL (dificulta teste isolado dos 6 passos), e (b) cobertura de testes irregular — vide achado E1.

**Violação SDD.** Nenhuma materializada. Há **risco de violação latente** (vide A2 abaixo): gal\_send\_use\_case instancia seleniumrequests.Firefox como factory padrão (linhas 113-141), o que tecnicamente é infra vazando para application; aceitável porque é factory injetável, mas merece atenção.

**Recomendação geral:** **MANTER com ajustes pontuais (baixo a médio impacto).** Sem refatoração estrutural; corrigir 3 swallowed exceptions, decompor execute do GAL em sub-passos testáveis, criar guardiões de testes para os módulos amplamente usados.

-----
**4. Notas 0–10**

|**Aspecto**|**Nota**|**Justificativa**|
| :- | :- | :- |
|Aderência SDD|**9**|Camada referenciada em todos os documentos canônicos; DTOs frozen, Ports, fail-closed de escopo (ExamForaDoEscopoError), idempotência dual-key, matriz de autorização — tudo presente. Pequeno desvio: factory Selenium dentro de gal\_send\_use\_case.|
|Arquitetura|**8**|Hexagonal corretamente aplicada; sem dependências invertidas. Ponto fraco: o GalSendUseCase concentra 6 passos numa só função, reduzindo coesão por passo.|
|Clareza e Enxutez|**7**|16/17 módulos enxutos; gal\_send\_use\_case viola "função pequena" (execute 374 linhas + \_process\_row 165 linhas). Resto é exemplar.|
|Robustez|**7**|Excelente design fail-closed na maioria; mas 3 except Exception swallowed (sem log nem mensagem específica) em equipment\_profile\_service (JSON parse), reports\_query\_use\_case (date parse) e equipment\_extraction\_service (broad).|
|Manutenibilidade|**7**|Tipagem ampla, docstrings, separação clara. Sofreria em refactor de GAL devido ao tamanho de execute.|
|Testabilidade|**5**|DTOs e Ports facilitariam mocks, mas grep em tests/ revela cobertura DIRETA da camada **escassa**: apenas tests/test\_ui\_view\_models.py aparece no Parte A do subagente. GAL/Reports/Equipment dependem de testes indiretos (via tests/test\_phase\_u3\_gal\_send\_use\_case.py etc.).|
|Risco Operacional|**7**|Idempotência GAL bem implementada (GAL-ROB-001..010); risco residual em swallowed exceptions que mascaram dados ausentes em relatórios e perfis.|
|Prontidão para Evolução|**8**|Ports + DTOs permitem adicionar adapter de equipamento, novo filtro de relatório ou novo passo GAL sem rasgar a camada. Restrição: decomposição do execute ajudaria.|
|**Geral**|**7,5**|Camada **canônica e madura**, sólida em padrões SDD. Ajustes pontuais (log em 3 except + decompor GAL + cobrir com testes diretos) elevariam a nota a 9+.|

-----
**5. Achados detalhados**

**A. Arquitetura & SDD**

[BAIXO] A1 — `application/` é a camada-modelo do projeto

Evidência:

\- 17/17 módulos com DTOs frozen, Ports/Protocols ou validação em \_\_post\_init\_\_.

\- reports\_contracts.py:96 lança ExamForaDoEscopoError (fail-closed de escopo).

\- gal\_send\_use\_case.py implementa GAL-ROB-001..010 (validação CSV antecipada

`  `L177-181, inflight\_keys com Lock L305-314, persistência imediata L399-405).

\- access\_control.py concretiza DEC-003 (matriz operação→nível).

\- equipment\_profile\_service.py concretiza DEC-006 (facade canônica JSON).

Problema:

Nenhum. Observação positiva.

Impacto:

Esta camada pode ser usada como REFERÊNCIA para revisar outras (ex.: `analise/`

órfão, ou cluster `services/` em DT-002).

Recomendação:

Nenhuma ação. Considerar citar `application/` como exemplar no `design.md §3`

para guiar novos contribuidores.

Teste sugerido:

N/A (achado informativo positivo).

[MÉDIO] A2 — Factory Selenium dentro de application/ (infra vazando para use-case)

Evidência:

\- application/gal\_send\_use\_case.py:113-141 `\_default\_webdriver\_factory` importa

`  ``seleniumrequests.Firefox` e `selenium.webdriver.firefox.options.Options`.

\- Imports no topo: linha 12 `from seleniumrequests import Firefox`.

Problema:

A camada application/ deve depender só de Protocols/Ports e domain/. Importar

selenium diretamente — mesmo como factory default — acopla o use-case à infra.

Impacto:

\- Testar a use-case requer ter selenium instalado.

\- Viola implicitamente o espírito de CLAUDE.md §6 (camadas).

\- Mascara que `GalSendServicePort` já abstrai TODAS as operações HTTP/login.

Recomendação:

Mover `\_default\_webdriver\_factory` para `services/gal/webdriver\_factory.py` e

deixar `gal\_send\_use\_case` receber a factory via parâmetro (já é injetável,

apenas o default deveria estar fora). NÃO IMPLEMENTAR SEM rodada de refactor

específica — toca código sob GAL-ROB já concluído.

Teste sugerido:

tests/test\_application\_layer\_no\_selenium\_imports.py — guardião AST que falhe se

qualquer .py em application/ contiver `import selenium` ou `from selenium\*`.

**B. Robustez & bugs prováveis**

[ALTO] B1 — \_load\_profile\_file engole Exception e perde perfil silenciosamente

Evidência:

\- application/equipment\_profile\_service.py:40-46

`    `def \_load\_profile\_file(self, path: Path) -> Optional[Dict[str, Any]]:

`        `try:

`            `payload = json.loads(path.read\_text(encoding="utf-8"))

`            `if isinstance(payload, dict):

`                `return payload

`        `except Exception:

`            `return None

`        `return None

Problema:

Qualquer erro (JSON malformado, UnicodeDecodeError, IOError, permissão) faz o

método retornar `None` SEM LOG NENHUM. O perfil simplesmente some de

`list\_profiles()` e `resolve\_profile()` retorna None depois → fluxo cascateia

para `EquipmentDetectionError` opaco.

Impacto:

\- Operador edita `config/contracts/equipment/7500\_extended.json` e deixa vírgula

`  `errada → equipamento "desaparece" silenciosamente → análise quebra com erro

`  `de detecção sem rastreio à causa real.

\- Risco operacional moderado em produção (lab depende desses contratos).

Recomendação:

Substituir por log estruturado:

`    `except Exception as exc:

`        `registrar\_log("EquipmentProfile",

`                      `f"Falha ao ler perfil {path.name}: {exc}", "ERROR")

`        `return None

Manter retorno None (não levantar) para não derrubar list\_profiles, mas

GARANTIR rastreabilidade.

Teste sugerido:

tests/test\_equipment\_profile\_service\_load\_failure.py — cria perfil JSON

inválido, assert (a) `list\_profiles()` não inclui esse perfil e (b) log foi

emitido com nível ERROR e nome do arquivo.

[MÉDIO] B2 — \_build\_details ignora silenciosamente data\_exame inválida

Evidência:

\- application/reports\_query\_use\_case.py:163-167

`    `data\_str = str(row.get("data\_exame") or "")

`    `try:

`        `data\_exame = date.fromisoformat(data\_str)

`    `except ValueError:

`        `continue

Problema:

Linha do SQLite com `data\_exame` corrompido (formato errado, string vazia,

NULL convertido em "None") é simplesmente removida do detalhamento sem log,

sem contador, sem aviso no DTO de saída.

Impacto:

\- Operador vê relatório com N linhas e não sabe que M foram descartadas.

\- Diverge de CA-R01..R10 (consistência entre summary e detail). O summary é

`  `calculado em outra fase (`execute`) com base em rows brutas, ANTES do filtro

`  `por data válida — risco de discrepância: "total=100, detalhe=87, sem

`  `explicação".

Recomendação:

Logar e contar:

`    `except ValueError:

`        `skipped\_invalid\_dates += 1

`        `registrar\_log("Reports", f"data\_exame invalida ignorada: {data\_str!r}",

`                      `"WARNING")

`        `continue

Considerar expor `skipped\_invalid\_dates` no ReportsResultDTO para a UI.

Teste sugerido:

tests/test\_reports\_query\_invalid\_date\_handling.py — repositório retorna 3

rows, 1 com data\_exame="abc". Assert: details tem 2 entradas; log WARNING

emitido; (se exposto) summary indica 1 descartada.

[MÉDIO] B3 — equipment\_extraction\_service tem dois `except Exception` amplos

Evidência:

\- application/equipment\_extraction\_service.py:79-82 (detecção)

\- application/equipment\_extraction\_service.py:119-130 (extração, com fallback

`  `legacy duplo-nível)

Problema:

Diferente de B1/B2, AQUI a exceção é wrapeada em `EquipmentDetectionError` /

`EquipmentExtractionFailure` (estruturada). Mas o `except Exception` perde a

classe original (TypeError vs FileNotFoundError vs PermissionError) e o tipo

não fica acessível em `\_\_cause\_\_` consistentemente.

Impacto:

\- Diagnóstico de erro em campo é mais difícil (motivo real escondido).

\- Pode mascarar bugs (ex.: AttributeError em adapter novo passa como

`  `"EquipmentExtractionFailure" genérico).

Recomendação:

Preservar causa: `raise EquipmentDetectionError(msg) from exc`. Verificar se

isto já está no código atual (subagente não detalhou); se não, adicionar.

Teste sugerido:

Mock que injeta TypeError no detector → assert que

`EquipmentDetectionError.\_\_cause\_\_` é TypeError.

**C. Tamanho / decomposição**

[MÉDIO] C1 — GalSendUseCase.execute concentra 6 passos + closure de 165 linhas

Evidência:

\- application/gal\_send\_use\_case.py:156-529 (execute = 374 linhas)

\- \_process\_row aninhada como closure: linhas 281-445 (~165 linhas)

\- Os 6 passos S10/S11/S20/S30/S40/S50/S60 estão TODOS dentro do mesmo método.

Problema:

\- Closure captura state local (idempotency, inflight\_keys, lock, journal) →

`  `difícil testar passos isoladamente.

\- Cobertura por passo exige mock pesado de GalSendServicePort.

\- Refactor pode quebrar GAL-ROB-001..010 se não houver suíte estática.

Impacto:

Manutenibilidade e testabilidade do passo mais crítico do sistema (envio GAL).

Recomendação:

Decompor em métodos privados: `\_step10\_validate\_csv`, `\_step20\_start\_driver`,

`\_step30\_login`, `\_step40\_metadata`, `\_step50\_dispatch\_workers`,

`\_step60\_finalize`. Manter `\_process\_row` como método de classe (não closure)

recebendo dependências explícitas. NÃO IMPLEMENTAR SEM rodada de refactor

SDD própria — código está sob GAL-ROB já concluído e qualquer mudança exige

guardião de regressão antes.

Teste sugerido:

tests/test\_gal\_send\_use\_case\_steps\_decomposition.py — testes unitários por

passo. Pré-requisito: refactor C1 concluído.

**D. Redundância & código morto**

[INFORMATIVO] D1 — Nenhum órfão detectado; mínima sobreposição funcional

Evidência:

Parte A do subagente confirmou consumidor de produção para os 17 módulos.

Sobreposição apenas semântica entre equipment\_extraction\_use\_case (escolha de

arquivo + parse) e equipment\_extraction\_service (dispatch de adapters); são

responsabilidades disjuntas.

Problema:

Nenhum.

Impacto:

Inexistente.

Recomendação:

Manter. Documentar em design.md a distinção entre use\_case e service de

extração (nuance importante para novos contribuidores).

Teste sugerido:

N/A.

[BAIXO] D2 — \_persist\_success\_immediately usa `# noqa: BLE001` justificado

Evidência:

\- application/gal\_send\_use\_case.py:555 `except Exception as exc:  # noqa: BLE001

`   `- caminho de hardening operacional`

Problema:

Nenhum efetivo — o `noqa` é justificado por comentário; a exceção é re-lançada

como RuntimeError com `from exc`. Boa prática.

Impacto:

Inexistente.

Recomendação:

Manter. Padrão correto a se replicar nos achados B1/B2.

Teste sugerido:

N/A.

**E. Testabilidade**

[ALTO] E1 — Cobertura direta da camada application/ é escassa em tests/

Evidência:

\- Parte A do subagente Explore: apenas `tests/test\_ui\_view\_models.py` aparece

`  `como teste direto de módulo da camada (cobre ui\_view\_models).

\- GAL-ROB-001..010 documentadas como concluídas em tasks.md citam testes

`  `indiretos (`tests/test\_phase\_u3\_gal\_send\_use\_case.py`).

\- Nenhum teste direto encontrado para: access\_control, reports\_query\_use\_case,

`  `reports\_contracts, equipment\_profile\_service, gal\_send\_use\_case (apenas

`  `fases U3).

Problema:

A camada mais crítica do sistema (GAL, Relatórios, Equipamentos, Autorização)

não tem suíte de testes unitários proporcional. Mudanças confiam em testes

de integração e auditoria humana.

Impacto:

\- Refactors necessários (C1) ficam arriscados.

\- Adições de novo CA (ex.: novo equipamento, novo filtro de relatório) podem

`  `introduzir regressão silenciosa.

\- Viola implicitamente CLAUDE.md §10 ("Mudança crítica sem teste de regressão

`  `é proibida").

Recomendação:

Em rodadas futuras de manutenção, criar PELO MENOS:

\- tests/test\_access\_control\_matrix.py (matriz operação×nível, fail-closed)

\- tests/test\_reports\_contracts\_normalize.py (from\_raw, ExamForaDoEscopoError,

`  `validação de range de datas)

\- tests/test\_equipment\_profile\_service\_resolve.py (resolve por alias/display)

\- tests/test\_reports\_query\_filters.py (positividade, status\_gal, paginação)

Cada um pode ser independente, em rodada própria.

Teste sugerido:

Já listado acima.

[MÉDIO] E2 — Guardião de "camada limpa" ausente

Evidência:

Não há teste que valide as restrições arquiteturais documentadas em

CLAUDE.md §6: `application/` não deve importar de `ui/` nem `tkinter`/

`customtkinter`/`seleniumrequests` (exceto factory de A2).

Problema:

Sem guardião, qualquer commit futuro pode reintroduzir dependência indevida

sem alerta automático.

Impacto:

Erosão silenciosa do padrão arquitetural. Risco aumenta com cada novo

contribuidor.

Recomendação:

tests/test\_application\_layer\_purity.py — AST scan que falhe se módulo em

application/ contiver: `from ui.`, `import ui`, `import tkinter`,

`import customtkinter`, `from selenium`, `import selenium`,

`from seleniumrequests`. Allowlist conhecida pode incluir apenas

`gal\_send\_use\_case.py` enquanto A2 não for resolvido.

Teste sugerido:

Já é o próprio teste.

-----
**Consolidação dos subagentes simulados**

|**Subagente**|**Veredicto**|
| :- | :- |
|**Arquiteto SDD**|Camada **canônica e madura**. Aderência alta a design.md §3.5/§3.7/§3.8, DEC-003/006, GAL-ROB-001..010. Ressalva A2 (Selenium em application).|
|**Bug Hunter**|3 swallowed exceptions sem log (B1, B2 confirmadas; B3 parcial). Alerta original sobre gal\_send\_use\_case:481 foi **descartado** após verificação — é fail-closed correto (GAL-ROB-001).|
|**Código Morto / Redundância**|Nenhum órfão. Sobreposição funcional mínima e justificada (D1).|
|**Especialista em Testes**|E1: cobertura direta escassa; E2: falta guardião de pureza da camada. Recomenda 5 suítes pequenas em rodadas futuras.|
|**Revisor de Enxutez**|16/17 módulos enxutos. Apenas gal\_send\_use\_case.execute (374 linhas) viola; decomposição em 6 passos privados melhoraria coesão sem alterar contrato.|

**Próximas decisões humanas relevantes**

Nenhuma DHP nova requerida. **DHPs pendentes que tangenciam** mas não bloqueiam esta camada:

- **DHP-10/11/12** (dados legados em dados/banco/ e banco\_template/) — não afetam código em application/, apenas runtime de produção.

**Resumo de ações priorizadas (todas READ-ONLY hoje; cada uma em rodada própria)**

1. **[ALTO]** B1 — adicionar registrar\_log no swallowed except de equipment\_profile\_service.\_load\_profile\_file.
1. **[MÉDIO]** B2 — logar/contar data\_exame inválida em reports\_query\_use\_case.\_build\_details.
1. **[MÉDIO]** B3 — verificar e adicionar from exc nas exceções estruturadas de equipment\_extraction\_service.
1. **[ALTO]** E1 — criar 4 suítes mínimas para access\_control, reports\_contracts, equipment\_profile\_service, reports\_query (uma rodada por suíte).
1. **[MÉDIO]** E2 — criar tests/test\_application\_layer\_purity.py (AST guardião).
1. **[MÉDIO]** A2 — mover \_default\_webdriver\_factory para services/gal/ (rodada conjunta com C1).
1. **[MÉDIO]** C1 — decompor GalSendUseCase.execute em 6 métodos privados (PRÉ-REQUISITO: E1 cobrir GAL primeiro).

Nenhuma alteração foi realizada nesta rodada.



**Auditoria SDD READ-ONLY — autenticacao/**

**1. Escopo analisado**

**Pasta alvo:** C:\Integragal - Backup - 20260128\_151811\autenticacao\

**Arquivos analisados (3 arquivos, ~52 KB):**

|**Arquivo**|**Linhas**|**Tamanho**|
| :- | :- | :- |
|[**init**.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/autenticacao/__init__.py)|0|0 B|
|[auth_service.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/autenticacao/auth_service.py)|1 073|38,0 KB|
|[login.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/autenticacao/login.py)|402|13,6 KB|

**Não analisados (e motivo):**

- usuarios.csv / credenciais.csv (legado): proibido por CLAUDE.md §9 (conteúdo sensível, hashes bcrypt + dados de usuários reais).
- \_\_pycache\_\_/\*.pyc: bytecode.
- Não foram lidas senhas/hashes literais; apenas a lógica.

**Arquivo correlato lido para contexto (NÃO é da pasta-alvo):**

- core/authentication/user\_manager.py (legado em deprecação controlada — DEC-003): cabeçalho + bloco \_\_main\_\_:1915-1935 apenas (confirmação de neutralização T-AUD-004B).
- test\_login.py na raiz do projeto: existência confirmada via Glob, conteúdo não detalhado (vide achado D2).

**Fontes SDD lidas:** CLAUDE.md §9/§15, AGENTS.md §15, .specify/memory/constitution.md, docs/specs/tasks.md (T-AUD-004/004A/004B/013/014, DEC-003, INST-004), docs/specs/requirements.md, notas\_de\_passagem.md.

-----
**2. Mapa da pasta**

autenticacao/

├─ \_\_init\_\_.py              (0 bytes — namespace vazio)

├─ auth\_service.py          (1 073 linhas — AuthService canônico, bcrypt, CSV-first)

└─ login.py                 (402 linhas — UI modal/embedded de login, CustomTkinter)

**Principais módulos & responsabilidades.**

|**Módulo**|**Responsabilidade canônica (DEC-003)**|
| :- | :- |
|AuthService (auth\_service.py:290)|Fonte ativa de autenticação. Lê/escreve usuarios.csv via PersistenceProvider+UserRepository com fallback csv\_io. Hashing **bcrypt**. Migração one-shot de credenciais.csv legado.|
|LoginDialog (login.py:~135)|Modal CustomTkinter sob grab\_set(). Coleta usuário/senha (show="\*"), chama AuthService.autenticar\_credenciais, loga, controla contador local de tentativas (3 em memória), no esgotamento faz \_on\_close(force\_exit=True) → sys.exit(1) indireto.|
|LoginPageEmbedded (login.py:265-402)|Variante embedded para Single Window/NavigationManager. Mesmo fluxo do dialog.|
|autenticar\_usuario(master) (login.py:~227)|Wrapper que cria root temporário se necessário, exibe LoginDialog, aguarda, retorna dict ou None.|

**Fluxos relevantes.**

1. **Login UI → AuthService → CSV** (entrypoint runtime):
   1. ui/main\_window.py:24 → autenticar\_usuario() → LoginDialog.verificar → AuthService.autenticar\_credenciais(usuario, senha) → load\_users\_df() (via PersistenceProvider ou fallback CSV) → bcrypt.checkpw(senha\_utf8, hash\_armazenado) → dict {usuario, nivel\_acesso, status, ...} ou None.
1. **Operações privilegiadas (autorização):**
   1. auth\_service.save\_users\_df / atualizar\_senha chamam application/access\_control.ensure\_operation\_allowed("users.mutate", access\_level) antes de persistir (auth\_service.py:440-445, 871).
1. **Migração legado:**
   1. unificar\_credenciais\_legadas() / executar\_migracao\_credenciais\_legadas() (auth\_service.py:896-1008) — comando operacional, não runtime.
1. **Sessão:** **NÃO existe nesta camada.** Função retorna dict; quem mantém estado é a UI (main\_window).

**Dependências internas.**

- application/access\_control (linhas 30-35) — matriz de autorização.
- domain/persistence\_contracts (linhas 36-44) — UserDTO, UserCreateDTO, UserUpdateDTO, UserAccessLevel, UserRepository (Protocol).
- domain/error\_codes (linha 45).
- services/persistence/persistence\_provider, services/persistence/csv\_io, services/core/error\_contracts, services/path\_resolver (linhas 46-52).
- utils/csv\_lock (CSVFileLock), utils/csv\_safety (sanitize\_csv\_value), utils/logger, utils/network\_io (linhas 53-56).
- login.py: from .auth\_service import AuthService; utils/after\_mixin, utils/gui\_utils, utils/logger, ui/components/base\_components.IGTextField, ui/theme.Theme (em LoginPageEmbedded).

**Dependências externas.**

- bcrypt (auth\_service.py:27) — hashing.
- pandas (auth\_service.py:28).
- csv, json, pathlib.Path, uuid, datetime.
- customtkinter, tkinter, PIL.Image (em login.py).

**Consumidores externos confirmados (8 callers de produção):** ui/main\_window.py:24, ui/menu\_handler.py:419, ui/admin\_panel.py, ui/user\_management.py, services/gal/history\_gal\_sync.py, exportacao/envio\_gal.py, scripts/run\_legacy\_credentials\_migration.py, test\_login.py (na raiz, vide D2).

**Legado relacionado.** core/authentication/user\_manager.py permanece fisicamente (1 935 linhas) mas em deprecação controlada (DEC-003). Bloco \_\_main\_\_:1915-1935 neutralizado com SystemExit(2). Zero imports runtime fora da própria pasta (guardião tests/test\_auth\_legacy\_user\_manager\_no\_runtime\_imports.py ativo — T-AUD-004A concluído).

-----
**3. Diagnóstico executivo**

**Coerência com SDD.** **Alta.** Pasta concretiza DEC-003 corretamente. auth\_service.py é a fonte canônica; legado neutralizado; guardiões T-AUD-004A/B passam. Integração com matriz de autorização application/access\_control.py documentada e usada.

**Enxutez.** **Insuficiente.** auth\_service.py tem 1 073 linhas e 3 funções acima de 50 linhas (uma com 113 linhas). login.py tem ~400 linhas com lógica de cleanup de Tk repetida em vários blocos try/except. Espaço claro para decomposição.

**Redundância.** **Baixa.** Há uma camada de fallback duplicada (PersistenceProvider → CSV direto) **necessária** (LIM-003: banco/\* em deprecação controlada). Migração legado mantida intencionalmente (DHP-11 pendente). Não há duplicação espúria.

**Bugs prováveis e fragilidades.** **Significativos.** Confirmados:

1. **Política de senha INEXISTENTE.** Schema do CSV reserva colunas tentativas\_falhas e bloqueado\_ate (auth\_service.py:67-68), são LIDAS para construir DTO (linha 520-521), mas **nunca incrementadas/setadas no fluxo de autenticação** (autenticar\_credenciais 667-743 não toca esses campos). O contrato persistido não é honrado.
1. **Throttling APENAS em memória cliente.** login.py:17 define MAX\_TENTATIVAS=3; LoginDialog.verificar:186 decrementa contador local; o atacante pode simplesmente reiniciar o app (ou abrir múltiplos processos) para zerar o contador. Lockout efetivo ausente.
1. **sys.exit(1) indireto via \_on\_close(force\_exit=True)** (login.py:204-205) — comportamento agressivo: ao esgotar tentativas o processo inteiro encerra. Não há mecanismo de desbloqueio em runtime.
1. **test\_login.py na raiz** — arquivo Python com nome de teste fora de tests/. Não é descoberto por pytest convencional; status indefinido (legado? smoke? esquecido?).

**Risco arquitetural.** **Médio.** Camada está no lugar certo (separada de UI e domínio), mas o tamanho do auth\_service.py e as 3 funções >50 linhas (incluindo uma de 113) sinalizam acúmulo. Migração legado precisa retornar a uma data-limite (HIG-009).

**Violação SDD.** Não há violação MATERIALIZADA. Mas há **promessa não cumprida**: as colunas tentativas\_falhas/bloqueado\_ate parecem prever uma política de lockout server-side que nunca foi implementada — viola implicitamente CONC-001/002/003 ("piloto controlado de 3-5 usuários", múltiplos processos compartilhando CSV). Em piloto isso é tolerável; em produção 10 usuários, **não**.

**Recomendação geral.** **AJUSTAR (pontual, médio impacto) + abrir DHP para política de senha.**

1. Implementar lockout server-side (escrita atômica em tentativas\_falhas/bloqueado\_ate sob CSVFileLock) — depende de **DHP nova** sobre política de senha (não implementar sem decisão humana).
1. Decompor auth\_service.py em sub-módulos por responsabilidade.
1. Definir destino de test\_login.py (mover para tests/ ou remover) — depende de inspeção do conteúdo.
1. Adicionar testes guardiões positivos (cobertura T-AUD-013 ainda pendente).
-----
**4. Notas 0–10**

|**Aspecto**|**Nota**|**Justificativa**|
| :- | :- | :- |
|Aderência SDD|**8**|DEC-003 totalmente implementada; legado corretamente neutralizado; T-AUD-004A/B concluídos. T-AUD-013 (cobertura complementar) pendente. INST-004 (ADMIN+MASTER) tangencial.|
|Arquitetura|**7**|Separação correta (autenticacao/ ≠ application/access\_control ≠ core/authentication legado). Boa hexagonalização via PersistenceProvider/UserRepository. Reduz nota: auth\_service.py muito grande (1 073 linhas, 3 funções acima de 50 linhas).|
|Clareza e Enxutez|**5**|auth\_service.py mistura: schema, normalização, IO CSV, IO provider, RBAC, hashing, migração legado. login.py repete blocos de cleanup de Tk em ~8 except.|
|Robustez|**5**|Hashing bcrypt CORRETO (sem comparação manual = sem timing attack). MAS: sem lockout server-side, sem força de senha, sem expiração, sem auditoria de falhas persistida. Para piloto: aceitável. Para produção: insuficiente.|
|Manutenibilidade|**6**|Tipagem ampla, DTOs do domínio, logging consistente. Tamanho dos arquivos reduz a nota.|
|Testabilidade|**3**|**Nenhum teste em tests/ importa autenticacao/** (confirmado pelo subagente). Único teste relacionado é o guardião AST de não-uso do legado. Há test\_login.py na raiz (descoberta acidental, não em pytest discovery). T-AUD-013 explicitamente pendente.|
|Risco Operacional|**5**|Em piloto 3-5 usuários: tolerável. Risco real em produção 10 usuários por (a) ausência de lockout server-side, (b) corrida em Read-Modify-Write multi-processo apesar do CSVFileLock, (c) sys.exit(1) no esgotamento de tentativas (impede recuperação graciosa).|
|Prontidão para Evolução|**6**|Hexagonalização via PersistenceProvider permite trocar CSV→SQLite sem refator de UI. Adicionar política de senha exige tocar autenticar\_credenciais (que já tem 77 linhas). Migração para JWT/token exigiria reescrita do contrato — não trivial.|
|**Geral**|**5,5**|Arquitetura SDD correta, hashing seguro, legado bem isolado. Mas **promessa de lockout não cumprida**, cobertura de testes inexistente, e tamanho dos módulos. Adequado para piloto; **não-pronto para produção 10 usuários** conforme CONC-001/002.|

-----
**5. Achados detalhados**

**A. Segurança & política de credenciais**

[ALTO] A1 — Promessa de lockout server-side não cumprida

Evidência:

\- autenticacao/auth\_service.py:67-68 (colunas no schema CSV)

`    `"tentativas\_falhas", "bloqueado\_ate"

\- autenticacao/auth\_service.py:520-521 (LEITURA para construir DTO)

`    `failed\_attempts = \_safe\_int(row.get("tentativas\_falhas"), 0)

`    `locked\_until = str(row.get("bloqueado\_ate", "") or "").strip() or None

\- Grep "tentativas\_falhas|bloqueado\_ate" em auth\_service.py: aparece em

`  `schema/leitura (linhas 67, 68, 87, 88, 162, 163, 268, 269, 520, 521)

`  `e em NENHUM ponto dentro de `autenticar\_credenciais()` (667-743) ou

`  ``verificar\_senha()` (745+) — nunca INCREMENTADAS/SETADAS no fluxo de login.

Problema:

O CSV de usuários reserva campos para política de lockout, o DTO os transporta,

mas o fluxo de autenticação nunca escreve. Logo, lockout server-side é fictício.

Impacto:

\- Atacante pode tentar senhas indefinidamente — bcrypt mitiga só por custo

`  `computacional, mas não bloqueia.

\- Quem cumprir CONC-002 (10 usuários, multi-processo) sem lockout real verá

`  `brute-force tornar-se viável (especialmente porque CSVs são compartilhados).

\- Auditoria pós-incidente impossível: não há trilha de "X tentativas falhas

`  `para usuário Y" persistida.

Recomendação:

ABRIR DHP NOVA sobre política de senha/lockout: definir (a) limite N de

tentativas antes de bloqueio, (b) duração do bloqueio, (c) como administrador

desbloqueia. NÃO IMPLEMENTAR SEM DECISÃO HUMANA. Política deve casar com

INST-004 (ADMIN+MASTER) e CONC-001 (piloto 3-5 → 10 usuários).

Teste sugerido:

tests/test\_auth\_lockout\_persistence.py — após 3 falhas:

(a) usuarios.csv tem tentativas\_falhas=3,

(b) bloqueado\_ate é timestamp futuro,

(c) próxima chamada a autenticar\_credenciais retorna None mesmo com senha

correta antes do bloqueado\_ate expirar.

[ALTO] A2 — Throttling existe APENAS em memória do cliente

Evidência:

\- autenticacao/login.py:17  `MAX\_TENTATIVAS = 3`

\- autenticacao/login.py:186 `self.tentativas\_restantes -= 1`

\- autenticacao/login.py:198-205 esgotado → `\_on\_close(force\_exit=True)`

\- O contador `tentativas\_restantes` é atributo de instância do LoginDialog

`  `(criada a cada chamada de `autenticar\_usuario`). Reinício do app = reset.

Problema:

Quem reinicia o aplicativo zera o contador. Quem abre múltiplos processos

contorna trivialmente. Sem nexo com servidor (que não persiste — vide A1).

Impacto:

Mesmo do A1. Throttling de UI sem persistência server-side é cosmético contra

brute-force determinado. Ainda assim, FALSO SENSO de proteção pode adiar a

implementação real.

Recomendação:

Manter contador local (boa UX), mas A1 (lockout server-side) é o real fix.

Resolver junto à DHP de política de senha. NÃO IMPLEMENTAR SEM DECISÃO HUMANA.

Teste sugerido:

tests/test\_login\_throttling\_clientside\_only.py — assert que reinstanciar

LoginDialog reseta `tentativas\_restantes` para MAX\_TENTATIVAS, evidenciando

o limite da proteção (documenta a fragilidade).

[MÉDIO] A3 — sys.exit(1) indireto no esgotamento de tentativas

Evidência:

\- autenticacao/login.py:204-205

`    `self.usuario\_autenticado = None

`    `self.\_on\_close(force\_exit=True)

\- (force\_exit=True chama `sys.exit(1)` indiretamente — confirmado por linha

`  `4 `import sys` e padrão observado em outros pontos)

Problema:

Encerrar o processo Python por falha de login é agressivo. Impede recuperação

graciosa, fecha a janela principal junto, perde estado em memória de outros

módulos UI eventualmente carregados.

Impacto:

\- Operacional: usuário trabalhando em outra janela perde estado.

\- Auditoria/teste: difícil simular múltiplos cenários sem matar o pytest.

\- Cobertura: testes que exercitarem login podem matar o runner.

Recomendação:

Substituir `force\_exit=True` por sinal de bloqueio que fecha SOMENTE o dialog

e marca sessão como bloqueada, deixando a recuperação para a camada superior.

Compatível com A1 (lockout server-side dita o desbloqueio).

Teste sugerido:

tests/test\_login\_no\_systemexit\_on\_lockout.py — patch sys.exit e assert que

nunca é chamado durante fluxo de login, mesmo após N falhas.

[BAIXO] A4 — Comparação de hash usa bcrypt.checkpw (correto, sem timing attack)

Evidência:

\- autenticacao/auth\_service.py:720, 791  `bcrypt.checkpw(senha\_utf8, hash)`

\- bcrypt.checkpw retorna bool diretamente; não há comparação manual de

`  `bytes com `==`.

Problema:

Nenhum. Observação positiva.

Impacto:

Bom design.

Recomendação:

Manter. Não substituir por `hmac.compare\_digest` em outras comparações de

hash sem necessidade.

Teste sugerido:

N/A.

**B. Encoding / normalização**

[MÉDIO] B1 — Normalização de username inconsistente entre métodos

Evidência:

\- \_normalize\_username() definido em auth\_service.py:95

\- Usado em obter\_usuario()? Resposta do subagente: NÃO. obter\_usuario usa

`  ``.str.strip().str.lower()` inline (linhas 654, 703, 776).

\- Resultado: dois caminhos de normalização paralelos no mesmo arquivo.

Problema:

Comportamentos podem divergir se um caminho for endurecido (ex.: NFKD) e o

outro não. Já hoje uma diferença sutil em strip de caracteres invisíveis

poderia permitir bypass — pouco provável, mas mensurável.

Impacto:

Risco baixo de inconsistência de comparação de username (ex.: usuário com

zero-width-space salvo no CSV não bate com input limpo).

Recomendação:

Substituir todos os usos inline pelo `\_normalize\_username()` único.

Rodada pequena, sem dependência de DHP.

Teste sugerido:

tests/test\_auth\_username\_normalization\_consistency.py — parametrizar com

["admin", "ADMIN ", " admin", "admin\u200b"] → todos devem resolver para

o mesmo registro.

**C. Arquitetura & tamanho**

[MÉDIO] C1 — auth\_service.py com 1 073 linhas e 3 funções acima de 50 linhas

Evidência:

\- autenticacao/auth\_service.py:1-1073

\- Funções >50 linhas (subagente confirmou):

`  `- `\_save\_users\_df\_via\_contract` (492-572): 81 linhas

`  `- `autenticar\_credenciais` (667-743): 77 linhas

`  `- `unificar\_credenciais\_legadas` (896-1008): 113 linhas

Problema:

Módulo concentra schema CSV, normalização, IO via provider, IO direto, RBAC,

hashing, migração one-shot legado e mapeamento DTO. Difícil revisar, difícil

testar, alto risco de regressão em mudanças.

Impacto:

Manutenibilidade e cobertura de testes (vide D1) ficam comprometidas.

Recomendação:

Decompor em rodada SDD futura em:

\- autenticacao/\_schema.py (colunas, defaults, normalizadores)

\- autenticacao/\_csv\_io.py (load\_users\_df, save\_users\_df via provider/fallback)

\- autenticacao/\_auth.py (autenticar\_credenciais, verificar\_senha)

\- autenticacao/\_migration\_legacy.py (unificar\_credenciais\_legadas e

`  `executar\_migracao\_credenciais\_legadas)

\- autenticacao/auth\_service.py (facade, mantém superfície pública)

NÃO IMPLEMENTAR SEM testes T-AUD-013 cobrindo o comportamento atual ANTES.

Teste sugerido:

Pré-requisito: T-AUD-013 (cobertura complementar).

[BAIXO] C2 — login.py com ~8 blocos try/except idênticos em cleanup Tk

Evidência:

\- autenticacao/login.py:41-65 `\_fechar\_dialogo\_login`

\- autenticacao/login.py:71-130 `\_cleanup\_login\_modal\_state` (8 blocos)

\- `\_is\_benign\_tk\_destroy\_error` (linhas 20-32) já define os erros aceitos.

Problema:

Pattern correto (lidar com erros benignos do ciclo de vida Tk em destruição),

mas repetido. Refactor leve em um único helper traria robustez sem mudança

funcional.

Impacto:

Clareza e enxutez apenas.

Recomendação:

Extrair `\_safe\_tk\_call(callable, \*, ignore\_benign=True)` e reusar nos 8

pontos.

Teste sugerido:

tests/test\_login\_safe\_tk\_cleanup.py — mock que injeta TclError com

mensagens benignas → assert que helper engole; com mensagens novas →

assert que propaga.

**D. Testabilidade & código órfão**

[ALTO] D1 — Zero testes em tests/ importam autenticacao/

Evidência:

\- Subagente Parte B: "Nenhum import de `autenticacao/` encontrado em

`  `diretório `tests/`."

\- tasks.md T-AUD-013 PENDENTE: "cobertura complementar de callers/guardiões

`  `de autenticação após DEC-003" (CLAUDE.md §10).

\- Único teste relacionado: tests/test\_auth\_legacy\_user\_manager\_no\_runtime\_imports.py

`  `(T-AUD-004A) — guardião AST do legado, não testa fluxo positivo.

Problema:

A camada de autenticação canônica, com hashing bcrypt e RBAC, não tem suíte

de regressão. Qualquer ajuste em A1/A2/A3/B1/C1 fica arriscado.

Impacto:

\- Alterações futuras silenciosamente quebrarão login.

\- T-AUD-013 explicitamente PENDENTE no SDD.

\- Refatorações grandes (C1) ficam bloqueadas até cobertura existir.

Recomendação:

Em rodada T-AUD-013, criar mínimos:

\- tests/test\_auth\_service\_authenticate\_success.py

\- tests/test\_auth\_service\_authenticate\_wrong\_password.py

\- tests/test\_auth\_service\_authenticate\_unknown\_user.py

\- tests/test\_auth\_service\_load\_with\_legacy\_fallback.py

\- tests/test\_login\_dialog\_three\_attempts\_then\_lockout.py

Mantém autenticacao/ funcional para o piloto.

Teste sugerido:

Listados acima.

[MÉDIO] D2 — test\_login.py na RAIZ do projeto (fora de tests/)

Evidência:

\- Glob `\*\*/test\_login.py` retorna `test\_login.py` (raiz do repo).

\- Não está em `tests/`. Pytest discovery padrão pode ignorar ou ambíguo.

\- Subagente Parte B confirmou: "test\_login.py:2 `from autenticacao.auth\_service

`  `import AuthService`".

Problema:

Arquivo de teste no nome, posição não-canônica. Status incerto: pode ser

smoke obsoleto, script de migração, scratch esquecido.

Impacto:

\- Confusão para novos contribuidores.

\- Risco de execução acidental ou de ser pego em coverage indevidamente.

\- Possível conteúdo desatualizado mascarando comportamento atual.

Recomendação:

Inspeção humana antes de qualquer ação. Decidir:

(a) mover para tests/test\_login\_smoke.py (se relevante) ou

(b) remover (rodada própria, símil HIG-007 — apenas após DHP-XX, NÃO

`   `implementar sem decisão humana).

Esta auditoria limita-se a SINALIZAR.

Teste sugerido:

N/A (a decisão é de housekeeping).

[INFORMATIVO] D3 — Legado core/authentication/user\_manager.py corretamente neutralizado

Evidência:

\- core/authentication/user\_manager.py:1915-1935

`    `if \_\_name\_\_ == "\_\_main\_\_":

`        `print("...legacy module in controlled deprecation...")

`        `raise SystemExit(2)

\- Único arquivo da pasta `core/authentication/`.

\- Guardião AST tests/test\_auth\_legacy\_user\_manager\_no\_runtime\_imports.py

`  `passa com allowlist vazia (T-AUD-004A concluído).

Problema:

Nenhum.

Impacto:

Confirma DEC-003. Boa governança de deprecação.

Recomendação:

Manter. Não remover fisicamente sem DEC nova (CLAUDE.md §15 / §9).

Teste sugerido:

Já existe.

**E. Conformidade com decisões pendentes**

[INFORMATIVO] E1 — INST-004 toca esta camada e está PENDENTE

Evidência:

\- CLAUDE.md §16 / AGENTS.md §16 (lista de pendentes):

`  `"INST-004 - ajustar Instalacao Inicial para ADMIN+MASTER com confirmacao

`   `forte, log/auditoria e backup previo futuro."

\- Já existe ensure\_operation\_allowed("users.mutate") em

`  `auth\_service.py:440-445.

Problema:

Nenhum agora (tarefa registrada). Lembrete de que mudanças nesta camada

podem precisar coordenar com INST-004.

Impacto:

Nenhum imediato.

Recomendação:

Ao endereçar A1 (política de senha) ou C1 (refactor), considerar INST-004

no mesmo movimento — economiza rodadas.

Teste sugerido:

N/A.

-----
**Consolidação dos subagentes simulados**

|**Subagente**|**Veredicto**|
| :- | :- |
|**Arquiteto SDD**|DEC-003 plenamente implementada; legado neutralizado; T-AUD-004A/B concluídos. T-AUD-013 pendente é a maior lacuna documental.|
|**Bug Hunter**|A1 (lockout server-side não cumprido) e A2 (throttling cosmético) são os mais sérios; A3 (sys.exit(1)) preocupa para teste. B1 (normalização) e C2 (cleanup Tk) são corretos mas inconsistentes.|
|**Código Morto / Redundância**|Não há órfãos dentro de autenticacao/. Há fallback legacy intencional (LIM-003/DEC-002). test\_login.py na raiz é candidato a housekeeping (D2).|
|**Especialista em Testes**|Cobertura DIRETA = zero. Precisa pelo menos 5 suítes pequenas (D1). T-AUD-013 deveria já ter sido executada.|
|**Revisor de Enxutez**|auth\_service.py precisa decomposição (C1, 1 073 linhas, função de 113 linhas). login.py pode beneficiar de helper de cleanup (C2).|

**Próximas decisões humanas (resumo)**

1. **DHP nova — política de senha/lockout** (depende de CONC-001..003 e INST-004). Define: limite de tentativas server-side, duração de bloqueio, recuperação, exigências mínimas (comprimento, complexidade). **Sem isso, A1/A2/A3 não devem ser tocados.**
1. **DHP de housekeeping para test\_login.py na raiz** — inspeção e decisão (mover/remover).
1. **T-AUD-013** — pré-requisito para C1 (refactor) e bloqueio efetivo de regressão em A1/A2/A3.

**Resumo de ações priorizadas**

1. **[ALTO] T-AUD-013** — criar 5 suítes mínimas de teste positivo/negativo (item D1).
1. **[ALTO] DHP nova** — política de senha/lockout (cobre A1, A2, A3).
1. **[MÉDIO] B1** — uniformizar normalização de username (rodada pequena, sem DHP).
1. **[MÉDIO] D2** — inspecionar test\_login.py da raiz (DHP de housekeeping).
1. **[MÉDIO] C1** — decompor auth\_service.py (depende de D1).
1. **[BAIXO] C2** — extrair helper \_safe\_tk\_call em login.py.

Nenhuma alteração foi realizada nesta rodada. Hashes, senhas e usuários reais NÃO foram lidos nem citados.



**Auditoria SDD READ-ONLY — config/**

**1. Escopo analisado**

**Pasta alvo:** C:\Integragal - Backup - 20260128\_151811\config\

**Arquivos analisados (44 arquivos, ~143 KB):**

|**Subgrupo**|**Arquivos**|**Notas**|
| :- | :- | :- |
|Python|9|\_\_init\_\_, business\_rules, column\_constants, ct\_thresholds, enums, feature\_flags, paths, settings, ui\_theme|
|JSON top-level|4|default\_config.json, feature\_flags.json, config\_old.json, ui\_boundary\_allowlist.json|
|Backups|10|config/backups/config\_backup\_2026052[7-9]\_\*.json e 2026053[0]\_\*.json|
|Contratos|12|config/contracts/{equipment,exams,gal,analysis\_rules,storage}/\*.json + 5 schemas|
|Exames|9|config/exams/\*.json (2 canônicos + 5 suspeitos + schema + template)|

**Não analisados (e motivo):**

- Conteúdo completo de cada JSON de backup (10) — bastou amostra (mais antigo + mais recente).
- \_\_pycache\_\_/\*.pyc.
- Nenhum arquivo dentro de config/ é sensível (sem credenciais/tokens neste diretório; URL pública GAL é informativa).

**Fontes SDD lidas:** CLAUDE.md §7/§9/§12-§16, AGENTS.md §15/§16, docs/specs/requirements.md (CA-12, LIM-001..003), docs/specs/design.md (§3.6/§3.7/§3.10), docs/specs/tasks.md (LOG-UNIF-001/002, CONFIG-PATH-001, INST-001..005, DEC-001/006), notas\_de\_passagem.md.

-----
**2. Mapa da pasta**

config/

├─ \_\_init\_\_.py                            (reexporta feature\_flags singleton)

├─ business\_rules.py                      (constantes CT — DUPLICA ct\_thresholds.py)

├─ column\_constants.py                    (RESULT\_PREFIX, normalizações)

├─ ct\_thresholds.py                       (CTThresholdsVR1E2 dataclass — DUPLICA business\_rules)

├─ enums.py                               (ResultStatus enum)

├─ feature\_flags.py                       (397 linhas — singleton, 17 flags hardcoded + JSON override)

├─ paths.py                               (28 linhas — ÓRFÃO, mkdir em import-time)

├─ settings.py                            (555 linhas — ConfigurationManager DEPRECATED)

├─ ui\_theme.py                            (UI\_COLORS por resultado)

│

├─ default\_config.json                    (canônico — DEC-001 template/local runtime)

├─ feature\_flags.json                     (override do hardcoded em feature\_flags.py)

├─ config\_old.json                        (8.1 KB — ÓRFÃO TOTAL: zero consumidores)

├─ ui\_boundary\_allowlist.json             (148 B — fora de uso conhecido)

│

├─ backups/                               (10 snapshots de config.json; cap=10 em settings.py)

│

├─ contracts/                             (DEC-006 — fonte canônica de equipamentos/exames)

│  ├─ schema.equipment\_profile.json       (18 campos obrigatórios)

│  ├─ schema.exam\_profile.json            (10 campos obrigatórios)

│  ├─ schema.gal\_profile.json             (5 campos obrigatórios)

│  ├─ schema.analysis\_rules\_profile.json

│  ├─ schema.storage\_profile.json

│  ├─ equipment/

│  │  ├─ 7500\_extended.json               (active=true — CANÔNICO)

│  │  ├─ abi\_7500.json                    (active=false — legado)

│  │  ├─ quantstudio.json                 (active=true — CANÔNICO)

│  │  └─ template\_equipment\_profile.json

│  ├─ exams/

│  │  ├─ zdcbm.json                       (CANÔNICO formato novo)

│  │  └─ template\_exam\_profile.json

│  ├─ gal/

│  │  ├─ zdcbm.json

│  │  └─ template\_gal\_profile.json

│  ├─ analysis\_rules/

│  │  ├─ zdcbm.json

│  │  └─ template\_analysis\_rules\_profile.json

│  └─ storage/

│     └─ default\_storage\_profile.json

│

└─ exams/                                 (formato ANTIGO — carregado por ExamRegistry)

`   `├─ schema.json                         (schema legado fora de contracts/)

`   `├─ template\_exame.json

`   `├─ vr1e2\_biomanguinhos\_7500.json       (CANÔNICO — active\_exams)

`   `├─ zdcbm.json                          (DUPLICA contracts/exams/zdcbm.json — schemas distintos)

`   `├─ 123.json                            (LIXO — alvos "aaaa", "TTTTT", "ZZZZ")

`   `├─ 2134.json                           (LIXO)

`   `├─ d2ed2.json                          (LIXO)

`   `├─ tara.json                           (LIXO — alvos "ss", "xx", "jytj", "wefgwgeg")

`   `└─ xxb.json                            (LIXO — alvos "xx", "bel", "ddddd")

**Responsabilidades percebidas.** Camada de configuração com **3 fontes de verdade coexistindo**:

1. **services/core/config\_service** (referenciado por settings.py) — canônico para config.json runtime.
1. **config/contracts/\*** (DEC-006) — canônico para perfis de equipamento/exame/GAL.
1. **config/exams/\*** (legado) — formato antigo ainda iterado por services/exam\_registry.py:507 (for path in EXAMS\_DIR.iterdir()).

**Fluxos relevantes.**

- **Boot:** config/\_\_init\_\_.py cria singleton feature\_flags → feature\_flags.py:\_load\_from\_file lê feature\_flags.json (com override sobre defaults hardcoded de 17 flags).
- **Settings runtime (legado):** ui/modules/tela\_configuracoes.py:13 → config.settings.configuracao → ConfigurationManager carrega default\_config.json + JSON do usuário, persiste backups em config/backups/ (cap=10, FIFO). DEPRECATED (warnings nas linhas 490-554).
- **Equipamento (canônico DEC-006):** UI/UseCases → application/equipment\_profile\_service → itera config/contracts/equipment/\*.json filtrando active=true.
- **Exame (DUPLO):**
  - via legado: services/exam\_registry.py:507 itera config/exams/\*.json (todos, sem filtro active).
  - via DEC-006: config/contracts/exams/\*.json (apenas zdcbm + template hoje).
- **Paths:** config/paths.py é **órfão** (zero consumidores Python); o canônico é services/system\_paths.py e services/path\_resolver.py (LOG-UNIF-002).

**Dependências internas — saídas.** config/feature\_flags.py, config/settings.py, config/ui\_theme.py importam de utils.\*, services.\*. Nenhum import circular detectado.

**Dependências externas.** json, pathlib, shutil, threading, hashlib, warnings, datetime. Sem deps pesadas.

**Consumidores externos (síntese):**

- **Amplamente usados:** feature\_flags (5+ callers em GAL, runtime\_flags, operacional), business\_rules (4+ callers em análise/UI/domain), enums (3+ callers).
- **Pontuais:** settings (2 callers, deprecated), ct\_thresholds (2 callers), column\_constants, ui\_theme (1 caller cada).
- **Órfãos:** paths.py (zero callers Python), config\_old.json (zero callers), ui\_boundary\_allowlist.json (status incerto).
-----
**3. Diagnóstico executivo**

**Coerência com SDD.** **Mista.** O lado novo (DEC-006 config/contracts/, INST-001/002/003, LOG-UNIF-001/002, CONFIG-PATH-001) está alinhado e bem documentado. O lado legado (config\_old.json, config/paths.py, config/settings.py deprecated, schema antigo em config/exams/) coexiste sem barreira nem deadline.

**Enxutez.** **Insuficiente.** settings.py tem 555 linhas marcadas como deprecadas mas ainda usadas; feature\_flags.py tem 397 linhas com 17 flags hardcoded; business\_rules.py e ct\_thresholds.py definem **as mesmas constantes CT** em paralelo sem sincronização. Total: ~50 KB de código + ~26 KB de JSON top-level.

**Redundância.** **Alta.** Quatro duplicações verificáveis:

1. business\_rules.py ↔ ct\_thresholds.py (constantes CT — risco de divergência).
1. config/exams/zdcbm.json (schema antigo kit\_codigo/alvos/mapa\_alvos) ↔ config/contracts/exams/zdcbm.json (schema novo exam\_id/contract\_version/targets/target\_aliases).
1. config/settings.py.ConfigurationManager ↔ services/core/config\_service (duas APIs para o mesmo arquivo).
1. config/paths.py ↔ services/system\_paths.py/services/path\_resolver.py.

**Bugs prováveis.**

1. **config/paths.py:26-27 cria diretórios em import-time** — se permissão negada, processo aborta antes do logger inicializar; sem fallback nem mensagem útil. Hoje é mitigado por ser órfão.
1. **config/feature\_flags.py:\_load\_from\_file e \_save\_to\_file engolem except Exception** (linhas 359, 371) — operador edita feature\_flags.json com vírgula errada → flag retorna ao hardcoded silenciosamente; comportamento muda sem aviso.
1. **ExamRegistry carrega exames lixo** (123.json, 2134.json, d2ed2.json, tara.json, xxb.json) confirmado via services/exam\_registry.py:74,507 (for path in EXAMS\_DIR.iterdir()). Hoje é mitigado por active\_exams no runtime real (CA-09/CA-10), mas o registry está poluído.
1. **config/settings.py usa @safe\_operation em quase todos os pontos críticos** — silencia falhas de carregar/salvar config (fail-open).

**Risco arquitetural.** **Alto.** Três fontes de verdade coexistindo + zero deadline de unificação. Cada deploy novo arrisca usar a fonte errada para um campo.

**Violação SDD.** **Materializada parcialmente.**

- config\_old.json mantém seção postgres.enabled=false — viola implicitamente CLAUDE.md §7 ("Postgres dedicado nao deve ser usado (provider nao implementado)"). O =false está correto, mas a SEÇÃO existe e pode ser reativada por engano.
- config/exams/{123,2134,d2ed2,tara,xxb}.json materializa exames fora do escopo active\_exams — viola §2 ("Qualquer outro exame esta fora de escopo operacional"). Mitigado por active\_exams em runtime, mas registry carrega.

**Recomendação geral.** **AJUSTAR fortemente, mas em rodadas SDD separadas com DHPs.**

1. Abrir **DHP nova** para deprecar config\_old.json, config/paths.py, config/settings.py com deadline e plano de migração.
1. Abrir **DHP nova** para definir destino dos 5 exames-lixo e do schema antigo config/exams/zdcbm.json (escolher uma das duas fontes).
1. Unificar business\_rules.py e ct\_thresholds.py em uma única fonte com migração coordenada (4 consumidores).
1. Endurecer logging em swallowed exceptions de feature\_flags.py.
-----
**4. Notas 0–10**

|**Aspecto**|**Nota**|**Justificativa**|
| :- | :- | :- |
|Aderência SDD|**6**|Lado novo (contracts/, DEC-006, INST-001..003, LOG-UNIF-001/002, CONFIG-PATH-001) totalmente alinhado. Lado legado coexiste sem DHP/deadline.|
|Arquitetura|**5**|3 fontes de verdade simultâneas. Singleton de feature\_flags thread-unsafe. Side effect de mkdir em import-time (órfão).|
|Clareza e Enxutez|**5**|settings.py (555 linhas, deprecated mas ativo) + feature\_flags.py (397 linhas) + duplicações de constantes CT + 5 exames-lixo.|
|Robustez|**5**|INST-001..003 corretos (lock atomic + dry-run + backup). MAS: @safe\_operation genérico em settings, except Exception swallowed em feature\_flags I/O, paths.py mkdir sem tratamento.|
|Manutenibilidade|**5**|Defaults hardcoded em 3 lugares (business\_rules, ct\_thresholds, feature\_flags). Mudar threshold CT exige tocar 2 arquivos.|
|Testabilidade|**5**|Guardiões LOG-UNIF-001 (tests/test\_log\_paths\_uniformization.py 9 passed) e LOG-UNIF-002 (tests/test\_banco\_path\_fallbacks.py 7 passed) cobrem paths. Não há teste de schema dos JSONs nem de "consistência entre business\_rules e ct\_thresholds".|
|Risco Operacional|**5**|Backup automático (INST-003) reduz risco. config\_old.json com postgres.enabled ainda lá é gatilho potencial de reativação acidental. Exames lixo poluem registry.|
|Prontidão para Evolução|**5**|Contracts/ + schemas/ pavimentam o caminho certo. MAS a migração das fontes legadas não tem cronograma; cada PR precisa decidir qual fonte usar.|
|**Geral**|**5,5**|Camada com base SDD sólida (contracts/, INST-001..003, LOG-UNIF, CONFIG-PATH-001), mas **convivência indefinida com legado** (config\_old.json, config/exams/ antigo, settings.py deprecado, paths.py órfão) reduz a nota. Não-pronto para deprecação automática — exige rodadas DHP coordenadas.|

-----
**5. Achados detalhados**

**A. Legado órfão & duplicação**

[ALTO] A1 — config\_old.json é ÓRFÃO TOTAL no código Python

Evidência:

\- C:\Integragal - Backup - 20260128\_151811\config\config\_old.json (8.1 KB)

\- Grep "config\_old" no repo inteiro retorna 1 match: `.gitignore`.

`  `Zero código Python referencia este arquivo.

\- Conteúdo contém: data\_root com path absoluto Windows hardcoded

`  `(c:\\Integragal - Backup - 20260128\_151811\\dados), seção postgres

`  `(com `enabled: false`, mas o bloco existe), URL produção GAL

`  `(`https://gal.saude.sc.gov.br`), credenciais com placeholders, e

`  ``active\_exams: ["VR1e2 Biomanguinhos 7500", "ZDC BioManguinhos"]`.

Problema:

Arquivo presente fisicamente, sem consumidor. Define duas coisas que SDD

explicitamente proibiu/deprecou: (a) bloco `postgres` (CLAUDE.md §7),

(b) paths absolutos hardcoded.

Impacto:

\- Risco de reativação acidental (alguém faz `import json; json.load(...)`).

\- Confusão para novos contribuidores ("qual config é a verdadeira?").

\- Auditoria de governança: arquivo com credenciais-placeholder não pertence

`  `a versionamento sem DEC explícita.

Recomendação:

ABRIR DHP NOVA para destino de `config\_old.json`. Opções:

(A) mover para docs/obsoletos/ (símil HIG-006);

(B) remover fisicamente (rodada própria, sem precedente);

(C) renomear com prefixo `\_LEGACY\_` e adicionar README local.

NÃO IMPLEMENTAR SEM DECISÃO HUMANA. Política DEC-002/DEC-004 sugere

preservar sem remoção automática.

Teste sugerido:

tests/test\_config\_old\_no\_runtime\_imports.py — guardião AST que falhe

se algum .py em runtime contiver `"config\_old.json"` literal.

[ALTO] A2 — Exames lixo em config/exams/ são carregados pelo ExamRegistry

Evidência:

\- services/exam\_registry.py:74  EXAMS\_DIR = BASE\_DIR / "config" / "exams"

\- services/exam\_registry.py:507  for path in EXAMS\_DIR.iterdir():

\- Exames detectados sem semântica:

`  `- 123.json:    nome="qefqefqfwf121", alvos=["aaaa","TTTTT","ZZZZ","RP"]

`  `- 2134.json:   (similar nonsense)

`  `- d2ed2.json:  (similar nonsense)

`  `- tara.json:   nome="teste tarantela", alvos=["ss","xx","ci","yy","jytj","wefgwgeg","geqg1ef1"]

`  `- xxb.json:    nome="xuxubelkezaxxb", alvos=["xx","bel","xxb","ddddd","rp"]

\- Nenhum campo `active` nesses JSONs (grep "active" em config/exams/ → 0 matches).

Problema:

Registry carrega TODOS os exames de config/exams/, incluindo fixtures

de teste deixadas pelo wizard. O filtro `active\_exams` (do config.json)

roda em runtime real e bloqueia execução fora de escopo, MAS o registry

em memória contém esses exames poluídos.

Impacto:

\- UI de seleção de exame pode listar nonsense.

\- Stubs de teste podem retornar `True` para qualquer exame (CA-10).

\- Risco de pollution se algum caller iterar `list\_exams()` sem filtrar.

\- Viola CLAUDE.md §2 (escopo ativo) materialmente no registry, mesmo

`  `com runtime protegido.

Recomendação:

ABRIR DHP NOVA para destino dos 5 exames-lixo + schema antigo

config/exams/zdcbm.json. Opções:

(A) mover para tests/fixtures/exams/ (apropriado se forem fixtures);

(B) remover fisicamente (rodada própria);

(C) adicionar campo `active: false` em cada um (mais conservador).

NÃO IMPLEMENTAR SEM DECISÃO HUMANA. Antes da DHP, considerar guardião

de teste que detecte exames novos sem `active`.

Teste sugerido:

tests/test\_exams\_directory\_only\_canonical.py — falhar se config/exams/\*.json

contiver exam\_name fora de {VR1e2 Biomanguinhos 7500, ZDC BioManguinhos,

TEMPLATE, SCHEMA}.

[ALTO] A3 — Duplicação real: config/exams/zdcbm.json vs config/contracts/exams/zdcbm.json

Evidência:

\- config/exams/zdcbm.json (formato antigo):

`    `"nome\_exame", "kit\_codigo": 1832, "alvos": [...], "mapa\_alvos": {...}

\- config/contracts/exams/zdcbm.json (formato DEC-006):

`    `"exam\_id": "zdcbm", "contract\_version": "1.0.0",

`    `"equipment\_id": "7500\_extended", "targets": [...], "target\_aliases": {...}

\- Ambos com o mesmo "slug": "zdcbm". Schemas distintos.

Problema:

Dois arquivos canônicos para ZDC com schemas diferentes. Qualquer divergência

(novo alvo, alteração de mapeamento) precisa ser feita em DOIS lugares e não

há guardião que detecte inconsistência.

Impacto:

\- Risco real de divergência clínica (Resultado\_geral pode usar mapa antigo

`  `enquanto envio GAL usa o novo).

\- Viola DEC-006 implicitamente (contracts/ deveria ser único canônico, mas

`  `exam\_registry ainda lê o antigo).

Recomendação:

ABRIR DHP NOVA para definir qual é canônico:

(A) contracts/ vence — config/exams/zdcbm.json passa a ser shim que aponta

`    `para contracts/, ou é removido após migração de exam\_registry;

(B) manter ambos com guardião de paridade automatizado.

Decisão liga-se a A2. NÃO IMPLEMENTAR SEM DHP coordenada.

Teste sugerido:

tests/test\_zdcbm\_dual\_schema\_parity.py — carregar ambos os arquivos,

extrair {alvos, mapa\_alvos→target\_aliases, kit\_codigo}, assert paridade

campo a campo enquanto coexistirem.

[MÉDIO] A4 — business\_rules.py e ct\_thresholds.py duplicam constantes CT

Evidência:

\- config/business\_rules.py:

`    `CT\_MAX\_DETECTAVEL = 35.0

`    `CT\_MIN\_INDETERMINADO = 35.0

`    `CT\_MAX\_INDETERMINADO = 40.0

`    `CT\_MIN\_RP\_VALIDO = 15.0

`    `CT\_MAX\_RP\_VALIDO = 35.0

\- config/ct\_thresholds.py:

`    `@dataclass class CTThresholdsVR1E2:

`        `DETECT\_MAX = 35.0

`        `INCONC\_MIN = 35.01     # ← divergência: 35.0 vs 35.01

`        `INCONC\_MAX = 40.0

`        `RP\_MIN = 15.0

`        `RP\_MAX = 35.0

Problema:

Mesmas constantes definidas em dois lugares com SEMÂNTICA SUTILMENTE

DIFERENTE: business\_rules usa CT\_MIN\_INDETERMINADO=35.0 (inclusive na

borda), ct\_thresholds usa INCONC\_MIN=35.01 (exclui borda). CLAUDE.md §5

declara borda VR1e2 como "8.01-35.0 / 35.01-40.0" — ct\_thresholds.py

está correto, business\_rules.py contradiz na borda.

Impacto:

\- Risco clínico: classificação na borda exata 35.00 pode divergir

`  `conforme qual constante o código consultar.

\- Manutenção dupla: trocar threshold exige editar 2 arquivos.

\- Atualmente: 4 consumidores de business\_rules (analysis\_service,

`  `analysis\_helpers, janela\_analise\_completa, domain/ct\_rules) +

`  `2 consumidores de ct\_thresholds (analise/vr1e2\_biomanguinhos\_7500,

`  `utils/result\_classifier).

Recomendação:

Unificar em ct\_thresholds.py (que está correto). business\_rules.py

re-exporta com aliases para compatibilidade enquanto consumidores migram.

NÃO IMPLEMENTAR SEM rodada SDD própria com guardião de regressão de

ct\_classification (já existe tests/test\_ct\_classification.py).

Teste sugerido:

tests/test\_ct\_constants\_consistency.py — assert que

business\_rules.CT\_MAX\_DETECTAVEL == ct\_thresholds.VR1E2\_THRESHOLDS.DETECT\_MAX

e que CT\_MIN\_INDETERMINADO == INCONC\_MIN. Atualmente FALHARÁ — é o sintoma.

**B. Estado deprecated coexistindo**

[ALTO] B1 — config/settings.py marcado DEPRECATED mas ativo em UI

Evidência:

\- config/settings.py:1-14 cabeçalho documenta deprecação e aponta

`  `config\_service como fonte de verdade.

\- config/settings.py:490-554 cinco funções com `warnings.warn(..., 

`  `DeprecationWarning)`.

\- Consumidores ATIVOS:

`  `- ui/modules/tela\_configuracoes.py:13  importa `configuracao`,

`    ``get\_config`, `set\_config`, `reset\_config`

`  `- utils/persistence.py:450  importa `get\_config`

Problema:

Camada deprecada continua sendo a interface de UI principal de

configurações e de um helper de persistência. Não há cronograma de

migração, nem teste guardião que falhe se novos callers aparecerem.

Impacto:

\- Risco de adicionar novos usos por engano (DeprecationWarning é silencioso

`  `em produção).

\- Duplicação de lógica de merge/save entre ConfigurationManager e

`  `config\_service.

\- Bug pode aparecer em apenas um dos caminhos.

Recomendação:

Em rodada futura: (1) migrar tela\_configuracoes e persistence para

config\_service; (2) substituir settings.py por shim mínimo que apenas

re-exporta; (3) guardião AST que limite novos imports. NÃO IMPLEMENTAR

SEM DHP de cronograma. Tela de configurações foi atualizada em

CFG-UI-001 — janela de oportunidade.

Teste sugerido:

tests/test\_config\_settings\_consumers\_frozen.py — allowlist explícita

de [ui/modules/tela\_configuracoes.py, utils/persistence.py]; novos

imports falham.

[ALTO] B2 — config/paths.py é ÓRFÃO e cria diretórios em import-time

Evidência:

\- Grep `from config.paths` / `import config.paths` no repo: 0 matches.

\- config/paths.py:26-27:

`    `for directory in [BANCO\_DIR, LOGS\_DIR, REPORTS\_DIR, CONFIG\_DIR, TESTS\_DIR]:

`        `directory.mkdir(parents=True, exist\_ok=True)

\- Sem try/except. Sem logging. Substituído canonicamente por

`  `services/system\_paths.py + services/path\_resolver.py (LOG-UNIF-002).

Problema:

Módulo zumbi. Não é importado, mas se algum dia for, criará 5 diretórios

no momento do import — pode falhar com PermissionError em ambiente

restrito, derrubando o processo antes do logger inicializar.

Impacto:

\- Latente hoje (zero consumidores). Risco residual se alguém importar

`  `por engano em CI ou container.

\- Confusão arquitetural: três módulos de paths competindo (paths,

`  `system\_paths, path\_resolver).

Recomendação:

ABRIR DHP de housekeeping para mover ou remover. Opções:

(A) marcar como deprecated com aviso no import (DeprecationWarning);

(B) remover side effect de mkdir em import-time como mínimo (refactor seguro);

(C) deletar arquivo (rodada própria).

NÃO IMPLEMENTAR SEM DHP. Política DEC-002/HIG-005 favorece preservação.

Teste sugerido:

tests/test\_config\_paths\_no\_runtime\_use.py — guardião AST que falhe se

qualquer .py importar config.paths.

**C. Robustez & swallowed exceptions**

[MÉDIO] C1 — feature\_flags.py swallow exceptions silenciosos em IO

Evidência:

\- config/feature\_flags.py:352-360 `\_load\_from\_file`:

`    `try: ... json.load ...

`    `except Exception as e: logger.error(...)

\- config/feature\_flags.py:362-372 `\_save\_to\_file`:

`    `try: ... json.dump ...

`    `except Exception as e: logger.error(...)

Problema:

Erro é logado mas a função continua. Em `\_load\_from\_file`, se falhar,

o arquivo é ignorado e os defaults hardcoded (linhas 33-187) prevalecem

silenciosamente. Operador edita feature\_flags.json com vírgula errada →

flag volta ao default sem alarme óbvio.

Impacto:

\- Comportamento DIVERGE silenciosamente da intenção. Por exemplo,

`  `flag USE\_GAL\_ENVIO\_SEM\_METADADOS (default disabled no hardcoded mas

`  `habilitada por operador no JSON) pode reverter sem aviso.

\- Diagnóstico em campo difícil: o log só aparece em DEBUG.

Recomendação:

Substituir `except Exception` por `except (json.JSONDecodeError, OSError) as e`

e elevar o nível: registrar\_log("FeatureFlags",

"FALHA ao carregar feature\_flags.json - usando defaults hardcoded", "WARNING").

Idealmente também emitir banner no boot se houve fallback.

Teste sugerido:

tests/test\_feature\_flags\_load\_failure\_emits\_warning.py — escreve JSON

inválido, instancia FeatureFlags, assert log WARNING emitido.

[MÉDIO] C2 — settings.py usa @safe\_operation em todos os pontos críticos

Evidência:

\- config/settings.py:69 \_carregar\_configuracoes\_padrao @safe\_operation

\- config/settings.py:90 \_carregar\_configuracoes\_usuario @safe\_operation

\- config/settings.py:182 salvar() @safe\_operation

\- config/settings.py:234 \_criar\_backup() @safe\_operation

Problema:

`@safe\_operation` (de `utils.error\_handler`) tipicamente engloba qualquer

exceção e retorna fallback. Numa camada que deve ser FAIL-CLOSED, isso

mascara falhas de IO, parse e validação.

Impacto:

\- Operador clica "Salvar Configurações" → erro silencioso → UI sugere

`  `sucesso → próxima sessão usa defaults.

\- Backup falha silenciosamente → próxima alteração perde o ponto de

`  `restauração.

Recomendação:

Auditar `safe\_operation` (não está nesta pasta). Substituir o uso em

\_criar\_backup e salvar por tratamento explícito que propague falha

crítica para a UI. NÃO IMPLEMENTAR SEM revisar utils/error\_handler.py

primeiro.

Teste sugerido:

tests/test\_settings\_save\_failure\_propagates.py — patch open()/json.dump

para raise → assert que salvar() retorna False ou levanta exception

recuperável pela UI.

**D. Backups & política**

[BAIXO] D1 — config/backups/ acumula com cap=10 (correto), mas sem janela temporal

Evidência:

\- config/settings.py:234-261 `\_criar\_backup()` mantém últimos 10 arquivos

`  `por timestamp do nome.

\- Inventário atual: 10 backups entre 2026-05-27 e 2026-05-30.

\- INST-003 concluído (backup/rollback implementados).

Problema:

Cap=10 funciona, mas é independente de janela temporal. Em dia de muitos

ajustes (cluster de 5 backups em 1h em 2026-05-29) pode esgotar a janela

e perder histórico anterior relevante.

Impacto:

Baixo. Restauração de longo prazo (>10 alterações) impossível.

Recomendação:

Considerar parametrizar via config (`backup\_retention\_days` ou

`backup\_retention\_count`) em rodada futura junto à DHP de paths.

Teste sugerido:

tests/test\_settings\_backup\_retention\_cap.py — gerar 12 backups em

sequência, assert 10 mantidos, 2 mais antigos removidos.

**E. Outros**

[INFORMATIVO] E1 — Schemas JSON Schema corretamente posicionados em config/contracts/

Evidência:

\- config/contracts/schema.equipment\_profile.json (18 campos obrigatórios)

\- config/contracts/schema.exam\_profile.json (10 campos)

\- config/contracts/schema.gal\_profile.json (5 campos)

\- config/contracts/schema.analysis\_rules\_profile.json

\- config/contracts/schema.storage\_profile.json

Problema:

Nenhum. Estrutura correta DEC-006.

Impacto:

Positivo. Servem de referência para validação programática.

Recomendação:

Considerar usar `jsonschema` (lib) em testes para validar contracts em

CI. Hoje a validação é feita ad-hoc em equipment\_profile\_service.

Teste sugerido:

tests/test\_contracts\_against\_schema.py — para cada

config/contracts/{equipment,exams,gal,storage,analysis\_rules}/\*.json

(não-template), validar contra o schema correspondente via jsonschema.

[INFORMATIVO] E2 — config/exams/schema.json fora de contracts/

Evidência:

\- config/exams/schema.json (2.9 KB, define 12 campos para exames antigos).

\- Schemas canônicos vivem em config/contracts/schema.\*.json.

Problema:

Schema solto fora do diretório de contratos. Sinaliza o convívio das duas

fontes (antiga vs DEC-006).

Impacto:

Confusão arquitetural; não é bug.

Recomendação:

Tratar junto à DHP de A2/A3 (destino de config/exams/).

Teste sugerido:

N/A.

[INFORMATIVO] E3 — ui\_boundary\_allowlist.json status incerto

Evidência:

\- config/ui\_boundary\_allowlist.json (148 B):

`    `"ui\_module\_import\_allowlist": [],

`    `"ui\_toolkit\_import\_allowlist": [...]

\- Subagente C: "não encontrado em grep de código" — quem usa?

Problema:

Arquivo pequeno cuja relevância runtime é incerta. Pode ser consumido

por um teste ou util não detectado.

Impacto:

Baixo. Pode ser órfão.

Recomendação:

Inspeção de baixo custo: grep "ui\_boundary\_allowlist" no repo inteiro

em rodada futura. Se órfão, tratar junto à DHP de A1.

Teste sugerido:

N/A.

-----
**Consolidação dos subagentes simulados**

|**Subagente**|**Veredicto**|
| :- | :- |
|**Arquiteto SDD**|Camada com base nova (DEC-006, INST-001..003, LOG-UNIF, CONFIG-PATH-001) sólida, mas convivência indefinida com legado pesa. Três fontes de verdade ativas.|
|**Bug Hunter**|C1/C2 (swallowed) materializados; A4 (constantes CT divergentes em business\_rules vs ct\_thresholds) é o achado clínico-relevante; A2/A3 (exames-lixo + duplicação zdcbm) são problemas de governança que se tornam bugs se acionados.|
|**Código Morto / Redundância**|config\_old.json órfão total; config/paths.py órfão; 5 exames-lixo; duplicação CT; duplicação zdcbm; config/settings.py deprecated mas ativo.|
|**Especialista em Testes**|LOG-UNIF tem guardiões (9+7 passed). Falta cobertura de: paridade A4, paridade A3, swallowed C1, exames-lixo A2, órfãos A1/B2.|
|**Revisor de Enxutez**|settings.py (555) e feature\_flags.py (397) merecem decomposição. Defaults hardcoded em 3 lugares.|

**Próximas decisões humanas (resumo)**

1. **DHP nova A1** — destino de config\_old.json.
1. **DHP nova A2** — destino dos 5 exames-lixo + schema antigo config/exams/schema.json.
1. **DHP nova A3** — política para config/exams/zdcbm.json vs config/contracts/exams/zdcbm.json.
1. **DHP nova B1** — cronograma de migração de config/settings.py para services/core/config\_service.
1. **DHP nova B2** — destino de config/paths.py.
1. **DHP-12** (já registrada) — banco\_template/historico.db (3.3MB) — tangencial.

**Resumo de ações priorizadas**

1. **[ALTO] A1** — DHP para config\_old.json.
1. **[ALTO] A2 + A3** — DHP conjunta para schema antigo de exames + 5 lixo + duplicação zdcbm.
1. **[ALTO] A4** — unificar business\_rules.py ↔ ct\_thresholds.py (após guardião de paridade falhar).
1. **[ALTO] B1** — cronograma para deprecar settings.py.
1. **[ALTO] B2** — DHP para config/paths.py órfão.
1. **[MÉDIO] C1/C2** — endurecer logging em swallowed exceptions.
1. **[BAIXO] D1** — backup retention por janela temporal.
1. **[INFORMATIVO] E1** — adicionar validação jsonschema em CI.

Nenhuma alteração foi realizada nesta rodada.



**Auditoria SDD READ-ONLY — core/**

**1. Escopo analisado**

**Pasta alvo:** C:\Integragal - Backup - 20260128\_151811\core\

**Arquivos analisados (1 arquivo, 16,6 KB):**

|**Arquivo**|**Linhas**|**Tamanho**|
| :- | :- | :- |
|[core/authentication/user_manager.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/core/authentication/user_manager.py)|1 935|16,6 KB|

**Arquivos NÃO encontrados (e impacto):**

- core/\_\_init\_\_.py — **NÃO EXISTE** (namespace package PEP 420).
- core/authentication/\_\_init\_\_.py — **NÃO EXISTE** (namespace package PEP 420).
- tests/test\_auth\_legacy\_user\_manager\_no\_runtime\_imports.py — **NÃO EXISTE no snapshot**, apesar de declarado "Concluído (1 passed)" em CLAUDE.md §10/§15 + AGENTS.md §16 + tasks.md (vide achado **CRÍTICO A1** abaixo).

**Arquivos não abertos (motivo):**

- usuarios.csv / credenciais.csv: proibidos por CLAUDE.md §9 (hashes bcrypt + dados de usuários reais).
- \_\_pycache\_\_/\*.pyc.

**Fontes SDD lidas:** CLAUDE.md §10/§12/§13/§15, AGENTS.md §16, docs/specs/tasks.md (T-AUD-004A/004B/013, DEC-003), docs/obsoletos/documento\_de\_passagem.md.

-----
**2. Mapa da pasta**

core/                                    (sem \_\_init\_\_.py — namespace package)

└─ authentication/                       (sem \_\_init\_\_.py — namespace package)

`   `└─ user\_manager.py                    (1 935 linhas — LEGADO DEC-003, neutralizado)

**Conteúdo do único arquivo (síntese).**

- **Cabeçalho (linhas 1-20):** descreve UserManager como "fonte de verdade para registros de usuários (usuarios.csv) ... trabalha em conjunto com autenticacao.auth\_service.AuthService". Data 2024-12-01, autor "MiniMax Agent" — anterior a DEC-003.
- **Símbolos públicos:**
  - NivelAcesso (Enum): ADMINISTRADOR, MASTER, DIAGNOSTICO.
  - StatusUsuario (Enum): ATIVO, INATIVO, BLOQUEADO, EXPIRADO.
  - Usuario (@dataclass): id, usuario, senha\_hash, nivel\_acesso, status, data\_criacao, ultimo\_acesso, tentativas\_falhas, bloqueado\_ate, preferencias.
  - UserManager: classe principal com \_\_init\_\_, autenticar, criar\_usuario, listar\_usuarios, \_carregar\_usuarios, \_salvar\_usuarios, \_gerar\_token\_sessao, \_garantir\_arquivo\_existe, \_parse\_json, \_to\_json.
  - inicializar\_sistema(): função de bootstrap **desativada** (bloco \_\_main\_\_ não a chama mais).
- **Modelo de credenciais:** CSV usuarios.csv (via services.path\_resolver.resolve\_users\_csv\_path()); hashing **bcrypt** (bcrypt.checkpw / bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())).
- **Política de senha/sessão (presente):**
  - Tamanho mínimo 8 caracteres (linha ~1443).
  - Lockout: 3 tentativas falhas → bloqueio 30 min (linhas ~1003-1035).
  - Reset de tentativas\_falhas após sucesso (linha ~1083).
  - Token de sessão SHA-256, timeout 8h (linha ~434).
- **Bloco \_\_main\_\_ (linhas 1915-1928) — confirmado neutralizado:**
- if \_\_name\_\_ == "\_\_main\_\_":
- `    `print(
- `        `"core.authentication.user\_manager is a legacy module in controlled "
- `        `"deprecation. Direct execution is disabled; use the active "
- `        `"authentication flow via autenticacao.login/AuthService."
- `    `)
- `    `raise SystemExit(2)
- **IO/side effects:** lê/escreve usuarios.csv com CSVFileLock e open\_with\_retry; cria diretório pai (mkdir parents=True exist\_ok=True); lê RetryPolicy do ambiente.
- **Funções >50 linhas:** **autenticar** com **~560 linhas** (linhas 691-1251 segundo o subagente) — método monolítico que orquestra busca, validação de status, detecção de bloqueio, verificação bcrypt, incremento de tentativas, persistência, verificação hierárquica de nível, emissão de token.
- **Tratamento de erro:** múltiplos try/except silenciosos com fallback (\_garantir\_arquivo\_existe, \_carregar\_usuarios, \_salvar\_usuarios, \_parse\_json → {}, \_to\_json → "{}").
- **TODOs/FIXMEs:** nenhum.

**Dependências internas (implícitas pelos imports descritos pelo subagente):** services.path\_resolver, utils.csv\_lock, utils.io\_retry (provável), services.persistence.\*.

**Dependências externas:** bcrypt, dataclasses, enum, json, secrets, hashlib, datetime, pathlib.

**Consumidores externos do módulo.**

- Grep from core.authentication / import core.authentication no repo: **ZERO imports ativos** (CLAUDE.md §15.1 DEC-003 confirmado).
- Referências encontradas: 1 menção em **comentário** de autenticacao/auth\_service.py (linhas 14-16 do cabeçalho) — documentação de intenção arquitetural futura, não import.
- Citação em release/app/autenticacao/auth\_service.py — cópia da mesma menção em pasta de release; sem impacto runtime.
- Auto-referência: linha 1924 do próprio bloco \_\_main\_\_.
-----
**3. Diagnóstico executivo**

**Coerência com SDD.** **Mista.**

- O arquivo em si está alinhado com DEC-003 / T-AUD-004B: bloco \_\_main\_\_ corretamente neutralizado, zero consumidores runtime, cabeçalho documenta papel legado, deprecação física não executada (conforme política).
- **Divergência grave:** o **guardião declarado em SDD não existe fisicamente neste snapshot** (vide achado A1). A documentação canônica diz "Concluído (1 passed)", mas o arquivo do teste não está presente.

**Enxutez.** **Insuficiente para um módulo legado.** 1 935 linhas com método autenticar de ~560 linhas. Mas como é legado em deprecação controlada, **não deve ser refatorado** sem DEC nova.

**Redundância.** **Significativa frente ao ativo autenticacao/auth\_service.py:**

- Ambos lêem/escrevem usuarios.csv (mesmo schema, mesmo hash bcrypt).
- Ambos contêm Usuario dataclass.
- A grande IRONIA arquitetural: este **legado tem política de senha e lockout PERSISTENTES** (escreve tentativas\_falhas e bloqueado\_ate em CSV), enquanto o ATIVO autenticacao/auth\_service.py **só lê esses campos sem nunca escrever** (achado A1/A2 da auditoria anterior de autenticacao/). Vide achado **C1** abaixo.

**Bugs prováveis.** Nenhum bug runtime ativo — código não executa (zero imports). Riscos LATENTES se reativado: múltiplos try/except silenciosos, método autenticar monolítico.

**Risco arquitetural.** **Médio.** Convivência indefinida com o ativo. O autor original (MiniMax Agent, 2024-12-01) escreveu este módulo como "fonte de verdade", e o auth\_service.py ativo o cita em comentário como "delegado futuro" — direção arquitetural INVERTIDA da realidade pós-DEC-003. Risco de retomada acidental.

**Violação SDD.** Materializada apenas na ausência do guardião T-AUD-004A (A1). O resto está conforme.

**Recomendação geral.** **MANTER (deprecação controlada), MAS CRIAR/RESTAURAR o guardião T-AUD-004A urgentemente** e cobrir T-AUD-013 (cobertura complementar de autenticação) na mesma rodada.

-----
**4. Notas 0–10**

|**Aspecto**|**Nota**|**Justificativa**|
| :- | :- | :- |
|Aderência SDD|**6**|DEC-003 honrada no código; bloco \_\_main\_\_ neutralizado (T-AUD-004B). MAS guardião T-AUD-004A declarado **não existe fisicamente** — divergência crítica entre SDD e estado.|
|Arquitetura|**5**|Legado bem isolado (zero callers). MAS sem \_\_init\_\_.py (PEP 420 frágil para tooling) e método autenticar de 560 linhas. Aceitável para legado.|
|Clareza e Enxutez|**4**|1 935 linhas, método de 560 linhas, múltiplos try/except silenciosos. Esperado em legado pré-SDD.|
|Robustez|**7**|Bcrypt correto, file lock, retry, política de senha e lockout PERSISTIDA — superior ao ativo (vide C1). Mas swallowed exceptions atrapalham diagnóstico.|
|Manutenibilidade|**3**|Não deve ser mantido (legado em deprecação). Tamanho impede refactor seguro. Nota reflete dificuldade se alguém precisar tocar.|
|Testabilidade|**2**|Cobertura ZERO no snapshot. Mesmo o único guardião declarado (T-AUD-004A) está ausente fisicamente.|
|Risco Operacional|**8**|Zero callers + bloco \_\_main\_\_ neutralizado = risco BAIXO em runtime. Risco residual é reativação acidental futura.|
|Prontidão para Evolução|**2**|Não deve evoluir. Pasta inteira é candidata a docs/obsoletos/ após DEC futura.|
|**Geral**|**5**|Legado corretamente neutralizado e isolado, MAS a ausência física do guardião T-AUD-004A é uma divergência grave entre SDD declarada e realidade. Recomendação imediata: criar/restaurar o guardião (item A1).|

-----
**5. Achados detalhados**

**A. Governança SDD**

[CRÍTICO] A1 — Guardião T-AUD-004A declarado em SDD não existe fisicamente no snapshot

Evidência:

\- CLAUDE.md §10 / §15.1 e AGENTS.md §16:

`    `"T-AUD-004A (L-T04 / DEC-003): Concluido - teste guardiao de nao uso

`     `runtime de `core.authentication.user\_manager` criado em

`     ``tests/test\_auth\_legacy\_user\_manager\_no\_runtime\_imports.py`;

`     `evidencia `1 passed`."

\- docs/specs/tasks.md (linhas ~96-97) confirma "Concluído" e cita o teste.

\- Glob `tests/test\_auth\_legacy\*.py` retorna ZERO matches.

\- Glob `tests/\*auth\*` retorna ZERO matches — nenhum teste de autenticação

`  `em tests/ neste snapshot.

Problema:

A documentação canônica afirma que o guardião AST existe e passou ("1 passed").

O arquivo NÃO ESTÁ FISICAMENTE no snapshot 2026-01-28. Três hipóteses:

(a) Teste criado em sessão posterior e não commitado neste snapshot;

(b) Teste removido/renomeado após criação inicial;

(c) Snapshot está defasado em relação ao tronco principal.

Impacto:

\- A proteção contra reintrodução de imports runtime de

`  ``core.authentication.user\_manager` NÃO está ativa.

\- Qualquer commit futuro pode adicionar `from core.authentication.user\_manager

`  `import UserManager` em runtime sem alerta automático.

\- A constituição (CLAUDE.md §6) declara: "documentação canônica vence".

`  `Aqui a documentação afirma um fato que não se materializa em código.

\- Viola implicitamente DEC-003 (que pressupõe guardião ativo).

Recomendação:

RECRIAR o teste a partir das especificações em tasks.md §10.4:

\- Usa AST.

\- Varre runtime areas: `main.py`, `autenticacao/`, `application/`,

`  ``services/`, `ui/`, `interface/`, `exportacao/`, `browser/`, `scripts/`.

\- Bloqueia imports de `core.authentication.user\_manager` com allowlist

`  `inicial VAZIA.

\- Espera `1 passed`.

NÃO PRECISA DE DHP (apenas restaura estado declarado). Considerar em rodada

T-AUD-013.

Teste sugerido:

O próprio T-AUD-004A. Esqueleto:

`    `# tests/test\_auth\_legacy\_user\_manager\_no\_runtime\_imports.py

`    `import ast

`    `from pathlib import Path

`    `RUNTIME\_ROOTS = ["autenticacao", "application", "services", "ui",

`                     `"interface", "exportacao", "browser", "scripts"]

`    `BANNED = {"core.authentication.user\_manager"}

`    `ALLOWLIST: set[str] = set()  # vazia por DEC-003

`    `def test\_no\_runtime\_imports\_of\_legacy\_user\_manager():

`        `repo\_root = Path(\_\_file\_\_).parent.parent

`        `offenders = []

`        `for root in RUNTIME\_ROOTS:

`            `for py in (repo\_root / root).rglob("\*.py"):

`                `if str(py) in ALLOWLIST:

`                    `continue

`                `tree = ast.parse(py.read\_text(encoding="utf-8"))

`                `for node in ast.walk(tree):

`                    `if isinstance(node, ast.ImportFrom) and node.module in BANNED:

`                        `offenders.append(f"{py}:{node.lineno}")

`                    `if isinstance(node, ast.Import):

`                        `for alias in node.names:

`                            `if alias.name in BANNED:

`                                `offenders.append(f"{py}:{node.lineno}")

`        `assert not offenders, "Imports proibidos de legado:\n" + "\n".join(offenders)

`        `# Bonus: também varrer raiz e main.py

[INFORMATIVO] A2 — Bloco \_\_main\_\_ corretamente neutralizado

Evidência:

\- core/authentication/user\_manager.py:1915-1928

`    `if \_\_name\_\_ == "\_\_main\_\_":

`        `print("core.authentication.user\_manager is a legacy module in controlled "

`              `"deprecation. Direct execution is disabled; use the active "

`              `"authentication flow via autenticacao.login/AuthService.")

`        `raise SystemExit(2)

\- Nenhuma chamada a `inicializar\_sistema()`, criação de usuário padrão,

`  `ou persistência. Confirma T-AUD-004B.

Problema:

Nenhum.

Impacto:

Positivo. Execução direta do script é segura (sai com código 2 + mensagem

útil).

Recomendação:

Manter exatamente como está. Não tocar sem DEC futura.

Teste sugerido:

N/A (T-AUD-004B já validou). Opcionalmente:

tests/test\_user\_manager\_main\_exits\_2.py — subprocess.run com python -m

e assert returncode == 2.

[INFORMATIVO] A3 — Zero consumidores runtime (DEC-003 cumprida)

Evidência:

\- Grep `from core.authentication` / `import core.authentication` no repo

`  `(excluindo \_\_pycache\_\_, \_rollback\_, snapshots/, próprio core/):

`  `- ZERO imports ativos.

`  `- 1 menção em COMENTÁRIO de autenticacao/auth\_service.py (linhas 14-16):

`    `"...delegar a gestao completa de usuarios para

`     `core.authentication.user\_manager.UserManager."

Problema:

Nenhum runtime. Mas a documentação no comentário do auth\_service.py descreve

uma DIREÇÃO ARQUITETURAL INVERTIDA (delegar do ativo para o legado), que

contradiz DEC-003 (legado em deprecação).

Impacto:

Baixo. Risco de confusão para novos contribuidores: comentário sugere

caminho oposto da realidade SDD.

Recomendação:

Em rodada futura de housekeeping, atualizar comentário de

autenticacao/auth\_service.py:14-16 para refletir DEC-003 (algo como

"compatibilidade com modulo legado em deprecacao controlada;

nao planejado delegar").

Teste sugerido:

N/A.

**B. Estrutura**

[MÉDIO] B1 — Pasta core/ é namespace package PEP 420 (sem \_\_init\_\_.py)

Evidência:

\- Glob `core/\*\*/\_\_init\_\_.py`: zero matches.

\- core/\_\_init\_\_.py NÃO EXISTE.

\- core/authentication/\_\_init\_\_.py NÃO EXISTE.

\- Python ≥3.3 importa via PEP 420 (namespace packages).

Problema:

Funciona, mas torna o pacote frágil para ferramentas que dependem de

\_\_init\_\_.py explícito (alguns linters, packagers, ferramentas estáticas

antigas). Também ambíguo para o teste guardião A1, que precisa decidir

se varre core/ ou não (provavelmente não, mas decisão precisa ser

explícita).

Impacto:

Pequena fragilidade de tooling. Sem impacto runtime.

Recomendação:

Avaliar adicionar core/\_\_init\_\_.py e core/authentication/\_\_init\_\_.py

com docstring "legacy in controlled deprecation per DEC-003" e nada mais.

NÃO IMPLEMENTAR SEM DEC futura (alteração em pasta legada exige

governança per CLAUDE.md §9).

Teste sugerido:

N/A.

**C. Comparação irônica com o ativo**

[ALTO] C1 — Legado tem política de lockout PERSISTIDA; ativo não tem

Evidência:

\- core/authentication/user\_manager.py:

`  `- Tamanho mínimo de senha = 8 caracteres (linha ~1443).

`  `- Incremento de tentativas\_falhas e set bloqueado\_ate em CSV

`    `(linhas ~1003-1035 segundo o subagente).

`  `- Reset de tentativas\_falhas após sucesso (linha ~1083).

`  `- Token de sessão SHA-256, timeout 8h (linha ~434).

\- autenticacao/auth\_service.py (auditoria anterior, achado A1):

`  `- Schema CSV tem `tentativas\_falhas` e `bloqueado\_ate` (linhas 67-68).

`  `- Apenas LIDOS para construir DTO (linhas 520-521).

`  `- NUNCA escritos em autenticar\_credenciais (linhas 667-743).

Problema:

O fluxo ATIVO de autenticação (DEC-003) é menos robusto que o LEGADO

em deprecação controlada. O contrato CSV existe (campos persistem), mas

a lógica de manter o contador foi PERDIDA na migração para

autenticacao/auth\_service.py.

Impacto:

\- Risco operacional de segurança no ativo (CLAUDE.md CONC-001/002):

`  `brute-force não tem persistência server-side.

\- Reforça achado A1 da auditoria anterior de `autenticacao/`.

\- Inverte o senso comum de "novo é melhor": neste caso, o novo SACRIFICOU

`  `uma proteção que o velho tinha.

Recomendação:

NÃO PORTAR diretamente do legado para o ativo (mistura de pre-DEC-003 e

pós-DEC-003 sem cuidado pode reintroduzir bugs). Em vez disso, ABRIR DHP

NOVA "política de senha/lockout" (já recomendada na auditoria de

autenticacao/, A1) e usar este módulo como REFERÊNCIA de como o lockout

server-side estava modelado antes. NÃO IMPLEMENTAR SEM DECISÃO HUMANA.

Teste sugerido:

Coberto pelo teste sugerido em autenticacao/A1.

**D. Robustez interna do legado (informativo, sem ação)**

[BAIXO] D1 — Múltiplos try/except silenciosos em IO

Evidência:

\- core/authentication/user\_manager.py:464-465 \_garantir\_arquivo\_existe

\- 472-498 \_carregar\_usuarios

\- 506-545 \_salvar\_usuarios

\- 563-603 \_parse\_json (fallback {})

\- 635-676 \_to\_json (fallback "{}")

Problema:

Falhas de IO/parse passam silenciosamente. Comportamento típico de código

pré-SDD.

Impacto:

Latente apenas (módulo não executa). Se reativado, diagnóstico difícil.

Recomendação:

NÃO ALTERAR (módulo legado, política DEC-003). Documentar como anti-padrão

em referência interna se útil para evitar repetição em novo código.

Teste sugerido:

N/A (módulo não evolui).

-----
**Consolidação dos subagentes simulados**

|**Subagente**|**Veredicto**|
| :- | :- |
|**Arquiteto SDD**|DEC-003 cumprida no código (bloco \_\_main\_\_ neutralizado, zero callers). Divergência grave: guardião T-AUD-004A declarado mas ausente fisicamente — viola constituição (documentação ≠ realidade).|
|**Bug Hunter**|Nenhum bug runtime (módulo não executa). Latente: 5 try/except silenciosos. Achado mais relevante é arquitetural-irônico: legado mais robusto que ativo (C1).|
|**Código Morto / Redundância**|Pasta inteira é "código morto controlado" por DEC-003. Não remover sem DEC futura.|
|**Especialista em Testes**|Cobertura = 0 no snapshot. Mesmo o único teste declarado (T-AUD-004A) está ausente. T-AUD-013 pendente é a rodada certa para corrigir.|
|**Revisor de Enxutez**|1 935 linhas, função autenticar de 560 linhas. Pré-SDD. Não tocar.|

**Próximas decisões humanas relevantes**

Nenhuma DHP nova é REQUERIDA para a pasta em si (DEC-003 já a cobre). Mas:

1. **A1** exige rodada imediata para recriar tests/test\_auth\_legacy\_user\_manager\_no\_runtime\_imports.py — **não precisa de DHP** (apenas restaura estado declarado em SDD).
1. **C1** depende da DHP nova "política de senha/lockout" já sugerida na auditoria anterior de autenticacao/. Este achado refina a recomendação: usar o legado como referência de modelo, não como código-fonte para portar.
1. **B1** (adicionar \_\_init\_\_.py em core/) exigiria DEC nova — não implementar sem decisão humana.

**Resumo de ações priorizadas**

1. **[CRÍTICO] A1** — Recriar guardião T-AUD-004A (não precisa de DHP; restaura estado SDD declarado). Pode ser feito em rodada própria de teste.
1. **[ALTO] C1** — Junto à DHP "política de senha/lockout" (já recomendada), usar este legado como referência arquitetural — **não** como código a portar.
1. **[MÉDIO] B1** — Avaliar adicionar \_\_init\_\_.py em rodada com DEC nova.
1. **[INFORMATIVO] A3** — Em housekeeping, atualizar comentário em autenticacao/auth\_service.py:14-16 que descreve direção arquitetural invertida.
1. **[BAIXO] D1** — Nenhuma ação (legado).

Nenhuma alteração foi realizada nesta rodada. Hashes, senhas e usuários reais NÃO foram lidos nem citados.






**Auditoria SDD READ-ONLY — domain/ e db/**

**1. Escopo analisado**

**Pastas alvo:** C:\Integragal - Backup - 20260128\_151811\domain\ e C:\Integragal - Backup - 20260128\_151811\db\

**Arquivos analisados (11 arquivos, ~39 KB):**

|**Pasta**|**Arquivo**|**Linhas**|**Tamanho**|
| :- | :- | :- | :- |
|domain|[**init**.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/domain/__init__.py)|2|43 B|
|domain|[ct_rules.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/domain/ct_rules.py)|66|1,9 KB|
|domain|[ct_rules_runtime.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/domain/ct_rules_runtime.py)|96|3,4 KB|
|domain|**ct\_rules\_runtime.py.bak.target\_recalc\_fix**|93|3,4 KB|
|domain|[error_codes.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/domain/error_codes.py)|30|1,1 KB|
|domain|[exam_scope.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/domain/exam_scope.py)|15|482 B|
|domain|[mapa_placa_layout.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/domain/mapa_placa_layout.py)|233|7,1 KB|
|domain|[persistence_contracts.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/domain/persistence_contracts.py)|332|8,6 KB|
|domain|[plate_mapping.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/domain/plate_mapping.py)|108|3,3 KB|
|domain|[resultado_geral.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/domain/resultado_geral.py)|93|2,7 KB|
|db|[db_utils.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/db/db_utils.py)|162|6,2 KB|

**Arquivos NÃO encontrados (e impacto):**

- tests/test\_\*domain\*.py — **NÃO EXISTE**. Glob retorna zero matches.
- tests/test\_\*import\*.py — **NÃO EXISTE**. Glob retorna zero matches.
- Conclusão: **guardião T-AUD-008 declarado em CLAUDE.md §10/§16 não existe fisicamente** (achado crítico A1, repete o padrão observado em core/ com T-AUD-004A).

**Não abertos:** \_\_pycache\_\_/\*.pyc; CSVs/DBs sensíveis fora destas pastas.

**Fontes SDD lidas:** CLAUDE.md §4-§7/§10/§13/§15-§16, AGENTS.md, .specify/memory/constitution.md, docs/specs/requirements.md (CA-09, CA-14), docs/specs/design.md, docs/specs/tasks.md (T-AUD-001, T-AUD-008, POCO-VAZIO, DT-001, DEC-002, LIM-003, HIG-009), notas\_de\_passagem.md.

-----
**2. Mapa das pastas**

domain/                                      (camada de DOMÍNIO PURO - SDD)

├─ \_\_init\_\_.py                                (2 linhas — sem \_\_all\_\_)

├─ ct\_rules.py                                (classificar\_ct + ResultadoCt; usa math.isnan ✓ T-AUD-001)

├─ ct\_rules\_runtime.py                        (classificar\_ct\_por\_exame; perfis dinâmicos)

├─ ct\_rules\_runtime.py.bak.target\_recalc\_fix  (BACKUP ABANDONADO — versão simplificada anterior)

├─ error\_codes.py                             (ErrorCode com 11 constantes)

├─ exam\_scope.py                              (ExamForaDoEscopoError — CA-09)

├─ mapa\_placa\_layout.py                       (4 dataclasses frozen + funções puras)

├─ persistence\_contracts.py                   (2 Enums + 9 DTOs + 8 Protocols + 6 Exceptions)

├─ plate\_mapping.py                           (gerar\_mapeamento\_24/32/48/96)

└─ resultado\_geral.py                         (calcular\_resultado\_geral + is\_amostra\_vazia — CA-14)

db/                                           (camada paralela de DB — convive com services/persistence/)

└─ db\_utils.py                                (facade dual stack: PostgreSQL stub + fallback CSV)

**Responsabilidades percebidas.**

- **domain/**: regras puras conforme CLAUDE.md §4/§6. Classificação CT por borda VR1e2 (8.01-35.0 / 35.01-40.0), Resultado\_geral com prioridade Inválido > Indeterminado > Detectável > Não Detectável, layout de mapa de placa, mapeamento de poços por kit (24/32/48/96), DTOs/Protocols para persistência, fail-closed de escopo, catálogo de error codes.
- **db/**: facade legado para histórico de processamento. get\_postgres\_connection() é stub que sempre retorna None (linha 19); operações reais caem em fallback CSV via services.persistence.csv\_io + CSVFileLock.

**Fluxos relevantes.**

1. **CT → Resultado**: services/analysis/analysis\_service → domain.ct\_rules.classificar\_ct → domain.resultado\_geral.calcular\_resultado\_geral → grid via domain.mapa\_placa\_layout.
1. **Escopo ativo (fail-closed)**: application/reports\_contracts e services/analysis/analysis\_service levantam domain.exam\_scope.ExamForaDoEscopoError quando exame não está em active\_exams.
1. **Persistência**: contratos em domain/persistence\_contracts (UserDTO/HistoryRecordDTO/UserRepository/PersistenceProvider) consumidos por autenticacao/auth\_service, services/core/service\_container, services/persistence/persistence\_adapters.
1. **Histórico de processamento**: utils/gui\_utils.py:13 → db.db\_utils.salvar\_historico\_processamento → tenta PostgreSQL (sempre falha por stub) → fallback CSV em logs/historico\_processos.csv.

**Dependências internas.** domain/ importa apenas domain.\* + config.business\_rules/config.enums/config.ct\_thresholds (constantes). Zero violações. db/db\_utils.py importa services.core.config\_service, services.persistence.csv\_io, utils.csv\_lock, utils.csv\_safety, utils.network\_io, utils.logger.

**Dependências externas.** domain/ usa apenas stdlib (math, enum, typing, dataclasses). Zero pandas, selenium, tkinter, openpyxl. db/db\_utils.py importa psycopg2 (no bloco morto) e pandas (lazy, em obter\_historico\_analises).

**Consumidores externos.**

- **domain/ amplamente consumido** (>22 callers identificados): error\_codes (6+), persistence\_contracts (4+), resultado\_geral (4+), ct\_rules (4+), plate\_mapping (3), exam\_scope (2), mapa\_placa\_layout (2).
- **db/db\_utils.py USADO** (corrige interpretação inicial): 4 consumidores de produção confirmados — utils/gui\_utils.py:13 (top-level), ui/janela\_analise\_completa.py:1650 (lazy), ui/modules/dashboard.py:1195 (lazy), scripts/consolidate\_history.py:24 (script).
-----
**3. Diagnóstico executivo**

**domain/ — Diagnóstico.**

**Coerência com SDD.** **Excelente** no código (10/10 arquivos cumprem § 6: domínio puro, sem pandas/selenium/tk). T-AUD-001 (DT-001) confirmado: ct\_rules.py usa math.isnan nativo. POCO-VAZIO/CA-14 implementada em resultado\_geral.py:is\_amostra\_vazia. ExamForaDoEscopoError correto. **Divergência grave:** guardião T-AUD-008 não existe fisicamente (vide A1).

**Enxutez.** **Boa.** Maior arquivo é persistence\_contracts.py (332 linhas) com 25 símbolos — apropriado pois são contratos. Todos os arquivos têm funções <50 linhas. Pasta proporcional ao papel.

**Redundância.** Baixa. Único item: ct\_rules\_runtime.py.bak.target\_recalc\_fix (93 linhas) — versão anterior abandonada de \_lookup\_rule, deixada na pasta crítica (vide A2).

**Bugs prováveis.** Nenhum no código ativo. ct\_rules.py:50-65 tem try/except com fallback NAO\_DETECTAVEL (fail-closed). mapa\_placa\_layout.formatar\_ct tem fallback string vazia (fail-closed).

**Risco arquitetural.** **Baixo**, pois código está conforme. **Risco residual** vem da ausência do guardião T-AUD-008 — qualquer commit futuro pode reintroduzir pandas em domain/ sem alerta.

**Violação SDD.** **Materializada apenas na ausência do guardião** (A1). Existência do .bak em zona regulada é sinal de processo (A2), não viola código.

**db/ — Diagnóstico.**

**Coerência com SDD.** **Baixa.** Pasta inteira é camada PARALELA a services/persistence/ sem registro em CLAUDE.md §4 ("Estrutura principal do projeto"). Contém bloco de código PostgreSQL completo (linhas ~77-115, 125+) que viola implicitamente CLAUDE.md §7 ("Postgres dedicado nao deve ser usado"). O stub get\_postgres\_connection() → None é a única coisa que protege.

**Enxutez.** Tamanho razoável (162 linhas) para 3 funções. Mas o bloco PostgreSQL morto é ~40% do código.

**Redundância.** **Alta.** Função salvar\_historico\_processamento cobre o mesmo papel que services/reports/history\_report.HistoryReportService (amplamente usado segundo auditorias anteriores). Duas APIs concorrentes para histórico.

**Bugs prováveis.**

- PostgreSQL bloco usa try/finally sem context manager para conn.close() — fail-safe mas frágil.
- obter\_historico\_analises retorna Optional[pd.DataFrame] — caller precisa lidar com None silencioso.

**Risco arquitetural.** **Médio.** Camada paralela usada por 4 callers de produção (UI + utils + scripts). Mudanças em formato de histórico precisariam tocar dois lugares (db/db\_utils.py + services/reports/history\_report.py). Risco real de divergência.

**Violação SDD.** **Materializada parcialmente:** (a) pasta db/ não consta em CLAUDE.md §4; (b) bloco PostgreSQL viola espírito de §7 mesmo desabilitado.

-----
**Recomendação geral.**

- **domain/: MANTER, mas restaurar guardião T-AUD-008 urgentemente** e tratar o .bak.
- **db/: AJUSTAR com DHP nova** — decidir entre (A) absorver db\_utils em services/persistence/ migrando os 4 callers, ou (B) remover bloco PostgreSQL morto deixando apenas fallback CSV, ou (C) manter como facade com README explícito.
-----
**4. Notas 0–10 — consolidadas para ambas as pastas**

|**Aspecto**|**Nota**|**Justificativa**|
| :- | :- | :- |
|Aderência SDD|**6**|domain/ aderência exemplar no código (T-AUD-001, POCO-VAZIO, fail-closed). db/ não consta em §4 do CLAUDE.md. Guardião T-AUD-008 declarado mas ausente.|
|Arquitetura|**7**|domain/ é referência (puro, DTOs frozen, Protocols). db/ é camada paralela órfã do mapa SDD.|
|Clareza e Enxutez|**8**|domain/ enxuto e bem dimensionado. db/ tem 40% de bloco PostgreSQL morto.|
|Robustez|**7**|domain/ fail-closed em todos os pontos. db/ tem fail-safe via stub PostgreSQL + fallback CSV, mas conexão sem with.|
|Manutenibilidade|**7**|domain/ clara, tipada, sem deps pesadas. db/ mistura 2 stacks.|
|Testabilidade|**3**|Guardião T-AUD-008 ausente fisicamente. Testes existentes cobrem comportamento (CT, POCO-VAZIO 18 passed), mas o guardião de pureza foi declarado e não está. db/ sem testes próprios.|
|Risco Operacional|**6**|domain/ baixo (zero IO, fail-closed). db/ médio (4 callers de produção dependem; divergência potencial com history\_report).|
|Prontidão para Evolução|**7**|domain/ permite adicionar regras sem refator. db/ precisa decisão de unificação.|
|**Geral**|**6,5**|domain/ mereceria 9 isoladamente, mas a ausência do guardião declarado puxa a nota. db/ mereceria 4-5 isoladamente. Média ponderada reflete o saldo.|

-----
**5. Achados detalhados**

**A. Guardiões SDD ausentes & higiene de domínio**

[CRÍTICO] A1 — Guardião T-AUD-008 declarado em SDD não existe fisicamente

Evidência:

\- CLAUDE.md §10 (suítes recomendadas) e §16 (lista de concluídas):

`    `"T-AUD-008 (L-T03): \*\*Concluido\*\* - teste-guardiao de imports em

`     ``domain/` proibe `pandas`, `selenium`, `tkinter`, `customtkinter`,

`     ``seleniumrequests`."

\- Glob `tests/test\_\*domain\*.py` → ZERO matches.

\- Glob `tests/test\_\*import\*.py` → ZERO matches.

\- Padrão idêntico ao A1 da auditoria de `core/` (T-AUD-004A também ausente).

Problema:

A documentação SDD canônica afirma que existe guardião AST/import que

falha se domain/ contiver `from pandas`, `from selenium`, etc. O arquivo

NÃO está fisicamente no snapshot. Nada impede regressão em domain/.

Impacto:

\- Qualquer commit futuro pode reintroduzir `import pandas` em domain/

`  `sem alerta automático.

\- DT-001 (resolvida 2026-05-12) já corrigiu o bug original — sem

`  `guardião, pode voltar.

\- Viola constituição (SDD §6 — domínio puro) implicitamente.

Recomendação:

RECRIAR o teste a partir da especificação. NÃO PRECISA DE DHP (apenas

restaura estado declarado). Esqueleto:

`    `# tests/test\_dominio\_imports\_puros.py

`    `import ast

`    `from pathlib import Path



`    `BANNED\_TOP = {"pandas", "selenium", "tkinter", "customtkinter",

`                  `"seleniumrequests", "openpyxl", "requests",

`                  `"PIL", "matplotlib"}



`    `def test\_domain\_layer\_only\_uses\_stdlib\_and\_config():

`        `domain\_dir = Path(\_\_file\_\_).parent.parent / "domain"

`        `offenders = []

`        `for py in domain\_dir.rglob("\*.py"):

`            `if py.suffix != ".py" or ".bak" in py.name:

`                `continue

`            `tree = ast.parse(py.read\_text(encoding="utf-8"))

`            `for node in ast.walk(tree):

`                `if isinstance(node, ast.Import):

`                    `for alias in node.names:

`                        `top = alias.name.split(".")[0]

`                        `if top in BANNED\_TOP:

`                            `offenders.append(f"{py}:{node.lineno}: {alias.name}")

`                `elif isinstance(node, ast.ImportFrom) and node.module:

`                    `top = node.module.split(".")[0]

`                    `if top in BANNED\_TOP:

`                        `offenders.append(f"{py}:{node.lineno}: from {node.module}")

`        `assert not offenders, "Imports proibidos em domain/:\n" + "\n".join(offenders)

Teste sugerido:

O próprio T-AUD-008 (acima). Rodada T-AUD-013 ou rodada própria de teste.

[ALTO] A2 — Arquivo .bak deixado em zona regulada (domain/)

Evidência:

\- domain/ct\_rules\_runtime.py.bak.target\_recalc\_fix (93 linhas, 3,4 KB)

\- Versão anterior simplificada de `\_lookup\_rule()` — sem `\_normalize()`

`  `aninhado, sem normalização de espaços nas chaves de `by\_target`.

\- Foi superada por `domain/ct\_rules\_runtime.py` (96 linhas, com

`  `normalização endurecida).

Problema:

Arquivo .bak abandonado dentro da pasta mais regulada do projeto

(CLAUDE.md §6/§16). Não é interpretado pelo Python como módulo (sufixo

.bak.\*), mas:

(a) confunde leitor;

(b) pode ser carregado por engano em tooling que glob "\*.py\*";

(c) sinaliza processo (refactor sem cleanup) que não condiz com a

maturidade declarada de domain/.

Impacto:

\- Risco baixo runtime (não importável).

\- Risco de governança: zona regulada com lixo enfraquece a credibilidade

`  `das próprias regras SDD.

Recomendação:

ABRIR DHP de housekeeping para mover/remover. Símil HIG-006. Opções:

(A) mover para docs/obsoletos/ct\_rules\_runtime/;

(B) remover (rodada própria);

(C) renomear para tests/fixtures/ se for útil como referência de regressão.

NÃO IMPLEMENTAR SEM DECISÃO HUMANA (política DEC-002/DEC-004 favorece

preservação).

Teste sugerido:

tests/test\_domain\_no\_backup\_files.py — falhar se domain/ contiver

arquivos com sufixos {.bak, .bak.\*, .orig, .swp, ~}.

**B. db/ — camada paralela não documentada em SDD**

[ALTO] B1 — Pasta db/ não consta em CLAUDE.md §4 (estrutura principal)

Evidência:

\- CLAUDE.md §4 lista: domain/, application/, services/, ui/, interface/,

`  `exportacao/, browser/, config/, banco/, docs/specs/, tests/.

`  `Não menciona `db/`.

\- db/db\_utils.py existe e tem 4 consumidores ATIVOS:

`  `- utils/gui\_utils.py:13 (import top-level)

`  `- ui/janela\_analise\_completa.py:1650 (lazy)

`  `- ui/modules/dashboard.py:1195 (lazy)

`  `- scripts/consolidate\_history.py:24

Problema:

Camada estrutural usada em runtime sem registro no mapa canônico SDD.

Concorre semanticamente com `services/persistence/` (canônica para

adapters de persistência) e `services/reports/history\_report.py`

(canônica para histórico).

Impacto:

\- Confusão para novos contribuidores.

\- Risco de divergência: histórico de processamento mantido por dois

`  `caminhos (db.db\_utils vs services/reports/history\_report).

\- Possível duplicação de schema de CSV.

Recomendação:

ABRIR DHP NOVA para definir destino:

(A) ABSORVER em services/persistence/history\_csv\_adapter.py com migração

`    `dos 4 callers (rodada média);

(B) DOCUMENTAR em CLAUDE.md §4 como camada legítima (rodada baixa);

(C) DEPRECAR com timeline conforme A4.

NÃO IMPLEMENTAR SEM DECISÃO HUMANA. Toca utils e UI ativos.

Teste sugerido:

N/A imediato. Após DHP, eventual guardião de import-ban (se A ou C).

[ALTO] B2 — Bloco PostgreSQL morto em db/db\_utils.py viola espírito do §7

Evidência:

\- CLAUDE.md §7 (regras de operação): "Postgres dedicado nao deve ser

`  `usado (provider nao implementado)."

\- db/db\_utils.py:19 `def get\_postgres\_connection() -> Optional[object]`

`  `retorna sempre None (stub).

\- db/db\_utils.py:77,125 `conn = get\_postgres\_connection()` — uso ativo

`  `do stub.

\- Bloco psycopg2 completo presente (linhas ~96-115) com `cursor.execute`,

`  ``conn.commit`, `conn.close` em try/finally, executados condicionalmente

`  `caso `conn` deixe de ser None.

\- import psycopg2 inferido pelo subagente (presente no arquivo).

Problema:

Embora o stub neutralize execução, o BLOCO COMPLETO de PostgreSQL

sobrevive. Basta alguém alterar get\_postgres\_connection() para retornar

uma conexão real e o pipeline volta a usar Postgres — exatamente o que

§7 proíbe.

Impacto:

\- Risco de reativação acidental (uma linha de código basta).

\- import psycopg2 pode tornar build dependente de driver Postgres mesmo

`  `sem uso.

\- Confusão: comentário em scripts/consolidate\_history.py:10 chama

`  `PostgreSQL de "Fonte de verdade", contradizendo o stub e o §7.

Recomendação:

NÃO IMPLEMENTAR SEM DHP B1. Quando B1 resolver, considerar:

(A) remover bloco psycopg2 inteiro deixando apenas fallback CSV;

(B) substituir comentário em consolidate\_history.py:10 que chama

`    `PostgreSQL de "Fonte de verdade".

Em qualquer caso, NÃO IMPLEMENTAR SEM DECISÃO HUMANA.

Teste sugerido:

tests/test\_no\_psycopg2\_imports.py — guardião AST que falhe se qualquer

.py em runtime contiver `import psycopg2` ou `from psycopg2`. Allowlist

inicial: vazia.

[MÉDIO] B3 — Conexão PostgreSQL usa try/finally sem context manager

Evidência:

\- db/db\_utils.py:77-115 padrão `conn = get\_postgres\_connection()` ...

`  ``with conn.cursor()` ... `conn.commit()` ... `conn.close()` em finally

`  `(subagente confirmou).

Problema:

Padrão correto-mas-frágil para o caso em que o stub retorne real um dia.

Se exceção ocorrer entre cursor e commit, transação fica pendente até

o close.

Impacto:

Baixo enquanto stub estiver ativo. Latente.

Recomendação:

Junto à decisão B1/B2, padronizar `with conn:` (autocommit/rollback) +

`with conn.cursor()`. NÃO IMPLEMENTAR isoladamente.

Teste sugerido:

N/A imediato.

**C. Outros**

[INFORMATIVO] C1 — domain/ é referência arquitetural exemplar

Evidência:

\- 10/10 arquivos sem pandas/selenium/tk.

\- ct\_rules.py usa math.isnan nativo (T-AUD-001 / DT-001).

\- exam\_scope.py implementa ExamForaDoEscopoError (CA-09).

\- resultado\_geral.py implementa is\_amostra\_vazia (CA-14 / POCO-VAZIO,

`  `guardião tests/test\_poco\_vazio\_invalido.py com 18 passed).

\- persistence\_contracts.py define 9 DTOs frozen, 8 Protocols e 6

`  `exceções semânticas — sem inversão de dependência indevida.

\- mapa\_placa\_layout.py documenta na linha 12: "não depende de UI,

`  `openpyxl, pandas ou reportlab".

Problema:

Nenhum. Observação positiva.

Impacto:

domain/ pode ser citado como modelo no design.md para guiar evoluções

de outras camadas (símil ao que se observa em application/).

Recomendação:

Considerar mencionar domain/ + application/ como REFERÊNCIAS canônicas

no design.md (rodada documental futura).

Teste sugerido:

N/A.

[INFORMATIVO] C2 — UserAccessLevel define apenas 3 níveis

Evidência:

\- domain/persistence\_contracts.py:25 UserAccessLevel: ADMIN, MASTER,

`  `DIAGNOSTICO.

\- application/access\_control.py (auditoria anterior) define matriz com

`  `"users.mutate" e PRIVILEGED\_LEVELS = {"ADMIN", "MASTER"}.

\- core/authentication/user\_manager.py (legado) define NivelAcesso:

`  `ADMINISTRADOR, MASTER, DIAGNOSTICO — diverge de UserAccessLevel.ADMIN.

Problema:

Diferença sutil de naming entre legado (ADMINISTRADOR) e ativo (ADMIN).

Documentação SDD não esclarece.

Impacto:

Baixo (legado não executa). Atenção em qualquer DHP futura de unificação.

Recomendação:

N/A nesta rodada. Anotar para DHP de política de senha (já registrada

em auditoria de autenticacao/).

Teste sugerido:

N/A.

[INFORMATIVO] C3 — db\_utils tem PostgreSQL chamado de "Fonte de verdade" em comentário de outro script

Evidência:

\- scripts/consolidate\_history.py:10 (comentário):

`    `"Fonte de verdade: PostgreSQL (db.db\_utils.salvar\_historico\_processamento)"

\- Realidade: PostgreSQL é stub que retorna None; verdade efetiva é CSV.

Problema:

Comentário documenta arquitetura desejada que NÃO é a real. Confunde

manutenção.

Impacto:

Baixo. Refora confusão sobre status de db/ (B1).

Recomendação:

Atualizar comentário em rodada da DHP B1.

Teste sugerido:

N/A.

-----
**Consolidação dos subagentes simulados**

|**Subagente**|**Veredicto**|
| :- | :- |
|**Arquiteto SDD**|domain/ é modelo. db/ é camada paralela órfã do mapa SDD. T-AUD-008 declarado mas ausente — segundo padrão de divergência SDD→realidade após T-AUD-004A.|
|**Bug Hunter**|Sem bugs runtime ativos. Riscos latentes: reativação PostgreSQL (B2), regressão em domain/ sem guardião (A1).|
|**Código Morto / Redundância**|.bak em domain/ (A2); bloco PostgreSQL em db/ (B2); redundância funcional entre db.db\_utils.salvar\_historico\_processamento e services.reports.history\_report (B1).|
|**Especialista em Testes**|Cobertura de comportamento existe (CT, POCO-VAZIO). Cobertura de PUREZA (T-AUD-008) ausente. Recomenda recriar guardião imediatamente.|
|**Revisor de Enxutez**|domain/ enxuto. db/db\_utils.py tem 40% morto.|

**Próximas decisões humanas (resumo)**

1. **DHP nova B1** — destino de db/db\_utils.py (absorver / documentar / deprecar).
1. **DHP de housekeeping A2** — destino do .bak em domain/.
1. **Nenhuma DHP requerida para A1/B2** — A1 apenas restaura estado declarado; B2 depende de B1.

**Resumo de ações priorizadas**

1. **[CRÍTICO] A1** — recriar guardião T-AUD-008 (esqueleto fornecido). Rodada própria de teste, sem DHP.
1. **[ALTO] B1** — DHP nova para db/db\_utils.py.
1. **[ALTO] A2** — DHP de housekeeping para .bak em domain/.
1. **[ALTO] B2** — junto à B1, decidir remoção do bloco PostgreSQL morto + guardião no\_psycopg2\_imports.
1. **[MÉDIO] B3** — junto à B1, padronizar context managers se PostgreSQL ficar.
1. **[INFORMATIVO] C3** — atualizar comentário em scripts/consolidate\_history.py:10 que chama PostgreSQL de "Fonte de verdade".

Nenhuma alteração foi realizada nesta rodada.



**Auditoria SDD READ-ONLY — exportacao/**

**1. Escopo analisado**

**Pasta alvo:** C:\Integragal - Backup - 20260128\_151811\exportacao\

**Arquivos analisados (10 Python + 2 debug, ~292 KB):**

|**Arquivo**|**Linhas**|**Tamanho**|
| :- | :- | :- |
|[**init**.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/exportacao/__init__.py)|1|0 B|
|[debug_login_runner.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/exportacao/debug_login_runner.py)|64|2,0 KB|
|[envio_gal.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/exportacao/envio_gal.py)|1 833|76,0 KB|
|[exportar_resultados.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/exportacao/exportar_resultados.py)|1 294|28,2 KB|
|[gal_exceptions.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/exportacao/gal_exceptions.py)|40|1,0 KB|
|[gal_formatter.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/exportacao/gal_formatter.py)|633|22,5 KB|
|[gal_payload_contract.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/exportacao/gal_payload_contract.py)|93|3,2 KB|
|[gal_payload_dto.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/exportacao/gal_payload_dto.py)|131|4,7 KB|
|[mapa_placa_exporter.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/exportacao/mapa_placa_exporter.py)|1 016|37,7 KB|
|debug/gal\_login\_fail.html|0|0 B|
|debug/gal\_login\_fail.png|(binário)|116 KB|

**Não abertos (motivo):**

- debug/gal\_login\_fail.png — **NÃO ABERTO**: arquivo binário possivelmente sensível (screenshot de tela de login do GAL após falha). Apenas confirmei tamanho e mecanismo de criação.
- \_\_pycache\_\_/\*.pyc.

**Fontes SDD lidas:** CLAUDE.md §4-§9/§13-§16, AGENTS.md §16, docs/specs/design.md §3.5/§3.3.1/§3.8, docs/specs/requirements.md (CA-11, CA-17), docs/specs/tasks.md (GAL-ROB-001..010, GAL-FEAT-001..005, GAL-PEND-001/002, T20/T21/T22, WIZ-GAL-01..07, DASH-007), notas\_de\_passagem.md.

-----
**2. Mapa da pasta**

exportacao/

├─ \_\_init\_\_.py                       (vazio)

├─ debug\_login\_runner.py             (64 linhas — script utilitário; env vars; sem credenciais)

├─ envio\_gal.py                      (1 833 linhas — GalService + IntegrationApp UI)

├─ exportar\_resultados.py            (1 294 linhas; ~880 morto após return na L394)

├─ gal\_exceptions.py                 (5 classes: GalIntegrationError + 4 derivados)

├─ gal\_formatter.py                  (formatação CSV canônica GAL)

├─ gal\_payload\_contract.py           (schema v1.0.0 + validate\_gal\_payload fail-OPEN)

├─ gal\_payload\_dto.py                (GalPayloadDTO frozen com coerção e normalização)

├─ mapa\_placa\_exporter.py            (gerador .xlsx — CA-17 Mapa Definitivo)

└─ debug/

`   `├─ gal\_login\_fail.html            (0 bytes — placeholder ou write incompleto)

`   `└─ gal\_login\_fail.png             (116 KB — screenshot de falha de login)

**Responsabilidades percebidas.**

- **envio\_gal.GalService** (linha 198) implementa **integralmente** os 11 métodos do GalSendServicePort (application/gal\_send\_use\_case): realizar\_login (L272-294), ler\_csv\_resultados (L1051-1076), buscar\_metadados (L582-703), construir\_payload (L705-826), enviar\_amostra (L946-1049), build\_idempotency\_key (L1078-1102), get\_transaction\_journal\_path (L1104-1107), load\_successful\_idempotency\_keys (L1109-1130), get\_user\_access\_level (L1132-1141), append\_journal\_events (L1143-1172), salvar\_relatorios (L1240-1423).
- **envio\_gal.IntegrationApp** (linha 1429) — frame CustomTkinter para UI modal.
- **mapa\_placa\_exporter.gerar\_mapa\_placa\_xlsx** (linha 967) — gera Mapa Definitivo .xlsx em <data\_root>/mapas/ (CA-17).
- **gal\_formatter** — formatação canônica CSV GAL para envio + painel (\_build\_gal\_dataframe\_core 140 linhas).
- **exportar\_resultados.exportar\_resultados\_core** (linha 70) — caso de uso isolado de UI; \_executar\_exportacao\_gal\_ui (linha 186, 107 linhas) é o adapter Tkinter. exportar\_resultados\_gal (linha 315) é wrapper de compatibilidade que delega ao adapter e contém 880 linhas mortas como fallback (vide B1/B2).

**Fluxos relevantes.**

1. **Envio GAL (U3 completo):** UI (ui/menu\_handler.py:16/658) → envio\_gal.abrir\_janela\_envio\_gal → IntegrationApp cria GalService → application/gal\_send\_use\_case.GalSendUseCase.execute orquestra os 6 passos chamando os métodos do GalSendServicePort (implementado por GalService).
1. **Mapa Definitivo:** UI análise (ui/janela\_analise\_completa.py:1827) → mapa\_placa\_exporter.gerar\_mapa\_placa\_xlsx → construir\_mapa\_de\_dataframe (consome domain.mapa\_placa\_layout) → renderizar\_xlsx\_grade\_fisica (openpyxl, A4 landscape, grid 8×12) → salva em <data\_root>/mapas/.
1. **CSV GAL canônico:** main.py:166, ui/janela\_analise\_completa.py:1651/1739, utils/gui\_utils.py:857-858 → gal\_formatter.formatar\_para\_gal / exportar\_csv\_gal\_oficial → \_write\_gal\_csv (temp file + os.replace atomic + CSVFileLock).
1. **Histórico de transações GAL:** salvar\_relatorios → services/gal/gal\_transactions.append\_transaction\_journal\_unique (dual-key, inflight\_keys).
1. **Debug de login:** envio\_gal.\_persist\_login\_debug\_artifacts (L553-580) cria debug/gal\_login\_fail.png|.html quando login falha.

**Dependências internas.** application.gal\_send\_use\_case (GalSendRequest), domain.error\_codes (ErrorCode), domain.mapa\_placa\_layout (DTOs frozen), services.exam\_registry, services.contract\_catalog, services.core.config\_service, services.core.runtime\_flags, services.gal.gal\_transactions, autenticacao.auth\_service (via get\_user\_access\_level), utils.csv\_lock, utils.network\_io, utils.logger, utils.text\_result\_classifier, utils.selecionado\_normalizer.

**Dependências externas.** pandas, seleniumrequests.Firefox, selenium, requests, openpyxl, customtkinter, tkinter, matplotlib, PIL (em UI).

**Consumidores externos.**

- envio\_gal — **amplamente usado**: ui/menu\_handler.py:16,658, utils/gui\_utils.py:858, exportacao/debug\_login\_runner.py:19 + testes tests/test\_exam\_creator\_campos\_gal.py.
- gal\_formatter — **amplamente usado**: main.py:166, utils/gui\_utils.py:857, ui/janela\_analise\_completa.py:1651/1739, scripts/generate\_phase0\_baseline.py:28 + 1 teste.
- mapa\_placa\_exporter — **pontual**: ui/janela\_analise\_completa.py:1827.
- gal\_exceptions, gal\_payload\_contract, gal\_payload\_dto — **internos** (apenas envio\_gal.py).
- exportar\_resultados — **suspeito de órfão** (vide B1): apenas scripts/report\_exportar\_resultados\_usage.py lê telemetria; nenhum caller chama exportar\_resultados\_gal em runtime.
- debug\_login\_runner — **órfão de produção** (script standalone para debug manual).
-----
**3. Diagnóstico executivo**

**Coerência com SDD.** **Alta** nos módulos canônicos. envio\_gal.py implementa fielmente todos os 10 GAL-ROB concluídos: excepção worker estruturada (L630-639, 684-688), lote não abortado (L594, 674), aviso de falhas (L690-698), CSV validado antes do browser (L1051-1076 → fail-closed antes do driver), aviso de gal\_exame\_codigo ausente, **mascaramento de payload** (L1005-1017 com \_SENSITIVE\_KEYS = ("paciente", "nomePaciente", "\_raw")), inflight\_keys atômicas via services.gal.gal\_transactions, normalização simétrica de datas DD/MM/YYYY (L600-602, L791-794), validação de codigo não-vazio (L765, 807-808), fallback por codigo\_amostra (L641-671). Também alinhado com GAL-FEAT-001..005 (flags USE\_GAL\_ENVIO\_SEM\_METADADOS, USE\_GAL\_FIREFOX\_HEADLESS, USE\_GAL\_TERMINAL\_LOG\_POR\_AMOSTRA). mapa\_placa\_exporter cumpre CA-17 (path <data\_root>/mapas/).

**Enxutez.** **Insuficiente em três módulos.** envio\_gal.py (1 833 linhas) tem salvar\_relatorios (183 linhas), buscar\_metadados (121), construir\_payload (121), enviar\_amostra (103), \_append\_upload\_history\_csv (64). mapa\_placa\_exporter.py (1 016 linhas) tem renderizar\_xlsx\_grade\_fisica (125), construir\_mapa\_de\_dataframe (104). gal\_formatter.py tem \_build\_gal\_dataframe\_core (140). exportar\_resultados.py tem 880 linhas mortas (vide B1).

**Redundância.** **Massiva em exportar\_resultados.py**: linhas 405-1175 são código inalcançável após return na L394, intencionalmente preservadas como "fallback de rollback técnico" com instrumentação (log\_suspected\_orphan\_usage na L385-390) e script de telemetria (scripts/report\_exportar\_resultados\_usage.py). Workflow de deprecação iniciado mas não concluído.

**Bugs prováveis.**

1. gal\_payload\_contract.validate\_gal\_payload é **fail-open**: retorna lista de erros sem lançar; depende do caller verificar (vide C1).
1. debug/gal\_login\_fail.html está com 0 bytes — write incompleto em sessão anterior; pode mascarar diagnóstico futuro se sobrescrito sem flush correto.
1. exportar\_resultados.py:336 tem typo exam\_cfg: any = None (lowercase any = builtin function, não typing.Any).

**Risco arquitetural.** **Médio-Alto.** Concentração extrema em envio\_gal.py (76 KB, 1 833 linhas) torna refatoração arriscada. GAL-PEND-002 (suite sem Selenium) é pré-requisito explícito para evolução segura. Bloco morto em exportar\_resultados.py aumenta superfície de auditoria.

**Violação SDD.** Não há violação MATERIALIZADA. Há **risco operacional** documentado:

- GAL-PEND-001 (retry transitório vs definitivo) ainda pendente.
- GAL-PEND-002 (suíte sem Selenium real) ainda pendente.

**Recomendação geral.** **AJUSTAR.** Três frentes:

1. **DHP nova** para concluir deprecação de exportar\_resultados\_gal (B1/B2) — workflow já iniciado.
1. **Endurecer** validate\_gal\_payload para fail-closed (C1).
1. **GAL-PEND-002** — sem suite sem Selenium, qualquer mudança em envio\_gal.py é arriscada.
-----
**4. Notas 0–10**

|**Aspecto**|**Nota**|**Justificativa**|
| :- | :- | :- |
|Aderência SDD|**9**|GAL-ROB-001..010 e GAL-FEAT-001..005 implementados fielmente; mascaramento presente; idempotência dual-key; CA-17 Mapa Definitivo correto.|
|Arquitetura|**6**|Hexagonal correto (porta em application/, implementação aqui). Mas envio\_gal.py concentra UI + service + helpers em 1 833 linhas; exportar\_resultados.py tem 880 linhas mortas.|
|Clareza e Enxutez|**5**|7 funções acima de 100 linhas. 880 linhas inalcançáveis. Adapter UI grande.|
|Robustez|**7**|Atomic CSV (temp + os.replace + lock), retry\_with\_backoff, mascaramento sensível, fail-closed em CSV antecipado. Pontos fracos: validate\_gal\_payload fail-open, GAL-PEND-001.|
|Manutenibilidade|**5**|Tamanho de envio\_gal.py e ausência de testes sem Selenium dificultam evolução segura. 880 linhas mortas atrapalham diff/review.|
|Testabilidade|**5**|2 testes diretos cobrem envio\_gal e gal\_formatter. **GAL-PEND-002 explícito**: falta suite sem Selenium real para evolução. Sem testes de exportar\_resultados.|
|Risco Operacional|**7**|Mascaramento + idempotência + atomic write mitigam riscos primários. PNG em debug/ pode conter dados sensíveis se não tratado (vide E1).|
|Prontidão para Evolução|**6**|GAL-PEND-001/002 são pré-requisitos para evolução segura. Decomposição de envio\_gal.py é necessária.|
|**Geral**|**6,5**|Camada **funcionalmente madura** (GAL-ROB-001..010 honestamente implementados) mas **estruturalmente pesada** (1 833 linhas concentradas, 880 mortas em outro módulo, suite sem Selenium ausente). Adequado para piloto produtivo; precisa endurecer antes de produção 10 usuários.|

-----
**5. Achados detalhados**

**A. envio\_gal.py — núcleo GAL**

[INFORMATIVO] A1 — envio\_gal.GalService implementa fielmente GAL-ROB-001..010

Evidência:

\- exportacao/envio\_gal.py:198 class GalService

\- ROB-001 worker estruturado: L630-639, 684-688

\- ROB-002 lote não abortado: L594, 674

\- ROB-003 aviso falhas paginas: L690-698

\- ROB-004 CSV validado antes do browser: L1051-1076 (ler\_csv\_resultados)

\- ROB-005 aviso gal\_exame\_codigo ausente: L590-593, 605-606

\- ROB-006 mascaramento: L1005-1017

`    `\_SENSITIVE\_KEYS = ("paciente", "nomePaciente", "\_raw") → "\*\*\*"

\- ROB-007 inflight\_keys atomicas: L1109-1130 + L1327 (delega gal\_transactions)

\- ROB-008 normalização datas simétrica: L600-602, L791-794 (DD/MM/YYYY)

\- ROB-009 validação codigo não-vazio: L765, 807-808 (fallback codigo=codigoAmostra)

\- ROB-010 fallback codigo\_amostra: L641-671

Problema:

Nenhum. Observação positiva.

Impacto:

GAL-ROB-001..010 completos. O módulo é referência de robustez no projeto.

Recomendação:

Manter. Considerar citá-lo no design.md §3.5 como módulo exemplar.

Teste sugerido:

N/A (positivo). Eventualmente, teste de regressão E2E (depende de GAL-PEND-002).

[MÉDIO] A2 — envio\_gal.py concentra 1 833 linhas com funções gigantes

Evidência:

\- exportacao/envio\_gal.py:

`  `- salvar\_relatorios: L1240-1423 (183 linhas)

`  `- buscar\_metadados: L582-703 (121)

`  `- construir\_payload: L705-826 (121)

`  `- enviar\_amostra: L946-1049 (103)

`  `- \_append\_upload\_history\_csv: L1174-1238 (64)

\- Classe GalService inteira (L198-1423) + IntegrationApp UI (L1429-1787) +

`  `funções top-level (L1794-1802) num único arquivo.

Problema:

Módulo crítico misturando: Service (lógica), UI (CustomTkinter modal),

helpers privados, funções top-level. Refactor seguro é difícil sem

GAL-PEND-002 (suíte sem Selenium real).

Impacto:

\- Manutenibilidade reduzida; risco de regressão alto.

\- Cobertura por passo (S10-S60) requer mocks pesados.

\- Quem precisa só do GalService importa UI junto (impacta CI sem display).

Recomendação:

NÃO IMPLEMENTAR SEM GAL-PEND-002 concluído. Quando concluído, decompor:

\- exportacao/gal\_service.py (apenas GalService + helpers)

\- exportacao/gal\_ui\_integration.py (IntegrationApp + abrir\_janela\_envio\_gal +

`  `create\_gal\_page)

\- exportacao/gal\_relatorios.py (salvar\_relatorios + \_append\_upload\_history\_csv)

Mantém superfície pública via re-export em \_\_init\_\_.

Teste sugerido:

Pré-requisito: GAL-PEND-002 cria suíte sem Selenium real.

**B. exportar\_resultados.py — código morto massivo**

[ALTO] B1 — exportar\_resultados.exportar\_resultados\_gal é função-fantasma com workflow de deprecação iniciado

Evidência:

\- exportacao/exportar\_resultados.py:315 def exportar\_resultados\_gal

\- exportacao/exportar\_resultados.py:385-390:

`    `try:

`        `log\_suspected\_orphan\_usage(

`            `"exportacao.exportar\_resultados.exportar\_resultados\_gal",

`            `rows=int(len(df\_processado)) if hasattr(df\_processado, "\_\_len\_\_") else 0,

`        `)

`    `except Exception:

`        `pass

\- scripts/report\_exportar\_resultados\_usage.py:3 docstring:

`    `"Consolida telemetria de uso runtime de exportar\_resultados\_gal no sistema.log."

\- Grep `exportar\_resultados\_gal` em runtime (excluindo \_\_pycache\_\_/\_rollback/tests):

`  `ZERO callers ativos. Únicas ocorrências: definição própria e script de

`  `análise de telemetria.

Problema:

Função carrega telemetria explícita para monitorar "suspeita de uso órfão".

Workflow de deprecação iniciado mas não concluído. Em código de produção

há ~1 000 linhas que existem apenas para "rollback tecnico".

Impacto:

\- Superfície de manutenção/auditoria inflada.

\- Dúvida persistente sobre status do módulo para novos contribuidores.

\- Workflow elegante porém inacabado.

Recomendação:

ABRIR DHP NOVA "Concluir deprecação de exportar\_resultados\_gal":

(A) Inspecionar logs (`scripts/report\_exportar\_resultados\_usage.py`) para

`    `confirmar zero uso runtime em janela ≥30 dias;

(B) Após confirmação, substituir corpo de exportar\_resultados\_gal por

`    `raise DeprecationWarning ou removê-la;

(C) Remover bloco morto L405-1175 (vide B2).

NÃO IMPLEMENTAR SEM DECISÃO HUMANA (módulo amplo, fluxo de exportação

crítico para garantir transição limpa).

Teste sugerido:

Análise do log via scripts/report\_exportar\_resultados\_usage.py — não é

um teste pytest. Sugerir: rodar script numa janela longa e arquivar

snapshot como evidência da DHP.

[ALTO] B2 — 880 linhas inalcançáveis após return na L394

Evidência:

\- exportacao/exportar\_resultados.py:392-403

`    `# Fluxo novo (Fase 1 AN-01): UI adapter -> core desacoplado.

`    `# Mantemos o corpo legado abaixo apenas como fallback de rollback tecnico.

`    `return \_executar\_exportacao\_gal\_ui(...)

\- Linhas 405-1175 contêm corpo legado completo (~880 linhas) inalcançável

`  `após o return da L394.

\- Linhas em branco intercaladas (vide L405-419 inspecionado) sugerem

`  `formatação preservada para diff legível.

Problema:

Código morto MASSIVO em arquivo de produção, com comentário admitindo

intenção ("fallback de rollback tecnico"). Mas Python não tem `if-rollback`,

então as 880 linhas existem APENAS para servir como referência humana de

versão anterior — algo que `git history` faz com mais segurança.

Impacto:

\- Tamanho do arquivo dobra (1 294 vs ~414 efetivos).

\- Linters reportam código não utilizado em larga escala.

\- Diff/review fica diluído.

Recomendação:

Junto à DHP B1, remover L405-1175 (versão anterior estará em git).

NÃO IMPLEMENTAR SEM DECISÃO HUMANA. Política HIG sugere preservar arquivos

inteiros; aqui o que é preservado é bloco morto DENTRO de arquivo ativo —

diferente.

Teste sugerido:

tests/test\_exportar\_resultados\_no\_unreachable.py — usar ast + grafo de

controle simples para detectar linhas após return incondicional em

módulo de produção. Allowlist explícita inicial.

**C. Validação fail-open**

[ALTO] C1 — gal\_payload\_contract.validate\_gal\_payload é fail-OPEN

Evidência:

\- exportacao/gal\_payload\_contract.py:62-77 validate\_gal\_payload retorna

`  `list[str] (erros) em vez de lançar.

\- Comentário L81-85 admite que campos podem estar "intencionalmente vazios"

`  `sob USE\_GAL\_ENVIO\_SEM\_METADADOS (S24).

\- Schema versionado v1.0.0 (GAL\_PAYLOAD\_SCHEMA\_VERSION).

Problema:

Contrato declara validação mas devolve lista. O caller PRECISA verificar.

Em código com 7 callers diretos potenciais, basta um esquecer e payload

vazio segue para GAL — corrompendo o histórico de envios.

Impacto:

\- Risco de envio com campos obrigatórios vazios.

\- Viola implicitamente espírito do fail-closed (CLAUDE.md §6).

\- Inconsistência com gal\_payload\_dto que faz coerção fail-closed

`  `(defaults lógicos).

Recomendação:

Endurecer:

(A) Adicionar variante `assert\_valid\_gal\_payload(payload)` que LANÇA

`    ``GalPayloadValidationError` (já existe em gal\_exceptions.py L40).

(B) Manter validate\_gal\_payload (fail-open) só para diagnóstico/UI; renomear

`    `para `collect\_gal\_payload\_errors`.

(C) `envio\_gal.enviar\_amostra` (linha ~946) deve chamar `assert\_valid\_\*`

`    `antes do POST.

NÃO IMPLEMENTAR SEM rodada de teste (impacta fluxo crítico).

Teste sugerido:

tests/test\_gal\_payload\_assert\_valid.py — assertVázio → raise

GalPayloadValidationError; assertCompleto → ok.

**D. Mapa Definitivo**

[INFORMATIVO] D1 — mapa\_placa\_exporter cumpre CA-17 e DASH-007

Evidência:

\- exportacao/mapa\_placa\_exporter.py:967 gerar\_mapa\_placa\_xlsx

\- L893-894: `os.makedirs(diretorio, exist\_ok=True)` em `diretorio\_saida`

`  `(recebido como argumento; chamadores passam `<data\_root>/mapas`).

\- L996-1006: nome padrão `mapa\_placa\_{slug\_exame}\_{slug\_placa}\_{YYYYMMDD\_HHMMSS}.xlsx`

`  `consumido por DASH-007 `\_localizar\_mapa\_definitivo`.

\- Dependências limpas em domain/mapa\_placa\_layout (DTOs frozen).

Problema:

Nenhum. Conforme CA-17 e DASH-007.

Impacto:

Positivo.

Recomendação:

Manter. Considerar decomposição de renderizar\_xlsx\_grade\_fisica (125 linhas)

e construir\_mapa\_de\_dataframe (104) se houver evolução futura.

Teste sugerido:

N/A imediato. Existir teste de path/nome em rodada futura seria útil.

**E. Artefatos de debug**

[ALTO] E1 — debug/gal\_login\_fail.png (116 KB) é artefato sensível em pasta versionada

Evidência:

\- exportacao/debug/gal\_login\_fail.png (116 276 bytes).

\- exportacao/debug/gal\_login\_fail.html (0 bytes — write incompleto).

\- Mecanismo de criação: envio\_gal.py:553-580 \_persist\_login\_debug\_artifacts:

`    `driver.save\_screenshot(os.path.join(debug\_dir, "gal\_login\_fail.png"))

`    `with open(os.path.join(debug\_dir, "gal\_login\_fail.html"), "w") as f:

`        `f.write(driver.page\_source)

Problema:

PNG é screenshot completo do navegador no momento da falha de login. Pode

conter:

\- URL do GAL real visível na barra de endereço;

\- Campos de usuário (texto não mascarado);

\- Mensagem de erro com detalhes técnicos;

\- Layout/elementos do GAL que podem ajudar engenharia adversa.

Está fisicamente na pasta exportacao/debug/ — sem confirmar se .gitignore

cobre.

Impacto:

\- Risco de exposição de informação sensível se versionado/distribuído.

\- HTML vazio sugere write incompleto na sessão anterior — pode mascarar

`  `diagnóstico futuro.

Recomendação:

ABRIR DHP de housekeeping:

(A) Confirmar se debug/ está em .gitignore. Se não, adicionar.

(B) Definir política de retenção (ex.: rotação por timestamp, max N

`    `arquivos, expurgo após dias).

(C) Remover PNG atual se julgado sensível (inspeção humana primeiro,

`    `via ferramenta segura).

(D) Garantir flush+close em escrita HTML para evitar 0 bytes.

NÃO IMPLEMENTAR SEM DECISÃO HUMANA (arquivo pode conter dado real).

Teste sugerido:

tests/test\_debug\_artifacts\_gitignored.py — assert que exportacao/debug/

está em .gitignore + assert que nenhum .png/.html é tracked por git.

**F. Script de debug**

[BAIXO] F1 — debug\_login\_runner.py é script utilitário órfão de produção

Evidência:

\- exportacao/debug\_login\_runner.py (64 linhas).

\- Usa env vars GAL\_TEST\_USER / GAL\_TEST\_PASS (L24-25). Comentário L12:

`  `"NÃO coloque credenciais no script." ✓

\- Único caller: ele mesmo (script standalone).

\- L46-47: try/except genérico que registra apenas repr(e), sem re-raise.

Problema:

Script utilitário sem allowlist documentada. Pode ser ferramenta interna

ou esquecido.

Impacto:

Baixo. Não executa em runtime. Risco residual: alguém roda com env vars

de produção por engano.

Recomendação:

Documentar status em docstring ou mover para scripts/ se for utilitário

operacional. NÃO IMPLEMENTAR SEM DHP de housekeeping (toca pasta com debug

artifacts).

Teste sugerido:

N/A.

**G. Pendências GAL**

[ALTO] G1 — GAL-PEND-001 e GAL-PEND-002 explícitas em tasks.md, ambas pendentes

Evidência:

\- docs/specs/tasks.md (linhas 285-286):

`  `- GAL-PEND-001 (S3/S6): retry com classificação de erro transitório vs

`    `definitivo em enviar\_amostra(). Risco moderado.

`  `- GAL-PEND-002 (S18): suite de testes sem Selenium real. Pré-requisito

`    `para evolução segura do modulo GAL.

Problema:

Sem GAL-PEND-002, qualquer refactor em envio\_gal.py (A2) ou exportar\_resultados

(B1/B2) fica arriscado. Sem GAL-PEND-001, falhas transitórias do GAL podem

ser tratadas como definitivas (amostra fica marcada como erro\_critico em

vez de retry).

Impacto:

\- Bloqueia decomposição de envio\_gal.py (A2).

\- Aumenta retrabalho em incidentes de rede transitórios.

Recomendação:

Priorizar GAL-PEND-002 (mocks de driver + requests) antes de qualquer

mudança estrutural. Em sequência, GAL-PEND-001.

Teste sugerido:

GAL-PEND-002 É a suite. Esqueleto: tests/test\_gal\_service\_no\_selenium.py

com fixtures fake-driver + responses mock.

**H. Limpeza / outros**

[BAIXO] H1 — Typo `any` vs `Any` em exportar\_resultados.py:336

Evidência:

\- exportacao/exportar\_resultados.py:336 `exam\_cfg: any = None`

\- `any` é builtin function; `typing.Any` é o type hint correto.

\- Não causa bug runtime (annotation ignorada), mas IDE/mypy reportam.

Problema:

Limpeza. Apenas estética/correto uso de tipos.

Impacto:

Inexistente em runtime.

Recomendação:

Corrigir em rodada de housekeeping junto à B1/B2.

Teste sugerido:

N/A.

[BAIXO] H2 — Mascaramento limitado a 3 chaves; pode escapar dados em logs amplos

Evidência:

\- exportacao/envio\_gal.py:1005-1017 \_SENSITIVE\_KEYS = ("paciente",

`  `"nomePaciente", "\_raw")

\- Resposta do GAL pode conter outras chaves sensíveis: "cpf", "nome",

`  `"endereco", "telefone", etc. (estrutura do endpoint não enumerada aqui).

Problema:

Lista de chaves mascaradas é heurística. Qualquer chave nova adicionada

pelo backend GAL passa sem mascaramento.

Impacto:

Risco baixo se backend é estável; risco crescente se backend evoluir.

Recomendação:

Considerar inversão: allowlist de chaves SEGURAS para log (codigoAmostra,

status, http\_status) em vez de blocklist de SENSITIVE\_KEYS. Mudança

arquitetural — junto à DHP de A2 ou em rodada própria de hardening.

Teste sugerido:

tests/test\_envio\_gal\_response\_masking.py — payload mock com 6 chaves

sensíveis, assert que log final contém apenas allowlist.

-----
**Consolidação dos subagentes simulados**

|**Subagente**|**Veredicto**|
| :- | :- |
|**Arquiteto SDD**|envio\_gal exemplar (GAL-ROB completo). exportar\_resultados em deprecação inacabada. mapa\_placa\_exporter cumpre CA-17.|
|**Bug Hunter**|C1 (validate\_gal\_payload fail-open) é o mais sério em runtime. E1 (debug PNG) é risco de segurança. H1 (typo any) cosmético.|
|**Código Morto / Redundância**|B1/B2 (880 linhas mortas + telemetria de deprecação); workflow correto mas inacabado.|
|**Especialista em Testes**|2 testes diretos. **GAL-PEND-002 explicitamente pendente**: sem suite sem Selenium, refactor é arriscado.|
|**Revisor de Enxutez**|7 funções acima de 100 linhas. envio\_gal.py (1 833) e exportar\_resultados.py (1 294) são os maiores. Decomposição depende de testes.|

**Próximas decisões humanas relevantes**

1. **DHP B1/B2** — concluir deprecação de exportar\_resultados\_gal (workflow já iniciado com telemetria).
1. **DHP E1** — gestão de exportacao/debug/ (retenção, gitignore, expurgo do PNG atual).
1. **GAL-PEND-002** — pré-requisito para A2 (decomposição de envio\_gal.py).
1. **GAL-PEND-001** — retry transitório/definitivo (independente, mas pode ser conjunto).
1. **C1** — endurecer validate\_gal\_payload (rodada de teste; impacta caller crítico).

**Resumo de ações priorizadas**

1. **[ALTO] GAL-PEND-002** — primeira prioridade (destrava todo o resto).
1. **[ALTO] C1** — endurecer validação para fail-closed.
1. **[ALTO] B1/B2** — DHP para concluir deprecação + remover 880 linhas mortas.
1. **[ALTO] E1** — DHP para debug/ (gitignore + retenção + flush HTML).
1. **[ALTO] GAL-PEND-001** — retry transitório/definitivo.
1. **[MÉDIO] A2** — decomposição de envio\_gal.py (depende de GAL-PEND-002).
1. **[BAIXO] H1/H2/F1** — housekeeping em rodada conjunta.

Nenhuma alteração foi realizada nesta rodada. PNG sensível não foi aberto.



**Auditoria SDD READ-ONLY — extracao/**

**1. Escopo analisado**

**Pasta alvo:** C:\Integragal - Backup - 20260128\_151811\extracao\

**Arquivos analisados (3 arquivos, ~39 KB):**

|**Arquivo**|**Linhas**|**Tamanho**|
| :- | :- | :- |
|[**init**.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/extracao/__init__.py)|1|0 B|
|[busca_extracao.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/extracao/busca_extracao.py)|865|36,7 KB|
|[mapeamento_placas.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/extracao/mapeamento_placas.py)|87|2,6 KB|

**Não abertos:** \_\_pycache\_\_/\*.pyc.

**Fontes SDD lidas:**

- CLAUDE.md §4 (estrutura principal — **extracao/ ausente da lista canônica**)
- CLAUDE.md §12 (decisões pós-T06: regra de delegação)
- AGENTS.md §4/§12
- docs/specs/design.md:27-29 (T06 promovido; pattern strangler removido)
- docs/specs/higienizacao\_implantacao.md:112 (**"extracao/ (legado; use case real em application/extraction\_plate\_mapping\_use\_case.py; confirmado sem imports de producao em REL-002)"**)
- docs/specs/ui\_spec.md:19
- docs/specs/tasks.md (T06, HIG-008, REL-002)
- Concorrentes canônicos: application/extraction\_plate\_mapping\_use\_case.py, application/equipment\_extraction\_use\_case.py, application/file\_chooser\_port.py, ui/modules/extraction\_plate\_mapping.py, domain/plate\_mapping.py.
-----
**2. Mapa da pasta**

extracao/                                  (LEGADO órfão — não consta em CLAUDE.md §4)

├─ \_\_init\_\_.py                              (vazio)

├─ busca\_extracao.py                        (865 linhas — UI Tkinter modal LEGADA)

└─ mapeamento\_placas.py                     (87 linhas — facade de logging sobre domain.plate\_mapping)

**Principais módulos & responsabilidades (declaradas).**

- **busca\_extracao.py**: "Interface Tkinter/CustomTkinter para seleção, validação e mapeamento de planilha de extração (FASE 4). Janela modal que retorna mapeamento com metadados." (cabeçalho).
  - BuscaExtracaoApp(AfterManagerMixin, ctk.CTkToplevel) — modal (não embedded).
  - carregar\_dados\_extracao(parent) — entrypoint público (extracao/busca\_extracao.py:845).
  - Helpers: \_encontrar\_inicio\_matriz, \_extrair\_numero\_extracao, \_selecionar\_e\_validar\_planilha, \_gerar\_mapeamento (442 linhas — vide D2), \_validar\_estrutura\_planilha, \_extrair\_amostras (definida e nunca chamada).
- **mapeamento\_placas.py**: docstring "Facade para domain.plate\_mapping.gerar\_mapeamento\_\*" com logging centralizado.
  - 4 funções (gerar\_mapeamento\_24/32/48/96) — todas thin wrappers chamando domain.plate\_mapping.\_\* + registrar\_log + re-raise em try/except.

**Fluxos relevantes.**

- busca\_extracao.carregar\_dados\_extracao(parent) → BuscaExtracaoApp modal → filedialog inline → pd.read\_excel("PLANILHA EXTRAÇÃO") → \_extrair\_numero\_extracao (célula C8) → \_validar\_estrutura\_planilha (B10:M17 = 8×12) → extracao.mapeamento\_placas.gerar\_mapeamento\_{kit}(parte) → preview com grid visual editável + textbox → confirma → retorna dict {'mapeamento', 'parte', 'numero\_extracao', 'caminho\_arquivo'}.
- Fluxo **CANÔNICO concorrente** (promovido por T-06): ui/menu\_handler.abrir\_busca\_extracao → navigation\_manager.navigate\_to("extracao") → ui/modules/extraction\_plate\_mapping.py::abrir\_mapeamento\_extracao (CTkFrame embedded, NÃO modal) → application/extraction\_plate\_mapping\_use\_case.build\_extraction\_mapping(df\_bloco, kit, parte) → domain/plate\_mapping.gerar\_mapeamento\_\*. NÃO toca extracao/.

**Dependências internas.**

- extracao/busca\_extracao.py importa: extracao.mapeamento\_placas (4 funções), utils.after\_mixin.AfterManagerMixin, utils.logger.registrar\_log, services.core.config\_service (lazy em try/except).
- extracao/mapeamento\_placas.py importa: domain.plate\_mapping (4 funções), utils.logger.registrar\_log.

**Dependências externas.** tkinter (filedialog, messagebox), customtkinter, pandas, openpyxl (via pandas engine).

**Consumidores externos.**

- extracao/busca\_extracao.py — **órfão de produção** (subagente B: zero callers em application/, ui/, services/). Único caller: extracao/mapeamento\_placas.py indireto pela importação inversa (FALSO — só busca\_extracao chama mapeamento\_placas).
- extracao/mapeamento\_placas.py — **órfão exceto pelo próprio busca\_extracao.py**.
- 1 referência possível em tests/test\_analysis\_service\_geometric\_expansion.py (precisa inspeção, mas o teste tem nome de geometria/expansão, pode ser apenas semelhança nominal).

**Concorrentes canônicos confirmados.**

- application/extraction\_plate\_mapping\_use\_case.py — build\_extraction\_mapping com ExtractionMappingResult (frozen DTO).
- application/equipment\_extraction\_use\_case.py + application/file\_chooser\_port.py — escolha de arquivo via Port (separação correta UI/use-case).
- ui/modules/extraction\_plate\_mapping.py — CTkFrame embedded em ModuleHost.
- domain/plate\_mapping.py — gerar\_mapeamento\_24/32/48/96 puro.
-----
**3. Diagnóstico executivo**

**Coerência com SDD.** **Baixa.** A pasta inteira é **legado documentado** (higienizacao\_implantacao.md:112) e não consta em CLAUDE.md §4. T-06 já promoveu o substituto canônico (design.md:29: "padrao strangler removido"). Convive fisicamente sem deadline de remoção.

**Enxutez.** **Insuficiente** para um legado. busca\_extracao.py tem 865 linhas concentradas, com função \_gerar\_mapeamento de 442 linhas que aninha duas janelas modais (\_open\_edit\_window 134 linhas + \_open\_detalhes\_window 71 linhas). mapeamento\_placas.py (87 linhas) é facade enxuta mas redundante.

**Redundância.** **Massiva.**

- busca\_extracao.py reimplementa o fluxo inteiro de "escolher arquivo + parse + mapear + editar" que está canonicamente em application/extraction\_plate\_mapping\_use\_case.py + ui/modules/extraction\_plate\_mapping.py + application/file\_chooser\_port.py.
- mapeamento\_placas.py adiciona apenas logging sobre domain.plate\_mapping — application/extraction\_plate\_mapping\_use\_case.\_load\_plate\_mapping (linhas 86-94) já faz isto sem o módulo intermediário.

**Bugs prováveis (residuais — código não executa).**

1. **Código morto INTERNO em busca\_extracao.\_gerar\_mapeamento**: flatten row-major calculado mas nunca usado (linhas 426-440); função \_extrair\_amostras definida mas nunca chamada; coluna Amostra atribuída duas vezes (linhas 450-460 — segunda sobrescreve a primeira) — risco de bug se reativado.
1. **5+ blocos try/except silenciosos** em cleanup Tk (consistente com legado pré-SDD).

**Risco arquitetural.** **Médio.** Pasta órfã sem deadline ≈ tentação de reativação. Se algum desenvolvedor importar from extracao.busca\_extracao import carregar\_dados\_extracao por engano, contornaria T-06 e ressuscitaria o pattern strangler proibido.

**Violação SDD.** **Latente, não materializada.** busca\_extracao.py IMPLEMENTA exatamente o anti-padrão proibido em CLAUDE.md §12: "Nao referenciar ExtractionUseCase ou TkFileChooser diretamente". Mas como nenhum código de produção o consome, viola apenas LATENTEMENTE.

**Recomendação geral.** **AJUSTAR via DHP** (mesma natureza da pasta analise/).

Três opções, todas requerem **DHP nova**:

- (A) Mover para docs/obsoletos/extracao/ (símil HIG-005/HIG-006);
- (B) Remover fisicamente (rodada própria, símil REL-004);
- (C) Manter como sandbox com README explícito + guardião de import-ban.

A política DEC-002/DEC-004 favorece preservação física, então **A** ou **C** são mais alinhadas. Em paralelo, criar guardião de import-ban (não precisa de DHP).

-----
**4. Notas 0–10**

|**Aspecto**|**Nota**|**Justificativa**|
| :- | :- | :- |
|Aderência SDD|**3**|Pasta não consta em §4. T-06 já promoveu substituto. busca\_extracao.py materializa anti-padrão proibido em §12 (latente).|
|Arquitetura|**3**|Camada paralela à canônica. Mistura UI + use-case + IO + edição no mesmo arquivo de 865 linhas.|
|Clareza e Enxutez|**3**|Função de 442 linhas com 2 janelas aninhadas; 3 trechos de código morto interno.|
|Robustez|**5**|try/except em pontos chave; messagebox para usuário; logs ERROR. Mas swallowed silencioso em cleanup Tk.|
|Manutenibilidade|**3**|Não deve ser mantido (legado). Tamanho impede refactor seguro.|
|Testabilidade|**2**|Nenhum teste em tests/ cobre. Referência possível em tests/test\_analysis\_service\_geometric\_expansion.py pode ser apenas nominal.|
|Risco Operacional|**7**|Zero callers de produção = risco runtime baixo. Risco residual de reativação acidental.|
|Prontidão para Evolução|**2**|Pasta inteira é candidata a docs/obsoletos/. Não deve evoluir.|
|**Geral**|**4**|Legado órfão documentado, sem deadline. Adequada para deprecação formal via DHP. Não-pronta para qualquer uso novo.|

-----
**5. Achados detalhados**

**A. Status SDD do pacote**

[ALTO] A1 — Pasta extracao/ é legado órfão documentado, sem deadline de remoção

Evidência:

\- CLAUDE.md §4 (estrutura principal): `extracao/` NÃO consta na lista canônica.

\- docs/specs/higienizacao\_implantacao.md:112:

`    `"extracao/ (legado; use case real em application/extraction\_plate\_mapping\_use\_case.py;

`     `confirmado sem imports de producao em REL-002)."

\- docs/specs/design.md:27-29:

`    `"T06 promovido; padrao strangler removido."

\- CLAUDE.md §12 (decisões pós-T06):

`    `"ui/menu\_handler.py::abrir\_busca\_extracao delega para

`     `ui/modules/extraction\_plate\_mapping.py::abrir\_mapeamento\_extracao.

`     `Nao referenciar ExtractionUseCase ou TkFileChooser diretamente no menu\_handler."

\- Subagente B confirmou: zero imports de produção em application/, ui/, services/.

Problema:

Camada paralela legada coexistindo fisicamente sem deadline de tratamento.

T-06 promoveu o substituto canônico e removeu o strangler, mas o original

permanece no disco. Mesma natureza estrutural da pasta `analise/` (auditada

anteriormente, DHP-13 sugerida).

Impacto:

\- Risco de reativação acidental (alguém faz `from extracao.busca\_extracao

`  `import carregar\_dados\_extracao`, contornando T-06).

\- Confusão para novos contribuidores ("qual fluxo é o vivo?").

\- Custo de manutenção zero hoje, mas custo de inspeção em cada auditoria.

Recomendação:

ABRIR DHP NOVA "destino de extracao/". Opções:

(A) mover para docs/obsoletos/extracao/ (símil HIG-005/HIG-006);

(B) remover fisicamente (rodada própria);

(C) manter com README "DEPRECATED — não usar" + guardião de import-ban.

NÃO IMPLEMENTAR SEM DECISÃO HUMANA. Política DEC-002/DEC-004 favorece A ou C.

Teste sugerido:

tests/test\_extracao\_legacy\_no\_runtime\_imports.py — guardião AST que falhe

se algum .py em runtime (application/, ui/, services/, exportacao/,

autenticacao/, browser/, scripts/) contiver `from extracao` ou

`import extracao`. NÃO PRECISA DE DHP (apenas formaliza estado declarado

em higienizacao\_implantacao.md:112).

[ALTO] A2 — busca\_extracao.py materializa anti-padrão proibido em CLAUDE.md §12

Evidência:

\- CLAUDE.md §12: "Nao referenciar ExtractionUseCase ou TkFileChooser

`  `diretamente no menu\_handler."

\- extracao/busca\_extracao.py:267-355 \_selecionar\_e\_validar\_planilha:

`  `combina filedialog.askopenfilename + pd.read\_excel + validação inline.

\- extracao/busca\_extracao.py:382-823 \_gerar\_mapeamento: combina cálculo

`  `de mapeamento + preview UI + edição + grid visual + textbox em uma única

`  `função de 442 linhas.

Problema:

O módulo IMPLEMENTA exatamente o "ExtractionUseCase + TkFileChooser num

mesmo lugar" que a regra arquitetural T-06 proíbe. Hoje só não viola

porque ninguém o chama em produção.

Impacto:

\- Latente: zero impacto runtime.

\- Real: qualquer reativação reintroduz o pattern strangler já removido.

\- Reforça necessidade de A1 (guardião de import-ban).

Recomendação:

Não tocar isoladamente. Endereçar junto à DHP A1.

Teste sugerido:

Coberto pelo teste sugerido em A1.

**B. Redundância de facade**

[MÉDIO] B1 — mapeamento\_placas.py é facade de logging redundante sobre domain.plate\_mapping

Evidência:

\- extracao/mapeamento\_placas.py:13-86 — 4 funções (gerar\_mapeamento\_24/32/48/96).

`  `Cada uma faz:

`    `1) chamar domain.plate\_mapping.\_{kit}(parte)

`    `2) log INFO de sucesso

`    `3) try/except → log WARNING + re-raise

\- domain.plate\_mapping (auditado) já implementa as 4 funções puras.

\- application/extraction\_plate\_mapping\_use\_case.py:86-94 já chama

`  `domain.plate\_mapping diretamente em `\_load\_plate\_mapping` (com seu

`  `próprio tratamento).

Problema:

Camada intermediária sem valor agregado claro além de logging. O caller

canônico (application) prefere abstração própria e não usa esta facade.

Só sobrevive porque `busca\_extracao.py` ainda a chama.

Impacto:

\- Manutenção dupla: qualquer evolução em domain.plate\_mapping precisaria

`  `refletir no facade se este voltar a ser usado.

\- Confusão arquitetural: três níveis (busca\_extracao → mapeamento\_placas

`  `→ domain.plate\_mapping) onde dois bastariam.

Recomendação:

Tratar junto à DHP A1. Se A escolhido (mover para docs/obsoletos/), levar

junto. Se C (manter como sandbox), documentar no README a redundância.

NÃO IMPLEMENTAR REMOÇÃO ISOLADA SEM DHP.

Teste sugerido:

N/A.

**C. Tamanho e código morto interno**

[MÉDIO] C1 — \_gerar\_mapeamento concentra 442 linhas com 2 janelas modais aninhadas

Evidência:

\- extracao/busca\_extracao.py:382-823 \_gerar\_mapeamento (442 linhas)

`  `- aninha \_open\_edit\_window (L564-697, 134 linhas)

`  `- aninha \_open\_detalhes\_window (L699-769, 71 linhas)

`  `- calcula flatten row-major (L426-430) E flatten column-major (L432-436);

`    `usa apenas column-major (flat\_col)

`  `- atribui df\_map["Amostra"] duas vezes (L450 e L457), segunda sobrescreve

Problema:

Função monolítica com closures de UI dentro de closures. Difícil rastrear

fluxo de dados. Lógica duplicada (atribuição de Amostra).

Impacto:

Latente apenas (módulo não executa). Se reativado, refactor é arriscado.

Recomendação:

Não refatorar. Endereçar junto à DHP A1. Em rodada A: mover como-está

(preserva história). Em rodada B: remover.

Teste sugerido:

N/A.

[BAIXO] C2 — Função \_extrair\_amostras definida e nunca chamada

Evidência:

\- extracao/busca\_extracao.py:362-380 \_extrair\_amostras

`  `(cria DataFrame iterando 12 colunas × 8 linhas).

\- Grep do nome dentro do próprio arquivo: 1 ocorrência (a definição).

Problema:

Função interna inutilizada. Sintoma de código incremental sem cleanup.

Impacto:

Inexistente. Latente.

Recomendação:

Endereçar junto à DHP A1.

Teste sugerido:

N/A.

**D. Conformidade T-06 do menu\_handler (informativo)**

[INFORMATIVO] D1 — menu\_handler.abrir\_busca\_extracao DELEGA corretamente conforme T-06

Evidência:

\- Subagente B confirmou em ui/menu\_handler.py:684-699:

`    `def abrir\_busca\_extracao(self):

`        `# ... reset de estado ...

`        `if hasattr(self.main\_window, "navigation\_manager"):

`            `self.main\_window.navigation\_manager.navigate\_to("extracao")

\- Nenhuma importação de `extracao/` em menu\_handler.py.

\- design.md:29: "T06 promovido; padrao strangler removido."

Problema:

Nenhum. Observação positiva.

Impacto:

Confirma que o usuário-final (UI) está usando o fluxo canônico

(ui/modules/extraction\_plate\_mapping.py + application/...). O `extracao/`

realmente não é exercitado em runtime.

Recomendação:

Manter. Considerar adicionar comentário em menu\_handler.abrir\_busca\_extracao

referenciando T-06 e §12 do CLAUDE.md para evitar regressão por novos

contribuidores.

Teste sugerido:

Coberto pelo guardião sugerido em A1.

-----
**Consolidação dos subagentes simulados**

|**Subagente**|**Veredicto**|
| :- | :- |
|**Arquiteto SDD**|Pasta inteira é legado órfão documentado (higienizacao\_implantacao.md:112); T-06 já fez substituição canônica. Falta apenas DHP de destino e guardião de import-ban.|
|**Bug Hunter**|Sem bugs runtime (zero callers). Latentes: código morto interno (C1/C2), \_gerar\_mapeamento gigante.|
|**Código Morto / Redundância**|Pasta INTEIRA é redundante. mapeamento\_placas.py é facade sem valor agregado. \_extrair\_amostras órfã interna.|
|**Especialista em Testes**|Cobertura zero. Recomenda apenas guardião de import-ban (A1).|
|**Revisor de Enxutez**|busca\_extracao.py (865 linhas) é o oposto de enxuto. Não deve ser refatorado — deve ser arquivado.|

**Próximas decisões humanas relevantes**

1. **DHP nova A1** — destino de extracao/\* (A: mover para docs/obsoletos/; B: remover; C: manter como sandbox). Mesma natureza da DHP-13 sugerida para analise/.
1. Considerar **DHP coordenada** com a de analise/ (DHP-13) para tratar ambas as "pastas paralelas órfãs" no mesmo movimento.

**Resumo de ações priorizadas**

1. **[ALTO] A1+A2** — DHP coordenada para destino de extracao/ (juntar com DHP-13 de analise/).
1. **[ALTO] Guardião de import-ban** — tests/test\_extracao\_legacy\_no\_runtime\_imports.py (NÃO precisa de DHP; formaliza REL-002).
1. **[MÉDIO] B1/C1/C2** — endereçados junto à DHP A1.
1. **[INFORMATIVO] D1** — adicionar comentário T-06 em menu\_handler.abrir\_busca\_extracao para preservar conhecimento.

Nenhuma alteração foi realizada nesta rodada.



Confirmado: **ZERO testes usam interface** apesar da fachada existir EXPLICITAMENTE "para testes" (higienizacao\_implantacao.md:113). Mas os 7 símbolos reexportados existem em ui/modules/. Consolidando.

-----
**Auditoria SDD READ-ONLY — interface/**

**1. Escopo analisado**

**Pasta alvo:** C:\Integragal - Backup - 20260128\_151811\interface\

**Arquivos analisados (7 arquivos, ~1,8 KB total — pasta minúscula):**

|**Arquivo**|**Linhas**|**Bytes**|
| :- | :- | :- |
|[**init**.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/interface/__init__.py)|42|855|
|[dashboard.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/interface/dashboard.py)|4|68|
|[exportacao_relatorios.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/interface/exportacao_relatorios.py)|14|236|
|[graficos_qualidade.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/interface/graficos_qualidade.py)|4|93|
|[historico_analises.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/interface/historico_analises.py)|4|93|
|[sistema_alertas.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/interface/sistema_alertas.py)|18|318|
|[visualizador_exame.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/interface/visualizador_exame.py)|4|149|

**Não analisados:** \_\_pycache\_\_/\*.pyc. Nenhum arquivo sensível na pasta.

**Fontes SDD lidas:**

- CLAUDE.md §4 (estrutura — menciona "ui/ e interface/ - camada de apresentacao CustomTkinter")
- docs/specs/higienizacao\_implantacao.md:113 — **"interface/ (fachada de compatibilidade para testes; re-exports puros de ui.modules.\*; nenhum import de producao)"**
- docs/specs/higienizacao\_implantacao.md:183 — **"release/app/ nao contem ... interface/ ... (legados, fachadas de teste, artefatos de debug/build; confirmados sem imports de producao em REL-002)"**
- docs/obsoletos/inventario\_de\_lixo.md:105 — "Fachada de compatibilidade para testes" / "Re-exports puros de ui.modules.\*; nenhum import de producao" / "Excluir de release/app/; testes nao entram no release"
- docs/obsoletos/procedimento\_smoke\_test\_release.md:121 — "Fachada de teste sem imports de producao"
- docs/obsoletos/documento\_de\_passagem.md:445 — REL-001 listou interface/ entre 12 itens não cobertos pelo manifest HIG-008 original.
-----
**2. Mapa da pasta**

interface/                                    (FACADE DE COMPATIBILIDADE PARA TESTES)

├─ \_\_init\_\_.py                                 (42 linhas — agregador, reexporta 15 símbolos)

├─ dashboard.py                                (4 linhas → ui.modules.dashboard.Dashboard)

├─ exportacao\_relatorios.py                    (14 linhas → ui.modules.exportacao\_relatorios.\*)

├─ graficos\_qualidade.py                       (4 linhas → ui.modules.graficos\_qualidade.GraficosQualidade)

├─ historico\_analises.py                       (4 linhas → ui.modules.historico\_analises.HistoricoAnalises)

├─ sistema\_alertas.py                          (18 linhas → ui.modules.sistema\_alertas.\*)

└─ visualizador\_exame.py                       (4 linhas → ui.modules.visualizador\_exame.\*)

**Responsabilidades percebidas (declaradas).**

- **\_\_init\_\_.py (linhas 1-5):** "Camada de compatibilidade para o pacote legacy interface. Reexporta as classes e funcoes atualmente localizadas em ui.modules."
- Cada arquivo: shim de re-export puro (1-2 from ui.modules.X import Y + \_\_all\_\_).
- **Função única:** permitir que código antigo (especialmente testes) que usava from interface.X import Y continue funcionando após o conteúdo migrar para ui.modules.X.

**Fluxos relevantes.** Nenhum fluxo de dados. Apenas resolução de imports.

**Dependências internas.** Cada arquivo importa do correspondente em ui.modules.\*. Todos os 7 símbolos canônicos (Dashboard, VisualizadorExame, GraficosQualidade, ExportadorRelatorios, HistoricoAnalises, GerenciadorAlertas, CentroNotificacoes) **existem** em ui/modules/\*.py (verificado: 10 arquivos com matches).

**Dependências externas.** Nenhuma.

**Consumidores externos confirmados.**

- **ZERO consumidores em produção.** Grep from interface / import interface em todo o repo (excluindo \_\_pycache\_\_): **0 matches**.
- **ZERO consumidores em testes.** Grep no diretório tests/ por "interface": **0 matches**. **Divergência:** a documentação declara que é "fachada de COMPATIBILIDADE PARA TESTES", mas nenhum teste atual a consome.
- 5 menções em docs/ (todas explicativas/de governança HIG, não imports).
-----
**3. Diagnóstico executivo**

**Coerência com SDD.** **Alta.** Fachada documentada explicitamente em higienizacao\_implantacao.md:113/183, excluída do release (HIG-008), classificada em inventario\_de\_lixo.md:105. Governança correta — diferente das pastas analise/ (sem DEC) ou extracao/ (T-06 promovido mas pasta esquecida).

**Enxutez.** **Excelente.** Total ~1,8 KB para 7 arquivos, todos shims puros. Não há código real de negócio nesta pasta.

**Redundância.** **Mínima e justificada.** \_\_init\_\_.py reexporta os mesmos 15 símbolos que os 6 arquivos individuais já cobrem — boilerplate duplo, mas é o padrão correto para pacote facade (caller pode usar from interface import Dashboard ou from interface.dashboard import Dashboard).

**Bugs prováveis.** **Nenhum em runtime** (sem callers). Risco residual: se algum dia ui.modules renomear um símbolo, os imports nesta pasta quebrarão na primeira carga — mas isso seria detectado imediatamente.

**Risco arquitetural.** **Baixo.** Fachada estável, sem código de negócio, sem violações.

**Violação SDD.** **Divergência leve:** a documentação afirma que existe "para testes", mas **nenhum teste atual a consome**. Ou (a) os testes que justificavam a fachada foram removidos sem cleanup, ou (b) a fachada é preservada profilaticamente para testes futuros / código externo não controlado. Não é violação de governança — é divergência entre justificativa declarada e uso real.

**Recomendação geral.** **MANTER como está + abrir DHP leve para reconsiderar status.**

A pasta cumpre todos os princípios SDD (documentada, excluída do release, sem regras de negócio, sem violações). Se confirmado que ninguém precisa dela, pode ser arquivada (símil HIG-005/006) em rodada futura. Por ora, mantê-la é mais barato e seguro que removê-la.

-----
**4. Notas 0–10**

|**Aspecto**|**Nota**|**Justificativa**|
| :- | :- | :- |
|Aderência SDD|**9**|Fachada documentada em HIG (linhas 113, 183), excluída do release, classificada como compatibilidade. Pequeno desvio: justificativa "para testes" sem testes consumindo.|
|Arquitetura|**9**|Re-export puro, sem regra de negócio, sem violação de camada. Padrão canônico de facade.|
|Clareza e Enxutez|**10**|7 arquivos, todos shims de 4-18 linhas. Nenhum excesso.|
|Robustez|**9**|Sem IO, sem state, sem tratamento de erro necessário. Risco zero.|
|Manutenibilidade|**8**|Trivial de manter. Único risco: drift se ui.modules renomear símbolo (detectável imediatamente).|
|Testabilidade|**6**|Documentada como "para testes" mas zero testes a usam (A2 abaixo). Curto-circuito da própria razão de existir.|
|Risco Operacional|**10**|Zero callers em runtime + zero IO = risco operacional nulo.|
|Prontidão para Evolução|**7**|Pasta não evolui — é facade estática. Adequada se houver código externo / futuro consumindo; supérflua se ninguém precisar.|
|**Geral**|**8,5**|Pasta minúscula, bem governada, ZERO violações. Único ponto: "para testes" sem testes consumindo levanta dúvida sobre razão de ser. Manter é mais barato que tocar.|

-----
**5. Achados detalhados**

**A. Status SDD & uso real**

[INFORMATIVO] A1 — Fachada documentada com governança exemplar

Evidência:

\- interface/\_\_init\_\_.py:1-5 docstring:

`    `"Camada de compatibilidade para o pacote legacy `interface`.

`     `Reexporta as classes e funcoes atualmente localizadas em `ui.modules`."

\- docs/specs/higienizacao\_implantacao.md:113:

`    `"interface/ (fachada de compatibilidade para testes; re-exports puros

`     `de ui.modules.\*; nenhum import de producao);"

\- docs/specs/higienizacao\_implantacao.md:183:

`    `"release/app/ nao contem ... interface/ ... confirmados sem imports

`     `de producao em REL-002."

\- docs/obsoletos/inventario\_de\_lixo.md:105:

`    `"Excluir de release/app/; testes nao entram no release."

Problema:

Nenhum. Observação positiva.

Impacto:

Modelo correto de fachada legada documentada + excluída do release.

Contraste com analise/ (sem DEC, achado A1 da auditoria) e extracao/

(legado T-06 sem deadline) — interface/ está formalmente governada.

Recomendação:

Manter. Considerar citar como modelo de "como fazer deprecação correta

de pasta" no design.md.

Teste sugerido:

N/A (positivo).

[MÉDIO] A2 — Documentação afirma "para testes" mas ZERO testes usam a fachada

Evidência:

\- higienizacao\_implantacao.md:113: "fachada de compatibilidade para testes"

\- docs/obsoletos/inventario\_de\_lixo.md:105: "Fachada de compatibilidade

`  `para testes"

\- Grep `interface` no diretório `tests/`: ZERO matches.

\- Grep `from interface` / `import interface` em todo o repo: ZERO matches.

Problema:

A justificativa de existência ("compatibilidade para testes") não se

sustenta no estado atual: nenhum teste consome a fachada. Três hipóteses:

(a) Testes que justificavam foram removidos sem cleanup.

(b) Fachada é mantida profilaticamente para código externo/futuro.

(c) Documentação está desatualizada e na verdade é resíduo de migração.

Impacto:

\- Confusão para novos contribuidores ("quem usa isto?").

\- Pasta consome 7 arquivos + manutenção mental sem justificativa real.

\- Custo: baixo (1,8 KB, sem complexidade).

Recomendação:

ABRIR DHP LEVE "destino de interface/". Opções:

(A) Atualizar docs removendo "para testes" e justificando como

`    `"compatibilidade para código externo não controlado";

(B) Mover para docs/obsoletos/interface/ (símil HIG-005);

(C) Manter como está + comentário em \_\_init\_\_.py explicando o histórico.

NÃO IMPLEMENTAR SEM DECISÃO HUMANA. Política DEC-002/DEC-004 favorece

preservação física. Esta DHP pode ser coordenada com as DHPs já

sugeridas para `analise/` e `extracao/` (rodada conjunta de housekeeping

de pastas paralelas).

Teste sugerido:

N/A imediato. Se Opção C, considerar tests/test\_interface\_reexports\_intact.py

— assert que cada símbolo em \_\_init\_\_.py:\_\_all\_\_ é importável (proteção

contra drift se ui.modules renomear).

**B. Outros (informativo)**

[BAIXO] B1 — Boilerplate duplicado entre \_\_init\_\_.py e arquivos individuais

Evidência:

\- interface/\_\_init\_\_.py:7-23 reexporta 15 símbolos de ui.modules.

\- interface/dashboard.py:1 reexporta Dashboard.

\- interface/exportacao\_relatorios.py:1-6 reexporta 4 símbolos.

\- interface/graficos\_qualidade.py:1 reexporta GraficosQualidade.

\- interface/historico\_analises.py:1 reexporta HistoricoAnalises.

\- interface/sistema\_alertas.py:1-8 reexporta 6 símbolos.

\- interface/visualizador\_exame.py:1 reexporta 2 símbolos.

Problema:

Duplicação leve: caller pode usar `from interface import Dashboard`

(via \_\_init\_\_.py) OU `from interface.dashboard import Dashboard` (via

shim individual). Ambos os caminhos precisam ser mantidos em sincronia.

Impacto:

Cosmético. Padrão aceitável para facades públicas.

Recomendação:

Manter (padrão correto). Se DHP A2 escolher Opção A/C, considerar

documentar a dupla face.

Teste sugerido:

N/A.

[INFORMATIVO] B2 — Todos os 7 símbolos reexportados EXISTEM em ui/modules/

Evidência:

\- Grep por nomes reexportados em ui/modules/:

`  `- Dashboard → ui/modules/dashboard.py

`  `- VisualizadorExame → ui/modules/visualizador\_exame.py

`  `- GraficosQualidade → ui/modules/graficos\_qualidade.py

`  `- ExportadorRelatorios + exportar\_pdf/excel/csv → ui/modules/exportacao\_relatorios.py

`  `- HistoricoAnalises → ui/modules/historico\_analises.py

`  `- GerenciadorAlertas + CentroNotificacoes + Alerta + TipoAlerta +

`    `CategoriaAlerta + gerar\_alertas\_exemplo → ui/modules/sistema\_alertas.py

`  `- criar\_dados\_exame\_exemplo → ui/modules/visualizador\_exame.py

\- ui/modules/\_\_init\_\_.py também reexporta esses símbolos (confirmado).

Problema:

Nenhum.

Impacto:

Confirma integridade funcional da fachada — não há símbolos faltando

nem broken imports.

Recomendação:

Manter.

Teste sugerido:

N/A. (Eventual proteção contra drift estaria em A2 Opção C.)

-----
**Consolidação dos subagentes simulados**

|**Subagente**|**Veredicto**|
| :- | :- |
|**Arquiteto SDD**|Fachada exemplar — documentada, excluída do release, sem violações. Modelo de deprecação correta.|
|**Bug Hunter**|Zero bugs runtime (sem callers, sem IO). Risco residual zero.|
|**Código Morto / Redundância**|Pasta INTEIRA é facade — por definição "redundante" no bom sentido. Boilerplate duplo justificado pelo padrão.|
|**Especialista em Testes**|Fachada documentada "para testes" sem testes consumindo (A2). Eventual guardião de drift se A2 Opção C.|
|**Revisor de Enxutez**|Total 1,8 KB. Nada a enxugar.|

**Próximas decisões humanas relevantes**

1. **DHP leve A2** — destino de interface/ (atualizar docs / mover para obsoletos / manter + comentário). **Coordenar com DHPs já sugeridas para analise/ e extracao/** como "rodada conjunta de housekeeping de pastas paralelas órfãs".

**Resumo de ações priorizadas**

1. **[MÉDIO] A2** — DHP coordenada (conjunta com analise/ e extracao/).
1. **[INFORMATIVO] A1/B2** — manter como referência de "fachada bem feita" no design.md.
1. Nenhuma ação técnica imediata necessária.

Nenhuma alteração foi realizada nesta rodada. A pasta interface/ é a auditoria mais saudável até aqui — 1,8 KB de shims puros, bem governados, sem violações.



**Auditoria SDD READ-ONLY — scratch/**

**1. Escopo analisado**

**Pasta alvo:** C:\Integragal - Backup - 20260128\_151811\scratch\

**Arquivos analisados (4 Python + 1 .pyc órfão, ~11 KB):**

|**Arquivo**|**Linhas**|**Tamanho**|**Status**|
| :- | :- | :- | :- |
|[fix_config.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/scratch/fix_config.py)|57|2,4 KB|Script one-shot de refactor (regex sobre UI)|
|[fix_main_window.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/scratch/fix_main_window.py)|108|4,1 KB|Script one-shot reescrevendo \_configurar\_janela|
|[refactor.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/scratch/refactor.py)|99|4,4 KB|Script one-shot migrando TreeView → ScientificDataGrid|
|[search_runtime_profile.py](vscode-webview://19cner0bd8s5862t85rtir0e2qt9cg8jmkaprsmtvomk29bf1eig/scratch/search_runtime_profile.py)|12|278 B|Script de grep trivial em \_runtime\_profile|
|**pycache**/search\_upsert.cpython-313.pyc|—|1,6 KB|**.pyc ÓRFÃO**: search\_upsert.py não existe|

**Não abertos:** \_\_pycache\_\_/\*.pyc (bytecode).

**Fontes SDD lidas:**

- CLAUDE.md §4 (estrutura principal — **scratch/ AUSENTE**).
- docs/specs/higienizacao\_implantacao.md (sem menção a scratch/).
- docs/ inteiro (grep scratch/ / search\_upsert): **0 matches**.
- Grep from scratch | import scratch | scratch. no repo: **0 matches**.
-----
**2. Mapa da pasta**

scratch/                                       (RASCUNHO de dev — NÃO documentada em SDD)

├─ fix\_config.py                                (regex over ui/modules/tela\_configuracoes.py + ui/components/base\_components.py)

├─ fix\_main\_window.py                           (substitui \_configurar\_janela em ui/main\_window.py)

├─ refactor.py                                  (migra TreeView → ScientificDataGrid em ui/janela\_analise\_completa.py)

├─ search\_runtime\_profile.py                    (grep simples por "\_runtime\_profile" em ui/janela\_analise\_completa.py)

└─ \_\_pycache\_\_/

`   `└─ search\_upsert.cpython-313.pyc             (ÓRFÃO — sem .py correspondente)

**Responsabilidades percebidas.**

- Os 4 scripts são **ferramentas de refactor one-shot** executadas manualmente pelo desenvolvedor: abrem arquivos da ui/, fazem substituições regex/textual, sobrescrevem in-place.
- Nenhum import. Nenhum entrypoint. Cada arquivo é roteiro autônomo (python scratch/fix\_config.py).

**Fluxos relevantes.**

- fix\_config.py: abre c:\Users\marci\Downloads\Integragal - Backup - 20260128\_151811\ui\modules\tela\_configuracoes.py (path ABSOLUTO HARDCODED) → substitui text\_color="gray" por text\_color=Theme.TEXT\_PRIMARY → adiciona import de Theme se ausente → regex sobre ctk.CTkLabel/CTkSwitch/CTkComboBox/CTkSlider/CTkEntry para INSERIR text\_color=Theme.TEXT\_PRIMARY quando ausente → reescreve arquivo. Depois faz o mesmo em ui/components/base\_components.py.
- fix\_main\_window.py: lê ui/main\_window.py (path RELATIVO ao CWD) → busca posições start\_idx (linha começando com def \_configurar\_janela) e end\_idx (linha começando com def get\_content\_frame) → substitui bloco inteiro por hardcoded insertion (multiline string) → reescreve arquivo.
- refactor.py: abre c:/Users/marci/Downloads/... (path ABSOLUTO HARDCODED) → faz 3 substituições textuais + regex sobre \_criar\_treeview até \_selecionar\_todos → reescreve arquivo.
- search\_runtime\_profile.py: lê ui/janela\_analise\_completa.py → imprime linhas que contêm \_runtime\_profile.

**Dependências internas.** Nenhuma (scripts standalone).

**Dependências externas.** Apenas stdlib: re, os, sys.

**Consumidores externos.** **ZERO em produção ou em testes.** Grep retorna 0 matches em todo repo.

-----
**3. Diagnóstico executivo**

**Coerência com SDD.** **Nula.** Pasta inteira NÃO consta em CLAUDE.md §4, NÃO consta em higienizacao\_implantacao.md, NÃO aparece em nenhum documento SDD. Diferente de core/ (DEC-003), analise/, extracao/, interface/ — esta é a primeira pasta auditada **totalmente fora da governança**.

**Enxutez.** Cada script é pequeno (12-108 linhas), proporcional ao trabalho one-shot. Mas a pasta INTEIRA não deveria existir em árvore versionada de produção.

**Redundância.** Não há redundância funcional entre os 4 scripts (cada um modifica um arquivo diferente). Há, porém, o .pyc ÓRFÃO de search\_upsert.py — evidência de que mais scripts existiram e foram removidos sem cleanup.

**Bugs prováveis & fragilidades.**

1. **Path absoluto hardcoded** em fix\_config.py:3,43 e refactor.py:3 aponta para c:\Users\marci\Downloads\Integragal - Backup - 20260128\_151811\.... Específico da máquina do desenvolvedor (Márcio Pacheco Lab — confirmado no gitconfig). Em qualquer outro ambiente, scripts falham.
1. **Path relativo dependente de CWD** em fix\_main\_window.py:3 e search\_runtime\_profile.py:4 — executar de outro diretório falha silenciosamente ou edita arquivo errado.
1. **Sem dry-run, sem backup, sem confirmação** — open(path, 'w') sobrescreve diretamente arquivos críticos da UI (tela\_configuracoes.py, main\_window.py, janela\_analise\_completa.py, base\_components.py).
1. **Não-idempotência potencial** — fix\_config.py:24 faz regex ctk\.CTkLabel\([^)]+\) que insere text\_color=... se ausente. Se rodar duas vezes, a verificação previne duplicação. Mas fix\_main\_window.py REPLACES BLOCO INTEIRO entre marcadores — segunda execução tenta encontrar o início original e falha (print "Failed to find indices"), comportamento aceitável mas ruidoso.
1. **refactor.py usa regex (?s).\*? sobre código Python** — pode capturar trecho errado se outra função \_criar\_treeview ou \_selecionar\_todos aparecer (defensivamente: provavelmente única).
1. **Permite executar uma vez e sair com sucesso** mesmo se o trabalho não foi efetivo — print("Updated successfully") é única indicação.

**Risco arquitetural.** **Médio em "drift histórico".** Os scripts editam ui/modules/tela\_configuracoes.py, ui/main\_window.py, ui/janela\_analise\_completa.py, ui/components/base\_components.py — todos arquivos canônicos de UI. Se algum dev rodar um destes hoje, sobrepõe alterações posteriores feitas em outras rodadas SDD (ex: CFG-UI-001, DASH-007).

**Violação SDD.** **Materializada por presença + ausência:**

- Pasta NÃO existe na estrutura canônica documentada (CLAUDE.md §4).
- Scripts editam arquivos de UI sem rodada autorizada (CLAUDE.md §9: "Nao alterar arquivos fora do escopo da tarefa autorizada").
- Naming enganoso de fix\_config.py (sugere config.json mas toca UI; nada a ver com DEC-001/CA-12).

**Recomendação geral.** **DEPRECAR via DHP.** Como analise/ e extracao/. A diferença: aqui o caso é mais simples porque nenhum script é referenciado, nenhum tem teste, nenhum entra em release. Pode-se classificar como "lixo histórico de refactor" e arquivar com símil HIG-005/006.

-----
**4. Notas 0–10**

|**Aspecto**|**Nota**|**Justificativa**|
| :- | :- | :- |
|Aderência SDD|**2**|Pasta NÃO consta em CLAUDE.md §4. NÃO consta em higienizacao\_implantacao.md. NÃO consta em release/HIG-008. NÃO documentada em nenhum lugar canônico.|
|Arquitetura|**2**|Scripts standalone sem estrutura. Acessam arquivos de UI por path absoluto/relativo. Não tem \_\_init\_\_.py no padrão de módulo.|
|Clareza e Enxutez|**5**|Cada script é compacto (12-108 linhas), mas conjunto desorganizado.|
|Robustez|**2**|Zero dry-run, zero backup, zero idempotência garantida, paths hardcoded por máquina, sem tratamento de erro real.|
|Manutenibilidade|**2**|Não devem ser mantidos. Cumprem refactor de um momento e ficam como dívida.|
|Testabilidade|**0**|Zero testes. Scripts modificadores de arquivo nunca podem ser testados sem ambiente espelho.|
|Risco Operacional|**6**|Zero callers runtime = risco runtime baixo. Risco real: dev roda um destes hoje e sobrepõe alterações canônicas posteriores.|
|Prontidão para Evolução|**1**|Pasta inteira é candidata a arquivamento. Não evolui.|
|**Geral**|**3**|Rascunho de dev fora da governança SDD, com paths absolutos da máquina específica, sem testes, sem documentação, sem backup. Adequada apenas para arquivar via DHP.|

-----
**5. Achados detalhados**

**A. Status SDD**

[ALTO] A1 — Pasta scratch/ totalmente FORA da governança SDD

Evidência:

\- CLAUDE.md §4 (Estrutura principal do projeto): scratch/ NÃO listado.

`  `Lista canônica: domain/, application/, services/, ui/, interface/,

`  `exportacao/, browser/, config/, banco/, docs/specs/, tests/.

\- docs/specs/higienizacao\_implantacao.md (manifest HIG-008): scratch/

`  `NÃO mencionado nem como legado, nem como excluído de release.

\- Grep "scratch/" em todo o diretório docs/: 0 matches.

\- Grep "from scratch | import scratch | scratch." em runtime: 0 matches.

Problema:

Pasta inteira existe fisicamente, contém scripts modificadores de arquivos

canônicos de UI (tela\_configuracoes.py, main\_window.py,

janela\_analise\_completa.py, base\_components.py), mas SDD não a registra.

Contraste: analise/ tem DHP-13 sugerida, extracao/ está em higienizacao,

interface/ é fachada documentada, core/ é DEC-003. Apenas scratch/ é

invisível para SDD.

Impacto:

\- Risco operacional: dev encontra a pasta, roda `python scratch/fix\_\*.py`,

`  `reverte alterações canônicas (CFG-UI-001, DASH-007, etc.).

\- Governança: viola implicitamente CLAUDE.md §9 ("Nao alterar arquivos

`  `fora do escopo da tarefa autorizada") — scripts editam arquivos UI sem

`  `rodada SDD.

\- Custo SDD: cada nova auditoria precisa redescobrir o status desta pasta.

Recomendação:

ABRIR DHP NOVA "destino de scratch/". Opções:

(A) mover para docs/obsoletos/scratch/ (símil HIG-005/HIG-006);

(B) remover fisicamente (rodada própria — política DEC-002/004 não

`    `favorece, mas aqui não há código de produção a preservar);

(C) manter como sandbox com README explícito "RASCUNHOS ONE-SHOT — não

`    `executar sem revisão" + adicionar `scratch/` a .gitignore para futuras

`    `contribuições.

COORDENAR com DHPs já sugeridas para analise/, extracao/ e interface/ —

rodada conjunta de housekeeping de pastas paralelas.

NÃO IMPLEMENTAR SEM DECISÃO HUMANA.

Teste sugerido:

tests/test\_scratch\_not\_in\_runtime.py — guardião AST que falhe se algum

.py em runtime (application/, ui/, services/, exportacao/, etc.)

contiver `from scratch` ou `import scratch`. Allowlist vazia.

**B. Riscos operacionais dos scripts**

[ALTO] A2 — Paths absolutos hardcoded apontam para máquina específica do desenvolvedor

Evidência:

\- scratch/fix\_config.py:3

`    `file\_path = r'c:\Users\marci\Downloads\Integragal - Backup - 20260128\_151811\ui\modules\tela\_configuracoes.py'

\- scratch/fix\_config.py:43

`    `file\_path\_bc = r'c:\Users\marci\Downloads\Integragal - Backup - 20260128\_151811\ui\components\base\_components.py'

\- scratch/refactor.py:3

`    `file\_path = "c:/Users/marci/Downloads/Integragal - Backup - 20260128\_151811/ui/janela\_analise\_completa.py"

\- Paths apontam para Downloads/ — pasta pessoal do usuário Márcio

`  `(gitconfig: "Marciopachecolab"). NÃO portável.

\- O repositório que estamos auditando está em c:\Integragal - Backup -

`  `20260128\_151811\ (raiz C:), não em Downloads. Logo, scripts apontam

`  `para CÓPIA ANTIGA do projeto, não para o atual.

Problema:

Os scripts NÃO operam sobre o repositório atual. Apontam para uma cópia

em Downloads que pode nem existir, ou se existir, está desatualizada.

Executar qualquer script destes:

(a) FileNotFoundError se Downloads/ não tem mais a cópia;

(b) Se Downloads ainda tem cópia, edita arquivo desatualizado sem efeito

`    `no repo atual;

(c) Em outro desenvolvedor, FileNotFoundError sempre.

Impacto:

\- Scripts são tecnicamente inúteis no estado atual.

\- Confirma que são lixo histórico de um momento específico (out-of-date).

\- Confusão para novo dev que tente "rodar para entender".

Recomendação:

Mesma DHP de A1. Se Opção A/C, marcar arquivos como

DEPRECATED\_PATH\_ABSOLUTO em comentário superior.

NÃO IMPLEMENTAR SEM DECISÃO HUMANA.

Teste sugerido:

N/A (DHP resolve isto).

[MÉDIO] A3 — Scripts destrutivos sem dry-run, sem backup, sem idempotência completa

Evidência:

\- scratch/fix\_config.py:37-38, 55-56 — open(file\_path, 'w') sem backup.

\- scratch/fix\_main\_window.py:103-104 — open('ui/main\_window.py', 'w')

`  `sem backup; substitui bloco entre marcadores manualmente identificados.

\- scratch/refactor.py:97-98 — open(file\_path, 'w') sem backup.

\- Nenhum dos 3 scripts: salva backup .bak antes; aceita --dry-run;

`  `imprime diff; pede confirmação; sai com código de erro distinguível

`  `em caso de no-op.

Problema:

Padrão "edit-in-place sem proteção" é exatamente o que CLAUDE.md §9

proíbe sem rodada autorizada. Os scripts são ferramentas internas

históricas, mas estão em árvore versionada com permissão de execução.

Impacto:

\- Se executado por engano, perde estado do arquivo editado sem trilha

`  `de rollback exceto git.

\- Não conforme com INST-001/002/003 (lock atomic, dry-run, backup) que

`  `é padrão SDD adotado para alterações em config.json.

Recomendação:

Mesma DHP de A1. Em qualquer das opções, deixar arquivos somente-leitura

para CI/contribuidores. Se opção C (manter), exigir adicionar `--dry-run`

default no topo de cada script.

NÃO IMPLEMENTAR SEM DECISÃO HUMANA.

Teste sugerido:

N/A (DHP resolve).

**C. Higiene**

[BAIXO] A4 — \_\_pycache\_\_/search\_upsert.cpython-313.pyc é ÓRFÃO (sem .py correspondente)

Evidência:

\- scratch/\_\_pycache\_\_/search\_upsert.cpython-313.pyc (1,6 KB, 2026-05-30 13:32:56)

\- scratch/search\_upsert.py NÃO existe (Glob da pasta confirmou).

Problema:

Bytecode preservado de um script removido. Sintoma de cleanup incompleto.

Pode confundir ferramentas de análise estática que dependem do .pyc.

Impacto:

Cosmético. .pyc não é importável diretamente sem o .py.

Recomendação:

Tratar junto à DHP A1:

\- Opção A (mover): mover .pyc junto com .py para docs/obsoletos/scratch/.

\- Opção B (remover): apagar .pyc junto.

\- Opção C (manter): garantir scratch/\_\_pycache\_\_/ está em .gitignore (e

`  `remover .pyc rastreado).

Inspeção secundária recomendada: verificar git log para entender quando

search\_upsert.py existiu — pode ter sido removido por outro PR sem rebuild

de cache.

Teste sugerido:

N/A.

[BAIXO] A5 — search\_runtime\_profile.py é tão trivial que não merece existir como script

Evidência:

\- scratch/search\_runtime\_profile.py:1-12 — 12 linhas que abrem

`  `ui/janela\_analise\_completa.py e imprimem linhas com "\_runtime\_profile".

Problema:

Operação equivalente a `grep "\_runtime\_profile" ui/janela\_analise\_completa.py`

ou `Grep` no Claude Code. Não justifica arquivo Python versionado.

Impacto:

Baixo. Apenas ruído.

Recomendação:

Tratar junto à DHP A1.

Teste sugerido:

N/A.

[BAIXO] A6 — Naming enganoso de fix\_config.py (não toca config.json)

Evidência:

\- scratch/fix\_config.py edita ui/modules/tela\_configuracoes.py

`  `(TELA de configurações, NÃO o arquivo config.json).

\- Risco: dev procurando "fix\_config.py" pensa que altera DEC-001/CA-12

`  `(config.json template/local runtime).

Problema:

Naming sugere algo diferente do que faz. Reforça a impressão de

desordem da pasta.

Impacto:

Cosmético, mas pode acionar reflexos errados em quem auditar.

Recomendação:

Tratar junto à DHP A1. Em opção C: renomear para fix\_tela\_configuracoes.py.

Teste sugerido:

N/A.

-----
**Consolidação dos subagentes simulados**

|**Subagente**|**Veredicto**|
| :- | :- |
|**Arquiteto SDD**|Pasta totalmente FORA da governança — nem em CLAUDE.md §4, nem em higienizacao, nem em obsoletos. Primeira pasta auditada com este vácuo.|
|**Bug Hunter**|Scripts são bombas de drift se executados: paths absolutos out-of-date + sem backup + sem dry-run. Hoje zero callers = zero risco runtime, mas risco LATENTE alto.|
|**Código Morto / Redundância**|Pasta INTEIRA é candidata a arquivamento. .pyc órfão é prova de cleanup parcial anterior.|
|**Especialista em Testes**|Zero. Recomenda apenas guardião de import-ban (A1).|
|**Revisor de Enxutez**|Scripts compactos individualmente, mas pasta inteira não deveria existir em árvore versionada.|

**Próximas decisões humanas relevantes**

1. **DHP nova A1** — destino de scratch/ (mover / remover / manter como sandbox documentado).
1. **DHP coordenada de housekeeping** sugerida para tratar conjuntamente: analise/, extracao/, interface/ e scratch/ — quatro pastas paralelas que merecem rodada única de decisão.

**Resumo de ações priorizadas**

1. **[ALTO] A1+A2+A3** — DHP nova para scratch/, coordenada com as DHPs já sugeridas.
1. **[BAIXO] A4** — limpar .pyc órfão junto à DHP.
1. **[BAIXO] A5/A6** — endereçados junto à DHP.

Nenhuma alteração foi realizada nesta rodada. Os scripts NÃO foram executados — apenas LIDOS.



**Auditoria SDD READ-ONLY — scripts/**

**1. Escopo analisado**

**Pasta alvo:** C:\Integragal - Backup - 20260128\_151811\scripts\

**Arquivos analisados (37 arquivos, ~190 KB):**

|**Categoria**|**Quantidade**|**Total**|
| :- | :- | :- |
|Python — modificadores|6|~50 KB|
|Python — check/report/telemetria|15|~52 KB|
|Python — operacionais (migração/sanitize/governance)|5|~35 KB|
|PowerShell — destrutivos/operacionais|9|~63 KB|
|CMD wrapper|1|577 B|
|Shim Python|1|181 B|

**Notáveis (tamanho):**

- build\_release\_whitelist.ps1 — 32 KB (REL-004; o maior)
- gerar\_exemplo\_mapa\_placa.py — 11,3 KB (demo PDF)
- update\_inventory.py — 10,4 KB
- generate\_phase0\_baseline.py — 10,1 KB
- refactor\_dashboard\_tabs.py — 10 KB (modifica ui/modules/dashboard.py)

**Não abertos:** \_\_pycache\_\_/\*.pyc. Nenhum credencial lido literalmente.

**Fontes SDD lidas:**

- CLAUDE.md §4 (estrutura — **scripts/ ausente**), §9 (políticas de segurança), §16 (REL-004 concluído)
- AGENTS.md §16 (mesma menção REL-004)
- docs/specs/higienizacao\_implantacao.md §6 (HIG-008 manifest + REL-004)
- docs/specs/tasks.md (HIG-003, REL-004, T-AUD-012, T-AUD-009/DEC-007, telemetria runtime)
- notas\_de\_passagem.md §54, §83-84, §852, §1086, §1252 (scripts limpeza classificados como destrutivos)
-----
**2. Mapa da pasta**

scripts/                                  (NÃO consta em CLAUDE.md §4)

│

├── ── Python OPERACIONAIS (modificam arquivos do projeto ou externos) ──

│   ├─ baseline\_refresh\_governance.py       (governança refresh baseline; ledger JSON)

│   ├─ consolidate\_history.py               (legacy: PostgreSQL + CSV — usa db.db\_utils)

│   ├─ generate\_phase0\_baseline.py          (gera snapshots/phase0\_runtime\_baseline.json)

│   ├─ migrate\_historical\_csv.py            (CSV → novo formato com UUID; backup obrigatório)

│   ├─ sanitize\_historico\_mojibake.py       (3 modos: dry-run | apply | restore)

│   ├─ refactor\_dashboard\_tabs.py           (regex over ui/modules/dashboard.py — SEM BACKUP)

│   ├─ normalize\_legacy\_csv\_utf8.py         (--apply / dry-run com backup)

│   ├─ merge\_config.py                      (mescla config.json + configuracao/config.json)

│   ├─ run\_legacy\_credentials\_migration.py  (CLI delegando AuthService)

│   └─ update\_inventory.py                  (gera 4 docs/INVENTARIO\_\*.md)

│

├── ── Python CHECK/REPORT/TELEMETRIA (read-only, saída JSON em snapshots/) ──

│   ├─ check\_bom.py                         (BOM scan; PATH ABSOLUTO HARDCODED)

│   ├─ check\_exam\_runs\_parity.py            (paridade SQL × CSV)

│   ├─ check\_history\_exam\_runs\_reconciliation.py

│   ├─ check\_query\_latency\_budget.py        (P95/P99)

│   ├─ generate\_daily\_parity\_snapshot.py    (CI daily)

│   ├─ manage\_daily\_parity\_task.py          (Windows Scheduler integration — schtasks)

│   ├─ query\_latency\_report.py

│   ├─ report\_exportar\_resultados\_usage.py  (telemetria do órfão exportar\_resultados\_gal)

│   ├─ report\_phase\_p3\_runtime\_usage.py     (AR-03/AR-04 telemetria)

│   ├─ report\_plate\_sync\_latency.py

│   ├─ scan\_csv\_encoding\_conformance.py     (CI gate de encoding)

│   ├─ verificar\_t15.py                     (STRANGLER\_EXTRACTION\_LEGACY)

│   ├─ verificar\_t24.py                     (STRANGLER\_CT\_DIVERGENCE)

│   ├─ gerar\_exemplo\_mapa\_placa.py          (demo PDF — único modificador desta categoria)

│   └─ legacy\_panel\_governance.py           (181 B — SHIM delegando services.legacy\_panel\_governance.main)

│

└── ── Shell (.ps1 / .cmd) ──

`    `├─ build\_release\_whitelist.ps1          (32 KB — REL-004; dry-run default; -Execute exige rodada autorizada)

`    `├─ limpeza\_logs\_reports.ps1             (HIG-003 — BLOQUEADO; PATH ABSOLUTO HARDCODED)

`    `├─ limpeza\_prioridade\_alta.ps1          (HIG-003 — BLOQUEADO; PATH ABSOLUTO HARDCODED)

`    `├─ organizar\_documentacao.ps1           (Move-Item 65+ arquivos; PATH ABSOLUTO HARDCODED)

`    `├─ create\_backup.ps1                    (robocopy /E /XD .venv \_\_pycache\_\_ .git reports)

`    `├─ normalize\_encoding.ps1               (modifica todos .py — ALTO risco; dry-run disponível)

`    `├─ check\_encoding.ps1                   (read-only — CSV report)

`    `├─ find\_special\_chars.ps1               (read-only — CSV report)

`    `├─ run\_all\_tests.ps1                    (3 testes hardcoded)

`    `├─ run\_baseline\_tests.ps1               (425 B — pytest -q wrapper)

`    `├─ run\_phase0\_gates.ps1                 (orquestra phase0 gates + 15 testes)

`    `└─ run\_daily\_parity\_snapshot.cmd        (577 B — wrapper batch com PATH HARDCODED)

**Responsabilidades percebidas.**

- **Telemetria & gates SDD:** Fase 0 baseline, daily parity snapshot, query latency budget, encoding conformance, runtime usage de funções suspeitas órfãs (exportar\_resultados\_gal, analysis\_engine.processar\_exame).
- **Migração & sanitização operacional:** mojibake (3 modos), CSV legacy → UTF-8 (apply/dry-run), CSV histórico → UUID + GAL tracking, credenciais legacy → usuarios.csv.
- **Release management:** build\_release\_whitelist.ps1 (REL-004 com HIG-008).
- **Housekeeping bloqueado:** limpeza\_logs\_reports.ps1 e limpeza\_prioridade\_alta.ps1 (HIG-003 — não executar sem DHP).
- **Verificadores STRANGLER:** verificar\_t15.py (extraction routing), verificar\_t24.py (CT shadow read divergence).
- **Refactor scripts:** refactor\_dashboard\_tabs.py (edição de UI — SEM BACKUP).

**Fluxos relevantes.**

1. **Phase 0 gates (CI-like):** run\_phase0\_gates.ps1 → generate\_phase0\_baseline.py --check → baseline\_refresh\_governance.py check → scan\_csv\_encoding\_conformance.py → pytest (15 testes smoke).
1. **Daily parity (Windows scheduler):** manage\_daily\_parity\_task.py register --start 03:00 → cria .cmd wrapper → schtasks.exe → executa generate\_daily\_parity\_snapshot.py diariamente → JSON em snapshots/parity\_daily\_<slug>\_<YYYYMMDD>.json.
1. **Telemetria de órfãos:** runtime → sistema.log (RuntimeUsage events) → report\_exportar\_resultados\_usage.py consolida em JSON → confirma se função é órfã para concluir deprecação (DHP B1 sugerida na auditoria de exportacao/).
1. **Release:** build\_release\_whitelist.ps1 SEM -Execute (default) = dry-run simulado; COM -Execute = cria release/app/ via robocopy filtrado pelo manifest HIG-008.

**Dependências internas.** Vários scripts importam services.\*, application.\*, domain.\*, exportacao.\*, autenticacao.\*. Lista típica:

- consolidate\_history.py → db.db\_utils
- generate\_phase0\_baseline.py → exportacao.gal\_formatter, services.analysis, services.equipment, services.reports.history\_report, services.core.runtime\_flags
- report\_phase\_p3\_runtime\_usage.py → services.core.config\_service
- run\_legacy\_credentials\_migration.py → autenticacao.auth\_service

**Dependências externas.** stdlib (argparse, json, hashlib, pathlib, datetime), pandas, reportlab (em gerar\_exemplo\_mapa\_placa.py).

**Consumidores externos.** Nenhum import from scripts. no código de produção (esperado: scripts são entrypoints, não bibliotecas). Callers identificados: run\_phase0\_gates.ps1 chama 3 scripts Python; run\_daily\_parity\_snapshot.cmd chama 1.

-----
**3. Diagnóstico executivo**

**Coerência com SDD.** **Mista alta.**

- **Lado positivo:** scripts canônicos (build\_release\_whitelist REL-004, limpeza HIG-003, telemetria runtime, verificadores STRANGLER) estão documentados, com governança humana (dry-run default em scripts destrutivos), classificações claras em tasks.md/higienizacao\_implantacao.md.
- **Lado negativo:** pasta inteira NÃO consta em CLAUDE.md §4 (estrutura principal). Múltiplos scripts (5+) têm PATH ABSOLUTO HARDCODED para C:\Users\marci\Downloads\Integragal - Copia (3) — diretório diferente do atual (C:\Integragal - Backup - 20260128\_151811). Aponta para CÓPIA ANTIGA do projeto, mesmo defeito visto em scratch/.

**Enxutez.** **Adequada.** Maioria dos scripts é proporcional ao trabalho. Exceções:

- build\_release\_whitelist.ps1 (718 linhas) é grande mas justificável (whitelist complexa, validações, robocopy filtrado).
- gerar\_exemplo\_mapa\_placa.py (367 linhas) tem 3 funções >50 linhas (\_draw\_block 75L, renderizar\_pdf 109L, \_gerar\_blocos\_zdc 80L) — esperado para gerador PDF de demo.

**Redundância.** **Baixa.** Cada script tem propósito distinto. Pequena sobreposição entre check\_bom.py (Python) e find\_special\_chars.ps1/check\_encoding.ps1 (PowerShell) — apenas em encoding scanning, mas com saídas diferentes.

**Bugs prováveis & fragilidades.**

1. **PATHS HARDCODED para cópia antiga** em: check\_bom.py:main(), limpeza\_logs\_reports.ps1, limpeza\_prioridade\_alta.ps1, organizar\_documentacao.ps1, run\_daily\_parity\_snapshot.cmd. Confirmação direta: o repositório atual está em C:\Integragal - Backup - 20260128\_151811\, scripts apontam para C:\Users\marci\Downloads\Integragal - Copia (3)\. Scripts inoperantes em qualquer outra máquina/cópia.
1. **refactor\_dashboard\_tabs.py SEM BACKUP** (208 linhas) — edita ui/modules/dashboard.py via regex direto, sem backup, sem dry-run, sem validação pós-escrita. Igual ao padrão visto em scratch/.
1. **merge\_config.py modifica config.json** — CLAUDE.md §9 explicitamente proíbe sem rodada autorizada. Há backup automático (timestamped), mas o script existe e pode ser invocado por engano.
1. **run\_all\_tests.ps1** tem path hardcoded de venv que não funciona em outro ambiente.
1. **consolidate\_history.py:10** comentário documenta "Fonte de verdade: PostgreSQL (db.db\_utils.salvar\_historico\_processamento)" — contradiz CLAUDE.md §7 ("Postgres dedicado nao deve ser usado") + comentário enganoso (vide auditoria db/ achado C3).

**Risco arquitetural.** **Médio.** Pasta funcional, mas com dois subconjuntos misturados: SDD-governados (saudável) e legados-com-path-hardcoded (frágeis). Sem um README local distinguindo.

**Violação SDD.**

- merge\_config.py: modificador de config.json versionado — viola CLAUDE.md §9 se executado sem rodada.
- refactor\_dashboard\_tabs.py: modificador de UI sem backup — viola §9 ("Nao alterar arquivos fora do escopo da tarefa autorizada").
- Scripts com hardcoded path: tecnicamente inúteis no repo atual, mas presença confunde governança.

**Recomendação geral.** **AJUSTAR via DHP coordenada.** Três frentes:

1. Documentar scripts/ em CLAUDE.md §4 (rodada documental).
1. Endereçar scripts com path hardcoded (rodada de housekeeping com DHP).
1. Adicionar README local em scripts/ classificando cada arquivo: SDD-GOVERNADO / SEGURO / DRY-RUN / DESTRUTIVO-BLOQUEADO.
-----
**4. Notas 0–10**

|**Aspecto**|**Nota**|**Justificativa**|
| :- | :- | :- |
|Aderência SDD|**6**|Scripts críticos (REL-004, HIG-003, telemetria) estão documentados. Mas pasta inteira NÃO consta em §4 e múltiplos scripts têm path hardcoded para cópia antiga.|
|Arquitetura|**7**|Telemetria bem instrumentada (3 reports); gates Phase 0 organizados; scheduler integration correto. Mistura de níveis de maturidade.|
|Clareza e Enxutez|**7**|Maioria proporcional. build\_release\_whitelist.ps1 é grande mas justificado. Refactor scripts grandes (208-275 linhas) são one-shot.|
|Robustez|**6**|Scripts destrutivos têm dry-run default (HIG-003 bloqueia execução). MAS: refactor\_dashboard\_tabs.py sem backup; consolidate\_history.py comentário PostgreSQL enganoso; hardcoded paths.|
|Manutenibilidade|**5**|Scripts de telemetria/governance fáceis de manter. Scripts com path hardcoded e refactor sem backup são dívida. Falta README local.|
|Testabilidade|**5**|Verificadores STRANGLER e check\_\* têm exit codes; alguns têm --fail-on-\* flags. Mas scripts modificadores não têm testes próprios.|
|Risco Operacional|**6**|Scripts HIG-003 explicitamente bloqueados (BOM). REL-004 com dry-run default. Risco real: dev roda refactor\_dashboard\_tabs.py ou merge\_config.py sem rodada autorizada.|
|Prontidão para Evolução|**6**|Telemetria runtime + daily parity são fundações sólidas. Scripts hardcoded precisam refactor de paths.|
|**Geral**|**6**|Pasta funcional com **dois subconjuntos**: SDD-governado (8/10) e legado-com-paths-hardcoded (3/10). Média ponderada reflete a mistura. Adequada para operação atual; precisa housekeeping antes de produção 10 usuários.|

-----
**5. Achados detalhados**

**A. Governança SDD**

[ALTO] A1 — Pasta scripts/ não consta em CLAUDE.md §4 (estrutura principal)

Evidência:

\- CLAUDE.md §4 lista: domain/, application/, services/, ui/, interface/,

`  `exportacao/, browser/, config/, banco/, docs/specs/, tests/.

`  ``scripts/` NÃO consta.

\- Mas scripts/ é amplamente referenciada em SDD:

`  `- REL-004 cita scripts/build\_release\_whitelist.ps1 (AGENTS.md:208,

`    `CLAUDE.md §16)

`  `- HIG-003 cita scripts/limpeza\_\*.ps1 (tasks.md, notas\_de\_passagem §852)

`  `- Telemetria runtime cita scripts/report\_\*.py (várias menções)

Problema:

Pasta funcionalmente crítica (release, telemetria, gates, governance)

ausente do mapa canônico. Inconsistência entre uso real e documentação

de estrutura.

Impacto:

\- Novos contribuidores não sabem se devem adicionar a `scripts/` ou a

`  `outro lugar.

\- Audit toolings podem subestimar superfície de mudança.

Recomendação:

ABRIR RODADA DOCUMENTAL para atualizar CLAUDE.md §4 + AGENTS.md §4

adicionando: "scripts/ - utilitários operacionais, gates de fase,

telemetria, release tooling, governance scripts. Mistura Python + .ps1

\+ .cmd." NÃO requer DHP (apenas documentação).

Teste sugerido:

N/A.

[ALTO] A2 — Múltiplos scripts têm PATH ABSOLUTO HARDCODED para cópia antiga

Evidência:

\- scripts/check\_bom.py:main() — aponta para

`  ``c:/Users/marci/Downloads/Integragal - Copia (3)`

\- scripts/limpeza\_logs\_reports.ps1 — hardcoded path para Downloads

\- scripts/limpeza\_prioridade\_alta.ps1 — hardcoded path para Downloads

\- scripts/organizar\_documentacao.ps1 — hardcoded path para Downloads

\- scripts/run\_daily\_parity\_snapshot.cmd — hardcoded path para Downloads

\- scripts/run\_all\_tests.ps1 — venv hardcoded

\- Repositório atual está em c:\Integragal - Backup - 20260128\_151811\,

`  `NÃO em Downloads. Logo, scripts apontam para CÓPIA ANTIGA.

Problema:

Idêntico ao problema visto em `scratch/` (auditoria anterior). Scripts

tecnicamente inúteis no estado atual; em qualquer outro dev ou ambiente,

falham com FileNotFoundError.

Impacto:

\- Scripts não funcionam onde estão.

\- Diferente de `scratch/`, esses são scripts referenciados em SDD

`  `(REL-004, HIG-003) e em fluxos operacionais (daily parity).

\- Risco de "ilusão de funcionalidade" — documentação afirma que existem,

`  `mas execução real falha.

Recomendação:

RODADA DE HOUSEKEEPING (pode coincidir com DHP de scratch/):

(A) Substituir paths absolutos por resolução relativa via

`    ``BASE\_DIR = Path(\_\_file\_\_).resolve().parent.parent` (Python) ou

`    ``$PSScriptRoot/..` (PowerShell).

(B) Para .cmd: usar `%~dp0..` para resolver raiz do script.

(C) Em scripts HIG-003 bloqueados (limpeza\_\*), correção é desejável

`    `mas não urgente (script não deve ser executado).

NÃO IMPLEMENTAR SEM DHP NOVA "destino de paths hardcoded em scripts/".

Política CLAUDE.md §9 sugere preservação física; refactor de paths é

mudança não-trivial.

Teste sugerido:

tests/test\_scripts\_no\_hardcoded\_paths.py — guardião AST/regex que falhe

se algum .py/.ps1/.cmd em scripts/ contiver string literal

"Downloads\\Integragal" ou "Downloads/Integragal".

**B. Modificadores de arquivo crítico sem proteção**

[ALTO] B1 — refactor\_dashboard\_tabs.py edita ui/modules/dashboard.py SEM BACKUP

Evidência:

\- scripts/refactor\_dashboard\_tabs.py (208 linhas)

\- Modifica `ui/modules/dashboard.py` via regex/string replacements.

\- Sem backup pré-execução.

\- Sem dry-run.

\- Sem validação pós-escrita (apenas `print` final).

\- Sem detecção de idempotência (se já aplicado, pode duplicar ou quebrar).

Problema:

Script one-shot de refactor que modifica arquivo canônico de UI sem

salvaguardas. Igual ao padrão visto em `scratch/` (mesma família de

problema).

Impacto:

\- Execução acidental sobrescreve dashboard.py atual (DASH-001..008 já

`  `concluídos) sem rollback.

\- Pode reverter alterações de outras rodadas SDD.

Recomendação:

Tratar junto à DHP "destino de scratch/" (auditoria anterior). Opções:

(A) marcar como DEPRECATED + adicionar `--dry-run` default;

(B) mover para docs/obsoletos/scripts\_legacy/;

(C) remover (rodada própria após confirmar zero callers em CI).

NÃO IMPLEMENTAR SEM DECISÃO HUMANA.

Teste sugerido:

Coberto pelo guardião sugerido em A2 (se path hardcoded) + verificar se

script tem comentário "ONE-SHOT REFACTOR - DO NOT RUN AGAIN".

[MÉDIO] B2 — merge\_config.py modifica config.json (CLAUDE.md §9)

Evidência:

\- scripts/merge\_config.py:1-132 — mescla config.json + configuracao/config.json

\- Cria backup em config/backups/config\_pre\_merge\_\*.json (positivo)

\- Sobrescreve config.json (item proibido por CLAUDE.md §9 sem rodada)

\- Sem `--dry-run` flag.

Problema:

CLAUDE.md §9 explicitamente: "Nao alterar `config.json` sem rodada

especifica autorizada." Script existe e pode ser invocado por engano.

Impacto:

\- Backup automático mitiga perda total.

\- Mas execução não-autorizada viola governança documentada.

Recomendação:

Adicionar header no script citando CLAUDE.md §9 e exigindo

confirmação interativa antes de prosseguir. Em DHP futura: avaliar se o

script ainda é necessário (legado de migração de configuracao/ para

config/).

Teste sugerido:

tests/test\_merge\_config\_requires\_confirmation.py — assert que

execução sem `--confirm` ou `--force` aborta antes de gravar.

**C. Scripts SDD-governados (informativo positivo)**

[INFORMATIVO] C1 — REL-004 (build\_release\_whitelist.ps1) com governança modelar

Evidência:

\- scripts/build\_release\_whitelist.ps1:1-718 (32 KB)

\- AGENTS.md:208 e CLAUDE.md §16: REL-004 concluída (2026-05-17):

`  `"script criado, modo simulacao por padrao (sem `-Execute`),

`   `validacoes seguranca e validacao pos-copia. O script NAO foi

`   `executado; release/ NAO foi criada."

\- docs/specs/higienizacao\_implantacao.md §6: whitelist HIG-008

`  `governa permissões.

\- Set-StrictMode -Version Latest, $ErrorActionPreference = "Stop",

`  `try/catch em helpers.

Problema:

Nenhum. Observação positiva.

Impacto:

Modelo de "script destrutivo bem governado": dry-run default, exige

flag explícita para execução real, documentado em SDD, validação

pós-copia.

Recomendação:

Manter. Citar como referência em rodada documental de §4.

Teste sugerido:

N/A.

[INFORMATIVO] C2 — HIG-003 bloqueia limpeza\_\*.ps1 corretamente

Evidência:

\- scripts/limpeza\_logs\_reports.ps1 (206 linhas) — Remove-Item em logs/reports

\- scripts/limpeza\_prioridade\_alta.ps1 (275 linhas) — Remove-Item +

.ruff\_cache -Recurse

\- tasks.md HIG-003 (T-AUD-012 concluída): "Scripts limpeza em scripts/

`  `classificados como potencialmente destrutivos; nao executar sem

`  `auditoria propria, baseline/backup e autorizacao explicita."

\- Ambos scripts: -DryRun default; `-Force` requer confirmação interativa.

Problema:

Nenhum (HIG-003 documenta o bloqueio). Path hardcoded é problema

separado (A2).

Impacto:

Governança correta.

Recomendação:

Manter bloqueio. Adicionar header explícito citando HIG-003 + DHP

necessária para execução. Resolver path hardcoded apenas em rodada

de housekeeping.

Teste sugerido:

N/A.

[INFORMATIVO] C3 — Telemetria runtime cobre 3 análises de uso suspeito

Evidência:

\- scripts/report\_exportar\_resultados\_usage.py — telemetria de

`  `exportar\_resultados\_gal (auditoria de exportacao/ identificou função

`  `como suspeita de órfão)

\- scripts/report\_phase\_p3\_runtime\_usage.py — AR-03/AR-04 telemetria

`  `(analysis\_engine.processar\_exame + suspected\_orphan)

\- scripts/report\_plate\_sync\_latency.py — latência plate.sync.merge

\- Todos lêem logs/sistema.log e geram JSON em snapshots/.

Problema:

Nenhum. Observação positiva.

Impacto:

Infraestrutura de telemetria pavimenta o caminho para DHPs de

deprecação (ex: B1/B2 da auditoria de exportacao/).

Recomendação:

Manter. Considerar agregar em report\_runtime\_usage\_summary.py futuro

que cubra todas as funções marcadas com log\_suspected\_orphan\_usage.

Teste sugerido:

N/A.

**D. Outros**

[BAIXO] D1 — verificar\_t15.py / verificar\_t24.py têm nomes ambíguos

Evidência:

\- scripts/verificar\_t15.py — verifica STRANGLER\_EXTRACTION\_LEGACY no

`  `journal (extraction routing).

\- scripts/verificar\_t24.py — verifica STRANGLER\_CT\_DIVERGENCE (CT

`  `shadow read).

\- Não correspondem às tarefas T15/T24 de tasks.md (que tratam de outros

`  `temas).

\- "T15" e "T24" parecem ser numerações internas de fase, não SDD.

Problema:

Naming ambíguo. Sugere mapeamento direto com tasks.md (T15, T24) que

não existe.

Impacto:

Confusão para auditor novo. Sem impacto runtime.

Recomendação:

Renomear para `verificar\_strangler\_extraction.py` e

`verificar\_strangler\_ct.py` em rodada de housekeeping. NÃO requer DHP.

Teste sugerido:

N/A.

[BAIXO] D2 — legacy\_panel\_governance.py (181 B) é shim puro

Evidência:

\- scripts/legacy\_panel\_governance.py:1-7

`    `"""CLI para governanca do legado painel\_\* (rollout e monitoramento)."""

`    `from services.legacy\_panel\_governance import main

`    `if \_\_name\_\_ == "\_\_main\_\_":

`        `raise SystemExit(main())

Problema:

Nenhum. Padrão correto de shim CLI delegando para serviço.

Impacto:

Positivo.

Recomendação:

Manter. Modelo a replicar em outros CLI wrappers.

Teste sugerido:

N/A.

[BAIXO] D3 — consolidate\_history.py contém comentário PostgreSQL enganoso

Evidência:

\- scripts/consolidate\_history.py:10 comentário:

`    `"Fonte de verdade: PostgreSQL (db.db\_utils.salvar\_historico\_processamento)"

\- Realidade: PostgreSQL é stub que retorna None (vide auditoria db/).

\- Verdade efetiva: CSV.

Problema:

Comentário documenta arquitetura desejada que NÃO é a real. Reforça

risco identificado na auditoria de db/ (achado B2 — PostgreSQL morto

violando §7).

Impacto:

Confusão arquitetural.

Recomendação:

Junto à DHP B1 da auditoria de db/ (destino de db\_utils), atualizar

comentário aqui.

Teste sugerido:

N/A.

[INFORMATIVO] D4 — Ausência de CI/CD detectado

Evidência:

\- Subagente C: "Nenhum arquivo Makefile, GitHub Actions, GitLab CI

`  `encontrado neste repo."

\- scripts/run\_phase0\_gates.ps1 e scripts/run\_daily\_parity\_snapshot.cmd

`  `são wrappers manuais/scheduler.

Problema:

Pipeline CI/CD seria natural complementar à infraestrutura de

telemetria já implementada. Hoje, gates dependem de execução manual ou

Windows Scheduler.

Impacto:

Não-crítico para piloto. Relevante para produção 10 usuários

(CONC-001/002).

Recomendação:

Considerar GitHub Actions / Azure DevOps em rodada futura. Os scripts

existentes (run\_phase0\_gates, manage\_daily\_parity\_task) podem ser

diretamente reaproveitados como steps de pipeline.

Teste sugerido:

N/A.

-----
**Consolidação dos subagentes simulados**

|**Subagente**|**Veredicto**|
| :- | :- |
|**Arquiteto SDD**|Pasta funcional mas ausente do §4. REL-004, HIG-003, telemetria runtime são modelares. Path hardcoded confunde governança.|
|**Bug Hunter**|A2 (paths hardcoded em 5+ scripts) é o mais sério; B1 (refactor sem backup) e B2 (merge\_config sem confirmação) são riscos latentes.|
|**Código Morto / Redundância**|Pequena sobreposição encoding scans. refactor\_dashboard\_tabs.py é one-shot esquecido (similar a scratch/).|
|**Especialista em Testes**|Verificadores STRANGLER + check\_\* têm exit codes adequados. Falta guardião de paths hardcoded e de import-ban de db.db\_utils.|
|**Revisor de Enxutez**|Maioria proporcional. build\_release\_whitelist.ps1 (718 linhas) é justificadamente grande.|

**Próximas decisões humanas relevantes**

1. **Rodada documental** — atualizar CLAUDE.md §4 / AGENTS.md §4 para incluir scripts/.
1. **DHP nova A2** — destino dos paths hardcoded em 5+ scripts (coordenar com DHP de scratch/ que tem mesmo problema).
1. **DHP B1** — destino de refactor\_dashboard\_tabs.py (coordenar com scratch/).
1. **B2** — endurecer merge\_config.py (rodada pequena com confirmação interativa).
1. **D3** — atualizar comentário em consolidate\_history.py junto à DHP B1 da auditoria de db/.

**Resumo de ações priorizadas**

1. **[ALTO] A1** — rodada documental para incluir scripts/ em §4 (não precisa de DHP).
1. **[ALTO] A2** — DHP coordenada com scratch/ para paths hardcoded.
1. **[ALTO] B1** — DHP para refactor\_dashboard\_tabs.py (coordenar com scratch/).
1. **[MÉDIO] B2** — endurecer merge\_config.py.
1. **[BAIXO] D1/D3** — renomear verificar\_t15/t24 + atualizar comentário em consolidate\_history.

Nenhuma alteração foi realizada nesta rodada. Scripts NÃO foram executados.

\




**Auditoria SDD READ-ONLY — services/**

**1. Escopo analisado**

**Pasta alvo:** C:\Integragal - Backup - 20260128\_151811\services\

**Inventário macro (92 arquivos, ~1 038 KB):**

|**Camada**|**Arquivos**|**Tamanho**|**Status SDD**|
| :- | :- | :- | :- |
|Top-level|30|~225 KB|Misto: canônicos + cluster operacional + utilidades|
|analysis/|14|308 KB|**MAIOR cluster** — fluxo de análise crítico|
|legacy\_audit/|8|115 KB|Phase-out (governança SLO + menu catalog)|
|persistence/|12|110 KB|Adapters CSV/SQLite + atomic IO|
|core/|9|92 KB|config\_service + runtime\_flags + DI container|
|reports/|8|79 KB|DASH-001..008 + R06 + history\_report|
|equipment/|4|71 KB|DEC-006 (detector + extractors + registry)|
|gal/|4|40 KB|GAL-ROB-007/008/010 (transactions + reconciler)|
|engine/|3|27 KB|analysis\_engine + data\_cleaner + config\_loader|

**Não abertos integralmente (motivo):** Devido à escala (~1 MB), inventário leu DOCSTRINGS + lista de SÍMBOLOS PÚBLICOS de cada arquivo. Análise integral de cada um exigiria ~30+ rodadas — fora do escopo single-pass conforme T-AUD-010 da SDD.

**Fontes SDD lidas:**

- CLAUDE.md §4/§13/§16 (DT-002, T-AUD-010 pendente)
- AGENTS.md §13/§16
- docs/specs/design.md (§3.5/§3.6/§3.7/§3.8/§3.10, DT-002 linha 349, INST-001 linha 415, LIM-004 linha 356, GAL-ROB-007 linha 79)
- **docs/specs/inventario\_services.md** — **T-AUD-010 PARCIALMENTE ATENDIDA** (inventário documental existe, split físico não executado)
- docs/specs/tasks.md (DASH-001..008, GAL-ROB-001..010, R01-R10, DEC-006, INST-001..003, LOG-UNIF-001/002, CONC-001..006, LIM-004)
- notas\_de\_passagem.md
-----
**2. Mapa da pasta**

services/                                       (~1 MB, 92 arquivos)

│

├── ── TOP-LEVEL — 30 arquivos ──

│   ├─ Catálogos canônicos

│   │   ├─ contract\_catalog.py        (679L — RuntimeContractBundle, ContractCatalog)

│   │   ├─ exam\_registry.py           (491L — ExamConfig, get\_exam\_cfg; itera config/exams/)

│   │   ├─ exam\_catalog\_availability.py (192L)

│   │   ├─ exam\_domain\_contracts.py   (~50L — uses\_default\_viral\_rule)

│   │   └─ contract\_preflight.py      (~150L — validações pré-flight)

│   │

│   ├─ Cluster operational\_\* (10 arquivos relacionados ao visualizador F9)

│   │   ├─ operational\_handover.py             (265L — handover F12)

│   │   ├─ operational\_viewer\_health.py        (313L — alerts F9)

│   │   ├─ operational\_viewer\_rollout.py       (142L — stage 10/25/50/100%)

│   │   ├─ operational\_viewer\_profiles.py      (132L)

│   │   ├─ operational\_viewer\_analytics.py

│   │   ├─ operational\_viewer\_quick\_filters.py

│   │   ├─ operational\_export\_audit.py

│   │   ├─ exam\_runs\_parity.py                 (244L)

│   │   ├─ history\_exam\_runs\_reconciliation.py (271L)

│   │   └─ legacy\_panel\_governance.py          (237L — F2.2 cutover)

│   │

│   ├─ Operacionais

│   │   ├─ installation\_checks.py     (364L — INST-001..003 bootstrap\_banco\_runtime)

│   │   ├─ formula\_parser.py          (589L — Fase 2.1 expressões matemáticas/lógicas)

│   │   ├─ menu\_catalog\_cutover\_ports.py

│   │   └─ menu\_compat\_shutdown\_policy.py

│   │

│   └─ Utilidades / Constantes

│       ├─ path\_resolver.py           (LOG-UNIF-002 — resolve\_banco\_dir)

│       ├─ system\_paths.py            (BASE\_DIR)

│       ├─ shared\_io.py / shared\_paths.py / shared\_text.py / dedupe\_keys.py / encoding\_policy.py

│       ├─ tk\_file\_chooser.py / suspected\_orphan\_telemetry.py

│       └─ cadastros\_diversos.py

│

├── ── analysis/ — 14 arquivos (MAIOR cluster, 308 KB) ──

│   ├─ analysis\_service.py           (1947L — AnalysisService.analisar\_corrida; FLUXO PRINCIPAL)

│   ├─ full\_run\_status\_sync.py       (1626L — sync status pós-GAL)

│   ├─ analysis\_runtime\_rollout.py   (725L — staged rollout 10/25/50/100%)

│   ├─ analysis\_helpers.py           (695L — Fase 2 helpers extraídos)

│   ├─ rules\_engine.py               (591L — Fase 2.2)

│   ├─ final\_run\_report.py           (544L)

│   ├─ analysis\_legacy\_registry\_parity.py (400L)

│   ├─ exam\_runs\_row\_mapper.py       (253L)

│   ├─ analysis\_runtime\_contract.py  (233L)

│   ├─ analysis\_runtime\_observability.py (180L)

│   ├─ full\_run\_artifact.py          (175L)

│   ├─ full\_run\_contract.py          (142L)

│   ├─ logic\_engine.py               (\*\*12L — STUB\*\*)

│   └─ \_\_init\_\_.py                   (vazio)

│

├── ── engine/ — 3 arquivos ──

│   ├─ analysis\_engine.py            (~450L — AnalysisEngine.processar\_exame; motor universal)

│   ├─ config\_loader.py              (~100L — encoding-hardened legacy ingest)

│   └─ data\_cleaner.py               (~140L — DataCleaner.clean\_dataframe)

│

├── ── equipment/ — 4 arquivos (DEC-006) ──

│   ├─ equipment\_detector.py         (877L — detectar\_equipamento)

│   ├─ equipment\_extractors.py       (566L — 4 extratores)

│   ├─ equipment\_registry.py         (435L — EquipmentConfig CRUD)

│   └─ \_\_init\_\_.py

│

├── ── gal/ — 4 arquivos (GAL-ROB-007/008/010) ──

│   ├─ history\_gal\_sync.py           (608L — sync histórico CSV)

│   ├─ gal\_transactions.py           (441L — build\_idempotency\_key, dual-key)

│   ├─ gal\_status\_reconciler.py      (130L — reconcile\_gal\_status)

│   └─ \_\_init\_\_.py

│

├── ── persistence/ — 12 arquivos ──

│   ├─ persistence\_adapters.py       (1281L — 12+ adapters CSV/SQLite)

│   ├─ persistence\_facade.py         (341L)

│   ├─ sqlite\_repository.py          (314L)

│   ├─ history\_writer\_core.py        (211L)

│   ├─ exam\_runs\_sqlite.py           (199L — ExamRunsSQLiteRepository, DASH-001)

│   ├─ exam\_runs\_csv.py              (165L)

│   ├─ csv\_io.py                     (155L — write\_csv\_atomic ✓)

│   ├─ csv\_contracts.py              (157L)

│   ├─ csv\_lock.py                   (137L — CSVFileLock)

│   ├─ history\_schema.py             (52L)

│   ├─ persistence\_provider.py       (53L — factory)

│   └─ \_\_init\_\_.py

│

├── ── reports/ — 8 arquivos ──

│   ├─ history\_report.py             (986L — HistoryReportService O(N²)→O(N))

│   ├─ dashboard\_analytics.py        (388L — obter\_estatisticas\_gestao ✓ DASH-003)

│   ├─ reports\_repository.py         (231L — ReportsSQLiteRepository, R06)

│   ├─ plate\_report.py               (186L — gerar\_mapa\_placa\_final)

│   ├─ relatorio\_csv.py              (183L)

│   ├─ reports\_exporter.py           (113L)

│   ├─ relatorio\_estatistico.py      (94L)

│   └─ \_\_init\_\_.py

│

├── ── core/ — 9 arquivos ──

│   ├─ config\_service.py             (971L — \_save\_config L669-720 INST-001 ✓)

│   ├─ config\_loader.py              (439L — LEGADO DEPRECADO)

│   ├─ runtime\_flags.py              (312L — todas as flags GAL/ANALYSIS canônicas)

│   ├─ query\_latency.py              (192L — telemetria p50/p95/p99)

│   ├─ event\_bus.py                  (172L — Pub/Sub singleton)

│   ├─ service\_container.py          (133L — DI container)

│   ├─ error\_contracts.py            (36L — ServiceError)

│   └─ \_\_init\_\_.py

│

└── ── legacy\_audit/ — 8 arquivos (PHASE-OUT) ──

`    `├─ operational\_tabular\_viewer.py            (1151L)

`    `├─ operational\_slo\_governance.py            (1060L — F10/F11)

`    `├─ menu\_catalog\_fallback\_audit.py           (344L)

`    `├─ menu\_catalog\_audit\_repository.py         (277L)

`    `├─ menu\_catalog\_cutover\_orchestrator.py     (149L)

`    `├─ menu\_invalid\_timestamp\_fallback\_policy.py (133L)

`    `├─ menu\_catalog\_cutover\_policy.py           (109L)

`    `└─ \_\_init\_\_.py

**Responsabilidades percebidas.** Camada CENTRAL do sistema, agregando:

1. **Pipeline de análise** (analysis/ + engine/ + equipment/) — fluxo CT → resultado.
1. **Persistência** (persistence/) — CSV + SQLite com atomic IO + locks.
1. **Integração GAL** (gal/) — idempotência dual-key + reconciliação.
1. **Relatórios e dashboard** (reports/) — DASH-001..008, R01-R10.
1. **Configuração central** (core/) — config\_service singleton, runtime\_flags, DI container.
1. **Governança operacional** (top-level operational\_\* + legacy\_audit/) — F9-F12 lifecycle.
1. **Contratos e registries** (contract\_catalog, exam\_registry, equipment\_registry).

**Confirmações SDD positivas (verificadas pelos subagentes):**

- ✅ core/config\_service.py:669-720 \_save\_config com O\_CREAT | O\_EXCL lock + tempfile.mkstemp + os.replace (**INST-001**)
- ✅ persistence/csv\_io.py:115 write\_csv\_atomic com temp file + rename
- ✅ gal/gal\_status\_reconciler.py:95 reconcile\_gal\_status (**GAL-ROB-010**)
- ✅ gal/gal\_transactions.py build\_idempotency\_key + normalize\_idempotency\_value (**GAL-ROB-007/008**)
- ✅ reports/dashboard\_analytics.py:64 obter\_estatisticas\_gestao (**DASH-003**)
- ✅ reports/history\_report.py (986L) append-only O(N) (**DASH-001**)
- ✅ persistence/exam\_runs\_sqlite.py ExamRunsSQLiteRepository (**DASH-001**)
- ✅ equipment/equipment\_detector.py:839 detectar\_equipamento com fallback legado + perfis ativos (**DEC-006**)
- ✅ core/runtime\_flags.py exporta FLAG\_GAL\_ENVIO\_SEM\_METADADOS, is\_contract\_analysis\_runtime\_enabled, is\_legacy\_gal\_success\_ledger\_enabled, is\_contractual\_csv\_legacy\_fallback\_enabled
- ✅ T-AUD-010 ATENDIDA documentalmente em docs/specs/inventario\_services.md (split em 7 subdomínios já mapeado)

**Consumidores externos (~52 arquivos):**

|**Camada**|**Arquivos**|**Imports típicos**|
| :- | :- | :- |
|ui/|20|config\_service, exam\_registry, history\_report, dashboard\_analytics, reports\_repository|
|scripts/|14|query\_latency, runtime\_flags, exam\_runs\_parity, history\_exam\_runs\_reconciliation|
|application/|6|analysis\_service, equipment\_profile\_service, reports\_repository, gal\_transactions|
|tests/|7|Vários (depende do teste)|
|exportacao/|4|gal\_transactions, exam\_registry, contract\_catalog, config\_service|
|autenticacao/|1|persistence\_adapters, csv\_io|

-----
**3. Diagnóstico executivo**

**Coerência com SDD.** **Alta nos módulos canônicos, mista globalmente.**

- **Positivo:** GAL-ROB-001..010 implementados em services/gal/; DASH-001..008 em services/reports/; DEC-006 em services/equipment/; INST-001..003 em services/core/config\_service.py e services/installation\_checks.py; LOG-UNIF-001/002 em services/path\_resolver.py. Inventário documental T-AUD-010 atendido em docs/specs/inventario\_services.md.
- **Negativo:** DT-002 ("services/ concentra dezenas de modulos") **PERMANECE**: o split FÍSICO em subdomínios não foi executado. Top-level ainda tem 30 arquivos, incluindo cluster de 10 operational\_\*. legacy\_audit/ é phase-out sem deadline.

**Enxutez.** **Insuficiente em vários pontos.** 17 arquivos com >300 linhas; 5 com >900 linhas. O maior é services/analysis/analysis\_service.py (**1 947 linhas**), seguido por full\_run\_status\_sync.py (**1 626**), persistence\_adapters.py (**1 281**), operational\_tabular\_viewer.py (**1 151**), operational\_slo\_governance.py (**1 060**), history\_report.py (**986**), config\_service.py (**971**), equipment\_detector.py (**877**). Cada um é candidato natural a decomposição.

**Redundância.**

- **Cluster operational\_**\* disperso: 10 arquivos top-level + 2 em legacy\_audit/ (operational\_tabular\_viewer, operational\_slo\_governance). Sem subpasta dedicada services/operational/.
- **2 config\_loader**: services/core/config\_loader.py (439L, DEPRECADO) + services/engine/config\_loader.py (~100L, encoding legacy). Naming conflitante.
- **logic\_engine.py** em services/analysis/ tem apenas **12 linhas** — STUB esquecido.

**Bugs prováveis & fragilidades.**

1. services/analysis/logic\_engine.py (12L) — stub que pode falhar silenciosamente se importado.
1. services/core/config\_loader.py (439L) marcado deprecado mas mantido — risco de imports paralelos com config\_service.py.
1. Arquivos gigantes (>1 000L) têm naturalmente funções >100L, dificultando isolamento de regressões.
1. Confirmação cross-cutting: subagente B (3 reports atrás) detectou que db/db\_utils.py mantém bloco PostgreSQL morto que se cruzaria com services/persistence/persistence\_adapters.py em runtime — duplicação latente.

**Risco arquitetural.** **Médio-Alto.** Cluster grande (1 MB / 92 arquivos / 5+ gigantes) é o principal débito técnico documentado (DT-002). Custo de refactor cresce a cada novo módulo. Mas funcionalmente está coerente — nenhum module conflita semanticamente com outro hoje.

**Violação SDD.** Nenhuma materializada. Há **divergências de governança** documentadas:

- DT-002 / T-AUD-010 (split físico pendente).
- LIM-004 (10 usuários simultâneos não comprovado — requer CONC-002/003 que tocam services/persistence/ e services/gal/).
- services/legacy\_audit/menu\_catalog\_\* em phase-out sem deadline.

**Recomendação geral.** **MANTER + AJUSTAR via rodadas T-AUD-010 e CONC-002/003.**

Três frentes priorizadas:

1. **Decompor os 5 arquivos >1 000 linhas** (em rodadas separadas, com testes-guardião antes).
1. **Consolidar cluster operational\_**\* em services/operational/ (rodada documental + mover físico).
1. **Concluir phase-out de services/legacy\_audit/menu\_catalog\_\*** (DHP de deadline).
-----
**4. Notas 0–10**

|**Aspecto**|**Nota**|**Justificativa**|
| :- | :- | :- |
|Aderência SDD|**8**|GAL-ROB-001..010, DASH-001..008, R06, DEC-006, INST-001..003, LOG-UNIF-001/002 todos implementados nesta camada. DT-002 ainda pendente; T-AUD-010 doc ok, físico não.|
|Arquitetura|**6**|Subpastas bem definidas e proporcionais aos domínios. Top-level com 30 arquivos sem subpasta operational/. 2 config\_loader em namespaces diferentes.|
|Clareza e Enxutez|**5**|5 arquivos >1 000 linhas; 17 >300. analysis\_service.py com 1 947 linhas é o caso mais agudo.|
|Robustez|**8**|atomic IO + locks (csv\_io, config\_service), idempotência dual-key (gal\_transactions), fallback ativo (equipment\_detector), telemetria latência (query\_latency).|
|Manutenibilidade|**6**|Camada é base sólida, mas tamanho dos módulos gigantes dificulta evolução. config\_loader deprecado convive com config\_service.|
|Testabilidade|**6**|Padrões testáveis (DI container, Protocols em domain). Mas testes diretos cobrem fração da superfície (T-AUD-013 pendente).|
|Risco Operacional|**7**|Pontos críticos (INST-001, GAL-ROB, atomic IO) corretamente implementados. LIM-004 (10 usuários) ainda pendente.|
|Prontidão para Evolução|**6**|DI container + Protocols + runtime\_flags pavimentam evolução. Mas refactor de 5 arquivos gigantes é pré-requisito para evolução não-traumática.|
|**Geral**|**6,5**|Camada **funcionalmente madura e completa** (cobre TODOS os domínios SDD), mas **estruturalmente pesada** (92 arquivos, 5 gigantes, cluster operational\_\* não consolidado). Adequada para piloto produtivo; T-AUD-010 + CONC-002/003 são pré-requisitos para produção 10 usuários.|

-----
**5. Achados detalhados**

**A. Estrutura & DT-002**

[ALTO] A1 — DT-002 permanece: 92 arquivos / 1 MB / 5 arquivos >1 000 linhas

Evidência:

\- CLAUDE.md §13 / design.md L349: "services/ concentra dezenas de modulos

`  `e arquivos individuais grandes. Tarefa: T-AUD-010."

\- docs/specs/inventario\_services.md: T-AUD-010 documentalmente atendida

`  `(split em 7 subdomínios mapeado).

\- Inventário físico: split não executado nos arquivos top-level.

\- 5 arquivos >1 000L: analysis\_service (1947), full\_run\_status\_sync (1626),

`  `persistence\_adapters (1281), operational\_tabular\_viewer (1151),

`  `operational\_slo\_governance (1060).

Problema:

T-AUD-010 entregou inventário documental, mas execução física do split foi

postergada. Cada arquivo gigante é candidato natural a decomposição.

Impacto:

\- Custo cognitivo alto para revisores.

\- Refactor seguro fica arriscado sem testes-guardião proporcionais.

\- LIM-004 (10 usuários) provavelmente exigirá ajustes nesses arquivos.

Recomendação:

ABRIR DHP "Plano de execução T-AUD-010-FASE-2":

(A) Decompor analysis\_service.py em sub-módulos por responsabilidade

`    `(carga, motor invoke, AppState sync, persistência).

(B) Decompor full\_run\_status\_sync.py em handlers separados.

(C) Consolidar cluster operational\_\* em services/operational/.

Cada item é rodada separada com testes-guardião ANTES.

NÃO IMPLEMENTAR SEM DHP NOVA + suíte de testes prévia.

Teste sugerido:

Pré-requisito: criar tests/test\_analysis\_service\_smoke.py cobrindo

analisar\_corrida happy-path antes de qualquer refactor.

[MÉDIO] A2 — Cluster operational\_\* disperso (10 top-level + 2 em legacy\_audit/)

Evidência:

\- Top-level: operational\_handover, operational\_viewer\_health,

`  `operational\_viewer\_rollout, operational\_viewer\_profiles,

`  `operational\_viewer\_analytics, operational\_viewer\_quick\_filters,

`  `operational\_export\_audit, exam\_runs\_parity,

`  `history\_exam\_runs\_reconciliation, legacy\_panel\_governance.

\- legacy\_audit/: operational\_tabular\_viewer, operational\_slo\_governance.

\- Nenhuma subpasta services/operational/.

Problema:

Cluster funcional sem reflexo estrutural. Naming "operational\_\*"

torna-os visualmente agrupados mas fisicamente espalhados.

Impacto:

\- Manutenção: alterar viewer toca top-level + legacy\_audit/.

\- Inventário T-AUD-010 documenta isso, mas split não executado.

Recomendação:

Junto à DHP de A1, criar services/operational/ e mover 12 arquivos.

NÃO IMPLEMENTAR SEM DHP coordenada.

Teste sugerido:

Após split, atualizar imports em ~20 callers de ui/ e ~14 callers

de scripts/. Guardião AST checa que imports estão atualizados.

[MÉDIO] A3 — 2 config\_loader em namespaces distintos

Evidência:

\- services/core/config\_loader.py (439L) — marcado DEPRECADO segundo

`  `subagente C.

\- services/engine/config\_loader.py (~100L) — encoding-hardened legacy

`  `ingest para protocolos/regras.

Problema:

Naming conflitante. Quem busca "ConfigLoader" pode encontrar o errado.

Auditoria anterior de config/ identificou também `ConfigLoader.BASE\_PATH`

em outro caminho (LOG-UNIF-002).

Impacto:

\- Risco de import errado.

\- Necessidade de renomear ou deprecar um.

Recomendação:

Junto à DHP de A1: renomear services/core/config\_loader.py para

`legacy\_config\_loader.py` e/ou marcar com `\_\_deprecated\_\_` flag.

Confirmar zero callers ativos antes.

Teste sugerido:

Grep `from services.core.config\_loader` → confirmar ZERO callers

(se confirmado, candidato a remoção).

**B. Código morto / stubs**

[ALTO] B1 — services/analysis/logic\_engine.py (12 linhas) é STUB esquecido

Evidência:

\- services/analysis/logic\_engine.py (12 linhas) — subagente A classificou

`  `como "Stub" / "Placeholder".

\- Outros módulos analysis/ têm 142-1947 linhas.

Problema:

Arquivo presente sem implementação real. Pode ser:

(a) Início de refactor abandonado;

(b) Shim para compatibilidade;

(c) Lixo.

Impacto:

\- Confusão para novos contribuidores.

\- Possível ImportError silencioso se algum caller esperar API completa.

Recomendação:

Verificar callers via grep `from services.analysis.logic\_engine`. Se

zero, candidato a remoção. Se algum, expor `\_\_deprecated\_\_` warning.

NÃO IMPLEMENTAR SEM rodada própria (mexe em pasta crítica analysis/).

Teste sugerido:

tests/test\_logic\_engine\_no\_runtime\_callers.py — guardião AST.

[MÉDIO] B2 — services/core/config\_loader.py deprecado mas mantido (439 linhas)

Evidência:

\- Subagente C marcou como "DEPRECADO".

\- Coexiste com config\_service.py (971L) que é o canônico.

Problema:

Camada deprecada com 439 linhas em pasta core/. Igual ao padrão visto em

config/settings.py vs services/core/config\_service (auditoria de config/

identificou B1).

Impacto:

\- Custo de inspeção em cada auditoria.

\- Risco de novo código usar API deprecada.

Recomendação:

Verificar callers reais. Endurecer com `DeprecationWarning` no import.

Plano de remoção após confirmação. NÃO IMPLEMENTAR SEM DHP coordenada

com auditoria anterior de config/.

Teste sugerido:

Grep `from services.core.config\_loader` para listar callers.

**C. Funções gigantes (>1 000 linhas — risco operacional)**

[ALTO] C1 — analysis\_service.py (1 947 linhas) — maior arquivo do projeto

Evidência:

\- services/analysis/analysis\_service.py (1 947 linhas)

\- Classe `AnalysisService` com método `analisar\_corrida` orquestrando

`  `fluxo principal de análise.

Problema:

Arquivo crítico (consumido por application/analysis\_orchestrator,

ui/janela\_analise\_completa, exportacao/envio\_gal indireto) com tamanho

que dificulta refactor, cobertura por passo e revisão.

Impacto:

\- LIM-004 (10 usuários) provavelmente exigirá otimizações neste módulo.

\- DASH-001..008 e GAL-FEAT-001..005 já tocaram este código —

`  `acumulação de mudanças.

Recomendação:

Decomposição planejada conforme A1. Sugestão de split:

\- analysis\_carga.py (carregamento + normalização)

\- analysis\_motor.py (invoke engine + interpret)

\- analysis\_estado.py (sync com AppState)

\- analysis\_relatorio.py (montagem de saída)

Pré-requisito: cobertura >70% do happy-path atual.

NÃO IMPLEMENTAR SEM DHP A1.

Teste sugerido:

tests/test\_analysis\_service\_full\_pipeline.py — VR1e2 + ZDC end-to-end

com fixture estável.

[ALTO] C2 — full\_run\_status\_sync.py (1 626 linhas) — sincronização complexa

Evidência:

\- services/analysis/full\_run\_status\_sync.py (1 626L) — sincronização

`  `de status pós-envio GAL.

Problema:

Tamanho que dificulta isolamento dos passos de sync (CSV, SQLite,

journal, dedupe).

Impacto:

\- Mudanças em GAL-ROB futuros (GAL-PEND-001) impactam aqui.

\- Sem testes-guardião proporcionais.

Recomendação:

Junto à DHP A1. Pré-requisito: GAL-PEND-002 (suite sem Selenium)

para cobertura indireta.

Teste sugerido:

Coberto por GAL-PEND-002.

[ALTO] C3 — persistence\_adapters.py (1 281 linhas) com 12+ adapters

Evidência:

\- services/persistence/persistence\_adapters.py (1 281L)

\- Subagente B: "múltiplas classes/métodos >100L (CsvHistoryRepositoryAdapter,

`  `SQLiteHistoryRepositoryAdapter)".

Problema:

Concentra 12+ adapters num único arquivo. Adicionar novo backend

exige tocar arquivo gigante.

Impacto:

\- Custo cognitivo.

\- Risco em refactor de adapters específicos.

Recomendação:

Junto à DHP A1. Split natural: 1 arquivo por contrato

(history\_adapter.py, exam\_config\_adapter.py, equipment\_adapter.py, etc.).

Teste sugerido:

Cada split exige teste de contrato (Protocol conformance).

[ALTO] C4 — operational\_tabular\_viewer.py (1 151 linhas) e operational\_slo\_governance.py (1 060 linhas)

Evidência:

\- services/legacy\_audit/operational\_tabular\_viewer.py (1151L)

\- services/legacy\_audit/operational\_slo\_governance.py (1060L)

\- Subagente C: status "PHASE-OUT" / "EM PHASE-OUT".

Problema:

Arquivos gigantes em PHASE-OUT sem deadline. Pode ser tentação para

expansão acidental.

Impacto:

\- Custo de manutenção sem perspectiva de saída.

Recomendação:

ABRIR DHP "Deadline de phase-out de services/legacy\_audit/menu\_catalog\_\*

e operational\_tabular\_viewer". Definir data + critérios.

NÃO IMPLEMENTAR SEM DECISÃO HUMANA.

Teste sugerido:

N/A imediato. Após DHP, guardião de não-expansão (linhas/símbolos

allowlist).

**D. Validações positivas (informativo)**

[INFORMATIVO] D1 — INST-001 (config\_service.\_save\_config) implementado corretamente

Evidência:

\- services/core/config\_service.py:669-720

`  `- Lock exclusivo: os.O\_CREAT | os.O\_EXCL com retry loop (50x, 0.1s)

`  `- Escrita atômica: tempfile.mkstemp() → write+fsync → os.replace()

`  `- Backup: shutil.copy2(CONFIG\_PATH, CONFIG\_PATH + ".bak")

Problema:

Nenhum. Observação positiva.

Impacto:

INST-001 cumprida. Modelo de "write atomic + lock" exemplar.

Recomendação:

Considerar replicar padrão em outros writes críticos (gal\_transactions,

exam\_runs\_csv) se ainda não usar csv\_io.write\_csv\_atomic.

Teste sugerido:

N/A.

[INFORMATIVO] D2 — GAL-ROB-007/008/010 implementados em services/gal/

Evidência:

\- gal/gal\_transactions.py:441L — build\_idempotency\_key (dual-key)

\- gal/gal\_status\_reconciler.py:95 — reconcile\_gal\_status (fallback

`  `por codigo\_amostra)

\- gal/history\_gal\_sync.py:608L — sync histórico

Problema:

Nenhum.

Impacto:

Cobertura completa de GAL-ROB nesta camada.

Recomendação:

Manter. GAL-PEND-001 (retry transitório/definitivo) é próximo passo.

Teste sugerido:

GAL-PEND-002 (sem Selenium real).

[INFORMATIVO] D3 — T-AUD-010 documentalmente atendida (inventario\_services.md)

Evidência:

\- docs/specs/inventario\_services.md mapeia 7 subdomínios.

\- 6 já existem fisicamente: core/, analysis/, engine/, equipment/, gal/,

`  `persistence/, reports/.

\- 1 falta físico: services/operational/ (vide A2).

Problema:

Nenhum imediato.

Impacto:

Inventário é referência viva para A1/A2.

Recomendação:

Manter atualizado. Citar como pré-requisito em DHP A1.

Teste sugerido:

N/A.

**E. Pendências SDD relevantes (informativo)**

[INFORMATIVO] E1 — LIM-004 (10 usuários) pendente — impacta CONC-002/003

Evidência:

\- design.md L356: "capacidade para 10 usuarios simultaneos nao comprovada"

\- CONC-002: teste multiprocess 10 usuários em CSVs críticos.

\- CONC-003: claim/lease GAL antes do envio externo.

\- Ambos tocam services/persistence/ e services/gal/.

Problema:

Nenhum imediato (documentado).

Impacto:

Bloqueia produção 10 usuários até resolução.

Recomendação:

Priorizar em rodada própria. Pode coordenar com GAL-PEND-001.

Teste sugerido:

tests/test\_persistence\_multiprocess\_10\_users.py + tests/test\_gal\_claim\_lease.py.

-----
**Consolidação dos subagentes simulados**

|**Subagente**|**Veredicto**|
| :- | :- |
|**Arquiteto SDD**|Camada FUNCIONALMENTE COMPLETA (todos os GAL-ROB, DASH, R0, DEC-006, INST cobertos). DT-002 / T-AUD-010 doc OK, físico pendente.|
|**Bug Hunter**|Nenhum bug runtime confirmado. Risco LATENTE: logic\_engine.py stub, config\_loader deprecado, arquivos gigantes.|
|**Código Morto / Redundância**|logic\_engine.py (12L stub); services/core/config\_loader.py (439L deprecado); 2 config\_loader; cluster operational\_\* disperso.|
|**Especialista em Testes**|Pontos críticos cobertos (csv\_io atomic, GAL-ROB, INST-001). Faltam testes diretos para 5 arquivos gigantes (>1000L) — T-AUD-013 pendente.|
|**Revisor de Enxutez**|5 arquivos >1 000L é o maior débito. 17 >300L. Decomposição depende de testes prévios.|

**Próximas decisões humanas relevantes**

1. **DHP A1** — Plano T-AUD-010-FASE-2 (split físico dos 5 gigantes).
1. **DHP A2** — Consolidar cluster operational\_\* em services/operational/.
1. **DHP B2** — Cronograma de remoção de services/core/config\_loader.py deprecado.
1. **DHP C4** — Deadline de phase-out de services/legacy\_audit/.
1. **CONC-002 / CONC-003** — Pré-requisitos para LIM-004.
1. **GAL-PEND-001 / GAL-PEND-002** — Já registradas; tocam services/gal/.

**Resumo de ações priorizadas**

1. **[ALTO] A1** — DHP para split físico dos 5 arquivos >1 000L. Pré-requisito: cobertura ≥70%.
1. **[ALTO] CONC-002/003** — para destravar LIM-004.
1. **[ALTO] B1** — verificar callers de services/analysis/logic\_engine.py (stub).
1. **[ALTO] C4** — DHP deadline phase-out legacy\_audit/.
1. **[MÉDIO] A2** — DHP consolidar operational\_\* em subpasta.
1. **[MÉDIO] A3/B2** — DHP destino dos config\_loader deprecados.
1. **[INFORMATIVO] D1/D2/D3** — manter padrões positivos como referência.

Nenhuma alteração foi realizada nesta rodada. Inventário leu docstrings + símbolos públicos; análise integral de ~1 MB exigiria múltiplas rodadas (vide nota em Escopo).





Confirmações cristalinas: sql/ é lixo legado documentado (inventario\_de\_lixo.md:109), dados/ tem DHPs ativas (10/11), dados/dados/ é **resíduo confirmado** do bug logs\_dir="dados/banco" (CONFIG-PATH-001 corrigiu mas físico permaneceu). Consolidando.

-----
**Auditoria SDD READ-ONLY — sql/ e dados/**

**1. Escopo analisado**

**Pastas alvo:**

- C:\Integragal - Backup - 20260128\_151811\sql\
- C:\Integragal - Backup - 20260128\_151811\dados\

**sql/ — 3 arquivos (~1,2 KB):**

|**Arquivo**|**Linhas**|**Tamanho**|
| :- | :- | :- |
|**init**.py|1|0 B|
|criar\_historico\_processos.sql|33|1,1 KB|
|requirements.txt|8|90 B|

**dados/ — ~1 462 arquivos (~22 MB):**

|**Subpasta**|**Arquivos**|**Tamanho**|**Conteúdo principal**|
| :- | :- | :- | :- |
|banco/|7|412 KB|historico.db (131 KB), historico\_analises.csv (280 KB), CSVs metadados|
|banco\_runtime/|1|1 KB|usuarios.csv|
|csv\_gal/|0|0 B|VAZIO|
|dados/ (aninhado!)|6 + subpastas|147 KB|resíduo bug LOGS\_DIR|
|data/|1|220 B|1 arquivo|
|logs/|79|17,5 MB|sistema.log (gigante), JSONs corridas|
|mapas/|49|504 KB|XLSXs gerados|
|reports/|1 263|2,7 MB|1 109 JSONs (relatorio\_final\_corrida\_\*) + 152 CSVs|

**Por tipo de arquivo (dados/):**

- 1 155 JSON (2,1 MB)
- 169 CSV (2,9 MB)
- 50 XLSX (521 KB)
- 27 TXT (183 KB)
- 3 LOG (14,9 MB)
- 1 PNG (8,6 KB)
- 1 DB (128 KB)

**NÃO abertos (motivo de governança):**

- dados/banco/usuarios.csv (439 B), dados/banco\_runtime/usuarios.csv (1 KB) — proibido por CLAUDE.md §9 + PRIV-001 (dados de credenciais).
- dados/banco/historico.db (131 KB), dados/banco/historico\_analises.csv (280 KB) — DHP-10/DHP-11 PENDENTES; inspecção requer rodada controlada LGPD-adequada.
- dados/banco/equipamentos.csv, exames\_config.csv, placas.csv, regras.csv — DHP-11 pendente.
- dados/logs/sistema.log (vários MB) e demais JSON/CSV de runtime — não relevantes para auditoria estrutural; podem conter dados clínicos.
- Conteúdo de mapas/*.xlsx, reports/*.json e reports/\*.csv — não amostrado; possíveis dados clínicos.

**Fontes SDD lidas:**

- CLAUDE.md §7 (Postgres proibido), §9 (segurança), §13 (LIM-003), §15 (DEC-002, DHP-10/11/12)
- AGENTS.md §15/§16
- docs/specs/design.md §3.10 (linhas 219, 376-382 — root unificado de logs + extinção de dados/banco/)
- docs/specs/tasks.md (linhas 142-145 DHP-10/11 pendentes; LOG-UNIF-001/002 concluídas; CONFIG-PATH-001 concluída linha 257)
- docs/obsoletos/inventario\_de\_lixo.md:109 — **classificação canônica de sql/ como "DDL PostgreSQL orphaned"**
- docs/specs/higienizacao\_implantacao.md:183 — sql/ excluída do release
- notas\_de\_passagem.md
-----
**2. Mapa das pastas**

**sql/ (LEGADO PostgreSQL — DOCUMENTADO COMO LIXO)**

sql/

├─ \_\_init\_\_.py                          (vazio — 1 linha)

├─ criar\_historico\_processos.sql        (33 linhas — 4 tabelas: historico\_processos,

│                                         log\_sistema, configuracoes, exames\_personalizados;

│                                         usa SERIAL PRIMARY KEY = PostgreSQL-específico)

└─ requirements.txt                     (8 linhas — pandas, openpyxl, matplotlib,

`                                         `seleniumrequests, dearpygui, simplejson,

`                                         `psycopg2-binary, tk)

**Status SDD:** docs/obsoletos/inventario\_de\_lixo.md:109:

"sql/ | DDL PostgreSQL orphaned | criar\_historico\_processos.sql usa SERIAL (PostgreSQL); Postgres nao e usado (AGENTS.md §7); sql/requirements.txt contem psycopg2-binary e dependencias orphaned | Excluir de release/app/"

Confirmado em docs/specs/higienizacao\_implantacao.md:183: "release/app/ nao contem ... sql/ ... (legados, fachadas de teste, artefatos de debug/build; confirmados sem imports de producao em REL-002)".

**dados/ (ARTEFATOS DE RUNTIME — resíduo de bug + DHPs pendentes)**

dados/

├─ banco/                               (DHP-10 + DHP-11 PENDENTES)

│  ├─ historico.db             (131 KB — DHP-10: inspecionar antes de excluir)

│  ├─ historico\_analises.csv   (280 KB — possíveis dados clínicos)

│  ├─ usuarios.csv             (439 B — PRIV-001, NÃO abrir)

│  ├─ equipamentos.csv         (36 B)

│  ├─ exames\_config.csv        (56 B)

│  ├─ placas.csv               (31 B)

│  └─ regras.csv               (39 B)

│

├─ banco\_runtime/                       (sobreposição com banco\_runtime/ canônico na raiz)

│  └─ usuarios.csv             (1 KB — PRIV-001)

│

├─ csv\_gal/                             (VAZIO — candidato a remoção)

│

├─ dados/                               (RESÍDUO BUG logs\_dir="dados/banco" — CONFIG-PATH-001 corrigido)

│  ├─ banco/                            (aninhamento extra!)

│  ├─ audit/                            (subpasta)

│  ├─ corridas\_vr1e2\_biomanguinhos\_7500.csv

│  ├─ historico\_analises.csv

│  ├─ query\_latency.csv

│  ├─ relatorio\_final\_corrida\_last.json

│  ├─ relatorio\_final\_corrida\_vr1e2\_...\*.xlsx

│  └─ audit.log

│

├─ data/                                (1 arquivo, 220 B — propósito desconhecido)

│

├─ logs/                                (17,5 MB — DUPLICAÇÃO de logs/ canônico na raiz)

│  ├─ sistema.log                       (maior arquivo, vários MB)

│  ├─ relatorio.csv

│  ├─ corridas\_vr1e2\_biomanguinhos\_7500.csv

│  ├─ gal\_transacoes.csv

│  └─ ~75 relatorio\_final\_corrida\_\*.{json,txt}

│

├─ mapas/                               (504 KB — 49 XLSXs Mapa Definitivo gerados)

│

└─ reports/                             (2,7 MB — 1 263 arquivos)

`   `├─ ~1 109 relatorio\_final\_corrida\_\*.json (DEC-005 sem retenção)

`   `├─ ~152 CSVs (placa, gal, etc)

`   `├─ 1 PNG

`   `└─ 1 XLSX

**Status SDD documentado:**

- design.md:219: "dados/banco/ (residuo extinto): existia como consequencia do bug logs\_dir = 'dados/banco' (corrigido em LOG-UNIF-001). Arquivos unicos migrados para logs/ em LOG-UNIF-002. Itens residuais pendentes de DHP-11."
- design.md:382: "**dados/banco/ extinto como destino ativo**: apos migracao dos arquivos unicos e correcao do logs\_dir, nenhum componente ativo grava em dados/banco/. Itens residuais (historico.db obsoleto, CSVs duplicados) aguardam DHP-10/DHP-11."
- tasks.md:257: "CONFIG-PATH-001 — config.json paths.logs\_dir de 'dados/banco' para 'logs' (**elimina pasta dados/dados/**); ... Rodada especifica autorizada."

**Fluxos relevantes.**

- Nenhum componente ativo grava em dados/banco/ (design.md §3.10).
- dados/dados/ é resíduo confirmado do bug pré-LOG-UNIF-001.
- dados/logs/ duplica logs/ canônico (gerado pelo bug logs\_dir antes da correção).
- dados/reports/ acumula relatorio\_final\_corrida\_\*.json sem política de retenção (DEC-005 documentada como pendente sem auto-cleanup).
- dados/mapas/ contém XLSXs do Mapa Definitivo gerados em sessões anteriores.

**Dependências (sql/):** ZERO imports Python (from sql retorna 0 matches). requirements.txt lista deps que NÃO são consumidas pelo projeto Python (dearpygui, psycopg2-binary, simplejson).

**Dependências (dados/):** É runtime data; código consome via services.path\_resolver, mas após LOG-UNIF-001/002 + CONFIG-PATH-001 o caminho canônico é logs/ (na raiz), banco\_runtime/ (na raiz), banco\_template/ (na raiz). dados/\* é resíduo histórico.

-----
**3. Diagnóstico executivo**

**sql/**

**Coerência com SDD.** **Nula.** Pasta documentada em inventario\_de\_lixo.md como "DDL PostgreSQL orphaned"; criar\_historico\_processos.sql usa SERIAL PRIMARY KEY (PostgreSQL-específico) e CLAUDE.md §7 explicitamente proíbe PostgreSQL. requirements.txt lista psycopg2-binary (PostgreSQL driver) + dearpygui (não usado pelo projeto, que usa customtkinter).

**Enxutez.** Pasta é minúscula (1,2 KB) — não há excesso.

**Redundância.** Pasta INTEIRA é redundante: zero callers, zero menções em código de produção, schema PostgreSQL que viola §7, deps órfãs.

**Bugs prováveis.** Nenhum runtime (nada executa). Risco LATENTE: dev instala requirements.txt da raiz desta pasta e contamina o env.

**Risco arquitetural.** **Baixo a Médio.** Confusão para novos contribuidores ("temos PostgreSQL?"). Manifest HIG-008 já exclui do release.

**Violação SDD.** **Materializada documentalmente** mas **inerte funcionalmente**:

- Viola §7 (PostgreSQL não deve ser usado) — apenas como DDL deixado no disco.
- Viola implicitamente §4 (estrutura principal não lista sql/).

**Recomendação geral.** **DEPRECAR formalmente via DHP** (mesma natureza do tratamento dado a analise/ e extracao/).

**dados/**

**Coerência com SDD.** **Mista.**

- **Positivo:** SDD documenta corretamente o status: LOG-UNIF-001/002 corrigiu o bug original; CONFIG-PATH-001 eliminou a fonte de novos resíduos; DHP-10/11 registram itens pendentes; design.md §3.10 declara dados/banco/ extinto como destino ativo.
- **Negativo:** Resíduo físico GIGANTE (~22 MB) permanece sem ferramenta de limpeza. dados/dados/ aninhado confirmado, dados/logs/ duplica logs/ canônico, dados/reports/ acumula 1 109 JSONs sem retenção.

**Enxutez.** **Insuficiente.** 22 MB de dados duplicados/resíduos em pasta declarada extinta.

**Redundância.** **Massiva.**

- dados/logs/ ↔ logs/ (raiz)
- dados/banco/ ↔ banco\_runtime/ (raiz) ↔ banco\_template/ (raiz)
- dados/banco\_runtime/ ↔ banco\_runtime/ (raiz) — segunda cópia de usuarios.csv
- dados/dados/banco/ ↔ todos os anteriores (resíduo de aninhamento triplo)
- dados/reports/ ↔ política DEC-005 indica .gitignore, mas físico persiste

**Bugs prováveis.**

1. **dados/dados/ aninhado** é evidência de bug histórico CONFIG-PATH-001 corrigido. Subpasta dados/dados/banco/ é aninhamento triplo (dados/dados/banco).
1. **dados/csv\_gal/ vazio** sugere bug ou pasta criada e nunca usada.
1. Possível **inconsistência de credenciais** entre dados/banco/usuarios.csv (439 B, mais antigo) e dados/banco\_runtime/usuarios.csv (1 KB) — DHP-11 trata, mas não foi resolvida.

**Risco arquitetural.** **Alto.**

- 22 MB de dados desnecessários inflam backup, git status, ferramentas de busca.
- usuarios.csv em DOIS locais (dados/banco/ + dados/banco\_runtime/) cria risco de DRIFT de credenciais.
- Se algum dev/script antigo apontar para dados/banco/, lê dados desatualizados (regressão silenciosa).

**Violação SDD.**

- DEC-005 (relatorio\_final\_corrida\_\*.json) sem aplicação de retenção física.
- LIM-003 (banco/\* legados em deprecação controlada) parcialmente aplicado: legado canônico banco/ está em deprecação documentada; mas dados/banco/ é resíduo SECUNDÁRIO sem governança.
- usuarios.csv em pasta versionada (mesmo que .gitignore cubra) viola §9 implicitamente — apenas o backup Integragal - Backup - 20260128\_151811 pode estar carregando.

**Recomendação geral.** **AJUSTAR via DHPs já registradas (10/11) + DHPs novas (12, 13, 14).**

-----
**4. Notas 0–10 — consolidadas para ambas**

|**Aspecto**|**Nota**|**Justificativa**|
| :- | :- | :- |
|Aderência SDD|**5**|sql/ documentado como lixo (positivo SDD), MAS viola §7 (PostgreSQL). dados/ tem DHPs registradas (DHP-10/11) corretamente, mas resíduo físico não foi tratado.|
|Arquitetura|**3**|sql/ é PostgreSQL órfão; dados/ tem 5+ pastas duplicadas/resíduos (dados/dados/, dados/logs/ duplicando logs/, banco e banco\_runtime em ambas raízes).|
|Clareza e Enxutez|**2**|dados/ tem 22 MB de resíduos. dados/dados/ aninhado é confuso. dados/csv\_gal/ vazio.|
|Robustez|**5**|DHPs 10/11 documentadas protegem contra remoção precipitada. Bug original (logs\_dir) corrigido em LOG-UNIF-001 e CONFIG-PATH-001. Mas falta cleanup automático de resíduos.|
|Manutenibilidade|**3**|Volume gigante (~22 MB) + naming confuso (dois banco\_runtime/, três níveis de dados/) torna investigação custosa em cada auditoria.|
|Testabilidade|**5**|LOG-UNIF-001/002 tem guardiões (tests/test\_log\_paths\_uniformization.py 9 passed, tests/test\_banco\_path\_fallbacks.py 7 passed). Não há guardião contra recriação de dados/banco/ ou dados/dados/.|
|Risco Operacional|**4**|usuarios.csv em 2 locais (drift potencial). 22 MB acumulados sem retenção em backup git-versionado pesa. sql/ órfão é confusão leve.|
|Prontidão para Evolução|**3**|Pastas deveriam ser tratadas antes de produção. Sem cleanup, cada deploy carrega o resíduo.|
|**Geral**|**3,5**|sql/ (3/10 — lixo documentado, fácil de tratar). dados/ (4/10 — bug corrigido na fonte mas resíduo físico de 22 MB permanece). Mereceu nota baixa apesar da boa governança documental (DHPs registradas) porque o estado físico real está desordenado.|

-----
**5. Achados detalhados**

**A. sql/ — lixo legado PostgreSQL**

[ALTO] A1 — sql/ é DDL PostgreSQL órfão violando CLAUDE.md §7

Evidência:

\- sql/criar\_historico\_processos.sql:3 `id SERIAL PRIMARY KEY` (PostgreSQL-específico)

\- sql/criar\_historico\_processos.sql cria 4 tabelas: historico\_processos,

`  `log\_sistema, configuracoes, exames\_personalizados.

\- sql/requirements.txt:7 `psycopg2-binary` (driver PostgreSQL)

\- sql/requirements.txt:5 `dearpygui` (UI lib NÃO usada pelo projeto)

\- CLAUDE.md §7: "Postgres dedicado nao deve ser usado (provider nao implementado)."

\- docs/obsoletos/inventario\_de\_lixo.md:109: "sql/ | DDL PostgreSQL orphaned ...

`  `Excluir de `release/app/`"

\- Grep `from sql | import sql.` no repo: ZERO callers.

\- higienizacao\_implantacao.md:183 confirma exclusão do release (REL-002).

Problema:

Pasta inteira é resíduo PostgreSQL documentado e classificado como lixo,

mas mantida fisicamente em árvore versionada.

Impacto:

\- Risco de instalação de psycopg2-binary se dev rodar `pip install -r sql/

`  `requirements.txt` por engano (contaminação de env).

\- Confusão arquitetural: presença sugere migração PostgreSQL em andamento

`  `que NÃO existe.

\- Esforço de inspeção repetido em cada auditoria.

Recomendação:

ABRIR DHP NOVA "destino de sql/" — mesma natureza dos casos analise/,

extracao/, scratch/, interface/ (rodada conjunta de housekeeping de

pastas paralelas órfãs).

Opções:

(A) mover para docs/obsoletos/sql/ (símil HIG-005/006);

(B) remover (rodada própria; precedente DEC-002/004 desfavorece);

(C) manter como referência com README "DEPRECATED — PostgreSQL não é

`    `usado per AGENTS.md §7".

NÃO IMPLEMENTAR SEM DECISÃO HUMANA. Recomendar (A) ou (C); contra (B)

sem precedente.

Teste sugerido:

tests/test\_sql\_legacy\_no\_runtime\_imports.py — guardião AST que falhe

se algum .py em runtime contiver `from sql` ou `import sql.X`.

[MÉDIO] A2 — requirements.txt em sql/ lista deps órfãs (dearpygui, simplejson)

Evidência:

\- sql/requirements.txt:5 `dearpygui` (UI alternativa Dear PyGui — NÃO usada

`  `pelo projeto, que usa customtkinter).

\- sql/requirements.txt:6 `simplejson` (alternativa à stdlib json — NÃO

`  `referenciada em código).

Problema:

requirements.txt em pasta legada lista deps que nunca foram canônicas.

Risco de poluir pip se rodado.

Impacto:

\- Confusão sobre quais deps realmente são necessárias.

\- requirements.txt da raiz do projeto (se existir) é o canônico, este é

`  `contraditório.

Recomendação:

Tratar junto à DHP A1. Em qualquer das opções, marcar como deprecated.

Teste sugerido:

N/A (DHP resolve).

**B. dados/ — resíduos físicos de bug corrigido**

[ALTO] B1 — dados/dados/ é resíduo físico do bug CONFIG-PATH-001 corrigido

Evidência:

\- dados/dados/ (147 KB, 6 arquivos + subpastas: banco/, audit/)

\- docs/specs/tasks.md:257 (CONFIG-PATH-001 concluída):

`    `"`config.json` `paths.logs\_dir` de `'dados/banco'` para `'logs'`

`     `(elimina pasta `dados/dados/`)"

\- design.md:219: "dados/banco/ (residuo extinto): existia como consequencia

`  `do bug `logs\_dir = 'dados/banco'`"

\- Inspecção: dados/dados/ contém corridas\_vr1e2\_..., historico\_analises.csv,

`  `relatorio\_final\_corrida\_last.json, query\_latency.csv, audit.log,

`  `e mais subpasta dados/dados/banco/ (aninhamento triplo).

Problema:

CONFIG-PATH-001 CORRIGIU a fonte do bug, mas o resíduo físico (~147 KB)

permaneceu na árvore. CONFIG-PATH-001 mencionou "elimina pasta dados/dados/"

mas a eliminação NÃO foi executada — só a configuração foi corrigida para

não gerar mais.

Impacto:

\- Backup carrega lixo.

\- Auditorias futuras precisam re-confirmar status.

\- Aninhamento triplo (dados/dados/banco/) é confuso.

Recomendação:

ABRIR DHP NOVA "Cleanup físico de dados/dados/ pós-CONFIG-PATH-001".

Subagentes anteriores não devem confundir com DHP-10/11 que tratam de

dados/banco/ (raiz da pasta dados/). Esta é DHP-13.

Após confirmar DHP-13, criar script idempotente:

`  `scripts/cleanup\_dados\_dados\_residuo.py --dry-run | --apply

NÃO IMPLEMENTAR SEM DECISÃO HUMANA.

Teste sugerido:

tests/test\_dados\_dados\_nao\_recriado.py — assert que após corrida

end-to-end nenhum arquivo é gravado em `dados/dados/`. Cobre regressão

caso `paths.logs\_dir` volte ao valor antigo.

[ALTO] B2 — dados/logs/ duplica logs/ canônico (17,5 MB)

Evidência:

\- dados/logs/ (79 arquivos, 17,5 MB) contém sistema.log, relatorio.csv,

`  `corridas\_\*, gal\_transacoes.csv, ~75 relatorio\_final\_corrida\_\*.json/txt.

\- Raiz tem logs/ canônico (consumido por config\_service.get\_paths()

`  `["logs\_dir"] = "logs" após CONFIG-PATH-001).

\- design.md §3.10 L376: "`logs/` e o unico root canônico para gravacao

`  `de logs e arquivos de saida de corridas."

Problema:

17,5 MB de logs paralelos gerados pelo bug original (logs\_dir = "dados/

banco" criando o aninhamento dados/dados/, posteriormente refatorado).

Não há limpeza automática.

Impacto:

\- Maior contribuição ao volume residual (~79% dos 22 MB).

\- Sistema.log antigo pode conter dados sensíveis (LGPD/PRIV-001).

\- Backups carregam logs duplicados.

Recomendação:

Junto à DHP B1 (ou DHP nova específica para dados/logs/), definir:

(A) script de migração: mover logs novos para logs/ raiz (se algum mais

`    `recente) e arquivar resto;

(B) preservar como evidência histórica em snapshots/;

(C) remover (após confirmação humana).

NÃO IMPLEMENTAR SEM DECISÃO HUMANA + PRIV-001 (rodada controlada LGPD).

Teste sugerido:

Coberto por B1 (mesmo guardião).

[CRÍTICO] B3 — usuarios.csv presente em DOIS locais (dados/banco/ e dados/banco\_runtime/)

Evidência:

\- dados/banco/usuarios.csv (439 bytes, 30/05/2026)

\- dados/banco\_runtime/usuarios.csv (1 KB, 30/05/2026)

\- Raiz banco\_runtime/usuarios.csv (canônico — LOG-UNIF-002)

\- DHP-11 (tasks.md:145): "Conteudo de usuarios.csv nao deve ser aberto

`  `sem ambiente controlado (PRIV-001)."

Problema:

TRÊS cópias potenciais de usuarios.csv:

1\. dados/banco/usuarios.csv (439 B, legado)

2\. dados/banco\_runtime/usuarios.csv (1 KB, desconhecido)

3\. banco\_runtime/usuarios.csv (raiz canônica)

Risco real de DRIFT entre versões. Inconsistência pode causar:

\- Login com credencial antiga aceito;

\- Auditoria de quem alterou senha desalinhada.

Impacto:

\*\*CRÍTICO\*\*: drift de credenciais é risco operacional grave. Mesmo que

runtime canônico aponte para raiz, presença física dos outros 2 arquivos

em pasta versionada confunde governança e cria risco de ferramentas

externas (backup, antivírus, scripts limpeza) tocarem o errado.

Recomendação:

ABRIR DHP URGENTE "Consolidação de usuarios.csv":

(A) Confirmar qual cópia é a vigente (rodada PRIV-001 controlada).

(B) Identificar processo que ainda escreve em dados/banco\_runtime/

`    `(esperado: nenhum após LOG-UNIF-002; se algum, BUG).

(C) Definir destino das cópias secundárias (arquivar/remover).

NÃO IMPLEMENTAR SEM DECISÃO HUMANA + PRIV-001 + ambiente LGPD-adequado.

NÃO ABRIR conteúdo do arquivo sem essa rodada.

Teste sugerido:

tests/test\_usuarios\_csv\_single\_canonical\_path.py — assert que apenas

banco\_runtime/usuarios.csv (raiz) é referenciado em runtime; nenhuma

escrita em dados/banco/ ou dados/banco\_runtime/.

[ALTO] B4 — dados/banco/ contém DHP-10 e DHP-11 ABERTAS

Evidência:

\- dados/banco/historico.db (131 KB, 30/05/2026)

\- dados/banco/historico\_analises.csv (280 KB)

\- dados/banco/equipamentos.csv, exames\_config.csv, placas.csv,

`  `regras.csv (< 60 B cada — provavelmente vazios ou headers só)

\- tasks.md:144 DHP-10 pendente: "Verificar conteudo de

`  `dados/banco/historico.db (131KB, 25/05/2026, mais antigo dos 4) antes

`  `de qualquer exclusao."

\- tasks.md:145 DHP-11 pendente: "Verificar e decidir destino dos CSVs

`  `duplicados residuais em dados/banco/ apos migracao das corridas...

`  `Conteudo de usuarios.csv nao deve ser aberto sem ambiente controlado

`  `(PRIV-001)."

Problema:

Decisões humanas já documentadas (DHP-10/11). Não há ação executável

sem rodada própria. Mas o estado físico não foi resolvido.

Impacto:

\- Mesmo histórico de risco de drift (B3) aplica.

\- historico\_analises.csv (280 KB) pode conter dados clínicos

`  `desatualizados.

Recomendação:

NÃO IMPLEMENTAR SEM RESOLUÇÃO DE DHP-10/11. Priorizar essa rodada antes

de produção 10 usuários (LIM-004).

Teste sugerido:

N/A (DHP resolve).

[ALTO] B5 — dados/reports/ tem 1 109 JSONs sem política de retenção (DEC-005)

Evidência:

\- dados/reports/ (2,7 MB, 1 263 arquivos)

`  `- 1 109 .json (relatorio\_final\_corrida\_\*.json)

`  `- 152 .csv

`  `- 1 .png, 1 .xlsx

\- CLAUDE.md §15.1 DEC-005 (RESOLVIDA): "arquivos relatorio\_final\_corrida\_\*.json

`  `localizados na raiz sao artefatos runtime/transitorios de execucao,

`  `nao entram no pacote de release operacional e devem ser tratados por

`  `politica de retencao, realocacao ou .gitignore em rodada propria.

`  `Nenhuma exclusao automatica autorizada."

\- HIG-007 (CLAUDE.md §16 concluída): ".gitignore ja cobre `relatorio\_final\_corrida\_\*.json`"

Problema:

DEC-005 + HIG-007 cobrem a versão na RAIZ do projeto. Mas em dados/reports/

1 109 JSONs equivalentes acumularam-se. .gitignore pode não cobrir essa

subpasta. Sem política de retenção real.

Impacto:

\- Backup carrega 2,7 MB de relatórios históricos.

\- Nenhuma rotação por timestamp/dias.

\- Risco de informação clínica acumulada sem governança.

Recomendação:

ABRIR DHP NOVA "Política de retenção para dados/reports/ e dados/mapas/".

Definir:

(A) janela de retenção (ex.: 90 dias);

(B) destino do arquivamento (snapshots/? remoção?);

(C) script de rotação automática.

NÃO IMPLEMENTAR SEM DECISÃO HUMANA. Coordenar com DEC-005 + PRIV-001

(possível conteúdo clínico).

Teste sugerido:

tests/test\_dados\_reports\_retention\_policy.py — após implementação,

assert que arquivos >N dias estão em snapshots/archive/ e não em

dados/reports/.

[BAIXO] B6 — dados/csv\_gal/ está VAZIO

Evidência:

\- dados/csv\_gal/ (0 arquivos, 0 bytes)

\- Nenhum dado, nenhum .gitkeep, nenhum README.

Problema:

Pasta vazia em pasta declarada extinta. Pode ser:

(a) Pasta criada pelo bug e nunca usada;

(b) Resíduo de cleanup parcial anterior;

(c) Placeholder esquecido.

Impacto:

Cosmético. Nenhum risco runtime.

Recomendação:

Tratar junto à DHP B1 (cleanup de dados/dados/). Remoção segura.

Teste sugerido:

N/A.

[BAIXO] B7 — dados/data/ tem 1 arquivo (220 B) com propósito desconhecido

Evidência:

\- dados/data/ (1 arquivo, 220 bytes)

\- Nome do arquivo não inspecionado para preservar tempo.

Problema:

Subpasta com nome confuso ("data" dentro de "dados") + 1 arquivo

pequeno. Difícil dizer status sem abrir.

Impacto:

Mínimo. Provavelmente lixo.

Recomendação:

Tratar junto à DHP B1.

Teste sugerido:

N/A.

[INFORMATIVO] B8 — dados/mapas/ contém 49 XLSXs (Mapa Definitivo)

Evidência:

\- dados/mapas/ (49 arquivos, 504 KB) — XLSXs `mapa\_placa\_\*.xlsx` (DASH-007

`  `/ CA-17)

Problema:

Nenhum imediato. SDD (CA-17) define que Mapa Definitivo deve ser gerado

em <data\_root>/mapas. `<data\_root>` pode estar apontando para dados/

em algum runtime histórico ou ser legítimo.

Impacto:

Se config\_service.get\_paths()["data\_root"] aponta para "dados" no runtime

atual, esta pasta É a canônica. Se aponta para outro lugar, é resíduo.

Recomendação:

Em rodada conjunta com DHP-11, verificar valor real de `data\_root` em

config.json e classificar dados/mapas/ adequadamente.

Teste sugerido:

N/A imediato.

-----
**Consolidação dos subagentes simulados**

|**Subagente**|**Veredicto**|
| :- | :- |
|**Arquiteto SDD**|sql/ documentado como lixo (inventario\_de\_lixo.md) — fácil. dados/ tem DHPs registradas (10/11) MAS resíduos físicos não foram tratados após CONFIG-PATH-001.|
|**Bug Hunter**|B3 (usuarios.csv em 3 locais) é CRÍTICO. B1/B2 (resíduos de bug corrigido) e B4 (DHPs abertas) são ALTOS.|
|**Código Morto / Redundância**|sql/ inteiro. dados/dados/, dados/logs/, dados/csv\_gal/, dados/banco\_runtime/ (duplica raiz) são todos resíduos.|
|**Especialista em Testes**|LOG-UNIF tem guardiões (9+7 passed). Faltam guardiões anti-regressão de dados/dados/ e dados/banco/ + consolidação de usuarios.csv (B3).|
|**Revisor de Enxutez**|22 MB de resíduos em pasta declarada extinta é o problema maior. sql/ é trivial.|

**Próximas decisões humanas relevantes**

1. **DHP-10** (já registrada) — dados/banco/historico.db.
1. **DHP-11** (já registrada) — CSVs duplicados em dados/banco/.
1. **DHP nova B1** — Cleanup físico de dados/dados/ (resíduo CONFIG-PATH-001).
1. **DHP nova B2** — Tratamento de dados/logs/ (17,5 MB).
1. **DHP nova B3 URGENTE** — Consolidação de usuarios.csv (3 locais; risco de drift de credenciais).
1. **DHP nova B5** — Política de retenção para dados/reports/ e dados/mapas/.
1. **DHP nova A1** — destino de sql/ (coordenar com DHPs de pastas paralelas já sugeridas — analise/, extracao/, interface/, scratch/).
1. **PRIV-001** (já registrada) — ambiente LGPD-adequado para qualquer inspeção de CSV/DB.

**Resumo de ações priorizadas**

1. **[CRÍTICO] B3** — DHP urgente para consolidação de usuarios.csv (3 locais).
1. **[ALTO] B1+B2** — DHP coordenada para resíduos de bug corrigido (dados/dados/ + dados/logs/).
1. **[ALTO] B4** — Executar DHP-10 e DHP-11 (já registradas) em rodada PRIV-001-compatível.
1. **[ALTO] B5** — DHP para retenção de dados/reports/.
1. **[ALTO] A1** — DHP para sql/ (coordenar com pastas paralelas).
1. **[BAIXO] B6/B7** — dados/csv\_gal/ (vazio) e dados/data/ — tratar junto às DHPs.

Nenhuma alteração foi realizada nesta rodada. NENHUM CSV/DB sensível foi aberto (CLAUDE.md §9 + PRIV-001 + DHP-10/11).



Dados densos. UI é a maior camada do projeto (1,6 MB), com **cadastros\_ui.py de 4326 linhas — o maior arquivo único do projeto inteiro**, e um .bak de 71 KB no top-level. Consolidando.

-----
**Auditoria SDD READ-ONLY — ui/**

**1. Escopo analisado**

**Pasta alvo:** C:\Integragal - Backup - 20260128\_151811\ui\

**Inventário macro (54 arquivos, ~1 637 KB):**

|**Camada**|**Arquivos**|**Tamanho**|**Notáveis**|
| :- | :- | :- | :- |
|Top-level|17|~360 KB|janela\_analise\_completa (86KB), menu\_handler.py (70KB), .BAK (71KB!), user\_management (38KB), main\_window (25KB)|
|modules/|26|971 KB|cadastros\_ui (112KB / 4326L!), dashboard (86KB/2026L), wizard exam\_creator (59KB/1482L)|
|components/|9|308 KB|full\_analysis\_grid, scientific\_data\_grid, base\_components, plate\_viewer, design\_tokens (em theme)|
|theme/|2|5,6 KB|design\_tokens.py (canônico Blueprint)|

**Não abertos (motivo):**

- Conteúdo integral de arquivos >1 000L (cadastros\_ui, dashboard, wizard, janela\_analise\_completa, menu\_handler) — inventário leu apenas docstrings + símbolos públicos (análise integral exigiria múltiplas rodadas, conforme padrão T-AUD-010).
- ui/menu\_handler.py.bak.moderniza (71 KB) — **NÃO ABERTO**: arquivo .bak; abrir conteúdo não agrega valor além do tamanho/status.
- \_\_pycache\_\_/\*.pyc.

**Fontes SDD lidas:**

- CLAUDE.md §4/§12/§16 (UI-AUD-001/002/003, DASH-001..008, CFG-UI-001, WIZ-GAL-01..07, T-06)
- AGENTS.md §16
- docs/specs/design.md §3.1-§3.8
- docs/specs/tasks.md (UI-AUD-001/002/003, T-AUD-014, INST-004/005, HIG-009, CONC-001..006)
- notas\_de\_passagem.md
-----
**2. Mapa da pasta**

**Top-level (17 arquivos)**

|**Arquivo**|**Linhas**|**Responsabilidade**|**Status**|
| :- | :- | :- | :- |
|\_\_init\_\_.py|34|Exports: MainWindow, MenuHandler, NavigationManager, StatusManager|OK|
|main\_window.py|~750|Bootstrap janela única (orquestra ModuleHost + Navigation + MenuHandler)|Entry point|
|menu\_handler.py|**~2 150**|Orquestra menu principal; delega para ui/modules/\* (T-06)|Ativo|
|**menu\_handler.py.bak.moderniza**|(n/a)|**BACKUP de refactor "moderniza" abandonado**|**ÓRFÃO**|
|janela\_analise\_completa.py|**1 934**|Modal de análise (legacy grande) com abas Análise + Mapa|Legacy ativo|
|user\_management.py|~1 290|CRUD usuários (AuthService + bcrypt) — T-AUD-014 corrigiu BOM|OK|
|admin\_panel.py|~450|Painel admin (Sistema, Config, Logs, Backup)|OK|
|admin\_initial\_setup.py|~350|Wrapper INST-001..003 (validação paths + ACLs)|OK|
|admin\_initial\_setup\_wizard.py|~150|Wizard step-by-step CTkToplevel|OK|
|equipment\_detection\_dialog.py|~200|Dialog modal: detecção automática + top-3 matches|OK|
|equipment\_confirmation\_dialog.py|~180|Dialog modal: confirmar/alterar equipamento detectado|OK|
|gal\_ui\_dialog\_adapter.py|~250|Adapter dialogs UI → GAL (CSV, observação, report name)|OK|
|navigation.py|~200|NavigationManager single-window (register/navigate/history/state)|OK|
|single\_window\_bootstrap.py|~150|Feature flag UI\_SINGLE\_WINDOW; create\_app\_with\_rollback|OK|
|module\_host.py|~130|Host de módulos single-window (show\_module, cache)|OK|
|notification\_backend.py|~100|Backend de notificação UI para ErrorHandler|OK|
|status\_manager.py|~90|Gerenciador da barra de status|OK|

**modules/ (26 arquivos)**

**Macro-categorias:**

|**Categoria**|**Arquivos**|**Notas**|
| :- | :- | :- |
|**Cadastros & CRUD**|2 (cadastros\_ui 112KB/4326L + cadastros\_diversos.py shim 443B)|cadastros\_ui é o **MAIOR ARQUIVO DO PROJETO**|
|**Dashboards & Relatórios**|5 (dashboard 86KB/2026L + reports 30KB/737L + historico\_analises 32KB/853L + graficos\_qualidade 28KB/700L + visualizador\_exame 25KB/704L)|DASH-001..008 todas concluídas|
|**Configurações**|1 (tela\_configuracoes 31KB/884L)|CFG-UI-001 concluído|
|**Wizard exame**|exam\_creator/wizard.py (59KB/1482L)|WIZ-GAL-01..07 + WIZ-UI-001|
|**Análise**|analise\_setup.py (9KB/234L)|Pré-análise fase 1|
|**Extração**|extraction\_plate\_mapping.py (21KB/495L)|T-06 canônico|
|**Exportação & Alertas**|exportacao\_relatorios (27KB/638L) + sistema\_alertas (34KB/928L)|Alertas tem fallback inline|
|**Operacional**|historico\_operacional.py (36KB/819L)|F9 viewer|
|**Estilos**|estilos/**init**, cores.py, fontes.py|LEGACY (concorre com ui/theme)|
|**Componentes**|componentes/card\_resumo.py|Usa ui.theme (moderno)|
|**Facade**|plate\_viewer.py (10L wildcard re-export)|shim para ui/components/plate\_viewer|

**components/ + theme/**

|**Arquivo**|**Linhas**|**Responsabilidade**|**Status**|
| :- | :- | :- | :- |
|components/full\_analysis\_grid.py|~150|Tabela completa (substitui ScientificDataGrid para análise)|Ativo DASH-007|
|components/scientific\_data\_grid.py|~120|Tabela científica com Design System|Ativo (migrado de TreeView por scratch/refactor.py)|
|components/base\_components.py|~50|IGCard, IGButton, IGTextField, IGSidebarMenu|T-AUD-014|
|components/plate\_viewer.py|~60|PlateModel + PlateViewer|Ativo|
|components/buttons.py / cards.py / badges.py|<60 cada|PrimaryButton, ContentCard, ClinicalBadge|Ativos|
|theme/design\_tokens.py|~100|**Fonte canônica**: Colors, SemanticColors, Typography, Spacing, Radii|Blueprint|
|theme/\_\_init\_\_.py|~5|Re-exports Theme, Colors|OK|

**Fluxos relevantes.**

- **Boot:** main\_window.MainWindow.\_\_init\_\_ → single\_window\_bootstrap.create\_app\_with\_rollback → NavigationManager + ModuleHost + MenuHandler + StatusManager.
- **Navegação:** menu\_handler.abrir\_X() → navigation\_manager.navigate\_to("modulo") → ModuleHost.show\_module → carrega ui/modules/X.py.
- **Análise:** janela\_analise\_completa.JanelaAnaliseCompleta (modal CTkFrame de 1934L) — fluxo legacy ativo.
- **Wizard exame:** exam\_creator.wizard.Wizard (1482L, 5 passos) — implementa WIZ-GAL-01..07.
- **Cadastros:** cadastros\_ui (4326L) — janela unificada Exames + Equipamentos + Placas + Regras.

**Dependências internas.** UI consome 20+ módulos de services/ (config\_service, exam\_registry, history\_report, dashboard\_analytics, reports\_repository, runtime\_flags, etc.), 6+ de application/ (use cases, contracts, ui\_view\_models), autenticacao.auth\_service, exportacao.\*.

**Dependências externas.** customtkinter, tkinter, pandas, PIL, reportlab (lazy), matplotlib, bcrypt, openpyxl.

-----
**3. Diagnóstico executivo**

**Coerência com SDD.** **Alta nos features concluídos, lacunas em inventário.**

- **Positivo:** UI-AUD-002 (Reaplicar Seleção), DASH-001..008, CFG-UI-001, WIZ-UI-001, CAL-UI-001, WIZ-GAL-01..07, T-AUD-014 — todos concluídos e referenciados aqui.
- **Negativo:** UI-AUD-001 (inventário canônico) e UI-AUD-003 (plano de modernização) **PENDENTES** — sem mapa formal de telas, modificações futuras são exploratórias.

**Enxutez.** **Crítica.** 6 arquivos >500L na pasta modules/, dos quais 3 >1 500L. **cadastros\_ui.py com 4 326 linhas é o MAIOR arquivo único de todo o projeto**, superando até analysis\_service.py (1 947L) auditado anteriormente.

**Redundância.**

- **Dois sistemas de design coexistem:** ui/modules/estilos/cores.py|fontes.py (paleta hardcoded legada) vs ui/theme/design\_tokens.py (Blueprint canônico). extraction\_plate\_mapping.py e componentes/card\_resumo.py usam ui.theme; sistema\_alertas.py:29-50 tem **fallback CORES/FONTES INLINE** redundante.
- **menu\_handler.py.bak.moderniza (71 KB)** é backup esquecido no top-level — padrão idêntico ao .bak visto em domain/ct\_rules\_runtime.py.bak.target\_recalc\_fix (auditoria de domain/).

**Bugs prováveis & fragilidades.**

1. **ui/modules/plate\_viewer.py** usa from ui.components.plate\_viewer import \* # noqa: F401,F403 — wildcard import com supressão de linter.
1. **TODO incompleto** em visualizador\_exame.py:~123 (v2.2.0 tendências CT).
1. **menu\_handler.py (~2 150L)** sob T-06 mas tamanho dificulta verificação de delegação para ui/modules/extraction\_plate\_mapping.py::abrir\_mapeamento\_extracao (CLAUDE.md §12).

**Risco arquitetural.** **Alto.** Volume de UI (1,6 MB) + tamanho dos super-arquivos + dois design systems concorrentes = manutenção custosa. UI-AUD-001 pendente eleva o risco de regressão a cada mudança.

**Violação SDD.** Nenhuma materializada criticamente. **Divergências documentadas:**

- UI-AUD-001 explicitamente pendente.
- UI-AUD-003 pendente.
- HIG-009 (refactor ~18 arquivos que tocam banco\_template/banco\_runtime) ainda não iniciada.

**Recomendação geral.** **AJUSTAR com DHPs coordenadas + executar UI-AUD-001 + UI-AUD-003.**

Quatro frentes priorizadas:

1. **UI-AUD-001** — inventário canônico de telas (pré-requisito de tudo).
1. **DHP nova** — destino do .bak em ui/ (coordenar com .bak em domain/).
1. **DHP nova** — split de cadastros\_ui.py (4326L) em editores dedicados, após cobertura mínima de testes.
1. **DHP nova** — unificação de design system (estilos/ → theme/), eliminando fallbacks inline.
-----
**4. Notas 0–10**

|**Aspecto**|**Nota**|**Justificativa**|
| :- | :- | :- |
|Aderência SDD|**7**|Features (DASH-001..008, CFG-UI-001, WIZ-GAL-01..07, T-AUD-014, T-06, UI-AUD-002) implementadas. UI-AUD-001/003 pendentes. Dois design systems coexistindo.|
|Arquitetura|**5**|Single-window bootstrap correto (main\_window + ModuleHost + Navigation). Mas top-level mistura entry/dialogs/legacy modal. .bak em árvore versionada.|
|Clareza e Enxutez|**3**|6 arquivos >500L; cadastros\_ui.py (4326L) é o maior do projeto. Wildcard imports. Dois design systems.|
|Robustez|**6**|Componentes base + design tokens centralizados. Mas tamanho dos super-arquivos dificulta isolamento de regressões.|
|Manutenibilidade|**4**|Refactors recentes (DASH, WIZ, CFG) bem feitos. cadastros\_ui exige split urgente. UI-AUD-001 pendente.|
|Testabilidade|**5**|UI-AUD-002 tem teste (test\_reaplicar\_selecao\_aptidao\_operacional). T-AUD-014 tem teste. Mas cobertura geral de UI é baixa (ScientificDataGrid + ui\_view\_models testados via application/).|
|Risco Operacional|**6**|Single-window bootstrap com rollback (boa governança). Risco residual: cadastros\_ui é frágil para mudanças sem cobertura.|
|Prontidão para Evolução|**5**|Design tokens + base\_components pavimentam modernização. Mas super-arquivos e UI-AUD-001 pendente dificultam evolução planejada.|
|**Geral**|**5,5**|Camada **funcionalmente completa** com features SDD concluídas, **mas estruturalmente pesada** (1,6 MB, 4326L em 1 arquivo, dois design systems, .bak órfão, UI-AUD-001 pendente). Adequada para piloto produtivo; UI-AUD-001/003 + split de cadastros\_ui são pré-requisitos para evolução não-traumática.|

-----
**5. Achados detalhados**

**A. Estrutura & tamanho**

[CRÍTICO] A1 — cadastros\_ui.py (4 326 linhas) é o MAIOR arquivo único do projeto

Evidência:

\- ui/modules/cadastros\_ui.py (4 326 linhas, 112 KB)

\- Subagente B: "Janela unificada exames/equipamentos/placas/regras, CSV

`  `CRUD, access control, equipment\_profile\_service, dual-editor."

\- Comparação: analysis\_service.py (1947L), janela\_analise\_completa.py (1934L),

`  `wizard.py (1482L), persistence\_adapters (1281L). cadastros\_ui supera todos.

Problema:

Arquivo monolítico que mistura 4 editores (exames, equipamentos, placas,

regras), controle de acesso e integração com equipment\_profile\_service.

Manutenção é arriscada sem testes proporcionais.

Impacto:

\- Refactor de qualquer editor afeta o todo.

\- Code review impossível.

\- Cobertura de testes para 4326 linhas exigiria suíte gigante.

\- Risco em UI-AUD-003 (modernização) — impossível modernizar sem split.

Recomendação:

ABRIR DHP NOVA "Split de cadastros\_ui.py" com pré-requisitos:

(1) UI-AUD-001 concluído (inventário canônico).

(2) Cobertura mínima 50% via tests/test\_cadastros\_\*.py.

(3) Split proposto:

`    `- cadastros\_ui.py (facade + roteamento)

`    `- cadastros\_exames.py (ExamCRUDEditor)

`    `- cadastros\_equipamentos.py (EquipmentCRUDEditor — usa equipment\_profile\_service)

`    `- cadastros\_placas.py

`    `- cadastros\_regras.py

NÃO IMPLEMENTAR SEM DHP NOVA + testes prévios.

Teste sugerido:

Pré-requisito: tests/test\_cadastros\_smoke\_happy\_path.py cobrindo abrir

cada editor + CRUD básico de um item.

[ALTO] A2 — menu\_handler.py.bak.moderniza (71 KB) é backup esquecido em top-level

Evidência:

\- ui/menu\_handler.py.bak.moderniza (71 KB)

\- Não foi aberto (política de auditoria — arquivo .bak).

\- menu\_handler.py (atual) tem 70 KB — sugere que .bak é cópia próxima do

`  `estado atual com refactor "moderniza" abandonado.

\- Padrão idêntico ao achado A2 da auditoria de `domain/`

`  `(ct\_rules\_runtime.py.bak.target\_recalc\_fix).

Problema:

Arquivo de backup em pasta canônica de UI. Não é interpretado pelo Python

(sufixo .bak), mas:

(a) confunde leitor;

(b) cria duplicação física;

(c) sinaliza processo de refactor abandonado.

Impacto:

\- Risco baixo runtime.

\- Risco de governança: zona crítica com backup informal.

\- Aumenta superfície de auditoria.

Recomendação:

ABRIR DHP de housekeeping (coordenar com .bak em domain/). Opções:

(A) mover para docs/obsoletos/ui\_refactor\_attempts/;

(B) remover (rodada própria);

(C) renomear para tests/fixtures/menu\_handler\_modernization\_attempt.py.

Política DEC-002/DEC-004 favorece preservação. NÃO IMPLEMENTAR SEM

DECISÃO HUMANA.

Teste sugerido:

tests/test\_ui\_no\_backup\_files.py — guardião que falhe se ui/ contiver

arquivos com sufixos {.bak, .bak.\*, .orig, .swp, ~}.

[ALTO] A3 — 6 arquivos UI >500 linhas (5 deles >700)

Evidência:

\- ui/modules/cadastros\_ui.py (4326L) — vide A1

\- ui/modules/dashboard.py (2026L) — DASH-001..008 acumuladas

\- ui/janela\_analise\_completa.py (1934L) — modal legacy

\- ui/modules/exam\_creator/wizard.py (1482L) — WIZ-GAL acumulado

\- ui/modules/sistema\_alertas.py (928L)

\- ui/modules/tela\_configuracoes.py (884L)

\- ui/modules/historico\_analises.py (853L)

\- ui/modules/historico\_operacional.py (819L)

\- ui/modules/reports.py (737L)

\- ui/modules/visualizador\_exame.py (704L)

\- ui/modules/graficos\_qualidade.py (700L)

Problema:

Camada UI inteira tem 11 arquivos >500 linhas. Padrão sintomático de

acumulação de features sem refactor.

Impacto:

\- Custo cognitivo alto.

\- Cobertura de teste fica desproporcional ao tamanho.

\- Modernização (UI-AUD-003) fica arriscada sem split prévio.

Recomendação:

Coordenar com UI-AUD-001 (inventário canônico). Cada arquivo grande

ganha rodada própria de split com testes prévios. NÃO IMPLEMENTAR

SEM UI-AUD-001 concluída.

Teste sugerido:

Por arquivo, suite mínima cobrindo happy-path.

**B. Design system & redundância**

[MÉDIO] B1 — Dois design systems coexistem (estilos/ vs theme/)

Evidência:

\- ui/modules/estilos/cores.py — paleta HARDCODED sem dependência de ui.theme

\- ui/modules/estilos/fontes.py — tuples e dicts próprios

\- ui/theme/design\_tokens.py — Colors, SemanticColors, Typography, Spacing,

`  `Radii (Blueprint canônico per subagente C)

\- Consumidores divididos:

`  `- ui/modules/extraction\_plate\_mapping.py:23-25 → usa ui.theme.Theme

`  `- ui/modules/componentes/card\_resumo.py:7 → usa ui.theme.Theme

`  `- ui/modules/sistema\_alertas.py:29-50 → fallback INLINE CORES/FONTES

Problema:

Dois sistemas paralelos para mesma necessidade. Alterar tema (escuro/claro,

ou semântica de cor) exige tocar 2 lugares + fallbacks inline.

Impacto:

\- Inconsistência visual entre módulos novos (ui.theme) e antigos (estilos/).

\- Manutenção dupla.

\- UI-AUD-003 (modernização) pressupõe canônico único.

Recomendação:

ABRIR DHP "Unificação de design system":

(A) Migrar estilos/cores.py + estilos/fontes.py para shims que apontam

`    `para ui.theme.design\_tokens;

(B) Remover fallback inline em sistema\_alertas.py:29-50;

(C) Marcar estilos/ como DEPRECATED até confirmar zero consumidores

`    `diretos (≥1 hoje).

NÃO IMPLEMENTAR SEM DHP. Pode ser parte de UI-AUD-003 quando aprovado.

Teste sugerido:

tests/test\_ui\_single\_design\_system.py — guardião que falhe se algum

.py em ui/ que NÃO seja estilos/ ou theme/ contiver `from ui.modules.estilos`.

[BAIXO] B2 — sistema\_alertas.py:29-50 tem fallback CORES/FONTES inline

Evidência:

\- ui/modules/sistema\_alertas.py:29-50 (segundo subagente B)

\- Define CORES/FONTES localmente se importação de estilos/ falhar.

Problema:

Padrão defensivo justificado historicamente, mas mantém duplicação ativa.

Se estilos/ for migrado (B1), fallback ficaria stale.

Impacto:

Manutenção tripla em mudança de tema.

Recomendação:

Tratar junto à DHP B1. Após unificação, remover fallback.

Teste sugerido:

N/A (DHP B1 resolve).

[BAIXO] B3 — plate\_viewer.py usa wildcard import com noqa

Evidência:

\- ui/modules/plate\_viewer.py (10L)

`    `from ui.components.plate\_viewer import \*  # noqa: F401,F403

Problema:

Wildcard import (F403) + import não usado (F401) com supressão de linter.

Padrão antipadrão Python mas comum para shims.

Impacto:

\- Refatoração em ui/components/plate\_viewer.py muda silenciosamente a

`  `superfície deste shim.

\- Auditores podem perder rastreio do que é reexportado.

Recomendação:

Listar explicitamente:

`    `from ui.components.plate\_viewer import PlateModel, PlateViewer

`    `\_\_all\_\_ = ["PlateModel", "PlateViewer"]

NÃO IMPLEMENTAR SEM rodada conjunta com B1/UI-AUD-003 (pode ser deletado).

Teste sugerido:

N/A.

**C. Lacunas SDD**

[ALTO] C1 — UI-AUD-001 (inventário canônico) PENDENTE

Evidência:

\- tasks.md:113: "UI-AUD-001 [Pendente]: inventário canônico de telas,

`  `fluxos e ações UI."

\- Arquivo previsto `docs/specs/ui\_inventory.md` não criado.

\- 54 arquivos UI / 1,6 MB sem mapa formal.

Problema:

Sem inventário, qualquer modificação em UI é exploratória. UI-AUD-003

(plano de modernização) depende disso.

Impacto:

\- Refactors arriscados (vide A1/A3).

\- HIG-009 (toca UI também) sem base de comparação.

\- Novos contribuidores sem mapa.

Recomendação:

EXECUTAR UI-AUD-001 em rodada própria. Pode ser parcialmente automatizado

(parser de imports + classificação por tipo). NÃO precisa de DHP (já

documentada como tarefa).

Teste sugerido:

N/A (entrega documental).

[ALTO] C2 — UI-AUD-003 (plano modernização) bloqueado por UI-AUD-001

Evidência:

\- tasks.md:114-115: "UI-AUD-003 [Pendente]: plano de modernização."

\- Depende de UI-AUD-001 (não iniciada).

\- UI-AUD-003-A (sistema design + base components) em PROGRESSO via

`  `HIG-009.

Problema:

Modernização rolando em paralelo (HIG-009) sem plano formal. Risco de

divergência entre componentes modernos (ui.theme, base\_components) e

super-arquivos legados (cadastros\_ui).

Impacto:

\- Esforços de modernização espalhados.

\- Sem critério único para decidir prioridades.

Recomendação:

Após UI-AUD-001, agendar UI-AUD-003 explicitamente. Documentar

trade-offs de cada split.

Teste sugerido:

N/A.

**D. Validações positivas (informativo)**

[INFORMATIVO] D1 — DASH-001..008 + DASH-FIX-001 implementadas corretamente

Evidência:

\- ui/modules/dashboard.py (2026L) implementa 3 abas (Resumo/Gestão/Analítica)

\- DASH-001 (ExamRunsSQLiteRepository), DASH-002 (filtros De/Até), DASH-003

`  `(dedup RES\_\*), DASH-004 (Gestão+barra+radar+pizza), DASH-005 (Visão

`  `Analítica + heatmap), DASH-006 (filtros reutilizáveis), DASH-007

`  `(detalhe read-only + Mapa Definitivo), DASH-008 (Corridas Recentes

`  `ordenação).

\- ui/modules/componentes/card\_resumo.py com set\_valor/set\_indicativo

`  `(DASH-FIX-001).

Problema:

Nenhum.

Impacto:

Mostra que UI evolui ativamente quando há rodada SDD focada.

Recomendação:

Manter. Considerar split em rodada futura coordenada com UI-AUD-003.

Teste sugerido:

N/A.

[INFORMATIVO] D2 — T-AUD-014 (BOM em user\_management.py) verificado

Evidência:

\- ui/user\_management.py (1290L) — BOM U+FEFF removido (T-AUD-014).

\- Subagente A: "BOM CHECK: user\_management.py clean (UTF-8 CRLF, no BOM U+FEFF)

`  `— T-AUD-014 confirmado."

Problema:

Nenhum.

Impacto:

Confirma que correção pontual foi mantida.

Recomendação:

Manter. Adicionar guardião opcional `tests/test\_ui\_no\_bom.py` que falhe

se algum .py em ui/ tiver BOM.

Teste sugerido:

tests/test\_ui\_no\_bom\_utf8.py — para cada .py em ui/, assert que

arquivo não começa com `\xef\xbb\xbf`.

[INFORMATIVO] D3 — WIZ-GAL-01..07 + WIZ-UI-001 + CAL-UI-001 + CFG-UI-001 concluídos

Evidência:

\- ui/modules/exam\_creator/wizard.py (1482L) — captura todos campos GAL

`  `+ Limpar Etapa (WIZ-UI-001).

\- ui/modules/dashboard.py — SimpleCalendar (CAL-UI-001).

\- ui/modules/tela\_configuracoes.py — \_carregar\_categoria chama

`  `\_carregar\_valores (CFG-UI-001).

Problema:

Nenhum.

Impacto:

Confirma que feature work UI está sólido.

Recomendação:

Manter.

Teste sugerido:

N/A.

**E. Pendências SDD relacionadas**

[INFORMATIVO] E1 — INST-004/005 pendentes (tocam admin\_initial\_setup)

Evidência:

\- tasks.md INST-004: "ajustar Instalacao Inicial para ADMIN+MASTER

`  `conforme DEC-010"

\- tasks.md INST-005: "teste end-to-end do wizard de instalacao"

\- ui/admin\_initial\_setup.py (350L) e ui/admin\_initial\_setup\_wizard.py (150L)

`  `existem.

Problema:

Nenhum imediato.

Impacto:

Bloqueia produção 10 usuários (CONC-001/004).

Recomendação:

Executar em rodada própria. Pode coordenar com CONC-001/CONC-004.

Teste sugerido:

INST-005 É o teste.

[INFORMATIVO] E2 — HIG-009 (refactor ~18 arquivos banco\_template/banco\_runtime) toca UI

Evidência:

\- tasks.md:141 HIG-009 [Pendente]

\- Escopo: ~18 arquivos .py que referenciam `banco/`.

\- Depende de PRIV-001 + GIG-001.

Problema:

Refactor estrutural pendente que toca UI (provavelmente cadastros\_ui,

admin\_panel, user\_management).

Impacto:

\- HIG-009 deveria coordenar com split A1 (cadastros\_ui) e UI-AUD-003.

Recomendação:

Agendar HIG-009 + UI-AUD-001 + UI-AUD-003 + A1 numa rodada-mãe.

Teste sugerido:

N/A.

-----
**Consolidação dos subagentes simulados**

|**Subagente**|**Veredicto**|
| :- | :- |
|**Arquiteto SDD**|Features (DASH, WIZ-GAL, CFG-UI, T-06, T-AUD-014) bem alinhadas. UI-AUD-001/003 pendentes são lacunas. Dois design systems coexistindo.|
|**Bug Hunter**|A1 (cadastros\_ui 4326L), A2 (.bak 71KB), A3 (11 arquivos >500L) são os maiores riscos estruturais. B1 (design duplo) e B2 (fallback inline) são frágeis.|
|**Código Morto / Redundância**|menu\_handler.py.bak.moderniza, estilos/ vs theme/, fallback inline em sistema\_alertas, wildcard import em plate\_viewer.py.|
|**Especialista em Testes**|UI-AUD-002 + T-AUD-014 têm testes. Cobertura geral de UI é baixa. Pré-requisito para qualquer refactor: cobertura mínima.|
|**Revisor de Enxutez**|1,6 MB de UI com cadastros\_ui (4326L) é insustentável. Split coordenado é prioridade.|

**Próximas decisões humanas relevantes**

1. **UI-AUD-001** — inventário canônico (NÃO precisa de DHP — já é tarefa). Pré-requisito de tudo.
1. **UI-AUD-003** — plano de modernização (depende de UI-AUD-001).
1. **DHP nova A1** — split de cadastros\_ui.py (4326L). Pré-requisito: cobertura mínima.
1. **DHP de housekeeping A2** — destino de menu\_handler.py.bak.moderniza (coordenar com .bak em domain/).
1. **DHP nova B1** — unificação de design system (estilos/ → theme/).
1. **INST-004/005** — execução pendente.
1. **HIG-009** — coordenação com UI-AUD-003.

**Resumo de ações priorizadas**

1. **[CRÍTICO+ALTO] A1+C1** — Executar UI-AUD-001 e abrir DHP para split de cadastros\_ui.
1. **[ALTO] A2** — DHP coordenada para .bak em ui/ + .bak em domain/.
1. **[ALTO] A3** — Tratar split dos 11 arquivos >500L em rodadas sequenciais.
1. **[ALTO] C2** — Após UI-AUD-001, agendar UI-AUD-003.
1. **[MÉDIO] B1** — DHP unificação design system.
1. **[BAIXO] B2/B3** — Endereçados junto à B1.
1. **[INFORMATIVO] D2** — Adicionar guardião BOM em UI (rodada própria de teste).

Nenhuma alteração foi realizada nesta rodada. O .bak de 71 KB e o conteúdo integral dos super-arquivos (>1000L) **não foram abertos** por política de auditoria (foco em estrutura + docstrings + símbolos).



Dados densos. Achado mais grave: **csv\_safety.py deletado sem governança SDD, 10 imports quebrados em runtime**. Consolidando.

-----
**Auditoria SDD READ-ONLY — utils/**

**1. Escopo analisado**

**Pasta alvo:** C:\Integragal - Backup - 20260128\_151811\utils\

**Arquivos analisados (30 arquivos, ~196 KB):**

|**Tier**|**Arquivos**|**Tamanho**|
| :- | :- | :- |
|Grandes (>5 KB)|15|~159 KB|
|Pequenos|15|~37 KB|

**Maiores:** gui\_utils.py (38,4 KB / 1 298 L), persistence.py (15,4 KB / 452 L), io\_utils.py (13,8 KB / 393 L), dataframe\_reporter.py (12,7 KB / 344 L), audit\_logger.py (12,6 KB / 390 L).

**Arquivos NÃO encontrados (CRÍTICO):**

- **utils/csv\_safety.py — DELETADO** no working tree (git status: D utils/csv\_safety.py). 10 imports ativos em runtime apontam para este arquivo — todos QUEBRADOS (vide achado A1).

**Não abertos:** \_\_pycache\_\_/\*.pyc.

**Fontes SDD lidas:**

- CLAUDE.md (LOG-UNIF-001, T-AUD-014, T-AUD-008, PRIV-001)
- AGENTS.md
- docs/specs/design.md, docs/specs/requirements.md, docs/specs/tasks.md (linhas 108, 139, 142)
- notas\_de\_passagem.md
-----
**2. Mapa da pasta**

utils/

│

├── ── IO & RESILIÊNCIA ──

│   ├─ csv\_lock.py            (CSVFileLock — lock atômico para CSV em rede)

│   ├─ network\_io.py          (RetryPolicy, call\_with\_retry, open\_with\_retry, path\_exists\_with\_retry)

│   ├─ io\_utils.py            (auto-detect separator/encoding + read\_data\_with\_auto\_detection 172L)

│   ├─ secure\_path.py         (SecurePath anti-path-traversal CWE-22)

│   └─ ✗ csv\_safety.py        (DELETADO — sanitize\_csv\_value)

│

├── ── OBSERVABILIDADE ──

│   ├─ logger.py              (registrar\_log canônico — CSV via persistence + RetryPolicy)

│   ├─ audit\_logger.py        (AuditLogger — JSON por linha + RotatingFileHandler; LOG-UNIF-001)

│   └─ dataframe\_reporter.py  (DataFrameReporter — captura DF em estágios; LOG-UNIF-001)

│

├── ── VALIDAÇÃO ──

│   ├─ validator.py           (Validator estático — Validator.ct\_valido usado em config/settings)

│   ├─ dataframe\_validator.py (validate\_merge\_quality, add\_data\_source\_flag)

│   └─ remove\_bom.py          (T-AUD-014 — utilitário para remover BOM UTF-8 inicial)

│

├── ── NORMALIZAÇÃO & CLASSIFICAÇÃO ──

│   ├─ text\_normalizer.py     (normalize\_cyrillic + repair\_mojibake\_text)

│   ├─ result\_classifier.py   (classificar\_resultado — numérico CT + RP)

│   ├─ result\_normalizer.py   (normalize\_result\_label — textual 21 variantes)

│   ├─ text\_result\_classifier.py (classify\_result\_text — Unicode-safe + result\_text\_to\_gal\_code)

│   ├─ well\_sorter.py         (parse\_well\_id, sort\_wells, get\_rp\_type — REFACTOR #2 2026-01-30)

│   ├─ ct\_formatter.py        (formatar\_ct\_display)

│   ├─ extraction\_helpers.py  (\_extrair\_numero\_extracao)

│   └─ selecionado\_normalizer.py (\_normalizar\_selecionado)

│

├── ── ERROR HANDLING ──

│   ├─ error\_handler.py       (safe\_operation decorator, ErrorContext — FAIL-OPEN suspeito)

│   └─ suppress\_ctk\_errors.py (filtros stderr/bgerror para CTk benignos)

│

├── ── UI HELPERS ──

│   ├─ gui\_utils.py           (1 298L — MAIOR: TabelaComSelecaoSimulada, CTkSelectionDialog;

│   │                          IMPORTA db.db\_utils L13 — violação de camada)

│   ├─ after\_mixin.py         (AfterManagerMixin para Tk lifecycle)

│   └─ notifications.py       (notificar\_gal\_saved)

│

├── ── ESTADO & ADMIN ──

│   ├─ persistence.py         (PersistenceManager singleton — sessão, cache TTL, backup)

│   ├─ retention.py           (RetentionPolicy + executar\_retencao — rotação logs)

│   ├─ feature\_flag\_admin.py  (CLI de admin de flags)

│   └─ privacy.py             (mask\_patient\_name — PRIV-001 LGPD)

│

└── ── HELPERS ──

`    `├─ import\_utils.py        (importar\_funcao dinâmico)

`    `├─ df\_debug.py            (dump\_df — LEGADO documentado)

`    `└─ \_\_init\_\_.py            (vazio — 0 B)

**Responsabilidades percebidas.** Camada de utilities centralizadas:

1. **IO resiliente** (csv\_lock + network\_io + io\_utils + secure\_path).
1. **Logging multi-canal** (logger CSV + audit\_logger JSON + dataframe\_reporter).
1. **Validação & normalização** (validator + dataframe\_validator + text\_normalizer + 3 classificadores de resultado).
1. **Error handling** (error\_handler com safe\_operation + suppress\_ctk\_errors).
1. **UI helpers** (gui\_utils dominante).
1. **Estado/admin** (persistence + retention + feature\_flag\_admin + privacy).

**Fluxos relevantes.**

1. **Escrita CSV resiliente:** CSVFileLock + open\_with\_retry + RetryPolicy → padrão usado em services/persistence/csv\_io.write\_csv\_atomic e services/gal/gal\_transactions.
1. **Logging canônico:** registrar\_log("Categoria", "msg", "level") → CSV em logs/sistema.log via csv\_contract + CSVFileLock. 60+ callers.
1. **Auditoria estruturada:** AuditLogger (JSON por linha) em pasta de logs separada via config\_service.get\_paths()["logs\_dir"] (LOG-UNIF-001).
1. **Validação CT:** Validator.ct\_valido() chamado por config/settings.py:\_validar\_configuracao.
1. **safe\_operation decorator:** usado em config/settings.py (@safe\_operation em todos os pontos críticos) — comportamento fail-open suspeito (vide A4).

**Dependências internas.** Camada limpa de saída — utils/ NÃO importa de application/ ou ui/, mas:

- gui\_utils.py:13 importa de db/db\_utils (violação cross-layer).
- gui\_utils.py importa de exportacao/\*, ui/modules/\* (UI helpers misturados com lógica de negócio).
- logger.py, audit\_logger.py, dataframe\_reporter.py importam de services.core.config\_service (legítimo — config service é serviço fundacional).
- persistence.py importa de config.settings.get\_config (deprecada).

**Dependências externas.** pandas, openpyxl (via pandas), tkinter, customtkinter, matplotlib, bcrypt (via auth), stdlib (json, csv, pathlib, socket, hashlib, functools, dataclasses).

**Consumidores externos (~73 arquivos):**

|**Consumidor**|**Count**|**Tipos típicos**|
| :- | :- | :- |
|services/|30+|logger, csv\_lock, network\_io|
|ui/|15+|logger, gui\_utils, text\_result\_classifier|
|autenticacao/|8+|logger, csv\_lock, **csv\_safety (QUEBRADO)**|
|application/|6+|logger, extraction\_helpers|
|exportacao/|5+|logger, **csv\_safety (QUEBRADO)**|
|scripts/|5+|logger, network\_io, csv\_lock|
|db/|2+|logger, **csv\_safety (QUEBRADO)**|

**Top utilities por uso:** logger.registrar\_log (60+ callers), CSVFileLock (12+), RetryPolicy + open\_with\_retry (8+), dataframe\_reporter (4+), text\_result\_classifier (3+).

-----
**3. Diagnóstico executivo**

**Coerência com SDD.** **Boa nos canônicos, com 1 violação CRÍTICA.**

- **Positivo:** LOG-UNIF-001 (audit\_logger + dataframe\_reporter) implementado; T-AUD-014 (remove\_bom.py) cumprido; PRIV-001 (privacy.mask\_patient\_name) endereçado pontualmente.
- **Crítico negativo:** csv\_safety.py DELETADO no working tree sem registro em DHP/tasks.md/design.md, **mas 10 imports runtime continuam apontando para o arquivo** — ModuleNotFoundError será disparado na primeira execução de qualquer um dos 10 callers.

**Enxutez.** **Aceitável com 1 exceção.** gui\_utils.py (1 298 linhas) é o maior — mistura UI helpers, TabelaComSelecaoSimulada, CTkSelectionDialog, integração com GAL e historico. Demais arquivos proporcionais.

**Redundância.**

- **3 classificadores de resultado**: result\_classifier.py (numérico CT+RP), result\_normalizer.py (label textual), text\_result\_classifier.py (Unicode-safe + GAL code). Lógica espelhada.
- **Duplicação de coleta metadata**: logger.\_get\_local\_ip + \_get\_ad\_user vs audit\_logger.\_get\_system\_metadata — mesma resolução socket/getpass implementada 2×.
- **Duplicação cleanup CTk**: suppress\_ctk\_errors.\_cancel\_internal\_after\_events vs gui\_utils.\_cancel\_customtkinter\_internal\_after\_events — código idêntico com diff em 1 flag.

**Bugs prováveis & fragilidades.**

1. **CRÍTICO:** csv\_safety.py deletado → 10 imports quebrados (vide A1).
1. **ALTO:** gui\_utils.py:13 importa db.db\_utils — violação de camada + risco de ciclo de import (db já depende de services/persistence/csv\_io que potencialmente depende de utils/logger).
1. **MÉDIO:** error\_handler.safe\_operation é fail-open (retorna fallback\_value por padrão sem re-raise) — usado em config/settings.py em todos os métodos críticos.
1. **MÉDIO:** audit\_logger.py:50 cria dir sem verificar permissão.

**Risco arquitetural.** **Alto pontual (csv\_safety) + Médio sistêmico (gui\_utils import + sobreposições).** Maior parte da camada é sólida e canônica; mas a deleção não-governada de csv\_safety pode quebrar runtime no próximo startup.

**Violação SDD.**

- **Materializada:** deleção de arquivo crítico sem rodada autorizada (CLAUDE.md §9: "Nao alterar arquivos fora do escopo da tarefa autorizada" — uma deleção em working tree de arquivo importado por 10 callers é alteração fora de escopo).
- safe\_operation fail-open é fragilidade arquitetural mas não viola requisito explícito.
- gui\_utils.py:13 import de db.db\_utils cria dependência circular potencial.

**Recomendação geral.** **DESBLOQUEAR csv\_safety URGENTE + AJUSTAR resto via DHPs.**

Cinco frentes priorizadas:

1. **[CRÍTICO] csv\_safety** — restaurar ou implementar substituto antes de qualquer commit/release.
1. Endurecer safe\_operation ou substituí-lo por tratamento explícito.
1. Refatorar gui\_utils.py:13 para remover import de db.db\_utils.
1. Consolidar os 3 classificadores de resultado.
1. Reduzir duplicação de metadata/cleanup entre módulos.
-----
**4. Notas 0–10**

|**Aspecto**|**Nota**|**Justificativa**|
| :- | :- | :- |
|Aderência SDD|**5**|LOG-UNIF-001, T-AUD-014, PRIV-001 cumpridos. MAS deleção de csv\_safety.py sem rodada SDD viola §9.|
|Arquitetura|**6**|Padrões corretos (CSVFileLock, RetryPolicy, secure\_path). gui\_utils:13 viola camada. Sobreposições internas.|
|Clareza e Enxutez|**7**|Maioria proporcional. gui\_utils.py (1 298 L) e io\_utils.read\_data\_with\_auto\_detection (172 L) destoam.|
|Robustez|**4**|csv\_lock + RetryPolicy + secure\_path são sólidos. MAS safe\_operation é fail-open; csv\_safety deletado quebra robustez geral.|
|Manutenibilidade|**5**|Camada bem isolada da maioria. Mas csv\_safety quebrado e duplicações (3 classificadores) elevam custo.|
|Testabilidade|**6**|LOG-UNIF tem guardiões (test\_log\_paths\_uniformization 9 passed). csv\_lock e network\_io são puros e testáveis. safe\_operation mascara falhas em testes.|
|Risco Operacional|**3**|csv\_safety quebrado é risco CRÍTICO em runtime. Demais OK.|
|Prontidão para Evolução|**5**|csv\_safety deve ser resolvido antes de qualquer evolução. Consolidação dos 3 classificadores ajudaria.|
|**Geral**|**5**|Camada **funcionalmente sólida** em pontos canônicos (LOG-UNIF, csv\_lock, network\_io) **mas com 1 bug operacional crítico** (csv\_safety deletado) e fragilidades arquiteturais (safe\_operation, gui\_utils:13). Resolver csv\_safety eleva nota para ~7.|

-----
**5. Achados detalhados**

**A. csv\_safety deletado — CRÍTICO**

[CRÍTICO] A1 — csv\_safety.py DELETADO no working tree com 10 imports runtime ativos

Evidência:

\- Git status (do contexto inicial): "D utils/csv\_safety.py"

\- Glob `utils/csv\_safety\*` retorna ZERO matches (arquivo não existe).

\- Grep `from utils.csv\_safety` / `sanitize\_csv\_value` no repo:

`  `10 arquivos com imports ativos:

`  `- autenticacao/auth\_service.py:54

`  `- services/persistence/exam\_runs\_csv.py:23

`  `- services/persistence/persistence\_facade.py:22

`  `- services/persistence/persistence\_adapters.py:55

`  `- services/analysis/full\_run\_artifact.py

`  `- services/analysis/full\_run\_status\_sync.py

`  `- services/gal/gal\_transactions.py

`  `- db/db\_utils.py

`  `- exportacao/envio\_gal.py

`  `- (1 referência em revert\_info.txt)

\- Uso confirmado de `sanitize\_csv\_value()` em:

`  `- auth\_service.py:584 (sanitizar valores em usuarios.csv)

`  `- exam\_runs\_csv.py:84 (sanitizar linhas)

`  `- persistence\_facade.py:139-141 (usuario, senha\_hash, nivel\_acesso)

`  `- persistence\_adapters.py:353, 538, 676 (atomic writes)

\- Grep `csv\_safety` em docs/specs/: ZERO matches.

`  `Nenhuma DHP, tarefa ou rodada SDD registra a deleção.

Problema:

Arquivo crítico (10 callers em runtime, incluindo auth, persistência,

GAL, db, exportação) foi deletado SEM rodada autorizada nem registro em

documentação canônica. Na primeira execução de qualquer caller:

ModuleNotFoundError: No module named 'utils.csv\_safety'.

Impacto:

\- \*\*Runtime quebra\*\* em login (auth\_service), persistência de corridas

`  `(exam\_runs\_csv), envio GAL (gal\_transactions), exportação (envio\_gal),

`  `e mais.

\- \*\*Violação CLAUDE.md §9\*\*: alteração fora de escopo autorizado.

\- \*\*Risco de perda/corrupção de dados\*\*: sanitize\_csv\_value previne CSV

`  `injection (`=`, `+`, `-`, `@` em valores). Substituir por código inline

`  `sem revisão pode reintroduzir vulnerabilidade.

Recomendação:

\*\*AÇÃO IMEDIATA\*\*:

(A) Recuperar o arquivo do histórico git (`git show HEAD:utils/csv\_safety.py

`    `> utils/csv\_safety.py`) e ABRIR DHP NOVA "destino de csv\_safety.py" para

`    `decidir formal:

`    `(A.1) MANTER em utils/ (status quo + registrar a função em docs/SDD);

`    `(A.2) MIGRAR para services/persistence/csv\_io.py com re-export shim em

`          `utils/csv\_safety.py;

`    `(A.3) DEPRECAR (exige migração dos 10 callers antes — não trivial).

(B) Adicionar guardião AST `tests/test\_utils\_csv\_safety\_exists\_or\_callers\_zero.py`

`    `que falhe se utils/csv\_safety.py for removido enquanto houver imports

`    `ativos.

NÃO COMMITAR estado atual sem resolução. Atual git working tree está

incoerente.

Teste sugerido:

1\. tests/test\_no\_broken\_csv\_safety\_imports.py — varre runtime areas,

`   `confirma que `from utils.csv\_safety` resolve OK.

2\. tests/test\_sanitize\_csv\_value\_security.py — assert que valores

`   `começando com `=`, `+`, `-`, `@`, `\t`, `\r` são prefixados com `'`

`   `(CSV injection mitigation).

**B. Fail-open & violações arquiteturais**

[ALTO] B1 — error\_handler.safe\_operation é fail-open por padrão

Evidência:

\- utils/error\_handler.py: define decorator `@safe\_operation(fallback\_value=None)`

\- Comportamento: captura `Exception`, retorna `fallback\_value` (default None),

`  `NÃO re-raise.

\- Consumidores conhecidos:

`  `- config/settings.py:69 \_carregar\_configuracoes\_padrao @safe\_operation

`  `- config/settings.py:90 \_carregar\_configuracoes\_usuario @safe\_operation

`  `- config/settings.py:182 salvar() @safe\_operation

`  `- config/settings.py:234 \_criar\_backup() @safe\_operation

`  `- utils/persistence.py: usado em 7 métodos.

Problema:

Em CAMADA DE CONFIGURAÇÃO e BACKUP, fail-open é o ANTI-PADRÃO certo de

evitar. Usuário clica "Salvar Configurações" → erro silenciado → UI

sugere sucesso → próxima sessão usa defaults sem aviso.

Impacto:

\- Backup pode falhar silenciosamente → próxima alteração sem rollback.

\- Auditoria pós-incidente difícil.

\- Reforça achado da auditoria de config/ (C2).

Recomendação:

ENDURECER em rodada de teste própria:

(A) Adicionar parâmetro `propagate\_critical=True` em pontos sensíveis;

(B) Substituir `@safe\_operation` por try/except explícito em salvar/backup;

(C) Documentar uso permitido apenas em UI / wrappers não-críticos.

NÃO IMPLEMENTAR SEM DHP coordenada com auditoria de config/ (C2 da

auditoria anterior).

Teste sugerido:

tests/test\_safe\_operation\_propagates\_critical.py — patch open()/json.dump

para raise → assert que salvar() em config retorna False ou propaga.

[ALTO] B2 — gui\_utils.py:13 importa db.db\_utils (violação de camada + risco circular)

Evidência:

\- utils/gui\_utils.py:13

`    `from db.db\_utils import salvar\_historico\_processamento

\- db/db\_utils.py importa de services.persistence.csv\_io, utils.csv\_lock,

`  `utils.csv\_safety (QUEBRADO), utils.logger, utils.network\_io.

\- utils/ não deveria importar de db/ (camada utility importando camada de

`  `dados).

Problema:

Direção de dependência invertida: utility consome adapter de dados.

Cria potencial ciclo: utils.gui\_utils → db.db\_utils → utils.csv\_lock /

utils.logger / utils.network\_io. Embora Python permita, dificulta

testes isolados e refactors.

Impacto:

\- Cada teste de gui\_utils precisa importar db (que importa pandas + outras).

\- Refactor de db.db\_utils quebra UI helpers.

\- Auditoria anterior de db/ identificou que db\_utils tem bloco PostgreSQL

`  `morto e está em DHP de destino (B1 da auditoria de db).

Recomendação:

Mover `salvar\_historico\_processamento` para `services/reports/history\_report`

(camada correta) e atualizar gui\_utils para importar de lá. Coordenar com

DHP B1 da auditoria de db.

Teste sugerido:

tests/test\_utils\_layer\_no\_db\_imports.py — guardião AST que falhe se

qualquer .py em utils/ contiver `from db.` ou `import db`.

**C. Redundância & sobreposição**

[MÉDIO] C1 — Três classificadores de resultado coexistem

Evidência:

\- utils/result\_classifier.py (55L) — classificação NUMÉRICA: ct\_alvo +

`  `ct\_rp + thresholds → "Detectado/Nao Detectado/Inconclusivo/Invalido"

\- utils/result\_normalizer.py (69L) — normalização TEXTUAL: 21 variantes

`  `→ formato canônico

\- utils/text\_result\_classifier.py (50L) — classificação TEXTUAL Unicode-safe

`  `→ "DET/ND/INC/INV" + GAL code

Problema:

Três funções com semelhança superficial e propósitos legitimamente

distintos, mas com risco de confusão e divergência. Lógica de

"resultado" não é canônica em um único módulo.

Impacto:

\- Manutenção tripla em mudança de vocabulário (ex: novo status).

\- Risco de inconsistência se um for atualizado e outro não.

\- Sobreposição confunde novos contribuidores.

Recomendação:

ABRIR DHP de consolidação:

(A) Um único módulo `utils/result\_taxonomy.py` com 3 funções claramente

`    `nomeadas (classify\_from\_ct, normalize\_label, to\_gal\_code) + um Enum

`    `canônico de resultados;

(B) Manter atual com README de "qual usar quando";

(C) Mover lógica para domain/resultado\_geral (já existe — pode absorver).

NÃO IMPLEMENTAR SEM DHP. Tocar mexe em ui\_theme + analysis\_service.

Teste sugerido:

tests/test\_resultado\_taxonomy\_consistency.py — assert que conjunto

de outputs distintos é consistente entre os 3 (mesma entrada → mesma

classe semântica).

[BAIXO] C2 — Duplicação de metadata (logger vs audit\_logger)

Evidência:

\- utils/logger.py:58-64 \_get\_ad\_user + 68-83 \_get\_local\_ip

\- utils/audit\_logger.py:74-105 \_get\_system\_metadata (mesma resolução

`  `socket + getpass + platform + python\_version)

Problema:

Mesma resolução de hostname/IP/usuário implementada 2 vezes. Mudança

em política de mascaramento (PRIV-001) exigiria tocar 2 lugares.

Impacto:

Manutenção dupla.

Recomendação:

Extrair `utils/\_metadata.py` com `get\_system\_metadata()` único, ambos

consumidores reusam.

Teste sugerido:

N/A.

[BAIXO] C3 — Duplicação de cleanup CTk (suppress\_ctk\_errors vs gui\_utils)

Evidência:

\- utils/suppress\_ctk\_errors.py:152-191 \_cancel\_internal\_after\_events

\- utils/gui\_utils.py:105-151 \_cancel\_customtkinter\_internal\_after\_events

\- Código quase idêntico (diff: flag `include\_update`).

Problema:

Mesmo padrão escrito 2 vezes. Bugfix em um não propaga ao outro.

Impacto:

Manutenção dupla.

Recomendação:

Consolidar em suppress\_ctk\_errors (módulo apropriado) e gui\_utils chama.

Teste sugerido:

N/A.

**D. Higiene & estado pendente**

[BAIXO] D1 — df\_debug.py marcado LEGADO mas mantido

Evidência:

\- utils/df\_debug.py (26 linhas) — comentário "Mantido para

`  `compatibilidade".

\- Wrapper de dataframe\_reporter.dump\_df.

Problema:

Legado documentado mas sem deadline.

Impacto:

Mínimo (26 linhas).

Recomendação:

Adicionar DeprecationWarning explícito ou DHP de cleanup.

Teste sugerido:

N/A.

[INFORMATIVO] D2 — remove\_bom.py é artefato T-AUD-014, manter

Evidência:

\- utils/remove\_bom.py (48 linhas) — utilitário para remover BOM UTF-8

`  `inicial.

\- T-AUD-014 (CLAUDE.md §10 / tasks.md:108) concluído usando este

`  `utilitário em ui/user\_management.py.

Problema:

Nenhum. Observação positiva.

Impacto:

Útil como ferramenta de manutenção pontual.

Recomendação:

Manter. Considerar adicionar guardião `tests/test\_no\_bom\_in\_runtime.py`

que falhe se algum .py em runtime tiver BOM (vide D2 da auditoria de ui/).

Teste sugerido:

N/A imediato (DHP já registrada).

[INFORMATIVO] D3 — privacy.py endereça PRIV-001 pontualmente

Evidência:

\- utils/privacy.py:1-23 mask\_patient\_name (3+ chars → "X\*\*\*Y")

\- PRIV-001 (CLAUDE.md §15.2, tasks.md:139): auditoria LGPD de banco/\* —

`  `PENDENTE.

Problema:

Função existe mas não há grep de uso amplo (subagente B não encontrou

consumidores explícitos).

Impacto:

\- Função pode ser órfã em runtime.

\- PRIV-001 amplo continua pendente.

Recomendação:

Confirmar callers reais em rodada de PRIV-001. Se zero, candidato a

arquivo órfão.

Teste sugerido:

Pré-requisito: PRIV-001 rodada própria.

**E. Pontos positivos (informativo)**

[INFORMATIVO] E1 — LOG-UNIF-001 totalmente implementado nesta camada

Evidência:

\- utils/logger.py: usa config\_service.get\_paths()["logs\_dir"]

\- utils/audit\_logger.py:29 idem

\- utils/dataframe\_reporter.py:21 idem

\- Guardião: tests/test\_log\_paths\_uniformization.py (9 passed)

Problema:

Nenhum.

Impacto:

Padrão correto a manter.

Recomendação:

N/A.

Teste sugerido:

Já existe.

[INFORMATIVO] E2 — network\_io.RetryPolicy + csv\_lock.CSVFileLock são padrões canônicos

Evidência:

\- utils/network\_io.py (212L): RetryPolicy, call\_with\_retry,

`  `open\_with\_retry (context manager), path\_exists\_with\_retry,

`  `exponential backoff com jitter.

\- utils/csv\_lock.py (86L): CSVFileLock context manager.

\- 8+ consumidores de network\_io; 12+ de csv\_lock.

Problema:

Nenhum. Observação positiva.

Impacto:

Modelos de "IO resiliente" exemplares.

Recomendação:

Manter. Citar em design.md como padrão a replicar.

Teste sugerido:

N/A.

[INFORMATIVO] E3 — secure\_path.SecurePath endereça CWE-22

Evidência:

\- utils/secure\_path.py:1-195 implementa SecurePath validator com

`  `base\_dir + allowed\_roots; SecurityError para violações.

\- Sem menção explícita em docs/SDD.

Problema:

Nenhum imediato. Observação positiva.

Impacto:

Mitigação anti-path-traversal disponível.

Recomendação:

Confirmar consumidores reais. Se órfão, documentar como utility

disponível para futuros usos.

Teste sugerido:

N/A imediato.

-----
**Consolidação dos subagentes simulados**

|**Subagente**|**Veredicto**|
| :- | :- |
|**Arquiteto SDD**|LOG-UNIF, T-AUD-014, secure\_path corretos. csv\_safety deletado sem governança é violação grave. gui\_utils:13 viola camada.|
|**Bug Hunter**|A1 (csv\_safety) é CRÍTICO operacional. B1 (safe\_operation) e B2 (gui\_utils import) são ALTOS.|
|**Código Morto / Redundância**|3 classificadores de resultado, duplicação metadata, duplicação cleanup CTk. df\_debug legado documentado.|
|**Especialista em Testes**|LOG-UNIF tem guardião. Falta: guardião csv\_safety, guardião camada utils→db, guardião taxonomia de resultado.|
|**Revisor de Enxutez**|gui\_utils.py (1 298L) é o maior. Demais proporcionais.|

**Próximas decisões humanas relevantes**

1. **CRÍTICO — sem DHP necessária** — restaurar csv\_safety.py do git history.
1. **DHP nova A1** — destino de longo prazo de csv\_safety (manter / migrar / deprecar).
1. **DHP nova B1** — endurecimento de safe\_operation (coordenar com auditoria de config/ C2).
1. **DHP nova B2** — remover import de db.db\_utils em gui\_utils.py:13 (coordenar com auditoria de db/ B1).
1. **DHP nova C1** — consolidação dos 3 classificadores de resultado.
1. **PRIV-001** (já registrada) — verificar uso real de privacy.mask\_patient\_name.

**Resumo de ações priorizadas**

1. **[CRÍTICO] A1** — restaurar csv\_safety.py IMEDIATAMENTE + DHP de destino.
1. **[ALTO] B1** — endurecer safe\_operation em config/settings.
1. **[ALTO] B2** — refatorar gui\_utils.py:13 (remove import de db.db\_utils).
1. **[MÉDIO] C1** — consolidar 3 classificadores de resultado.
1. **[BAIXO] C2/C3/D1** — cleanup de duplicações + df\_debug deprecated.
1. **[INFORMATIVO] D2/D3/E1-3** — manter padrões positivos como referência.

Nenhuma alteração foi realizada nesta rodada. **Atenção urgente:** o working tree atual está incoerente (csv\_safety deletado, callers não atualizados). Não comitar nesse estado.



