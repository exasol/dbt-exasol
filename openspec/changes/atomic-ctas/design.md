## Context

The `exasol__create_table_as` macro currently emits two SQL statements connected by the `|SEPARATEMEPLEASE|` splitter in `connections.py`:

1. `CREATE OR REPLACE TABLE t AS <sql> WITH NO DATA` — auto-commits, leaving an empty table
2. `ALTER TABLE t ...` (constraints if any) + `INSERT INTO t <sql>` — populates the table

If the process crashes between steps 1 and 2, the table is permanently empty. This is tracked in [Issue #195](https://github.com/exasol/dbt-exasol/issues/195).

**Exasol grammar constraints** (verified on Exasol 8.29.13):
- The `CREATE TABLE` statement has two mutually exclusive paths — column definitions OR `AS subquery`. You cannot combine `CREATE TABLE t (col_defs) AS <subquery>` in Exasol (unlike standard SQL / PostgreSQL).
- `DISTRIBUTE BY` and `PARTITION BY` are **NOT** supported inline with `CREATE TABLE ... AS <subquery>`. They cause `syntax error, unexpected DISTRIBUTE_BY_`. They **must** be applied via `ALTER TABLE` after creation.
- `CHECK` constraints are **not supported at all** in Exasol 8.29 — neither inline in `CREATE TABLE` nor via `ALTER TABLE` (`Feature not supported: constraint check definition`).
- `UNIQUE` constraints are **not supported at all** in Exasol 8.29 — neither inline nor via `ALTER TABLE` (`Feature not supported: UNIQUE column constraint`).
- `NOT NULL` and `PRIMARY KEY` constraints work via `ALTER TABLE` after CTAS.
- `CREATE TABLE ... AS SELECT CAST(x AS TYPE)` correctly preserves the CAST target type. Without CAST, Exasol infers minimal types (e.g., `SELECT 1` becomes `DECIMAL(1,0)`, not `DECIMAL(18,0)`).

**Current callers of `create_table_as`**: `table.sql` (line 18), `incremental.sql` (lines 19, 25, 32), `snapshot.sql` (lines 261, 301), `replace.sql` (line 2).

**No temporary table support**: Exasol has no `CREATE TEMPORARY TABLE` syntax. The `temporary=True` parameter is ignored — temp relations are just regular tables with `__dbt_tmp` suffix.

## Goals / Non-Goals

**Goals:**
- Make `exasol__create_table_as` atomic: a table either contains the new data or the previous version is preserved unchanged
- Keep `DISTRIBUTE BY` / `PARTITION BY` as `ALTER TABLE` statements after CTAS (Exasol does not support them inline with `CREATE TABLE ... AS`)
- Handle contract enforcement by implementing a new `exasol__get_select_subquery` adapter macro override that emits `CAST()` expressions for each column to enforce contract-defined types, then apply `NOT NULL` and `PRIMARY KEY` constraints via `ALTER TABLE` after the atomic CTAS — these are additive operations that cannot cause data loss
- Maintain backward compatibility for all 6 call sites of `create_table_as`

**Non-Goals:**
- Adding a config option to preserve the old non-atomic behavior (data safety should not be optional)
- Changing the `table.sql` materialization to use the intermediate+rename pattern (the `CREATE OR REPLACE` approach is fine once CTAS is atomic)
- Addressing the `|SEPARATEMEPLEASE|` mechanism itself (it's still needed for constraint ALTER statements)
- Optimizing multi-node cluster performance — `DISTRIBUTE BY` / `PARTITION BY` must remain as `ALTER TABLE` (Exasol grammar limitation). Preventing silent data corruption is the priority; any performance tuning (e.g., distribute-before-insert on multi-node clusters) is secondary and can be revisited separately
- Handling `CHECK` or `UNIQUE` constraints — Exasol 8.29 does not support them at all

## Decisions

### Decision 1: Single atomic CTAS for non-contract path

**Choice**: `CREATE OR REPLACE TABLE t AS <sql>` followed by `ALTER TABLE t DISTRIBUTE BY ...` and `ALTER TABLE t PARTITION BY ...` (if configured) via `|SEPARATEMEPLEASE|`

**Rationale**: The CTAS is a single SQL statement. If the SELECT fails, Exasol preserves the existing table unchanged (verified on Exasol 8.29.13). `DISTRIBUTE BY` and `PARTITION BY` **cannot** be inline with `CREATE TABLE ... AS` — Exasol returns `syntax error, unexpected DISTRIBUTE_BY_`. They must remain as separate `ALTER TABLE` statements.

**Alternative considered**: Inline `DISTRIBUTE BY` / `PARTITION BY` in the CTAS statement — this is NOT supported by Exasol grammar on the AS-subquery path (verified).

### Decision 2: Atomic CTAS + ALTER CONSTRAINT for contract-enforced path

**Choice**: `CREATE OR REPLACE TABLE t AS <get_select_subquery(sql)>` followed by `ALTER TABLE t DISTRIBUTE BY ...`, `ALTER TABLE t PARTITION BY ...`, `ALTER TABLE t MODIFY COLUMN ... NOT NULL`, and `ALTER TABLE t ADD CONSTRAINT ... PRIMARY KEY (...)`

**Rationale**: Exasol cannot combine column definitions with `AS subquery` in a single `CREATE TABLE`. Since we can't define constraints inline, we apply them after the table is populated. This is safe because:
- The CTAS is atomic — data is guaranteed to be present
- `ALTER TABLE ADD CONSTRAINT` is additive — it doesn't remove data
- If a constraint ALTER fails, the table still has its data (just missing a constraint)

**Critical — type enforcement requires a new adapter macro**: The dbt-core `default__get_select_subquery` does **NOT** emit `CAST()` expressions. It only selects columns by name:
```sql
-- dbt-core default__get_select_subquery output (NO type casting):
select id, color, date_day from (<user_sql>) as model_subq
```
In the current code, type enforcement works because `CREATE TABLE (id DECIMAL(18,0), ...)` defines the types, and `INSERT INTO` implicitly casts. With CTAS, there are no column definitions, so types come from the SELECT. Without CAST, `SELECT 1` produces `DECIMAL(1,0)` not `DECIMAL(18,0)` (verified on Exasol 8.29.13).

**Solution**: Implement `exasol__get_select_subquery(sql)` in `adapters.sql` that wraps each contract column in `CAST(col AS <contract_type>)`:
```sql
-- new exasol__get_select_subquery output:
select CAST(id AS DECIMAL(18,0)) AS id, CAST(color AS CHAR(50)) AS color, CAST(date_day AS CHAR(50)) AS date_day
from (<user_sql>) as model_subq
```
The column names and types are available from `model['columns']` (same source used by `get_table_columns_and_constraints`).

**Constraint support** (verified on Exasol 8.29.13):
- `NOT NULL` — supported via `ALTER TABLE MODIFY COLUMN col NOT NULL` ✓
- `PRIMARY KEY` — supported via `ALTER TABLE ADD CONSTRAINT pk PRIMARY KEY (col)` ✓
- `FOREIGN KEY` — supported via `ALTER TABLE ADD CONSTRAINT fk FOREIGN KEY (col) REFERENCES ...` ✓
- `CHECK` — **NOT supported** in Exasol 8.29 at all (neither inline nor ALTER) — silently ignored by dbt
- `UNIQUE` — **NOT supported** in Exasol 8.29 at all (neither inline nor ALTER) — silently ignored by dbt

**Alternative considered**: Use the intermediate+rename pattern (create with col_defs, insert data, rename swap). This would preserve constraints inline but adds complexity and still has a non-atomic insert step.

### Decision 3: Primary key via ALTER TABLE (not inline)

**Choice**: Apply `PRIMARY KEY` via `ALTER TABLE t ADD CONSTRAINT ... PRIMARY KEY (...)` after CTAS

**Rationale**: The current `add_constraints` macro already applies primary keys via `ALTER TABLE` with `|SEPARATEMEPLEASE|`. The only change is that this now happens after data is loaded (instead of after an empty CREATE). This is actually safer — the PK constraint is validated against real data.

### Decision 4: `add_constraints` macro restructuring

**Choice**: The `add_constraints` macro continues to emit all post-creation `ALTER TABLE` statements (DISTRIBUTE BY, PARTITION BY, PRIMARY KEY) connected via `|SEPARATEMEPLEASE|`. No inline clauses are needed since Exasol does not support DISTRIBUTE/PARTITION inline with CTAS.

**Rationale**: All three clause types (DISTRIBUTE BY, PARTITION BY, PRIMARY KEY) must be `ALTER TABLE` statements. The `|SEPARATEMEPLEASE|` splitter is still needed for all of them, but they are now safe because the atomic CTAS guarantees data is present.

**What changes**: The `add_constraints` macro is called AFTER the CTAS instead of between an empty CREATE and an INSERT. The macro itself needs minimal changes — it already emits the correct `ALTER TABLE` pattern.

## Risks / Trade-offs

**[Risk] Distribution reshuffling on multi-node clusters** → `ALTER TABLE t DISTRIBUTE BY ...` after CTAS (with data) will trigger data reshuffling across cluster nodes. This applies to ALL paths (not just contract-enforced), because Exasol does not support inline `DISTRIBUTE BY` with CTAS. This is a one-time cost per model run but can be slow for large tables. **Mitigation**: Accepted. Preventing silent data corruption is the priority; any performance tuning (e.g., distribute-before-insert on multi-node clusters) is secondary and can be revisited separately. The reshuffling cost is real but acceptable for correctness.

**[Risk] Contract test fixture changes** → The `exasol_expected_sql` in `tests/functional/adapter/constraints/fixtures.py` hardcodes the current two-step SQL pattern. **Mitigation**: Update the fixture to match the new pattern. This is a test-only change, not a user-facing breaking change.

**[Risk] NOT NULL constraint enforcement timing** → With the new approach, `NOT NULL` constraints are applied via `ALTER TABLE ... MODIFY COLUMN ... NOT NULL` after data is loaded. If the data contains NULLs, the ALTER will fail. **Mitigation**: This is actually correct behavior — the current pattern applies NOT NULL on the empty table (no validation), then inserts data that might contain NULLs. The new pattern properly validates the constraint.

**[Risk] Users depending on exact emitted SQL** → Any monitoring/auditing tools that parse dbt-exasol's generated SQL will see a different pattern. **Mitigation**: This is a bugfix, not a feature change. The new pattern is strictly safer.
