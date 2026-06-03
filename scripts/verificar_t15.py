"""
Verificação T1.5 — Checar se STRANGLER_EXTRACTION_LEGACY apareceu no journal
após a corrida real com USE_EXTRACTION_PORT_ROUTING=ON.

Uso:
    python scripts/verificar_t15.py --desde <YYYY-MM-DD HH:MM:SS>

    Se omitir --desde, busca em todas as linhas.

Saída:
    - 0 ocorrências → caminho novo funcionou, pronto para promover.
    - N ocorrências → caminho legado ainda foi exercido, investigar.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "sistema.log"
STRANGLER_CODE = "STRANGLER_EXTRACTION_LEGACY"


def verificar(desde: str | None) -> int:
    if not LOG_PATH.exists():
        print(f"[ERRO] Log não encontrado: {LOG_PATH}")
        return 1

    ocorrencias = []
    total = 0

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

    print(f"Total de linhas no journal : {total}")
    if desde:
        print(f"Filtro desde              : {desde}")
    print(f"Ocorrências {STRANGLER_CODE}: {len(ocorrencias)}")

    if ocorrencias:
        print("\n--- Detalhes ---")
        for r in ocorrencias:
            print(f"  {r[0]} | ação={r[3]} | detalhe={r[4]}")
        print("\n[RESULTADO] ❌ Caminho legado ainda foi exercido. NÃO promover.")
        return 2

    print("\n[RESULTADO] ✅ Nenhum STRANGLER_EXTRACTION_LEGACY. Pronto para promover.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Verificação T1.5")
    parser.add_argument(
        "--desde",
        metavar="YYYY-MM-DD HH:MM:SS",
        help="Timestamp de início da janela de busca",
        default=None,
    )
    args = parser.parse_args()
    sys.exit(verificar(args.desde))


if __name__ == "__main__":
    main()
