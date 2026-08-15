## Context

`ExasolRelation.quote_policy` defaults to `ExasolQuotePolicy(database=False, schema=False, identifier=False)`. `BaseRelation.render()` wraps each path component in double quotes only if `quote_policy.get_part(part)` is `True`, so the default policy renders `schema.model_a`.

The Exasol DDL macros **bypass `render()` entirely**, accessing raw dataclass fields:

```sql
CREATE OR REPLACE TABLE {{ relation.schema }}.{{ relation.identifier }} AS ...
```

The DDL is therefore always unquoted regardless of `quote_policy`, while `ref()` and `source()` go through `Relation.create_from()`, which deep-merges project-level `quoting:` into `quote_policy`. With `quoting: {identifier: true}`, `ref('model_a')` compiles to `schema."model_a"` but the DDL creates `MODEL_A`.

### What was measured

All findings below were reproduced against Exasol 8.29 / dbt-core 1.12 before implementing anything:

| Configuration | Before fix | After fix |
|---|---|---|
| default policy, lowercase models, ref() chain | passes | passes (DDL byte-identical) |
| `quoting: {identifier: true}`, table/view/ref | **fails** `object "model_a" not found` | passes |
| `quoting: {identifier: true}`, 2nd `dbt run` | **fails** `ApproximateMatchError` | passes |
| `quoting: {identifier: true}`, ALL_CAPS incremental `--full-refresh` | **fails** `object "model_inc" does not exist` | passes |
| `quoting: {identifier: true}`, 2nd `dbt snapshot` | **fails** `object …SNAP not found` | passes |
| `quoting: {identifier: true}`, seed | **fails** `["my_seed"] is not a safe identifier` | passes |
| `quoting: {identifier: true}`, contract model with PK | **fails** `syntax error` | passes |

The last four are *not* fixed by the DDL rewiring alone; each needed its own change. Three of them are pre-existing failures independent of this change, but they all sit on the path this change opens up, so shipping the DDL fix without them would advertise a config that still does not work.

## Goals / Non-Goals

**Goals:**
- Make every DDL render path go through `render()` so `quote_policy` is consistently applied
- Guarantee zero behavioral change for projects that do not set `quoting:` (verified by diffing materialized SQL)
- Make `quoting: {identifier: true}` actually usable: seed, table, view, incremental, full-refresh, snapshot, and contract constraints
- Keep the change inside relation-level rendering — no change to column-level quoting

**Non-Goals:**
- Changing `ExasolQuotePolicy` defaults — they stay all `False` (see D3)
- Column-level quoting: `quote_seed_column()`, `exasol__quote_column`, and snapshot/merge column helpers handle SQL keyword detection, which is orthogonal
- Supporting `quoting: {schema: true}`. Measured: it breaks schema creation independently of this change (`create_schema` renders `"schema"` while `list_schemas`/`drop_schema` do not agree). Explicitly documented as unsupported rather than silently half-working (see D6).
- Supporting two models whose names differ only by case

## Decisions

### D1: Replace raw `.schema`/`.identifier` with `{{ relation }}` in DDL macros

`{{ relation }}` invokes `__str__()` → `render()` → `_render_iterator()`, which consults `quote_policy` per component. This is the canonical dbt-core pattern.

**Rationale:** Under the default policy, `render()` produces the same string as raw field access, so existing output is unchanged. For users who opt into quoting, the DDL now respects their config.

**Macros changed:**

| Macro | Before | After |
|-------|--------|-------|
| `exasol__create_view_as` | `{{ relation.schema }}.{{ relation.identifier }}` | `{{ relation }}` |
| `exasol__create_table_as` | same (4×) | `{{ relation }}` (4×) |
| `exasol__drop_relation` | same | `{{ relation }}` |
| `exasol__drop_table` | same | `{{ relation }}` |
| `exasol__drop_view` | same | `{{ relation }}` |
| `exasol__get_rename_table_sql` | same | `{{ relation }}` |
| `exasol__get_rename_view_sql` | same | `{{ relation }}` |
| `exasol__truncate_relation` | `{{ relation \| replace('"', '') }}` | `{{ relation }}` |

`exasol__get_columns_in_relation` is intentionally **not** changed — it compares `{{ relation.identifier\|upper }}` against a system catalog column, which is case-insensitive on both sides, not a DDL identifier.

### D2: Return catalog identifiers as stored; mark cache relations `dbt_created`

`exasol__list_relations_without_caching` applied `lower()` to `table_name`/`table_schema`. Cache relations are not only used for existence checks — they are passed straight into DDL (`drop_relation_if_exists(existing_relation)`, `rename_relation(existing_relation, backup_relation)`). With quoting enabled, a lowercased cache entry renders `"model_inc"` while the physical object is `MODEL_INC`, so `RENAME` fails.

The fix returns identifiers **as stored** and sets `dbt_created=True` when constructing cache relations. `BaseRelation._is_exactish_match` already does:

```python
if self.dbt_created and self.quote_policy.get_part(field) is False:
    return self.path.get_lowered_part(field) == value.lower()
```

