{% materialization table, adapter='exasol', supported_languages=['sql'] %}

  {%- set existing_relation = load_cached_relation(this) -%}
  {%- set target_relation = this.incorporate(type='table') %}
  -- grab current tables grants config for comparision later on
  {% set grant_config = config.get('grants') %}


  {{ run_hooks(pre_hooks, inside_transaction=False) }}

  {{ run_hooks(pre_hooks, inside_transaction=True) }}

  {% if target_relation.type != existing_relation.type %}
    {{ drop_relation_if_exists(existing_relation) }}
  {% endif %}

  {% call statement('main') -%}
    {{ create_table_as(False, target_relation, sql) }}
  {%- endcall %}

  {{ run_hooks(post_hooks, inside_transaction=True) }}

  {% set should_revoke = should_revoke(existing_relation, full_refresh_mode=True) %}
  {% do apply_grants(target_relation, grant_config, should_revoke=should_revoke) %}

  {% do persist_docs(target_relation, model) %}

  {{ adapter.commit() }}

  {{ run_hooks(post_hooks, inside_transaction=False) }}

  {{ return({'relations': [target_relation]}) }}
{% endmaterialization %}
