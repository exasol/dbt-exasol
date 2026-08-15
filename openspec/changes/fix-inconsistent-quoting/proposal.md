## Why

`ExasolRelation`'s DDL macros access `.schema` and `.identifier` as raw dataclass attributes, bypassing the `render()` method that applies `quote_policy`. This means `CREATE TABLE` / `CREATE VIEW` DDL always renders identifiers unquoted, while `ref()` and `source()` respect `quote_policy`. Setting `quoting:` in `dbt_project.yml` therefore *half-works*: `ref('model_a')` compiles to `"model_a"` while the DDL created the Exasol-uppercased `MODEL_A`, producing `object "model_a" not found`.

Measured against the current code (Exasol 8.29, dbt-core 1.12):

- **With no `quoting:` config** (the default), a fresh two-model project with lowercase `snake_case` names **works**. `ref()` renders unquoted, DDL renders unquoted, both resolve to the same uppercase object. The bug report's "minimal repro" does not reproduce in this configuration.
- **With `quoting: {identifier: true}`**, the same project **fails**: `ref()`/`source()` honor the setting, the DDL ignores it.

So the defect is not "lowercase model names are broken by default" — it is "`quoting:` is silently inconsistent, and therefore unusable". That is still a correctness bug: a documented dbt-core project config is accepted, partially applied, and produces broken SQL rather than an error.

## What Changes

- Rewire DDL macros (`create_view_as`, `create_table_as`, `drop_relation`, `drop_table`, `drop_view`, `get_rename_table_sql`, `get_rename_view_sql`, `truncate_relation`) to use `{{ relation }}` (which calls `render()` and respects `quote_policy`) instead of raw `{{ relation.schema }}.{{ relation.identifier }}`.
- Remove the `| replace('"', '')` quote-stripping hack in `truncate_relation` — the relation now renders correctly via `render()`.
- Return identifiers **as stored** from `list_relations_without_caching` instead of `lower()`-ing them, and mark cache relations `dbt_created=True`. Cache-derived relations are used to *build DDL* (rename, drop, replace), so a lowercased cache produced DDL that named a non-existent object as soon as quoting was enabled. `dbt_created=True` keeps `BaseRelation._is_exactish_match` case-insensitive for unquoted relations, preserving today's matching behavior.
- Stop uppercasing rendered relations inside snapshot SQL (`snapshot.sql`, `snapshot_merge.sql`). `{{ target_relation | upper }}` uppercases *inside* the quotes, turning `"snap"` into `"SNAP"` — a different object.
- Derive PK constraint names from the relation's raw path parts (`exasol__constraint_name_prefix`) instead of `relation|replace('.','_')`. The rendered form embeds quote characters, and Exasol rejects the result with a syntax error.
- Parse the `0CSV|` seed target with a quote-aware splitter (`_split_relation_path`) and enable pyexasol's `quote_ident`, so seed `IMPORT INTO` targets the object the seed's `CREATE TABLE` created under any quote policy.

This is **not a breaking change**. Under the default `ExasolQuotePolicy` (all fields `False`), `{{ relation }}` and raw `.schema`.`identifier` produce identical output. This was verified by diffing every materialized statement under `target/run/` for a project covering seed, table, view, incremental, full-refresh and snapshot, before and after the change: the only delta is one `SNAP__DBT_TMP` → `SNAP__dbt_tmp` case change in an *unquoted* position, which Exasol folds identically.

## Capabilities

### New Capabilities

_None._ This is a bug fix to the existing `quoting` capability.

### Modified Capabilities

- `quoting`: The existing spec already requires the adapter to respect `quoting` configuration. The requirements are correct but the implementation diverged. The spec gains scenarios that codify DDL/`ref()` consistency, the source-quoting boundary, the non-breaking default guarantee, and the seed/snapshot/rename/constraint paths that quoting also touches.

## Impact

- **DDL macros**: `dbt/include/exasol/macros/adapters.sql`, `relations/table/drop.sql`, `relations/view/drop.sql`, `relations/table/rename.sql`, `relations/view/rename.sql`
- **Snapshot macros**: `materializations/snapshot.sql`, `materializations/snapshot_merge.sql`
- **Constraint helper**: `create_table_helpers.sql` (new `exasol__constraint_name_prefix`)
- **Catalog macro**: `adapters.sql` (`list_relations_without_caching` returns identifiers as stored)
- **Adapter code**: `dbt/adapters/exasol/impl.py` (`dbt_created=True` on cache relations), `dbt/adapters/exasol/connections.py` (`_split_relation_path`, `quote_ident=True`)
- **Untouched**: `dbt/adapters/exasol/relation.py` (`ExasolQuotePolicy` defaults unchanged), `_make_match_kwargs` (left as-is — see design D2), `exasol__quote_column` and snapshot/merge column-level helpers
- **Tests**: `tests/unit/test_connections.py` updated (the `0CSV|` seed target is now case-folded — an intentional behavior change) plus new `_split_relation_path` coverage; new `tests/functional/adapter/test_quoting_consistency.py` covering both policies end-to-end. No existing test assertion was weakened or deleted.
- **Release notes**: document that the undocumented `identifier: '"orders"'` workaround is no longer needed — set `quoting: {identifier: true}` on the source instead.
