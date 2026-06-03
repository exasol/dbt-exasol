{% macro exasol__aggregate_function_sql(target_relation) %}
    {% do exceptions.raise_compiler_error("SQL aggregate UDFs are not supported in Exasol. Use Python with type: aggregate and language: python.") %}
{% endmacro %}

{% macro exasol__aggregate_function_python(target_relation) %}
{% do exasol__warn_unsupported_volatility() %}
{% if model.config.get('aggregate_state') is not none %}
    {% do exceptions.warn(
        "Found `aggregate_state` specified on function `" ~ model.name ~
        "`. Exasol handles distributed aggregation transparently; `aggregate_state` and `merge()` are unused."
    ) %}
{% endif %}
{% set runtime_version = model.config.get('runtime_version') %}
{% if runtime_version is not none %}
    {% set msg = "Found `runtime_version` specified on function `" ~ model.name ~ "`. Exasol uses a fixed PYTHON3 runtime, and `runtime_version` will be ignored" %}
    {% do exceptions.warn(msg) %}
{% endif %}
CREATE OR REPLACE PYTHON3 SET SCRIPT {{ target_relation.render() }} (
    {{ exasol__formatted_script_function_args_sql() }}
)
RETURNS {{ model.returns.data_type }}
AS
{{ model.compiled_code | trim }}

def run(ctx):
    agg = {{ model.config.get('entry_point') }}()
    while True:
        agg.accumulate(
            {%- for arg in model.arguments -%}
                ctx.{{ arg.name }}{{ ", " if not loop.last }}
            {%- endfor -%}
        )
        if not ctx.next():
            break
    return agg.finish()
{% endmacro %}
