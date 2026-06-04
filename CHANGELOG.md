# Changelog

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
