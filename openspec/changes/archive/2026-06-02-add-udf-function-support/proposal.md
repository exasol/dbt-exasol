# Change: Add UDF function support to dbt-exasol

## Why
Issue #178 requires dbt-exasol to support dbt-core v1.11's new User-Defined Function (UDF) feature. UDFs allow defining and registering custom functions in Exasol that can be reused outside dbt (BI tools, notebooks), promoting code reuse across the data platform.

## What Changes

### SQL Scalar UDFs via CREATE FUNCTION
- Create `materializations/functions/scalar.sql` with Exasol-specific macro overrides
- Generate `CREATE OR REPLACE FUNCTION schema.name(args) RETURN type IS ... END` syntax
- Support both expression bodies (auto-wrapped) and full procedural bodies (auto-detect via `BEGIN` keyword)
- Handle dbt's `SELECT <expr>` convention by stripping leading `SELECT` keyword
- Emit warning for unsupported `volatility` configuration (Exasol doesn't support it)

### Python Scalar UDFs via CREATE SCRIPT
- Add Python UDF support in `materializations/functions/scalar.sql`
- Generate `CREATE OR REPLACE PYTHON3 SCALAR SCRIPT` with `run(ctx)` bridge wrapper
- Bridge maps Exasol's `ctx.param` API to dbt's direct-argument convention by iterating `model.arguments`
- Ignore `runtime_version` config with warning (Exasol uses `PYTHON3` keyword, no version selection)

### Python Aggregate UDFs via CREATE SET SCRIPT
- Create `materializations/functions/aggregate.sql`
- Generate `CREATE OR REPLACE PYTHON3 SET SCRIPT` with `ctx.next()` iteration bridge
- Instantiate user's class via `model.config.get('entry_point')` (e.g., `SumSquared`)
- Bridge calls `accumulate()` per row and `finish()` at end; `merge()` and `aggregate_state` are unused (Exasol handles distribution transparently)

### Cross-Type Cleanup
- Override `function_execute_build_sql` in `materializations/functions/helpers.sql`
- Before CREATE, check `model.language`: drop stale SCRIPT when creating FUNCTION (and vice versa)
- Uses `model.get('language')` (not `target_relation.language` which doesn't exist on BaseRelation)

### Error Handling
- SQL aggregate UDFs: raise clear error (Exasol has no SQL aggregate mechanism)
- Validation of required Python configs (runtime_version, entry_point) handled by dbt-core

### Tests
- Create `tests/functional/adapter/functions/test_udfs.py` and `test_udafs.py`
- Override `is_function_create_event()` in Python/aggregate test classes (base checks for `CREATE OR REPLACE FUNCTION` / `CREATE OR REPLACE AGGREGATE FUNCTION` which don't match Exasol's `CREATE ... SCRIPT` syntax)
- Override `check_function_volatility()` in volatility test classes to assert keyword absence
- Override test fixtures for Exasol data types (`float` -> `DOUBLE`, `numeric` -> `DECIMAL`)

## Impact
- **Affected specs**: New `udf-functions` capability
- **Affected code**: 3 new macro files (~300 lines), 2 new test files (~250 lines)
- **Risk**: Medium -- complex DDL generation, Python bridge requires testing
- **Backward compatibility**: No breaking changes -- entirely additive feature

## Dependencies
- Requires `upgrade-dbt-core-1.11-compat` to be completed first

## Design Document
See `design.md` for detailed technical decisions on Exasol DDL mapping, Python bridge implementation, and test overrides.

---

## Review Findings

### Bugs

#### B1 — `PythonUDFRuntimeVersionRequired` / `PythonUDFEntryPointRequired` will fail at test time
Tasks 4.1.7 and 4.1.8 say "inherit directly (validation is dbt-core level)." That assumption is wrong in practice.

Both classes inherit from `PythonUDFNotSupported`, whose `test_udfs` asserts:
```
"No macro named 'scalar_function_python' found within namespace"
```
Since Exasol implements `exasol__scalar_function_python`, that error is never raised. dbt-core's validation fires a different message:
- `"A runtime_version is required for python functions"`
- `"An entry_point is required for python functions"`

**Fix**: Both `TestExasolPythonUDFRuntimeVersionRequired` and `TestExasolPythonUDFEntryPointRequired` need `test_udfs` overrides that assert the correct dbt-core error message instead of the "macro not found" message.

#### B2 — Trailing `;` produces double-semicolons in `default__scalar_function_sql`
The dbt-core default composes sub-macros as:
```jinja
{{ scalar_function_create_replace_signature_sql(target_relation) }}
{{ scalar_function_body_sql() }};   {# ← trailing semicolon appended by dbt #}
```
Exasol procedural bodies already end with `END my_udf;`. Using the sub-dispatch path (tasks 1.1.2–1.1.3) without overriding the top-level `scalar_function_sql` yields double semicolons and a DDL parse error. This is the primary reason `exasol__scalar_function_sql` must be overridden at the top level.

### Consistency Issues

#### C1 — Sub-macro strategy conflicts with top-level override (tasks 1.1.1–1.1.5)
The dbt dispatch chain for SQL scalar UDFs is:
```
function.sql → scalar_function_sql → default__scalar_function_sql
                                        ├─ scalar_function_create_replace_signature_sql
                                        ├─ scalar_function_body_sql  ← (+ trailing ;)
                                        └─ scalar_function_volatility_sql
```
Task 1.1.1 overrides `exasol__scalar_function_sql` (the top level). Once that fires, `default__scalar_function_sql` is never called, so tasks 1.1.2–1.1.5 produce dead code — sub-overrides that no dispatch path ever reaches.

**Resolution**: Choose one of two consistent models:
- **Option A (recommended)** — Override only the four top-level entry points: `exasol__scalar_function_sql`, `exasol__scalar_function_python`, `exasol__aggregate_function_sql`, `exasol__aggregate_function_python`. Each macro generates complete DDL inline. Drop tasks 1.1.2–1.1.5.
- **Option B** — Remove task 1.1.1; rely on sub-dispatch only; handle the trailing `;` issue by ensuring `exasol__scalar_function_body_sql` emits the full `IS … END name;` block without a trailing semicolon and dbt appends the required one. More fragile.

**Option A is strongly preferred.**

#### C2 — `exasol__formatted_scalar_function_args_sql` override is unnecessary (task 1.1.4)
The default `default__formatted_scalar_function_args_sql` already generates exactly `name type, name type` from `model.arguments` with no DEFAULT clause — identical to what Exasol needs. The data-type mapping (`float` vs `DOUBLE`) belongs in test YAML fixtures, not in this macro. Additionally, `formatted_scalar_function_args_sql` is reused by `default__get_formatted_aggregate_function_args`, so not overriding it is the correct choice for the aggregate path too.

**Fix**: Remove task 1.1.4 entirely.

#### C3 — `formatted_scalar_function_args_sql()` call ambiguous in design snippets
Decision 2 and 3 in design.md call `formatted_scalar_function_args_sql()` (without namespace prefix) inside the Exasol bridge macros. Since `exasol__formatted_scalar_function_args_sql` is not defined (per C2), the call dispatches to the default, which works correctly. However, the naming implies an Exasol override might be in scope. Clarify in design.md that `formatted_scalar_function_args_sql()` calls the dispatched default intentionally.

#### C4 — `model.get('language')` default value inconsistent across artifacts
- Proposal (Cross-Type Cleanup section): `model.get('language')` — no default
- Design Decision 4: `model.get('language', 'sql')` — with default
- Task 3.1.1: repeats the version without a default

`model.language` may not be set for SQL functions without an explicit `language:` key. The default `'sql'` is the safe choice. Use `model.get('language', 'sql')` consistently in all three artifacts.

#### C5 — `function()` macro resolution is dbt-core behaviour, not adapter work
The spec scenario "Referencing UDF in models" says the macro resolves to `schema.my_udf` (no database prefix). This is driven by how `target_relation.render()` works on Exasol's existing relation class (schema-only, no database prefix). It is not a new implementation task for UDF support. Fine to document as a constraint, but should not be framed as a testable requirement in the spec.

### KISS Observations

#### K1 — SQL aggregate error test must not assert on `sql_event_catcher` (task 5.1.1)
`UDAFBase.test_udaf` first builds (then checks `sql_event_catcher`). When the build *fails*, the event catcher catches nothing — any inherited assertion on `sql_event_catcher.caught_events` will fail. The `TestExasolAggregateSQLError` override of `test_udaf` must use `run_dbt([...], expect_pass=False)` and check for the error message only, skipping all event catcher assertions.

#### K2 — Three identical volatility overrides → one shared mixin (tasks 4.1.2–4.1.4)
`TestExasolDeterministicUDF`, `TestExasolStableUDF`, and `TestExasolNonDeterministicUDF` each override `check_function_volatility` to assert a single keyword is absent. Since Exasol emits *nothing* for all volatility values, all three checks are equivalent. A single mixin keeps the intent explicit:

```python
class ExasolVolatilityMixin:
    def check_function_volatility(self, sql: str):
        assert "IMMUTABLE" not in sql
        assert "STABLE" not in sql
        assert "VOLATILE" not in sql

class TestExasolDeterministicUDF(ExasolVolatilityMixin, DeterministicUDF): pass
class TestExasolStableUDF(ExasolVolatilityMixin, StableUDF): pass
class TestExasolNonDeterministicUDF(ExasolVolatilityMixin, NonDeterministicUDF): pass
```

Apply the same mixin to `TestExasolPythonUDFVolatility` (task 4.1.11), which needs the same check.

### Finding Summary

| # | Severity | Area | Tasks | Issue |
|---|---|---|---|---|
| B1 | 🐛 Bug | Tests | 4.1.7–4.1.8 | Wrong error message asserted; tests will fail |
| B2 | 🐛 Bug | Macros | 1.1.1–1.1.3 | Double `;` if sub-dispatch path used without top-level override |
| C1 | ⚠️ Consistency | Design/Tasks | 1.1.1–1.1.5 | Top-level override and sub-overrides are mutually exclusive; dead code |
| C2 | ⚠️ Consistency | Tasks | 1.1.4 | `formatted_scalar_function_args_sql` override is unnecessary |
| C3 | ⚠️ Consistency | Design | design.md §D2–D3 | `formatted_scalar_function_args_sql()` call ambiguous in snippets |
| C4 | ⚠️ Consistency | All artifacts | proposal/design/tasks | `model.get('language')` default missing in two of three places |
| C5 | ℹ️ Minor | Spec | spec.md | `function()` resolution is dbt-core behaviour, not adapter work |
| K1 | 💡 KISS | Tests | 5.1.1 | SQL aggregate error test must not assert on `sql_event_catcher` |
| K2 | 💡 KISS | Tests | 4.1.2–4.1.4, 4.1.11 | Three identical volatility overrides → one shared mixin |
