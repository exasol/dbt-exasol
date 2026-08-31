/*
LIST_RELATIONS_MACRO_NAME = 'list_relations_without_caching'
GET_COLUMNS_IN_RELATION_MACRO_NAME = 'get_columns_in_relation'
LIST_SCHEMAS_MACRO_NAME = 'list_schemas'
CHECK_SCHEMA_EXISTS_MACRO_NAME = 'check_schema_exists'
CREATE_SCHEMA_MACRO_NAME = 'create_schema'
DROP_SCHEMA_MACRO_NAME = 'drop_schema'
TRUNCATE_RELATION_MACRO_NAME = 'truncate_relation'
DROP_RELATION_MACRO_NAME = 'drop_relation'
ALTER_COLUMN_TYPE_MACRO_NAME = 'alter_column_type'
 */


{% macro exasol__list_relations_without_caching(schema) %}
    {% call statement('list_relations_without_caching', fetch_result=True) -%}
    select
      'db' as [database],
      table_name as [name],
      table_schema as [schema],
  	  lower(table_type) as table_type
    from (
		select table_name,table_schema,'table' as table_type from sys.exa_all_tables
		union
		select view_name, view_schema,'view' from sys.exa_all_views
	  )
    where upper(table_schema) = '{{ schema.schema |upper }}'
{% endcall %}  
    {{ return(load_result('list_relations_without_caching').table) }}
{% endmacro %}

{% macro exasol__list_schemas(database) %}
    {% call statement('list_schemas', fetch_result=True, auto_begin=False) -%}
    select schema_name as [schema] from exa_schemas
  {% endcall %}
    {{ return(load_result('list_schemas').table) }}
{% endmacro %}

