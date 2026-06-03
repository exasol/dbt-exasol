# Design: Fix UDF correctness issues and clean up

## D1 — Python script generation: column-0 payload

### Problem
Jinja `{% macro %}` content is indented inside the source file. Jinja inserts the leading whitespace of the line containing `{{ … }}` only before the *first* line of the interpolated value; subsequent lines retain their original column. For Python UDFs the result is mixed indentation that Exasol's VM rejects at invocation time.

### Decision
Restructure the Python macros so the **entire `AS` payload is generated at column 0**. The macro becomes a top-level Jinja block that emits the CREATE statement preamble (which Exasol tolerates loose whitespace on) then a clean column-0 Python block.

### Target shape
```jinja
{% macro exasol__scalar_function_python(target_relation) %}
{% do exasol__warn_unsupported_volatility() %}
{% set runtime_version = model.config.get('runtime_version') %}
{% if runtime_version is not none %}
  {% do exceptions.warn("Found `runtime_version` ... will be ignored") %}
{% endif %}
CREATE OR REPLACE PYTHON3 SCALAR SCRIPT {{ target_relation.render() }} (
  {{ formatted_scalar_function_args_sql() }}
)
RETURNS {{ model.returns.data_type }}
AS
{{ model.compiled_code | trim }}

def run(ctx):
    return {{ model.config.get('entry_point') }}(
        {%- for arg in model.arguments -%}
            ctx.{{ arg.name }}{{ ", " if not loop.last }}
        {%- endfor -%}
    )
{% endmacro %}
```

Key points:
- No leading whitespace on lines that produce script content
- `| trim` on `compiled_code` removes trailing whitespace from user file
- Exactly one blank line separates user code from bridge
- `def run` at column 0; its body at 4 spaces

### Validation
- Inspect generated DDL in test debug logs (no leading whitespace on `def`)
- All four failing Python tests pass

## D2 — `BEGIN` detection: word-boundary regex

### Decision
Replace `'BEGIN' in code | upper` with a word-boundary regex via `modules.re`:

```jinja
{% set is_procedural = modules.re.search('\\bBEGIN\\b', code, modules.re.IGNORECASE) is not none %}
{% if is_procedural %}
    {{ code }}
{% else %}
    BEGIN
        RETURN {{ code }};
    END {{ model.name }};
{% endif %}
```

`modules.re` is exposed by dbt's Jinja sandbox and matches Python's `re` semantics. Word boundaries (`\b`) exclude `BEGIN_DATE`, `beginning`, etc.

### Alternatives considered
- **First-token anchor** — Rejected: breaks any procedural body with leading comment.
- **Explicit `procedural: true` config** — Rejected for this change: breaking change to existing behavior. Could be a future enhancement.

### Residual risk
A SQL string literal `'BEGIN'` inside an expression body would still match. Acceptable: extremely unlikely in scalar UDF expressions, and the workaround (use procedural form explicitly) is documented.

## D3 — Shared volatility warning macro

### Decision
Extract:

```jinja
{% macro exasol__warn_unsupported_volatility() %}
    {% set volatility = model.config.get('volatility') %}
    {% if volatility is not none %}
        {% do unsupported_volatility_warning(volatility) %}
    {% endif %}
{% endmacro %}
```

Call from `exasol__scalar_function_sql`, `exasol__scalar_function_python`, and `exasol__aggregate_function_python`. All three paths now produce identical warning behavior.

### Why a new macro vs. inlining
- One source of truth for the truthiness check (`is not none`)
- Easy to extend (e.g., add level=warn vs. fatal, or include node name in message)

## D4 — `aggregate_state` warning

### Decision
In `exasol__aggregate_function_python`, after the volatility warning:

```jinja
{% if model.config.get('aggregate_state') is not none %}
    {% do exceptions.warn(
        "Found `aggregate_state` specified on function `" ~ model.name ~
        "`. Exasol handles distributed aggregation transparently; `aggregate_state` and `merge()` are unused."
    ) %}
{% endif %}
```

Mirror the existing `runtime_version` warning style. README gains a sentence explicitly stating `merge()` is never invoked.

## D5 — Test mixin extraction

### Decision
Introduce in `test_udfs.py`:

```python
class ExasolPythonScalarScriptEventMixin:
    function_name = "price_for_xlarge"
    script_marker = "CREATE OR REPLACE PYTHON3 SCALAR SCRIPT"

    def is_function_create_event(self, event):
        return (event.data.node_info.node_name == self.function_name
                and self.script_marker in event.data.sql)
```

And in `test_udafs.py`:

```python
class ExasolPythonSetScriptEventMixin:
    function_name = "sum_squared"
    script_marker = "CREATE OR REPLACE PYTHON3 SET SCRIPT"
    # same is_function_create_event body
```

(Or one shared mixin in a `conftest.py`/helpers module if preferred.)

Test classes become one-liners:
```python
class TestExasolPythonUDF(ExasolPythonScalarScriptEventMixin, PythonUDFSupported):
    @pytest.fixture(scope="class")
    def functions(self): ...
```

### Duplicate `test_udfs` bodies
`TestExasolPythonUDFRuntimeVersionRequired` and `TestExasolPythonUDFEntryPointRequired` have byte-identical `test_udfs` methods differing only in expected error string. Collapse via a parent helper:

```python
class _PythonUDFValidationTest:
    expected_error: str  # set by subclass

    def test_udfs(self, project, sql_event_catcher):
        run_result_error_catcher = EventCatcher(RunResultError)
        result = run_dbt(["build", "--debug"], expect_pass=False,
                         callbacks=[run_result_error_catcher.catch])
        assert len(result.results) == 1
        assert result.results[0].status == RunStatus.Error
        assert len(run_result_error_catcher.caught_events) == 1
        assert self.expected_error in run_result_error_catcher.caught_events[0].data.msg
```

## D6 — `TestExasolAggregateSQLError` cascade tolerance

### Problem
Base dbt fixture includes `basic_model.sql` referencing `{{ function('sum_squared') }}`. When the UDAF compile-errors:
1. The function itself errors with our message ✓
2. The dependent model also errors (cascade) ✗ (extra unexpected result)

### Decision
Override to assert *the function result*, not the result count:

```python
def test_udaf(self, project, sql_event_catcher):
    catcher = EventCatcher(RunResultError)
    result = run_dbt(["build", "--debug"], expect_pass=False, callbacks=[catcher.catch])

    function_results = [r for r in result.results if r.node.resource_type == "function"]
    assert len(function_results) == 1
    assert function_results[0].status == RunStatus.Error

    function_errors = [
        e for e in catcher.caught_events
        if "SQL aggregate UDFs are not supported in Exasol" in e.data.msg
    ]
    assert len(function_errors) == 1
```

This stays correct whether or not the cascading model failure is present.

## D7 — `tasks.md` of `add-udf-function-support`

Strike tasks 1.1.2, 1.1.4, 1.1.5 (Option B sub-macros that were never implemented), or mark each with an `(N/A — Option A chosen)` note. Mechanical edit; no spec impact.

## Risk Summary

| Risk | Mitigation |
|------|------------|
| Whitespace fix breaks SQL UDF (which currently works) | SQL macro touched only for shared-warning refactor; payload structure unchanged. Tests cover it. |
| Regex `\bBEGIN\b` rejects a case the substring accepted | Behavior change documented; no test currently uses an edge case |
| `modules.re` not available in Jinja sandbox | `modules.re` is part of dbt's default macro context (stable since dbt 1.x). If absent, fall back to `regex_search` filter |
| Cascade test still fails after fix | Validated by D6 selecting by `resource_type == "function"` (always present even on cascade) |
