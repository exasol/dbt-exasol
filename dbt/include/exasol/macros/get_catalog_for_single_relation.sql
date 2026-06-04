{#
    Single-relation catalog lookup.

    `ExasolAdapter.get_catalog_for_single_relation` calls the `get_catalog_for_single_relation`
    macro with a single `relation` kwarg. We provide a dispatching wrapper plus an
    Exasol implementation that delegates to `exasol__get_catalog_relations` with a
    one-element relation list, so the relation-filtered EXA object/column where-clause
    logic is reused rather than duplicated. This guarantees the returned column shape
    matches the full-schema `exasol__get_catalog` path.
#}
{% macro get_catalog_for_single_relation(relation) -%}
    {{ return(adapter.dispatch('get_catalog_for_single_relation', 'dbt')(relation)) }}
{%- endmacro %}


{% macro default__get_catalog_for_single_relation(relation) -%}
    {% do exceptions.raise_not_implemented(
        '`get_catalog_for_single_relation` macro not implemented for adapter ' ~ adapter.type()
    ) %}
{%- endmacro %}


{% macro exasol__get_catalog_for_single_relation(relation) -%}
    {{ return(exasol__get_catalog_relations(none, [relation])) }}
{%- endmacro %}
