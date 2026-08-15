## 1. Macro: adapters.sql DDL rewiring

- [x] 1.1 In `dbt/include/exasol/macros/adapters.sql`, replace `{{ relation.schema }}.{{ relation.identifier }}` with `{{ relation }}` in `exasol__create_view_as`
- [x] 1.2 In the same file, replace all four occurrences in `exasol__create_table_as`: the contract-path `CREATE OR REPLACE TABLE`, the `ALTER TABLE ... MODIFY COLUMN` NOT NULL clause, the `ALTER TABLE ... ADD CONSTRAINT` clause, and the non-contract `CREATE OR REPLACE TABLE`
- [x] 1.3 In the same file, replace `{{ relation.schema }}.{{ relation.identifier }}` with `{{ relation }}` in `exasol__drop_relation`
- [x] 1.4 In the same file, replace `{{ relation | replace('"', '') }}` with `{{ relation }}` in `exasol__truncate_relation`
- [x] 1.5 Leave `exasol__get_columns_in_relation` unchanged — `{{ relation.identifier|upper }}` there is a case-insensitive system-catalog comparison, not a DDL identifier

## 2. Macro: relations/ drop and rename rewiring

- [x] 2.1 `relations/table/drop.sql`: `{{ relation }}` in `exasol__drop_table`
- [x] 2.2 `relations/view/drop.sql`: `{{ relation }}` in `exasol__drop_view`
- [x] 2.3 `relations/table/rename.sql`: `{{ relation }}` in `exasol__get_rename_table_sql`
- [x] 2.4 `relations/view/rename.sql`: `{{ relation }}` in `exasol__get_rename_view_sql`

## 3. Catalog: return identifiers as stored

- [x] 3.1 In `dbt/include/exasol/macros/adapters.sql`, change `exasol__list_relations_without_caching` to select `table_name` / `table_schema` instead of `lower(table_name)` / `lower(table_schema)`. Cache relations feed DDL (drop/rename/replace), so a lowercased cache emits DDL naming a non-existent object once quoting is enabled.
- [x] 3.2 In `dbt/adapters/exasol/impl.py`, pass `dbt_created=True` when building relations in `list_relations_without_caching`, so `BaseRelation._is_exactish_match` keeps unquoted matching case-insensitive while quoted relations match exactly.
- [x] 3.3 Leave `_make_match_kwargs` unchanged. Fixing the cache at the source makes the previously proposed unconditional-lowercase override unnecessary, and keeps `tests/unit/test_impl.py::TestMakeMatchKwargs` passing untouched.

## 4. Snapshots: stop uppercasing rendered relations

- [x] 4.1 In `materializations/snapshot.sql`, change `from {{ target_relation | upper }} sd` to `from {{ target_relation }} sd`. `| upper` uppercases *inside* the quotes, turning `"snap"` into the non-existent `"SNAP"`.
- [x] 4.2 In `materializations/snapshot_merge.sql`, drop `| upper` from both `merge into {{ target }}` and `using {{ source }}`.

## 5. Constraints: build names from raw path parts

- [x] 5.1 Add `exasol__constraint_name_prefix(relation)` to `create_table_helpers.sql`, building the name from `relation.schema` + `relation.identifier` with quote characters stripped.
- [x] 5.2 Use it in `create_table_helpers.sql::primary_key_conf` in place of `relation|replace('.','_')`.
- [x] 5.3 Use it in `adapters.sql::exasol__create_table_as` for the contract-path `ADD CONSTRAINT ... __pk`. Verified: the previous form emitted `schema_"model"__pk`, which Exasol rejects with `syntax error, unexpected IDENTIFIER_PART_`.

## 6. Seeds: quote-aware `0CSV|` target parsing

- [x] 6.1 Add `_split_relation_path` to `dbt/adapters/exasol/connections.py`: split on unquoted dots only, unwrap quoted components (collapsing `""` escapes), upper-case unquoted components to mirror Exasol's folding, and raise `DbtRuntimeError` on a malformed path.
- [x] 6.2 Use it in `ExasolCursor.execute` in place of `table_path.split(".", 1)`.
- [x] 6.3 Pass `quote_ident=True` when opening the pyexasol connection, so the HTTP transport quotes the already-case-resolved components verbatim instead of applying its own folding.

## 7. Tests

- [x] 7.1 Update `tests/unit/test_connections.py::test_execute_csv_import` — the seed `IMPORT` target is now case-folded (`("SCHEMA", "TABLE")`). This is the intentional fix, not a regression: the old value only worked because pyexasol was silently upper-casing it.
- [x] 7.2 Add `test_execute_csv_import_quoted_relation` asserting a quoted target keeps its exact case.
- [x] 7.3 Add `TestSplitRelationPath` unit coverage: unquoted folding, quoted pass-through, mixed quoting, escaped inner quote, dot inside a quoted component, and malformed paths.
- [x] 7.4 Add `tests/functional/adapter/test_quoting_consistency.py` with two subclasses — default policy and `quoting: {identifier: true}` — each running seed → run → re-run → `--full-refresh` → snapshot → snapshot → test, plus an assertion that the `CREATE TABLE` DDL and the `ref()` body render the identifier identically. Read the DDL from `target/run/<project>/models/<model>.sql`; `run_results.json`'s `compiled_code` holds only the SELECT body.
- [x] 7.5 Confirm no existing test assertion was weakened or removed to make the change pass.

## 8. Validation

- [x] 8.1 `uv run nox -s test:unit` — 245 passed.
- [x] 8.2 `uv run nox -s test:integration` — 226 passed, 1 skipped, 9 xfailed, 2 xpassed.
- [x] 8.3 `uv run nox -s format:check lint:code lint:security lint:typing` — all four sessions pass.
- [x] 8.4 Verify the non-breaking guarantee: capture `target/run/**` for a full-lifecycle project under the default policy before and after the change and diff. Result: identical except `SNAP__DBT_TMP` → `SNAP__dbt_tmp` in an unquoted position, which Exasol folds identically.

## 9. Documentation

- [x] 9.1 CHANGELOG: record the quoting consistency fix, note that `identifier: '"orders"'` in source YAML is no longer needed (use source-level `quoting: {identifier: true}`), and state that `quoting: {schema: true}` is unsupported.
- [x] 9.2 README: document supported `quoting:` configuration and the Exasol case-folding behavior users need to understand when enabling it.
