#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.encoding_policy import get_ingest_encodings
from utils.csv_lock import CSVFileLock
from utils.network_io import RetryPolicy, open_with_retry
from utils.text_normalizer import repair_mojibake_text

UTF8_BOM = b"\xef\xbb\xbf"
DEFAULT_ROOTS = ("logs", "reports", "banco_runtime", "banco")
DEFAULT_REPORT = Path("snapshots/legacy_csv_encoding_migration_report.json")


@dataclass(frozen=True)
class FileResult:
    path: str
    status: str
    reason: str
    source_encoding: str | None = None
    backup_path: str | None = None
    changed: bool = False


def iter_csv_files(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if not root.exists():
            continue
        if root.is_file() and root.suffix.lower() == ".csv":
            yield root
            continue
        if root.is_dir():
            for path in root.rglob("*.csv"):
                yield path


def decode_best_effort(raw: bytes, encodings: List[str]) -> tuple[str | None, str | None]:
    for enc in encodings:
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return None, None


def normalize_text(text: str, *, repair_mojibake: bool) -> str:
    if not repair_mojibake:
        return text
    lines = text.splitlines(keepends=True)
    return "".join(repair_mojibake_text(line) for line in lines)


def process_file(
    path: Path,
    *,
    apply: bool,
    backup_root: Path,
    repair_mojibake: bool,
    policy: RetryPolicy,
    encodings: List[str],
) -> FileResult:
    raw = path.read_bytes()
    has_bom = raw.startswith(UTF8_BOM)

    decoded_utf8: str | None
    if has_bom:
        decoded_utf8 = raw[len(UTF8_BOM) :].decode("utf-8", errors="strict")
        source_enc = "utf-8-sig"
    else:
        try:
            decoded_utf8 = raw.decode("utf-8", errors="strict")
            source_enc = "utf-8"
        except UnicodeDecodeError:
            decoded_utf8, source_enc = decode_best_effort(raw, encodings)
            if decoded_utf8 is None:
                return FileResult(
                    path=str(path),
                    status="error",
                    reason="unreadable_with_policy_encodings",
                )

    normalized = normalize_text(decoded_utf8, repair_mojibake=repair_mojibake)
    target_raw = normalized.encode("utf-8")
    changed = target_raw != raw
    if not changed:
        return FileResult(
            path=str(path),
            status="ok",
            reason="already_utf8_canonical",
            source_encoding=source_enc,
            changed=False,
        )

    if not apply:
        return FileResult(
            path=str(path),
            status="planned",
            reason="would_normalize_to_utf8",
            source_encoding=source_enc,
            changed=True,
        )

    try:
        relative_path = path.relative_to(BASE_DIR)
    except ValueError:
        relative_path = Path(path.name)
    backup_path = backup_root / relative_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    with open_with_retry(path, "rb", policy=policy) as src, open_with_retry(
        backup_path, "wb", policy=policy
    ) as dst:
        shutil.copyfileobj(src, dst)

    with CSVFileLock(path):
        with open_with_retry(path, "wb", policy=policy) as handle:
            handle.write(target_raw)

    return FileResult(
        path=str(path),
        status="changed",
        reason="normalized_to_utf8",
        source_encoding=source_enc,
        backup_path=str(backup_path),
        changed=True,
    )


def write_report(results: List[FileResult], report_path: Path) -> None:
    summary = {
        "total": len(results),
        "changed": sum(1 for item in results if item.status == "changed"),
        "planned": sum(1 for item in results if item.status == "planned"),
        "ok": sum(1 for item in results if item.status == "ok"),
        "errors": sum(1 for item in results if item.status == "error"),
    }
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "results": [asdict(item) for item in results],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normaliza CSV legados para UTF-8 sem BOM.")
    parser.add_argument("--root", action="append", default=[], help="Raiz a processar (repeatable).")
    parser.add_argument("--apply", action="store_true", help="Aplica alteracoes.")
    parser.add_argument(
        "--backup-dir",
        default=None,
        help="Diretorio de backup (obrigatorio com --apply se quiser sobrescrever padrao).",
    )
    parser.add_argument(
        "--repair-mojibake",
        action="store_true",
        help="Aplica reparo textual de mojibake apos decode (mais agressivo).",
    )
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="Relatorio JSON da execucao.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    roots = [Path(item) for item in args.root] if args.root else [Path(item) for item in DEFAULT_ROOTS]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = (
        Path(args.backup_dir)
        if args.backup_dir
        else Path("snapshots") / f"encoding_backup_{stamp}"
    )
    report_path = Path(args.report)
    retry_policy = RetryPolicy.from_env()
    encodings = get_ingest_encodings()

    results = [
        process_file(
            csv_path,
            apply=bool(args.apply),
            backup_root=backup_root,
            repair_mojibake=bool(args.repair_mojibake),
            policy=retry_policy,
            encodings=encodings,
        )
        for csv_path in sorted(iter_csv_files(roots))
    ]
    write_report(results, report_path)

    summary = {
        "changed": sum(1 for item in results if item.status == "changed"),
        "planned": sum(1 for item in results if item.status == "planned"),
        "ok": sum(1 for item in results if item.status == "ok"),
        "errors": sum(1 for item in results if item.status == "error"),
    }
    print(
        "[normalize-legacy-csv] "
        f"apply={bool(args.apply)} changed={summary['changed']} planned={summary['planned']} "
        f"ok={summary['ok']} errors={summary['errors']} report={report_path}"
    )
    return 2 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
