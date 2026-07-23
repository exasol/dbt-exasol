import re

from dbt.tests.adapter.concurrency.test_concurrency import (
    BaseConcurrency,
    seeds__update_csv,
)
from dbt.tests.util import (
    check_relations_equal,
    check_table_does_not_exist,
    rm_file,
    run_dbt,
    run_dbt_and_capture,
    write_file,
)


class TestConcurrencyExasol(BaseConcurrency):
    def test_concurrency(self, project):
        run_dbt(["seed", "--select", "seed"])
        results = run_dbt(["run"], expect_pass=False)
        assert len(results) == 7
        check_relations_equal(project.adapter, ["seed", "view_model"])
        check_relations_equal(project.adapter, ["seed", "dep"])
        check_relations_equal(project.adapter, ["seed", "table_a"])
        check_relations_equal(project.adapter, ["seed", "table_b"])
        check_table_does_not_exist(project.adapter, "invalid")
        check_table_does_not_exist(project.adapter, "skip")

        rm_file(project.project_root, "seeds", "seed.csv")
        write_file(seeds__update_csv, project.project_root, "seeds", "seed.csv")

        results = run_dbt(["run"], expect_pass=False)
        assert len(results) == 7
        check_relations_equal(project.adapter, ["seed", "view_model"])
        check_relations_equal(project.adapter, ["seed", "dep"])
        check_relations_equal(project.adapter, ["seed", "table_a"])
        check_relations_equal(project.adapter, ["seed", "table_b"])
        check_table_does_not_exist(project.adapter, "invalid")
        check_table_does_not_exist(project.adapter, "skip")

        from collections import Counter
        from dbt.artifacts.schemas.results import RunStatus
        result_statuses = Counter([result.status for result in results])
        expected_statuses = {
            RunStatus.Success: 5,
            RunStatus.Error: 1,
            RunStatus.Skipped: 1,
        }
        assert result_statuses == expected_statuses
