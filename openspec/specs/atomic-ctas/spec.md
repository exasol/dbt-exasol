# atomic-ctas Specification

## Requirements

### Requirement: Atomic CTAS for non-contract path
The `exasol__create_table_as` macro SHALL emit a single atomic `CREATE OR REPLACE TABLE ... AS <sql>` statement when contract enforcement is not active. If the SELECT fails, the existing table SHALL be preserved unchanged.

#### Scenario: Simple table creation is atomic
- **WHEN** `exasol__create_table_as(False, relation, sql)` is called without contract enforcement
- **THEN** the macro SHALL emit exactly one `CREATE OR REPLACE TABLE <schema>.<identifier> AS <sql>` statement
- **AND** no `WITH NO DATA` clause SHALL be present
- **AND** no `INSERT INTO` statement SHALL follow

#### Scenario: Table creation with temporary relation
- **WHEN** `exasol__create_table_as(True, tmp_relation, sql)` is called
- **THEN** the macro SHALL emit the same atomic CTAS pattern as for non-temporary relations
- **AND** no `WITH NO DATA` + `INSERT` pattern SHALL be used

### Requirement: DISTRIBUTE BY and PARTITION BY via ALTER TABLE after CTAS
Exasol does **not** support `DISTRIBUTE BY` or `PARTITION BY` clauses inline with `CREATE TABLE ... AS <subquery>` (verified: syntax error on Exasol 8.29.13). These clauses SHALL be applied via `ALTER TABLE` statements after the atomic CTAS, connected via `|SEPARATEMEPLEASE|`.

#### Scenario: Table with distribution configuration
- **WHEN** `exasol__create_table_as` is called with `distribute_by_config = ['a', 'b']`
- **THEN** the macro SHALL emit: `CREATE OR REPLACE TABLE <relation> AS <sql>` followed by `|SEPARATEMEPLEASE|` and `ALTER TABLE <relation> DISTRIBUTE BY a, b`
- **AND** `DISTRIBUTE BY` SHALL NOT appear inline in the `CREATE TABLE` statement

#### Scenario: Table with partitioning configuration
- **WHEN** `exasol__create_table_as` is called with `partition_by_config = ['order_date']`
- **THEN** the macro SHALL emit: `CREATE OR REPLACE TABLE <relation> AS <sql>` followed by `|SEPARATEMEPLEASE|` and `ALTER TABLE <relation> PARTITION BY order_date`
- **AND** `PARTITION BY` SHALL NOT appear inline in the `CREATE TABLE` statement

#### Scenario: Table with both distribution and partitioning
- **WHEN** `exasol__create_table_as` is called with both `distribute_by_config` and `partition_by_config`
- **THEN** the macro SHALL emit separate `ALTER TABLE` statements for each, connected via `|SEPARATEMEPLEASE|`

### Requirement: Contract-enforced path uses atomic CTAS with CAST for type safety
When `contract.enforced = true`, the `exasol__create_table_as` macro SHALL first create the table atomically with data via `CREATE OR REPLACE TABLE ... AS <get_select_subquery(sql)>`, then apply constraints via `ALTER TABLE` statements connected by `|SEPARATEMEPLEASE|`.

**Critical — type enforcement requires a new adapter macro**: The dbt-core `default__get_select_subquery` does **NOT** emit `CAST()` expressions — it only selects columns by name (`select id, color from (...) as model_subq`). In the current code, type enforcement works because `CREATE TABLE (id DECIMAL(18,0), ...)` defines the types and `INSERT INTO` implicitly casts. With CTAS, there are no column definitions, so types come from the SELECT. Without CAST, `SELECT 1` becomes `DECIMAL(1,0)` not `DECIMAL(18,0)` (verified on Exasol 8.29.13). A new `exasol__get_select_subquery(sql)` adapter macro override MUST be implemented that wraps each contract column in `CAST(col AS <contract_type>)`.

Supported constraints (verified on Exasol 8.29.13):
- `NOT NULL` — via `ALTER TABLE MODIFY COLUMN <col> NOT NULL` ✓
- `PRIMARY KEY` — via `ALTER TABLE ADD CONSTRAINT ... PRIMARY KEY (...)` ✓
- `FOREIGN KEY` — via `ALTER TABLE ADD CONSTRAINT ... FOREIGN KEY (...) REFERENCES ...` ✓
- `CHECK` — **NOT supported** in Exasol 8.29 at all — silently ignored by dbt
- `UNIQUE` — **NOT supported** in Exasol 8.29 at all — silently ignored by dbt

