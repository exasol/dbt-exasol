# Change: Update relation rename and replace behavior to align with dbt-adapters framework

## Why
The `ExasolRelation` class does not declare `renameable_relations` or `replaceable_relations`, leaving both as empty frozensets inherited from `BaseRelation`. This means `can_be_renamed` and `can_be_replaced` are always `False`, causing the `get_replace_sql` orchestration macro to always fall through to the least safe "drop and create" strategy. Exasol fully supports `RENAME TABLE/VIEW` and `CREATE OR REPLACE TABLE/VIEW`, so these capabilities should be registered. Additionally, the per-type macro hooks (`get_rename_table_sql`, `get_rename_view_sql`, `get_replace_table_sql`, `get_replace_view_sql`, `drop_table`, `drop_view`) that the dbt-adapters framework dispatches to are not implemented, which would cause `compiler_error` exceptions if the relation types were registered without the corresponding macros.

The Exasol-specific incremental and snapshot materializations also use the legacy `adapter.drop_relation()` and `adapter.rename_relation()` calls directly. These should be migrated to use `drop_relation_if_exists()` (for the snapshot post-cleanup) and the framework-consistent patterns, matching how the global default materializations handle relation lifecycle operations.

## What Changes
- Add `renameable_relations` field to `ExasolRelation` containing `{RelationType.View, RelationType.Table}`
- Add `replaceable_relations` field to `ExasolRelation` containing `{RelationType.View, RelationType.Table}`
- Add per-type rename macros: `exasol__get_rename_table_sql` and `exasol__get_rename_view_sql`
- Add per-type replace macros: `exasol__get_replace_table_sql` and `exasol__get_replace_view_sql`
- Add per-type drop macros: `exasol__drop_table` and `exasol__drop_view`
- Migrate Exasol incremental materialization to use `drop_relation_if_exists()` and the intermediate/backup/rename pattern from the global default incremental materialization
- Migrate Exasol snapshot `exasol__post_snapshot` to use `drop_relation_if_exists()` instead of `adapter.drop_relation()`
- Remove the legacy `exasol__rename_relation` and `exasol__drop_relation` macros from `adapters.sql`, since all callers will use the new framework dispatch path
- Add unit tests for the new `ExasolRelation` properties

## Impact
- Affected specs: relation-management (new capability)
- Affected code:
  - `dbt/adapters/exasol/relation.py` (add renameable/replaceable fields)
  - `dbt/include/exasol/macros/relations/table/rename.sql` (new file)
  - `dbt/include/exasol/macros/relations/table/replace.sql` (new file)
  - `dbt/include/exasol/macros/relations/table/drop.sql` (new file)
  - `dbt/include/exasol/macros/relations/view/rename.sql` (new file)
  - `dbt/include/exasol/macros/relations/view/replace.sql` (new file)
  - `dbt/include/exasol/macros/relations/view/drop.sql` (new file)
  - `dbt/include/exasol/macros/adapters.sql` (remove legacy `exasol__rename_relation` and `exasol__drop_relation`)
  - `dbt/include/exasol/macros/materializations/incremental.sql` (migrate to framework patterns)
  - `dbt/include/exasol/macros/materializations/snapshot.sql` (migrate `exasol__post_snapshot`)
  - `tests/unit/test_relation_quoting.py` (add tests for new properties)
