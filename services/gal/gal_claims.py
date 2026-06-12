# -*- coding: utf-8 -*-
"""Claim/lease interprocesso para envio GAL (CONC-003 / FINDING-005).

Fecha a janela de corrida entre estacoes (processos distintos) que a idempotencia
atual nao cobre: `inflight_keys` e apenas intra-processo e `successful_keys` e lido
uma unica vez do journal. Aqui cada amostra REIVINDICA (claim) suas chaves de
idempotencia de forma atomica e duravel, com validade temporal (lease/TTL), ANTES
do POST ao GAL.

Mecanismo: SQLite com `chave` como PRIMARY KEY e transacoes `BEGIN IMMEDIATE`
(serializa escritores entre processos). Um claim 'inflight' expira apos o TTL e
pode ser recuperado (reclaim) caso o dono tenha caido. Um claim 'committed' e
permanente (idempotencia de sucesso).

Concorrencia encapsulada no repositorio/porta — nao vaza para o caso de uso
(Constituicao 7). A validacao de SQLite em compartilhamento real e CONC-005.
"""

from __future__ import annotations

import os
import socket
import sqlite3
import time
from enum import Enum
from pathlib import Path
from typing import Protocol, Sequence


class ClaimOutcome(str, Enum):
    """Resultado de uma tentativa de claim."""

    ACQUIRED = "acquired"
    ALREADY_COMMITTED = "already_committed"
    HELD_BY_OTHER = "held_by_other"


class GalClaimsPort(Protocol):
    """Porta de reivindicacao de chaves de idempotencia GAL."""

    def try_claim(self, keys: Sequence[str], *, owner: str, ttl_seconds: float) -> ClaimOutcome: ...

    def commit(self, keys: Sequence[str], *, owner: str) -> None: ...

    def release(self, keys: Sequence[str], *, owner: str) -> None: ...


def default_owner_token(run_id: str = "") -> str:
    """Token de dono unico por estacao/execucao (host|pid|run_id)."""
    try:
        host = socket.gethostname()
    except Exception:
        host = "host"
    return f"{host}|{os.getpid()}|{run_id}"


def _norm_keys(keys: Sequence[str]) -> list[str]:
    # Remove vazias e duplicadas preservando ordem.
    return list(dict.fromkeys(str(k) for k in keys if str(k)))


class SqliteGalClaimsRepository:
    """Repositorio de claims em SQLite (cross-process via BEGIN IMMEDIATE)."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        # isolation_level=None -> autocommit; controlamos BEGIN/COMMIT explicitamente.
        conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS gal_claims (
                    chave TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )
        finally:
            conn.close()

    def try_claim(self, keys: Sequence[str], *, owner: str, ttl_seconds: float) -> ClaimOutcome:
        ks = _norm_keys(keys)
        if not ks:
            return ClaimOutcome.ACQUIRED
        now = time.time()
        expires = now + float(ttl_seconds)
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            placeholders = ",".join("?" for _ in ks)
            rows = conn.execute(
                f"SELECT chave, status, owner, expires_at FROM gal_claims WHERE chave IN ({placeholders})",
                ks,
            ).fetchall()
            for _chave, status, row_owner, row_expires in rows:
                if status == "committed":
                    conn.execute("ROLLBACK")
                    return ClaimOutcome.ALREADY_COMMITTED
                # inflight: bloqueia apenas se ainda valido e de OUTRO dono.
                if float(row_expires) > now and row_owner != owner:
                    conn.execute("ROLLBACK")
                    return ClaimOutcome.HELD_BY_OTHER
            # Adquire/recupera todas as chaves (upsert) — inclui reclaim de lease expirado.
            for chave in ks:
                conn.execute(
                    """
                    INSERT INTO gal_claims (chave, status, owner, created_at, expires_at)
                    VALUES (?, 'inflight', ?, ?, ?)
                    ON CONFLICT(chave) DO UPDATE SET
                        status='inflight', owner=excluded.owner,
                        created_at=excluded.created_at, expires_at=excluded.expires_at
                    """,
                    (chave, owner, now, expires),
                )
            conn.execute("COMMIT")
            return ClaimOutcome.ACQUIRED
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            conn.close()

    def commit(self, keys: Sequence[str], *, owner: str) -> None:
        ks = _norm_keys(keys)
        if not ks:
            return
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            for chave in ks:
                conn.execute(
                    "UPDATE gal_claims SET status='committed' WHERE chave=? AND owner=?",
                    (chave, owner),
                )
            conn.execute("COMMIT")
        finally:
            conn.close()

    def release(self, keys: Sequence[str], *, owner: str) -> None:
        ks = _norm_keys(keys)
        if not ks:
            return
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            for chave in ks:
                conn.execute(
                    "DELETE FROM gal_claims WHERE chave=? AND owner=? AND status='inflight'",
                    (chave, owner),
                )
            conn.execute("COMMIT")
        finally:
            conn.close()
