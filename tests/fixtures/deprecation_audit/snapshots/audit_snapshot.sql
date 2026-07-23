{% snapshot audit_snapshot %}
{{
    config(
        target_schema=env_var('DBT_SCHEMA', 'public'),
        unique_key='id',
        strategy='check',
        check_cols=['name'],
    )
}}
select * from {{ ref('audit_model') }}
{% endsnapshot %}
