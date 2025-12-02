"""
Test suite for dbt-exasol snapshot handling of reserved keywords in column names.

Tests that snapshots correctly handle reserved SQL keywords as column names,
such as 'time', 'date', 'user', etc.
"""
import pytest
from dbt.tests.util import run_dbt


# Model that creates a table with reserved keyword column names
# Using {{ config(materialized='table') }} to allow UPDATE/DELETE in tests
models__source_reserved_keywords_sql = """
{{ config(materialized='table') }}

select
    cast(1 as integer) as field_id,
    cast(100 as integer) as issue_id,
    cast('2019-12-31T10:00:00.000000' as timestamp) as "time",
    cast('alice' as varchar(50)) as "user",
    cast('2019-12-31' as date) as "date"
union all
select 2, 101, cast('2019-12-31T11:00:00.000000' as timestamp), 'bob', cast('2019-12-31' as date)
union all
select 3, 102, cast('2019-12-31T12:00:00.000000' as timestamp), 'charlie', cast('2019-12-31' as date)
union all
select 4, 103, cast('2019-12-31T13:00:00.000000' as timestamp), 'dave', cast('2019-12-31' as date)
union all
select 5, 104, cast('2019-12-31T14:00:00.000000' as timestamp), 'eve', cast('2019-12-31' as date)
"""

# Snapshot with reserved keyword in unique_key
# Note: Reserved keywords that were created with quotes (lowercase) need to be
# specified with quotes in the config: '"time"' and '"date"'
snapshots__snapshot_reserved_keywords_sql = """
{% snapshot snapshot_reserved_keywords %}
    {{
        config(
            target_schema=schema,
            strategy='timestamp',
            unique_key=['field_id', 'issue_id', '"time"'],
            updated_at='"date"'
        )
    }}
    select * from {{ ref('source_reserved_keywords') }}
{% endsnapshot %}
"""

# Snapshot with check strategy and reserved keywords
snapshots__snapshot_reserved_check_sql = """
{% snapshot snapshot_reserved_check %}
    {{
        config(
            target_schema=schema,
            strategy='check',
            unique_key=['field_id', 'issue_id'],
            check_cols=['"time"', '"user"', '"date"']
        )
    }}
    select * from {{ ref('source_reserved_keywords') }}
{% endsnapshot %}
"""

# Snapshot with reserved keywords and hard_deletes='new_record'
snapshots__snapshot_reserved_new_record_sql = """
{% snapshot snapshot_reserved_new_record %}
    {{
        config(
            target_schema=schema,
            strategy='timestamp',
            unique_key=['field_id', '"time"'],
            updated_at='"date"',
            hard_deletes='new_record'
        )
    }}
    select * from {{ ref('source_reserved_keywords') }}
{% endsnapshot %}
"""


