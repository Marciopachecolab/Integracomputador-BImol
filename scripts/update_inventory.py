# -*- coding: utf-8 -*-
"""
Generate inventory reports for the repository.

Outputs:
- docs/INVENTARIO_SISTEMA.md
- docs/INVENTARIO_HIERARQUIA.md
- docs/INVENTARIO_DUPLICADOS.md
- docs/INVENTARIO_RECURSOS_ORFAOS.md
"""

from __future__ import annotations

import hashlib
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"

EXCLUDED_DIRS = {
    ".venv",
    "build",
    ".pytest_cache",
    ".tmp",
    ".snapshots",
    "snapshots",
    ".archive",
    "BACKUP_PHASE_2",
    "__pycache__",
}

EXCLUDED_PREFIXES = ("pytest-cache-files-",)

RESOURCE_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".gif",
    ".ico",
    ".bmp",
    ".tiff",
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".mp3",
    ".wav",
    ".mp4",
}

TEXT_EXTS = {
    ".py",
    ".json",
    ".ini",
    ".cfg",
    ".yml",
    ".yaml",
    ".txt",
    ".csv",
    ".ps1",
}


def main() -> int:
    files = list(iter_files(ROOT))
    stats = build_stats(files)
    duplicates = find_duplicates(files)

    resource_files = [f for f in files if f.suffix.lower() in RESOURCE_EXTS]
    duplicate_names = sorted({f.name for group in duplicates for f in group})
    resource_names = sorted({f.name for f in resource_files})
    names_to_check = sorted(set(resource_names + duplicate_names))

    used_names = find_used_names(files, names_to_check)
    orphan_resources = [
        f for f in resource_files if f.name.lower() not in used_names
    ]

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    write_inventory_summary(stats)
    write_tree(stats)
    write_duplicates(duplicates, used_names)
    write_orphans(orphan_resources)

    return 0


def iter_files(root: Path) -> Iterable[Path]:
    for current, dirs, files in os.walk(root):
        rel = Path(current).relative_to(root)
        dirs[:] = [
            d
            for d in dirs
            if not should_exclude_dir(rel / d)
        ]
        for fname in files:
            path = Path(current) / fname
            if should_exclude_dir(path.parent.relative_to(root)):
                continue
            yield path


