## ADDED Requirements

### Requirement: Reserved-Word Argument Identifiers in Python Scripts
The system SHALL quote argument identifiers in generated `PYTHON3 SCALAR SCRIPT` and `PYTHON3 SET SCRIPT` signatures so that Exasol reserved words (e.g. `value`) are legal argument names. The quoting SHALL NOT be applied to the SQL `CREATE FUNCTION` path, where user-written bodies reference unquoted identifiers and quoting would break name resolution.

#### Scenario: Python aggregate argument named with a reserved word
- **GIVEN** a Python aggregate UDF with an argument named `value` (an Exasol reserved word)
- **WHEN** running `dbt build`
- **THEN** the generated `CREATE OR REPLACE PYTHON3 SET SCRIPT` signature quotes the identifier as `"value" DOUBLE`
- **AND** the script is created without a syntax error
- **AND** the `def run(ctx)` bridge accesses it via `ctx.value` and the aggregate returns the expected result

#### Scenario: Python scalar argument named with a reserved word
- **GIVEN** a Python scalar UDF with an argument named with a reserved word
- **WHEN** running `dbt build`
- **THEN** the generated `CREATE OR REPLACE PYTHON3 SCALAR SCRIPT` signature quotes the identifier
- **AND** invoking the function returns the expected result

#### Scenario: SQL function arguments remain unquoted
- **GIVEN** a SQL scalar UDF whose body references its arguments by unquoted name
- **WHEN** running `dbt build`
- **THEN** the generated `CREATE FUNCTION` signature does NOT quote argument identifiers
- **AND** the function body resolves its arguments successfully

### Requirement: Host Environment Prerequisite for Script-Language UDFs
Exasol script-language UDFs (Python, R, Java) run the `exaudfclient` subprocess inside an unprivileged user namespace created via `nschroot`. On hosts where the kernel restricts unprivileged user namespaces (Ubuntu 24.04+ default `kernel.apparmor_restrict_unprivileged_userns=1`), this subprocess is forced into a restricted AppArmor profile and dies on its first IPC receive, surfacing as `VM error: Internal error: VM crashed` at invocation time. The test/CI environment SHALL disable this restriction on the Docker host so script-language UDF tests can run. SQL UDFs are unaffected.

#### Scenario: CI runner disables the userns restriction before integration tests
- **GIVEN** a GitHub Actions `ubuntu-latest` (Ubuntu 24.04+) runner
- **WHEN** the integration job runs, before the Exasol container is started
- **THEN** the workflow sets `kernel.apparmor_restrict_unprivileged_userns=0` (guarded so it is a no-op where the sysctl is absent)
- **AND** Python/aggregate UDF invocation tests pass without `VM crashed` errors

#### Scenario: Local/self-hosted host configured once
- **GIVEN** an Ubuntu 24.04+ Docker host used for `mise run test:integration`
- **WHEN** `kernel.apparmor_restrict_unprivileged_userns` is set to `0` (persisted under `/etc/sysctl.d/`)
- **THEN** script-language UDF invocations succeed against the Exasol `docker-db` container

## MODIFIED Requirements

### Requirement: SQL UDF Volatility Warning
The system SHALL emit a warning when `volatility` is configured on ANY UDF type (SQL scalar, Python scalar, or Python aggregate), since Exasol does not support volatility on any function type.

#### Scenario: SQL volatility warning
- **GIVEN** a SQL scalar UDF with `config: volatility: deterministic`
- **WHEN** running `dbt build`
- **THEN** a warning is logged via `unsupported_volatility_warning` indicating Exasol ignores volatility
- **AND** the function is created successfully without volatility keywords

#### Scenario: Python scalar volatility warning
- **GIVEN** a Python scalar UDF with `config: volatility: stable`
- **WHEN** running `dbt build`
- **THEN** the same warning is logged
- **AND** the script is created successfully without volatility keywords

#### Scenario: Python aggregate volatility warning
- **GIVEN** a Python aggregate UDF with `config: volatility: volatile`
- **WHEN** running `dbt build`
- **THEN** the same warning is logged
- **AND** the SET script is created successfully without volatility keywords

