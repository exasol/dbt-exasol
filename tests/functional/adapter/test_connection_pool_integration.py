"""Integration tests for connection pool leak prevention.

These tests verify that the connection pool properly cleans up connections
against a real Exasol database, preventing session leaks (issue #182).
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
    ExasolConnectionManager._atexit_registered = False
    yield
    ExasolConnectionManager.cleanup_pool()
    ExasolConnectionManager._atexit_registered = False


class TestConnectionPoolNoLeak:
    """Verify that opening and closing connections does not leak sessions."""

    def test_close_handle_does_not_leak_when_pool_occupied(self, pool_credentials):
        """Opening multiple connections and closing them should not leak sessions.

        Reproduces issue #182: with a single-slot pool, only one connection
        can be pooled. Extra connections must be explicitly closed.
        """
        # Open multiple connections (simulating threads > 1)
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

        # All handles should be open real connections
        handles = [c.handle for c in connections]
        for h in handles:
            assert not h.is_closed, "Connection should be open after open()"

        # Close all connections via _close_handle (as dbt does)
        for conn in connections:
            ExasolConnectionManager._close_handle(conn)

        # Exactly one should be pooled (open), rest must be closed
        pool = ExasolConnectionManager._get_pool()
        assert len(pool) == 1, f"Pool should have exactly 1 connection, has {len(pool)}"

        closed_count = sum(1 for h in handles if h.is_closed)
        assert closed_count == 3, (
            f"Expected 3 of 4 connections to be closed, but {closed_count} are closed. "
            f"This means {4 - closed_count - 1} connections leaked."
        )

        # The pooled connection should still be valid
        pooled = list(pool.values())[0]
        assert not pooled.is_closed

    def test_cleanup_pool_closes_real_connections(self, pool_credentials):
        """cleanup_pool() should close real database connections."""
        # Open a connection and return it to pool
        conn = Connection(
            type="exasol",
            name="test_cleanup",
            state="init",
            credentials=pool_credentials,
        )
        conn = ExasolConnectionManager.open(conn)
        handle = conn.handle
        ExasolConnectionManager._close_handle(conn)

        # Pool should have one connection, handle should be open
        pool = ExasolConnectionManager._get_pool()
        assert len(pool) == 1
        assert not handle.is_closed

        # Cleanup pool
        ExasolConnectionManager.cleanup_pool()
        assert len(pool) == 0
        assert handle.is_closed, "Pooled connection should be closed after cleanup"

    def test_multiple_open_close_cycles_no_leak(self, pool_credentials):
        """Multiple cycles of open + close should not accumulate sessions."""
        # Use dict keyed by id() to deduplicate handles (pooled ones get reused)
        all_handles = {}

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

        # After 3 cycles, only 1 connection should be pooled
        pool = ExasolConnectionManager._get_pool()
        assert len(pool) == 1

        # Count unique handles still open (should be exactly 1 — the pooled one)
        unique_handles = list(all_handles.values())
        open_count = sum(1 for h in unique_handles if not h.is_closed)
        total_unique = len(unique_handles)
        assert open_count == 1, (
            f"Expected exactly 1 open connection (pooled) out of {total_unique} "
            f"unique handles, but {open_count} are open. "
            f"{open_count - 1} connections leaked across 3 cycles."
        )

        # Clean up
        ExasolConnectionManager.cleanup_pool()

        # Now all should be closed
        open_after_cleanup = sum(1 for h in unique_handles if not h.is_closed)
        assert open_after_cleanup == 0, (
            f"{open_after_cleanup} connections still open after cleanup_pool()"
        )

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
