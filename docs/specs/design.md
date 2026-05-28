# Design - SDD Fonte Unica

## 1. Arquitetura em camadas
- `ui/`: telas, eventos e dialogs.
- `application/`: use cases e contratos de orquestracao.
- `domain/`: regras puras (CT, mapeamento, prioridades).
- `services/` e `exportacao/`: adaptadores de infraestrutura.

Regra: comportamento clinico e operacional nao pode ficar duplicado em telas.

## 2. Stack
- Python 3.x
- CustomTkinter/Tkinter
- Pandas/OpenPyXL
- Selenium + seleniumrequests
- CSV/JSON + SQLite-first
- Pytest

## 3. Modulos chave

### 3.1 Analise
- `services.analysis_service`: pipeline de ingestao, classificacao e resultado geral.
- `services.analysis_runtime_contract`: resolve limite de CT por exame/alvo.
- `domain.ct_rules` e `domain.ct_rules_runtime`: regra canonica de classificacao.

### 3.2 Mapeamento
- `application.extraction_plate_mapping_use_case`: calculo puro para preview e retorno.
- `ui/modules/extraction_plate_mapping.py`: visualizacao e confirmacao. Encapsula `ExtractionUseCase` e `TkFileChooser`.
- `ui/menu_handler.py::abrir_busca_extracao`: delega para `abrir_mapeamento_extracao` (T06 promovido; padrao strangler removido).

### 3.3 Cadastro/edicao de exame
- `ui/modules/exam_creator/wizard.py`: entrada item 7 (incluir/editar).
- `services.cadastros_diversos.ExamFormDialog`: formulario completo de edicao.
- `services.exam_registry`: fonte de configuracao ativa.

### 3.4 Compartilhamento multiusuario
- `services.config_service.configure_shared_storage`: padroniza `data_root/allowed_roots`.
- `services.installation_checks`: valida path, CSV e ACL do compartilhamento.
- Auditoria READ-ONLY de 2026-05-15: classificacao multiusuario **APTO COM RESTRICOES**. Decisao humana posterior definiu implantacao inicial em piloto controlado com 3 a 5 usuarios. O desenho atual nao comprova aptidao plena para 10 usuarios sem backlog CONC adicional.

### 3.5 Envio GAL
- `application.gal_send_use_case`: executa loop de envio com verificacao de dupla chave antes de cada envio e persistencia imediata apos sucesso.
- `exportacao.envio_gal`
- `services.gal_transactions`: `build_idempotency_key`, `load_successful_idempotency_keys`, `append_transaction_journal_unique`.
- Risco de concorrencia documentado em 2026-05-15: a idempotencia dual-key reduz duplicidade em fluxo sequencial, mas ainda exige CONC-003 para claim/lease antes do envio externo quando houver concorrencia real entre estacoes.

### 3.6 Escopo de exames
Guard de runtime opera em dois modos claramente distintos:
- **Registry carregado em runtime real**: `services.exam_registry.is_active(nome)` consulta a lista `active_exams` configurada. Se a lista existir e o exame nao constar, `_analisar_corrida_pipeline()` levanta `domain.exam_scope.ExamForaDoEscopoError` antes de qualquer IO de analise (fail-closed). `active_exams` vazio em registry carregado bloqueia todos os exames.
- **Stubs de teste sem configuracao**: por contrato canonico, `is_active()` pode retornar `True` incondicionalmente para preservar suites que nao configuram `active_exams`. Esse comportamento e exclusivo do contexto de teste e nao afeta o fail-closed do registry real.

Componentes:
- `services.exam_registry`: `is_active(nome)` e `iter_active_exams()` — fonte canonica de consulta de escopo.
- `domain.exam_scope.ExamForaDoEscopoError`: excecao de dominio puro lancada pelo guard em `_analisar_corrida_pipeline()` quando o exame nao esta na lista `active_exams`.

Rastreabilidade: `requirements.md §8` CA-09 e CA-10; auditoria D-12.

### 3.7 Cadastro tecnico de equipamentos (SDD Fases 0-7 concluidas — ver tasks.md §7)
Fonte canonica unica para configuracao de equipamentos de PCR, substituindo CSV/JSON/builtins legados.

