# -*- coding: utf-8 -*-
"""Repository SQL dedicado da trilha de fallback legado do menu."""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional


class MenuCatalogAuditRepository:
    """Encapsula persistencia/consulta SQL da trilha auditavel do menu."""

    def __init__(self, *, db_path: Path) -> None:
        self._db_path = Path(db_path)

    def _with_connection(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _accumulate_telemetry(
        telemetry: Optional[dict[str, int]],
        *,
        key: str,
        value: int,
    ) -> None:
        if telemetry is None:
            return
        telemetry[key] = int(telemetry.get(key, 0)) + int(value)

    @staticmethod
    def _to_epoch_seconds(value: str) -> int | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            return int(datetime.fromisoformat(raw).timestamp())
        except ValueError:
            return None

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS menu_catalog_fallback_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL,
                mode TEXT NOT NULL,
                outcome TEXT NOT NULL,
                error TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        existing_columns = {
            str(row[1]).strip().lower()
            for row in conn.execute("PRAGMA table_info(menu_catalog_fallback_audit)").fetchall()
        }
        if "timestamp_epoch" not in existing_columns:
            conn.execute(
                "ALTER TABLE menu_catalog_fallback_audit ADD COLUMN timestamp_epoch INTEGER"
            )
        if "created_at_epoch" not in existing_columns:
            conn.execute(
                "ALTER TABLE menu_catalog_fallback_audit ADD COLUMN created_at_epoch INTEGER"
            )

        conn.execute(
            """
            UPDATE menu_catalog_fallback_audit
            SET timestamp_epoch = CAST(strftime('%s', timestamp) AS INTEGER)
            WHERE timestamp_epoch IS NULL
              AND strftime('%s', timestamp) IS NOT NULL
            """
        )
        conn.execute(
            """
            UPDATE menu_catalog_fallback_audit
            SET created_at_epoch = CAST(strftime('%s', created_at) AS INTEGER)
            WHERE created_at_epoch IS NULL
              AND strftime('%s', created_at) IS NOT NULL
            """
        )

        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_menu_catalog_fallback_timestamp
            ON menu_catalog_fallback_audit(timestamp);

            CREATE INDEX IF NOT EXISTS idx_menu_catalog_fallback_timestamp_epoch
            ON menu_catalog_fallback_audit(timestamp_epoch);

            CREATE INDEX IF NOT EXISTS idx_menu_catalog_fallback_created_at
            ON menu_catalog_fallback_audit(created_at);

            CREATE INDEX IF NOT EXISTS idx_menu_catalog_fallback_created_at_epoch
            ON menu_catalog_fallback_audit(created_at_epoch);

            CREATE INDEX IF NOT EXISTS idx_menu_catalog_fallback_outcome
            ON menu_catalog_fallback_audit(outcome);
            """
        )

    def _execute_with_retry(
        self,
        operation: Callable[[sqlite3.Connection], Any],
        *,
        telemetry: Optional[dict[str, int]] = None,
    ) -> Any:
        attempts = 6
        delay = 0.05
        lock_retry_count = 0
        for attempt in range(1, attempts + 1):
            try:
                with self._with_connection() as conn:
                    self._ensure_schema(conn)
                    result = operation(conn)
                    conn.commit()
                    self._accumulate_telemetry(
                        telemetry,
                        key="lock_retry_count",
                        value=lock_retry_count,
                    )
                    return result
            except sqlite3.OperationalError as exc:
                is_lock_error = "locked" in str(exc).lower()
                if not is_lock_error or attempt >= attempts:
                    self._accumulate_telemetry(
                        telemetry,
                        key="lock_retry_count",
                        value=lock_retry_count,
                    )
                    raise
                lock_retry_count += 1
                time.sleep(delay * attempt)
        raise RuntimeError("unexpected_sql_retry_exit")

    def _apply_retention_rows(self, conn: sqlite3.Connection, *, max_rows: int) -> None:
        target = max(1, int(max_rows or 1))
        total = int(
            conn.execute("SELECT COUNT(1) FROM menu_catalog_fallback_audit").fetchone()[0]
        )
        overflow = total - target
        if overflow <= 0:
            return
        conn.execute(
            """
            DELETE FROM menu_catalog_fallback_audit
            WHERE id IN (
                SELECT id FROM menu_catalog_fallback_audit
                ORDER BY id ASC
                LIMIT ?
            )
            """,
            (overflow,),
        )

    def insert_event(
        self,
        *,
        timestamp: str,
        actor: str,
        mode: str,
        outcome: str,
        error: str,
        max_rows: int = 2000,
        created_at_epoch: Optional[int] = None,
        telemetry: Optional[dict[str, int]] = None,
    ) -> None:
        timestamp_epoch = self._to_epoch_seconds(timestamp)
        created_epoch = (
            int(created_at_epoch)
            if created_at_epoch is not None
            else int(time.time())
        )

        def _write(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                INSERT INTO menu_catalog_fallback_audit
                (timestamp, actor, mode, outcome, error, timestamp_epoch, created_at_epoch)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    actor,
                    mode,
                    outcome,
                    error,
                    timestamp_epoch,
                    created_epoch,
                ),
            )
            self._apply_retention_rows(conn, max_rows=max_rows)

        self._execute_with_retry(_write, telemetry=telemetry)

    def read_recent(
        self,
        *,
        limit: int,
        telemetry: Optional[dict[str, int]] = None,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, int(limit or 1))

        def _query(conn: sqlite3.Connection) -> list[dict[str, Any]]:
            rows = conn.execute(
                """
                SELECT timestamp, actor, mode, outcome, error
                FROM menu_catalog_fallback_audit
                ORDER BY id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
            normalized = [dict(row) for row in rows]
            normalized.reverse()
            return normalized

        return self._execute_with_retry(_query, telemetry=telemetry)

    def query_interval(
        self,
        *,
        start_epoch: int,
        end_epoch: int,
        allow_global_invalid_fallback: bool = True,
        telemetry: Optional[dict[str, int]] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        def _query_window(conn: sqlite3.Connection) -> tuple[list[dict[str, Any]], int]:
            rows = conn.execute(
                """
                SELECT timestamp, actor, mode, outcome, error
                FROM menu_catalog_fallback_audit
                WHERE timestamp_epoch IS NOT NULL
                  AND timestamp_epoch BETWEEN ? AND ?
                ORDER BY timestamp_epoch ASC, id ASC
                """,
                (int(start_epoch), int(end_epoch)),
            ).fetchall()
            invalid_count_window = conn.execute(
                """
                SELECT COUNT(1)
                FROM menu_catalog_fallback_audit
                WHERE timestamp_epoch IS NULL
                  AND created_at_epoch BETWEEN ? AND ?
                """,
                (int(start_epoch), int(end_epoch)),
            ).fetchone()[0]
            if int(invalid_count_window) > 0:
                return [dict(row) for row in rows], int(invalid_count_window)
            if not bool(allow_global_invalid_fallback):
                return [dict(row) for row in rows], 0

            # Compatibilidade transitoria: bancos legados podem nao ter
            # created_at_epoch coerente com a janela de referencia.
            invalid_count_global = conn.execute(
                """
                SELECT COUNT(1)
                FROM menu_catalog_fallback_audit
                WHERE timestamp_epoch IS NULL
                """
            ).fetchone()[0]
            return [dict(row) for row in rows], int(invalid_count_global)

        return self._execute_with_retry(_query_window, telemetry=telemetry)


__all__ = ["MenuCatalogAuditRepository"]
