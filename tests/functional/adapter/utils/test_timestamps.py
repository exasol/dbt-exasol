import pytest
from dbt.tests.adapter.utils.test_timestamps import BaseCurrentTimestamps

_MODEL_CURRENT_TIMESTAMP = """
select {{ current_timestamp() }} as curr_timestamp,
       {{ current_timestamp_in_utc_backcompat() }} as current_timestamp_in_utc_backcompat,
       {{ current_timestamp_backcompat() }} as current_timestamp_backcompat
"""

_MODEL_EXPECTED_SQL = """
select current_timestamp() as curr_timestamp,
       current_timestamp() as current_timestamp_in_utc_backcompat,
       current_timestamp() as current_timestamp_backcompat
"""


class TestCurrentTimestampsExasol(BaseCurrentTimestamps):
    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {"get_current_timestamp.sql": _MODEL_CURRENT_TIMESTAMP}

    # any adapters that don't want to check can set expected schema to None
    @pytest.fixture(scope="class")
    @classmethod
    def expected_sql(cls):
        return _MODEL_EXPECTED_SQL

    @pytest.fixture(scope="class")
    @classmethod
    def expected_schema(cls):
        return {
            "CURR_TIMESTAMP": "TIMESTAMP",
            "CURRENT_TIMESTAMP_IN_UTC_BACKCOMPAT": "TIMESTAMP",
            "CURRENT_TIMESTAMP_BACKCOMPAT": "TIMESTAMP",
        }
