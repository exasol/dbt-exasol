## ADDED Requirements

> **Note:** This is a meta-spec. It defines the contract by which `dbt-exasol` claims compatibility with a given `dbt-core` minor version. Unlike behavioural specs (e.g. `quoting`, `relation-management`), the requirements here are *about* the adapter's declarations and test coverage rather than about database behaviour. Future minor-version bumps (1.12, 1.13, …) add delta files against this same spec.

### Requirement: Adapter declares an explicit dbt-core target version

The adapter SHALL declare its target dbt-core minor version in exactly one place that is machine-readable and discoverable.

#### Scenario: Version is declared in pyproject.toml
- **WHEN** a developer reads `pyproject.toml`
- **THEN** the `project.version` field SHALL match the `dbt-core` minor version (e.g. `1.11.x` for dbt-core 1.11), and the `dependencies` array SHALL pin `dbt-core>=<minor>.0` and `dbt-adapters>=<minor>.0`

#### Scenario: Version is exported in code
- **WHEN** a caller imports `dbt.adapters.exasol.__version__`
- **THEN** the value SHALL equal the version in `pyproject.toml`

### Requirement: Capability matrix is declared and matches the parity claim

The adapter SHALL declare every `dbt.adapters.capability.Capability` enum value with an explicit `CapabilitySupport` entry, OR explicitly omit it with a documented reason. No capability may be left implicitly `Unknown`.

#### Scenario: All capabilities are declared
- **WHEN** a developer inspects `ExasolAdapter._capabilities`
- **THEN** every value in `Capability` enum SHALL appear as a key, with `Support.Full`, `Support.Versioned`, `Support.Unsupported`, or (only with an inline `# justification:` comment) absent

#### Scenario: SchemaMetadataByRelations is Full
- **WHEN** dbt-core probes `adapter.supports(Capability.SchemaMetadataByRelations)`
- **THEN** the result SHALL be `True` and `get_catalog_by_relations` SHALL be implemented

#### Scenario: TableLastModifiedMetadata is Full
- **WHEN** dbt-core probes `adapter.supports(Capability.TableLastModifiedMetadata)`
- **THEN** the result SHALL be `True` and source freshness via metadata SHALL work without per-table SELECTs

#### Scenario: TableLastModifiedMetadataBatch is Full
- **WHEN** dbt-core probes `adapter.supports(Capability.TableLastModifiedMetadataBatch)`
- **THEN** the result SHALL be `True` and the batched freshness path SHALL query `EXA_ALL_OBJECTS` with an `IN` predicate for multiple tables in one round-trip

#### Scenario: GetCatalogForSingleRelation is Full
- **WHEN** dbt-core probes `adapter.supports(Capability.GetCatalogForSingleRelation)`
- **THEN** the result SHALL be `True` and `ExasolAdapter.get_catalog_for_single_relation(relation)` SHALL return a populated `CatalogTable` without scanning the entire schema

#### Scenario: MicrobatchConcurrency is explicitly Unsupported
- **WHEN** dbt-core probes `adapter.supports(Capability.MicrobatchConcurrency)`
- **THEN** the result SHALL be `False`, the capability dict SHALL contain `MicrobatchConcurrency: CapabilitySupport(support=Support.Unsupported)`, and a code comment SHALL reference Exasol's transaction-conflict semantics on shared-target DELETE+INSERT

### Requirement: Single-relation catalog lookup is implemented

The adapter SHALL implement `get_catalog_for_single_relation(relation)` returning a `CatalogTable` for one specific relation without scanning unrelated schemas or relations.

#### Scenario: Returns catalog metadata for an existing table
- **WHEN** `get_catalog_for_single_relation` is called for an existing Exasol table
- **THEN** it SHALL return a `CatalogTable` with `metadata`, `columns` (in ordinal position order), and `stats` populated, filtered to that single `(schema, identifier)` pair

#### Scenario: Returns None for a non-existent relation
- **WHEN** `get_catalog_for_single_relation` is called for a relation that does not exist in Exasol
- **THEN** it SHALL return `None` (not raise) so dbt-core's caller can handle the absence gracefully

### Requirement: Catalog integrations are handled gracefully

The adapter SHALL allow projects that declare a `catalogs.yml` to parse and run, provided no model in the run actively requests a catalog. Active requests SHALL fail with a clear, adapter-specific error.

#### Scenario: Project with unused catalogs.yml parses and runs
- **WHEN** a user runs `dbt parse` or `dbt run` against a project containing a non-empty `catalogs.yml` and no model sets `config(catalog=...)`
- **THEN** the run SHALL succeed without warning or error from the adapter

#### Scenario: Model requesting a catalog fails with a clear error
- **WHEN** a model includes `{{ config(catalog='some_iceberg_catalog') }}`
- **THEN** the run SHALL fail with a `DbtRuntimeError` whose message identifies Exasol and states that catalog integrations are not supported on this platform

### Requirement: Microbatch concurrency is documented as unsupported

The adapter SHALL NOT execute microbatch incremental batches concurrently across threads against the same target relation, and SHALL document this constraint in user-facing docs.

