{% macro exasol__split_part(string_text, delimiter_text, part_number) %}

  {{ exceptions.raise_compiler_error("Unsupported on Exasol! Sorry...") }}

{% endmacro %}
