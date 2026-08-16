# pylint: disable=duplicate-code
"""Exasol column type validation via dbt's ``is_type`` test + type predicates.

Subclasses upstream ``BaseColumnTypes`` (parity marker) and extends the macro
to cover Exasol-specific type predicates: ``is_boolean``, ``is_date``,
``is_timestamp``, and ``is_hashtype`` -- all of which are exercised through the
real ``get_columns_in_relation`` → ``api.Column(*row)`` path.

Coverage target (column.py):
  33  (is_integer scale=0)
  36  (is_float)
  42  (is_hashtype)
  45  (is_boolean)
  49  (is_timestamp incl. TIMESTAMP WITH LOCAL TIME ZONE)
  52  (is_date)
"""

import os

import pytest
from dbt.tests.adapter.column_types.test_column_types import BaseColumnTypes
from dbt.tests.util import run_dbt

_exasol_type_check_macro = """
{% macro simple_type_check_column(column, check) %}
    {% if check == 'string' %}
        {{ return(column.is_string()) }}
    {% elif check == 'float' %}
        {{ return(column.is_float()) }}
    {% elif check == 'number' %}
        {{ return(column.is_number()) }}
    {% elif check == 'numeric' %}
        {{ return(column.is_numeric()) }}
    {% elif check == 'integer' %}
        {{ return(column.is_integer()) }}
    {% elif check == 'boolean' %}
        {{ return(column.is_boolean()) }}
    {% elif check == 'date' %}
        {{ return(column.is_date()) }}
    {% elif check == 'timestamp' %}
        {{ return(column.is_timestamp()) }}
    {% elif check == 'hashtype' %}
        {{ return(column.is_hashtype()) }}
    {% else %}
        {% do exceptions.raise_compiler_error('invalid type check value: ' ~ check) %}
    {% endif %}
{% endmacro %}

{% macro type_check_column(column, type_checks) %}
    {% set failures = [] %}
    {% for type_check in type_checks %}
        {% if type_check.startswith('not ') %}
            {% if simple_type_check_column(column, type_check[4:]) %}
                {% do log('simple_type_check_column got ', True) %}
                {% do failures.append(type_check) %}
            {% endif %}
        {% else %}
            {% if not simple_type_check_column(column, type_check) %}
                {% do failures.append(type_check) %}
            {% endif %}
        {% endif %}
    {% endfor %}
    {% if (failures | length) > 0 %}
        {% do log('column ' ~ column.name ~ ' had failures: ' ~ failures, info=True) %}
    {% endif %}
    {% do return((failures | length) == 0) %}
{% endmacro %}

{% test is_type(model, column_map) %}
    {% if not execute %}
        {{ return(None) }}
    {% endif %}
    {% if not column_map %}
        {% do exceptions.raise_compiler_error('test_is_type must have a column name') %}
    {% endif %}
    {% set columns = adapter.get_columns_in_relation(model) %}
    {% if (column_map | length) != (columns | length) %}
        {% set column_map_keys = (column_map | list | string) %}
        {% set column_names = (columns | map(attribute='name') | list | string) %}
        {% do exceptions.raise_compiler_error('did not get all the columns/all columns not specified:\\n' ~ column_map_keys ~ '\\nvs\\n' ~ column_names) %}
    {% endif %}
    {% set bad_columns = [] %}
    {% for column in columns %}
        {% set column_key = (column.name | lower) %}
        {% if column_key in column_map %}
            {% set type_checks = column_map[column_key] %}
            {% if not type_checks %}
                {% do exceptions.raise_compiler_error('no type checks?') %}
            {% endif %}
            {% if not type_check_column(column, type_checks) %}
                {% do bad_columns.append(column.name) %}
            {% endif %}
        {% else %}
            {% do exceptions.raise_compiler_error('column key ' ~ column_key ~ ' not found in ' ~ (column_map | list | string)) %}
        {% endif %}
    {% endfor %}
    {% do log('bad columns: ' ~ bad_columns, info=True) %}
    {% for bad_column in bad_columns %}
      select '{{ bad_column }}' as bad_column
      {{ 'union all' if not loop.last }}
    {% endfor %}
      select * from (select 1 limit 0) as nothing
{% endtest %}
"""

# Exasol-specific model using native Exasol types.
# CASTs ensure the types survive through the Exasol query engine.
_model_sql = """
select
    cast(1 as decimal(18,0))             as int_col,
    cast(2.5 as double)                  as double_col,
    cast(3.5 as decimal(18,9))           as numeric_col,
    cast('hello' as varchar(20))         as varchar_col,
    cast('x' as char(5))                 as char_col,
    true                                 as bool_col,
    date '2025-01-01'                    as date_col,
    timestamp '2025-01-01 00:00:00'      as ts_col,
    cast(timestamp '2025-01-01 00:00:00'
         as timestamp with local time zone) as tsltz_col,
    hashtype_md5('a')                    as hash_col
"""

_schema_yml = """
version: 2
models:
  - name: model
    data_tests:
      - is_type:
          column_map:
            int_col:     ['integer', 'numeric', 'number']
            double_col:  ['float', 'number', 'not integer']
            numeric_col: ['numeric', 'number', 'not integer']
            varchar_col: ['string', 'not number']
            char_col:    ['string', 'not number']
            bool_col:    ['boolean', 'not number']
            date_col:    ['date', 'not number']
            ts_col:      ['timestamp', 'not number']
            tsltz_col:   ['timestamp', 'not number']
            hash_col:    ['hashtype', 'not string', 'not number']
"""


class TestExasolColumnTypes(BaseColumnTypes):
    """Cover ``is_boolean``, ``is_date``, ``is_timestamp``, and ``is_hashtype``
    predicates through a real ``get_columns_in_relation`` → ``api.Column`` round-trip.

    The ``tsltz_col`` exercises ``is_timestamp()`` for ``TIMESTAMP WITH LOCAL
    TIME ZONE``, which Exasol's ``get_columns_in_relation`` reduces to the
    base type prefix ``TIMESTAMP``.
    """

    @pytest.fixture(scope="class")
    def dbt_profile_target(self):
        return {
            "type": "exasol",
            "threads": 8,
            "dsn": os.getenv("DBT_DSN", "localhost:8563"),
            "user": os.getenv("DBT_USER", "sys"),
            "pass": os.getenv("DBT_PASS", "exasol"),
            "dbname": "DB",
            "timestamp_format": "YYYY-MM-DD HH:MI:SS.FF6",
            "validate_server_certificate": False,
        }

    @pytest.fixture(scope="class")
    def macros(self):
        return {"test_is_type.sql": _exasol_type_check_macro}

    @pytest.fixture(scope="class")
    def models(self):
        return {"model.sql": _model_sql, "schema.yml": _schema_yml}

    def test_run_and_test(self, project):
        """Run the model and validate column types against Exasol predicates."""
        results = run_dbt(["run"])
        assert len(results) == 1
        results = run_dbt(["test"])
        assert len(results) == 1