#### Scenario: Concurrent batches against shared target are serialized
- **WHEN** dbt-core schedules microbatch batches for a model whose adapter declares `MicrobatchConcurrency: Unsupported`
- **THEN** batches SHALL run sequentially (dbt-core's existing behaviour for unsupported concurrency), regardless of the project's thread count

#### Scenario: Constraint is documented
- **WHEN** a user reads the README parity matrix
- **THEN** microbatch concurrency SHALL appear with a "Not supported" marker and a one-sentence reason citing transaction-conflict semantics

### Requirement: Upstream test classes prove the parity claim

For every capability or feature claimed as supported, the adapter's test suite SHALL subclass the corresponding `dbt-tests-adapter` base class at the same minor version, and that subclass SHALL pass against a real Exasol instance in CI.

#### Scenario: Clone tests are subclassed
- **WHEN** the test suite is collected via `pytest --collect-only`
- **THEN** subclasses of `BaseCloneNotPossible`, `BaseCloneSameSourceAndTarget`, and `BaseCloneSameTargetAndState` SHALL be present under `tests/functional/adapter/dbt_clone/`

#### Scenario: Snapshot 1.9+ feature tests are subclassed
- **WHEN** the test suite is collected
- **THEN** subclasses of the upstream `test_ephemeral_snapshot_hard_deletes` and `new_record_dbt_valid_to_current` test classes SHALL be present under `tests/functional/adapter/simple_snapshot/`, in addition to existing Exasol-specific snapshot tests

#### Scenario: Sample mode is subclassed
- **WHEN** the test suite is collected
- **THEN** a subclass of `dbt.tests.adapter.sample_mode.test_sample_mode.BaseSampleModeTest` SHALL be present and visible in collection

#### Scenario: Catalog integrations smoke test is subclassed
- **WHEN** the test suite is collected
- **THEN** a subclass of `BaseCatalogIntegrationValidation` SHALL be present and SHALL assert both the graceful-no-op and the clear-error paths defined above

### Requirement: Behavior-flag scaffolding is present

The adapter SHALL override `_behavior_flags` even if returning an empty list, with a docstring describing the override pattern for future flags.

#### Scenario: Empty flags list is returned
- **WHEN** dbt-core constructs an `ExasolAdapter` instance
- **THEN** `adapter._behavior_flags` SHALL return `[]` without raising, and the property SHALL carry a docstring describing how to add platform-specific flags

### Requirement: Hard-deprecation audit runs in CI

The CI pipeline SHALL include a step that runs `dbt parse` against an adapter-owned fixture project with `warn-error: true`, failing the build if any adapter-owned macro or fixture triggers a dbt-core deprecation.

#### Scenario: Audit passes on clean code
- **WHEN** the CI pipeline runs `nox -s lint:deprecations` (or equivalent) against the current adapter macros and example fixtures
- **THEN** the step SHALL exit with code 0

#### Scenario: Audit fails when a macro emits a deprecation
- **WHEN** an adapter-owned macro or fixture triggers any `dbt.deprecations.*Deprecation` event
- **THEN** the step SHALL exit non-zero with the deprecation name in the output

### Requirement: Public parity matrix exists and is current

The README SHALL include a parity matrix listing every dbt-core feature relevant to adapter authors, with one of four states: `✅ Supported`, `⚠️ Conditional`, `❌ Not supported (platform)`, `❌ Not supported (not yet)`. The matrix SHALL be updated as part of any change that alters a capability declaration.

#### Scenario: Matrix exists in README
- **WHEN** a reader opens `README.md`
- **THEN** a section titled "dbt-core version parity" (or equivalent) SHALL be present and list at minimum: microbatch, microbatch concurrency, sample mode, empty model, UDFs (SQL), UDAFs (Python), Python models, materialized views, snapshots with `hard_deletes`, snapshots with `dbt_valid_to_current`, dbt clone, catalog integrations / Iceberg, unit testing, single-relation catalog, batched last-modified metadata

#### Scenario: Matrix entries match capability declarations
- **WHEN** an entry in the parity matrix says `✅ Supported` for a feature backed by a `Capability` enum value
- **THEN** the corresponding entry in `ExasolAdapter._capabilities` SHALL be `Support.Full` or `Support.Versioned`

### Requirement: Platform-blocked features are documented with reasons

Features that dbt-core ships but Exasol cannot support due to platform limitations SHALL be listed in the parity matrix with state `❌ Not supported (platform)` and a one-sentence reason linked from the matrix.

#### Scenario: Python models are documented as platform-blocked
- **WHEN** a reader inspects the Python-models entry in the parity matrix
- **THEN** the entry SHALL state platform non-support and reference Exasol's lack of a Python execution sandbox outside UDF SCRIPTs

#### Scenario: Materialized views are documented as platform-blocked
- **WHEN** a reader inspects the materialized-views entry
- **THEN** the entry SHALL state platform non-support and reference Exasol's lack of an MV primitive

#### Scenario: Iceberg / catalog integrations are documented as platform-blocked
- **WHEN** a reader inspects the catalog-integrations entry
- **THEN** the entry SHALL state platform non-support and reference Exasol's lack of external-table-format integration
