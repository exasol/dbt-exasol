"""
Test suite for dbt-exasol snapshot composite (multi-column) unique key functionality.

Tests that snapshots correctly handle unique_key as a list of columns.
"""

import pytest
from dbt.tests.util import run_dbt


# Seeds with composite key
seeds__seed_composite_csv = """region,product_id,sales,some_date
NA,PROD001,100,2019-12-31T00:00:00.000000
NA,PROD002,200,2019-12-31T00:00:00.000000
EU,PROD001,150,2019-12-31T00:00:00.000000
EU,PROD002,250,2019-12-31T00:00:00.000000
APAC,PROD001,120,2019-12-31T00:00:00.000000
"""

# Snapshot with composite unique_key (2 columns)
snapshots__snapshot_composite_sql = """
{% snapshot snapshot_composite %}
    {{
        config(
            target_schema=schema,
            strategy='timestamp',
            unique_key=['region', 'product_id'],
            updated_at='some_date'
        )
    }}
    select * from {{ ref('seed_composite') }}
{% endsnapshot %}
"""

# Snapshot with composite unique_key and hard_deletes='invalidate'
snapshots__snapshot_composite_invalidate_sql = """
{% snapshot snapshot_composite_invalidate %}
    {{
        config(
            target_schema=schema,
            strategy='timestamp',
            unique_key=['region', 'product_id'],
            updated_at='some_date',
            hard_deletes='invalidate'
        )
    }}
    select * from {{ ref('seed_composite') }}
{% endsnapshot %}
"""

# Snapshot with composite unique_key and hard_deletes='new_record'
snapshots__snapshot_composite_new_record_sql = """
{% snapshot snapshot_composite_new_record %}
    {{
        config(
            target_schema=schema,
            strategy='timestamp',
            unique_key=['region', 'product_id'],
            updated_at='some_date',
            hard_deletes='new_record'
        )
    }}
    select * from {{ ref('seed_composite') }}
{% endsnapshot %}
"""

# Snapshot with 3-column composite key
snapshots__snapshot_triple_key_sql = """
{% snapshot snapshot_triple_key %}
    {{
        config(
            target_schema=schema,
            strategy='timestamp',
            unique_key=['region', 'product_id', 'sales'],
            updated_at='some_date'
        )
    }}
    select * from {{ ref('seed_composite') }}
{% endsnapshot %}
"""


class TestSnapshotCompositeKey:
    """Test basic composite unique_key functionality"""

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"seed_composite.csv": seeds__seed_composite_csv}

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {"snapshot_composite.sql": snapshots__snapshot_composite_sql}

    def test_snapshot_composite_key_initial(self, project):
        """
        Test that initial snapshot with composite key creates correct records.
        """
        # Initial seed and snapshot
        run_dbt(["seed"])
        run_dbt(["snapshot"])

        # Verify: all 5 records should be created
        results = project.run_sql(
            "SELECT COUNT(*) as cnt FROM {schema}.snapshot_composite", fetch="one"
        )
        assert results[0] == 5, f"Expected 5 records, got {results[0]}"

        # Verify: all records should be current (dbt_valid_to is NULL)
        results = project.run_sql(
            "SELECT COUNT(*) as cnt FROM {schema}.snapshot_composite WHERE dbt_valid_to IS NULL",
            fetch="one",
        )
        assert results[0] == 5, f"Expected 5 current records, got {results[0]}"

    def test_snapshot_composite_key_update(self, project):
        """
        Test that updating a record identified by composite key works correctly.
        """
        # Initial seed and snapshot
        run_dbt(["seed"])
        run_dbt(["snapshot"])

        # Update record (NA, PROD001)
        project.run_sql(
            """UPDATE {schema}.seed_composite
               SET sales = 110, some_date = '2020-01-15T00:00:00.000000'
               WHERE region = 'NA' AND product_id = 'PROD001'"""
        )

        # Run snapshot again
        run_dbt(["snapshot"])

        # Verify: (NA, PROD001) should have 2 records
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_composite
               WHERE region = 'NA' AND product_id = 'PROD001'""",
            fetch="one",
        )
        assert results[0] == 2, (
            f"Expected 2 records for (NA, PROD001), got {results[0]}"
        )

        # Verify: old record should be closed out
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_composite
               WHERE region = 'NA' AND product_id = 'PROD001'
               AND sales = 100 AND dbt_valid_to IS NOT NULL""",
            fetch="one",
        )
        assert results[0] == 1, (
            f"Expected old record to be closed out, got {results[0]}"
        )

        # Verify: new record should be current
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_composite
               WHERE region = 'NA' AND product_id = 'PROD001'
               AND sales = 110 AND dbt_valid_to IS NULL""",
            fetch="one",
        )
        assert results[0] == 1, f"Expected new record to be current, got {results[0]}"

        # Verify: other records should not be affected
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_composite
               WHERE NOT (region = 'NA' AND product_id = 'PROD001')""",
            fetch="one",
        )
        assert results[0] == 4, f"Expected 4 other records unchanged, got {results[0]}"

    def test_snapshot_composite_key_multiple_updates(self, project):
        """
        Test updating multiple records with different composite keys.
        """
        # Initial seed and snapshot
        run_dbt(["seed"])
        run_dbt(["snapshot"])

        # Update two records
        project.run_sql(
            """UPDATE {schema}.seed_composite
               SET sales = 110, some_date = '2020-01-15T00:00:00.000000'
               WHERE region = 'NA' AND product_id = 'PROD001'"""
        )
        project.run_sql(
            """UPDATE {schema}.seed_composite
               SET sales = 160, some_date = '2020-01-15T00:00:00.000000'
               WHERE region = 'EU' AND product_id = 'PROD001'"""
        )

        # Run snapshot again
        run_dbt(["snapshot"])

        # Verify: total records should be 7 (5 original + 2 updates)
        results = project.run_sql(
            "SELECT COUNT(*) as cnt FROM {schema}.snapshot_composite", fetch="one"
        )
        assert results[0] == 7, f"Expected 7 total records, got {results[0]}"

        # Verify: 5 current records (2 updated + 3 unchanged)
        results = project.run_sql(
            "SELECT COUNT(*) as cnt FROM {schema}.snapshot_composite WHERE dbt_valid_to IS NULL",
            fetch="one",
        )
        assert results[0] == 5, f"Expected 5 current records, got {results[0]}"


