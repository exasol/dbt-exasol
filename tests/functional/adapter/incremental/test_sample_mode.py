"""TDD Cycle 6: Test sample mode works with Exasol.

Sample mode (--sample flag) runs dbt in "small-data" mode by building only
the N most recent time-based slices of models. This requires microbatch
support to be fully functional.
"""

import os
from unittest import mock

import freezegun
import pytest
from dbt.tests.adapter.sample_mode.test_sample_mode import BaseSampleModeTest
from dbt.tests.util import run_dbt

# Exasol-compatible input model (no timezone suffix in timestamps)
_input_model_sql = """
{{ config(materialized='table', event_time='event_time') }}
select 1 as id, TIMESTAMP '2020-01-15 10:00:00' as event_time
union all
select 2 as id, TIMESTAMP '2020-01-16 10:00:00' as event_time
union all
select 3 as id, TIMESTAMP '2020-01-17 10:00:00' as event_time
union all
select 4 as id, TIMESTAMP '2020-01-18 10:00:00' as event_time
union all
select 5 as id, TIMESTAMP '2020-01-19 10:00:00' as event_time
"""

_microbatch_model_sql = """
{{ config(
    materialized='incremental',
    incremental_strategy='microbatch',
    event_time='event_time',
    begin='2020-01-01',
    batch_size='day'
) }}
select * from {{ ref('input_model') }}
"""


class TestSampleModeTwoDays:
    """Test --sample flag with 2 days of batches."""

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "input_model.sql": _input_model_sql,
            "microbatch_model.sql": _microbatch_model_sql,
        }

    @mock.patch.dict(os.environ, {"DBT_EXPERIMENTAL_SAMPLE_MODE": "True"})
    @freezegun.freeze_time("2020-01-20T00:00:00Z")
    def test_sample_limits_batches(self, project):
        """--sample 2 should only process 2 most recent batches."""
        # First, run to build input_model
        run_dbt(["run", "--select", "input_model"])

        # Run microbatch with sample mode - should only get 2 most recent days
        run_dbt(["run", "--select", "microbatch_model", "--sample=2 days"])

        result = project.run_sql(
            "select count(*) as cnt from {schema}.microbatch_model",
            fetch="one",
        )
        # Should only have data from 2 most recent days (Jan 18 and Jan 19)
        assert result[0] == 2, f"--sample 2 should limit to 2 batches, got {result[0]}"


class TestSampleModeOneDay:
    """Test --sample flag with 1 day of batches."""

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "input_model.sql": _input_model_sql,
            "microbatch_model.sql": _microbatch_model_sql,
        }

    @mock.patch.dict(os.environ, {"DBT_EXPERIMENTAL_SAMPLE_MODE": "True"})
    @freezegun.freeze_time("2020-01-20T00:00:00Z")
    def test_sample_single_day(self, project):
        """--sample 1 day should only process the most recent batch."""
        # First, run to build input_model
        run_dbt(["run", "--select", "input_model"])

        # Run microbatch with sample mode - should only get most recent day
        run_dbt(["run", "--select", "microbatch_model", "--sample=1 day"])

        result = project.run_sql(
            "select count(*) as cnt from {schema}.microbatch_model",
            fetch="one",
        )
        # Should only have data from most recent day (Jan 19)
        assert result[0] == 1, f"--sample 1 day should limit to 1 batch, got {result[0]}"


# Exasol-compatible fixtures for base sample mode test
_base_input_model_sql = """
{{ config(materialized='table', event_time='event_time') }}
select 1 as id, TIMESTAMP '2025-01-01 01:25:00' as event_time
union all
select 2 as id, TIMESTAMP '2025-01-02 13:47:00' as event_time
union all
select 3 as id, TIMESTAMP '2025-01-03 01:32:00' as event_time
"""


class TestExasolSampleMode(BaseSampleModeTest):
    """Inherit standard sample mode tests from dbt-tests-adapter."""

    @pytest.fixture(scope="class")
    def input_model_sql(self) -> str:
        """Override input model with Exasol-compatible timestamp format."""
        return _base_input_model_sql
