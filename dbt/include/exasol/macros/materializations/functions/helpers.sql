{% macro exasol__formatted_script_function_args_sql() %}
    {#
        Quote argument identifiers for PYTHON3 SCALAR/SET SCRIPT signatures so
        that Exasol reserved words (e.g. `value`) are legal. Safe for SCRIPT
        paths because the generated `def run(ctx)` bridge accesses arguments via
        `ctx.<name>`, which resolves the quoted (case-preserved) identifier.
        NOT used for SQL FUNCTION DDL, where user-written bodies reference
        unquoted identifiers and quoting would break name resolution.
    #}
    {% set args = [] %}
    {% for arg in model.arguments -%}
        {%- do args.append('"' ~ arg.name ~ '" ' ~ arg.data_type) -%}
    {%- endfor %}
    {{ args | join(', ') }}
{% endmacro %}

{% macro exasol__function_execute_build_sql(build_sql, existing_relation, target_relation) %}
    {% set language = model.get('language', 'sql') %}
    {% if language == 'sql' %}
        {# Creating FUNCTION -- drop any stale SCRIPT with same name #}
        {% call statement('drop_stale_script', auto_begin=False) %}
            DROP SCRIPT IF EXISTS {{ target_relation.render() }}
        {% endcall %}
    {% else %}
        {# Creating SCRIPT -- drop any stale FUNCTION with same name #}
        {% call statement('drop_stale_function', auto_begin=False) %}
            DROP FUNCTION IF EXISTS {{ target_relation.render() }}
        {% endcall %}
    {% endif %}

    {{ default__function_execute_build_sql(build_sql, existing_relation, target_relation) }}
{% endmacro %}
