import pytest
from dbt.tests.adapter.utils.data_types.base_data_type_macro import BaseDataTypeMacro

models__expected_sql = """
select 999999999999999999999999999999999999 as bigint_col
""".lstrip()

models__actual_sql = """
select cast('999999999999999999999999999999999999' as {{ type_bigint() }}) as bigint_col
"""


class BaseTypeBigInt(BaseDataTypeMacro):
    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "expected.sql": models__expected_sql,
            "actual.sql": models__actual_sql,
        }
