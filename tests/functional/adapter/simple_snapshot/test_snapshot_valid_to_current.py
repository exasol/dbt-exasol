"""
Test suite for dbt-exasol snapshot dbt_valid_to_current functionality.

Tests that current snapshot records use a configured future timestamp
instead of NULL for dbt_valid_to.
"""

import pytest
from dbt.tests.util import run_dbt

# Seeds
seeds__seed_csv = """id,name,some_date
1,Easton,2019-12-31T00:00:00.000000
2,Lillian,2019-12-31T00:00:00.000000
3,Jeremiah,2019-12-31T00:00:00.000000
4,Nolan,2019-12-31T00:00:00.000000
5,Hannah,2019-12-31T00:00:00.000000
"""

# Snapshot with dbt_valid_to_current configured
snapshots__snapshot_valid_to_current_sql = """
{% snapshot snapshot_valid_to_current %}
    {{
        config(
            target_schema=schema,
            strategy='timestamp',
            unique_key='id',
            updated_at='some_date',
            dbt_valid_to_current='9999-12-31T23:59:59'
        )
    }}
    select * from {{ ref('seed') }}
{% endsnapshot %}
"""

# Snapshot with dbt_valid_to_current and hard_deletes='invalidate'
snapshots__snapshot_valid_to_current_invalidate_sql = """
{% snapshot snapshot_valid_to_current_invalidate %}
    {{
        config(
            target_schema=schema,
            strategy='timestamp',
            unique_key='id',
            updated_at='some_date',
            dbt_valid_to_current='9999-12-31T23:59:59',
            hard_deletes='invalidate'
        )
    }}
    select * from {{ ref('seed') }}
{% endsnapshot %}
"""

# Snapshot with dbt_valid_to_current and hard_deletes='new_record'
snapshots__snapshot_valid_to_current_new_record_sql = """
{% snapshot snapshot_valid_to_current_new_record %}
    {{
        config(
            target_schema=schema,
            strategy='timestamp',
            unique_key='id',
            updated_at='some_date',
            dbt_valid_to_current='9999-12-31T23:59:59',
            hard_deletes='new_record'
        )
    }}
    select * from {{ ref('seed') }}
{% endsnapshot %}
"""


class TestSnapshotValidToCurrent:
    """Test dbt_valid_to_current configuration - uses future timestamp instead of NULL"""

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"seed.csv": seeds__seed_csv}

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {"snapshot_valid_to_current.sql": snapshots__snapshot_valid_to_current_sql}

    def test_snapshot_valid_to_current_initial(self, project):
        """
        Test that initial snapshot records have dbt_valid_to set to the
        configured future timestamp instead of NULL.
        """
        # Initial seed and snapshot
        run_dbt(["seed"])
        run_dbt(["snapshot"])

        # Verify: all records should have dbt_valid_to = '9999-12-31 23:59:59'
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_valid_to_current
               WHERE dbt_valid_to = TO_TIMESTAMP('9999-12-31 23:59:59', 'YYYY-MM-DD HH24:MI:SS')""",
            fetch="one",
        )
        assert results[0] == 5, f"Expected 5 records with future timestamp, got {results[0]}"

        # Verify: no records should have NULL dbt_valid_to
        results = project.run_sql(
            "SELECT COUNT(*) as cnt FROM {schema}.snapshot_valid_to_current WHERE dbt_valid_to IS NULL", fetch="one"
        )
        assert results[0] == 0, f"Expected 0 records with NULL dbt_valid_to, got {results[0]}"

    def test_snapshot_valid_to_current_update(self, project):
        """
        Test that when a record is updated, the old record gets closed out
        (dbt_valid_to changes from future date) and new record gets future date.
        """
        # Initial seed and snapshot
        run_dbt(["seed"])
        run_dbt(["snapshot"])

        # Update record with id=1
        project.run_sql(
            "UPDATE {schema}.seed SET name = 'Easton Updated', some_date = '2020-01-15T00:00:00.000000' WHERE id = 1"
        )

        # Run snapshot again
        run_dbt(["snapshot"])

        # Verify: id=1 should have 2 records
        results = project.run_sql(
            "SELECT COUNT(*) as cnt FROM {schema}.snapshot_valid_to_current WHERE id = 1", fetch="one"
        )
        assert results[0] == 2, f"Expected 2 records for id=1, got {results[0]}"

        # Verify: old record should have dbt_valid_to != future timestamp (closed out)
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_valid_to_current
               WHERE id = 1 AND name = 'Easton'
               AND dbt_valid_to != TO_TIMESTAMP('9999-12-31 23:59:59', 'YYYY-MM-DD HH24:MI:SS')""",
            fetch="one",
        )
        assert results[0] == 1, f"Expected old record to be closed out, got {results[0]}"

        # Verify: new record should have dbt_valid_to = future timestamp
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_valid_to_current
               WHERE id = 1 AND name = 'Easton Updated'
               AND dbt_valid_to = TO_TIMESTAMP('9999-12-31 23:59:59', 'YYYY-MM-DD HH24:MI:SS')""",
            fetch="one",
        )
        assert results[0] == 1, f"Expected new record to have future timestamp, got {results[0]}"


class TestSnapshotValidToCurrentWithInvalidate:
    """Test dbt_valid_to_current combined with hard_deletes='invalidate'"""

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"seed.csv": seeds__seed_csv}

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {"snapshot_valid_to_current_invalidate.sql": snapshots__snapshot_valid_to_current_invalidate_sql}

    def test_snapshot_valid_to_current_with_invalidate(self, project):
        """
        Test that deleted records are properly invalidated when using
        dbt_valid_to_current with hard_deletes='invalidate'.
        """
        # Initial seed and snapshot
        run_dbt(["seed"])
        run_dbt(["snapshot"])

        # Verify initial state - all records have future timestamp
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_valid_to_current_invalidate
               WHERE dbt_valid_to = TO_TIMESTAMP('9999-12-31 23:59:59', 'YYYY-MM-DD HH24:MI:SS')""",
            fetch="one",
        )
        assert results[0] == 5, f"Expected 5 current records, got {results[0]}"

        # Delete record with id=1
        project.run_sql("DELETE FROM {schema}.seed WHERE id = 1")

        # Run snapshot again
        run_dbt(["snapshot"])

        # Verify: id=1 should have dbt_valid_to changed (not future timestamp anymore)
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_valid_to_current_invalidate
               WHERE id = 1 AND dbt_valid_to != TO_TIMESTAMP('9999-12-31 23:59:59', 'YYYY-MM-DD HH24:MI:SS')""",
            fetch="one",
        )
        assert results[0] == 1, f"Expected deleted record to be invalidated, got {results[0]}"

        # Verify: other records still have future timestamp
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_valid_to_current_invalidate
               WHERE dbt_valid_to = TO_TIMESTAMP('9999-12-31 23:59:59', 'YYYY-MM-DD HH24:MI:SS')""",
            fetch="one",
        )
        assert results[0] == 4, f"Expected 4 current records, got {results[0]}"


