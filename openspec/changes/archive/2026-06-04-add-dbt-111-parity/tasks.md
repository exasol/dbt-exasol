## 1. Spike: verify microbatch concurrency assumption

- [x] 1.1 Write a manual repro script under `scripts/spikes/microbatch_concurrency.py` that opens two `pyexasol` connections and runs disjoint DELETE+INSERT statements against the same test table concurrently
- [x] 1.2 Document the observed outcome (transaction conflict OR success) in `openspec/changes/add-dbt-111-parity/spike-notes.md`
- [x] 1.3 If conflicts observed → keep `MicrobatchConcurrency: Unsupported` decision; if no conflicts → escalate to user before changing scope

## 2. Adapter capability declarations

- [x] 2.1 In `dbt/adapters/exasol/impl.py`, expand `_capabilities` to declare every `Capability` enum value (use `dir(Capability)` to enumerate against installed dbt-adapters)
- [x] 2.2 Add `Capability.GetCatalogForSingleRelation: CapabilitySupport(support=Support.Full)`
- [x] 2.3 Add `Capability.TableLastModifiedMetadataBatch: CapabilitySupport(support=Support.Full)`
- [x] 2.4 Add `Capability.MicrobatchConcurrency: CapabilitySupport(support=Support.Unsupported)` with an inline `# Exasol uses optimistic transaction-conflict detection ...` comment
- [x] 2.5 Add a unit test in `tests/unit/test_impl.py` asserting `ExasolAdapter._capabilities` declares every value of `Capability`

## 3. Single-relation catalog implementation

- [x] 3.1 Create `dbt/include/exasol/macros/get_catalog_for_single_relation.sql` with `exasol__get_catalog_for_single_relation(information_schema, relation)` macro that delegates to the existing `exasol__get_catalog_relations` (passing a single-element `relations` list) so the relation-filtered `EXA_ALL_OBJECTS` / `EXA_ALL_COLUMNS` where-clause logic is reused rather than duplicated — guaranteeing the same column shape as `exasol__get_catalog`
- [x] 3.2 In `impl.py`, replace `get_catalog_for_single_relation` `NotImplementedError` body with a call to `self.execute_macro("get_catalog_for_single_relation", kwargs={"relation": relation})` and `_catalog_filter_table` post-processing matching the existing `get_catalog` path
- [x] 3.3 Return `None` from the method when the macro yields zero rows
- [x] 3.4 Add a unit test asserting same-shape output between single-relation and full-schema paths (mock the cursor)
- [x] 3.5 Add a functional test under `tests/functional/adapter/relations/test_single_relation_catalog.py` that creates one table, calls the adapter method directly, and asserts metadata + columns are populated

## 4. Batched last-modified metadata

- [x] 4.1 `exasol__get_relation_last_modified` already loops over many relations, so the batched path works; switch its source from `SYS.EXA_USER_OBJECTS` to `SYS.EXA_ALL_OBJECTS` (map `root_name`/`object_name`/`object_type`/`last_commit`) so cross-owner sources resolve and `TableLastModifiedMetadataBatch: Full` is honest
- [x] 4.2 Update the existing functional test `tests/functional/adapter/test_get_relation_last_modified.py` to exercise the batched path with ≥3 relations spanning more than one schema/owner

## 5. Behavior-flag scaffolding

- [x] 5.1 In `impl.py`, override `_behavior_flags` property to `return []` with a docstring documenting the override pattern and linking to `dbt.adapters.base.impl._behavior_flags`
- [x] 5.2 Add a unit test asserting `ExasolAdapter(...)._behavior_flags == []`

## 6. Catalog-integrations graceful handling

- [x] 6.1 Add a functional test `tests/functional/adapter/catalog_integrations/test_catalog_integration.py` subclassing `BaseCatalogIntegrationValidation` with two fixtures: (a) `catalogs.yml` present but no model uses it → run succeeds; (b) one model sets `config(catalog='foo')` → run fails with `DbtRuntimeError` mentioning Exasol
- [x] 6.2 If test 6.1(b) currently fails with a non-clear traceback, add an `exasol__build_catalog_relation` macro or override `ExasolAdapter.build_catalog_relation` to raise the clear error
- [x] 6.3 Confirm `CATALOG_INTEGRATIONS = []` is sufficient (no override needed) and document the decision in a code comment in `impl.py`

