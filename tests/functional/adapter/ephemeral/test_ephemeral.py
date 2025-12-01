import pytest
from dbt.tests.adapter.ephemeral.test_ephemeral import (
    BaseEphemeralMulti,
    BaseEphemeral,
    ephemeral_errors__dependent_sql,
    ephemeral_errors__base__base_sql,
    ephemeral_errors__base__base_copy_sql,
)
from dbt.tests.util import run_dbt, check_relations_equal


class TestEphemeralMultiExasol(BaseEphemeralMulti):
    def test_ephemeral_multi(self, project):
        run_dbt(["seed"])
        results = run_dbt(["run"])
        assert len(results) == 3
        check_relations_equal(
            project.adapter,
            ["SEED", "DEPENDENT", "DOUBLE_DEPENDENT", "SUPER_DEPENDENT"],
        )


class TestEphemeralNestedExasol(BaseEphemeral):
    pass


class TestEphemeralErrorHandling(BaseEphemeral):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "dependent.sql": ephemeral_errors__dependent_sql,
            "base": {
                "base.sql": ephemeral_errors__base__base_sql,
                "base_copy.sql": ephemeral_errors__base__base_copy_sql,
            },
        }

    def test_ephemeral_error_handling(self, project):
        results = run_dbt(["run"], expect_pass=False)
        assert len(results) == 1
        assert results[0].status == "skipped"
        assert "Compilation Error" in results[0].message
