# Changelog

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

### Fixed
- Column comments (`persist_docs`) are now applied only to columns that
  actually exist in the relation, using `validate_doc_columns`; stale model
  column definitions no longer break comment propagation.

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
