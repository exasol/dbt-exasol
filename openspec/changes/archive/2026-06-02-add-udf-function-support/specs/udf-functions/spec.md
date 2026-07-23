## ADDED Requirements

### Requirement: SQL Scalar UDF Support via CREATE FUNCTION
The system SHALL support creating SQL scalar UDFs using Exasol's `CREATE FUNCTION` mechanism.

#### Scenario: Expression-based UDF
- **GIVEN** a UDF defined in `functions/my_udf.sql` containing `price * 2`
- **AND** a properties YAML with `arguments: [{name: price, data_type: DOUBLE}]` and `returns: {data_type: DOUBLE}`
- **WHEN** running `dbt build --select "resource_type:function"`
- **THEN** the adapter generates `CREATE OR REPLACE FUNCTION schema.my_udf(price DOUBLE) RETURN DOUBLE IS BEGIN RETURN price * 2; END my_udf;`
- **AND** the function is created in Exasol's `EXA_ALL_FUNCTIONS` system table

#### Scenario: SELECT keyword stripping
- **GIVEN** a UDF body containing `SELECT price * 2` (dbt convention)
- **WHEN** building the function
- **THEN** the adapter strips the leading `SELECT` and generates `RETURN price * 2;`

#### Scenario: Procedural body UDF
- **GIVEN** a UDF body containing `BEGIN`, variable declarations, and control flow
- **WHEN** building the function
- **THEN** the adapter detects the `BEGIN` keyword and inserts the body directly after `IS`
- **AND** generates valid Exasol procedural SQL

#### Scenario: Referencing UDF in models
- **GIVEN** a model containing `{{ function('my_udf') }}(column_name)`
- **WHEN** running `dbt compile`
- **THEN** the macro resolves to the fully qualified name `schema.my_udf` (no database prefix)

### Requirement: SQL UDF Volatility Warning
The system SHALL emit a warning when volatility is configured, as Exasol does not support it.

#### Scenario: Volatility warning emitted
- **GIVEN** a UDF with `config: volatility: deterministic`
- **WHEN** running `dbt build`
- **THEN** a warning is logged via `unsupported_volatility_warning` indicating Exasol ignores volatility
- **AND** the function is created successfully without volatility keywords

### Requirement: Python Scalar UDF Support via CREATE SCRIPT
The system SHALL support creating Python scalar UDFs using Exasol's `CREATE PYTHON3 SCALAR SCRIPT` mechanism with a bridge wrapper.

#### Scenario: Python UDF with bridge
- **GIVEN** a Python UDF in `functions/my_func.py` with entry point function `main(price)`
- **AND** YAML with `language: python`, `entry_point: main`
- **WHEN** running `dbt build`
- **THEN** the adapter generates `CREATE OR REPLACE PYTHON3 SCALAR SCRIPT schema.my_func(price DOUBLE) RETURNS DOUBLE AS <user_code> def run(ctx): return main(ctx.price)`
- **AND** the script is created in Exasol's `EXA_ALL_SCRIPTS` system table

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
The system SHALL support creating Python aggregate UDFs using Exasol's `CREATE PYTHON3 SET SCRIPT` mechanism.

#### Scenario: Python aggregate UDF with iteration bridge
- **GIVEN** a Python class with `__init__`, `accumulate`, and `finish` methods
- **AND** YAML with `type: aggregate`, `language: python`, `entry_point: SumSquared`
- **WHEN** running `dbt build`
- **THEN** the adapter generates `CREATE OR REPLACE PYTHON3 SET SCRIPT` with bridge that instantiates `SumSquared()`, calls `accumulate(ctx.value)` in a `ctx.next()` loop, and returns `finish()`

#### Scenario: Aggregate execution with GROUP BY
- **GIVEN** a created Python aggregate UDF
- **WHEN** executing `SELECT schema.agg_udf(value) FROM table GROUP BY category`
- **THEN** the aggregation executes correctly using the iteration bridge

#### Scenario: merge method unused
- **GIVEN** a Python UDAF class with a `merge` method
- **WHEN** executing the aggregate
- **THEN** `merge()` is not called (Exasol handles distribution transparently)
- **AND** aggregation still produces correct results

### Requirement: SQL Aggregate UDF Not Supported
The system SHALL raise a clear error when SQL aggregate UDFs are attempted.

#### Scenario: SQL aggregate error
- **GIVEN** a UDF with `config: type: aggregate` and SQL language
- **WHEN** running `dbt build`
- **THEN** a compilation error is raised with message directing user to use Python instead
- **AND** no function is created in the warehouse

### Requirement: Cross-Type Object Cleanup
The system SHALL clean up stale function/script objects when switching between SQL and Python implementations.

#### Scenario: SQL to Python transition
- **GIVEN** an existing SQL function `my_udf` in `EXA_ALL_FUNCTIONS`
- **WHEN** changing the UDF to Python and running `dbt build`
- **THEN** the adapter executes `DROP FUNCTION IF EXISTS schema.my_udf` before creating the SCRIPT
- **AND** only the Python SCRIPT remains in the warehouse

#### Scenario: Python to SQL transition
- **GIVEN** an existing Python script `my_udf` in `EXA_ALL_SCRIPTS`
- **WHEN** changing the UDF to SQL and running `dbt build`
- **THEN** the adapter executes `DROP SCRIPT IF EXISTS schema.my_udf` before creating the FUNCTION
- **AND** only the SQL FUNCTION remains in the warehouse

### Requirement: Default Argument Values Not Supported
The system SHALL not generate DEFAULT clauses for UDF arguments, as Exasol does not support them.

#### Scenario: Default arg ignored
- **GIVEN** a UDF argument with `default_value: 100` configured
- **WHEN** building the function
- **THEN** the generated SQL does NOT contain `DEFAULT 100`

### Requirement: UDF Test Coverage
The system SHALL provide comprehensive test coverage for all UDF functionality by subclassing dbt-tests-adapter base test classes.

#### Scenario: SQL scalar UDF tests pass
- **GIVEN** `TestExasolUDFsBasic` inheriting from `UDFsBasic`
- **WHEN** running the test
- **THEN** SQL scalar UDF creation and execution succeed

#### Scenario: Python scalar UDF tests pass with overridden event check
- **GIVEN** `TestExasolPythonUDF` inheriting from `PythonUDFSupported`
- **AND** `is_function_create_event()` overridden to check `"CREATE OR REPLACE PYTHON3 SCALAR SCRIPT"`
- **WHEN** running the test
- **THEN** Python scalar UDF creation and execution succeed

#### Scenario: Python aggregate UDF tests pass with overridden event check
- **GIVEN** `TestExasolAggregatePython` inheriting from `BasicPythonUDAF`
- **AND** `is_function_create_event()` overridden to check `"CREATE OR REPLACE PYTHON3 SET SCRIPT"`
- **WHEN** running the test
- **THEN** Python aggregate UDF creation and execution succeed

#### Scenario: Volatility test classes assert keyword absence
- **GIVEN** `TestExasolDeterministicUDF` inheriting from `DeterministicUDF`
- **AND** `check_function_volatility()` overridden to assert `IMMUTABLE` NOT in sql
- **WHEN** running the test
- **THEN** the test passes confirming Exasol omits volatility keywords
