#!/usr/bin/env python3
"""Comando operacional para migrar credenciais legadas para usuarios.csv."""

from __future__ import annotations

import argparse
import json
import sys

from autenticacao.auth_service import AuthService


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa migracao explicita de credenciais.csv para usuarios.csv.",
    )
    parser.add_argument(
        "--usuario",
        default="",
        help="Limita a migracao para um unico usuario (opcional).",
    )
    parser.add_argument(
        "--default-access-level",
        default="DIAGNOSTICO",
        help="Nivel padrao aplicado a novos usuarios sem nivel no legado.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    service = AuthService()
    result = service.executar_migracao_credenciais_legadas(
        usuario=args.usuario or None,
        default_access_level=args.default_access_level,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("sucesso", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
