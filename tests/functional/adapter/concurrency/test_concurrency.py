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

        results, output = run_dbt_and_capture(["run"], expect_pass=False)
        assert len(results) == 7
        check_relations_equal(project.adapter, ["seed", "view_model"])
        check_relations_equal(project.adapter, ["seed", "dep"])
        check_relations_equal(project.adapter, ["seed", "table_a"])
        check_relations_equal(project.adapter, ["seed", "table_b"])
        check_table_does_not_exist(project.adapter, "invalid")
        check_table_does_not_exist(project.adapter, "skip")

        # Exasol appends NO-OP counts in the run summary, so allow that variant too.
        summary_pattern = r"PASS=5\s+WARN=0\s+ERROR=1\s+SKIP=1\s+(NO-OP=\d+\s+)?TOTAL=7"
        assert re.search(summary_pattern, output), output
