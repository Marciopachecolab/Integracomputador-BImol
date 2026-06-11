# -*- coding: utf-8 -*-
"""Guardiao: registry de equipamentos so expoe perfis ativos (FINDING-012).

design.md 3.7: apenas `7500_extended` e `quantstudio` tem `active=true` em
producao. Os arquivos `abi_7500.json` (`active=false`) e
`template_equipment_profile.json` (template, embora marcado `active=true` e com
`equipment_id=7500_extended`) NAO podem ser oferecidos como equipamento
operacional.

Mitigacoes existentes que este guardiao trava contra regressao:
  - `EquipmentProfileService._iter_profile_paths` ignora arquivos cujo nome
    comeca por `template`/`schema` (independente da flag `active`);
  - `list_active_profiles` ainda filtra por `active=true` (exclui `abi_7500`).

Nenhum arquivo e removido — apenas validacao de leitura.
"""

from application.equipment_profile_service import EquipmentProfileService


def _svc():
    return EquipmentProfileService()


def test_apenas_dois_perfis_ativos_canonicos():
    svc = _svc()
    ids = sorted(str(p.get("equipment_id", "")) for p in svc.list_active_profiles())
    # Exatamente 2 — se o template (equipment_id=7500_extended, active=true)
    # vazasse, haveria um 7500_extended duplicado (len 3).
    assert ids == ["7500_extended", "quantstudio"], (
        f"perfis ativos inesperados: {ids}"
    )


def test_inativo_abi_7500_excluido():
    svc = _svc()
    ids = {str(p.get("equipment_id", "")) for p in svc.list_active_profiles()}
    assert "abi_7500" not in ids, "perfil inativo (active=false) nao pode ser ativo"


def test_template_e_schema_excluidos_por_nome():
    svc = _svc()
    nomes = [p.name for p in svc._iter_profile_paths()]
    assert not any(n.startswith(("template", "schema")) for n in nomes), (
        f"arquivos template/schema nao podem ser enumerados como perfil: {nomes}"
    )
    # abi_7500 e enumerado (mas inativo); template nao e enumerado.
    assert "abi_7500.json" in nomes
    assert "template_equipment_profile.json" not in nomes


def test_resolve_profile_nao_resolve_inativo():
    svc = _svc()
    assert svc.resolve_profile("abi_7500") is None, (
        "equipamento inativo nao deve ser resolvido como operacional"
    )
