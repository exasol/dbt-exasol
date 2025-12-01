{%- macro exasol__last_day(date, datepart) -%}
    {%- if datepart | lower != 'quarter' %}
        cast(
            add_days(add_{{datepart | lower}}s(date_trunc('{{datepart}}',{{date}}), 1), -1)
            as date)
    {%- else -%}
        cast(
            add_days(add_months(date_trunc('{{datepart}}',{{date}}), 3), -1)
            as date)
    {%- endif -%}
{%- endmacro -%}