## Context
dbt-exasol is adding full UDF support for dbt-core v1.11. Exasol has a unique dual-mechanism system that requires careful mapping to dbt's UDF framework.

## Exasol's Two Mechanisms

### CREATE FUNCTION (SQL only, scalar only)
- System table: `EXA_ALL_FUNCTIONS`
- Syntax: `CREATE OR REPLACE FUNCTION schema.name(args) RETURN type IS [vars;] BEGIN ... RETURN expr; END name;`
- Supports: procedural SQL, variables, IF/ELSE, FOR loops
- Drop command: `DROP FUNCTION [IF EXISTS] schema.name`
- No volatility support, no default argument values

### CREATE SCRIPT (Multi-language: Lua, Python3, Java, R)
- System table: `EXA_ALL_SCRIPTS`
- Types: `SCALAR` (row-level) or `SET` (aggregate)
- Syntax: `CREATE OR REPLACE PYTHON3 [SCALAR|SET] SCRIPT schema.name(args) RETURNS type AS <code>`
- Uses `ctx.param_name` API for parameter access, `ctx.next()` for row iteration in SET scripts
- Drop command: `DROP SCRIPT [IF EXISTS] schema.name`

## Goals
1. SQL Scalar UDFs via `CREATE FUNCTION`
2. Python Scalar UDFs via `CREATE PYTHON3 SCALAR SCRIPT` with bridge
3. Python Aggregate UDFs via `CREATE PYTHON3 SET SCRIPT` with bridge
4. Clear errors for unsupported SQL aggregate UDFs
5. Cross-type cleanup when switching between SQL and Python

## Non-Goals
- Lua/Java/R script support (dbt framework only supports SQL and Python)
- SQL aggregate UDFs (Exasol has no SQL aggregate function mechanism)
- Table-returning UDFs (not yet supported in dbt framework)
- PACKAGES clause (Exasol uses BucketFS for Python libraries, not inline PACKAGES)

## Decisions

### Decision 1: SQL Body Format -- Auto-detect expression vs procedural
**Rationale**: Exasol's CREATE FUNCTION supports full procedural SQL. We auto-detect based on `BEGIN` keyword presence.

**Implementation** (Jinja):
```jinja
{% macro exasol__scalar_function_body_sql() %}
    {% set code = model.compiled_code | trim %}
    {# Strip leading SELECT (dbt convention) #}
    {% if code[:6] | lower == 'select' %}
        {% set code = code[6:] | trim %}
    {% endif %}
    {# Auto-detect procedural vs expression body #}
    {% if 'BEGIN' in code | upper %}
        {# Procedural: user provides full IS...END block #}
        {{ code }}
    {% else %}
        {# Expression: wrap in BEGIN RETURN <expr>; END <name>; #}
    BEGIN
        RETURN {{ code }};
    END {{ model.name }};
    {% endif %}
{% endmacro %}
```

### Decision 2: Python Scalar Bridge -- Generate `run(ctx)` wrapper
**Rationale**: dbt's Python convention uses direct function arguments (`def main(price)`). Exasol's scripts use `ctx` API (`ctx.price`). We generate a bridge.

**Implementation** (Jinja):
```jinja
{% macro exasol__scalar_function_python(target_relation) %}
    CREATE OR REPLACE PYTHON3 SCALAR SCRIPT {{ target_relation.render() }}
        ({{ formatted_scalar_function_args_sql() }})
        RETURNS {{ model.returns.data_type }}
    AS
    {{ model.compiled_code }}

    def run(ctx):
        return {{ model.config.get('entry_point') }}(
            {%- for arg in model.arguments -%}
                ctx.{{ arg.name }}{{ ", " if not loop.last }}
            {%- endfor -%}
        )
{% endmacro %}
```

Key details:
- Iterates `model.arguments` to generate `ctx.arg1, ctx.arg2, ...` for all parameters
- Uses `model.config.get('entry_point')` to call the user's function (e.g., `price_for_xlarge`)
- `runtime_version` is ignored with warning (Exasol uses `PYTHON3` keyword, no version selection)

### Decision 3: Python Aggregate Bridge -- Iteration wrapper with class instantiation
**Rationale**: dbt's Python UDAF convention uses a class with `accumulate`/`merge`/`finish` methods. Exasol SET scripts iterate rows with `ctx.next()`.

