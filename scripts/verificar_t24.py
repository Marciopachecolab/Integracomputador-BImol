"""
Verificação T2.4 — Checar se STRANGLER_CT_DIVERGENCE apareceu no journal
após habilitar USE_DOMAIN_CT_RULES=ON (shadow read ativo).

Uso:
    python scripts/verificar_t24.py --desde <YYYY-MM-DD HH:MM:SS>
    python scripts/verificar_t24.py --desde <YYYY-MM-DD HH:MM:SS> --por-exame

    Se omitir --desde, busca em todas as linhas.

Saída:
    - 0 ocorrências → domain/ct_rules e logic_engine concordam, pronto para cutover.
    - N ocorrências → divergência detectada, investigar antes de promover.
    --por-exame    → agrupa e exibe contagem de divergências por slug de exame.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "sistema.log"
STRANGLER_CODE = "STRANGLER_CT_DIVERGENCE"

_RE_SLUG = re.compile(r"exame=([^\s]+)")


def _extrair_slug(detalhe: str) -> str:
    """Extrai o slug do exame do campo detalhe do log."""
    m = _RE_SLUG.search(detalhe)
    return m.group(1) if m else "(desconhecido)"


def verificar(desde: str | None, por_exame: bool = False) -> int:
    if not LOG_PATH.exists():
        print(f"[ERRO] Log não encontrado: {LOG_PATH}")
        return 1

    ocorrencias = []
    total = 0
    por_exame_count: dict[str, int] = defaultdict(int)

    with LOG_PATH.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.reader(fh, delimiter=";"):
            if len(row) < 8:
                continue
            total += 1
            timestamp = row[0].strip()
            error_code = row[7].strip()

            if desde and timestamp < desde:
                continue

            if error_code == STRANGLER_CODE:
                ocorrencias.append(row)
                if por_exame:
                    detalhe = row[4].strip() if len(row) > 4 else ""
                    slug = _extrair_slug(detalhe)
                    por_exame_count[slug] += 1

    print(f"Total de linhas no journal : {total}")
    if desde:
        print(f"Filtro desde              : {desde}")
    print(f"Ocorrências {STRANGLER_CODE}: {len(ocorrencias)}")

    if por_exame and por_exame_count:
        print("\n--- Divergências por exame ---")
        for slug, count in sorted(por_exame_count.items(), key=lambda x: -x[1]):
            status = "❌" if count > 0 else "✅"
            print(f"  {status} {slug}: {count}")
    elif por_exame and not por_exame_count:
        print("\n--- Divergências por exame: nenhuma ---")

    if ocorrencias:
        print("\n--- Detalhes ---")
        for r in ocorrencias:
            print(f"  {r[0]} | ação={r[3]} | detalhe={r[4]}")
        print("\n[RESULTADO] ❌ Divergência detectada. NÃO fazer cutover — investigar.")
        return 2

    print("\n[RESULTADO] ✅ Nenhum STRANGLER_CT_DIVERGENCE. Pronto para cutover (T2.4).")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Verificação T2.4")
    parser.add_argument(
        "--desde",
        metavar="YYYY-MM-DD HH:MM:SS",
        help="Timestamp de início da janela de busca (início do período shadow)",
        default=None,
    )
    parser.add_argument(
        "--por-exame",
        action="store_true",
        help="Agrupa e exibe divergências por slug de exame",
        dest="por_exame",
    )
    args = parser.parse_args()
    sys.exit(verificar(args.desde, por_exame=args.por_exame))


if __name__ == "__main__":
    main()
