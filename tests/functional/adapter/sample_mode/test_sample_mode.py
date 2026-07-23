"""Sample-mode parity marker.

This explicit subclass of the upstream `BaseSampleModeTest` lives under
`sample_mode/` so the sample-mode parity claim is discoverable via
`pytest --collect-only`.

NOTE: Intentional duplication. The Exasol-specific sample-mode behaviour is also
exercised in `tests/functional/adapter/incremental/test_sample_mode.py` (which
holds the microbatch-driven `--sample` scenarios). Keep both files in sync; this
one is the discoverable parity marker, that one carries the Exasol-specific cases.
"""

import pytest
from dbt.tests.adapter.sample_mode.test_sample_mode import BaseSampleModeTest

# Exasol-compatible input model (no timezone suffix in timestamps).
_base_input_model_sql = """
{{ config(materialized='table', event_time='event_time') }}
select 1 as id, TIMESTAMP '2025-01-01 01:25:00' as event_time
union all
select 2 as id, TIMESTAMP '2025-01-02 13:47:00' as event_time
union all
select 3 as id, TIMESTAMP '2025-01-03 01:32:00' as event_time
"""


class TestExasolSampleMode(BaseSampleModeTest):
    """Upstream sample-mode parity proof (see module docstring cross-reference)."""

    @pytest.fixture(scope="class")
    def input_model_sql(self) -> str:
        return _base_input_model_sql
