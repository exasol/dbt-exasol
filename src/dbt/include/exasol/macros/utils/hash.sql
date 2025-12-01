{% macro exasol__hash(field) -%}
    hashtype_md5(cast({{ field }} as {{ api.Column.translate_type('string') }}))
{%- endmacro %}
