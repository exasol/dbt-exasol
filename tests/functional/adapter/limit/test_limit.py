import pytest
from dbt.tests.adapter.basic.test_base import BaseSimpleMaterializations
from dbt.tests.util import run_dbt, run_dbt_and_capture
from dbt.tests.adapter.dbt_show.test_dbt_show import BaseShowSqlHeader, BaseShowLimit
from tests.functional.adapter.limit.fixtures import exasol__sql_header


class TestLimitExasol(BaseSimpleMaterializations):
    def test_base(self, project):
        run_dbt(["seed"])
        run_dbt(["build"])

        (results, log_output) = run_dbt_and_capture(
            ["show", "--select", "view_model", "--limit", "5"]
        )
        assert len(results) == 1
        assert "Previewing node 'sample_model'" not in log_output
        assert "Previewing node 'view_model'" in log_output
        assert "5 | Hannah" in log_output
        assert "6 | Eleanor" not in log_output


class TestShowLimitExasol(BaseShowLimit):
    pass


class TestShowSqlHeaderExasol(BaseShowSqlHeader):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "sql_header.sql": exasol__sql_header,
        }
