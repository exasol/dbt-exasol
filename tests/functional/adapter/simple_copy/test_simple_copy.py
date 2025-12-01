import pytest

from dbt.tests.util import run_dbt

from dbt.tests.adapter.simple_copy.test_simple_copy import (
    SimpleCopyBase,
    EmptyModelsArentRunBase,
)


class TestSimpleCopyBaseExasol(SimpleCopyBase):
    @pytest.mark.xfail
    def test_simple_copy_with_materialized_views(self, project):
        pass


# This return a dictionary of table names to 'view' or 'table' values.
def exasol_get_tables_in_schema(self):
    sql = """
            select object_name,
                    case when object_type = 'TABLE' then 'table'
                            when object_type = 'VIEW' then 'view'
                            else object_type
                    end as materialization
            from SYS.EXA_USER_OBJECTS
            where {}
            order by object_name
            """
    sql = sql.format("{} like '{}'".format("ROOT_NAME", self.test_schema))
    result = self.run_sql(sql, fetch="all")
    return {model_name: materialization for (model_name, materialization) in result}


class TestEmptyModelsArentRunExasol(EmptyModelsArentRunBase):
    def test_dbt_doesnt_run_empty_models(self, project):
        results = run_dbt(["seed"])
        assert len(results) == 1
        results = run_dbt()
        assert len(results) == 7

        tables = exasol_get_tables_in_schema(self=project)

        assert "empty" not in tables.keys()
        assert "disabled" not in tables.keys()
