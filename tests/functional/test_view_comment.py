import pytest
from dbt.tests.adapter.basic.files import (
    base_table_sql,
    generic_test_table_yml,
    generic_test_view_yml,
    schema_base_yml,
)
from dbt.tests.adapter.basic.test_generic_tests import BaseGenericTests


class TestExasolViewComment(BaseGenericTests):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "view_model.sql": """
                {{config(
                    materialized='view',
                    persist_docs={"relation": true, "columns": true }
                )}}
                select * from {{ source('raw', 'seed') }}
            """,
            "table_model.sql": base_table_sql,
            "schema.yml": schema_base_yml,
            "schema_view.yml": generic_test_view_yml,
            "schema_table.yml": generic_test_table_yml,
        }
