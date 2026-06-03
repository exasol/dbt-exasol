## 1. Spike: verify microbatch concurrency assumption

- [ ] 1.1 Write a manual repro script under `scripts/spikes/microbatch_concurrency.py` that opens two `pyexasol` connections and runs disjoint DELETE+INSERT statements against the same test table concurrently
- [ ] 1.2 Document the observed outcome (transaction conflict OR success) in `openspec/changes/add-dbt-111-parity/spike-notes.md`
- [ ] 1.3 If conflicts observed → keep `MicrobatchConcurrency: Unsupported` decision; if no conflicts → escalate to user before changing scope

## 2. Adapter capability declarations

- [ ] 2.1 In `dbt/adapters/exasol/impl.py`, expand `_capabilities` to declare every `Capability` enum value (use `dir(Capability)` to enumerate against installed dbt-adapters)
- [ ] 2.2 Add `Capability.GetCatalogForSingleRelation: CapabilitySupport(support=Support.Full)`
- [ ] 2.3 Add `Capability.TableLastModifiedMetadataBatch: CapabilitySupport(support=Support.Full)`
- [ ] 2.4 Add `Capability.MicrobatchConcurrency: CapabilitySupport(support=Support.Unsupported)` with an inline `# Exasol uses optimistic transaction-conflict detection ...` comment
- [ ] 2.5 Add a unit test in `tests/unit/test_impl.py` asserting `ExasolAdapter._capabilities` declares every value of `Capability`

## 3. Single-relation catalog implementation

- [ ] 3.1 Create `dbt/include/exasol/macros/get_catalog_for_single_relation.sql` with `exasol__get_catalog_for_single_relation(information_schema, relation)` macro that filters `EXA_ALL_COLUMNS` + `EXA_ALL_OBJECTS` to one `(schema, identifier)` pair, returning the same column shape as `exasol__get_catalog`
- [ ] 3.2 In `impl.py`, replace `get_catalog_for_single_relation` `NotImplementedError` body with a call to `self.execute_macro("get_catalog_for_single_relation", kwargs={"relation": relation})` and `_catalog_filter_table` post-processing matching the existing `get_catalog` path
- [ ] 3.3 Return `None` from the method when the macro yields zero rows
- [ ] 3.4 Add a unit test asserting same-shape output between single-relation and full-schema paths (mock the cursor)
- [ ] 3.5 Add a functional test under `tests/functional/adapter/relations/test_single_relation_catalog.py` that creates one table, calls the adapter method directly, and asserts metadata + columns are populated

## 4. Batched last-modified metadata

- [ ] 4.1 Verify whether `exasol__get_relation_last_modified` already supports an `IN` predicate over many relations; if not, extend it
- [ ] 4.2 If extended, update the existing functional test `tests/functional/adapter/test_get_relation_last_modified.py` to exercise the batched path with ≥3 relations

## 5. Behavior-flag scaffolding

- [ ] 5.1 In `impl.py`, override `_behavior_flags` property to `return []` with a docstring documenting the override pattern and linking to `dbt.adapters.base.impl._behavior_flags`
- [ ] 5.2 Add a unit test asserting `ExasolAdapter(...)._behavior_flags == []`

## 6. Catalog-integrations graceful handling

- [ ] 6.1 Add a functional test `tests/functional/adapter/catalog_integrations/test_catalog_integration.py` subclassing `BaseCatalogIntegrationValidation` with two fixtures: (a) `catalogs.yml` present but no model uses it → run succeeds; (b) one model sets `config(catalog='foo')` → run fails with `DbtRuntimeError` mentioning Exasol
- [ ] 6.2 If test 6.1(b) currently fails with a non-clear traceback, add an `exasol__build_catalog_relation` macro or override `ExasolAdapter.build_catalog_relation` to raise the clear error
- [ ] 6.3 Confirm `CATALOG_INTEGRATIONS = []` is sufficient (no override needed) and document the decision in a code comment in `impl.py`

## 7. Upstream clone tests

