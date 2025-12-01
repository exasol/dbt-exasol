{% macro exasol__get_catalog(information_schema, schemas) -%}

    {% set query %}
        with tables as (
            {{ exasol__get_catalog_tables_sql(information_schema) }}
        ),
        columns as (
            {{ exasol__get_catalog_columns_sql(information_schema) }}
        )
        {{ exasol__get_catalog_results_sql() }}
        {{ exasol__get_catalog_schemas_where_clause_sql(schemas) }}
        order by 
        tables.table_owner,
        columns.table_name,
        columns.column_index
    {%- endset -%}

    {{ return(run_query(query)) }}

{%- endmacro %}


{% macro exasol__get_catalog_relations(information_schema, relations) -%}

    {% set query %}
        with tables as (
            {{ exasol__get_catalog_tables_sql(information_schema) }}
        ),
        columns as (
            {{ exasol__get_catalog_columns_sql(information_schema) }}
        )
        {{ exasol__get_catalog_results_sql() }}
        {{ exasol__get_catalog_relations_where_clause_sql(relations) }}
        order by 
        tables.table_owner,
        columns.table_name,
        columns.column_index
    {%- endset -%}

    {{ return(run_query(query)) }}

{%- endmacro %}


{% macro exasol__get_catalog_tables_sql(information_schema) -%}
    select
      'DB' as table_database,
      ROOT_NAME as table_schema,
      OBJECT_NAME as table_name,
      ROOT_NAME as table_owner,
      OBJECT_TYPE AS table_type,
      OBJECT_COMMENT as table_comment
    from sys.EXA_USER_OBJECTS 
    WHERE OBJECT_TYPE IN('TABLE', 'VIEW')
{%- endmacro %}


{% macro exasol__get_catalog_columns_sql(information_schema) -%}
    select
        'DB' as table_database,
        column_schema as table_schema,
        column_table as table_name,
        column_name,
        column_ordinal_position as column_index,
        column_type,
        column_comment
    from sys.exa_user_columns
{%- endmacro %}


{% macro exasol__get_catalog_results_sql() -%}
    select 
      tables.table_owner as [table_owner],
      tables.table_type AS [table_type],
      tables.table_comment as [table_comment],
      columns.table_database as [table_database],
      columns.table_schema as [table_schema],
      columns.table_name as [table_name],
      columns.column_name as [column_name],
      columns.column_index as [column_index],
      case 
      when columns.column_type='TIMESTAMP(3)' then 'TIMESTAMP' 
      else columns.column_type 
      end as [column_type],
      columns.column_comment as [column_comment]
    from tables
    join columns on tables.table_database = columns.table_database and tables.table_schema = columns.table_schema and tables.table_name = columns.table_name
{%- endmacro %}


{% macro exasol__get_catalog_schemas_where_clause_sql(schemas, schema_name) -%}
   where ({%- for schema in schemas -%}
        upper(tables.table_owner) = upper('{{ schema }}'){%- if not loop.last %} or {% endif -%}
    {%- endfor -%})
{%- endmacro %}


{% macro exasol__get_catalog_relations_where_clause_sql(relations) -%}
    where (
        {%- for relation in relations -%}
            {% if relation.schema and relation.identifier %}
                (
                    upper(tables.table_owner) = upper('{{ relation.schema }}')
                    and upper(columns.table_name) = upper('{{ relation.identifier }}')
                )
            {% elif relation.schema %}
                (
                    upper(tables.table_owner) = upper('{{ relation.schema }}')
                )
            {% else %}
                {% do exceptions.raise_compiler_error(
                    '`get_catalog_relations` requires a list of relations, each with a schema'
                ) %}
            {% endif %}

            {%- if not loop.last %} or {% endif -%}
        {%- endfor -%}
    )
{%- endmacro %}