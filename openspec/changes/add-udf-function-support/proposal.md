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
