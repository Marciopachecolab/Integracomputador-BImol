# -*- coding: utf-8 -*-
"""
Installation checks for shared storage and prerequisites.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from services.core.config_service import config_service
from services.persistence.csv_contracts import get_csv_contract
from services.path_resolver import resolve_banco_dir, resolve_users_csv_path


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    message: str


@dataclass(frozen=True)
class SetupReport:
    timestamp: str
    app_user: str
    os_user: str
    data_root: str
    allowed_roots: List[str]
    path_checks: List[CheckResult]
    csv_checks: List[CheckResult]
    acl_checks: List[CheckResult]


def bootstrap_banco_runtime(csv_defs):
    for name, path_str, expected_cols, required in csv_defs:
        if not expected_cols:
            continue
        p = Path(path_str)
        if not p.exists() or p.stat().st_size == 0:
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                contract = get_csv_contract(path_str)
                encoding = contract.encoding if contract else "utf-8-sig"
                delimiter = contract.delimiter if contract else ";"
                p.write_text(delimiter.join(expected_cols) + "\n", encoding=encoding)
            except Exception:
                pass


def build_setup_report(app_user: str) -> SetupReport:
    cfg = config_service.get_all()
    data_root = str(cfg.get("data_root") or "").strip()
    allowed_roots = list(cfg.get("allowed_roots") or [])
    os_user = _get_os_user()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    path_defs, csv_defs, paths_error = _collect_critical_items()
    path_checks = _check_paths(path_defs)
    if paths_error:
        path_checks.insert(
            0,
            CheckResult(
                "config_paths",
                "FAIL",
                f"Falha ao resolver paths do config: {paths_error}",
            ),
        )
    if not data_root:
        path_checks.append(
            CheckResult(
                "data_root",
                "WARN",
                "data_root vazio (share nao configurado)",
            )
        )
    if not allowed_roots:
        path_checks.append(
            CheckResult(
                "allowed_roots",
                "WARN",
                "allowed_roots vazio (restricao de paths desativada)",
            )
        )
    shared_status = config_service.get_shared_storage_status()
    if shared_status.get("same_root_policy"):
        path_checks.append(
            CheckResult(
                "shared_storage_policy",
                "OK",
                "Todos os paths de dados configurados sob um unico compartilhamento.",
            )
        )
    else:
        path_checks.append(
            CheckResult(
                "shared_storage_policy",
                "WARN",
                "Padronizacao de compartilhamento nao aplicada (data_root/allowed_roots divergentes).",
            )
        )
    if shared_status.get("required") and not shared_status.get("ready"):
        path_checks.append(
            CheckResult(
                "shared_storage_required",
                "FAIL",
                "Politica de compartilhamento obrigatorio ativa, mas configuracao ainda nao esta pronta.",
            )
        )
        
    bootstrap_banco_runtime(csv_defs)
    csv_checks = _check_csvs(csv_defs)

    paths_for_acl = [p for _, p, *_ in path_defs if p]
    acl_checks = _check_acl(paths_for_acl, os_user)

    return SetupReport(
        timestamp=timestamp,
        app_user=app_user or "Desconhecido",
        os_user=os_user,
        data_root=data_root,
        allowed_roots=allowed_roots,
        path_checks=path_checks,
        csv_checks=csv_checks,
        acl_checks=acl_checks,
    )


def export_setup_report(report: SetupReport, output_dir: Optional[str] = None) -> str:
    if not output_dir:
        try:
            paths = config_service.get_paths()
            output_dir = paths.get("default_results_folder") or "reports"
        except Exception:
            output_dir = "reports"
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"relatorio_instalacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    out_path = out_dir / filename
    out_path.write_text(_format_report(report), encoding="utf-8")
    return str(out_path)


def summarize_checks(checks: Iterable[CheckResult]) -> Tuple[int, int, int]:
    ok = sum(1 for c in checks if c.status == "OK")
    warn = sum(1 for c in checks if c.status == "WARN")
    fail = sum(1 for c in checks if c.status == "FAIL")
    return ok, warn, fail


def _collect_critical_items():
    paths_error = None
    try:
        paths = config_service.get_paths()
    except Exception as exc:
        paths = {}
        paths_error = str(exc)
    banco = resolve_banco_dir()
    users_csv = str(resolve_users_csv_path())

    path_defs = [
        ("log_file", paths.get("log_file"), "file", False),
        ("gal_history_csv", paths.get("gal_history_csv"), "file", False),
        ("gal_upload_history_csv", paths.get("gal_upload_history_csv"), "file", False),
        ("default_csv_folder", paths.get("default_csv_folder"), "dir", False),
        ("default_results_folder", paths.get("default_results_folder"), "dir", False),
        ("banco_dir", str(banco), "dir", True),
    ]

    csv_defs = [
        ("banco_runtime/exames_config.csv", str(banco / "exames_config.csv"), ["exame"], True),
        ("banco_runtime/exames_metadata.csv", str(banco / "exames_metadata.csv"), ["exame"], True),
        ("banco_runtime/equipamentos_metadata.csv", str(banco / "equipamentos_metadata.csv"), ["equipamento"], True),
        ("banco_runtime/placas_metadata.csv", str(banco / "placas_metadata.csv"), ["tipo_placa"], True),
        ("banco_runtime/regras_analise_metadata.csv", str(banco / "regras_analise_metadata.csv"), ["exame"], True),
        ("banco_runtime/usuarios.csv", users_csv, ["usuario", "senha_hash"], False),
        ("banco_runtime/equipamentos.csv", str(banco / "equipamentos.csv"), [], False),
        ("banco_runtime/placas.csv", str(banco / "placas.csv"), [], False),
        ("banco_runtime/regras.csv", str(banco / "regras.csv"), [], False),
    ]
    return path_defs, csv_defs, paths_error


def _check_paths(items) -> List[CheckResult]:
    results: List[CheckResult] = []
    for name, path, kind, required in items:
        if not path:
            status = "FAIL" if required else "WARN"
            results.append(CheckResult(name, status, "Caminho vazio"))
            continue
        target = Path(path)
        exists = target.exists()
        if kind == "file":
            if exists:
                results.append(CheckResult(name, "OK", f"Arquivo encontrado: {path}"))
            else:
                status = "FAIL" if required else "WARN"
                results.append(CheckResult(name, status, f"Arquivo ausente: {path}"))
        else:
            if exists:
                results.append(CheckResult(name, "OK", f"Pasta encontrada: {path}"))
            else:
                status = "FAIL" if required else "WARN"
                results.append(CheckResult(name, status, f"Pasta ausente: {path}"))
    return results


def _check_csvs(items) -> List[CheckResult]:
    results: List[CheckResult] = []
    for name, path, expected_cols, required in items:
        p = Path(path)
        if not p.exists():
            status = "FAIL" if required else "WARN"
            results.append(CheckResult(name, status, f"CSV ausente: {path}"))
            continue

        try:
            header, has_rows = _read_csv_header(path)
        except Exception as exc:
            status = "FAIL" if required else "WARN"
            results.append(CheckResult(name, status, f"Erro ao ler CSV: {exc}"))
            continue

        if not header:
            status = "FAIL" if required else "WARN"
            results.append(CheckResult(name, status, "CSV sem cabecalho"))
            continue

        missing = [c for c in expected_cols if c not in header]
        if missing:
            results.append(
                CheckResult(
                    name,
                    "FAIL" if required else "WARN",
                    f"Colunas ausentes: {missing}",
                )
            )
            continue

        if len(set(header)) != len(header):
            results.append(CheckResult(name, "WARN", "Cabecalho com colunas duplicadas"))
            continue

        if not has_rows:
            results.append(CheckResult(name, "WARN", "CSV sem linhas de dados"))
            continue

        results.append(CheckResult(name, "OK", "CSV integro"))

    return results


def _check_acl(paths: Iterable[str], os_user: str) -> List[CheckResult]:
    roots = sorted({r for r in (_extract_share_root(p) for p in paths) if r})
    if not roots:
        return [CheckResult("ACL", "WARN", "Nenhum caminho valido para verificar ACL")]

    results: List[CheckResult] = []
    for root in roots:
        if os.name != "nt":
            results.append(CheckResult(root, "INFO", "Verificacao de ACL suportada apenas no Windows"))
            continue

        access_ok = os.access(root, os.R_OK | os.W_OK)
        icacls_info = _icacls_summary(root, os_user)

        if access_ok and icacls_info["write"]:
            results.append(CheckResult(root, "OK", icacls_info["message"]))
        elif access_ok:
            results.append(CheckResult(root, "WARN", icacls_info["message"]))
        else:
            results.append(CheckResult(root, "FAIL", "Sem acesso de leitura/escrita ao share"))
    return results


def _icacls_summary(path: str, os_user: str) -> dict:
    try:
        output = subprocess.check_output(["icacls", path], text=True, errors="ignore")
    except Exception as exc:
        return {"write": False, "message": f"icacls falhou: {exc}"}

    candidates = _principal_candidates(os_user)
    has_write = False
    matched = []
    for line in output.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        principal, rights = line.split(":", 1)
        principal = principal.strip()
        rights = rights.strip().upper()
        if any(c.lower() == principal.lower() for c in candidates):
            matched.append(f"{principal} {rights}")
            if "(F)" in rights or "(M)" in rights or "(W)" in rights:
                has_write = True
    if matched:
        return {
            "write": has_write,
            "message": "ACL detectada para usuario/grupo: " + "; ".join(matched),
        }
    return {
        "write": False,
        "message": "Nao foi encontrada regra explicita para o usuario no ACL",
    }


def _principal_candidates(os_user: str) -> List[str]:
    candidates = []
    domain = os.environ.get("USERDOMAIN", "").strip()
    user = os_user.split("\\")[-1]
    if domain and user:
        candidates.append(f"{domain}\\{user}")
    if os_user:
        candidates.append(os_user)
    if user:
        candidates.append(user)
    candidates.extend(
        [
            "BUILTIN\\USERS",
            "USERS",
            "AUTHENTICATED USERS",
            "EVERYONE",
        ]
    )
    return candidates


def _extract_share_root(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    if path.startswith("\\\\"):
        parts = path.strip("\\").split("\\")
        if len(parts) >= 2:
            return f"\\\\{parts[0]}\\{parts[1]}"
        return None
    drive, _ = os.path.splitdrive(path)
    if drive:
        return f"{drive}\\"
    return None


def _read_csv_header(path: str) -> Tuple[List[str], bool]:
    contract = get_csv_contract(path)
    if contract is not None:
        with open(path, "r", encoding=contract.encoding, newline="") as f:
            first = f.readline()
            if not first:
                return [], False
            header = [h.strip() for h in first.strip().split(contract.delimiter)]
            has_rows = bool(f.readline())
            return header, has_rows

    encodings = ["utf-8-sig", "utf-8", "latin-1"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                first = f.readline()
                if not first:
                    return [], False
                delimiter = _detect_delimiter(first)
                header = [h.strip() for h in first.strip().split(delimiter)]
                has_rows = bool(f.readline())
                return header, has_rows
        except Exception:
            continue
    raise ValueError("Nao foi possivel ler o CSV com encodings suportados")


def _detect_delimiter(line: str) -> str:
    comma = line.count(",")
    semi = line.count(";")
    return ";" if semi > comma else ","


def _format_report(report: SetupReport) -> str:
    lines = []
    lines.append("RELATORIO DE INSTALACAO - INTEGRAGAL")
    lines.append("=" * 46)
    lines.append(f"Data/Hora: {report.timestamp}")
    lines.append(f"Usuario (App): {report.app_user}")
    lines.append(f"Usuario (OS): {report.os_user}")
    lines.append(f"data_root: {report.data_root or '(vazio)'}")
    lines.append(f"allowed_roots: {report.allowed_roots or '(vazio)'}")
    lines.append("")

    lines.append("[CHECKLIST PATHS]")
    lines.extend(_format_check_lines(report.path_checks))
    lines.append("")
    lines.append("[CHECKLIST CSVs]")
    lines.extend(_format_check_lines(report.csv_checks))
    lines.append("")
    lines.append("[ACL SHARE]")
    lines.extend(_format_check_lines(report.acl_checks))
    lines.append("")
    ok, warn, fail = summarize_checks(
        report.path_checks + report.csv_checks + report.acl_checks
    )
    lines.append("[RESUMO]")
    lines.append(f"OK: {ok} | WARN: {warn} | FAIL: {fail}")
    return "\n".join(lines)


def _format_check_lines(checks: Iterable[CheckResult]) -> List[str]:
    out = []
    for c in checks:
        out.append(f"- [{c.status}] {c.name}: {c.message}")
    return out


def _get_os_user() -> str:
    domain = os.environ.get("USERDOMAIN", "").strip()
    user = os.environ.get("USERNAME", "").strip()
    if domain and user:
        return f"{domain}\\{user}"
    if user:
        return user
    return os.environ.get("USER", "UNKNOWN")