- `config/contracts/equipment/*.json`: um arquivo por equipamento ativo. Apenas `7500_extended.json` e `quantstudio.json` tem `active=true` em producao.
- `application.equipment_profile_service.EquipmentProfileService`: facade canonica. Expoe `list_active_profiles()`, `resolve_profile(alias)`, `detect_equipment(path)`, `validate_profile(profile)`, `save_profile(profile, actor)`. Escrita restrita a perfis ADMIN/MASTER.
- `services.contract_catalog.ContractCatalog.list_equipment_profiles()`: ponto de leitura dos perfis; respeita hierarquia `contracts > config_json > csv`.
- `services.equipment_detector.detectar_equipamento()`: detecta equipamento a partir de arquivo XLSX. Detector profile-driven com shadow legacy anexado/logado em divergencia (E05).
- `services/cadastros_diversos.py` (aba Equipamentos): UI de edicao tecnica completa — todos os campos do contrato sao editaveis, incluindo `signature`, `sheet_policy`, `row_policy`, `column_mapping`, `ct_policy` completo, `well_policy`, `extractor_strategy`, `validation_rules`. Escrita via `save_profile()` com backup atomico.

**Contrato minimo de perfil (`equipment_id`, `display_name`, `aliases`, `active`, `signature`, `sheet_policy`, `row_policy`, `column_mapping`, `ct_policy`, `well_policy`, `extractor_strategy`, `confidence_threshold`, `validation_rules`, `audit`).**

**Estado das fases (referencia `tasks.md §7` — E01..E07 `[Concluido]` em 2026-05-11):**
- Fase 0 (Baseline com fixtures reais), Fase 1 (Contratos JSON canonicos + aliases), Fase 2 (Facade `EquipmentProfileService`), Fase 3 (Detector profile-driven com shadow legacy), Fase 4 (Extracao por contrato sem fallback legado silencioso), Fase 5 parcial (UI tecnica completa), Fase 6 (Integracao UI com deteccao automatica) e Fase 7 (Deprecacao controlada) estao todas marcadas concluidas em `tasks.md`.
- **Decisao operacional sobre legado** (E07): conforme `docs/specs/equipment_legacy_deprecation.md`, `banco/equipamentos.csv`, `banco/equipamentos_metadata.csv`, `banco/profiles/equipment_profiles.json` e built-ins de `services/equipment_registry.py` permanecem **fisicamente presentes** para rollback controlado, com marcadores de origem em runtime (`legacy_equipment_csv`, `legacy_equipment_metadata_csv`, `legacy_equipment_profiles_json`, `legacy_builtin_registry`). **Remocao fisica nao foi executada nesta rodada e depende de DEC-002** (ver `requirements.md §10`).
- Documentacao auxiliar canonica:
  - `docs/specs/plano_equipamentos_sdd.md` — plano original das fases (referencia historica/canonica).
  - `docs/specs/equipment_legacy_deprecation.md` — decisao operacional E07.

Sem dividas residuais de fase aberta. Pendencias documentais e de codigo agregadas em `tasks.md §10`.

Rastreabilidade: auditoria D-03, D-10, D-11.

### 3.8 Modulo de relatorios
Modulo somente leitura para consultas gerenciais e operacionais sobre analises, execucoes e envio ao GAL.

- `application.reports_query_use_case` (novo): orquestra filtros, validacoes de escopo e composicao dos dados sem depender de UI.
- `application.reports_contracts` (novo): DTOs de filtro e retorno para resumo, series temporais, agrupamentos e linhas detalhadas.
- `services.reports_repository` (novo): consultas SQLite-first sobre `historico_analises` e `exam_runs`, com fallback controlado para CSV quando o provider atual estiver em modo legado.
- `services.gal_transactions`: fonte auxiliar para reconciliar status GAL por chave normalizada e diferenciar enviado, pendente, erro e duplicado.
- `ui/modules/reports.py` (novo): tela de filtros, visualizacao tabular/agregada e exportacao. Nao deve calcular classificacao clinica nem prioridade de `Resultado_geral`.

O modulo deve tratar equipamentos apenas como metadado opcional de auditoria. Relatorios operacionais devem priorizar exame, periodo, analista, kit/lote, positividade e status GAL.

### 3.9 Padronizacao Visual e Sistema de Design (UI)
O sistema adota um Design System centralizado inspirado em interfaces web institucionais, implementado via `CustomTkinter` para garantir alta performance sem dependência de navegadores.

- **Fundações:** 
  - Fundo principal: Cinza claro (`#F4F6FA`).
  - Cards e Paineis: Branco (`#FFFFFF`) com borda solida de separacao (`#E2E8F0`), evitando o uso de sombras complexas (que degradam performance no Tkinter).
  - Acoes Primarias: Azul institucional (`#1A56DB`).