class TestSnapshotCompositeKeyWithInvalidate:
    """Test composite unique_key with hard_deletes='invalidate'"""

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"seed_composite.csv": seeds__seed_composite_csv}

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {
            "snapshot_composite_invalidate.sql": snapshots__snapshot_composite_invalidate_sql
        }

    def test_snapshot_composite_key_delete_invalidate(self, project):
        """
        Test deleting a record identified by composite key with invalidate mode.
        """
        # Initial seed and snapshot
        run_dbt(["seed"])
        run_dbt(["snapshot"])

        # Delete record (NA, PROD001)
        project.run_sql(
            """DELETE FROM {schema}.seed_composite
               WHERE region = 'NA' AND product_id = 'PROD001'"""
        )

        # Run snapshot again
        run_dbt(["snapshot"])

        # Verify: (NA, PROD001) should have dbt_valid_to set
        results = project.run_sql(
            """SELECT dbt_valid_to FROM {schema}.snapshot_composite_invalidate
               WHERE region = 'NA' AND product_id = 'PROD001'""",
            fetch="one",
        )
        assert results[0] is not None, "Expected deleted record to be invalidated"

        # Verify: other records should still be current
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_composite_invalidate
               WHERE dbt_valid_to IS NULL""",
            fetch="one",
        )
        assert results[0] == 4, f"Expected 4 current records, got {results[0]}"


class TestSnapshotCompositeKeyWithNewRecord:
    """Test composite unique_key with hard_deletes='new_record'"""

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"seed_composite.csv": seeds__seed_composite_csv}

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {
            "snapshot_composite_new_record.sql": snapshots__snapshot_composite_new_record_sql
        }

    def test_snapshot_composite_key_delete_new_record(self, project):
        """
        Test deleting a record identified by composite key with new_record mode.
        """
        # Initial seed and snapshot
        run_dbt(["seed"])
        run_dbt(["snapshot"])

        # Verify initial state
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_composite_new_record
               WHERE dbt_is_deleted = 'False'""",
            fetch="one",
        )
        assert results[0] == 5, (
            f"Expected 5 records with dbt_is_deleted='False', got {results[0]}"
        )

        # Delete record (NA, PROD001)
        project.run_sql(
            """DELETE FROM {schema}.seed_composite
               WHERE region = 'NA' AND product_id = 'PROD001'"""
        )

        # Run snapshot again
        run_dbt(["snapshot"])

        # Verify: deletion record created for (NA, PROD001)
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_composite_new_record
               WHERE region = 'NA' AND product_id = 'PROD001' AND dbt_is_deleted = 'True'""",
            fetch="one",
        )
        assert results[0] == 1, f"Expected 1 deletion record, got {results[0]}"

        # Verify: total records for (NA, PROD001) should be 2
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_composite_new_record
               WHERE region = 'NA' AND product_id = 'PROD001'""",
            fetch="one",
        )
        assert results[0] == 2, (
            f"Expected 2 records for (NA, PROD001), got {results[0]}"
        )


class TestSnapshotTripleKey:
    """Test snapshot with 3-column composite unique_key"""

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"seed_composite.csv": seeds__seed_composite_csv}

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {"snapshot_triple_key.sql": snapshots__snapshot_triple_key_sql}

    def test_snapshot_triple_key_works(self, project):
        """
        Test that snapshot with 3-column unique_key works correctly.
        """
        # Initial seed and snapshot
        run_dbt(["seed"])
        run_dbt(["snapshot"])

        # Verify: all 5 records should be created
        results = project.run_sql(
            "SELECT COUNT(*) as cnt FROM {schema}.snapshot_triple_key", fetch="one"
        )
        assert results[0] == 5, f"Expected 5 records, got {results[0]}"

        # Verify: all records are current
        results = project.run_sql(
            "SELECT COUNT(*) as cnt FROM {schema}.snapshot_triple_key WHERE dbt_valid_to IS NULL",
            fetch="one",
        )
        assert results[0] == 5, f"Expected 5 current records, got {results[0]}"

        # Update a record - since sales is part of the key, this creates a new key
        project.run_sql(
            """UPDATE {schema}.seed_composite
               SET some_date = '2020-01-15T00:00:00.000000'
               WHERE region = 'NA' AND product_id = 'PROD001'"""
        )

        run_dbt(["snapshot"])

        # Verify: same record updated (key didn't change since sales unchanged)
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_triple_key
               WHERE region = 'NA' AND product_id = 'PROD001' AND sales = 100""",
            fetch="one",
        )
        assert results[0] == 2, f"Expected 2 records for same key, got {results[0]}"
