"""Governanca de refresh do baseline funcional (B0-QA03).

Uso:
  python scripts/baseline_refresh_governance.py check
  python scripts/baseline_refresh_governance.py record --reason "..." --changed-by "..." --approved-by "..."
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

DEFAULT_SNAPSHOT = Path("snapshots/phase0_runtime_baseline.json")
DEFAULT_LEDGER = Path("snapshots/baseline_refresh_governance.json")

REQUIRED_ENTRY_FIELDS = (
    "entry_id",
    "timestamp_utc",
    "snapshot_path",
    "snapshot_hash_sha256",
    "reason",
    "changed_by",
    "approved_by",
    "status",
)


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def compute_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_ledger(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"schema_version": "1.0.0", "entries": []}
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("Ledger invalido: formato raiz nao e objeto JSON.")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("Ledger invalido: campo 'entries' deve ser lista.")
    return payload


def _validate_entry(entry: Dict[str, Any]) -> None:
    for field in REQUIRED_ENTRY_FIELDS:
        if field not in entry or str(entry.get(field, "")).strip() == "":
            raise ValueError(f"Ledger invalido: campo obrigatorio ausente/vazio: {field}")


def _find_last_entry_for_snapshot(entries: List[Dict[str, Any]], snapshot: Path) -> Dict[str, Any] | None:
    snapshot_text = str(snapshot).replace("\\", "/")
    for entry in reversed(entries):
        if str(entry.get("snapshot_path", "")).replace("\\", "/") == snapshot_text:
            return entry
    return None


def check_refresh(snapshot: Path = DEFAULT_SNAPSHOT, ledger_path: Path = DEFAULT_LEDGER) -> Tuple[bool, str]:
    if not snapshot.exists():
        return False, f"Snapshot nao encontrado: {snapshot}"

    current_hash = compute_sha256(snapshot)
    if not ledger_path.exists():
        return False, f"Ledger nao encontrado: {ledger_path}"

    ledger = load_ledger(ledger_path)
    entries = ledger.get("entries", [])
    if not entries:
        return False, "Ledger sem entradas. Registre aprovacao de baseline."

    for entry in entries:
        _validate_entry(entry)

    last_entry = _find_last_entry_for_snapshot(entries, snapshot)
    if last_entry is None:
        return False, "Sem entrada de governanca para o snapshot atual."

    if str(last_entry.get("status", "")).strip().lower() != "approved":
        return False, "Ultima entrada de governanca nao esta aprovada."

    if str(last_entry.get("snapshot_hash_sha256", "")).lower() != current_hash.lower():
        return False, (
            "Hash do snapshot diverge da ultima aprovacao. "
            "Execute comando de record com justificativa."
        )

    return True, "Governanca de baseline valida para hash atual."


def record_refresh(
    *,
    reason: str,
    changed_by: str,
    approved_by: str,
    snapshot: Path = DEFAULT_SNAPSHOT,
    ledger_path: Path = DEFAULT_LEDGER,
    commands: List[str] | None = None,
    related_artifacts: List[str] | None = None,
) -> Dict[str, Any]:
    if not snapshot.exists():
        raise FileNotFoundError(f"Snapshot nao encontrado: {snapshot}")
    if not reason.strip():
        raise ValueError("Campo --reason e obrigatorio.")
    if not changed_by.strip():
        raise ValueError("Campo --changed-by e obrigatorio.")
    if not approved_by.strip():
        raise ValueError("Campo --approved-by e obrigatorio.")

    ledger = load_ledger(ledger_path)
    entries: List[Dict[str, Any]] = list(ledger.get("entries", []))
    current_hash = compute_sha256(snapshot)

    next_id = 1
    if entries:
        try:
            next_id = int(entries[-1].get("entry_id", 0)) + 1
        except (TypeError, ValueError):
            next_id = len(entries) + 1

    entry = {
        "entry_id": next_id,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "snapshot_path": str(snapshot).replace("\\", "/"),
        "snapshot_hash_sha256": current_hash,
        "reason": reason.strip(),
        "changed_by": changed_by.strip(),
        "approved_by": approved_by.strip(),
        "status": "approved",
        "commands": commands or [
            "python scripts/generate_phase0_baseline.py --check",
            "./scripts/run_phase0_gates.ps1",
        ],
        "related_artifacts": related_artifacts or [],
    }
    entries.append(entry)
    ledger["entries"] = entries
    _write_json(ledger_path, ledger)
    return entry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Governanca de refresh do baseline fase 0.")
    sub = parser.add_subparsers(dest="command", required=True)

    check_cmd = sub.add_parser("check", help="Valida governanca para hash atual do snapshot.")
    check_cmd.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    check_cmd.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)

    record_cmd = sub.add_parser("record", help="Registra aprovacao do snapshot atual.")
    record_cmd.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    record_cmd.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    record_cmd.add_argument("--reason", required=True)
    record_cmd.add_argument("--changed-by", required=True)
    record_cmd.add_argument("--approved-by", required=True)
    record_cmd.add_argument("--artifact", action="append", default=[])
    record_cmd.add_argument("--exec-cmd", dest="exec_cmds", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "check":
        ok, message = check_refresh(snapshot=args.snapshot, ledger_path=args.ledger)
        print(f"[baseline-governance] {message}")
        return 0 if ok else 2

    if args.command == "record":
        entry = record_refresh(
            reason=args.reason,
            changed_by=args.changed_by,
            approved_by=args.approved_by,
            snapshot=args.snapshot,
            ledger_path=args.ledger,
            related_artifacts=list(args.artifact),
            commands=list(args.exec_cmds),
        )
        print(
            "[baseline-governance] Registro criado: "
            f"entry_id={entry['entry_id']} hash={entry['snapshot_hash_sha256'][:12]}..."
        )
        return 0

    print("[baseline-governance] Comando invalido.")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
