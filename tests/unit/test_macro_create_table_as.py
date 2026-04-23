"""Unit tests for exasol__create_table_as Jinja2 macro.

Tests that the macro produces atomic CTAS statements (no WITH NO DATA + INSERT pattern)
and that the contract-enforced path uses CAST expressions for type preservation.
"""

import re
import unittest

from jinja2 import Environment


def normalize_whitespace(s):
    """Normalize whitespace for comparison."""
    return re.sub(r"\s+", " ", s).strip()


# Macro sources (copied from the actual macro files for isolated testing)
EXASOL_GET_SELECT_SUBQUERY_MACRO = """
{% macro exasol__get_select_subquery(sql) %}
    {%- set user_provided_columns = model['columns'] -%}
    {%- set column_exprs = [] -%}
    {%- for col_name in user_provided_columns -%}
        {%- set col = user_provided_columns[col_name] -%}
        {%- set col_identifier = adapter.quote(col['name']) if col.get('quote') else col['name'] -%}
        {%- set column_exprs = column_exprs.append('CAST(' ~ col_identifier ~ ' AS ' ~ col['data_type'] ~ ') AS ' ~ col_identifier) -%}
    {%- endfor -%}
    select {{ column_exprs | join(', ') }}
    from (
        {{ sql }}
    ) as model_subq
{% endmacro %}
"""

EXASOL_CREATE_TABLE_AS_MACRO = """
{% macro exasol__create_table_as(temporary, relation, sql) -%}
    {%- set contract_config = config.get('contract') -%}
    {%- set partition_by_config = config.get('partition_by_config') -%}
    {%- set distribute_by_config = config.get('distribute_by_config') -%}
    {%- set primary_key_config = config.get('primary_key_config') -%}
    {%- if contract_config.enforced -%}
        {{- get_assert_columns_equivalent(sql) }}
        CREATE OR REPLACE TABLE {{ relation.schema }}.{{ relation.identifier }} AS
            {{ exasol__get_select_subquery(sql) }}
        {%- for col_name in model['columns'] -%}
            {%- set col = model['columns'][col_name] -%}
            {%- if col.get('constraints') -%}
                {%- for constraint in col['constraints'] -%}
                    {%- if constraint.type == 'not_null' -%}
|SEPARATEMEPLEASE|
    ALTER TABLE {{ relation.schema }}.{{ relation.identifier }} MODIFY COLUMN {{ adapter.quote(col['name']) if col.get('quote') else col['name'] }} NOT NULL;
                    {%- endif -%}
                {%- endfor -%}
            {%- endif -%}
        {%- endfor -%}
    {%- else -%}
        CREATE OR REPLACE TABLE {{ relation.schema }}.{{ relation.identifier }} AS
            {{ sql }}
    {%- endif -%}
    {{ add_constraints(relation, partition_by_config, distribute_by_config, primary_key_config) }}
{% endmacro %}
"""


class FakeAdapter:
    """Minimal mock adapter that quotes identifiers with double quotes."""

    @staticmethod
    def quote(identifier):
        return f'"{identifier}"'


