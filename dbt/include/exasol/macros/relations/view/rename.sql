{% macro exasol__get_rename_view_sql(relation, new_name) -%}
    RENAME VIEW {{ relation.schema }}.{{ relation.identifier }} TO {{ new_name }}
{%- endmacro %}
