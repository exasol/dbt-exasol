{% macro exasol__drop_view(relation) -%}
    {% call statement('drop_view') -%}
        DROP VIEW IF EXISTS {{ relation.schema }}.{{ relation.identifier }}
    {%- endcall %}
{%- endmacro %}