- **Estados Clinicos e Cores Canonicas:**
  - `Não Detectável` / Sucesso: Verde (`#16A34A`).
  - `Indeterminado` / Aviso: Amarelo/Laranja (`#CA8A04`).
  - `Detectável` / Inválido / Falha: Vermelho (`#DC2626`).
- **Arquitetura UI:** 
  - Paradigma de Navegacao: "Janela Unica" (Single Window Context). Uso de MainFrame com Sidebars ao inves da criacao de Toplevels multiplos.
  - Componentes basicos (Botoes, Entradas, Badges, Cards) devem ser isolados em classes reutilizaveis dentro de `ui/components/`. 
  - A UI apenas reflete as regras de dominio (DTOs de entrada), sendo estritamente proibido duplicar lógicas clínicas em eventos de tela.

## 4. Contratos obrigatorios

### 4.1 Retorno de mapeamento
```python
{
  "mapeamento": DataFrame,
  "parte": int,
  "numero_extracao": str,
  "caminho_arquivo": str,
}
```

### 4.2 Profile de CT por exame/alvo
```python
{
  "default_rule": {...},
  "by_target": {"ALVO": {...}},
  "rp_min": float,
  "rp_max": float,
}
```

### 4.3 Chave de idempotencia GAL
Esquema dual (ambas verificadas antes do envio; ambas adicionadas ao conjunto em memoria apos sucesso):
- **Chave legada (4 campos)**: `codigo_amostra|kit|lote_kit|data_exame`
- **Chave com escopo (4+N campos)**: `codigo_amostra|kit|lote_kit|data_exame|campo=valor...`

Somente linhas com `status=sucesso` no journal bloqueiam reenvio. `status=erro` e `status=duplicado` permitem retry.
Dedup intra-batch via conjunto em memoria (`successful_keys`) — sem acesso adicional ao journal por linha.

### 4.4 Consulta de relatorios
Contrato de entrada minimo:
```python
{
  "data_inicio": "YYYY-MM-DD",
  "data_fim": "YYYY-MM-DD",
  "exames": ["VR1e2 Biomanguinhos 7500", "ZDC BioManguinhos"],
  "status_realizacao": ["realizado", "a_realizar"],
  "positividade": ["positivo", "negativo", "inconclusivo", "invalido"],
  "analistas": ["usuario"],
  "kits": ["kit"],
  "lotes": ["lote"],
  "status_gal": ["enviado", "nao_enviado", "erro", "duplicado"],
  "agrupar_por": ["periodo", "exame", "positividade", "analista", "kit", "status_gal"],
  "limit": 500,
  "offset": 0,
}
```

Contrato de saida minimo:
```python
{
  "resumo": {...},
  "agrupamentos": [
    {"chaves": {...}, "total": 0, "positivos": 0, "negativos": 0, "pendentes_gal": 0}
  ],
  "detalhes": [
    {
      "corrida_id": "...",
      "amostra_codigo": "...",
      "exame": "...",
      "data_exame": "YYYY-MM-DD",
      "analista": "...",
      "kit": "...",
      "lote": "...",
      "resultado_geral": "...",
      "status_gal": "enviado|nao_enviado|erro|duplicado",
    }
  ],
  "paginacao": {"limit": 500, "offset": 0, "total_estimado": 0},
}
```

Filtros de exame devem respeitar `ExamRegistry.active_exams`. Exame fora de escopo deve falhar antes de qualquer leitura pesada ou exportacao.

## 5. Fluxos

### 5.1 Fluxo de analise
1. Selecionar exame + arquivo de corrida + contexto de extracao.
2. Classificar alvos por CT.
3. Consolidar `Resultado_geral`.
4. Mostrar tabela e cores/tags.
5. Permitir ajuste de mapa e sincronizar tabela.

### 5.2 Fluxo item 7 (incluir/editar)
1. Abrir modulo maximizado.
2. Exibir lista rolavel de exames cadastrados.
3. Selecionar exame e abrir formulario completo de edicao.
4. Salvar em registry e recarregar catalogo.

