{% macro exasol__current_timestamp() -%}
  current_timestamp()
{%- endmacro %}

{% macro exasol__snapshot_string_as_time(timestamp) -%}
  {%- set result = "to_timestamp('" ~ timestamp ~ "')" -%}
  {{ return(result) }}
{%- endmacro %}

{% macro exasol__snapshot_get_time() -%}
  to_timestamp({{ current_timestamp() }})
{%- endmacro %}

{% macro exasol__current_timestamp_backcompat() %}
  current_timestamp()
{% endmacro %}

{% macro exasol__current_timestamp_in_utc_backcompat() %}
  current_timestamp()
{% endmacro %}
