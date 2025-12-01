{% macro partition_by_conf(partition_by_config) %} 
    {%- if partition_by_config is not none and partition_by_config is string -%}
        {%- set partition_by_config = [partition_by_config] -%}
    {%- endif -%}
    {%- if partition_by_config is not none -%}
        {%- set partition_by_string = 'partition by ' ~ partition_by_config|join(", ") -%}
    {% else %}
        {%- set partition_by_string = '' -%}
    {%- endif -%}
    {{return(partition_by_string)}}
{% endmacro %}

{% macro distribute_by_conf(distribute_by_config) %} 
    {%- if distribute_by_config is not none and distribute_by_config is string -%}
        {%- set distribute_by_config = [distribute_by_config] -%}
    {%- endif -%}
    {%- if distribute_by_config is not none -%}
        {%- set distribute_by_string = 'distribute by ' ~ distribute_by_config|join(", ") -%}
    {% else %}
        {%- set distribute_by_string = '' -%}
    {%- endif -%}
    {{return(distribute_by_string)}}
{% endmacro %}

{% macro primary_key_conf(primary_key_config, relation) %} 
    {%- if primary_key_config is not none and primary_key_config is string -%}
        {%- set primary_key_config = [primary_key_config] -%}
    {%- endif -%}
    {%- if primary_key_config is not none -%}
        {%- set primary_key_string = ' add constraint ' ~relation|replace('.','_')~'__pk primary key(' ~ primary_key_config|join(", ") ~ ')' -%}
    {% else %}
        {%- set primary_key_string = '' -%}
    {%- endif -%}
    {{return(primary_key_string)}}
{% endmacro %}

{% macro add_constraints(target_relation, partition_by_config, distribute_by_config, primary_key_config) %}
    {%- if partition_by_config is not none -%}
        |SEPARATEMEPLEASE|
            ALTER TABLE {{target_relation}} {{partition_by_conf(partition_by_config)}};
    {% endif %}
    
    {%- if distribute_by_config is not none -%}
        |SEPARATEMEPLEASE|
            ALTER TABLE {{target_relation}} {{distribute_by_conf(distribute_by_config)}}; 
    {% endif %}
    
    {%- if primary_key_config is not none -%}
        |SEPARATEMEPLEASE|
            ALTER TABLE {{target_relation}} {{primary_key_conf(primary_key_config, target_relation)}};
    {% endif %}  
{% endmacro %}