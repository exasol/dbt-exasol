import os

import pytest
from dbt.tests.adapter.basic.files import config_materialized_view
from dbt.tests.util import run_dbt


@pytest.fixture(scope="class")
def dbt_profile_target():
    return {
        "type": "exasol",
        "threads": 1,
        "dsn": os.getenv("DBT_DSN", "localhost:8563"),
        "user": os.getenv("DBT_USER", "sys"),
        "pass": os.getenv("DBT_PASS", "exasol"),
        "dbname": "DB",
        "timestamp_format": "YYYY-MM-DD HH:MI:SS",
        "validate_server_certificate": False,
    }


base_view_sql = config_materialized_view + "select 1 as id;"

seeds_tsspace_csv = """
id,name,some_date
1,Easton,1981-05-20 06:46:51
2,Lillian,1978-09-03 18:10:33
3,Jeremiah,1982-03-11 03:59:51
4,Nolan,1976-05-06 20:21:35
5,Hannah,1982-06-23 05:41:26
6,Eleanor,1991-08-10 23:12:21
7,Lily,1971-03-29 14:58:02
8,Jonathan,1988-02-26 02:55:24
9,Adrian,1994-02-09 13:14:23
10,Nora,1976-03-01 16:51:39
""".lstrip()


class TestViewModelSemicolon:
    @pytest.fixture(scope="class")
    def models(self):
        return {"view_model.sql": base_view_sql}

    def test_view(self, project):
        results = run_dbt(["build"], expect_pass=False)
        assert len(results) == 1
        assert results[0].status == "error"


class TestCustomTimestampFormat:
    @pytest.fixture(scope="class")
    def seeds(self):
        return {"ts_space.csv": seeds_tsspace_csv}

    def test_custom_ts_format(self, project):
        results = run_dbt(["seed"])
        assert len(results) == 1
        assert results[0].status == "success"
