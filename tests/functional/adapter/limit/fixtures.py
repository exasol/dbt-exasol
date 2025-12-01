exasol__sql_header = """
{% call set_sql_header(config) %}
with variables as (
    select 1 as my_variable
)
{%- endcall %}
select my_variable from variables
"""
