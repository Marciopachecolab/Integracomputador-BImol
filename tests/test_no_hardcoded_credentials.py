# -*- coding: utf-8 -*-
"""
Guardiao (AC-2.4 / Audit Refactoring T-006).

Falha se encontrar credenciais hardcoded em arquivos .py da raiz ou das areas
de runtime canonicas. Protege contra regressao do tipo `test_login.py`
(senha '123456' literal passada a chamada de autenticacao) e contra atribuicao
de senha literal a variavel de credencial.

Constitution.delta §2.1: "MUST NOT existir senha hardcoded em qualquer arquivo
.py no repositorio ... Unico caminho permitido: variaveis de ambiente."

Escopo de scan (CLAUDE.md §4 — areas de runtime) + .py da raiz.

EXCLUSOES DELIBERADAS (nao sao runtime):
- `tests/`  : fixtures de teste podem usar credenciais sinteticas.
- `docs/`   : evidencia forense arquivada (docs/obsoletos/incidents/).
- `core/`   : `core/authentication/user_manager.py` e LEGADO em deprecacao
              controlada (DT-003 / DEC-003), neutralizado e import-banido por
              T-AUD-004A. Contem `password="admin123456"` (linha ~1811) — achado
              conhecido, fora do escopo da Fase 0; remocao fisica exige DEC
              futura. Registrado em notas_de_passagem.md.

Allowlist explicita (arquivos que legitimamente referenciam credenciais via
ambiente, sem literal):
- scripts/debug_login_runner.py  (usa GAL_TEST_USER/GAL_TEST_PASS)
"""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

RUNTIME_ROOTS = [
    "autenticacao",
    "application",
    "services",
    "exportacao",
    "ui",
    "interface",
    "browser",
    "config",
    "utils",
    "domain",
    "scripts",
]

# Caminhos (relativos, com '/') isentos por decisao documentada.
ALLOWLIST = {
    "scripts/debug_login_runner.py",
}

# Nomes de variaveis/argumentos que designam senha.
PASSWORD_NAMES = {"senha", "password", "passwd", "pwd"}

# Funcoes de autenticacao cujas chamadas com literal de senha sao proibidas.
AUTH_FUNCS = {"login", "autenticar", "autenticar_credenciais", "authenticate"}


def _rel(p: Path) -> str:
    return p.relative_to(REPO_ROOT).as_posix()


def _iter_py_files():
    # .py da raiz
    for py in REPO_ROOT.glob("*.py"):
        yield py
    # areas de runtime
    for root in RUNTIME_ROOTS:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for py in base.rglob("*.py"):
            if ".bak" in py.name:
                continue
            yield py


def _is_nonempty_str_const(node) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.strip() != ""


def _scan(tree: ast.AST):
    """Retorna lista de (lineno, motivo) de credenciais hardcoded."""
    achados = []
    for node in ast.walk(tree):
        # 1) Atribuicao: senha = "literal"
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id.lower() in PASSWORD_NAMES:
                    if _is_nonempty_str_const(node.value):
                        achados.append((node.lineno, f"atribuicao '{tgt.id}' = literal"))
        # 2) Anotada: senha: str = "literal"
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id.lower() in PASSWORD_NAMES and node.value is not None:
                if _is_nonempty_str_const(node.value):
                    achados.append((node.lineno, f"atribuicao anotada '{node.target.id}' = literal"))
        # 3) Chamada: keyword password="literal"
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg and kw.arg.lower() in PASSWORD_NAMES and _is_nonempty_str_const(kw.value):
                    achados.append((node.lineno, f"keyword '{kw.arg}'= literal em chamada"))
            # 4) Chamada a funcao de auth com literal posicional (ex.: login('u','123456'))
            fname = None
            if isinstance(node.func, ast.Attribute):
                fname = node.func.attr
            elif isinstance(node.func, ast.Name):
                fname = node.func.id
            if fname in AUTH_FUNCS:
                for arg in node.args:
                    if _is_nonempty_str_const(arg):
                        achados.append((node.lineno, f"chamada '{fname}(...)' com senha literal"))
                        break
    return achados


def test_no_hardcoded_credentials():
    offenders = []
    for py in _iter_py_files():
        rel = _rel(py)
        if rel in ALLOWLIST:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8-sig"))
        except (SyntaxError, UnicodeDecodeError):
            # Parsing e responsabilidade de outro guardiao; nao mascarar aqui.
            continue
        for lineno, motivo in _scan(tree):
            offenders.append(f"{rel}:{lineno}: {motivo}")

    assert not offenders, (
        "Credenciais hardcoded detectadas em runtime/raiz:\n"
        + "\n".join(offenders)
        + "\n\nUse variaveis de ambiente (ex.: os.environ['GAL_TEST_PASS'])."
    )
