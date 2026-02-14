# relation-management Specification

## Purpose
TBD - created by archiving change update-relation-rename-replace. Update Purpose after archive.
## Requirements
### Requirement: Renameable Relations Declaration
The `ExasolRelation` class SHALL declare `renameable_relations` as a frozenset containing `RelationType.View` and `RelationType.Table`, enabling the `can_be_renamed` property to return `True` for tables and views.

#### Scenario: Table relation is renameable
- **WHEN** an `ExasolRelation` instance has `type=RelationType.Table`
- **THEN** `can_be_renamed` SHALL return `True`

#### Scenario: View relation is renameable
- **WHEN** an `ExasolRelation` instance has `type=RelationType.View`
- **THEN** `can_be_renamed` SHALL return `True`

### Requirement: Replaceable Relations Declaration
The `ExasolRelation` class SHALL declare `replaceable_relations` as a frozenset containing `RelationType.View` and `RelationType.Table`, enabling the `can_be_replaced` property to return `True` for tables and views.

#### Scenario: Table relation is replaceable
- **WHEN** an `ExasolRelation` instance has `type=RelationType.Table`
- **THEN** `can_be_replaced` SHALL return `True`

#### Scenario: View relation is replaceable
- **WHEN** an `ExasolRelation` instance has `type=RelationType.View`
- **THEN** `can_be_replaced` SHALL return `True`

### Requirement: Per-Type Rename Macros
The adapter SHALL implement `exasol__get_rename_table_sql` and `exasol__get_rename_view_sql` macros that generate Exasol-compatible `RENAME TABLE/VIEW` SQL. These macros are dispatched by the `get_rename_sql` framework macro when renaming relations during replace operations.

#### Scenario: Rename a table
- **WHEN** `get_rename_table_sql` is called with a table relation and a new name
- **THEN** the adapter SHALL generate SQL: `RENAME TABLE <schema>.<identifier> TO <new_name>`

#### Scenario: Rename a view
- **WHEN** `get_rename_view_sql` is called with a view relation and a new name
- **THEN** the adapter SHALL generate SQL: `RENAME VIEW <schema>.<identifier> TO <new_name>`

### Requirement: Per-Type Replace Macros
The adapter SHALL implement `exasol__get_replace_table_sql` and `exasol__get_replace_view_sql` macros that generate Exasol-compatible `CREATE OR REPLACE` SQL. These macros are dispatched by the `get_replace_sql` framework macro when atomically replacing relations.

#### Scenario: Replace a table
- **WHEN** `get_replace_table_sql` is called with a table relation and SQL
- **THEN** the adapter SHALL generate SQL using `CREATE OR REPLACE TABLE` with the provided query, consistent with the existing `exasol__create_table_as` pattern

#### Scenario: Replace a view
- **WHEN** `get_replace_view_sql` is called with a view relation and SQL
- **THEN** the adapter SHALL generate SQL using `CREATE OR REPLACE VIEW` with the provided query, consistent with the existing `exasol__create_view_as` pattern

### Requirement: Per-Type Drop Macros
The adapter SHALL implement `exasol__drop_table` and `exasol__drop_view` macros that generate Exasol-compatible `DROP` SQL. These macros are dispatched by the `get_drop_sql` framework macro.

#### Scenario: Drop a table
- **WHEN** `drop_table` is called with a table relation
- **THEN** the adapter SHALL generate SQL: `DROP TABLE IF EXISTS <schema>.<identifier>`

#### Scenario: Drop a view
- **WHEN** `drop_view` is called with a view relation
- **THEN** the adapter SHALL generate SQL: `DROP VIEW IF EXISTS <schema>.<identifier>`

### Requirement: Legacy Macro Removal
The legacy `exasol__rename_relation` and `exasol__drop_relation` macros in `adapters.sql` SHALL be removed. All callers (incremental materialization, snapshot materialization, and global materializations) SHALL use the new framework dispatch path instead.

#### Scenario: Legacy rename macro removed
- **WHEN** the adapter is loaded
- **THEN** there SHALL be no `exasol__rename_relation` macro in `adapters.sql`
- **AND** the `rename_relation` dispatch SHALL fall through to `default__rename_relation`, which calls `get_rename_sql`, which dispatches to `exasol__get_rename_table_sql` or `exasol__get_rename_view_sql`

#### Scenario: Legacy drop macro removed
- **WHEN** the adapter is loaded
- **THEN** there SHALL be no `exasol__drop_relation` macro in `adapters.sql`
- **AND** the `drop_relation` dispatch SHALL fall through to `default__drop_relation`, which calls `get_drop_sql`, which dispatches to `exasol__drop_table` or `exasol__drop_view`

### Requirement: Incremental Materialization Uses Framework Patterns
The Exasol incremental materialization SHALL use `drop_relation_if_exists()` for safe drops and `adapter.rename_relation()` for renames, aligning with the global default incremental materialization pattern. The full-refresh path SHALL use the intermediate/backup/rename swap pattern.

#### Scenario: Full refresh drops backup safely
- **WHEN** the incremental materialization runs in full-refresh mode
- **THEN** it SHALL use `drop_relation_if_exists()` to clean up pre-existing intermediate and backup relations before creating the new table

#### Scenario: Full refresh swaps via rename
- **WHEN** the incremental materialization runs in full-refresh mode and an existing table relation exists
- **THEN** it SHALL create an intermediate relation, rename the existing relation to a backup, rename the intermediate to the target, and drop the backup after commit

#### Scenario: Post-commit cleanup uses safe drop
- **WHEN** backup relations need to be dropped after commit in the incremental materialization
- **THEN** it SHALL use `drop_relation_if_exists()` instead of `adapter.drop_relation()`

### Requirement: Snapshot Post-Cleanup Uses Framework Patterns
The `exasol__post_snapshot` macro SHALL use `drop_relation_if_exists()` instead of `adapter.drop_relation()` for dropping the staging relation.

#### Scenario: Staging table cleanup
- **WHEN** the snapshot materialization completes and needs to drop the staging table
- **THEN** `exasol__post_snapshot` SHALL call `drop_relation_if_exists(staging_relation)` to safely handle the case where the relation may not exist

### Requirement: Unit Test Coverage for Relation Properties
Unit tests SHALL verify that `ExasolRelation` correctly reports `can_be_renamed` and `can_be_replaced` for table and view relation types.

#### Scenario: Test renameable property for table
- **WHEN** a unit test creates an `ExasolRelation` with `type=RelationType.Table`
- **THEN** the `can_be_renamed` property SHALL return `True`

#### Scenario: Test replaceable property for view
- **WHEN** a unit test creates an `ExasolRelation` with `type=RelationType.View`
- **THEN** the `can_be_replaced` property SHALL return `True`

