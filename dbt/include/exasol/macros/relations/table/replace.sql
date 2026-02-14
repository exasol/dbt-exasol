{% macro exasol__get_replace_table_sql(relation, sql) -%}
    {{ exasol__create_table_as(False, relation, sql) }}
{%- endmacro %}