### Requirement: Python Scalar UDF Support via CREATE SCRIPT
The system SHALL support creating Python scalar UDFs using Exasol's `CREATE PYTHON3 SCALAR SCRIPT` mechanism with a bridge wrapper. The generated script body SHALL have valid, consistent Python indentation regardless of the macro's source-file indentation.

#### Scenario: Python UDF with bridge
- **GIVEN** a Python UDF in `functions/my_func.py` with entry point function `main(price)`
- **AND** YAML with `language: python`, `entry_point: main`
- **WHEN** running `dbt build`
- **THEN** the adapter generates `CREATE OR REPLACE PYTHON3 SCALAR SCRIPT schema.my_func(price DOUBLE) RETURNS DOUBLE AS <user_code> def run(ctx): return main(ctx.price)`
- **AND** the script is created in Exasol's `EXA_ALL_SCRIPTS` system table
- **AND** invoking the function returns the expected result without VM errors

#### Scenario: Generated script has no leading indentation
- **GIVEN** any Python scalar UDF
- **WHEN** the DDL is generated
- **THEN** the `AS` payload (user code + `def run(ctx)` bridge) contains no leading whitespace on lines that introduce a Python block
- **AND** user-supplied `compiled_code` indentation is preserved exactly as written

#### Scenario: Multi-argument Python bridge
- **GIVEN** a Python UDF with multiple arguments `(a, b, c)`
- **WHEN** building the function
- **THEN** the bridge generates `def run(ctx): return entry_point(ctx.a, ctx.b, ctx.c)`

#### Scenario: Runtime version warning
- **GIVEN** a Python UDF with `runtime_version: "3.12"` configured
- **WHEN** building the function
- **THEN** a warning is emitted (Exasol uses `PYTHON3` keyword with no version selection)
- **AND** the function is created successfully

### Requirement: Python Aggregate UDF Support via CREATE SET SCRIPT
The system SHALL support creating Python aggregate UDFs using Exasol's `CREATE PYTHON3 SET SCRIPT` mechanism. The generated script body SHALL have valid, consistent Python indentation.

#### Scenario: Python aggregate UDF with iteration bridge
- **GIVEN** a Python class with `__init__`, `accumulate`, and `finish` methods
- **AND** YAML with `type: aggregate`, `language: python`, `entry_point: SumSquared`
- **WHEN** running `dbt build`
- **THEN** the adapter generates `CREATE OR REPLACE PYTHON3 SET SCRIPT` with bridge that instantiates `SumSquared()`, calls `accumulate(ctx.value)` in a `ctx.next()` loop, and returns `finish()`
- **AND** the script body contains no leading whitespace and invokes correctly

#### Scenario: Aggregate execution with GROUP BY
- **GIVEN** a created Python aggregate UDF
- **WHEN** executing `SELECT schema.agg_udf(value) FROM table GROUP BY category`
- **THEN** the aggregation executes correctly using the iteration bridge

#### Scenario: aggregate_state warning
- **GIVEN** a Python aggregate UDF with `config: aggregate_state: {...}`
- **WHEN** running `dbt build`
- **THEN** a warning is logged stating Exasol handles distribution transparently and `aggregate_state`/`merge()` are unused
- **AND** the SET script is created successfully

#### Scenario: merge method unused
- **GIVEN** a Python UDAF class with a `merge` method
- **WHEN** executing the aggregate
- **THEN** `merge()` is not called (Exasol handles distribution transparently)
- **AND** aggregation still produces correct results

### Requirement: Procedural Body Detection Uses Word Boundary
The system SHALL detect Exasol procedural bodies (vs. expression bodies) using a word-boundary match on the `BEGIN` keyword, not a naive substring match.

#### Scenario: Expression containing the substring BEGIN is wrapped
- **GIVEN** a SQL scalar UDF body `date_diff('day', BEGIN_DATE, END_DATE)`
- **WHEN** running `dbt build`
- **THEN** the body is treated as an expression and wrapped as `BEGIN RETURN date_diff(...); END name;`
- **AND** the function compiles successfully in Exasol

#### Scenario: Body with standalone BEGIN keyword treated as procedural
- **GIVEN** a SQL scalar UDF body starting with `BEGIN ... END;`
- **WHEN** running `dbt build`
- **THEN** the body is inserted directly after `IS` without additional wrapping
