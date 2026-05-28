# Plano SDD - Cadastro Canonico de Equipamentos

## 1. Objetivo

Consolidar toda a configuracao de equipamentos de analise em um cadastro tecnico unico, editavel pela UI, usado para deteccao do equipamento, leitura correta do arquivo de resultados e selecao da estrategia de extracao.

O plano deve manter somente dois equipamentos operacionais:

- `7500_Extended`
- `QuantStudio`

Aliases obrigatorios de `QuantStudio`:

- `QuantStudio`
- `QuantStudio 5`
- `QuantStudio 6`

Todos os aliases devem resolver para o mesmo `equipment_id` canonico.

## 2. Decisoes Confirmadas

- O usuario que edita cadastro tecnico de equipamento precisa ter perfil `ADMIN` ou `MASTER`.
- A UI pode salvar diretamente em `config/contracts/equipment/*.json`.
- Fixture real para `7500_Extended`:
  - `C:\Users\marci\Downloads\18 JULHO 2025\20250718 VR1-VR2 BIOM PLACA 5.xlsx`
- Fixture real para `QuantStudio`:
  - `C:\Users\marci\Downloads\18 JULHO 2025\20250924 VR1_VR2 BIOM PLACA 01_Results_20260220 173647.xlsx`
- Equipamentos fora de escopo (`7500`, `CFX96`, `CFX96_Export` e outros) nao devem ficar ativos no fluxo operacional.

## 3. Estado Atual Resumido

Hoje a configuracao de equipamentos esta fragmentada:

- `services/equipment_detector.py`: contem padroes hardcoded de deteccao.
- `services/equipment_registry.py`: carrega CSV, built-ins e contratos.
- `services/equipment_extractors.py`: contem extratores por nome/estrategia.
- `services/engine/config_loader.py`: le `banco/profiles/equipment_profiles.json`.
- `services/contract_catalog.py`: ja possui mecanismo de contratos para equipment profiles.
- `banco/equipamentos.csv`: cadastro simples com `nome`, `modelo`, `fabricante`, `observacoes`.
- `banco/equipamentos_metadata.csv`: metadados de leitura duplicados em CSV.
- `config/contracts/equipment/*.json`: melhor candidato para fonte canonica.

Problema principal: nao ha uma unica fonte de verdade para detectar, validar, extrair e administrar equipamentos.

## 4. Fonte Canonica Proposta

A fonte canonica deve ser:

```text
config/contracts/equipment/*.json
```

Arquivos esperados:

```text
config/contracts/equipment/7500_extended.json
config/contracts/equipment/quantstudio.json
```

O `ContractCatalog` deve ser o ponto de leitura dos perfis. A UI deve editar esses arquivos por meio de uma camada de aplicacao/servico, sem escrever JSON diretamente a partir de callbacks de tela.

## 5. Contrato Tecnico Minimo

Cada `EquipmentProfile` deve conter:

- `equipment_id`: identificador canonico estavel.
- `display_name`: nome exibido ao usuario.
- `aliases`: nomes alternativos aceitos na UI/deteccao.
- `active`: booleano operacional.
- `contract_version`: versao do perfil.
- `fabricante`: fabricante do equipamento.
- `modelo`: modelo comercial.
- `file_type`: extensoes aceitas (`xlsx`, `xls`, `xlsm`).
- `signature`: assinatura para deteccao.
- `sheet_policy`: aba alvo, abas ignoradas e estrategia de selecao.
- `row_policy`: linha de header, linha inicial de dados e estrategia de busca.
- `column_mapping`: colunas canonicas (`well`, `sample`, `target`, `ct`).
- `ct_policy`: aliases de CT, blocklist, valores nulos e separador decimal.
- `well_policy`: formato esperado (`A1` ou `A01`) e normalizacao.
- `extractor_strategy`: estrategia de extracao (`indexed_table`, `quantstudio_table`, etc.).
- `confidence_threshold`: score minimo para auto-deteccao.
- `validation_rules`: colunas obrigatorias, minimo de linhas e erros bloqueantes.
- `audit`: `updated_at`, `updated_by`, `change_reason`.

## 6. Fases De Implementacao

### Fase 0 - Baseline e Congelamento

Objetivo: garantir que o comportamento atual seja mensuravel antes de qualquer troca.

Acoes:

- Criar testes de baseline com os dois fixtures reais.
- Registrar resultado atual de deteccao para cada fixture.
- Registrar shape e colunas do DataFrame extraido.
- Confirmar que somente `7500_Extended` e `QuantStudio` serao considerados ativos.

Riscos:

- Fixtures podem estar fora do workspace ou indisponiveis no ambiente de teste.
- Arquivos reais podem conter dados sensiveis.

Mitigacoes:

