{% macro exasol__get_rename_table_sql(relation, new_name) -%}
    RENAME TABLE {{ relation }} TO {{ new_name }}
{%- endmacro %}