class FakeConfig:
    """Mock config that returns values from a dict."""

    def __init__(self, values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


class FakeRelation:
    """Mock relation with schema and identifier."""

    def __init__(self, schema, identifier):
        self.schema = schema
        self.identifier = identifier

    def __str__(self):
        return f"{self.schema}.{self.identifier}"


class TestExasolCreateTableAs(unittest.TestCase):
    """Test exasol__create_table_as macro output."""

    def _render(self, model_columns, config_dict, relation, sql, contract_enforced=False):
        """Render the create_table_as macro with the given context.

        Args:
            model_columns: dict of column definitions
            config_dict: dict of config values
            relation: FakeRelation instance
            sql: user SQL
            contract_enforced: whether contract is enforced

        Returns:
            Normalized rendered SQL string
        """
        env = Environment(extensions=["jinja2.ext.do"])
        template_str = (
            EXASOL_GET_SELECT_SUBQUERY_MACRO
            + EXASOL_CREATE_TABLE_AS_MACRO
            + "{{ exasol__create_table_as(temporary, relation, sql) }}"
        )
        template = env.from_string(template_str)

        config = FakeConfig(config_dict)
        config._values["contract"] = type("", (), {"enforced": contract_enforced})()

        context = {
            "model": {"columns": model_columns},
            "adapter": FakeAdapter(),
            "config": config,
            "relation": relation,
            "sql": sql,
            "get_assert_columns_equivalent": lambda sql: "",
            "add_constraints": lambda *args, **kwargs: "",  # Empty for simplicity
        }
        result = template.render(**context, temporary=False)
        return result

    def test_non_contract_path_is_atomic_ctas(self):
        """Test that non-contract path produces a single atomic CTAS statement.

        This verifies there is no WITH NO DATA + INSERT INTO pattern.
        """
        config_dict = {
            "partition_by_config": None,
            "distribute_by_config": None,
            "primary_key_config": None,
        }
        relation = FakeRelation("myschema", "mytable")
        sql = "select 1 as id, 'blue' as color"

        result = self._render({}, config_dict, relation, sql, contract_enforced=False)
        normalized = normalize_whitespace(result)

        # Must have CREATE OR REPLACE TABLE ... AS
        self.assertIn("create or replace table myschema.mytable as", normalized.lower())
        # Must have the user SQL
        self.assertIn(sql, result)

        # Must NOT have the old patterns
        self.assertNotIn("with no data", normalized.lower())
        self.assertNotIn("insert into", normalized.lower())

    def test_contract_path_uses_cast_for_type_preservation(self):
        """Test that contract-enforced path uses CAST expressions for type preservation.

        This verifies that exasol__get_select_subquery wraps each column
        in CAST to preserve contract-defined types.
        """
        model_columns = {
            "id": {"name": "id", "data_type": "decimal(18,0)"},
            "color": {"name": "color", "data_type": "char(50)"},
            "date_day": {"name": "date_day", "data_type": "char(50)"},
        }
        config_dict = {
            "partition_by_config": None,
            "distribute_by_config": None,
            "primary_key_config": None,
        }
        relation = FakeRelation("myschema", "mytable")
        sql = "select 'blue' as color, 1 as id, '2019-01-01' as date_day"

        result = self._render(model_columns, config_dict, relation, sql, contract_enforced=True)
        normalized = normalize_whitespace(result)

        # Must use CAST expressions for column type enforcement
        self.assertIn("CAST(id AS decimal(18,0)) AS id", normalized)
        self.assertIn("CAST(color AS char(50)) AS color", normalized)
        self.assertIn("CAST(date_day AS char(50)) AS date_day", normalized)

        # Must NOT have the old patterns
        self.assertNotIn("with no data", normalized.lower())
        self.assertNotIn("insert into", normalized.lower())

    def test_contract_path_emits_not_null_alter(self):
        """Test that contract-enforced path emits ALTER TABLE MODIFY COLUMN NOT NULL."""
        model_columns = {
            "id": {
                "name": "id",
                "data_type": "decimal(18,0)",
                "constraints": [{"type": "not_null"}],
            },
            "color": {"name": "color", "data_type": "char(50)"},
        }
        config_dict = {
            "partition_by_config": None,
            "distribute_by_config": None,
            "primary_key_config": None,
        }
        relation = FakeRelation("myschema", "mytable")
        sql = "select 1 as id, 'blue' as color"

        result = self._render(model_columns, config_dict, relation, sql, contract_enforced=True)
        normalized = normalize_whitespace(result)

        # Must emit ALTER TABLE MODIFY COLUMN for NOT NULL constraint
        self.assertIn("alter table myschema.mytable modify column id not null", normalized.lower())

    def test_contract_path_with_quoted_not_null_column(self):
        """Test that NOT NULL ALTER TABLE uses quoted column name for reserved words."""
        model_columns = {
            "id": {
                "name": "id",
                "data_type": "decimal(18,0)",
                "constraints": [{"type": "not_null"}],
            },
            "from": {
                "name": "from",
                "data_type": "char(50)",
                "quote": True,
                "constraints": [{"type": "not_null"}],
            },
        }
        config_dict = {
            "partition_by_config": None,
            "distribute_by_config": None,
            "primary_key_config": None,
        }
        relation = FakeRelation("myschema", "mytable")
        sql = "select 1 as id, 'blue' as \"from\""

        result = self._render(model_columns, config_dict, relation, sql, contract_enforced=True)
        normalized = normalize_whitespace(result)

        # Quoted column name should use double quotes in ALTER TABLE
        self.assertIn('modify column "from" not null', normalized.lower())


if __name__ == "__main__":
    unittest.main()
