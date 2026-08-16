# pylint: disable=duplicate-code
"""Functional tests for ``ExasolColumn`` API via ``run-operation`` macros.

``from_description`` is never called by dbt-core 1.12 nor by any Exasol adapter
macro -- it is reachable *only* through ``api.Column`` in Jinja. The tests
below exercise every branch through a real ``dbt run-operation``, which runs
inside the adapter/Jinja context and counts as functional coverage.

Coverage target (column.py):
  56  (string_size() on non-string → error)
  68-102  (from_description: simple types, HASHTYPE(16 BYTE), DECIMAL(x,y), invalid)
"""

import os

import pytest
from dbt.tests.util import run_dbt

_macros = {
    "assert_from_description.sql": """
{% macro assert_from_description() %}
  {# DECIMAL with precision + scale -- exercises the 2-part size branch #}
  {% set c = api.Column.from_description('c', 'DECIMAL(18,0)') %}
  {% if c.numeric_precision != 18 or c.numeric_scale != 0 %}
    {{ exceptions.raise_compiler_error('bad decimal precision/scale') }}
  {% endif %}

  {# HASHTYPE with a byte qualifier -- exercises the regex strip + single-part size branch #}
  {% set h = api.Column.from_description('h', 'HASHTYPE(16 BYTE)') %}
  {% if h.char_size != 16 %}
    {{ exceptions.raise_compiler_error('bad hashtype char_size') }}
  {% endif %}
  {% if not h.is_hashtype() %}
    {{ exceptions.raise_compiler_error('hashtype not detected') }}
  {% endif %}

  {# VARCHAR with size #}
  {% set v = api.Column.from_description('v', 'VARCHAR(100)') %}
  {% if v.string_size() != 100 %}
    {{ exceptions.raise_compiler_error('bad varchar string_size') }}
  {% endif %}
  {% if not v.is_string() %}
    {{ exceptions.raise_compiler_error('varchar not string') }}
  {% endif %}

  {# Bare type with no size info -- exercises the ``size_info is None`` branch #}
  {% set b = api.Column.from_description('b', 'BOOLEAN') %}
  {% if not b.is_boolean() %}
    {{ exceptions.raise_compiler_error('boolean not detected') }}
  {% endif %}

  select 1 as result
{% endmacro %}
""",
    "bad_char_size.sql": """
{% macro bad_char_size() %}
  {% do api.Column.from_description('x', 'VARCHAR(abc)') %}
{% endmacro %}
""",
    "bad_precision.sql": """
{% macro bad_precision() %}
  {% do api.Column.from_description('x', 'DECIMAL(a,0)') %}
{% endmacro %}
""",
    "bad_scale.sql": """
{% macro bad_scale() %}
  {% do api.Column.from_description('x', 'DECIMAL(18,b)') %}
{% endmacro %}
""",
    "string_size_on_numeric.sql": """
{% macro string_size_on_numeric() %}
  {% do api.Column('n', 'decimal', none, 18, 0).string_size() %}
{% endmacro %}
""",
    "bad_type_unparseable.sql": """
{% macro bad_type_unparseable() %}
  {% do api.Column.from_description('x', '') %}
{% endmacro %}
""",
}


class TestColumnFromDescription:
    """Exercise ``ExasolColumn.from_description`` happy path through ``run-operation``."""

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
    def macros(self):
        return _macros

    def test_from_description_happy_path(self, project):
        """Assert from_description correctly parses DECIMAL, HASHTYPE(16 BYTE), VARCHAR, BOOLEAN."""
        results = run_dbt(["run-operation", "assert_from_description"])
        assert len(results) == 1

    @pytest.mark.parametrize(
        "macro_name,error_match",
        [
            ("bad_char_size", "could not convert"),
            ("bad_precision", "could not convert"),
            ("bad_scale", "could not convert"),
            ("bad_type_unparseable", "Could not interpret data type"),
        ],
    )
    def test_from_description_errors(self, project, macro_name, error_match):
        """Invalid type strings cause run-operation to fail with a descriptive message."""
        results = run_dbt(["run-operation", macro_name], expect_pass=False)
        assert len(results) == 1
        assert error_match in results[0].message  # type: ignore[union-attr]

    def test_string_size_on_non_string_raises(self, project):
        """Calling string_size() on a numeric column causes run-operation to fail."""
        results = run_dbt(["run-operation", "string_size_on_numeric"], expect_pass=False)
        assert len(results) == 1
        assert "non-string field" in results[0].message  # type: ignore[union-attr]
