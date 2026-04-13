## 0. Implement `exasol__get_select_subquery` adapter macro override

**Why this is needed**: The dbt-core `default__get_select_subquery` only selects columns by name (`select id, color from (...) as model_subq`) — it does NOT emit `CAST()`. In the current code, type enforcement works because `CREATE TABLE (id DECIMAL(18,0))` defines types and `INSERT INTO` implicitly casts. With CTAS, there are no column definitions, so without CAST, `SELECT 1` produces `DECIMAL(1,0)` not the contract-defined `DECIMAL(18,0)` (verified on Exasol 8.29.13).

- [ ] 0.1 Implement `exasol__get_select_subquery(sql)` macro in `dbt/include/exasol/macros/adapters.sql` that reads `model['columns']` and wraps each column in `CAST(<col_name> AS <data_type>) AS <col_name>`, respecting quoted column names. Expected output:
```sql
select CAST(id AS DECIMAL(18,0)) AS id, CAST(color AS CHAR(50)) AS color, CAST(date_day AS CHAR(50)) AS date_day
from (
    <user_sql>
) as model_subq
```
- [ ] 0.2 Add a unit test that verifies `exasol__get_select_subquery` emits CAST for each column with the correct contract type
- [ ] 0.3 Add a unit test that verifies quoted column names are handled correctly (e.g., `CAST("from" AS CHAR(50)) AS "from"`)

## 1. Rewrite `exasol__create_table_as` macro

- [ ] 1.1 Implement the non-contract path: emit `CREATE OR REPLACE TABLE <schema>.<identifier> AS <sql>` as a single atomic statement, followed by `ALTER TABLE ... DISTRIBUTE BY`, `ALTER TABLE ... PARTITION BY`, and `ALTER TABLE ... ADD CONSTRAINT ... PRIMARY KEY` via `|SEPARATEMEPLEASE|` (only when configured)
- [ ] 1.2 Implement the contract-enforced path: call `get_assert_columns_equivalent(sql)` first (preserves existing column validation), then emit `CREATE OR REPLACE TABLE <schema>.<identifier> AS <get_select_subquery(sql)>` (which now dispatches to `exasol__get_select_subquery` and emits `CAST()` expressions), followed by `ALTER TABLE ... MODIFY COLUMN <col> NOT NULL` for each not-null column, `ALTER TABLE ... ADD CONSTRAINT ... PRIMARY KEY (...)`, `ALTER TABLE ... DISTRIBUTE BY`, and `ALTER TABLE ... PARTITION BY` via `|SEPARATEMEPLEASE|`
- [ ] 1.3 Remove the call to `get_table_columns_and_constraints()` from the contract path — column definitions are no longer needed since CTAS derives the schema from the SELECT (with types enforced by CAST in `exasol__get_select_subquery`)
- [ ] 1.4 Remove all `WITH NO DATA` and `INSERT INTO` patterns from the macro
- [ ] 1.5 Remove the `temporary` parameter handling distinction (both paths use the same atomic CTAS)

Expected SQL output for each path:

**Non-contract, no configs:**
```sql
CREATE OR REPLACE TABLE s.t AS <sql>
```

**Non-contract, with distribute + partition + primary key:**
```sql
CREATE OR REPLACE TABLE s.t AS <sql>
|SEPARATEMEPLEASE|
ALTER TABLE s.t DISTRIBUTE BY a, b;
|SEPARATEMEPLEASE|
ALTER TABLE s.t PARTITION BY dt;
|SEPARATEMEPLEASE|
ALTER TABLE s.t ADD CONSTRAINT s_t__pk PRIMARY KEY (id);
```

**Contract-enforced, with NOT NULL + PK + distribute:**
(note: CAST expressions come from the new `exasol__get_select_subquery` override, not from dbt-core)
```sql
CREATE OR REPLACE TABLE s.t AS SELECT CAST(id AS DECIMAL(18,0)) AS id, CAST(color AS CHAR(50)) AS color FROM (<user_sql>) AS model_subq
|SEPARATEMEPLEASE|
ALTER TABLE s.t MODIFY COLUMN id NOT NULL;
|SEPARATEMEPLEASE|
ALTER TABLE s.t ADD CONSTRAINT s_t__pk PRIMARY KEY (id);
|SEPARATEMEPLEASE|
ALTER TABLE s.t DISTRIBUTE BY id;
```

## 2. Simplify `create_table_helpers.sql` macros

- [ ] 2.1 Verify `partition_by_conf` and `distribute_by_conf` macros still work correctly — they already return clause strings without semicolons, which is correct for `ALTER TABLE` usage
- [ ] 2.2 Verify `add_constraints` macro works correctly when called after CTAS (instead of between empty CREATE and INSERT) — the macro already emits `|SEPARATEMEPLEASE|` prefixed `ALTER TABLE` statements, which is the correct pattern
- [ ] 2.3 For the contract-enforced path, add NOT NULL constraint emission via `ALTER TABLE MODIFY COLUMN <col> NOT NULL` for each column that has a `not_null` constraint in the contract — these must be emitted as `|SEPARATEMEPLEASE|` separated statements

**Note on unsupported constraints**: Exasol 8.29 does NOT support `CHECK` or `UNIQUE` constraints at all (neither in `CREATE TABLE` column defs nor via `ALTER TABLE`). The current test fixtures reference CHECK constraints but Exasol rejects them with "Feature not supported". dbt silently ignores unsupported constraint types. No code changes needed for CHECK/UNIQUE.

## 3. Update contract test fixtures

- [ ] 3.1 Update `exasol_expected_sql` in `tests/functional/adapter/constraints/fixtures.py` to match the new atomic CTAS + ALTER CONSTRAINT pattern. The new expected SQL should be approximately:
```sql
create or replace table <model_identifier> as
    select cast(id as decimal(18,0)) as id, cast(color as char(50)) as color, cast(date_day as char(50)) as date_day from (
        select 'blue' as color, 1 as id, '2019-01-01' as date_day
    ) as model_subq
|separatemeplease|
    alter table <model_identifier> modify column id not null;
```
(Note: CAST expressions come from the new `exasol__get_select_subquery` override. Exact format may vary — verify by running the contract tests and inspecting the actual generated SQL)
- [ ] 3.2 Verify contract enforcement tests pass with the new SQL pattern
- [ ] 3.3 Verify that CHECK constraint in `exasol_constrained_model_schema_yml` fixture is silently ignored (not emitted in SQL) — this should already be the case

## 4. Run existing test suites

- [ ] 4.1 Run unit tests to verify no regressions
- [ ] 4.2 Run contract enforcement functional tests
- [ ] 4.3 Run table materialization functional tests
- [ ] 4.4 Run incremental materialization functional tests
- [ ] 4.5 Run snapshot materialization functional tests

## 5. Add atomicity verification test

- [ ] 5.1 Add a test that verifies `exasol__create_table_as` generates a single atomic CTAS statement (no `WITH NO DATA` + `INSERT` pattern) by checking the rendered SQL output
- [ ] 5.2 Add a test that verifies the contract-enforced path uses `CAST()` expressions in the CTAS to preserve column types (not minimal inferred types) — this depends on the `exasol__get_select_subquery` override from task 0
