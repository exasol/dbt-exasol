import os

import pytest
from dbt.tests.adapter.basic.files import config_materialized_view
from dbt.tests.util import run_dbt


@pytest.fixture(scope="class")
def dbt_profile_target():
    return {
        "type": "exasol",
        "threads": 8,
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
    @classmethod
    def models(cls):
        return {"view_model.sql": base_view_sql}

    def test_view(self, project):
        results = run_dbt(["build"], expect_pass=False)
        assert len(results) == 1
        assert results[0].status == "error"


class TestCustomTimestampFormat:
    @pytest.fixture(scope="class")
    @classmethod
    def seeds(cls):
        return {"ts_space.csv": seeds_tsspace_csv}

    def test_custom_ts_format(self, project):
        results = run_dbt(["seed"])
        assert len(results) == 1
        assert results[0].status == "success"


non_default_dbname_model_sql = "select 1 as id"


class TestNonDefaultDatabaseName:
    """Regression test for #257.

    ``exasol__list_relations_without_caching`` must report the profile's
    ``database`` (``dbname``) for every relation. With any other value the
    relations cache is keyed on a different database than the target relation,
    so ``get_relation()`` returns ``None`` for existing tables and every
    incremental model silently takes its first-run branch.
    """

    @pytest.fixture(scope="class")
    def dbt_profile_target(self):
        return {
            "type": "exasol",
            "threads": 8,
            "dsn": os.getenv("DBT_DSN", "localhost:8563"),
            "user": os.getenv("DBT_USER", "sys"),
            "pass": os.getenv("DBT_PASS", "exasol"),
            "dbname": "exa_db",
            "timestamp_format": "YYYY-MM-DD HH:MI:SS",
            "validate_server_certificate": False,
        }

    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {"dbname_model.sql": non_default_dbname_model_sql}

    def test_get_relation_finds_existing_table(self, project):
        run_dbt(["run"])

        relation = project.adapter.get_relation(
            database=project.database,
            schema=project.test_schema,
            identifier="dbname_model",
        )

        assert relation is not None, (
            "get_relation() did not find the table created by the previous run; "
            f"the relations cache is not keyed on the profile database {project.database!r}"
        )

    def test_listed_relations_carry_profile_database(self, project):
        run_dbt(["run"])

        relations = project.adapter.list_relations(database=project.database, schema=project.test_schema)

        assert relations, f"no relations listed for database {project.database!r}"
        assert {relation.database for relation in relations} == {project.database}