- [ ] 7.1 Create `tests/functional/adapter/dbt_clone/__init__.py` and `test_clone.py` subclassing `BaseCloneNotPossible`, `BaseCloneSameSourceAndTarget`, `BaseCloneSameTargetAndState`
- [ ] 7.2 Run subclasses against Exasol; for any failures, either fix or document a skip with a reason in the test file
- [ ] 7.3 Document the outcome (clone-as-view semantics) in the parity matrix entry

## 8. Upstream snapshot tests for 1.9+ features

- [ ] 8.1 Add `tests/functional/adapter/simple_snapshot/test_upstream_hard_deletes.py` subclassing `dbt.tests.adapter.simple_snapshot.test_ephemeral_snapshot_hard_deletes` test class(es)
- [ ] 8.2 Add `tests/functional/adapter/simple_snapshot/test_upstream_valid_to_current.py` subclassing the `new_record_dbt_valid_to_current` test class(es)
- [ ] 8.3 Run subclasses; resolve or document skips for any Exasol-specific failures (e.g. quoting, identifier casing)
- [ ] 8.4 Keep existing custom tests (`test_snapshot_hard_deletes.py`, `test_snapshot_valid_to_current.py`) — they cover Exasol-specific concerns

## 9. Upstream sample-mode test

- [ ] 9.1 Add an explicit subclass of `BaseSampleModeTest` at `tests/functional/adapter/sample_mode/test_sample_mode.py` (the existing test in `incremental/test_sample_mode.py` indirectly exercises it but is not discoverable as a parity claim)
- [ ] 9.2 Confirm both files cover distinct cases; consolidate or cross-reference as needed

## 10. Hard-deprecation audit in CI

- [ ] 10.1 Create a minimal fixture project under `tests/fixtures/deprecation_audit/` with `dbt_project.yml`, `profiles.yml` template, one model, one source, one snapshot — exercising adapter-owned macros
- [ ] 10.2 Add a nox session `lint:deprecations` in `noxfile.py` that sets `DBT_WARN_ERROR=true` and runs `dbt parse` against the fixture
- [ ] 10.3 Run locally; fix any deprecations triggered by adapter-owned macros (e.g. add `+` prefix to config keys, fix `dispatch` patterns)
- [ ] 10.4 Add `lint:deprecations` to the `mise run check` target and the GitHub Actions workflow

## 11. README parity matrix

- [ ] 11.1 Add a "dbt-core version parity" section to `README.md` with a markdown table covering: microbatch, microbatch concurrency, sample mode, empty model, UDFs (SQL), UDAFs (Python), Python models, materialized views, snapshot hard_deletes, snapshot dbt_valid_to_current, dbt clone, catalog integrations / Iceberg, unit testing, single-relation catalog, batched last-modified, get_columns_in_relation, persist_docs, grants
- [ ] 11.2 Use the four states defined in the spec: `✅`, `⚠️`, `❌ (platform)`, `❌ (not yet)`
- [ ] 11.3 For every `❌ (platform)` entry, add a one-sentence "Why" footnote under the matrix
- [ ] 11.4 Cross-link from `CHANGELOG.md` (or release notes) to the matrix on next release

## 12. Version assertion

- [ ] 12.1 Add a unit test asserting that `dbt.adapters.exasol.__version__` starts with `1.11.` (catches forgotten version bumps)
- [ ] 12.2 Confirm `pyproject.toml` `[project] version` matches `__version__.py`

## 13. Validation & release prep

- [ ] 13.1 Run `mise run check` (format, lint, typing) — all green
- [ ] 13.2 Run `mise run test` (unit + integration) — all green
- [ ] 13.3 Run `openspec validate add-dbt-111-parity --strict`
- [ ] 13.4 Update `CHANGELOG.md` (or release notes) with a "1.11 parity" entry summarising the matrix and pointing to the spec
- [ ] 13.5 Verify the in-flight `add-udf-function-support` change has archived before this one merges; if not, mark UDF/UDAF rows in the parity matrix as `⚠️ Conditional (in flight)`
