# Change: Fix UDF correctness issues and clean up

## Why
The completed `add-udf-function-support` change has five correctness and quality issues uncovered after merging, and 5 of 14 functional UDF/UDAF tests currently fail. This change fixes the bugs, restores green tests, and tightens the implementation.

## Context
`add-udf-function-support` is functionally complete and addresses all of its own prior review findings (B1, B2, C1, C2, C4, K1, K2). The remaining issues were uncovered during a post-merge cross-check:

- **Functional tests partially broken**: 5 / 14 tests fail.
- **Real correctness bugs**: indentation-corrupted Python scripts cause Exasol VM crashes; `BEGIN` substring detection produces false positives.
- **Behavioral inconsistencies**: volatility warning only fires on the SQL path; `aggregate_state` is silently ignored.
- **Hygiene**: `tasks.md` of the previous change still claims sub-macros are "done" that don't exist (Option A was chosen).

## What Changes

### 1. Fix Python UDF/UDAF generated script indentation (bug — VM crash)
The macros `exasol__scalar_function_python` and `exasol__aggregate_function_python` interpolate `model.compiled_code` inside an indented Jinja block. Jinja indents only the first line; subsequent lines retain the user's original column. Combined with the indented `def run(ctx):` template wrapper, this produces a Python script with inconsistent indentation that compiles inside Exasol but crashes the VM on invocation:

```
    AS
    def price_for_xlarge(price: float) -> float:   ← 4-space (jinja indent)
  return price * 2                                 ← 2-space (user file, no jinja prefix)

    def run(ctx):                                  ← 4-space (jinja indent)
        return price_for_xlarge(ctx.price)
```

**Fix**: Restructure the macro so the `AS` payload is column-0. Use `{{ model.compiled_code | trim }}` and place `def run(ctx):` at column 0 with no leading whitespace inside the macro. Strip any user-code trailing whitespace, add exactly one blank line, then the bridge function.

### 2. Robust procedural-body detection (bug — false positives)
`exasol__scalar_function_sql` uses `'BEGIN' in code | upper`, which mis-classifies any expression containing the letters `BEGIN` (e.g., `BEGIN_DATE`, `beginning`, `'BEGIN'` literal).

**Fix**: Replace with a word-boundary regex test using `regex_search('\\bBEGIN\\b', ...)` (or equivalent Jinja-available approach via `re.search` exposed by dbt). Anchor the detection on whole-word matches only.

### 3. Volatility warning consistency
`exasol__scalar_function_sql` warns when `volatility` is set; `exasol__scalar_function_python` and `exasol__aggregate_function_python` silently ignore it. README documents the warning as universal.

**Fix**: Extract a shared `{% macro exasol__warn_unsupported_volatility() %}` helper and call it from all three top-level macros. Both Python paths must produce the same warning as the SQL path.

### 4. `aggregate_state` ignored-warning
The Python aggregate path silently discards `aggregate_state` (and any user-implemented `merge` method) because Exasol handles distribution transparently. Other ignored configs (`runtime_version`, `volatility`) warn the user; this one doesn't.

**Fix**: Add a warning in `exasol__aggregate_function_python` when `model.config.get('aggregate_state')` is set. Document in README that `merge()` will never be invoked.

### 5. Test refactor — `ExasolPythonScriptEventMixin`
Five test classes carry near-identical `is_function_create_event` overrides differing only by node name and SCRIPT type:

```
test_udfs.py:   TestExasolPythonUDF, TestExasolPythonUDFDefaultArg, TestExasolPythonUDFVolatility
test_udafs.py:  TestExasolAggregatePython, TestExasolAggregatePythonDefaultArg
```

**Fix**: Introduce `ExasolPythonScalarScriptEventMixin` and `ExasolPythonSetScriptEventMixin` (or one parameterized mixin with class-level `function_name` + `script_marker`). Mirror the `ExasolVolatilityMixin` pattern already established by K2. Collapse the two duplicate `test_udfs` bodies in `RuntimeVersionRequired` / `EntryPointRequired` into a shared helper or parameterized base.

### 6. Failing functional tests — restore green suite
Currently failing:

| Test | Cause | Fix |
|------|-------|-----|
| `TestExasolAggregatePython::test_udaf` | Python script indentation (#1) | Fixed by #1 |
| `TestExasolAggregatePythonDefaultArg::test_udaf` | Python script indentation (#1) | Fixed by #1 |
| `TestExasolPythonUDF::test_udfs` | Python script indentation (#1) | Fixed by #1 |
| `TestExasolPythonUDFVolatility::test_udfs` | Python script indentation (#1) | Fixed by #1 |
| `TestExasolAggregateSQLError::test_udaf` | Asserts `len(result.results) == 1` but cascading model failure produces 2 | Relax assertion: select the `function.*` result via predicate; only assert that result's error message contains our error string |

The cascade in the last test happens because the base dbt fixture's `basic_model.sql` references `{{ function('sum_squared') }}`; when the UDAF compile-errors, the dependent model also errors. Our override must tolerate ≥ 1 result and pick out the function-typed one.

### 7. Hygiene: update stale `tasks.md` of the previous change
Tasks 1.1.2, 1.1.4, 1.1.5 in `openspec/changes/add-udf-function-support/tasks.md` claim sub-macros are implemented; they aren't (Option A chosen during implementation). Update those entries to reflect Option A reality so the archive flow leaves a clean record.

## Impact
- **Affected specs**: `udf-functions` — MODIFIED requirements for volatility warning (now universal) and Python script generation (whitespace-correct)
- **Affected code**:
  - `dbt/include/exasol/macros/materializations/functions/scalar.sql` (~40 line touch)
  - `dbt/include/exasol/macros/materializations/functions/aggregate.sql` (~20 line touch)
  - `tests/functional/adapter/functions/test_udfs.py` (mixin extraction)
  - `tests/functional/adapter/functions/test_udafs.py` (cascade-tolerant assertion + mixin)
  - `README.md` (volatility/merge clarifications)
  - `openspec/changes/add-udf-function-support/tasks.md` (3-line hygiene fix)
- **Risk**: Low. All fixes are localized; tests prove correctness end-to-end.
- **Backward compatibility**: Behavior changes are bug fixes. The new word-boundary `BEGIN` detection is stricter — any user model that relied on accidental substring matching to enter procedural mode would change behavior, but that path is undocumented and unlikely.

## Out of Scope
- R/Lua/Java UDF support (Exasol supports these natively but dbt-core does not yet — future work)
- Doc-only review findings C3 (design.md clarification) and C5 (spec.md framing of `function()` resolution). These are captured separately if desired but are not test-affecting.

## Dependencies
- None. `add-udf-function-support` is complete and merged.