**Implementation** (Jinja):
```jinja
{% macro exasol__aggregate_function_python(target_relation) %}
    CREATE OR REPLACE PYTHON3 SET SCRIPT {{ target_relation.render() }}
        ({{ formatted_scalar_function_args_sql() }})
        RETURNS {{ model.returns.data_type }}
    AS
    {{ model.compiled_code }}

    def run(ctx):
        agg = {{ model.config.get('entry_point') }}()
        while True:
            agg.accumulate(
                {%- for arg in model.arguments -%}
                    ctx.{{ arg.name }}{{ ", " if not loop.last }}
                {%- endfor -%}
            )
            if not ctx.next():
                break
        return agg.finish()
{% endmacro %}
```

Key details:
- Class name from `model.config.get('entry_point')` (e.g., `SumSquared`)
- Bridge calls `accumulate()` per row and `finish()` at end
- `merge()` and `aggregate_state` from dbt convention are **unused** -- Exasol handles distributed aggregation transparently via its cluster architecture
- Multiple arguments supported via `model.arguments` iteration

### Decision 4: Cross-Type Cleanup -- Use `model.get('language')`
**Rationale**: If user switches from SQL to Python, both objects exist (FUNCTION in `EXA_ALL_FUNCTIONS`, SCRIPT in `EXA_ALL_SCRIPTS`). Must clean up.

**Critical**: The language is on `model`, NOT on `target_relation`. `BaseRelation` has no `language` attribute.

**Implementation** (Jinja):
```jinja
{% macro exasol__function_execute_build_sql(build_sql, existing_relation, target_relation) %}
    {% set language = model.get('language', 'sql') %}
    {% if language == 'sql' %}
        {# Creating FUNCTION -- drop any stale SCRIPT with same name #}
        {% call statement('drop_stale_script', auto_begin=False) %}
            DROP SCRIPT IF EXISTS {{ target_relation.render() }}
        {% endcall %}
    {% else %}
        {# Creating SCRIPT -- drop any stale FUNCTION with same name #}
        {% call statement('drop_stale_function', auto_begin=False) %}
            DROP FUNCTION IF EXISTS {{ target_relation.render() }}
        {% endcall %}
    {% endif %}

    {{ default__function_execute_build_sql(build_sql, existing_relation, target_relation) }}
{% endmacro %}
```

Uses `target_relation.render()` which respects Exasol's schema-only naming (no database prefix).

### Decision 5: Volatility -- Warn via existing dispatch mechanism
**Rationale**: Exasol doesn't support IMMUTABLE/STABLE/VOLATILE. Use dbt-adapters' built-in `unsupported_volatility_warning` macro for all volatility values.

**Implementation** (Jinja):
```jinja
{% macro exasol__scalar_function_volatility_sql() %}
    {% set volatility = model.config.get('volatility') %}
    {% if volatility is not none %}
        {% do unsupported_volatility_warning(volatility) %}
    {% endif %}
{% endmacro %}
```

### Decision 6: Test Fixture Overrides
**Rationale**: Base test classes check for SQL patterns that don't match Exasol's DDL:

| Base class check | Exasol DDL | Override needed |
|---|---|---|
| `"CREATE OR REPLACE FUNCTION" in sql` | `CREATE OR REPLACE FUNCTION` (SQL scalar) | No -- matches! |
| `"CREATE OR REPLACE FUNCTION" in sql` | `CREATE OR REPLACE PYTHON3 SCALAR SCRIPT` (Python scalar) | Yes -- override `is_function_create_event()` |
| `"CREATE OR REPLACE AGGREGATE FUNCTION" in sql` | `CREATE OR REPLACE PYTHON3 SET SCRIPT` (Python aggregate) | Yes -- override `is_function_create_event()` |
| `"IMMUTABLE" in sql` | (no keyword) | Yes -- override `check_function_volatility()` |
| `"STABLE" in sql` | (no keyword) | Yes -- override `check_function_volatility()` |
| `"VOLATILE" in sql` | (no keyword) | Yes -- override `check_function_volatility()` |

Data type mapping for Exasol test fixtures:
- `float` -> `DOUBLE` (or keep as `float` -- Exasol accepts `FLOAT` as alias for `DOUBLE PRECISION`)
- `numeric` -> `DECIMAL` (or keep as `numeric` -- need to test Exasol acceptance)

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Python bridge overhead | Minimal -- one extra function call per row |
| Aggregate `merge` unused | Document; Exasol handles distribution transparently |
| CREATE SCRIPT with embedded semicolons | pyexasol sends as single statement; no `\|SEPARATEMEPLEASE\|` needed |
| No SQL aggregate support | Clear compilation error with actionable message |
| Namespace collision (FUNCTION vs SCRIPT) | Cross-type cleanup in `function_execute_build_sql` |
| SELECT stripping edge case | Only strip at start, after trim, case-insensitive; safe for all normal bodies |
| Exasol PYTHON3 only -- no version selection | Warn if `runtime_version` set; PYTHON3 keyword is fixed |
