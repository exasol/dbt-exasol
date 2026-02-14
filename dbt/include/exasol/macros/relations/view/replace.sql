{% macro exasol__get_replace_view_sql(relation, sql) -%}
    {{ exasol__create_view_as(relation, sql) }}
{%- endmacro %}