#### Scenario: Contract-enforced table creation
- **WHEN** `exasol__create_table_as` is called with `contract.enforced = true`
- **THEN** the macro SHALL first call `get_assert_columns_equivalent(sql)` to validate the user SQL columns match the contract schema (existing dbt-core validation — must be preserved)
- **AND** then emit: `CREATE OR REPLACE TABLE <relation> AS <get_select_subquery(sql)>`
- **AND** then emit `ALTER TABLE` statements for constraints via `|SEPARATEMEPLEASE|`
- **AND** the `WITH NO DATA` + `INSERT INTO` pattern SHALL NOT be used

#### Scenario: Contract-enforced CTAS preserves column types via CAST
- **WHEN** a contract defines `id DECIMAL(18,0)` and the user SQL is `SELECT 1 AS id`
- **THEN** the adapter-specific `exasol__get_select_subquery(sql)` SHALL wrap the column as `CAST(id AS DECIMAL(18,0)) AS id`
- **AND** the resulting table column SHALL have type `DECIMAL(18,0)`, NOT `DECIMAL(1,0)`
- **NOTE** the dbt-core `default__get_select_subquery` does NOT emit CAST — this adapter override is required because CTAS has no column definitions to enforce types

#### Scenario: All contract columns are CAST in select subquery
- **WHEN** a contract defines columns `id DECIMAL(18,0)`, `color CHAR(50)`, `date_day CHAR(50)`
- **THEN** `exasol__get_select_subquery(sql)` SHALL emit:
  ```sql
  select CAST(id AS DECIMAL(18,0)) AS id, CAST(color AS CHAR(50)) AS color, CAST(date_day AS CHAR(50)) AS date_day
  from (<user_sql>) as model_subq
  ```
- **AND** column names and types SHALL be read from `model['columns']` (same source used by `get_table_columns_and_constraints`)
- **AND** quoted column names SHALL be preserved (e.g., `CAST("from" AS CHAR(50)) AS "from"`)

#### Scenario: NOT NULL constraint applied after data load
- **WHEN** a contract-enforced model defines a column with `not_null` constraint
- **THEN** the `NOT NULL` constraint SHALL be applied via `ALTER TABLE <relation> MODIFY COLUMN <col> NOT NULL` after the atomic CTAS
- **AND** the constraint SHALL be validated against the loaded data (if data contains NULLs, the ALTER will fail — this is correct behavior)

#### Scenario: PRIMARY KEY constraint applied after data load
- **WHEN** `primary_key_config` is configured on a model
- **THEN** the primary key SHALL be applied via `ALTER TABLE <relation> ADD CONSTRAINT ... PRIMARY KEY (...)` after the atomic CTAS
- **AND** this statement SHALL be connected via `|SEPARATEMEPLEASE|`

#### Scenario: CHECK and UNIQUE constraints are not supported
- **WHEN** a contract defines `CHECK` or `UNIQUE` constraints
- **THEN** these constraints SHALL be silently ignored (not emitted in SQL)
- **AND** no error SHALL be raised
- **BECAUSE** Exasol 8.29 does not support these constraint types at all (`Feature not supported: constraint check definition` / `Feature not supported: UNIQUE column constraint`)

### Requirement: No data loss on process interruption
If the dbt process is interrupted at any point during `create_table_as` execution, the target relation SHALL either contain the new data or the previous version of the table SHALL be preserved unchanged.

#### Scenario: Interruption during CTAS
- **WHEN** the dbt process is interrupted during the `CREATE OR REPLACE TABLE ... AS <sql>` statement
- **THEN** Exasol's `CREATE OR REPLACE` semantics SHALL preserve the existing table unchanged (verified on Exasol 8.29.13: existing table preserved when SELECT fails)

#### Scenario: Interruption during post-creation ALTER
- **WHEN** the dbt process is interrupted after the atomic CTAS but before constraint ALTER statements complete
- **THEN** the table SHALL contain its data (possibly missing some constraints or distribution/partitioning)
- **AND** no empty-table state SHALL occur
- **NOTE** preventing silent data corruption is the priority; any performance tuning (e.g., distribute-before-insert on multi-node clusters) is secondary and can be revisited separately

### Requirement: Replace table macro uses atomic CTAS
The `exasol__get_replace_table_sql` macro SHALL delegate to the atomic `exasol__create_table_as` macro, producing a single atomic `CREATE OR REPLACE TABLE ... AS` statement.

#### Scenario: Replace table operation is atomic
- **WHEN** `exasol__get_replace_table_sql` is called with a relation and SQL
- **THEN** it SHALL call `exasol__create_table_as(False, relation, sql)`
- **AND** the resulting SQL SHALL be atomic (single CTAS statement, with ALTER TABLE follow-ups if distribution/partitioning/PK configured)
