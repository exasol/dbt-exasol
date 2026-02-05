{% materialization table, adapter='exasol' %}
  {#
    Exasol table materialization using CREATE OR REPLACE TABLE directly.

    Exasol supports atomic CREATE OR REPLACE TABLE, so we skip the
    intermediate/backup/rename pattern used by dbt-core default.
    This avoids cache inconsistency errors with parallel model builds.
  #}

  {%- set identifier = model['alias'] -%}
  {%- set old_relation = adapter.get_relation(database=database, schema=schema, identifier=identifier) -%}
  {%- set exists_as_target_type = (old_relation is not none and old_relation.is_table) -%}
  {%- set target_relation = api.Relation.create(
      identifier=identifier,
      schema=schema,
      database=database,
      type='table'
  ) -%}
  {% set grant_config = config.get('grants') %}

  {{ run_hooks(pre_hooks) }}

  {#
      We only need to drop this thing if it is not a table.
      If it _is_ already a table, then we can overwrite it without downtime.
  #}
  {%- if old_relation is not none and not old_relation.is_table -%}
    {{ adapter.drop_relation(old_relation) }}
  {%- endif -%}

  {% call statement('main') -%}
    {{ create_table_as(False, target_relation, sql) }}
  {%- endcall %}

  {% set should_revoke = should_revoke(exists_as_target_type, full_refresh_mode=True) %}
  {% do apply_grants(target_relation, grant_config, should_revoke=should_revoke) %}

  {% do persist_docs(target_relation, model) %}

  {{ run_hooks(post_hooks) }}

  {{ return({'relations': [target_relation]}) }}

{% endmaterialization %}
