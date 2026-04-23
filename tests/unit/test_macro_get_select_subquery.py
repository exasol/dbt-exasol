"""Unit tests for exasol__get_select_subquery Jinja2 macro.

Tests that the macro correctly emits CAST expressions for each column
with the contract-defined data type, and handles quoted column names.

These tests use Jinja2 to render the macro directly, providing mock
objects for the dbt-specific context (model, adapter, config).
"""

import re
import unittest

from jinja2 import Environment


def normalize_whitespace(s):
    """Normalize whitespace for comparison."""
    return re.sub(r"\s+", " ", s).strip()


# Macro source for exasol__get_select_subquery (copied from adapters.sql
# for isolated testing — the source of truth is the macro file itself)
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


class FakeAdapter:
    """Minimal mock adapter that quotes identifiers with double quotes."""

    @staticmethod
    def quote(identifier):
        return f'"{identifier}"'


class TestExasolGetSelectSubquery(unittest.TestCase):
    """Test exasol__get_select_subquery macro output."""

    def _render_macro(self, model_columns, sql, adapter=None):
        """Render the macro with the given context.

        Args:
            model_columns: dict of column definitions (name, data_type, etc.)
            sql: the user SQL to wrap
            adapter: mock adapter (defaults to FakeAdapter)

        Returns:
            Rendered SQL string
        """
        if adapter is None:
            adapter = FakeAdapter()

        env = Environment(extensions=["jinja2.ext.do"])
        wrapper = env.from_string(EXASOL_GET_SELECT_SUBQUERY_MACRO + "{{ exasol__get_select_subquery(sql) }}")
        context = {
            "model": {"columns": model_columns},
            "adapter": adapter,
        }
        return wrapper.render(**context, sql=sql)

    def test_basic_cast_expressions(self):
        """Test that CAST is emitted for each column with correct contract type."""
        model_columns = {
            "id": {"name": "id", "data_type": "decimal(18,0)"},
            "color": {"name": "color", "data_type": "char(50)"},
            "date_day": {"name": "date_day", "data_type": "char(50)"},
        }
        sql = "select 'blue' as color, 1 as id, '2019-01-01' as date_day"

        result = self._render_macro(model_columns, sql)
        normalized = normalize_whitespace(result)

        # Each column should have a CAST expression with the correct type
        self.assertIn("CAST(id AS decimal(18,0)) AS id", normalized)
        self.assertIn("CAST(color AS char(50)) AS color", normalized)
        self.assertIn("CAST(date_day AS char(50)) AS date_day", normalized)

        # Should wrap user SQL in subquery
        self.assertIn("from (", normalized)
        self.assertIn(") as model_subq", normalized)

    def test_quoted_column_names(self):
        """Test that quoted column names are preserved in CAST expressions."""
        model_columns = {
            "id": {"name": "id", "data_type": "decimal(18,0)"},
            "from": {"name": "from", "data_type": "char(50)", "quote": True},
            "date_day": {"name": "date_day", "data_type": "char(50)"},
        }
        sql = "select 'blue' as \"from\", 1 as id, '2019-01-01' as date_day"

        result = self._render_macro(model_columns, sql)
        normalized = normalize_whitespace(result)

        # Quoted column should use double quotes in CAST
        self.assertIn('CAST("from" AS char(50)) AS "from"', normalized)
        # Unquoted columns should not have double quotes
        self.assertIn("CAST(id AS decimal(18,0)) AS id", normalized)
        self.assertIn("CAST(date_day AS char(50)) AS date_day", normalized)

    def test_single_column(self):
        """Test macro with a single column."""
        model_columns = {
            "value": {"name": "value", "data_type": "decimal(18,0)"},
        }
        sql = "select 1 as value"

        result = self._render_macro(model_columns, sql)
        normalized = normalize_whitespace(result)

        self.assertIn("CAST(value AS decimal(18,0)) AS value", normalized)
        self.assertIn("from (", normalized)

    def test_all_columns_have_cast(self):
        """Test that ALL columns get CAST, not just some."""
        model_columns = {
            "a": {"name": "a", "data_type": "integer"},
            "b": {"name": "b", "data_type": "varchar(100)"},
            "c": {"name": "c", "data_type": "timestamp"},
        }
        sql = "select * from some_table"

        result = self._render_macro(model_columns, sql)
        normalized = normalize_whitespace(result)

        self.assertIn("CAST(a AS integer) AS a", normalized)
        self.assertIn("CAST(b AS varchar(100)) AS b", normalized)
        self.assertIn("CAST(c AS timestamp) AS c", normalized)

    def test_user_sql_preserved_in_subquery(self):
        """Test that the user SQL is preserved inside the subquery."""
        model_columns = {
            "id": {"name": "id", "data_type": "decimal(18,0)"},
        }
        original_sql = "select 1 as id from my_table where status = 'active'"

        result = self._render_macro(model_columns, original_sql)
        # The original SQL should appear inside the subquery
        self.assertIn(original_sql, result)


if __name__ == "__main__":
    unittest.main()
