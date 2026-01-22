"""Test quoting configuration for sources and models (Issue #72)."""

import pytest
import os
from dbt.tests.util import run_dbt


# Source configuration with quoting enabled
sources__schema_yml = """
version: 2

sources:
  - name: test_source
    schema: "{{ var('test_schema') }}"
    quoting:
      schema: true
      identifier: true
    tables:
      - name: order
        identifier: seed_order
        columns:
          - name: id
          - name: status
      - name: order_overwrite
        identifier: seed_order
        quoting:
          identifier: false
        columns:
          - name: id
          - name: status
"""

# Seed data for the source table
seeds__seed_order_csv = """id,status
1,pending
2,completed
3,shipped
"""

# Model that selects from the quoted source
models__model_from_source_sql = """
select * from {{ source('test_source', 'order') }}
"""

# Model that selects from the source with overwritten quoting
models__model_from_source_overwrite_sql = """
select * from {{ source('test_source', 'order_overwrite') }}
"""

# Model with quoting config
models__quoted_model_sql = """
{{
    config(
        materialized='table',
        alias='MyTable'
    )
}}
select id, status from {{ source('test_source', 'order') }}
"""

# Schema for model with quoting
models__schema_yml = """
version: 2

models:
  - name: quoted_model
    quoting:
      identifier: true
    columns:
      - name: id
      - name: status
"""


class TestQuotingSourceConfiguration:
    """Test that quoting configuration in sources is respected."""

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"seed_order.csv": seeds__seed_order_csv}

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "sources.yml": sources__schema_yml,
            "schema.yml": models__schema_yml,
            "model_from_source.sql": models__model_from_source_sql,
            "model_from_source_overwrite.sql": models__model_from_source_overwrite_sql,
            "quoted_model.sql": models__quoted_model_sql,
        }

    @pytest.fixture(scope="class")
    def project_config_update(self, unique_schema):
        return {
            "vars": {
                "test_schema": unique_schema,
            },
        }

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

    def test_source_quoting_is_respected(self, project):
        """Test that source quoting configuration generates quoted identifiers in SQL."""
        # First, seed the data
        results = run_dbt(["seed"])
        assert len(results) == 1

        # Compile the models to check generated SQL
        run_dbt(["compile"])

        # Read the compiled SQL for model_from_source
        compiled_path = os.path.join(
            project.project_root,
            "target",
            "compiled",
            "test",
            "models",
            "model_from_source.sql",
        )

        with open(compiled_path, "r") as f:
            compiled_sql = f.read()

        # According to the spec, when quoting is enabled for schema and identifier,
        # the generated SQL should contain quoted identifiers like "TEST"."seed_order"
        # The schema should be quoted
        assert '"' in compiled_sql, (
            f"Expected quoted identifiers in compiled SQL but found none. "
            f"Compiled SQL: {compiled_sql}"
        )

        # Check that the identifier is quoted (should be "seed_order" not seed_order)
        # Note: Exasol uppercases unquoted identifiers, so we expect uppercase schema
        assert '"seed_order"' in compiled_sql or '"SEED_ORDER"' in compiled_sql, (
            f"Expected quoted identifier '\"seed_order\"' or '\"SEED_ORDER\"' in compiled SQL. "
            f"Compiled SQL: {compiled_sql}"
        )

    def test_source_quoting_overwrite_is_respected(self, project):
        """Test that table quoting config overwrites source quoting config."""
        # Compile the models to check generated SQL
        run_dbt(["compile"])

        # Read the compiled SQL for model_from_source_overwrite
        compiled_path = os.path.join(
            project.project_root,
            "target",
            "compiled",
            "test",
            "models",
            "model_from_source_overwrite.sql",
        )

        with open(compiled_path, "r") as f:
            compiled_sql = f.read()

        # Schema should be quoted (inherited from source config: true)
        assert '"' in compiled_sql, f"Expected quoting in compiled SQL: {compiled_sql}"

        # Identifier should NOT be quoted (overwritten in table config: false)
        # We expect seed_order to appear unquoted.
        assert "seed_order" in compiled_sql, (
            f"Expected identifier 'seed_order' in compiled SQL: {compiled_sql}"
        )
        assert '"seed_order"' not in compiled_sql, (
            f"Did not expect quoted '\"seed_order\"' in compiled SQL: {compiled_sql}"
        )
        assert '"SEED_ORDER"' not in compiled_sql, (
            f"Did not expect quoted '\"SEED_ORDER\"' in compiled SQL: {compiled_sql}"
        )

    def test_model_quoting_configuration(self, project):
        """Test that model quoting configuration is respected."""
        # Seed the data
        run_dbt(["seed"])

        # Compile the quoted_model
        run_dbt(["compile"])

        # Read the compiled SQL for quoted_model
        compiled_path = os.path.join(
            project.project_root,
            "target",
            "compiled",
            "test",
            "models",
            "quoted_model.sql",
        )

        with open(compiled_path, "r") as f:
            compiled_sql = f.read()

        # The source reference should be quoted based on source configuration
        assert '"seed_order"' in compiled_sql or '"SEED_ORDER"' in compiled_sql, (
            f"Expected quoted source identifier in compiled SQL. "
            f"Compiled SQL: {compiled_sql}"
        )
