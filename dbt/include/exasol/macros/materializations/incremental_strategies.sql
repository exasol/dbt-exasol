{% macro exasol__get_incremental_default_sql(arg_dict) %}

  {% if arg_dict["unique_key"] %}
    {% do return(get_incremental_delete_insert_sql(arg_dict)) %}
  {% else %}
    {% do return(get_incremental_append_sql(arg_dict)) %}
  {% endif %}

{% endmacro %}


{% macro exasol__get_incremental_microbatch_sql(arg_dict) %}
    {#-- Microbatch strategy: DELETE matching batch window + INSERT all from temp --#}
    {%- set target = arg_dict["target_relation"] -%}
    {%- set source = arg_dict["temp_relation"] -%}
    {%- set dest_columns = arg_dict["dest_columns"] -%}
    {%- set incremental_predicates = [] if arg_dict.get('incremental_predicates') is none else arg_dict.get('incremental_predicates') -%}

    {#-- Build batch time predicates for DELETE based on model.batch info --#}
    {% if model.batch is not none and model.batch.event_time_start is not none -%}
        {%- set start_ts = model.batch.event_time_start.strftime('%Y-%m-%d %H:%M:%S') -%}
        {% do incremental_predicates.append(model.config.event_time ~ " >= TIMESTAMP '" ~ start_ts ~ "'") %}
    {% endif %}
    {% if model.batch is not none and model.batch.event_time_end is not none -%}
        {%- set end_ts = model.batch.event_time_end.strftime('%Y-%m-%d %H:%M:%S') -%}
        {% do incremental_predicates.append(model.config.event_time ~ " < TIMESTAMP '" ~ end_ts ~ "'") %}
    {% endif %}

    {#-- DELETE existing data in batch window --#}
    {% if incremental_predicates %}
delete from {{ target }}
where (
    {% for predicate in incremental_predicates %}
        {%- if not loop.first %}and {% endif -%} {{ predicate }}
    {% endfor %}
)
    {% endif %}
|SEPARATEMEPLEASE|
    {#-- INSERT new data --#}
    {%- set dest_cols_csv = get_quoted_csv(dest_columns | map(attribute="name")) -%}
insert into {{ target }} ({{ dest_cols_csv }})
(
    select {{ dest_cols_csv }}
    from {{ source }}
)
{% endmacro %}
