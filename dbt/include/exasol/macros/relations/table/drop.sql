{% macro exasol__drop_table(relation) -%}
    {% call statement('drop_table') -%}
        DROP TABLE IF EXISTS {{ relation.schema }}.{{ relation.identifier }}
    {%- endcall %}
{%- endmacro %}
