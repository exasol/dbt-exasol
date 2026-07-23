import os

import pytest
from dbt.cli.main import dbtRunner

# Two sources across two schemas with three tables total, exercising the *batched*
# last-modified path (Capability.TableLastModifiedMetadataBatch: Full). The macro
# reads SYS.EXA_ALL_OBJECTS so cross-owner/cross-schema relations resolve in a single
# round-trip with an IN-style predicate.
freshness_via_metadata_schema_yml = """version: 2
sources:
  - name: test_source_a
    freshness:
      warn_after: {count: 10, period: hour}
      error_after: {count: 1, period: day}
    schema: "{{ env_var('DBT_GET_LAST_RELATION_TEST_SCHEMA_A') }}"
    loaded_at_field: ts
    tables:
      - name: test_table_1
      - name: test_table_2
  - name: test_source_b
    freshness:
      warn_after: {count: 10, period: hour}
      error_after: {count: 1, period: day}
    schema: "{{ env_var('DBT_GET_LAST_RELATION_TEST_SCHEMA_B') }}"
    loaded_at_field: ts
    tables:
      - name: test_table_3
"""


class TestGetRelationLastModified:
    @pytest.fixture(scope="class", autouse=True)
    def set_env_vars(self, project):
        os.environ["DBT_GET_LAST_RELATION_TEST_SCHEMA_A"] = project.test_schema
        os.environ["DBT_GET_LAST_RELATION_TEST_SCHEMA_B"] = f"{project.test_schema}_b"
        yield
        del os.environ["DBT_GET_LAST_RELATION_TEST_SCHEMA_A"]
        del os.environ["DBT_GET_LAST_RELATION_TEST_SCHEMA_B"]

    @pytest.fixture(scope="class")
    def models(self):
        return {"schema.yml": freshness_via_metadata_schema_yml}

    @pytest.fixture(scope="class")
    def custom_schemas(self, project, set_env_vars):
        schemas = [
            os.environ["DBT_GET_LAST_RELATION_TEST_SCHEMA_A"],
            os.environ["DBT_GET_LAST_RELATION_TEST_SCHEMA_B"],
        ]
        relations = []
        with project.adapter.connection_named("__test"):
            for schema in schemas:
                relation = project.adapter.Relation.create(database=project.database, schema=schema)
                project.adapter.drop_schema(relation)
                project.adapter.create_schema(relation)
                relations.append(relation)

        yield [r.schema for r in relations]

        with project.adapter.connection_named("__test"):
            for relation in relations:
                project.adapter.drop_schema(relation)

    def test_get_relation_last_modified(self, project, set_env_vars, custom_schemas):
        schema_a, schema_b = custom_schemas

        for schema, table in (
            (schema_a, "test_table_1"),
            (schema_a, "test_table_2"),
            (schema_b, "test_table_3"),
        ):
            project.run_sql(
                f"create table {schema}.{table} "
                "(id integer, name varchar(100) not null, ts timestamp default current_timestamp)"
            )
            project.run_sql(f"insert into {schema}.{table} (id, name) values (1, 'exasol')")

        project.run_sql("COMMIT")

        warning_or_error = False

        def probe(e):
            nonlocal warning_or_error
            if e.info.level in ["warning", "error"]:
                warning_or_error = True

        runner = dbtRunner(callbacks=[probe])
        # Batched freshness across 3 relations spanning 2 schemas/owners.
        runner.invoke(["source", "freshness"])

        # The 'source freshness' command should succeed without warnings or errors.
        assert not warning_or_error
