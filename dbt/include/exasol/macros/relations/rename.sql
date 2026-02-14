{% macro exasol__rename_relation(from_relation, to_relation) -%}
    {% set target_name = adapter.quote_as_configured(to_relation.identifier, 'identifier') %}
    {% call statement('rename_relation') -%}
        {%- if from_relation.is_view -%}
            {{ get_rename_view_sql(from_relation, target_name) }}
        {%- elif from_relation.is_table -%}
            {{ get_rename_table_sql(from_relation, target_name) }}
        {%- else -%}
            {{ exceptions.raise_compiler_error("`rename_relation` has not been implemented for: " ~ from_relation.type) }}
        {%- endif -%}
    {%- endcall %}
{% endmacro %}
