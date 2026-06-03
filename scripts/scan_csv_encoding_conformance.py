#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Scanner de conformidade de encoding para CSVs criticos.

Objetivo:
- detectar BOM UTF-8;
- detectar arquivos nao legiveis em UTF-8;
- detectar marcadores tipicos de mojibake em texto.

Modo padrao: auditoria (nao bloqueante).
Modo estrito: retorna codigo != 0 quando houver nao conformidade.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

UTF8_BOM = b"\xef\xbb\xbf"

# Marcadores comuns de texto UTF-8 lido como latin1/cp1252.
MOJIBAKE_TOKENS = (
    "Ãƒ",
    "Ã‚",
    "Ã¢â",
    "ï¿½",
    "�",
    "Ã£",
    "Ã§",
    "Ã¡",
    "Ã©",
    "Ãª",
    "Ã­",
    "Ã³",
    "Ã´",
    "Ãº",
)

DEFAULT_ROOTS = ("logs", "reports", "banco_runtime", "banco")
DEFAULT_REPORT = Path("snapshots/encoding_conformance_report.json")
EXCLUDED_REPORT_NAMES = {"encoding_conformance_report.json"}


@dataclass(frozen=True)
class MojibakeHit:
    line: int
    token: str
    sample: str


@dataclass(frozen=True)
class CsvScanResult:
    path: str
    has_bom: bool
    valid_utf8: bool
    mojibake_hits: List[MojibakeHit]


def _iter_csv_files(roots: Iterable[Path], report_path: Path) -> Iterable[Path]:
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            if root.suffix.lower() == ".csv":
                yield root
            continue
        for csv_path in root.rglob("*.csv"):
            if csv_path.name in EXCLUDED_REPORT_NAMES:
                continue
            if csv_path.resolve() == report_path.resolve():
                continue
            yield csv_path


def _scan_csv(path: Path) -> CsvScanResult:
    raw = path.read_bytes()
    has_bom = raw.startswith(UTF8_BOM)
    try:
        text = raw.decode("utf-8")
        valid_utf8 = True
    except UnicodeDecodeError:
        text = ""
        valid_utf8 = False

    hits: List[MojibakeHit] = []
    if valid_utf8:
        for line_no, line in enumerate(text.splitlines(), start=1):
            for token in MOJIBAKE_TOKENS:
                if token in line:
                    hits.append(
                        MojibakeHit(
                            line=line_no,
                            token=token,
                            sample=line[:200],
                        )
                    )

    return CsvScanResult(
        path=str(path),
        has_bom=has_bom,
        valid_utf8=valid_utf8,
        mojibake_hits=hits,
    )


def _build_report(results: List[CsvScanResult]) -> dict:
    total = len(results)
    bom_count = sum(1 for item in results if item.has_bom)
    invalid_utf8_count = sum(1 for item in results if not item.valid_utf8)
    mojibake_file_count = sum(1 for item in results if item.mojibake_hits)
    mojibake_hit_count = sum(len(item.mojibake_hits) for item in results)

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "csv_total": total,
            "bom_files": bom_count,
            "invalid_utf8_files": invalid_utf8_count,
            "mojibake_files": mojibake_file_count,
            "mojibake_hits": mojibake_hit_count,
        },
        "results": [
            {
                **asdict(item),
                "mojibake_hits": [asdict(hit) for hit in item.mojibake_hits],
            }
            for item in results
        ],
    }


def _has_violation(
    report: dict,
    *,
    strict: bool,
    strict_bom: bool,
    strict_invalid_utf8: bool,
    strict_mojibake: bool,
) -> bool:
    summary = report["summary"]
    if strict:
        return (
            summary["bom_files"] > 0
            or summary["invalid_utf8_files"] > 0
            or summary["mojibake_files"] > 0
        )
    if strict_bom and summary["bom_files"] > 0:
        return True
    if strict_invalid_utf8 and summary["invalid_utf8_files"] > 0:
        return True
    if strict_mojibake and summary["mojibake_files"] > 0:
        return True
    return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scanner de conformidade CSV (encoding/BOM/mojibake).")
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        help="Raiz para scan de CSV (pode repetir). Default: logs, reports, banco.",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT),
        help="Arquivo JSON de saida do scanner.",
    )
    parser.add_argument("--strict", action="store_true", help="Falha se houver qualquer nao conformidade.")
    parser.add_argument("--strict-bom", action="store_true", help="Falha se houver arquivo com BOM.")
    parser.add_argument(
        "--strict-invalid-utf8",
        action="store_true",
        help="Falha se houver arquivo nao legivel em UTF-8.",
    )
    parser.add_argument(
        "--strict-mojibake",
        action="store_true",
        help="Falha se houver marcador de mojibake.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    roots = [Path(value) for value in args.root] if args.root else [Path(item) for item in DEFAULT_ROOTS]
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    results = [_scan_csv(path) for path in sorted(_iter_csv_files(roots, report_path))]
    report = _build_report(results)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = report["summary"]
    print(
        "[encoding-scan] csv_total={csv_total} bom_files={bom_files} invalid_utf8_files={invalid_utf8_files} "
        "mojibake_files={mojibake_files} mojibake_hits={mojibake_hits}".format(**summary)
    )
    print(f"[encoding-scan] report={report_path}")

    has_violation = _has_violation(
        report,
        strict=bool(args.strict),
        strict_bom=bool(args.strict_bom),
        strict_invalid_utf8=bool(args.strict_invalid_utf8),
        strict_mojibake=bool(args.strict_mojibake),
    )
    if has_violation:
        print("[encoding-scan] STRICT violation detected.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
