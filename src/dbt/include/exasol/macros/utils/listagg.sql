{% macro exasol__listagg(measure, delimiter_text, order_by_clause, limit_num) -%}
    {% if limit_num -%}
        {{ exceptions.raise_compiler_error("`limit_num` parameter is not supported on Exasol!") }}
    {% endif -%}

    listagg(
        {{ measure }},
        {{ delimiter_text }}
        )
        {% if order_by_clause -%}
        within group ({{ order_by_clause }})
        {%- endif %}

{%- endmacro %}