### 5.3 Fluxo de compartilhamento
1. ADMIN ou MASTER define compartilhamento unico no modulo de instalacao inicial, com confirmacao forte antes de aplicar configuracao e registro em log/auditoria.
2. Sistema aplica `data_root` e `allowed_roots` unificados.
3. Checklist valida ACL leitura/escrita.
4. Antes de uso produtivo irrestrito, instalacao deve cobrir backlog INST: lock/atomic write de `config.json`, dry-run, backup/rollback, ajuste ADMIN+MASTER conforme DEC-010 e teste end-to-end do wizard.

### 5.4 Fluxo de relatorios
1. Usuario abre o modulo de relatorios.
2. Sistema carrega opcoes de filtros a partir de fontes canonicas e do escopo ativo.
3. Usuario informa periodo e filtros opcionais.
4. Use case valida escopo e normaliza filtros.
5. Repositorio executa consultas SQLite-first e reconcilia status GAL pelo journal.
6. UI exibe resumo, agrupamentos e detalhes paginados.
7. Usuario exporta CSV/XLSX com metadados dos filtros aplicados quando necessario.

## 6. Restricoes
- Somente dois exames ativos em producao.
- Postgres dedicado nao deve ser usado (provider nao implementado).
- Mudanca critica sem teste de regressao e proibida.
- Quebra de schema CSV exige migracao explicita.
- Relatorios nao podem recalcular classificacao de CT nem duplicar prioridade de `Resultado_geral`; devem consumir resultados persistidos.
- Consultas de relatorio devem ser somente leitura e nao podem acionar IO de analise, envio GAL ou alteracao de historico.

## 7. Diretriz de testes
Executar pelo menos:
```powershell
python -m pytest tests/test_ct_classification.py tests/test_vr1_vr2_inconclusivo_runtime.py -q --tb=short
python -m pytest tests/test_analysis_service_phase6_vectorization.py tests/test_classificacao_cores_caracterizacao_h03.py -q --tb=short
python -m pytest tests/test_extraction_plate_mapping_use_case.py tests/test_mapeamento_extracao_caracterizacao_h04.py -q --tb=short
python -m pytest tests/test_0260325_exam_creator_registry_rollout.py tests/test_shared_storage_standardization.py -q --tb=short
```

## 8. Dividas tecnicas documentadas
Achados estruturais identificados na auditoria SDD 2026-05-12 (READ-ONLY). Esta secao registra dividas para tratamento em rodadas proprias de codigo.

- **DT-001 (D-01) - RESOLVIDA**: `domain/ct_rules.py` nao importa mais `pandas` e nao usa mais `pd.isna`. A regra de CT passou a usar checagem nativa com `math.isnan`, mantendo `domain/` livre de dependencias pesadas de infraestrutura. Evidencias registradas em `tasks.md`: T-AUD-008 (`tests/test_domain_pure_imports.py`) e T-AUD-001 concluidas; recorte CT validado. Nova orientacao: nao reintroduzir `pandas`, UI, Selenium ou dependencias equivalentes em `domain/`.
- **DT-002 (R-T3)**: `services/` concentra dezenas de modulos e arquivos individuais grandes (`cadastros_diversos.py`, `analysis_service.py`). Alto custo cognitivo, sem violacao funcional. Tratamento: inventario para futuro split por subdominio (analysis/, equipment/, gal/, reports/, persistence/). Refatoracao ampla NAO esta autorizada nesta rodada. Tarefa: T-AUD-010.
- **DT-003 (D-04)**: `core/authentication/user_manager.py` (~1900 LOC) coexiste com `autenticacao/auth_service.py`. Nao caracterizado como dead code sem verificacao de callers. Tratamento: auditar callers reais e decidir consolidacao ou deprecacao. Tarefa: T-AUD-004 / T-AUD-013.

