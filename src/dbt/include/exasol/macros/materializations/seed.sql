{% macro exasol__basic_load_csv_rows(model, batch_size, agate_table) %}

    {% do adapter.add_query( "0CSV|"+this.render(), bindings=agate_table, abridge_sql_log=True) %}

    {# Return SQL so we can render it out into the compiled files #}
    {{ return('IMPORT INTO {} FROM CSV AT ...'.format(this.render())) }}
{% endmacro %}

{% macro exasol__load_csv_rows(model, agate_table) %}
  {{ return(exasol__basic_load_csv_rows(model, 10000, agate_table) )}}
{% endmacro %}