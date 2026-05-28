# Deprecacao Controlada De Equipamentos Legados

Data: 2026-05-11

## Objetivo

Registrar a transicao E07 do cadastro legado de equipamentos para a fonte canonica:

```text
config/contracts/equipment/*.json
```

## Fonte Canonica Operacional

Somente estes perfis devem participar do fluxo operacional canonico:

- `7500_Extended`
- `QuantStudio`

## Fontes Legadas Mantidas Para Rollback

As fontes abaixo nao devem ser apagadas nesta fase. Elas ficam disponiveis apenas para migracao, auditoria ou rollback documentado:

- `banco/equipamentos.csv`
- `banco/equipamentos_metadata.csv`
- `banco/profiles/equipment_profiles.json`
- built-ins de `services/equipment_registry.py`

## Marcadores De Runtime

Quando uma fonte legada for carregada, os objetos em memoria devem expor marcadores de origem:

- `legacy_equipment_csv`
- `legacy_equipment_metadata_csv`
- `legacy_equipment_profiles_json`
- `legacy_builtin_registry`

Contratos canonicos usam:

- `contracts`

## Regra Operacional

O fluxo novo de deteccao e extracao deve usar contratos JSON. Fontes legadas nao devem reativar equipamentos fora do escopo operacional.

## Rollback

Rollback e permitido apenas de forma explicita e temporaria. Nao remover arquivos legados ate concluir um ciclo de validacao com as suites de equipamentos passando.
