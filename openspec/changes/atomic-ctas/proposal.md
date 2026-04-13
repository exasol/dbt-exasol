## Why

The `exasol__create_table_as` macro emits two separate SQL statements—`CREATE OR REPLACE TABLE ... WITH NO DATA` followed by `INSERT INTO ...`—connected via the `|SEPARATEMEPLEASE|` splitter. If the dbt process dies between these statements (signal, network drop, OOM), the first statement has already auto-committed, leaving the target table permanently empty. Downstream models silently produce zero-row results, and only row-count or freshness tests can catch the corruption. This is tracked in [GitHub Issue #195](https://github.com/exasol/dbt-exasol/issues/195).

## What Changes

- Replace the two-step `CREATE ... WITH NO DATA` + `INSERT` pattern in `exasol__create_table_as` with a single atomic `CREATE OR REPLACE TABLE ... AS <sql>` statement
- Keep `DISTRIBUTE BY` and `PARTITION BY` as `ALTER TABLE` statements after the atomic CTAS (Exasol does **not** support these clauses inline with `CREATE TABLE ... AS <subquery>` — verified on Exasol 8.29.13)
- For the contract-enforced path, implement a new `exasol__get_select_subquery(sql)` adapter macro override that emits `CAST()` expressions for each column to enforce contract-defined types (the dbt-core default does NOT cast — it only selects by name, which would produce wrong types with CTAS). Then apply `NOT NULL` and `PRIMARY KEY` constraints via `ALTER TABLE` *after* the atomic CTAS — these are additive operations that don't risk data loss
- Note: Exasol does **not** support `CHECK` or `UNIQUE` constraints at all (neither inline in `CREATE TABLE` nor via `ALTER TABLE`) — verified on Exasol 8.29.13. These constraint types are silently ignored by dbt and require no handling
- Update the `exasol__get_replace_table_sql` macro (which delegates to `exasol__create_table_as`) to benefit from the atomic fix
- Update contract enforcement test fixtures to reflect the new SQL pattern
- **BREAKING**: The contract-enforcement path changes from `CREATE TABLE (col_defs) ; INSERT INTO ...` to `CREATE TABLE AS <sql> ; ALTER TABLE ADD CONSTRAINT ...` — any users relying on the exact emitted SQL will see a difference
- Note: `FOREIGN KEY` constraints require a referenced table to exist and are not commonly used; they remain supported via `ALTER TABLE ADD CONSTRAINT ... FOREIGN KEY` if configured

## Capabilities

### New Capabilities
- `atomic-ctas`: Guarantees that `create_table_as` is atomic — a table is either populated with data or the previous version is preserved unchanged

### Modified Capabilities
- `relation-management`: The `exasol__get_replace_table_sql` macro (which currently delegates to the non-atomic `exasol__create_table_as`) will now produce a single atomic `CREATE OR REPLACE TABLE ... AS` statement, changing the replace-table SQL generation behavior

## Impact

- **Macros**: `dbt/include/exasol/macros/adapters.sql` (`exasol__create_table_as`, new `exasol__get_select_subquery`), `dbt/include/exasol/macros/create_table_helpers.sql` (`add_constraints`, `partition_by_conf`, `distribute_by_conf`)
- **Materializations**: `table.sql`, `incremental.sql`, `snapshot.sql` — all call `create_table_as`; the fix applies transparently
- **Contract tests**: `tests/functional/adapter/constraints/fixtures.py` — `exasol_expected_sql` must be updated
- **Multi-node clusters**: `DISTRIBUTE BY` and `PARTITION BY` remain as `ALTER TABLE` statements (same as current behavior) — Exasol does not support these clauses inline with CTAS. The ALTER now runs after data is loaded (instead of after an empty table CREATE), which triggers reshuffling on multi-node clusters. **Preventing silent data corruption is the priority; any performance tuning (e.g., distribute-before-insert on multi-node clusters) is secondary and can be revisited separately.**
- **No API/dependency changes**: This is purely a SQL-generation change within the adapter
