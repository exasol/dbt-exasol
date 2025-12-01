{% macro exasol__get_delete_insert_merge_sql(target, source, unique_key, dest_columns,incremental_predicates) -%}

    {%- set dest_cols_csv = get_quoted_csv(dest_columns | map(attribute="name")) -%}

    {% if unique_key %}
        {% if unique_key is sequence and unique_key is not string %}
            delete from {{target }}
            where exists ( select 1 from {{ source }}
            where 
                {% for key in unique_key %}
                    {{ source }}.{{ key }} = {{ target }}.{{ key }}
                    {{ "and " if not loop.last}}
                {% endfor %}
                {% if incremental_predicates %}
                    {% for predicate in incremental_predicates %}
                        and {{ predicate }}
                    {% endfor %}
                {% endif %}
            );
        {% else %}
            delete from {{ target }}
            where (
                {{ unique_key }}) in (
                select ({{ unique_key }})
                from {{ source }}
            )
            {%- if incremental_predicates %}
                {% for predicate in incremental_predicates %}
                    and {{ predicate }}
                {% endfor %}
            {%- endif -%};

        {% endif %}
    {% endif %}

    |SEPARATEMEPLEASE|

    insert into {{ target }} ({{ dest_cols_csv }})
    (
        select {{ dest_cols_csv }}
        from {{ source }}
    )

{%- endmacro %}


{% macro exasol_check_and_quote_unique_key_for_incremental_merge(unique_key, incremental_predicates=none) %}
    {%- set unique_key_list = [] -%}
    {%- set unique_key_merge_predicates = [] if incremental_predicates is none else [] + incremental_predicates -%}
    {% if unique_key is sequence and unique_key is not mapping and unique_key is not string %}
          {% for key in unique_key | unique %}
                {% if adapter.should_identifier_be_quoted(key, model.columns) == true %}
                    {% do unique_key_list.append('"' ~ key ~ '"') %}
                {% else %}
                    {% do unique_key_list.append(key.upper()) %}
                {% endif %}
          {% endfor %}
    {% else %}
        {% if adapter.should_identifier_be_quoted(unique_key, model.columns) == true %}
            {% do unique_key_list.append('"' ~ unique_key ~ '"') %}
        {% else %}
            {% do unique_key_list.append(unique_key.upper()) %}
        {% endif %}
    {% endif %}
    {% for key in unique_key_list %}
        {% set this_key_match %}
            DBT_INTERNAL_SOURCE.{{ key }} = DBT_INTERNAL_DEST.{{ key }}
        {% endset %}
        {% do unique_key_merge_predicates.append(this_key_match) %}
    {% endfor %}
    {%- set unique_key_result = {'unique_key_list': unique_key_list, 
                                'unique_key_merge_predicates': unique_key_merge_predicates} -%}
    {{ return(unique_key_result)}}
{% endmacro %}


{% macro exasol__get_merge_update_columns(merge_update_columns, merge_exclude_columns, dest_columns) %}
  {%- set default_cols = dest_columns | map(attribute='name') | list -%}

  {%- if merge_update_columns and merge_exclude_columns -%}
    {{ exceptions.raise_compiler_error(
        'Model cannot specify merge_update_columns and merge_exclude_columns. Please update model to use only one config'
    )}}
  {%- elif merge_update_columns -%}
    {%- set update_columns = merge_update_columns -%}
  {%- elif merge_exclude_columns -%}
    {%- set update_columns = [] -%}
    {%- for column in dest_columns -%}
      {% if column.column | lower not in merge_exclude_columns | map("lower") | list %}
        {%- do update_columns.append(column.name) -%}
      {% endif %}
    {%- endfor -%}
  {%- else -%}
    {%- set update_columns = default_cols -%}
  {%- endif -%}

   {%- set quoted_update_columns = [] -%}
   {% for col in update_columns %}
        {% do quoted_update_columns.append(adapter.check_and_quote_identifier(col, model.columns)) %}
   {% endfor %}
   {{ return(quoted_update_columns)}}
{% endmacro %}


{% macro exasol__get_incremental_merge_sql(args_dict) %}
    {%- set dest_columns = args_dict["dest_columns"] -%}
    {%- set temp_relation = args_dict["temp_relation"] -%}
    {%- set target_relation = args_dict["target_relation"] -%}
    {%- set unique_key = args_dict["unique_key"] -%}
    {%- set dest_column_names = dest_columns | map(attribute='name') | list -%}
    {%- set dest_cols_csv = get_quoted_csv(dest_columns | map(attribute="name"))  -%}
    {%- set merge_update_columns = config.get('merge_update_columns') -%}
    {%- set merge_exclude_columns = config.get('merge_exclude_columns') -%}
    {%- set incremental_predicates = args_dict["incremental_predicates"] -%}
    {%- set update_columns = get_merge_update_columns(merge_update_columns, merge_exclude_columns, dest_columns) -%}
    {%- if unique_key -%}
        {%- set unique_key_result = exasol_check_and_quote_unique_key_for_incremental_merge(unique_key, incremental_predicates) -%}
        {%- set unique_key_list = unique_key_result['unique_key_list'] -%}
        {%- set unique_key_merge_predicates = unique_key_result['unique_key_merge_predicates'] -%}
        merge into {{ target_relation }} DBT_INTERNAL_DEST
          using {{ temp_relation }} DBT_INTERNAL_SOURCE
          on ({{ unique_key_merge_predicates | join(' AND ') }})
        when matched then
          update set
          {% for col in update_columns if (col.upper() not in unique_key_list and col not in unique_key_list) -%}
            DBT_INTERNAL_DEST.{{ col }} = DBT_INTERNAL_SOURCE.{{ col }}{% if not loop.last %}, {% endif %}
          {% endfor -%}
        when not matched then
          insert({{ dest_cols_csv }})
          values(
            {% for col in dest_columns -%}
              DBT_INTERNAL_SOURCE.{{ adapter.check_and_quote_identifier(col.name, model.columns) }}{% if not loop.last %}, {% endif %}
            {% endfor -%}
          )
    {%- else -%}
    insert into  {{ target_relation }} ({{ dest_cols_csv }})
    (
       select {{ dest_cols_csv }}
       from {{ temp_relation }}
    )
    {%- endif -%}
{% endmacro %}

