## Context

The dbt-adapters framework (v1.22+) provides a structured relation management system through `BaseRelation.renameable_relations` and `BaseRelation.replaceable_relations` fields. These control how the `get_replace_sql` orchestration macro selects a replacement strategy:

1. **Atomic replace** (`CREATE OR REPLACE`) when `can_be_replaced` is `True` and types match
2. **Rename-based swap** (intermediate + backup) when `can_be_renamed` is `True`
3. **Drop and create** as fallback

The Exasol adapter currently falls through to strategy 3 in all cases because neither field is set. Exasol supports both `RENAME TABLE/VIEW` and `CREATE OR REPLACE TABLE/VIEW`, so it should use strategies 1 and 2.

The postgres adapter serves as the reference implementation, declaring both tables and views as renameable and replaceable, with per-type macros in a `macros/relations/{table,view}/` directory structure.

### Dispatch Path Analysis

There are two parallel dispatch paths for relation operations in dbt-adapters:

1. **Legacy path:** `adapter.drop_relation()` / `adapter.rename_relation()` -> `execute_macro("drop_relation")` / `execute_macro("rename_relation")` -> dispatches to `exasol__drop_relation` / `exasol__rename_relation` (if they exist) or falls through to `default__drop_relation` / `default__rename_relation`

2. **Framework path:** `default__drop_relation` calls `get_drop_sql()` which dispatches per-type to `drop_table()` / `drop_view()`. Similarly, `default__rename_relation` calls `get_rename_sql()` which dispatches per-type to `get_rename_table_sql()` / `get_rename_view_sql()`.

Currently, the legacy `exasol__drop_relation` and `exasol__rename_relation` macros short-circuit the dispatch, preventing the framework path from ever being reached. All callers -- including the global table/view materializations and the Exasol-specific incremental/snapshot materializations -- go through the legacy path.

By removing the legacy macros, all callers automatically fall through to the framework path without needing changes to their call sites (they still call `adapter.drop_relation()` / `adapter.rename_relation()` / `drop_relation_if_exists()`).

## Goals / Non-Goals
- Goals:
  - Register tables and views as renameable and replaceable in `ExasolRelation`
  - Implement the per-type macro hooks that the framework dispatches to
  - Remove the legacy `exasol__drop_relation` and `exasol__rename_relation` macros so the framework path is used
  - Migrate the Exasol incremental materialization to use the intermediate/backup/rename pattern from the global default
  - Migrate the Exasol snapshot `exasol__post_snapshot` to use `drop_relation_if_exists()`
  - Follow the same directory structure pattern as the postgres adapter for macro organization
  - Add unit test coverage for the new relation properties
- Non-Goals:
  - Materialized view support (Exasol does not support materialized views)
  - Changes to the adapter Python class (`impl.py`)
  - Modifying the global table/view materializations (they already use `adapter.rename_relation` / `drop_relation_if_exists` which will work correctly with the new dispatch path)

## Decisions

- **Remove legacy macros:** The existing `exasol__rename_relation` and `exasol__drop_relation` macros in `adapters.sql` will be removed. When these are gone, the `drop_relation` Jinja macro dispatches to `default__drop_relation`, which calls `get_drop_sql()`, which dispatches per-type to `exasol__drop_table` / `exasol__drop_view`. Similarly for rename. All existing callers (`adapter.drop_relation()`, `adapter.rename_relation()`, `drop_relation_if_exists()`) continue to work because they go through the same Jinja dispatch mechanism -- only the target macro changes.
  - Alternatives considered: Keeping legacy macros alongside the new ones. Rejected because it creates two parallel code paths that must be kept in sync, and the legacy macros prevent the framework path from being used.

- **Migrate incremental materialization to global pattern:** The Exasol incremental materialization's full-refresh path currently has a custom backup strategy (manual backup identifier, special-casing views vs tables). This will be refactored to follow the global default incremental pattern: use `make_intermediate_relation` / `make_backup_relation`, `drop_relation_if_exists` for cleanup, and the standard rename swap. The non-full-refresh (merge/delete+insert) path remains unchanged.
  - Alternatives considered: Keeping the custom incremental pattern. Rejected because it duplicates framework logic and would diverge further over time.

- **No `CASCADE` in drop macros:** Exasol's `DROP TABLE/VIEW IF EXISTS` does not require `CASCADE` (Exasol handles dependencies differently from PostgreSQL). The existing `exasol__drop_relation` macro does not use `CASCADE`, so the new per-type macros will follow the same pattern.

- **Replace macros delegate to existing create macros:** `exasol__get_replace_table_sql` will reuse the `exasol__create_table_as` logic (which already does `CREATE OR REPLACE TABLE`), and `exasol__get_replace_view_sql` will reuse `exasol__create_view_as` (which already does `CREATE OR REPLACE VIEW`).

## Risks / Trade-offs

- **Behavioral change in replacement strategy:** With `can_be_replaced=True`, the framework will now use `CREATE OR REPLACE` instead of `DROP + CREATE` when replacing a table with a table or a view with a view of the same type. This is actually safer (atomic) but is a behavioral change.
  - Mitigation: This matches what `exasol__create_table_as` and `exasol__create_view_as` already do (`CREATE OR REPLACE`), so the SQL emitted is consistent.

- **Cross-type replacement uses rename strategy:** When changing from table to view (or vice versa), the framework will now use the rename-based backup strategy instead of drop+create. This is safer but involves more SQL statements.
  - Mitigation: The framework handles this orchestration correctly; no adapter-specific logic needed.

- **Removing legacy macros may break custom user macros:** If users have written custom macros that call `exasol__rename_relation` or `exasol__drop_relation` directly (rather than via `adapter.rename_relation()` / `adapter.drop_relation()`), those calls will break.
  - Mitigation: Direct calls to adapter-prefixed dispatch targets is an anti-pattern. The standard approach is to call the unprefixed macro (`rename_relation`, `drop_relation`) or the Python method (`adapter.rename_relation`, `adapter.drop_relation`). This is a minor breaking change.

## Open Questions
- None. The implementation is straightforward and mirrors the postgres adapter pattern.