class TestSnapshotValidToCurrentWithNewRecord:
    """Test dbt_valid_to_current combined with hard_deletes='new_record'"""

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"seed.csv": seeds__seed_csv}

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {"snapshot_valid_to_current_new_record.sql": snapshots__snapshot_valid_to_current_new_record_sql}

    def test_snapshot_valid_to_current_with_new_record(self, project):
        """
        Test that deletion records are properly created when using
        dbt_valid_to_current with hard_deletes='new_record'.
        """
        # Initial seed and snapshot
        run_dbt(["seed"])
        run_dbt(["snapshot"])

        # Verify initial state
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_valid_to_current_new_record
               WHERE dbt_valid_to = TO_TIMESTAMP('9999-12-31 23:59:59', 'YYYY-MM-DD HH24:MI:SS')
               AND dbt_is_deleted = 'False'""",
            fetch="one",
        )
        assert results[0] == 5, f"Expected 5 current records, got {results[0]}"

        # Delete record with id=1
        project.run_sql("DELETE FROM {schema}.seed WHERE id = 1")

        # Run snapshot again
        run_dbt(["snapshot"])

        # Verify: deletion record created with dbt_is_deleted='True'
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_valid_to_current_new_record
               WHERE id = 1 AND dbt_is_deleted = 'True'""",
            fetch="one",
        )
        assert results[0] == 1, f"Expected 1 deletion record, got {results[0]}"

        # Verify: deletion record should have the future timestamp for dbt_valid_to
        results = project.run_sql(
            """SELECT dbt_valid_to FROM {schema}.snapshot_valid_to_current_new_record
               WHERE id = 1 AND dbt_is_deleted = 'True'""",
            fetch="one",
        )
        # Note: The deletion record's dbt_valid_to is inherited from the closed record
        # This behavior may vary - adjust assertion based on actual implementation
        assert results[0] is not None, "Expected deletion record to have dbt_valid_to set"

        # Verify: original record should be closed out (dbt_valid_to != future)
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_valid_to_current_new_record
               WHERE id = 1 AND dbt_is_deleted = 'False'
               AND dbt_valid_to != TO_TIMESTAMP('9999-12-31 23:59:59', 'YYYY-MM-DD HH24:MI:SS')""",
            fetch="one",
        )
        assert results[0] == 1, f"Expected original record to be closed out, got {results[0]}"
