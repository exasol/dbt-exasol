# Changelog

## 1.12.1 — polish and bugfixes

A maintenance release with no breaking changes. Completes the feature set
announced in v1.12.0 with the last fixes and some usability improvements.

### Added
- `database` parameter in `profiles.yml` now defaults to `"DB"` (Exasol's
  default database name), so projects that don't need a specific database can
  omit it entirely.
- TLS certificate parameter documented in the README for secure connections.

### Changed
- **`timestamp_format` is now documented as session-wide** ([#229](https://github.com/exasol/dbt-exasol/issues/229)).
  The value is applied with `ALTER SESSION SET NLS_TIMESTAMP_FORMAT` on every
  connection the adapter opens, so it governs model SQL, snapshots and seed
  imports — not seeds alone. The default `YYYY-MM-DDTHH:MI:SS.FF6` keeps
  ISO-8601 seed files working ([#35](https://github.com/exasol/dbt-exasol/issues/35))
  but differs from Exasol's server default `YYYY-MM-DD HH24:MI:SS.FF6`, which
  makes dbt-compiled SQL behave differently in other clients. The README now
  states the scope and how to opt into the server default; the applied format
  is also emitted as a debug log line. No behaviour change — the default is
  unchanged and a breaking change is deferred to a major release.
- The `exasol__create_schema` and `exasol__persist_docs` macro overrides have
  been removed: both had converged to be byte-identical to dbt-core's current
  `default__create_schema` / `default__persist_docs`. Dispatch now falls
  through to the shared macros; no behaviour change, less surface to keep in
  sync with upstream.

### Fixed
- **Seed CSV line endings are now detected per file.** The `IMPORT ... ROW
  SEPARATOR` used for seeds was derived from the client OS (`os.linesep`),
  which says nothing about the bytes in the CSV file. Both mismatches failed
  silently: a CRLF seed built on Linux appended a stray `\r` to the last
  column of every row, and an LF seed built on Windows loaded zero rows while
  `dbt seed` reported success. The separator is now sniffed from each seed
  file, so `LF`, `CRLF` and `CR` seeds — including a mix of them in one
  project — import correctly. Setting `row_separator` in `profiles.yml` still
  forces that value for every seed (unchanged behaviour); files with genuinely
  mixed line endings now emit a warning instead of corrupting rows silently.
- **Quoting is now applied consistently.** DDL (`CREATE TABLE`/`VIEW`, `DROP`,
  `TRUNCATE`, `RENAME`), snapshots, seeds, and relation lookups now render
  through the relation's `quote_policy`, matching `ref()` and `source()`.
  Previously, with `quoting: {identifier: true}`, `ref('model_a')` compiled to
  `"model_a"` while `CREATE TABLE` created the Exasol-folded `MODEL_A`,
  producing `object "model_a" not found`; tables, views, incremental models,
  `--full-refresh`, snapshots, seeds, and enforced contracts now work
  end-to-end. The undocumented `identifier: '"orders"'` workaround for
  case-sensitive sources is no longer needed — set source-level
  `quoting: {identifier: true}` instead (project-level `quoting:` never
  applies to sources, per dbt-core). `quoting: {schema: true}` remains
  unsupported.
- **Unit tests (`dbt test --select test_type:unit`) no longer execute the full
  model query.** The macro that builds the metadata-only temp table used to
  discover column names/types (`get_empty_subquery_sql`) was missing the
  `where false` / `limit 0` filter dbt-core's default provides, so every unit
  test run materialized the model's real result set before immediately
  dropping it. The filter is restored; the Exasol-specific subquery alias
  (`dbt_sbq_tmp`, required because Exasol rejects unquoted identifiers
  starting with `_`) is unchanged.
- **A contracted or unit-tested model with a statement-style `sql_header` no
  longer fails to build.** Exasol accepts exactly one statement per request,
  so emitting a header such as `alter session set TIME_ZONE = '...';`
  immediately in front of the metadata-only `select` (as dbt-core's default
  does) raised `syntax error, unexpected SELECT_, expecting END_OF_INPUT_`.
  A header that is a complete statement is now submitted separately on the
  same connection, so the session setting still applies to the following
  query. Headers that are only a query prefix — most notably a leading
  `with ... as (...)` CTE — remain inline and are no longer concatenated
  directly onto the `select` keyword.
- Column comments (`persist_docs`) are now applied only to columns that
  actually exist in the relation, using `validate_doc_columns`; stale model
  column definitions no longer break comment propagation.

## 1.12.0 — dbt-core 1.12 support

Supports **dbt-core 1.12** and adopts its new adapter-facing features. See the
[dbt-core version parity matrix](README.md#dbt-core-version-parity) for the full
feature list.

### Added
- Support for **dbt-core 1.12** (`dbt-core>=1.12.0,<1.13`, `dbt-adapters>=1.24.5`).
- Empty-seed support: `dbt seed --empty` and `dbt build --empty` create correctly
  typed empty tables; covered by the upstream `BaseTestEmptySeedFlag` suite.
  Known limitation: an `--empty` seed followed immediately by a plain
  (non-`--full-refresh`) `seed` on a CSV with decimal columns is not fully
  validated — use `dbt seed --full-refresh` to reload (see README).
- Functional coverage for `latest_version_pointer`: versioned models
  automatically get a pointer view named after the base model (dbt-core 1.12).
- `Capability.CatalogsV2` declared as `Unsupported`.
- Python 3.14 support; Python support window is now **3.11–3.14**
  (3.10 dropped).

### Changed
- `ExasolCursor.fetchone`/`fetchmany`/`fetchall` now raise
  `dbt_common.exceptions.DbtRuntimeError` instead of a raw `RuntimeError` when
  called on an unset statement, aligning with dbt-core 1.12 exception handling.
- `convert_number_type` returns `float` for zero-row agate tables (e.g. empty
  seeds) instead of letting `agate.MaxPrecision` degrade decimal columns to
  `integer`.

## 1.11.0 — dbt-core 1.11 parity

Establishes an explicit, testable parity claim against **dbt-core 1.11** (reference
adapter: dbt-snowflake). See the
[dbt-core version parity matrix](README.md#dbt-core-version-parity) for the full
feature list and the
[`dbt-core-version-parity` spec](openspec/specs/dbt-core-version-parity/spec.md)
for the underlying contract.

### Added
- Support for **User-Defined Functions (UDFs)** and **User-Defined Aggregate Functions (UDAFs)**, including SQL scalar, Python scalar, and Python aggregate functions.
- Capability declarations for every `dbt.adapters.capability.Capability` value:
  `GetCatalogForSingleRelation` and `TableLastModifiedMetadataBatch` as `Full`,
  `MicrobatchConcurrency` as `Unsupported` (Exasol transaction-conflict semantics).
- `ExasolAdapter.get_catalog_for_single_relation` plus the
  `get_catalog_for_single_relation` macro (delegates to `exasol__get_catalog_relations`).
- `_behavior_flags` scaffolding (returns `[]`) for future platform flags.
- Clear `DbtRuntimeError` when a model sets `config(catalog=...)`; projects with an
  unused `catalogs.yml` still parse and run.
- Upstream `dbt-tests-adapter` subclasses for clone, snapshot `hard_deletes` and
  `dbt_valid_to_current`, sample mode, and catalog-integration validation.
- `lint:deprecations` nox session running `dbt parse` with `warn-error: true`
  against an adapter-owned fixture project (wired into `mise run check` and CI).
- "dbt-core version parity" matrix in `README.md`.

### Changed
- `exasol__get_relation_last_modified` now reads `SYS.EXA_ALL_OBJECTS` (was
  `SYS.EXA_USER_OBJECTS`) so cross-owner sources resolve, honouring the
  `TableLastModifiedMetadataBatch: Full` claim.
- Reconciled the runtime version string in `dbt/adapters/exasol/__version__.py`
  (`1.10.6` → `1.11.0`) to match `pyproject.toml`.

### Fixed
- **Pooled-connection thread binding** — adapter metadata calls (e.g.
  `list_relations`) issued on a thread that has no bound connection (outside a
  `connection_named` block) now acquire a pooled connection on demand instead of
  raising `InvalidConnectionError: connection never acquired for thread`. This
  restores the implicit contract that non-pooled adapters satisfy, and unblocks
  upstream `dbt-tests-adapter` classes that invoke adapter methods directly.
- **`dbt clone --target otherschema`** — cross-target clone-as-view now works
  end-to-end; `TestExasolCloneNotPossible` passes against a live Exasol instance.
