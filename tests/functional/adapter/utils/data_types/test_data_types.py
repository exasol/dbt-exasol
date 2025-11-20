import os

import pytest
from dbt.tests.adapter.utils.data_types.test_type_boolean import BaseTypeBoolean
from dbt.tests.adapter.utils.data_types.test_type_float import BaseTypeFloat
from dbt.tests.adapter.utils.data_types.test_type_int import BaseTypeInt
from dbt.tests.adapter.utils.data_types.test_type_numeric import BaseTypeNumeric
from dbt.tests.adapter.utils.data_types.test_type_string import BaseTypeString
from dbt.tests.adapter.utils.data_types.test_type_timestamp import BaseTypeTimestamp
from test_type_bigint import BaseTypeBigInt


class TestTypeBigIntExasol(BaseTypeBigInt):
    pass


class TestTypeFloatExasol(BaseTypeFloat):
    pass


class TestTypeIntExasol(BaseTypeInt):
    pass


class TestTypeNumericExasol(BaseTypeNumeric):
    pass


class TestTypeStringExasol(BaseTypeString):
    pass


class TestTypeTimestampExasol(BaseTypeTimestamp):
    @pytest.fixture(scope="class")
    def dbt_profile_target(self):
        return {
            "type": "exasol",
            "threads": 1,
            "dsn": os.getenv("DBT_DSN", "localhost:8563"),
            "user": os.getenv("DBT_USER", "sys"),
            "pass": os.getenv("DBT_PASS", "exasol"),
            "dbname": "DB",
            "timestamp_format": "YYYY-MM-DD HH:MI:SS.FF6",
            "validate_server_certificate": False,
        }


class TestTypeBooleanExasol(BaseTypeBoolean):
    pass
