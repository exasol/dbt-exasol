{% macro exasol__warn_unsupported_volatility() %}
    {% set volatility = model.config.get('volatility') %}
    {% if volatility is not none %}
        {% do unsupported_volatility_warning(volatility) %}
    {% endif %}
{% endmacro %}

{% macro exasol__scalar_function_sql(target_relation) %}
    {% set code = model.compiled_code | trim %}
    {# Strip leading SELECT (dbt convention). Word-boundary match avoids
       mangling bodies that begin with a SELECT-prefixed identifier such as
       `SELECTED_FLAG * 2`. #}
    {% if modules.re.match('select\\s', code, modules.re.IGNORECASE) is not none %}
        {% set code = code[6:] | trim %}
    {% endif %}

    {# Emit volatility warning if configured (shared across UDF types) #}
    {% do exasol__warn_unsupported_volatility() %}

    {# Word-boundary check: avoid false positives like BEGIN_DATE, beginning, etc. #}
    {% set is_procedural = modules.re.search('\\bBEGIN\\b', code, modules.re.IGNORECASE) is not none %}

    CREATE OR REPLACE FUNCTION {{ target_relation.render() }} (
        {{ formatted_scalar_function_args_sql() }}
    )
    RETURN {{ model.returns.data_type }} IS
    {% if is_procedural %}
        {{ code }}
    {% else %}
        BEGIN
            RETURN {{ code }};
        END {{ model.name }};
    {% endif %}
{% endmacro %}

{% macro exasol__scalar_function_python(target_relation) %}
{# Exasol uses PYTHON3 keyword; runtime_version is not selectable #}
{% do exasol__warn_unsupported_volatility() %}
{% set runtime_version = model.config.get('runtime_version') %}
{% if runtime_version is not none %}
    {% set msg = "Found `runtime_version` specified on function `" ~ model.name ~ "`. Exasol uses a fixed PYTHON3 runtime, and `runtime_version` will be ignored" %}
    {% do exceptions.warn(msg) %}
{% endif %}
CREATE OR REPLACE PYTHON3 SCALAR SCRIPT {{ target_relation.render() }} (
    {{ exasol__formatted_script_function_args_sql() }}
)
RETURNS {{ model.returns.data_type }}
AS
{{ model.compiled_code | trim }}

def run(ctx):
    return {{ model.config.get('entry_point') }}(
        {%- for arg in model.arguments -%}
            ctx.{{ arg.name }}{{ ", " if not loop.last }}
        {%- endfor -%}
    )
{% endmacro %}
