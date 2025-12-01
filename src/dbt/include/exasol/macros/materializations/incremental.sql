{% materialization incremental, adapter='exasol', supported_languages=['sql'] %}

  {% set unique_key = config.get('unique_key') %}
  {%- set language = model['language'] -%}
  {% set target_relation = this.incorporate(type='table') %}
  {% set existing_relation = load_cached_relation(this) %}
  {% set tmp_relation = make_temp_relation(this) %}
  {% set on_schema_change = incremental_validate_on_schema_change(config.get('on_schema_change'), default='ignore') %}
  {% set  grant_config = config.get('grants') %}
  {%- set full_refresh_mode = (should_full_refresh()  or existing_relation.is_view) -%}

  {{ run_hooks(pre_hooks, inside_transaction=False) }}

  -- `BEGIN` happens here:
  {{ run_hooks(pre_hooks, inside_transaction=True) }}

  {% set to_drop = [] %}
  {% if existing_relation is none %}
      {% set build_sql = create_table_as(False, target_relation, sql) %}
  {% elif full_refresh_mode %}
      {#-- Checking if backup relation exists#}
      {% set backup_identifier = existing_relation.identifier ~ "__dbt_backup" %}
      {% set backup_relation = existing_relation.incorporate(path={"identifier": backup_identifier}) %}
      {% do adapter.drop_relation(backup_relation) %}
      {% if existing_relation.is_view %}
            {% do adapter.drop_relation(existing_relation) %}
      {% else %}
            {% do adapter.rename_relation(existing_relation, backup_relation) %}
      {% endif %}
      {% set build_sql = create_table_as(False, target_relation, sql) %}
      {% do to_drop.append(backup_relation) %}
  {% else %}
      {% set tmp_relation = make_temp_relation(target_relation) %}
      {% do to_drop.append(tmp_relation) %}
      {% call statement("make_tmp_relation") %}
        {{create_table_as(True, tmp_relation, sql)}}
      {% endcall %}
      {% do adapter.expand_target_column_types(
             from_relation=tmp_relation,
             to_relation=target_relation) %}
      {% set dest_columns = process_schema_changes(on_schema_change, tmp_relation, existing_relation) %}
      {% if not dest_columns %}
        {% set dest_columns = adapter.get_columns_in_relation(existing_relation) %}
      {% endif %}

      {#-- Get the incremental_strategy, the macro to use for the strategy, and build the sql --#}
      {% set incremental_strategy = config.get('incremental_strategy') or 'default' %}
      {% set incremental_predicates = config.get('predicates', none) or config.get('incremental_predicates', none) %}
      {% set strategy_sql_macro_func = adapter.get_incremental_strategy_macro(context, incremental_strategy) %}
      {% set strategy_arg_dict = ({'target_relation': target_relation, 'temp_relation': tmp_relation, 'unique_key': unique_key, 'dest_columns': dest_columns, 'incremental_predicates': incremental_predicates }) %}
      {% set build_sql = strategy_sql_macro_func(strategy_arg_dict) %}

  {% endif %}

  {% call statement("main") %}
      {{ build_sql }}
  {% endcall %}

  {% do persist_docs(target_relation, model) %}

  {{ run_hooks(post_hooks, inside_transaction=True) }}

  -- `COMMIT` happens here
  {% do adapter.commit() %}

  {% for rel in to_drop %}
      {% do adapter.drop_relation(rel) %}
  {% endfor %}

  {{ run_hooks(post_hooks, inside_transaction=False) }}

  {% set should_revoke = should_revoke(existing_relation.is_table, full_refresh_mode) %}
  {% do apply_grants(target_relation, grant_config, should_revoke=should_revoke) %}

  {{ return({'relations': [target_relation]}) }}

{%- endmaterialization %}