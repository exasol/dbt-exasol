{% macro exasol__get_rename_table_sql(relation, new_name) -%}
    RENAME TABLE {{ relation.schema }}.{{ relation.identifier }} TO {{ new_name }}
{%- endmacro %}
