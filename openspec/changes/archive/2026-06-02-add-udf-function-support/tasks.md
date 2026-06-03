## 1. Create Scalar Function Macros

> **Note**: Implementation followed **Option A** (per Review Finding C1 in `proposal.md`): only the four top-level dispatch entry points are overridden. Sub-macros (1.1.2, 1.1.4, 1.1.5) were intentionally NOT implemented because once the top-level `exasol__scalar_function_sql` fires, `default__scalar_function_sql` is never invoked, making sub-overrides unreachable dead code.

- [x] 1.1 Create `dbt/include/exasol/macros/materializations/functions/scalar.sql`:
  - [x] 1.1.1 Implement `exasol__scalar_function_sql(target_relation)` -- compose signature + body inline (Option A: complete DDL in one macro)
  - [N/A] 1.1.2 ~~Implement `exasol__scalar_function_create_replace_signature_sql`~~ — N/A (Option A: top-level override only)
  - [x] 1.1.3 Procedural body detection (now inlined in 1.1.1) -- auto-detect expression vs procedural via `BEGIN` keyword; strip leading `SELECT`
  - [N/A] 1.1.4 ~~Implement `exasol__formatted_scalar_function_args_sql`~~ — N/A (per Review Finding C2: default already generates correct output; data-type mapping belongs in test YAML fixtures)
  - [N/A] 1.1.5 ~~Implement `exasol__scalar_function_volatility_sql`~~ — N/A (Option A: volatility warning inlined in 1.1.1)
  - [x] 1.1.6 Implement `exasol__scalar_function_python(target_relation)` -- `CREATE OR REPLACE PYTHON3 SCALAR SCRIPT` with bridge: iterate `model.arguments` to generate `def run(ctx): return <entry_point>(ctx.arg1, ctx.arg2, ...)`

## 2. Create Aggregate Function Macros
- [x] 2.1 Create `dbt/include/exasol/macros/materializations/functions/aggregate.sql`:
  - [x] 2.1.1 Implement `exasol__aggregate_function_sql(target_relation)` -- raise compilation error: "SQL aggregate UDFs are not supported in Exasol. Use Python with type: aggregate and language: python."
  - [x] 2.1.2 Implement `exasol__aggregate_function_python(target_relation)` -- `CREATE OR REPLACE PYTHON3 SET SCRIPT` with iteration bridge: instantiate class from `model.config.get('entry_point')`, loop `ctx.next()` calling `accumulate(ctx.arg)`, return `finish()`

## 3. Create Helper Macros
- [x] 3.1 Create `dbt/include/exasol/macros/materializations/functions/helpers.sql`:
  - [x] 3.1.1 Implement `exasol__function_execute_build_sql(build_sql, existing_relation, target_relation)`:
    - Use `model.get('language')` to detect language (NOT `target_relation.language` which doesn't exist)
    - If `language == 'sql'`: execute `DROP SCRIPT IF EXISTS {{ target_relation.render() }}`
    - If `language != 'sql'`: execute `DROP FUNCTION IF EXISTS {{ target_relation.render() }}`
    - Then delegate to `default__function_execute_build_sql` for grants, persist_docs, commit

## 4. Create UDF Tests
- [x] 4.1 Create `tests/functional/adapter/functions/test_udfs.py`:
  - [x] 4.1.1 `TestExasolUDFsBasic(UDFsBasic)` -- override `functions` fixture: use Exasol-compatible SQL body (strip `SELECT`), override data types (`float` -> `DOUBLE`)
  - [x] 4.1.2 `TestExasolDeterministicUDF(DeterministicUDF)` -- override `check_function_volatility()` to assert `IMMUTABLE` NOT in sql (Exasol ignores volatility)
  - [x] 4.1.3 `TestExasolStableUDF(StableUDF)` -- override `check_function_volatility()` to assert `STABLE` NOT in sql
  - [x] 4.1.4 `TestExasolNonDeterministicUDF(NonDeterministicUDF)` -- override `check_function_volatility()` to assert `VOLATILE` NOT in sql
  - [x] 4.1.5 `TestExasolErrorForUnsupportedType(ErrorForUnsupportedType)` -- inherit directly, no override needed
  - [x] 4.1.6 `TestExasolPythonUDF(PythonUDFSupported)` -- override `functions` fixture for Exasol types, override `is_function_create_event()` to check `"CREATE OR REPLACE PYTHON3 SCALAR SCRIPT"` instead of `"CREATE OR REPLACE FUNCTION"`
  - [x] 4.1.7 `TestExasolPythonUDFRuntimeVersionRequired(PythonUDFRuntimeVersionRequired)` -- inherit directly (validation is dbt-core level)
  - [x] 4.1.8 `TestExasolPythonUDFEntryPointRequired(PythonUDFEntryPointRequired)` -- inherit directly
  - [x] 4.1.9 `TestExasolSqlUDFDefaultArg(SqlUDFDefaultArgSupport)` -- set `expect_default_arg_support = False`
  - [x] 4.1.10 `TestExasolPythonUDFDefaultArg(PythonUDFDefaultArgSupport)` -- set `expect_default_arg_support = False`
  - [x] 4.1.11 `TestExasolPythonUDFVolatility(PythonUDFVolatilitySupport)` -- override `check_function_volatility()` to assert `VOLATILE` NOT in sql, override `is_function_create_event()` for SCRIPT check

## 5. Create UDAF Tests
- [x] 5.1 Create `tests/functional/adapter/functions/test_udafs.py`:
  - [x] 5.1.1 `TestExasolAggregateSQLError(BasicSQLUDAF)` -- override `test_udaf()` to expect build failure with "not supported" message
  - [x] 5.1.2 `TestExasolAggregatePython(BasicPythonUDAF)` -- override `functions` fixture for Exasol types, override `is_function_create_event()` to check `"CREATE OR REPLACE PYTHON3 SET SCRIPT"` instead of `"CREATE OR REPLACE AGGREGATE FUNCTION"`
  - [x] 5.1.3 `TestExasolAggregatePythonDefaultArg(PythonUDAFDefaultArgSupport)` -- set `expect_default_arg_support = False`, override `is_function_create_event()` for SCRIPT check

## 6. Integration Testing
- [x] 6.1 Run UDF tests: `pytest tests/functional/adapter/functions/ -v`
- [x] 6.2 Run full test suite: `uv run nox -s test:integration`
- [x] 6.3 Run lint/format checks: `uv run nox -s format:check lint:code`

## 7. Documentation
- [x] 7.1 Update README.md with UDF support section
- [x] 7.2 Document Exasol-specific limitations: no SQL aggregates, no volatility, no default args, no PACKAGES clause, PYTHON3 only

## 8. Validation
- [x] 8.1 Run `openspec validate add-udf-function-support --strict`
- [x] 8.2 Verify all checklist items complete
