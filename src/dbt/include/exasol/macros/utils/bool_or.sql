{% macro exasol__bool_or(expression) -%}

    any({{ expression }})

{%- endmacro %}
