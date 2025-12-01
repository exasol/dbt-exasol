{% macro exasol__safe_cast(field, type) %}
    {%- if type | lower == "boolean" -%}
    CASE WHEN is_boolean({{ field }}) THEN cast({{ field }} as {{ type }}) ELSE null END
    {%- elif type | lower == "timestamp" -%}
    CASE WHEN is_timestamp({{ field }}) THEN cast({{ field }} as {{ type }}) ELSE null END
    {%- elif type | lower == "date" -%}
    CASE WHEN is_date({{ field }}) THEN cast({{ field }} as {{ type }}) ELSE null END
    {%- elif type.lower().startswith("decimal") or type.lower().startswith("double") or type in ["int", "float"] -%}
    CASE WHEN is_number({{ field }}) THEN cast({{ field }} as {{ type }}) ELSE null END
    {%- else -%}
    {#- try to cast it anyway...e.g. strings -#}
    cast({{ field }} as {{ type }})
    {%- endif -%}
{% endmacro %}
