{% macro exasol__snapshot_merge_sql(target, source, insert_cols) -%}
    {%- set insert_cols_csv = insert_cols | join(', ') -%}
    {%- set dbt_valid_to_current = config.get('dbt_valid_to_current') -%}

    merge into {{ target | upper }} as DBT_INTERNAL_DEST
    using {{ source |upper }} as DBT_INTERNAL_SOURCE
    on DBT_INTERNAL_SOURCE.dbt_scd_id = DBT_INTERNAL_DEST.dbt_scd_id

    when matched
        then update
        set dbt_valid_to = DBT_INTERNAL_SOURCE.dbt_valid_to
        where
            (
            {%- if dbt_valid_to_current %}
                DBT_INTERNAL_DEST.dbt_valid_to = {{ snapshot_string_as_time(dbt_valid_to_current) }}
                or DBT_INTERNAL_DEST.dbt_valid_to is null
            {%- else %}
                DBT_INTERNAL_DEST.dbt_valid_to is null
            {%- endif %}
            )
            and DBT_INTERNAL_SOURCE.dbt_change_type in ('update', 'delete')

    when not matched
        then insert ({{ insert_cols_csv }})
        values ({{ insert_cols_csv }})
        where DBT_INTERNAL_SOURCE.dbt_change_type = 'insert'
    ;
{% endmacro %}
