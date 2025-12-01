{% macro exasol__dateadd(datepart, interval, from_date_or_timestamp) %}
    {%- set supported_dateparts = ["year", "month", "week", "day", "hour", "minute", "second"] %}
    {%- if datepart | lower not in supported_dateparts %}
        {{ exceptions.raise_compiler_error("Unsupported `datepart`! Use one of " ~ ','.join(supported_dateparts) ~ "!") }}
    {%- endif -%}
    
    add_{{ datepart | lower }}s({{ from_date_or_timestamp }}, {{ interval }})

{%- endmacro %}
