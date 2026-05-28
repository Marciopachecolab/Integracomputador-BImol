# -*- coding: utf-8 -*-
"""Persistencia SQLite para historico por exame (corridas_<slug_exame>)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

from services.path_resolver import resolve_banco_dir

CORE_FIELDS = (
    "corrida_id",
    "exame_slug",
    "equipamento_id",
    "equipamento_modelo",
    "data_exame",
    "hora_exame",
    "lote",
    "amostra_codigo",
    "pocos",
    "resultado_geral",
    "status_placa",
)


def default_exam_runs_db_path() -> Path:
    """Retorna o caminho padrão do banco para historico por exame."""
    return resolve_banco_dir() / "historico.db"


class ExamRunsSQLiteRepository:
    """Repositorio SQLite-first para historico por exame com dedupe contratual."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else default_exam_runs_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS exam_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    corrida_id TEXT NOT NULL,
                    exame_slug TEXT NOT NULL,
                    equipamento_id TEXT,
                    equipamento_modelo TEXT,
                    data_exame TEXT NOT NULL,
                    hora_exame TEXT,
                    lote TEXT NOT NULL,
                    amostra_codigo TEXT NOT NULL,
                    pocos TEXT,
                    resultado_geral TEXT,
                    status_placa TEXT,
                    targets_json TEXT DEFAULT '{}',
                    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_exam_runs_contract_dedupe
                ON exam_runs(
                    lower(trim(corrida_id)),
                    lower(trim(amostra_codigo)),
                    lower(trim(lote)),
                    lower(trim(data_exame))
                )
                WHERE
                    length(trim(corrida_id)) > 0
                    AND length(trim(amostra_codigo)) > 0
                    AND length(trim(lote)) > 0
                    AND length(trim(data_exame)) > 0;
                CREATE INDEX IF NOT EXISTS idx_exam_runs_lote
                ON exam_runs(lower(trim(lote)));
                CREATE INDEX IF NOT EXISTS idx_exam_runs_exame_data
                ON exam_runs(exame_slug, data_exame);
                """
            )

    def append_rows(self, rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
        """Insere linhas novas e retorna somente as efetivamente inseridas."""
        inserted: List[Dict[str, str]] = []
        if not rows:
            return inserted

        with sqlite3.connect(self.db_path) as conn:
            for row in rows:
                core = {key: row.get(key, "") for key in CORE_FIELDS}
                targets = {k: v for k, v in row.items() if k not in CORE_FIELDS}
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO exam_runs (
                        corrida_id, exame_slug, equipamento_id, equipamento_modelo,
                        data_exame, hora_exame, lote, amostra_codigo, pocos,
                        resultado_geral, status_placa, targets_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        core["corrida_id"],
                        core["exame_slug"],
                        core["equipamento_id"],
                        core["equipamento_modelo"],
                        core["data_exame"],
                        core["hora_exame"],
                        core["lote"],
                        core["amostra_codigo"],
                        core["pocos"],
                        core["resultado_geral"],
                        core["status_placa"],
                        json.dumps(targets, ensure_ascii=False, sort_keys=True),
                    ),
                )
                if cursor.rowcount == 1:
                    inserted.append(row)
            conn.commit()
        return inserted

    def count(self) -> int:
        """Conta registros totais (suporte a teste)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM exam_runs")
            return int(cursor.fetchone()[0])

    def list_rows(self) -> List[Dict[str, str]]:
        """Lista linhas persistidas (suporte a teste/diagnostico)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT corrida_id, exame_slug, equipamento_id, equipamento_modelo,
                       data_exame, hora_exame, lote, amostra_codigo, pocos,
                       resultado_geral, status_placa, targets_json
                FROM exam_runs
                ORDER BY id
                """
            ).fetchall()

        result: List[Dict[str, str]] = []
        for row in rows:
            payload = dict(row)
            targets = json.loads(payload.pop("targets_json") or "{}")
            payload.update({str(k): str(v) for k, v in targets.items()})
            result.append({str(k): str(v) for k, v in payload.items()})
        return result

    def update_status_fields_by_contract_key(
        self,
        updates: Mapping[tuple[str, str, str, str], Dict[str, str]],
    ) -> int:
        """
        Atualiza campos dinamicos em `targets_json` por chave contratual.

        Chave: (corrida_id, amostra_codigo, lote, data_exame) em formato normalizado.
        """
        if not updates:
            return 0

        updated_rows = 0
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            for key, payload in updates.items():
                if len(key) != 4:
                    continue
                corrida_id, amostra_codigo, lote, data_exame = key
                row = conn.execute(
                    """
                    SELECT id, targets_json
                    FROM exam_runs
                    WHERE lower(trim(corrida_id)) = ?
                      AND lower(trim(amostra_codigo)) = ?
                      AND lower(trim(lote)) = ?
                      AND lower(trim(data_exame)) = ?
                    LIMIT 1
                    """,
                    (corrida_id, amostra_codigo, lote, data_exame),
                ).fetchone()
                if row is None:
                    continue

                current_targets = json.loads(row["targets_json"] or "{}")
                changed = False
                for field, value in payload.items():
                    current = str(current_targets.get(field, "") or "")
                    desired = str(value or "")
                    if current != desired:
                        current_targets[field] = desired
                        changed = True

                if not changed:
                    continue

                conn.execute(
                    "UPDATE exam_runs SET targets_json = ? WHERE id = ?",
                    (json.dumps(current_targets, ensure_ascii=False, sort_keys=True), int(row["id"])),
                )
                updated_rows += 1
            conn.commit()
        return updated_rows
