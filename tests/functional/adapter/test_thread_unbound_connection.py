"""Functional tests for on-demand thread connection acquisition.

Verifies that adapter metadata methods (e.g. ``list_relations``) succeed when
called on a thread that has no bound connection (i.e. outside a
``connection_named`` / ``acquire_connection`` block).

Requirement: connection-pooling / On-Demand Thread Connection Acquisition
  - Scenario: Metadata call on a thread with no bound connection succeeds
  - Scenario: Lazily acquired connection is returned to the pool
"""

import pytest

from dbt.adapters.exasol.connections import ExasolConnectionManager

simple_model_sql = """
select 1 as id, cast('hello' as varchar(100)) as name
"""


class TestThreadUnboundConnection:
    """Adapter metadata calls succeed without an explicit connection_named block."""

    @pytest.fixture(scope="class")
    def models(self):
        return {"simple_model.sql": simple_model_sql}

    def test_list_relations_outside_connection_named(self, project):
        """list_relations on an unbound thread must not raise InvalidConnectionError.

        Scenario: Metadata call on a thread with no bound connection succeeds
        """
        from dbt.tests.util import run_dbt

        run_dbt(["run"])

        # Release any connection that run_dbt may have left on this thread,
        # so we start genuinely unbound.
        project.adapter.connections.clear_thread_connection()

        # This call must succeed — no connection_named wrapper.
        schema_relations = project.adapter.list_relations(database=project.database, schema=project.test_schema)

        identifiers = [r.identifier.upper() for r in schema_relations]
        assert "SIMPLE_MODEL" in identifiers, f"Expected SIMPLE_MODEL in schema relations, got: {identifiers}"

    def test_repeated_calls_no_session_leak(self, project):
        """Repeated thread-unbound metadata calls must not grow open session count.

        Scenario: Lazily acquired connection is returned to the pool
        """
        from dbt.tests.util import run_dbt

        run_dbt(["run"])

        credentials = project.adapter.config.credentials
        pool_key = ExasolConnectionManager._get_pool_key(credentials)

        # Release any connection left from the run step.
        project.adapter.connections.clear_thread_connection()

        # Call list_relations several times without any connection_named block.
        call_count = 5
        for _ in range(call_count):
            project.adapter.connections.clear_thread_connection()
            project.adapter.list_relations(database=project.database, schema=project.test_schema)
            # Explicitly release the lazily-acquired connection back to the pool.
            project.adapter.connections.release()

        # Pool size should be bounded (≤ effective pool size, not growing
        # by call_count).  The effective size defaults to profile.threads.
        pool = ExasolConnectionManager._get_pool()
        pool_entries = pool.get(pool_key, [])
        effective_pool_size = ExasolConnectionManager._pool_sizes.get(pool_key, 1)

        assert len(pool_entries) <= effective_pool_size, (
            f"Pool has {len(pool_entries)} entries after {call_count} unbound calls "
            f"but effective pool size is {effective_pool_size} — possible session leak."
        )
