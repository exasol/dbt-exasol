"""Tests for microbatch incremental strategy."""

import pytest
from dbt.tests.adapter.incremental.test_incremental_microbatch import BaseMicrobatch
from dbt.tests.util import run_dbt

# Exasol-compatible input model (no timezone suffix in timestamps)
_input_model_sql = """
{{ config(materialized='table', event_time='event_time') }}
select 1 as id, TIMESTAMP '2020-01-01 00:00:00' as event_time
union all
select 2 as id, TIMESTAMP '2020-01-02 00:00:00' as event_time
union all
select 3 as id, TIMESTAMP '2020-01-03 00:00:00' as event_time
"""


class TestMicrobatchExasol(BaseMicrobatch):
    """Test that microbatch strategy works with Exasol adapter."""

    @pytest.fixture(scope="class")
    def input_model_sql(self) -> str:
        """Override input model with Exasol-compatible timestamp format."""
        return _input_model_sql

    @pytest.fixture(scope="class")
    def insert_two_rows_sql(self, project) -> str:
        """Override insert SQL with Exasol-compatible timestamp format."""
        test_schema_relation = project.adapter.Relation.create(database=project.database, schema=project.test_schema)
        return f"insert into {test_schema_relation}.input_model (id, event_time) values (4, TIMESTAMP '2020-01-04 00:00:00'), (5, TIMESTAMP '2020-01-05 00:00:00')"


# Input model for lookback test (3 days of data with begin date close to data)
# Cast id to INTEGER to allow larger values in insert statements
_lookback_input_model_sql = """
{{ config(materialized='table', event_time='event_time') }}
select cast(1 as integer) as id, TIMESTAMP '2020-01-01 10:00:00' as event_time
union all
select cast(2 as integer) as id, TIMESTAMP '2020-01-02 10:00:00' as event_time
union all
select cast(3 as integer) as id, TIMESTAMP '2020-01-03 10:00:00' as event_time
"""

# Microbatch model with lookback=2
_microbatch_with_lookback_sql = """
{{ config(
    materialized='incremental',
    incremental_strategy='microbatch',
    event_time='event_time',
    begin='2020-01-01',
    batch_size='day',
    lookback=2
) }}
select * from {{ ref('input_model') }}
"""


class TestMicrobatchLookback:
    """Test lookback configuration is accepted by microbatch models.

    Note: Full lookback behavior (reprocessing previous batches for late-arriving
    data) is handled by dbt-core's automatic batch calculation. This test verifies
    that the lookback configuration is accepted and the model runs correctly.
    """

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "input_model.sql": _lookback_input_model_sql,
            "microbatch_model.sql": _microbatch_with_lookback_sql,
        }

    def test_lookback_config_accepted(self, project):
        """Model with lookback=2 should run successfully."""
        # Run with explicit time range to ensure predictable behavior
        run_dbt(
            [
                "run",
                "--event-time-start",
                "2020-01-01",
                "--event-time-end",
                "2020-01-04",
            ]
        )

        # Verify all data was processed
        result = project.run_sql(
            "select count(*) as cnt from {schema}.microbatch_model",
            fetch="one",
        )
        assert result[0] == 3, f"Expected 3 rows after run, got {result[0]}"

    def test_lookback_incremental_run(self, project):
        """Incremental run should work with lookback configuration."""
        # First run - full backfill
        run_dbt(
            [
                "run",
                "--event-time-start",
                "2020-01-01",
                "--event-time-end",
                "2020-01-04",
            ]
        )

        # Insert new data for day 3
        project.run_sql(
            """
            insert into {schema}.input_model (id, event_time)
            values (99, TIMESTAMP '2020-01-03 12:00:00')
        """
        )

        # Second run - only select microbatch model to avoid rebuilding input
        run_dbt(
            [
                "run",
                "--select",
                "microbatch_model",
                "--event-time-start",
                "2020-01-03",
                "--event-time-end",
                "2020-01-04",
            ]
        )

        # Verify new data was picked up
        result = project.run_sql(
            "select count(*) as cnt from {schema}.microbatch_model where id = 99",
            fetch="one",
        )
        assert result[0] == 1, "New data should be included in incremental run"
