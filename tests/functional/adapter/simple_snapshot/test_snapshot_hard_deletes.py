"""
Test suite for dbt-exasol snapshot hard_deletes functionality.

Tests the two hard_deletes modes:
- 'invalidate': Sets dbt_valid_to timestamp when source record is deleted
- 'new_record': Creates new record with dbt_is_deleted='True' when source record is deleted
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

# Snapshot with hard_deletes='invalidate'
snapshots__snapshot_invalidate_sql = """
{% snapshot snapshot_invalidate %}
    {{
        config(
            target_schema=schema,
            strategy='timestamp',
            unique_key='id',
            updated_at='some_date',
            hard_deletes='invalidate'
        )
    }}
    select * from {{ ref('seed') }}
{% endsnapshot %}
"""

# Snapshot with hard_deletes='new_record'
snapshots__snapshot_new_record_sql = """
{% snapshot snapshot_new_record %}
    {{
        config(
            target_schema=schema,
            strategy='timestamp',
            unique_key='id',
            updated_at='some_date',
            hard_deletes='new_record'
        )
    }}
    select * from {{ ref('seed') }}
{% endsnapshot %}
"""


class TestSnapshotHardDeletesInvalidate:
    """Test hard_deletes='invalidate' mode - marks deleted records with dbt_valid_to timestamp"""

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"seed.csv": seeds__seed_csv}

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {"snapshot_invalidate.sql": snapshots__snapshot_invalidate_sql}

    def test_snapshot_hard_deletes_invalidate(self, project):
        """
        Test that when a source record is deleted, the snapshot record
        is invalidated by setting dbt_valid_to to the deletion timestamp.
        """
        # Initial seed and snapshot
        run_dbt(["seed"])
        run_dbt(["snapshot"])

        # Verify initial snapshot - all 5 records should be current (dbt_valid_to is NULL)
        results = project.run_sql(
            "SELECT COUNT(*) as cnt FROM {schema}.snapshot_invalidate WHERE dbt_valid_to IS NULL", fetch="one"
        )
        assert results[0] == 5, f"Expected 5 current records, got {results[0]}"

        # Delete record with id=1 from source
        project.run_sql("DELETE FROM {schema}.seed WHERE id = 1")

        # Run snapshot again
        run_dbt(["snapshot"])

        # Verify: record id=1 should now have dbt_valid_to set (invalidated)
        results = project.run_sql("SELECT dbt_valid_to FROM {schema}.snapshot_invalidate WHERE id = 1", fetch="one")
        assert results[0] is not None, "Expected dbt_valid_to to be set for deleted record"

        # Verify: other 4 records should still be current
        results = project.run_sql(
            "SELECT COUNT(*) as cnt FROM {schema}.snapshot_invalidate WHERE dbt_valid_to IS NULL", fetch="one"
        )
        assert results[0] == 4, f"Expected 4 current records, got {results[0]}"

        # Verify: total records should still be 5 (no new records created)
        results = project.run_sql("SELECT COUNT(*) as cnt FROM {schema}.snapshot_invalidate", fetch="one")
        assert results[0] == 5, f"Expected 5 total records, got {results[0]}"


class TestSnapshotHardDeletesNewRecord:
    """Test hard_deletes='new_record' mode - creates new record with dbt_is_deleted='True'"""

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"seed.csv": seeds__seed_csv}

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {"snapshot_new_record.sql": snapshots__snapshot_new_record_sql}

    def test_snapshot_hard_deletes_new_record(self, project):
        """
        Test that when a source record is deleted, a new snapshot record
        is created with dbt_is_deleted='True'.
        """
        # Initial seed and snapshot
        run_dbt(["seed"])
        run_dbt(["snapshot"])

        # Verify initial snapshot - all 5 records should have dbt_is_deleted='False'
        results = project.run_sql(
            "SELECT COUNT(*) as cnt FROM {schema}.snapshot_new_record WHERE dbt_is_deleted = 'False'", fetch="one"
        )
        assert results[0] == 5, f"Expected 5 records with dbt_is_deleted='False', got {results[0]}"

        # Verify dbt_is_deleted column exists
        results = project.run_sql("SELECT dbt_is_deleted FROM {schema}.snapshot_new_record WHERE id = 1", fetch="one")
        assert results[0] == "False", f"Expected dbt_is_deleted='False', got {results[0]}"

        # Delete record with id=1 from source
        project.run_sql("DELETE FROM {schema}.seed WHERE id = 1")

        # Run snapshot again
        run_dbt(["snapshot"])

        # Verify: a new record for id=1 should exist with dbt_is_deleted='True'
        results = project.run_sql(
            "SELECT COUNT(*) as cnt FROM {schema}.snapshot_new_record WHERE id = 1 AND dbt_is_deleted = 'True'",
            fetch="one",
        )
        assert results[0] == 1, f"Expected 1 deletion record for id=1, got {results[0]}"

        # Verify: total records for id=1 should be 2 (original + deletion record)
        results = project.run_sql("SELECT COUNT(*) as cnt FROM {schema}.snapshot_new_record WHERE id = 1", fetch="one")
        assert results[0] == 2, f"Expected 2 records for id=1, got {results[0]}"

        # Verify: the original record should have dbt_valid_to set
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_new_record
               WHERE id = 1 AND dbt_is_deleted = 'False' AND dbt_valid_to IS NOT NULL""",
            fetch="one",
        )
        assert results[0] == 1, f"Expected original record to be closed out, got {results[0]}"

        # Verify: total records should be 6 (5 original + 1 deletion record)
        results = project.run_sql("SELECT COUNT(*) as cnt FROM {schema}.snapshot_new_record", fetch="one")
        assert results[0] == 6, f"Expected 6 total records, got {results[0]}"

    def test_snapshot_hard_deletes_new_record_readd(self, project):
        """
        Test that when a deleted record reappears in source, a new active
        record is created (resurrection).
        """
        # Initial seed and snapshot
        run_dbt(["seed"])
        run_dbt(["snapshot"])

        # Delete record with id=2 from source
        project.run_sql("DELETE FROM {schema}.seed WHERE id = 2")
        run_dbt(["snapshot"])

        # Re-add record with id=2 (with updated date)
        project.run_sql(
            "INSERT INTO {schema}.seed (id, name, some_date) VALUES (2, 'Lillian', '2020-01-15T00:00:00.000000')"
        )
        run_dbt(["snapshot"])

        # Verify: id=2 should have 3 records (original, deletion, resurrection)
        results = project.run_sql("SELECT COUNT(*) as cnt FROM {schema}.snapshot_new_record WHERE id = 2", fetch="one")
        assert results[0] == 3, f"Expected 3 records for id=2, got {results[0]}"

        # Verify: latest record should be active (dbt_is_deleted='False', dbt_valid_to IS NULL)
        results = project.run_sql(
            """SELECT dbt_is_deleted FROM {schema}.snapshot_new_record
               WHERE id = 2 AND dbt_valid_to IS NULL
               ORDER BY dbt_valid_from DESC""",
            fetch="one",
        )
        assert results[0] == "False", f"Expected resurrected record to have dbt_is_deleted='False', got {results[0]}"
