## 1. Update ExasolRelation class
- [x] 1.1 Add `renameable_relations` field as `frozenset({RelationType.View, RelationType.Table})` to `ExasolRelation` in `dbt/adapters/exasol/relation.py`
- [x] 1.2 Add `replaceable_relations` field as `frozenset({RelationType.View, RelationType.Table})` to `ExasolRelation` in `dbt/adapters/exasol/relation.py`

## 2. Create per-type relation macros
- [x] 2.1 Create `dbt/include/exasol/macros/relations/table/rename.sql` with `exasol__get_rename_table_sql(relation, new_name)` macro
- [x] 2.2 Create `dbt/include/exasol/macros/relations/view/rename.sql` with `exasol__get_rename_view_sql(relation, new_name)` macro
- [x] 2.3 Create `dbt/include/exasol/macros/relations/table/replace.sql` with `exasol__get_replace_table_sql(relation, sql)` macro
- [x] 2.4 Create `dbt/include/exasol/macros/relations/view/replace.sql` with `exasol__get_replace_view_sql(relation, sql)` macro
- [x] 2.5 Create `dbt/include/exasol/macros/relations/table/drop.sql` with `exasol__drop_table(relation)` macro
- [x] 2.6 Create `dbt/include/exasol/macros/relations/view/drop.sql` with `exasol__drop_view(relation)` macro

## 3. Remove legacy macros from adapters.sql
- [x] 3.1 Remove `exasol__drop_relation` macro from `dbt/include/exasol/macros/adapters.sql`
- [x] 3.2 Remove `exasol__rename_relation` macro from `dbt/include/exasol/macros/adapters.sql`
- [x] 3.3 Update comment block at top of `adapters.sql` to remove references to removed macros

## 4. Migrate incremental materialization
- [x] 4.1 Refactor `dbt/include/exasol/macros/materializations/incremental.sql` full-refresh path to use intermediate/backup/rename pattern (matching global default incremental materialization)
- [x] 4.2 Add `drop_relation_if_exists()` calls for pre-existing intermediate and backup relations before the transaction
- [x] 4.3 Replace post-commit `adapter.drop_relation(rel)` loop with `drop_relation_if_exists()` calls

## 5. Migrate snapshot materialization
- [x] 5.1 Update `exasol__post_snapshot` in `dbt/include/exasol/macros/materializations/snapshot.sql` to use `drop_relation_if_exists()` instead of `adapter.drop_relation()`

## 6. Add unit tests
- [x] 6.1 Add unit tests for `can_be_renamed` property on table and view types in `tests/unit/test_relation_quoting.py`
- [x] 6.2 Add unit tests for `can_be_replaced` property on table and view types in `tests/unit/test_relation_quoting.py`

## 7. Validate
- [x] 7.1 Run `uv run nox -s format:fix` to ensure formatting compliance
- [x] 7.2 Run `uv run nox -s lint:code` to check for linting issues
- [x] 7.3 Run `uv run nox -s test:unit` to verify unit tests pass