so unquoted relations keep matching case-insensitively (today's behavior), while quoted relations match exactly — which is correct, because a quoted identifier *is* case-sensitive in Exasol.

**This replaces the originally proposed change to `_make_match_kwargs`.** That approach (always `.lower()` the match key) was measured to work for the `ref()` case but left the rename path broken, because it fixed the *lookup key* while the *cached relation itself* still carried a lowercased identifier into DDL. It also required rewriting two existing unit tests that assert case preservation under quoting. Fixing the cache at the source is strictly better: `_make_match_kwargs` needs no change, and `tests/unit/test_impl.py::TestMakeMatchKwargs` passes untouched.

**Alternatives considered:**
- Always lowercase in `_make_match_kwargs` (the original proposal): rejected, incomplete — see above.
- Change `ExasolQuotePolicy` defaults to `True`: rejected as breaking (see D3).

### D3: `ExasolQuotePolicy` defaults remain unchanged

Keep `database=False, schema=False, identifier=False`.

**Rationale:** Changing defaults would break every existing project: `ref()` would start rendering quoted, and existing physical tables (created unquoted as `MODEL_A`) would not match `"model_a"`. Users would need a `--full-refresh` of every model. Keeping `False` preserves Exasol's native case-insensitive behavior for users who do not opt in.

### D4: Snapshots must not uppercase a rendered relation

`snapshot.sql` used `from {{ target_relation | upper }} sd`, and `snapshot_merge.sql` used `merge into {{ target | upper }}` / `using {{ source | upper }}`. When quoting is enabled the rendered string contains quotes, so `| upper` produces `"SNAP"` — a *different*, non-existent object. Under the default policy the filter is a no-op on an already-uppercase-folded identifier, which is why this was never noticed.

Removing `| upper` is safe under both policies: Exasol folds the unquoted form itself. Verified by a second `dbt snapshot` run (the merge path) under both policies.

### D5: Constraint names come from raw path parts

`exasol__create_table_as` built `{{ relation|replace('.','_') }}__pk` from the *rendered* relation. With quoting enabled this yields:

```sql
ADD CONSTRAINT test_schema_"c_model"__pk PRIMARY KEY(id)
```

Measured result: `syntax error, unexpected IDENTIFIER_PART_`. The original proposal claimed this was "ugly but valid SQL — Exasol accepts quoted characters in [constraint names]". That claim is **false**; it was never tested.

New helper `exasol__constraint_name_prefix(relation)` builds the name from `relation.schema ~ '_' ~ relation.identifier` with quote characters stripped. Applied at both sites (`adapters.sql` contract path and `create_table_helpers.sql::primary_key_conf`). Verified: the emitted constraint name is `TEST_SCHEMA_C_MODEL__PK` under both policies — i.e. identical to today's default-policy output.

### D6: Seeds parse the `0CSV|` target quote-aware; pyexasol quotes identifiers

`exasol__basic_load_csv_rows` passes `this.render()` through the `0CSV|` protocol, and `ExasolCursor.execute` did `table_path.split(".", 1)`. With quoting enabled the components still carry quote characters, which pyexasol's `safe_ident` rejects outright (`Value ["my_seed"] is not a safe identifier`).

Two coordinated changes:
1. `_split_relation_path` splits on unquoted dots only, unwraps quoted components (collapsing `""` escapes), and **upper-cases unquoted components** to mirror Exasol's folding — so the `IMPORT INTO` target matches the object the seed's `CREATE TABLE` actually created.
2. `quote_ident=True` on the pyexasol connection, so the HTTP transport quotes each component verbatim instead of applying its own folding.

Because step 1 resolves each component to its exact stored case before pyexasol sees it, step 2 is safe: pyexasol is only ever handed already-correct identifiers. Malformed paths raise `DbtRuntimeError` rather than silently mis-targeting a table.

`quoting: {schema: true}` remains unsupported: measured, it breaks `create_schema` before seeds are even reached. This is stated as a limitation rather than silently half-fixed.

## Risks / Trade-offs

- **`quote_ident=True` is connection-wide.** It only affects pyexasol's own identifier formatting for HTTP transport (`IMPORT`/`EXPORT`); ordinary SQL is passed through as text built by dbt macros. The adapter does not call pyexasol's `ext`/`open_schema` helpers, which are the other consumers of the flag. Covered by the full functional suite, including every seed test.

- **Catalog now returns mixed-case identifiers.** Anything comparing cache identifiers by raw string equality would be affected. `dbt_created=True` restores case-insensitive matching for unquoted relations, and the full functional suite (226 tests, including `dbt docs generate`, catalog, and clone tests) passes.

- **Seed `IMPORT` target changed from as-rendered to case-folded.** This is the intentional fix; `tests/unit/test_connections.py::test_execute_csv_import` was updated from `("schema", "table")` to `("SCHEMA", "TABLE")`. It is not a regression: the old value only worked because pyexasol was silently upper-casing it, which is exactly what broke once quotes appeared.

- **The `'"orders"'` source workaround stops being necessary.** Users who embedded literal quotes in `identifier:` should remove them and set `quoting: {identifier: true}` on the source. Release notes must document this.

- **One cosmetic delta under the default policy**: `SNAP__DBT_TMP` → `SNAP__dbt_tmp` in snapshot merge SQL. Unquoted, so Exasol folds it identically; verified by passing snapshot tests under both policies.

## Migration Plan

1. Apply the macro, catalog, snapshot, constraint, and seed changes.
2. Run `uv run nox -s test:unit` — 245 pass.
3. Run `uv run nox -s test:integration` — 226 pass, 1 skipped, 9 xfailed, 2 xpassed.
4. Confirm the non-breaking guarantee by diffing `target/run/**` for a full-lifecycle project before/after under the default policy.
5. Release with a note deprecating the `'"orders"'` workaround and documenting that `quoting: {schema: true}` is unsupported.

**Rollback:** Revert the macro and Python changes. No data migration or state change is involved.

## Open Questions

_None._ Every decision above was validated against a live Exasol instance.