class TestSnapshotReservedKeywords:
    """Test snapshots with reserved keywords in column names"""

    @pytest.fixture(scope="class")
    def models(self):
        return {"source_reserved_keywords.sql": models__source_reserved_keywords_sql}

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {"snapshot_reserved_keywords.sql": snapshots__snapshot_reserved_keywords_sql}

    def test_snapshot_reserved_keywords_initial(self, project):
        """
        Test that initial snapshot with reserved keywords in unique_key creates correct records.
        """
        # Initial model and snapshot
        run_dbt(["run"])
        run_dbt(["snapshot"])

        # Verify: all 5 records should be created
        results = project.run_sql(
            "SELECT COUNT(*) as cnt FROM {schema}.snapshot_reserved_keywords",
            fetch="one"
        )
        assert results[0] == 5, f"Expected 5 records, got {results[0]}"

        # Verify: all records should be current (dbt_valid_to is NULL)
        results = project.run_sql(
            "SELECT COUNT(*) as cnt FROM {schema}.snapshot_reserved_keywords WHERE dbt_valid_to IS NULL",
            fetch="one"
        )
        assert results[0] == 5, f"Expected 5 current records, got {results[0]}"

    def test_snapshot_reserved_keywords_update(self, project):
        """
        Test that updating a record identified by reserved keyword columns works correctly.
        """
        # Initial model and snapshot
        run_dbt(["run"])
        run_dbt(["snapshot"])

        # Update record with field_id=1
        project.run_sql(
            """UPDATE {schema}.source_reserved_keywords
               SET "user" = 'alice_updated', "date" = '2020-01-15'
               WHERE field_id = 1"""
        )

        # Run snapshot again
        run_dbt(["snapshot"])

        # Verify: record with field_id=1 should have 2 records
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_reserved_keywords
               WHERE field_id = 1""",
            fetch="one"
        )
        assert results[0] == 2, f"Expected 2 records for field_id=1, got {results[0]}"

        # Verify: old record should be closed out
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_reserved_keywords
               WHERE field_id = 1 AND "user" = 'alice' AND dbt_valid_to IS NOT NULL""",
            fetch="one"
        )
        assert results[0] == 1, f"Expected old record to be closed out, got {results[0]}"

        # Verify: new record should be current
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_reserved_keywords
               WHERE field_id = 1 AND "user" = 'alice_updated' AND dbt_valid_to IS NULL""",
            fetch="one"
        )
        assert results[0] == 1, f"Expected new record to be current, got {results[0]}"


class TestSnapshotReservedKeywordsCheck:
    """Test check strategy with reserved keywords in check_cols"""

    @pytest.fixture(scope="class")
    def models(self):
        return {"source_reserved_keywords.sql": models__source_reserved_keywords_sql}

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {"snapshot_reserved_check.sql": snapshots__snapshot_reserved_check_sql}

    def test_snapshot_reserved_check_initial(self, project):
        """
        Test that check strategy with reserved keywords works correctly.
        """
        # Initial model and snapshot
        run_dbt(["run"])
        run_dbt(["snapshot"])

        # Verify: all 5 records should be created
        results = project.run_sql(
            "SELECT COUNT(*) as cnt FROM {schema}.snapshot_reserved_check",
            fetch="one"
        )
        assert results[0] == 5, f"Expected 5 records, got {results[0]}"

    def test_snapshot_reserved_check_update(self, project):
        """
        Test that check strategy detects changes in reserved keyword columns.
        """
        # Initial model and snapshot
        run_dbt(["run"])
        run_dbt(["snapshot"])

        # Update the 'time' column (a reserved keyword)
        project.run_sql(
            """UPDATE {schema}.source_reserved_keywords
               SET "time" = TO_TIMESTAMP('2020-01-15T10:00:00.000000', 'YYYY-MM-DDTHH:MI:SS.FF6')
               WHERE field_id = 1"""
        )

        # Run snapshot again
        run_dbt(["snapshot"])

        # Verify: record with field_id=1 should have 2 records
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_reserved_check
               WHERE field_id = 1""",
            fetch="one"
        )
        assert results[0] == 2, f"Expected 2 records for field_id=1, got {results[0]}"


class TestSnapshotReservedKeywordsWithNewRecord:
    """Test reserved keywords with hard_deletes='new_record'"""

    @pytest.fixture(scope="class")
    def models(self):
        return {"source_reserved_keywords.sql": models__source_reserved_keywords_sql}

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {"snapshot_reserved_new_record.sql": snapshots__snapshot_reserved_new_record_sql}

    def test_snapshot_reserved_delete_new_record(self, project):
        """
        Test deleting a record identified by reserved keyword columns with new_record mode.
        """
        # Initial model and snapshot
        run_dbt(["run"])
        run_dbt(["snapshot"])

        # Verify initial state
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_reserved_new_record
               WHERE dbt_is_deleted = 'False'""",
            fetch="one"
        )
        assert results[0] == 5, f"Expected 5 records with dbt_is_deleted='False', got {results[0]}"

        # Delete record with field_id=1
        project.run_sql(
            """DELETE FROM {schema}.source_reserved_keywords
               WHERE field_id = 1"""
        )

        # Run snapshot again
        run_dbt(["snapshot"])

        # Verify: deletion record created for field_id=1
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_reserved_new_record
               WHERE field_id = 1 AND dbt_is_deleted = 'True'""",
            fetch="one"
        )
        assert results[0] == 1, f"Expected 1 deletion record, got {results[0]}"

        # Verify: total records for field_id=1 should be 2
        results = project.run_sql(
            """SELECT COUNT(*) as cnt FROM {schema}.snapshot_reserved_new_record
               WHERE field_id = 1""",
            fetch="one"
        )
        assert results[0] == 2, f"Expected 2 records for field_id=1, got {results[0]}"
