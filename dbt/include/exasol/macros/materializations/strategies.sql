{% macro exasol__snapshot_hash_arguments(args) %}
    hash_md5({% for arg in args %}
        coalesce(cast({{ arg }} as varchar(100)), '') {% if not loop.last %} || '|' || {% endif %}
    {% endfor %})
{% endmacro %}

{#
    Helper macro to quote a column name for Exasol.
    - If already quoted (starts and ends with "), pass through as-is (user explicitly specified case)
    - Otherwise, uppercase and quote (standard Exasol behavior for unquoted identifiers)

    This handles the common case where:
    - Regular columns are created without quotes and stored as UPPERCASE
    - Reserved keyword columns should be specified with quotes in the config: '"time"'
#}
{% macro exasol__quote_column(col) -%}
    {%- if col.startswith('"') and col.endswith('"') -%}
        {{- col -}}
    {%- else -%}
        {{- adapter.quote(col | upper) -}}
    {%- endif -%}
{%- endmacro %}

{#
    Build properly quoted scd_args for Exasol snapshots.
    Handles both single and composite unique_key, plus the updated_at column.
#}
{% macro exasol__build_scd_args(primary_key, updated_at) %}
    {% set quoted_args = [] %}
    {% if primary_key is string %}
        {% do quoted_args.append(exasol__quote_column(primary_key)) %}
    {% else %}
        {% for pk in primary_key %}
            {% do quoted_args.append(exasol__quote_column(pk)) %}
        {% endfor %}
    {% endif %}
    {% do quoted_args.append(exasol__quote_column(updated_at)) %}
    {{ return(quoted_args) }}
{% endmacro %}

{#
    IMPORTANT: Global override of snapshot_timestamp_strategy.

    This macro does NOT use the exasol__ prefix because dbt's strategy_dispatch()
    function does not use adapter.dispatch() - it directly calls the strategy macro
    by name. Therefore, we must override the global macro to intercept it for Exasol.

    WARNING: In multi-adapter environments where multiple adapter packages are loaded,
    this global override may cause conflicts. This is a known limitation of dbt's
    snapshot strategy dispatch mechanism. For Exasol-only projects, this works correctly.

    Purpose: Properly quote column names (unique_key, updated_at) to handle SQL
    reserved keywords like TIME, DATE, USER, etc.
#}
{% macro snapshot_timestamp_strategy(node, snapshotted_rel, current_rel, model_config, target_exists) %}
    {% set primary_key = config.get('unique_key') %}
    {% set updated_at = config.get('updated_at') %}
    {% set hard_deletes = adapter.get_hard_deletes_behavior(config) %}
    {% set invalidate_hard_deletes = hard_deletes == 'invalidate' %}
    {% set columns = config.get("snapshot_table_column_names") or get_snapshot_table_column_names() %}

    {# Quote the updated_at column for use in row_changed expression #}
    {% set quoted_updated_at = exasol__quote_column(updated_at) %}

    {% set row_changed_expr -%}
        ({{ snapshotted_rel }}.{{ columns.dbt_valid_from }} < {{ current_rel }}.{{ quoted_updated_at }})
    {%- endset %}

    {# Build properly quoted scd_args #}
    {% set scd_args = exasol__build_scd_args(primary_key, updated_at) %}
    {% set scd_id_expr = snapshot_hash_arguments(scd_args) %}

    {% do return({
        "unique_key": primary_key,
        "updated_at": quoted_updated_at,
        "row_changed": row_changed_expr,
        "scd_id": scd_id_expr,
        "invalidate_hard_deletes": invalidate_hard_deletes,
        "hard_deletes": hard_deletes
    }) %}
{% endmacro %}

{% macro exasol__snapshot_check_all_get_existing_columns(node, target_exists) -%}
    {%- set query_columns = get_columns_in_query(node['injected_sql']) -%}
    {%- if not target_exists -%}
        {# no table yet -> return whatever the query does #}
        {{ return([false, query_columns]) }}
    {%- endif -%}
    {# handle any schema changes #}
    {%- set target_table = node.get('alias', node.get('name')) -%}
    {%- set target_relation = adapter.get_relation(database=node.database, schema=node.schema, identifier=target_table) -%}
    {%- set existing_cols = get_columns_in_query(node['injected_sql']) -%}
    {%- set ns = namespace() -%} {# handle for-loop scoping with a namespace #}
    {%- set ns.column_added = false -%}

    {%- set intersection = [] -%}
    {%- for col in query_columns -%}
        {%- if col in existing_cols -%}
            {%- do intersection.append(col) -%}
        {%- else -%}
            {% set ns.column_added = true %}
        {%- endif -%}
    {%- endfor -%}
    {{ return([ns.column_added, intersection]) }}
{%- endmacro %}

{#
    Exasol-specific snapshot_check_strategy with proper quoting for reserved keywords.
    Uses exasol__ prefix for proper dispatch.
#}
{% macro exasol__snapshot_check_strategy(node, snapshotted_rel, current_rel, config, target_exists) %}
    {% set check_cols_config = config['check_cols'] %}
    {% set primary_key = config['unique_key'] %}
    {% set hard_deletes = adapter.get_hard_deletes_behavior(config) %}
    {% set invalidate_hard_deletes = hard_deletes == 'invalidate' %}
    {% set select_current_time -%}
        select {{ snapshot_get_time() }} as snapshot_start
    {%- endset %}

    {#-- don't access the column by name, to avoid dealing with casing issues on exasol #}
    {%- set now = run_query(select_current_time)[0][0] -%}
    {% if now is none or now is undefined -%}
        {%- do exceptions.raise_compiler_error('Could not get a snapshot start time from the database') -%}
    {%- endif %}
    {% set updated_at = snapshot_string_as_time(now) %}

    {% set column_added = false %}

    {% if check_cols_config == 'all' %}
        {% set column_added, check_cols = exasol__snapshot_check_all_get_existing_columns(node, target_exists) %}
    {% elif check_cols_config is iterable and (check_cols_config | length) > 0 %}
        {% set check_cols = check_cols_config %}
    {% else %}
        {% do exceptions.raise_compiler_error("Invalid value for 'check_cols': " ~ check_cols_config) %}
    {% endif %}

    {# Quote check_cols for row_changed expression #}
    {%- set row_changed_expr -%}
    (
    {%- if column_added -%}
        TRUE
    {%- else -%}
    {%- for col in check_cols -%}
        {% set quoted_col = exasol__quote_column(col) %}
        {{ snapshotted_rel }}.{{ quoted_col }} != {{ current_rel }}.{{ quoted_col }}
        or
        ({{ snapshotted_rel }}.{{ quoted_col }} is null) != ({{ current_rel }}.{{ quoted_col }} is null)
        {%- if not loop.last %} or {% endif -%}
    {%- endfor -%}
    {%- endif -%}
    )
    {%- endset %}

    {# Build properly quoted scd_args - for check strategy, updated_at is a timestamp literal, not a column #}
    {% set quoted_args = [] %}
    {% if primary_key is string %}
        {% do quoted_args.append(exasol__quote_column(primary_key)) %}
    {% else %}
        {% for pk in primary_key %}
            {% do quoted_args.append(exasol__quote_column(pk)) %}
        {% endfor %}
    {% endif %}
    {% do quoted_args.append(updated_at) %}
    {% set scd_id_expr = snapshot_hash_arguments(quoted_args) %}

    {% do return({
        "unique_key": primary_key,
        "updated_at": updated_at,
        "row_changed": row_changed_expr,
        "scd_id": scd_id_expr,
        "invalidate_hard_deletes": invalidate_hard_deletes,
        "hard_deletes": hard_deletes
    }) %}
{% endmacro %}