# Change: Claim full dbt-core 1.11 parity for dbt-exasol

## Why

dbt-exasol's `pyproject.toml` declares `version = "1.11.0"` and depends on `dbt-core>=1.11.0` / `dbt-adapters>=1.11.0`, but the runtime version string in `dbt/adapters/exasol/__version__.py` still reads `1.10.6` (so `dbt --version` disagrees with the package metadata), and the adapter has never made an explicit, testable claim of "1.11 parity". This change also reconciles `__version__.py` to `1.11.0`. Several 1.11-era features are *functionally* present (microbatch, sample mode, snapshot `hard_deletes`, snapshot `dbt_valid_to_current`, UDFs/UDAFs in flight) yet are not advertised through the capability matrix, not covered by the upstream `dbt-tests-adapter` 1.11 test classes, and not documented as supported. Other 1.11 framework hooks (single-relation catalog, batched last-modified metadata, catalog integrations) are stubbed or absent. The result is that users, the dbt-labs compatibility matrix, and contributors cannot tell which 1.11 features actually work on Exasol — and where the gaps are, they aren't explained.

This change establishes a single, auditable parity claim against dbt-core 1.11 (taking dbt-snowflake as the feature-completeness reference) by (a) implementing the small framework hooks that are missing, (b) subclassing the relevant upstream tests so the claim is provable, and (c) documenting features that are intentionally non-applicable to Exasol with a stated reason.

## What Changes

### Adapter capability declarations
- Declare `Capability.GetCatalogForSingleRelation` as `Support.Full` after implementing `ExasolAdapter.get_catalog_for_single_relation()` against `EXA_ALL_COLUMNS` / `EXA_ALL_OBJECTS`.
- Declare `Capability.TableLastModifiedMetadataBatch` as `Support.Full` (we already declare `TableLastModifiedMetadata: Full`; the existing `exasol__get_relation_last_modified` macro already loops over multiple relations, so the batched path works today). As part of this change the macro is switched from `SYS.EXA_USER_OBJECTS` (current-user-owned objects only) to `SYS.EXA_ALL_OBJECTS` so cross-owner sources resolve and the `Full` claim is honest.
- Declare `Capability.MicrobatchConcurrency` explicitly as `Support.Unsupported` with an inline comment explaining Exasol's transaction-conflict semantics on shared-table DELETE+INSERT (see design.md).
- Add empty `_behavior_flags` scaffolding (returns `[]`) so future per-adapter behavior flags have a documented home.

### Single-relation catalog implementation
- Replace `get_catalog_for_single_relation` `NotImplementedError` with a real implementation that returns a `CatalogTable` for one relation by querying `EXA_ALL_COLUMNS` filtered to `(table_schema, table_name)`.
- Add a corresponding `exasol__get_catalog_for_single_relation` macro under `dbt/include/exasol/macros/`.

### Catalog-integrations graceful no-op
- Keep `CATALOG_INTEGRATIONS = []` (default) but add a functional smoke test that verifies dbt-exasol parses and runs a project containing a `catalogs.yml` without crashing, as long as no model sets the `catalog` config.
- If a model *does* set `catalog`, the run must fail with a clear `DbtRuntimeError` (not a Python traceback) stating Exasol does not support catalog integrations.

### Upstream-test subclassing (proof of parity)
- `dbt.tests.adapter.dbt_clone`: subclass `BaseCloneNotPossible`, `BaseCloneSameSourceAndTarget`, `BaseCloneSameTargetAndState` under `tests/functional/adapter/dbt_clone/`. (No code change — relies on default `can_clone_table` returning `False`, materializing clones as views.)
- `dbt.tests.adapter.simple_snapshot`: subclass `test_ephemeral_snapshot_hard_deletes` and `new_record_dbt_valid_to_current` under `tests/functional/adapter/simple_snapshot/`. The existing custom tests stay; the upstream subclasses become the authoritative parity proof.
- `dbt.tests.adapter.catalog_integrations.test_catalog_integration.BaseCatalogIntegrationValidation`: subclass to assert the graceful no-op behaviour above.
- `dbt.tests.adapter.sample_mode.test_sample_mode.BaseSampleModeTest`: already subclassed indirectly via the microbatch test; add an explicit subclass so the claim is visible in `pytest --collect-only`.

### Hard-deprecation audit
- Add a CI job that runs `dbt parse` against the existing fixtures with `warn-error: true` to catch any deprecated patterns in adapter macros or example projects (e.g. `MissingPlusPrefixDeprecation`, `CustomKeyInConfigDeprecation`).
- Fix any deprecation warnings the audit surfaces in adapter-owned files (macros and example `dbt_project.yml` fragments in tests).

### Documentation
- Add a 1.11 parity matrix to `README.md` modelled on dbt-labs' adapter-feature matrix, listing every capability/feature with one of: `✅ Supported`, `⚠️ Conditional`, `❌ Not supported (platform)`, `❌ Not supported (not yet)`.
- Document the **microbatch concurrency** non-support and **catalog integrations / Iceberg** non-support with explicit reasoning, so users on multi-warehouse projects aren't surprised.
- Document that **Python models** and **materialized views** remain unsupported with reasons.

### Out of scope
- Implementing Python models on Exasol (no Python execution sandbox available on the DB side outside UDF SCRIPTs).
- Implementing materialized views (Exasol has no MV primitive).
- Implementing Iceberg / external catalog integrations.
- Making microbatch concurrent — would require either Exasol's `MERGE` with row-level isolation testing or a per-batch sub-transaction strategy; revisit later as its own change.
- UDF/UDAF work — covered by the in-flight `add-udf-function-support` change.

## Capabilities

### New Capabilities
- `dbt-core-version-parity`: Defines the contract by which dbt-exasol claims compatibility with a given dbt-core minor version. Specifies which capability declarations must be present, which upstream test classes must be subclassed, which features are explicitly non-applicable and why, and where the public parity matrix lives. Initial version targets dbt-core 1.11; future minor-version bumps update this spec.

### Modified Capabilities
<!-- None. The existing specs (atomic-ctas, cicd, connection-pooling, development-environment, quality, quoting, relation-management) describe Exasol-specific behaviours that are independent of which dbt-core minor version we target. -->

## Impact

- **Code**: `dbt/adapters/exasol/impl.py` (capability dict, `get_catalog_for_single_relation`, `_behavior_flags` scaffold), one new macro `dbt/include/exasol/macros/get_catalog_for_single_relation.sql`.
- **Tests**: new subclass files under `tests/functional/adapter/dbt_clone/`, `tests/functional/adapter/simple_snapshot/` (additions), `tests/functional/adapter/catalog_integrations/` (new dir), `tests/functional/adapter/sample_mode/` (new dir).
- **CI**: new nox session `lint:deprecations` (or extend existing `lint:code`) running `dbt parse` with `warn-error: true` against the test fixture project.
- **Docs**: `README.md` parity matrix section, possibly a new `docs/1.11-parity.md`.
- **Dependencies**: no version changes; we already require `dbt-core>=1.11.0`, `dbt-adapters>=1.11.0`, and `dbt-tests-adapter>=1.11.0` (dev).
- **No breaking changes** for end users. Declaring new capabilities only enables additional dbt-core code paths (e.g. single-relation catalog lookup) that previously fell back to whole-schema queries — strictly a performance improvement.
- **Interaction with `add-udf-function-support`**: the UDF change should land first; this proposal's parity matrix will reference UDFs/UDAFs as `✅ Supported` once that change archives. If the UDF change is still open when this one starts, the matrix entry stays as `⚠️ Conditional (in flight)` until both ship.
