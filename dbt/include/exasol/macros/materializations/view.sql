{% materialization view, adapter='exasol' %}
  {#
    Exasol view materialization using CREATE OR REPLACE VIEW directly.

    Exasol supports atomic CREATE OR REPLACE VIEW, so we skip the
    intermediate/backup/rename pattern used by dbt-core default.
    This avoids cache inconsistency errors with parallel model builds.
  #}

  {%- set identifier = model['alias'] -%}
  {%- set old_relation = adapter.get_relation(database=database, schema=schema, identifier=identifier) -%}
  {%- set exists_as_target_type = (old_relation is not none and old_relation.is_view) -%}
  {%- set target_relation = api.Relation.create(
      identifier=identifier,
      schema=schema,
      database=database,
      type='view'
  ) -%}
  {% set grant_config = config.get('grants') %}

  {{ run_hooks(pre_hooks) }}

  {#
      We only need to drop this thing if it is not a view.
      If it _is_ already a view, then we can overwrite it without downtime.
  #}
  {%- if old_relation is not none and not old_relation.is_view -%}
    {{ adapter.drop_relation(old_relation) }}
  {%- endif -%}

  {% call statement('main') -%}
    {{ get_create_view_as_sql(target_relation, sql) }}
  {%- endcall %}

  {% set should_revoke = should_revoke(exists_as_target_type, full_refresh_mode=True) %}
  {% do apply_grants(target_relation, grant_config, should_revoke=should_revoke) %}

  {% do persist_docs(target_relation, model) %}

  {{ run_hooks(post_hooks) }}

  {{ return({'relations': [target_relation]}) }}

{% endmaterialization %}