{# exasol__create_schema intentionally not overridden: identical to dbt-core's
   default__create_schema (create schema if not exists {{ relation.without_identifier() }}).
   Dispatch falls through to the shared macro. #}

{% macro exasol__drop_schema(relation) -%}
    {% call statement('drop_schema') -%}
    drop schema if exists {{ relation }} cascade
  {% endcall %}
{% endmacro %}

{% macro exasol__drop_relation(relation) -%}
    {% call statement('drop_relation', fetch_result=True) -%}
        drop {{ relation.type }} if exists {{ relation }}
    {%- endcall %}
{% endmacro %}

{% macro exasol__check_schema_exists(database, schema) -%}
    {% call statement('check_schema_exists', fetch_result=True, auto_begin=False) -%}
    select count(*) as schema_exist from (
		select schema_name as [schema] from exa_schemas
    ) WHERE upper([schema]) = '{{ schema | upper }}'
    {%- endcall %}
    {{ return(load_result('check_schema_exists').table) }}
{% endmacro %}

{% macro exasol__assert_no_catalog_integration() -%}
    {#- Exasol has no catalog integration (Iceberg / external table formats). A
        catalogs.yml may exist in this project, but a model that actively sets
        config(catalog=...) must fail with a clear, Exasol-specific error rather
        than silently ignoring the request. -#}
    {%- if config.get('catalog') or config.get('catalog_name') -%}
        {%- do exceptions.raise_compiler_error(
            'Exasol does not support catalog integrations (e.g. Iceberg / external '
            ~ 'table formats). Remove the `catalog` config from this model to run it '
            ~ 'on Exasol.'
        ) -%}
    {%- endif -%}
{%- endmacro %}

{% macro exasol__create_view_as(relation, sql) -%}
    {{ exasol__assert_no_catalog_integration() }}
    {%- set contract_config = config.get('contract') -%}
    {%- if contract_config.enforced -%}
        {{ get_assert_columns_equivalent(sql) }}
    {%- endif %}
CREATE OR REPLACE VIEW {{ relation }} 
    {{- persist_view_column_docs(relation, sql) }}
AS 
(
    {{ sql | indent(4) }}
)
{{ persist_view_relation_docs() }}
{% endmacro %}


{% macro exasol__get_select_subquery(sql) %}
    {%- set user_provided_columns = model['columns'] -%}
    {%- set column_exprs = [] -%}
    {%- for col_name in user_provided_columns -%}
        {%- set col = user_provided_columns[col_name] -%}
        {%- set col_identifier = adapter.quote(col['name']) if col.get('quote') else col['name'] -%}
        {%- set column_exprs = column_exprs.append('CAST(' ~ col_identifier ~ ' AS ' ~ col['data_type'] ~ ') AS ' ~ col_identifier) -%}
    {%- endfor -%}
    select {{ column_exprs | join(', ') }}
    from (
        {{ sql }}
    ) as model_subq
{% endmacro %}

{% macro exasol__create_table_as(temporary, relation, sql) -%}
    {{ exasol__assert_no_catalog_integration() }}
    {%- set contract_config = config.get('contract') -%}

    {%- set partition_by_config = config.get('partition_by_config') -%}
    {%- set distribute_by_config = config.get('distribute_by_config') -%}
    {%- set primary_key_config = config.get('primary_key_config') -%}

    {%- if contract_config.enforced -%}
        {{- get_assert_columns_equivalent(sql) }}
        CREATE OR REPLACE TABLE {{ relation }} AS
            {{ get_select_subquery(sql) }}
        {% for col_name in model['columns'] %}
            {%- set col = model['columns'][col_name] -%}
            {%- if col.get('constraints') -%}
                {%- for constraint in col['constraints'] -%}
                    {%- if constraint.type == 'not_null' -%}|SEPARATEMEPLEASE|
    ALTER TABLE {{ relation }} MODIFY COLUMN {{ adapter.quote(col['name']) if col.get('quote') else col['name'] }} NOT NULL;{% endif %}{% endfor %}
            {%- endif %}
        {% endfor %}
        {% if model.get('constraints') -%}
                {%- for constraint in model['constraints'] -%}
                    {%- if constraint.type == 'primary_key' -%}|SEPARATEMEPLEASE|
    ALTER TABLE {{ relation }} ADD CONSTRAINT {{ exasol__constraint_name_prefix(relation) }}__pk PRIMARY KEY({{ constraint.columns|join(', ') }});{% endif %}{% endfor %}
        {%- endif -%}
    {%- else -%}
        CREATE OR REPLACE TABLE {{ relation }} AS
            {{ sql }}
    {%- endif -%}
    {{ add_constraints(relation, partition_by_config, distribute_by_config, primary_key_config) }}
{% endmacro %}

{% macro exasol__truncate_relation(relation) -%}
    {% call statement('truncate_relation') -%}
        truncate table {{ relation }}
    {%- endcall %}
{% endmacro %}

{% macro exasol__get_columns_in_relation(relation) -%}
    {% call statement('get_columns_in_relation', fetch_result=True) %}
      select
          column_name,
          regexp_substr(column_type, '[A-Za-z]+', 1) as column_type,
          column_maxsize,
          column_num_prec,
          column_num_scale
      from exa_all_columns
      where upper(column_table) = '{{ relation.identifier|upper }}'
        and upper(column_schema) = '{{ relation.schema|upper }}'
      order by column_ordinal_position

  {% endcall %}
    {% set table = load_result('get_columns_in_relation').table %}
    {{ return(sql_convert_columns_in_relation(table)) }}
{% endmacro %}

{% macro exasol__get_columns_in_query(select_sql) %}
    {% call statement('get_columns_in_query', fetch_result=True, auto_begin=False) -%}
        select * from (
            {{ select_sql }}
        ) as dbt_sbq
        where false
        limit 0
    {% endcall %}

    {{ return(load_result('get_columns_in_query').table.columns | map(attribute='name') | list) }}
{% endmacro %}

{% macro exasol__alter_relation_comment(relation, relation_comment) -%}
    {# Comments on views are not supported outside DDL, see https://docs.exasol.com/db/latest/sql/comment.htm#UsageNotes #}
    {%- if not relation.is_view %}
        {%- set comment = relation_comment | replace("'", "''") %}
    COMMENT ON {{ relation.type }} {{ relation }} IS '{{ comment }}';
    {%- endif %}
{% endmacro %}

{% macro get_column_comment_sql(column_name, column_dict, apply_comment=false) -%}
    {% if (column_name|upper in column_dict) -%}
    {% set matched_column = column_name|upper -%}
  {% elif (column_name|lower in column_dict) -%}
    {% set matched_column = column_name|lower -%}
  {% elif (column_name in column_dict) -%}
    {% set matched_column = column_name -%}
  {% else -%}
        {% set matched_column = None -%}
    {% endif -%}
    {% if matched_column -%}
    {% set comment = column_dict[matched_column]['description'] | replace("'", "''") -%}
  {% else -%}
        {% set comment = "" -%}
    {% endif -%}
    {{ adapter.quote(column_name) }} {{ "COMMENT" if apply_comment }} IS '{{ comment }}'
{%- endmacro %}

{% macro exasol__alter_column_comment(relation, column_dict) -%}
    {# Comments on views are not supported outside DDL, see https://docs.exasol.com/db/latest/sql/comment.htm#UsageNotes #}
    {%- if not relation.is_view %}
        {# For seeds and existing tables, get columns from the relation itself #}
        {# For models with SQL, get columns from the query #}
        {% if sql is defined and sql %}
      {% set relation_columns = get_columns_in_query(sql) %}
    {% else %}
            {% set relation_columns = adapter.get_columns_in_relation(relation) | map(attribute='name') | list %}
        {% endif %}
    COMMENT ON {{ relation.type }} {{ relation }} (
    {% for column_name in relation_columns %}
            {{ get_column_comment_sql(column_name, column_dict) }} {{- ',' if not loop.last }}
        {% endfor %}
    );
    {%- endif %}
{% endmacro %}

{# exasol__persist_docs intentionally not overridden: dbt-core 1.12's
   default__persist_docs already calls validate_doc_columns, matching what this
   adapter used to add itself. Dispatch falls through to the shared macro. #}

{% macro persist_view_column_docs(relation, sql) %}
    {%- if config.persist_column_docs() %}
        
(
  {% set query_columns = get_columns_in_query(sql) %}
        {%- for column_name in query_columns %}
            {{ get_column_comment_sql(column_name, model.columns, true) -}}{{ ',' if not loop.last -}}
        {%- endfor %}
)
    {%- endif %}
{%- endmacro %}

{% macro persist_view_relation_docs() %}
    {%- if config.persist_relation_docs() -%}
    COMMENT IS '{{ model.description | replace("'", "''") }}'
    {%- endif -%}
{% endmacro %}

{% macro exasol__alter_column_type(relation, column_name, new_column_type) -%}
    {% call statement('alter_column_type') %}
    alter table {{ relation }} modify column {{ adapter.quote(column_name) }} {{ new_column_type }};
  {% endcall %}
{% endmacro %}

{% macro exasol__get_empty_subquery_sql(select_sql, select_sql_header=None) %}
    {#- Same contract as dbt-core's default__get_empty_subquery_sql (optional
       header + zero-row guarantee via `where false` / `limit 0`), with two
       Exasol-specific deviations:

       1. The subquery alias is `dbt_sbq_tmp` instead of `__dbt_sbq`: Exasol
          rejects unquoted identifiers starting with `_` (see
          ExasolRelation._render_subquery_alias).
       2. A statement-style `sql_header` is emitted as its OWN statement.
          Exasol accepts exactly one statement per request, so concatenating
          `alter session set ...;` with the following `select` raises
          `syntax error, unexpected SELECT_, expecting END_OF_INPUT_`.
          `|SEPARATEMEPLEASE|` makes ExasolCursor.execute submit the header and
          the select separately on the same connection, so session settings
          still apply to the select.

       Headers that are a syntactic prefix of the query rather than a standalone
       statement (e.g. a leading `with ... as (...)` CTE) must stay inline. They
       are told apart by the trailing semicolon of a complete statement.

       This macro backs dbt's unit-test materialization
       (`get_empty_subquery_sql(sql)` in the `unit` materialization) and model
       contract enforcement (`assert_columns_equivalent`), which only need column
       names/types from the result -- without the zero-row filter they would
       execute the full model query. #}
    {%- if select_sql_header is not none -%}
    {{ select_sql_header }}
    {#- A statement-style header gets the sentinel; a query-prefix header only
       needs a separator token so it cannot be glued onto the `select`. -#}
    {%- if (select_sql_header | trim).endswith(';') -%}|SEPARATEMEPLEASE|{{ '\n' }}{%- else %}
    {% endif -%}
    {%- endif -%}
    select * from (
        {{ select_sql }}
    ) dbt_sbq_tmp
    where false
    limit 0
{% endmacro %}

{% macro exasol__alter_relation_add_remove_columns(relation, add_columns, remove_columns) %}

    {% if add_columns is none %}
        {% set add_columns = [] %}
    {% endif %}
    {% if remove_columns is none %}
        {% set remove_columns = [] %}
    {% endif %}

    {% for column in add_columns %}
    {% set sql -%}
        alter {{ relation.type }} {{ relation }} add column {{ column.name }} {{ column.data_type }};
    {%- endset -%}
    {% do run_query(sql) %}
  {% endfor %}

    {% for column in remove_columns %}
    {% set sql -%}
        alter {{ relation.type }} {{ relation }} drop column {{ column.name }};
    {%- endset -%}
    {% do run_query(sql) %}
  {% endfor %}

{% endmacro %}
