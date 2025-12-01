{% macro exasol__get_show_grant_sql(relation) %}
    select privilege as "privilege_type", grantee as "grantee"
    from EXA_DBA_OBJ_PRIVS
    where upper(object_schema) = upper('{{ relation.schema }}')
      and upper(object_name) = upper('{{ relation.name }}')
      -- filter out current user
      and grantee != current_user
{% endmacro %}

{% macro exasol__call_dcl_statements(dcl_statement_list) %}
    {#- Exasol doesn't allow multiple statements so we have to call it individually... -#}
    {% for dcl_statement in dcl_statement_list %}
        {% call statement('grants') %}
            {{ dcl_statement }};
        {% endcall %}
    {% endfor %}
{% endmacro %}