## 7. Upstream clone tests

- [x] 7.1 Create `tests/functional/adapter/dbt_clone/__init__.py` and `test_clone.py` subclassing `BaseCloneNotPossible`, `BaseCloneSameSourceAndTarget`, `BaseCloneSameTargetAndState`
- [x] 7.2 Run subclasses against Exasol; for any failures, either fix or document a skip with a reason in the test file
- [x] 7.3 Document the outcome (clone-as-view semantics) in the parity matrix entry

## 8. Upstream snapshot tests for 1.9+ features

- [x] 8.1 Add `tests/functional/adapter/simple_snapshot/test_upstream_hard_deletes.py` subclassing `dbt.tests.adapter.simple_snapshot.test_ephemeral_snapshot_hard_deletes` test class(es)
- [x] 8.2 Add `tests/functional/adapter/simple_snapshot/test_upstream_valid_to_current.py` subclassing the `new_record_dbt_valid_to_current` test class(es)
- [x] 8.3 Run subclasses; resolve or document skips for any Exasol-specific failures (e.g. quoting, identifier casing)
- [x] 8.4 Keep existing custom tests (`test_snapshot_hard_deletes.py`, `test_snapshot_valid_to_current.py`) — they cover Exasol-specific concerns

## 9. Upstream sample-mode test

- [x] 9.1 Add an explicit subclass of `BaseSampleModeTest` at `tests/functional/adapter/sample_mode/test_sample_mode.py` (the existing test in `incremental/test_sample_mode.py` indirectly exercises it but is not discoverable as a parity claim)
- [x] 9.2 Keep both files; add a comment in each cross-referencing the other (`incremental/test_sample_mode.py` ↔ `sample_mode/test_sample_mode.py`) so the duplication is intentional and discoverable, with the `sample_mode/` subclass serving as the `pytest --collect-only` parity marker

## 10. Hard-deprecation audit in CI

- [x] 10.1 Create a minimal fixture project under `tests/fixtures/deprecation_audit/` with `dbt_project.yml`, `profiles.yml` template, one model, one source, one snapshot — exercising adapter-owned macros
- [x] 10.2 Add a nox session `lint:deprecations` in `noxfile.py` that sets `DBT_WARN_ERROR=true` and runs `dbt parse` against the fixture
- [x] 10.3 Run locally; fix any deprecations triggered by adapter-owned macros (e.g. add `+` prefix to config keys, fix `dispatch` patterns)
- [x] 10.4 Add `lint:deprecations` to the `mise run check` target and the GitHub Actions workflow

## 11. README parity matrix

- [x] 11.1 Add a "dbt-core version parity" section to `README.md` with a markdown table covering: microbatch, microbatch concurrency, sample mode, empty model, UDFs (SQL), UDAFs (Python), Python models, materialized views, snapshot hard_deletes, snapshot dbt_valid_to_current, dbt clone, catalog integrations / Iceberg, unit testing, single-relation catalog, batched last-modified, get_columns_in_relation, persist_docs, grants
- [x] 11.2 Use the four states defined in the spec: `✅`, `⚠️`, `❌ (platform)`, `❌ (not yet)`
- [x] 11.3 For every `❌ (platform)` entry, add a one-sentence "Why" footnote under the matrix
- [x] 11.4 Cross-link from `CHANGELOG.md` (or release notes) to the matrix on next release

## 12. Version assertion

- [x] 12.1 Bump `dbt/adapters/exasol/__version__.py` `VERSION` from `1.10.6` to `1.11.0`, then add a unit test asserting that `dbt.adapters.exasol.__version__` starts with `1.11.` (catches forgotten version bumps)
- [x] 12.2 Confirm `pyproject.toml` `version` (`1.11.0`) matches `__version__.py` `VERSION`

## 13. Validation & release prep

- [x] 13.1 Run `mise run check` (format, lint, typing) — all green
- [x] 13.2 Run `mise run test` (unit + integration) — all green
- [x] 13.3 Run `openspec validate add-dbt-111-parity --strict`
- [x] 13.4 Update `CHANGELOG.md` (or release notes) with a "1.11 parity" entry summarising the matrix and pointing to the spec
- [x] 13.5 Verify the in-flight `add-udf-function-support` change has archived before this one merges; if not, mark UDF/UDAF rows in the parity matrix as `⚠️ Conditional (in flight)`
