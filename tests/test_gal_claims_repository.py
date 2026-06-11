# -*- coding: utf-8 -*-
"""Testes do repositorio de claims/lease GAL (CONC-003 / FINDING-005).

Valida a semantica cross-process do claim atomico: aquisicao unica, bloqueio por
dono distinto, idempotencia permanente apos commit, reentrancia do mesmo dono,
recuperacao de lease expirado, release e contencao concorrente (um unico vencedor).
"""

import threading
import time

from services.gal.gal_claims import ClaimOutcome, SqliteGalClaimsRepository


def _repo(tmp_path, name="claims.db"):
    return SqliteGalClaimsRepository(tmp_path / name)


def test_acquire_then_held_by_other(tmp_path):
    repo = _repo(tmp_path)
    assert repo.try_claim(["k1", "k2"], owner="A", ttl_seconds=300) == ClaimOutcome.ACQUIRED
    assert repo.try_claim(["k1"], owner="B", ttl_seconds=300) == ClaimOutcome.HELD_BY_OTHER


def test_committed_blocks_as_already_committed(tmp_path):
    repo = _repo(tmp_path)
    repo.try_claim(["k1", "k2"], owner="A", ttl_seconds=300)
    repo.commit(["k1", "k2"], owner="A")
    assert repo.try_claim(["k1"], owner="B", ttl_seconds=300) == ClaimOutcome.ALREADY_COMMITTED
    assert repo.try_claim(["k2"], owner="A", ttl_seconds=300) == ClaimOutcome.ALREADY_COMMITTED


def test_same_owner_reentrant(tmp_path):
    repo = _repo(tmp_path)
    assert repo.try_claim(["k1"], owner="A", ttl_seconds=300) == ClaimOutcome.ACQUIRED
    assert repo.try_claim(["k1"], owner="A", ttl_seconds=300) == ClaimOutcome.ACQUIRED


def test_expired_lease_is_reclaimable(tmp_path):
    repo = _repo(tmp_path)
    # TTL 0 -> expira imediatamente; outro dono pode recuperar o lease orfao.
    assert repo.try_claim(["k1"], owner="A", ttl_seconds=0.0) == ClaimOutcome.ACQUIRED
    time.sleep(0.02)
    assert repo.try_claim(["k1"], owner="B", ttl_seconds=300) == ClaimOutcome.ACQUIRED


def test_release_allows_reclaim(tmp_path):
    repo = _repo(tmp_path)
    repo.try_claim(["k1"], owner="A", ttl_seconds=300)
    repo.release(["k1"], owner="A")
    assert repo.try_claim(["k1"], owner="B", ttl_seconds=300) == ClaimOutcome.ACQUIRED


def test_release_only_affects_own_inflight(tmp_path):
    repo = _repo(tmp_path)
    repo.try_claim(["k1"], owner="A", ttl_seconds=300)
    repo.release(["k1"], owner="B")  # nao e dono -> no-op
    assert repo.try_claim(["k1"], owner="C", ttl_seconds=300) == ClaimOutcome.HELD_BY_OTHER


def test_commit_only_by_owner(tmp_path):
    repo = _repo(tmp_path)
    repo.try_claim(["k1"], owner="A", ttl_seconds=300)
    repo.commit(["k1"], owner="B")  # nao dono -> no-op
    repo.commit(["k1"], owner="A")  # dono correto -> committed
    assert repo.try_claim(["k1"], owner="X", ttl_seconds=300) == ClaimOutcome.ALREADY_COMMITTED


def test_concurrent_contention_single_winner(tmp_path):
    repo = _repo(tmp_path)
    results: list[ClaimOutcome] = []
    lock = threading.Lock()

    def worker(name: str):
        outcome = repo.try_claim(["shared"], owner=name, ttl_seconds=300)
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=worker, args=(f"w{i}",)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    acquired = [r for r in results if r == ClaimOutcome.ACQUIRED]
    assert len(acquired) == 1, f"esperava exatamente 1 vencedor, obtive {results}"
    assert all(r == ClaimOutcome.HELD_BY_OTHER for r in results if r != ClaimOutcome.ACQUIRED)
