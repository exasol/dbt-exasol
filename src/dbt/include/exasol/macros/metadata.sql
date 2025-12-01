{% macro exasol__get_relation_last_modified(information_schema, relations) -%}

  {%- call statement('last_modified', fetch_result=True) -%}
        select root_name as table_schema,
               object_name as identifier,
               object_type as table_type,
               last_commit as last_modified,
               {{ current_timestamp() }} as snapshotted_at
        from sys.exa_user_objects
        where (
          {%- for relation in relations -%}
            (upper(root_name) = upper('{{ relation.schema }}') and
             upper(object_name) = upper('{{ relation.identifier }}') and
             upper(object_type) in ('TABLE', 'VIEW')){%- if not loop.last %} or {% endif -%}
          {%- endfor -%}
        )
  {%- endcall -%}

  {{ return(load_result('last_modified')) }}

{% endmacro %}