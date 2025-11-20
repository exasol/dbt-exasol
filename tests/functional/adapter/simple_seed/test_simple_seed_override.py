import pytest, os
from dbt.tests.adapter.simple_seed.test_seed_type_override import (
    BaseSimpleSeedColumnOverride,
)
from dbt.tests.adapter.utils.base_utils import run_dbt

_SCHEMA_YML = """
version: 2
seeds:
- name: seed_enabled
  columns:
  - name: birthday
    tests:
    - column_type:
        type: VARCHAR(2000000)
  - name: seed_id
    tests:
    - column_type:
        type: DOUBLE

- name: seed_tricky
  columns:
  - name: seed_id
    tests:
    - column_type:
        type: DECIMAL(18,0)
  - name: seed_id_str
    tests:
    - column_type:
        type: VARCHAR(2000000)
  - name: a_bool
    tests:
    - column_type:
        type: BOOLEAN
  - name: looks_like_a_bool
    tests:
    - column_type:
        type: VARCHAR(2000000)
  - name: a_date
    tests:
    - column_type:
        type: TIMESTAMP
  - name: looks_like_a_date
    tests:
    - column_type:
        type: VARCHAR(2000000)
  - name: relative
    tests:
    - column_type:
        type: VARCHAR(2000000)
  - name: weekday
    tests:
    - column_type:
        type: VARCHAR(2000000)
""".lstrip()


class TestSimpleSeedColumnOverride(BaseSimpleSeedColumnOverride):
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

    @pytest.fixture(scope="class")
    def schema(self):
        return "simple_seed"

    @pytest.fixture(scope="class")
    def models(self):
        return {"models-exasol.yml": _SCHEMA_YML}

    @staticmethod
    def seed_enabled_types():
        return {
            "seed_id": "DOUBLE PRECISION",
            "birthday": "VARCHAR(2000000)",
        }

    @staticmethod
    def seed_tricky_types():
        return {
            "seed_id_str": "VARCHAR(2000000)",
            "looks_like_a_bool": "VARCHAR(2000000)",
            "looks_like_a_date": "VARCHAR(2000000)",
        }

    def test_exasol_simple_seed_with_column_override_exasol(self, project):
        seed_results = run_dbt(["seed"])
        assert len(seed_results) == 2
        test_results = run_dbt(["test"])
        assert len(test_results) == 10