def should_exclude_dir(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDED_DIRS:
            return True
        for prefix in EXCLUDED_PREFIXES:
            if part.startswith(prefix):
                return True
    return False


def build_stats(files: List[Path]) -> Dict:
    total_size = 0
    ext_counts: Dict[str, int] = defaultdict(int)
    size_by_dir: Dict[Path, int] = defaultdict(int)
    count_by_dir: Dict[Path, int] = defaultdict(int)

    for f in files:
        try:
            size = f.stat().st_size
        except OSError:
            continue
        total_size += size
        ext = f.suffix.lower() or "<none>"
        ext_counts[ext] += 1
        rel = f.relative_to(ROOT)
        parent = rel.parent
        count_by_dir[parent] += 1
        size_by_dir[parent] += size
        for p in parent.parents:
            if p == Path("."):
                break
            count_by_dir[p] += 1
            size_by_dir[p] += size

    largest = sorted(
        files,
        key=lambda p: p.stat().st_size if p.exists() else 0,
        reverse=True,
    )[:20]

    return {
        "files": files,
        "total_size": total_size,
        "ext_counts": dict(sorted(ext_counts.items(), key=lambda x: x[1], reverse=True)),
        "size_by_dir": size_by_dir,
        "count_by_dir": count_by_dir,
        "largest": largest,
    }


def find_duplicates(files: List[Path]) -> List[List[Path]]:
    size_map: Dict[int, List[Path]] = defaultdict(list)
    for f in files:
        try:
            size_map[f.stat().st_size].append(f)
        except OSError:
            continue

    duplicates: List[List[Path]] = []
    for size, group in size_map.items():
        if size == 0 or len(group) < 2:
            continue
        hash_map: Dict[str, List[Path]] = defaultdict(list)
        for f in group:
            digest = sha256_file(f)
            if digest:
                hash_map[digest].append(f)
        for digest, members in hash_map.items():
            if len(members) > 1:
                duplicates.append(members)
    return duplicates


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def find_used_names(files: List[Path], names: List[str]) -> set:
    if not names:
        return set()
    used = set()
    names_lower = [n.lower() for n in names]
    pattern_chunks = build_name_patterns(names_lower, chunk_size=40)
    text_files = [f for f in files if f.suffix.lower() in TEXT_EXTS]

    for f in text_files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        for pattern in pattern_chunks:
            for match in pattern.finditer(content):
                used.add(match.group(0))
    return used


def build_name_patterns(names: List[str], chunk_size: int = 40) -> List[re.Pattern]:
    patterns = []
    for i in range(0, len(names), chunk_size):
        chunk = names[i : i + chunk_size]
        chunk = [re.escape(n) for n in chunk if n]
        if not chunk:
            continue
        patterns.append(re.compile("|".join(chunk)))
    return patterns


def write_inventory_summary(stats: Dict) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_mb = stats["total_size"] / (1024 * 1024)
    ext_counts = stats["ext_counts"]
    largest = stats["largest"]

    lines = []
    lines.append("# Inventario do Sistema")
    lines.append("")
    lines.append(f"Gerado em: {now}")
    lines.append("")
    lines.append("## Escopo")
    lines.append(f"- Raiz: `{ROOT}`")
    lines.append("- Exclusoes: " + ", ".join(sorted(EXCLUDED_DIRS)))
    lines.append("- Prefixos excluidos: " + ", ".join(EXCLUDED_PREFIXES))
    lines.append("")
    lines.append("## Resumo")
    lines.append(f"- Total de arquivos: {len(stats['files'])}")
    lines.append(f"- Tamanho total: {total_mb:.2f} MB")
    lines.append("")
    lines.append("## Extensoes (top 20)")
    for ext, count in list(ext_counts.items())[:20]:
        lines.append(f"- {ext}: {count}")
    lines.append("")
    lines.append("## Maiores arquivos (top 20)")
    for f in largest:
        try:
            size_mb = f.stat().st_size / (1024 * 1024)
        except OSError:
            size_mb = 0
        rel = f.relative_to(ROOT)
        lines.append(f"- {rel} ({size_mb:.2f} MB)")

    (DOCS_DIR / "INVENTARIO_SISTEMA.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def write_tree(stats: Dict) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    size_by_dir = stats["size_by_dir"]
    count_by_dir = stats["count_by_dir"]

    lines = []
    lines.append("# Hierarquia de Pastas")
    lines.append("")
    lines.append(f"Gerado em: {now}")
    lines.append("")
    lines.append("```\n" + build_tree(size_by_dir, count_by_dir) + "\n```")

    (DOCS_DIR / "INVENTARIO_HIERARQUIA.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def build_tree(size_by_dir: Dict[Path, int], count_by_dir: Dict[Path, int]) -> str:
    lines = []
    root_label = f"{ROOT.name}/"
    lines.append(root_label)

    def walk(dir_path: Path, prefix: str) -> None:
        children = sorted(
            [
                d
                for d in size_by_dir.keys()
                if d.parent == dir_path and d != dir_path and d != Path(".")
            ]
        )
        for idx, child in enumerate(children):
            is_last = idx == len(children) - 1
            branch = "`-- " if is_last else "|-- "
            size_mb = size_by_dir.get(child, 0) / (1024 * 1024)
            count = count_by_dir.get(child, 0)
            lines.append(
                f"{prefix}{branch}{child.name}/ (files={count}, size={size_mb:.2f} MB)"
            )
            next_prefix = prefix + ("    " if is_last else "|   ")
            walk(child, next_prefix)

    walk(Path("."), "")
    return "\n".join(lines)


def write_duplicates(duplicates: List[List[Path]], used_names: set) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append("# Arquivos Duplicados (por conteudo)")
    lines.append("")
    lines.append(f"Gerado em: {now}")
    lines.append("")
    if not duplicates:
        lines.append("Nenhum duplicado encontrado no escopo analisado.")
    else:
        for idx, group in enumerate(duplicates, start=1):
            lines.append(f"## Grupo {idx}")
            for f in group:
                rel = f.relative_to(ROOT)
                try:
                    size_kb = f.stat().st_size / 1024
                except OSError:
                    size_kb = 0
                used = "USADO" if f.name.lower() in used_names else "NAO_REFERENCIADO"
                lines.append(f"- `{rel}` ({size_kb:.1f} KB) [{used}]")
            lines.append("")
        lines.append(
            "Notas: [USADO] indica nome de arquivo encontrado no codigo/config. "
            "Revisar antes de excluir duplicados."
        )

    (DOCS_DIR / "INVENTARIO_DUPLICADOS.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def write_orphans(orphan_resources: List[Path]) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append("# Recursos Orfaos (nao referenciados)")
    lines.append("")
    lines.append(f"Gerado em: {now}")
    lines.append("")
    if not orphan_resources:
        lines.append("Nenhum recurso orfao encontrado no escopo analisado.")
    else:
        for f in orphan_resources:
            rel = f.relative_to(ROOT)
            lines.append(f"- `{rel}`")
        lines.append("")
        lines.append(
            "Notas: analise baseada em busca por nome do arquivo em fontes de texto."
        )

    (DOCS_DIR / "INVENTARIO_RECURSOS_ORFAOS.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


if __name__ == "__main__":
    raise SystemExit(main())
