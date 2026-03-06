"""Integration tests for connection pool leak prevention.

These tests verify that the connection pool properly cleans up connections
against a real Exasol database, preventing session leaks (issue #182).

With the multi-slot pool (issue #183), up to N connections per credentials
key can be pooled, where N is the effective pool size (defaults to threads).
"""

import os

import pytest
from dbt.adapters.contracts.connection import Connection

from dbt.adapters.exasol.connections import (
    ExasolConnectionManager,
    ExasolCredentials,
)


@pytest.fixture()
def pool_credentials():
    """Create credentials for pool tests."""
    return ExasolCredentials(
        dsn=os.getenv("DBT_DSN", "localhost:8563"),
        user=os.getenv("DBT_USER", "sys"),
        password=os.getenv("DBT_PASS", "exasol"),
        database=os.getenv("DBT_DATABASE", "DB"),
        schema=os.getenv("DBT_SCHEMA", "public"),
        validate_server_certificate=False,
    )


@pytest.fixture(autouse=True)
def clean_pool():
    """Ensure pool is clean before and after each test."""
    ExasolConnectionManager.cleanup_pool()
    ExasolConnectionManager._pool_sizes.clear()
    ExasolConnectionManager._atexit_registered = False
    yield
    ExasolConnectionManager.cleanup_pool()
    ExasolConnectionManager._pool_sizes.clear()
    ExasolConnectionManager._atexit_registered = False


class TestConnectionPoolNoLeak:
    """Verify that opening and closing connections does not leak sessions."""

    def test_close_handle_pools_multiple_connections(self, pool_credentials):
        """With multi-slot pool, all N connections are pooled instead of just one.

        Reproduces the improvement from issue #183: with pool_size=4, opening 4
        connections and returning them should pool all 4 (not close 3 as before).
        """
        pool_key = ExasolConnectionManager._get_pool_key(pool_credentials)
        ExasolConnectionManager._pool_sizes[pool_key] = 4

        # Open 4 connections (simulating threads=4)
        connections = []
        for i in range(4):
            conn = Connection(
                type="exasol",
                name=f"test_{i}",
                state="init",
                credentials=pool_credentials,
            )
            conn = ExasolConnectionManager.open(conn)
            connections.append(conn)

        handles = [c.handle for c in connections]
        for h in handles:
            assert not h.is_closed, "Connection should be open after open()"

        # Return all connections via _close_handle
        for conn in connections:
            ExasolConnectionManager._close_handle(conn)

        # All 4 should be pooled (multi-slot pool)
        pool = ExasolConnectionManager._get_pool()
        assert len(pool[pool_key]) == 4, f"Multi-slot pool should have 4 connections, has {len(pool[pool_key])}"

        # All handles should still be open (in pool)
        closed_count = sum(1 for h in handles if h.is_closed)
        assert closed_count == 0, f"Expected 0 closed connections, but {closed_count} are closed."

    def test_cleanup_pool_closes_real_connections(self, pool_credentials):
        """cleanup_pool() should close real database connections."""
        pool_key = ExasolConnectionManager._get_pool_key(pool_credentials)
        ExasolConnectionManager._pool_sizes[pool_key] = 2

        # Open two connections simultaneously (so neither can reuse the other),
        # then return them both to the pool.
        conns = []
        for i in range(2):
            conn = Connection(
                type="exasol",
                name=f"test_cleanup_{i}",
                state="init",
                credentials=pool_credentials,
            )
            conn = ExasolConnectionManager.open(conn)
            conns.append(conn)

        handles = [c.handle for c in conns]

        for conn in conns:
            ExasolConnectionManager._close_handle(conn)

        # Pool should have 2 connections, all handles open
        pool = ExasolConnectionManager._get_pool()
        assert len(pool[pool_key]) == 2
        for h in handles:
            assert not h.is_closed

        # Cleanup pool
        ExasolConnectionManager.cleanup_pool()
        assert len(pool) == 0
        for h in handles:
            assert h.is_closed, "Pooled connection should be closed after cleanup"

    def test_multiple_open_close_cycles_no_leak(self, pool_credentials):
        """Multiple cycles of open + close should not accumulate sessions.

        With pool_size=4 and threads=4, at the end of every cycle exactly 4
        connections are pooled (reused in subsequent cycles), and the total
        number of open handles is bounded by pool_size.
        """
        pool_key = ExasolConnectionManager._get_pool_key(pool_credentials)
        ExasolConnectionManager._pool_sizes[pool_key] = 4

        # Use dict keyed by id() to deduplicate handles (pooled ones get reused)
        all_handles: dict[int, object] = {}

        # Simulate 3 dbt build cycles, each with 4 connections
        for cycle in range(3):
            connections = []
            for i in range(4):
                conn = Connection(
                    type="exasol",
                    name=f"cycle{cycle}_conn{i}",
                    state="init",
                    credentials=pool_credentials,
                )
                conn = ExasolConnectionManager.open(conn)
                connections.append(conn)
                all_handles[id(conn.handle)] = conn.handle

            for conn in connections:
                ExasolConnectionManager._close_handle(conn)

        # After 3 cycles, exactly 4 connections should be pooled
        pool = ExasolConnectionManager._get_pool()
        assert len(pool[pool_key]) == 4, f"Expected 4 pooled connections, has {len(pool[pool_key])}"

        # Count unique handles still open (should be exactly 4 — the pooled ones)
        unique_handles = list(all_handles.values())
        open_count = sum(1 for h in unique_handles if not h.is_closed)
        total_unique = len(unique_handles)
        assert open_count == 4, (
            f"Expected exactly 4 open connections (pooled) out of {total_unique} "
            f"unique handles, but {open_count} are open. "
            f"{open_count - 4} connections may have leaked."
        )

        # Clean up
        ExasolConnectionManager.cleanup_pool()

        # Now all should be closed
        open_after_cleanup = sum(1 for h in unique_handles if not h.is_closed)
        assert open_after_cleanup == 0, f"{open_after_cleanup} connections still open after cleanup_pool()"

    def test_excess_connections_closed_not_leaked(self, pool_credentials):
        """Connections exceeding pool_size are closed, not silently dropped.

        Opens N+2 connections with pool_size=N, closes them all, then verifies
        that every handle is either pooled or has is_closed=True.
        """
        pool_size = 2
        pool_key = ExasolConnectionManager._get_pool_key(pool_credentials)
        ExasolConnectionManager._pool_sizes[pool_key] = pool_size

        connections = []
        for i in range(pool_size + 2):
            conn = Connection(
                type="exasol",
                name=f"test_excess_{i}",
                state="init",
                credentials=pool_credentials,
            )
            conn = ExasolConnectionManager.open(conn)
            connections.append(conn)

        handles = [c.handle for c in connections]

        for conn in connections:
            ExasolConnectionManager._close_handle(conn)

        pool = ExasolConnectionManager._get_pool()
        pooled_ids = {id(h) for h in pool.get(pool_key, [])}

        for h in handles:
            assert id(h) in pooled_ids or h.is_closed, f"Handle {id(h)} is neither pooled nor closed — leaked!"

        assert len(pool.get(pool_key, [])) == pool_size

    def test_atexit_handler_registered_on_open(self, pool_credentials):
        """open() should register the atexit handler."""
        assert not ExasolConnectionManager._atexit_registered

        conn = Connection(
            type="exasol",
            name="test_atexit",
            state="init",
            credentials=pool_credentials,
        )
        conn = ExasolConnectionManager.open(conn)

        assert ExasolConnectionManager._atexit_registered
        ExasolConnectionManager._close_handle(conn)
