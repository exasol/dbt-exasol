{% macro exasol__validate_sql(sql) -%}
  {% call statement('validate_sql') -%}
    {{ sql }} limit 0 
  {% endcall %}
  {{ return(load_result('validate_sql')) }}
{% endmacro %}
