"""Spike: verify Exasol's transaction-conflict behaviour for concurrent microbatch writes.

dbt-core's microbatch strategy materialises each batch as a DELETE (of the batch
window) + INSERT against the *same* target relation. When dbt declares
``Capability.MicrobatchConcurrency`` as supported, dbt-core schedules these batches
across threads concurrently.

This script reproduces that pattern by opening two ``pyexasol`` connections and
running disjoint DELETE+INSERT statements against one shared target table at the
same time. It records whether Exasol raises a transaction conflict (the expected
outcome — see ``openspec/changes/add-dbt-111-parity/design.md`` decision D3) or
whether both transactions commit cleanly.

Usage::

    EXASOL_DSN=host:8563 EXASOL_USER=sys EXASOL_PASSWORD=exasol \
        uv run python scripts/spikes/microbatch_concurrency.py

This is a manual de-risking spike, not part of the automated test suite. It
requires a live Exasol instance and is intentionally kept out of ``pytest``
collection.
"""

from __future__ import annotations

import os
import threading
import time

import pyexasol  # type: ignore[import-untyped]

DSN = os.environ.get("EXASOL_DSN", "localhost:8563")
USER = os.environ.get("EXASOL_USER", "sys")
PASSWORD = os.environ.get("EXASOL_PASSWORD", "exasol")
SCHEMA = os.environ.get("EXASOL_SCHEMA", "MICROBATCH_SPIKE")
TARGET = f"{SCHEMA}.EVENTS"


def _connect():
    return pyexasol.connect(dsn=DSN, user=USER, password=PASSWORD, autocommit=False)


def setup() -> None:
    con = _connect()
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    con.execute(f"DROP TABLE IF EXISTS {TARGET}")
    con.execute(f"CREATE TABLE {TARGET} (event_day INT, payload VARCHAR(50))")
    # Seed two disjoint date windows.
    con.execute(f"INSERT INTO {TARGET} VALUES (1, 'seed-1'), (2, 'seed-2')")
    con.commit()
    con.close()


def microbatch(day: int, results: dict[int, str], barrier: threading.Barrier) -> None:
    """Run one DELETE+INSERT 'batch' for a single disjoint day window."""
    con = _connect()
    try:
        # Ensure both threads start their write transaction at the same time.
        barrier.wait(timeout=30)
        con.execute(f"DELETE FROM {TARGET} WHERE event_day = {day}")
        con.execute(f"INSERT INTO {TARGET} VALUES ({day}, 'batch-{day}')")
        # Hold the transaction briefly to maximise the conflict window.
        time.sleep(0.5)
        con.commit()
        results[day] = "committed"
    except Exception as exc:  # noqa: BLE001 - we want the raw message
        results[day] = f"error: {type(exc).__name__}: {exc}"
    finally:
        con.close()


def main() -> None:
    setup()
    results: dict[int, str] = {}
    barrier = threading.Barrier(2)
    threads = [threading.Thread(target=microbatch, args=(day, results, barrier)) for day in (1, 2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print("=== Concurrent microbatch outcome ===")
    for day in sorted(results):
        print(f"  day={day}: {results[day]}")

    conflicts = [r for r in results.values() if "conflict" in r.lower() or r.startswith("error")]
    if conflicts:
        print("\nRESULT: transaction conflict / error observed -> keep MicrobatchConcurrency: Unsupported")
    else:
        print("\nRESULT: both batches committed cleanly -> ESCALATE before changing scope")


if __name__ == "__main__":
    main()
