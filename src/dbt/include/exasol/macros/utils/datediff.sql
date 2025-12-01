{% macro exasol__datediff(first_date, second_date, datepart) %}
    {%- set supported_dateparts = ['year', 'month', 'day', 'hour', 'minute', 'second'] %}
    {%- if datepart | lower in supported_dateparts %}
        ceil({{datepart}}s_between({{second_date}}, {{first_date}}))
    {%- else -%}
        {{ exceptions.raise_compiler_error("Unsupported `datepart`! Use one of " ~ supported_dateparts ~ "!") }}
    {%- endif -%}
{%- endmacro %}