## 9. Limitacoes conhecidas
- **LIM-001 (D-02 / DEC-001)**: `config.json` versionado nao esta pronto para producao — `shared_storage.required=true` com `data_root=""` e `allowed_roots=[]`. Instalacao Inicial (T11) e obrigatoria antes do primeiro uso. Ver `requirements.md §7.1` e CA-12.
- **LIM-002 (D-08) - RESOLVIDA COMO CORRECAO FORMAL, MANTIDA COMO LIMITACAO OPERACIONAL**: T-AUD-008-CFG removeu a chave literal vazia `""` e corrigiu o mojibake de `lab_responsible` sem inserir dados reais sensiveis. `config.json` permanece template/local runtime nao pronto para producao; `shared_storage.root`, `data_root` e `allowed_roots` seguem vazios ate a Instalacao Inicial/configuracao local validada.
- **LIM-003 (D-11)**: arquivos legados em `banco/*` (`equipamentos.csv`, `equipamentos_metadata.csv`, `profiles/equipment_profiles.json`) permanecem fisicamente presentes apos E07. Remocao depende de DEC-002. Fallback documentado em `equipment_legacy_deprecation.md`.
- **LIM-004 (2026-05-15)**: capacidade para 10 usuarios simultaneos nao comprovada. Estado atual: APTO COM RESTRICOES; implantacao inicial aprovada como piloto controlado com 3 a 5 usuarios. CONC-002, CONC-003 e INST-001 sao prioritarias antes de ampliar para 10 usuarios.
- **LIM-005 (2026-05-15)**: modulo de Instalacao Inicial funcional com restricoes. Falta lock/atomicidade de `config.json`, dry-run, rollback, ajuste ADMIN+MASTER conforme DEC-010 e teste end-to-end do wizard.

## 10. Pendencias documentais e decisoes humanas
Consolidadas em `tasks.md` (tarefas T-AUD, SDD-20260514, UI-AUD e HIG). Referencia cruzada para `requirements.md` (DEC-001 a DEC-007). Nenhuma decisao humana pendente foi resolvida na sincronizacao de 2026-05-14; permanecem pendentes DHP-02/DHP-09, DHP-04, DHP-05 e DHP-07.

## 11. Atualizacoes de desenho registradas em 2026-05-14

Estas regras refletem comportamento ja implementado e documentado para evitar que agentes reabram diagnosticos concluidos antes da auditoria de higienizacao.

- **Relatorio final pre-GAL**: analise concluida com envio GAL ainda nao executado e estado operacional valido. Deve ser registrada como `status_execucao=analise_concluida_envio_pendente`, `status_envio_gal=pendente_envio` e `status_item=selecionado_pendente_envio`, nao como falha de analise.
- **Completude VR1e2 com placa cheia**: para contrato VR1e2 com 96 pocos e agrupamento de 2 pocos/amostra, a saida esperada e 48 grupos. Perda de grupos por mapeamento/gabarito ausente ou malformado deve falhar fail-closed com erro claro (`AnalysisCompletenessError`) antes de relatorio parcial.
- **Extrator por contrato**: saidas com aliases contratuais (`bem`, `amostra`, `alvo`, `ct`) devem ser normalizadas para o vocabulario esperado pelo pipeline (`Well`, `Sample`, `Target`, `Ct`) antes da identificacao de colunas PCR.
- **Tela de Analise / Reaplicar Selecao**: a selecao automatica deve depender das colunas ja calculadas de aptidao operacional: `Sugestao_de_repeticao=Nao`, `Res_RP_1=Valido`, `Res_RP_2=Valido`, `Status_Placa=Valida`, excluindo CN, CP e controles.
- **UI-AUD e HIG**: inventario UI, plano de modernizacao UI e auditoria de higienizacao seguem pendentes; esta secao nao autoriza execucao de limpeza, remocao, migracao ou refatoracao.

## 12. Atualizacoes de desenho registradas em 2026-05-15

Estas regras registram a auditoria READ-ONLY de capacidade multiusuario e modulo de instalacao. Nao autorizam alteracao de codigo, `config.json`, banco, scripts, limpeza ou GAL real.

- **Multiusuario**: classificacao operacional atual = `APTO COM RESTRICOES`. Decisao humana registrada: implantacao inicial em piloto controlado com 3 a 5 usuarios.
- **Instalacao Inicial**: classificacao operacional atual = `FUNCIONAL COM RESTRICOES`. O modulo existe, mas precisa do backlog INST antes de uso produtivo irrestrito.
- **Meta condicionada**: 10 usuarios simultaneos depende da conclusao dos testes CONC e correcoes prioritarias.
- **Prioridade antes de ampliar para 10 usuarios**: CONC-002 (teste multiprocess 10 usuarios em CSVs criticos), CONC-003 (claim/lease GAL antes do envio) e INST-001 (lock/atomic write para `config.json`).
- **Decisao registrada em DEC-010**: Instalacao Inicial deve ser acessivel por ADMIN e MASTER, desde que protegida por confirmacao forte, log/auditoria e, futuramente, backup previo. INST-004 permanece pendente para ajuste de UI/codigo em rodada propria caso a aba ainda restrinja acesso apenas a ADMIN.
