{{ config(materialized='table') }}

select
    1 as id,
    cast('exasol' as varchar(100)) as name
