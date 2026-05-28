from __future__ import annotations

import sys
import tempfile
import os
import uuid
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent
root_str = str(ROOT)

# Base temporário seguro (evita PermissionError com tempfile padrão)
_TMP_BASE = ROOT / ".tmp" / "pytest_tmp"
_TMP_BASE.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(_TMP_BASE)


def _safe_mkdtemp(suffix=None, prefix=None, dir=None):
    """mkdtemp compatível, mas criando diretórios com permissões acessíveis."""
    base = Path(dir or _TMP_BASE)
    base.mkdir(parents=True, exist_ok=True)
    prefix = "tmp" if prefix is None else prefix
    suffix = "" if suffix is None else suffix
    for _ in range(100):
        name = f"{prefix}{uuid.uuid4().hex}{suffix}"
        path = base / name
        try:
            path.mkdir()
            return str(path)
        except FileExistsError:
            continue
    raise FileExistsError("Não foi possível criar diretório temporário seguro.")


tempfile.mkdtemp = _safe_mkdtemp
downloads_root = ROOT.parent
normalized_sys_path = []
for entry in sys.path:
    if not entry:
        continue
    try:
        resolved = Path(entry).resolve()
    except Exception:
        normalized_sys_path.append(entry)
        continue
    if resolved == downloads_root:
        continue
    normalized_sys_path.append(entry)
sys.path = [root_str] + [p for p in normalized_sys_path if p != root_str]

def _purge_shadowed_module(name: str) -> None:
    mod = sys.modules.get(name)
    if mod is None:
        return
    mod_file = getattr(mod, "__file__", "")
    if not mod_file:
        sys.modules.pop(name, None)
        return
    mod_path = Path(mod_file).resolve()
    if ROOT not in mod_path.parents:
        sys.modules.pop(name, None)

for _name in (
    "config",
    "db",
    "services",
    "ui",
    "exportacao",
    "extracao",
    "analise",
    "utils",
    "autenticacao",
    "domain",
    "interface",
):
    _purge_shadowed_module(_name)

import importlib

for _name in (
    "config",
    "db",
    "services",
    "ui",
    "exportacao",
    "extracao",
    "analise",
    "utils",
    "autenticacao",
    "domain",
    "interface",
):
    try:
        sys.modules.pop(_name, None)
        importlib.import_module(_name)
    except Exception:
        # If import fails here, tests will surface the error with context.
        pass

collect_ignore = [
    "test_debug.txt",
    "test_error.txt",
]


def _tk_available() -> bool:
    try:
        import tkinter as tk
        root = tk.Tk()
        root.destroy()
        return True
    except Exception:
        return False


_HAS_TK = _tk_available()


def pytest_ignore_collect(collection_path, config):
    if _HAS_TK:
        return False
    ui_tests = {
        "test_janela_unica_abas.py",
        "test_integracao_completa.py",
        "test_performance.py",
    }
    return collection_path.name in ui_tests


@pytest.fixture
def tmp_path():
    """Fixture tmp_path customizada (evita tmpdir plugin)."""
    base = _TMP_BASE / "tmp_paths"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"tmp_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path