- Testes devem pular com mensagem clara se o arquivo real nao existir.
- Criar fixtures anonimizadas/minimas depois que o baseline real estiver validado.
- Nunca versionar os arquivos reais no repositorio.

Criterios de aceite:

- Baseline de `7500_Extended` passa com o arquivo real informado.
- Baseline de `QuantStudio` passa com o arquivo real informado.
- Falta de fixture gera skip explicito, nao falha opaca.

### Fase 1 - Especificacao e Contrato

Objetivo: formalizar o cadastro canonico antes de mudar runtime.

Acoes:

- Atualizar `schema.equipment_profile.json` com todos os campos minimos.
- Criar `7500_extended.json`.
- Criar `quantstudio.json`.
- Cadastrar aliases de QuantStudio no perfil `quantstudio`.
- Definir `active=true` somente para os dois perfis.

Riscos:

- Schema incompleto pode forcar nova migracao logo em seguida.
- Divergencia entre nomes usados por UI, detector e extrator.

Mitigacoes:

- Validar contrato contra os dois fixtures.
- Criar teste de resolucao de alias.
- Usar `equipment_id` como chave tecnica, nunca `display_name`.

Criterios de aceite:

- `ContractCatalog` carrega os dois perfis.
- `QuantStudio`, `QuantStudio 5` e `QuantStudio 6` resolvem para o mesmo `equipment_id`.
- Nenhum outro equipamento aparece como ativo.

### Fase 2 - Facade Canonica de Equipamentos

Objetivo: criar um ponto unico para a aplicacao consumir equipamentos.

Acoes:

- Criar uma facade em `application/`, por exemplo `equipment_profile_service.py`.
- Expor operacoes:
  - `list_active_profiles()`
  - `resolve_profile(equipment_id_or_alias)`
  - `detect_equipment(file_path)`
  - `extract_results(file_path, profile)`
  - `validate_profile(profile)`
  - `save_profile(profile, actor)`
- A facade deve usar contratos como fonte primaria.
- Manter fallback legado atras de flag/rollback.

Riscos:

- Acoplamento com `services/equipment_registry.py` e `services/equipment_detector.py`.
- Duplicidade temporaria durante a migracao.

Mitigacoes:

- Nao remover APIs antigas nesta fase.
- Criar testes de compatibilidade para chamadas atuais.
- Logar quando fallback legado for usado.

Criterios de aceite:

- UI e services conseguem listar somente perfis ativos pela facade.
- Resolucao por alias funciona.
- Perfis invalidos sao rejeitados antes da escrita.

### Fase 3 - Detector Profile-Driven

Objetivo: substituir padroes hardcoded por deteccao baseada no cadastro canonico.

Acoes:

- Fazer o detector calcular score a partir de `signature`, `row_policy`, `column_mapping`, `well_policy` e `validation_rules`.
- Restringir candidatos a perfis `active=true`.
- Retornar alternativas com score.
- Manter erro claro quando a confianca ficar abaixo do minimo.

Riscos:

- Detector novo pode escolher equipamento errado.
- Arquivos com metadados incompletos podem perder score.

Mitigacoes:

- Rodar em shadow mode comparando detector antigo x novo.
- Exigir confirmacao do usuario quando score for baixo ou houver empate.
- Registrar headers detectados e motivo do score.

Criterios de aceite:

- Fixture `7500_Extended` detecta `7500_Extended`.
- Fixture `QuantStudio` detecta `quantstudio`.
- Equipamentos fora de escopo nao sao retornados como candidatos ativos.

### Fase 4 - Extracao Por Contrato

Objetivo: usar o mesmo perfil detectado para ler corretamente o arquivo.

Acoes:

- Mapear `extractor_strategy` para extratores existentes.
- Manter estrategia dedicada para `7500_Extended`.
- Manter estrategia dedicada para `QuantStudio`.
- Normalizar saida para colunas canonicas:
  - `bem`
  - `amostra`
  - `alvo`
  - `ct`
- Bloquear equipamento inativo antes de IO de analise.

Riscos:

- Mudanca de coluna CT pode alterar resultado da analise.
- QuantStudio pode ter variacoes de header entre versoes.

Mitigacoes:

- Testes com fixtures reais.
- Validar contagem minima de linhas extraidas.
- Validar amostras de wells e alvos esperados.
- Manter rollback para extratores legados.

Criterios de aceite:

- Os dois fixtures geram DataFrame canonico nao vazio.
- CTs numericos e vazios sao tratados conforme `ct_policy`.
- Wells sao normalizados de forma consistente.

### Fase 5 - Cadastro Tecnico Editavel Pela UI

Objetivo: permitir que `ADMIN` e `MASTER` editem o cadastro tecnico completo.

Acoes:

- Substituir/expandir aba Equipamentos em `services/cadastros_diversos.py`.
- Campos obrigatorios:
  - identidade e aliases;
  - assinatura de deteccao;
  - mapeamento de colunas;
  - politica de CT;
  - politica de poços;
  - estrategia de extracao;
  - status ativo/inativo.
- Validar perfil antes de salvar.
- Salvar diretamente em `config/contracts/equipment/*.json`.
- Criar backup automatico antes de sobrescrever JSON.
- Exigir perfil `ADMIN` ou `MASTER`.
- Adicionar botao "Testar com arquivo" para validar deteccao/extracao.

Riscos:

- Usuario pode salvar JSON invalido e quebrar deteccao.
- Edicao simultanea em ambiente multiusuario pode sobrescrever alteracoes.
- Tela pode ficar complexa demais.

Mitigacoes:

- Escrita atomica com backup.
- Validacao contra schema antes de salvar.
- File lock durante escrita.
- UI em seco: validar e mostrar diff antes de confirmar.
- Campos avancados agrupados em secoes.

Criterios de aceite:

- Usuario sem `ADMIN`/`MASTER` nao consegue salvar.
- JSON invalido nao e gravado.
- Backup e criado antes da escrita.
- Botao de teste valida os dois fixtures.

### Fase 6 - Integracao UI Com Deteccao Automatica

Objetivo: usar deteccao automatica no fluxo operacional com confirmacao.

Acoes:

- Reativar fluxo automatico em `ui/menu_handler.py`.
- Armazenar caminho do arquivo de resultados no estado da aplicacao.
- Exibir equipamento detectado, score e alternativas.
- Permitir confirmacao manual apenas entre `7500_Extended` e `QuantStudio`.

Riscos:

- Fluxo atual pode depender de selecao manual.
- Arquivo de resultado pode nao estar disponivel no momento da deteccao.

Mitigacoes:

- Fallback manual restrito aos dois ativos.
- Mensagem clara quando o arquivo nao puder ser lido.
- Nao seguir para analise sem equipamento resolvido.

Criterios de aceite:

- Fluxo detecta equipamento automaticamente quando arquivo existe.
- Usuario pode confirmar ou trocar para outro equipamento ativo.
- Falha de deteccao nao causa crash.

### Fase 7 - Descontinuacao Controlada Do Legado

Objetivo: remover dependencia operacional das fontes antigas.

Acoes:

- Marcar como legado:
  - `banco/equipamentos.csv`
  - `banco/equipamentos_metadata.csv`
  - `banco/profiles/equipment_profiles.json`
  - `services/engine/config_loader.py` para equipamentos
  - built-ins em `services/equipment_registry.py`
  - hardcoded em `services/equipment_detector.py`
- Manter leitura apenas para migracao/rollback por um ciclo.
- Atualizar docs de operacao.

Riscos:

- Algum fluxo secundario ainda pode ler arquivos legados.
- Testes antigos podem esperar equipamentos fora de escopo.

Mitigacoes:

- Usar `rg` para mapear chamadas remanescentes antes da remocao.
- Criar warnings e telemetria antes de excluir.
- Ajustar testes para escopo ativo.

Criterios de aceite:

- Runtime principal usa somente contratos.
- Fontes legadas nao reativam equipamentos fora de escopo.
- Rollback documentado e testado.

## 7. Testes Minimos

Executar por fase:

```powershell
python -m pytest tests/test_equipment_detector.py -q --tb=short
python -m pytest tests/test_equipment_registry.py tests/test_phase1_equipment_registry_contract_precedence.py -q --tb=short
python -m pytest tests/test_equipment_extractors.py tests/test_phase2_equipment_extraction_port.py -q --tb=short
```

Adicionar testes novos para:

- schema dos dois perfis canonicos;
- aliases de `QuantStudio`;
- bloqueio de equipamentos fora de escopo;
- deteccao com os dois fixtures reais;
- extracao canonica com os dois fixtures reais;
- permissao `ADMIN`/`MASTER` na UI;
- backup e validacao antes de salvar JSON.

## 8. Rollback

Cada fase deve manter rollback simples:

- Fases 1-2: remover novos perfis/facade e voltar ao registry atual.
- Fase 3: flag para detector antigo.
- Fase 4: flag para extrator legado.
- Fase 5: restaurar backup JSON anterior.
- Fase 6: voltar para selecao manual.
- Fase 7: nao remover arquivos legados ate concluir um ciclo de validacao.

## 9. Ordem Recomendada De Execucao

1. Baseline com fixtures reais.
2. Schema e perfis canonicos.
3. Facade canonica.
4. Detector por contrato em shadow mode.
5. Extracao por contrato.
6. Cadastro tecnico editavel pela UI.
7. Reativacao da deteccao automatica.
8. Descontinuacao controlada do legado.

Essa ordem reduz risco porque nenhuma fase critica substitui o runtime sem teste e sem rollback.
