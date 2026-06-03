## Context

`dbt-exasol` already runs against `dbt-core 1.11.9` and `dbt-adapters 1.23.0`, and prior phases (`phase-1.10-phase1/2/3`) brought in microbatch and sample mode. What never happened is a **systematic audit** against the 1.11 reference adapter (dbt-snowflake) plus an **explicit public claim** of which 1.11 features Exasol supports.

The de-risking spike behind this proposal established four findings:

1. Most "1.11 features" are functionally present but invisible (no capability declared, no upstream test subclassed, no doc).
2. `get_catalog_for_single_relation` is the one concrete code gap — currently `raise NotImplementedError`.
3. `MicrobatchConcurrency` is the one place where Exasol's platform model materially differs from Snowflake's: declaring it would be unsafe.
4. Hard deprecations in 1.11 are still warnings by default, but become errors under `warn-error: true` — adapter-owned macros must be clean.

This design covers the architectural choices that flow from those findings. Line-by-line implementation belongs in tasks.md.

## Goals / Non-Goals

**Goals:**
- Produce a single, public, testable parity claim for dbt-core 1.11 on Exasol.
- Make every parity claim *provable* by subclassing the corresponding `dbt-tests-adapter` 1.11 test class.
- Make every non-parity claim *explained* with platform reasoning users can read.
- Implement the small framework hooks that are missing (single-relation catalog, batched last-modified) so we get the same code-paths Snowflake gets.
- Establish a precedent for how future minor-version bumps (1.12, 1.13, …) are claimed.

**Non-Goals:**
- Implementing Python models, materialized views, dynamic tables, Iceberg/catalog integrations — these are platform-blocked and called out as such.
- Making microbatch concurrent — a future change can revisit this with a different strategy.
- Re-litigating decisions from prior 1.9/1.10 phases (snapshot features, sample mode, microbatch strategy) — those are accepted as-is; this change only proves them via upstream tests.
- Changing the UDF/UDAF work in `add-udf-function-support` — that change is the source of truth for functions.

## Decisions

### D1. Single new capability spec, not per-feature specs

**Decision:** Introduce one new capability `dbt-core-version-parity` rather than separate `adapter-capabilities`, `catalog-integrations`, `clone-support`, `snapshot-features` specs.

**Rationale:** All the requirements being captured share one underlying concern — "what does it mean to claim dbt-core minor-version X parity?". Splitting them would scatter the claim across multiple spec files and make future bumps (1.12, 1.13) painful to update. The existing seven specs (`atomic-ctas`, `cicd`, …) describe *Exasol behaviours* that are version-independent and remain untouched.

**Alternatives considered:**
- One spec per feature (clone, snapshot, catalog, capability matrix). Rejected — too granular for the actual coupling.
- Modify an existing spec (e.g. `relation-management`). Rejected — would mix version-independent and version-dependent requirements in one file.

### D2. Capability declarations are part of the spec, not just code

**Decision:** The `dbt-core-version-parity` spec lists each `Capability.*` enum value with the required `Support` level for Exasol and a one-line justification. The Python `_capabilities` dict in `impl.py` is the implementation; the spec is the contract.

**Rationale:** Capability declarations are observable adapter behaviour (dbt-core branches on them) — they deserve spec coverage like any other requirement. This also catches the case where an adapter quietly downgrades a capability without anyone noticing.

### D3. Microbatch concurrency is `Unsupported`, not `Unknown`

**Decision:** Explicitly declare `Capability.MicrobatchConcurrency: Support.Unsupported` rather than leaving it undeclared (which would default to `Unknown`).

**Rationale:** `Unknown` invites future contributors to "just turn it on". An explicit `Unsupported` with an inline comment forces them to read why first.

**The why:** Exasol uses optimistic transaction-conflict detection at table granularity. Two concurrent transactions performing `DELETE … WHERE event_time IN [d1, d2)` + `INSERT INTO target …` against the same target table will, with high probability, hit a transaction conflict and one will abort with `"transaction conflict for transaction X"`. Snowflake avoids this because its microbatch DELETE+INSERT runs as a single auto-committed statement with snapshot isolation; Exasol's transaction model requires explicit COMMIT and detects write-write conflicts after the fact.

**Alternatives considered:**
- Per-batch `BEGIN`/`COMMIT` blocks with retry-on-conflict. Rejected as out-of-scope; would require harness changes in `ExasolConnectionManager` and is its own design problem.
- Switch microbatch to `MERGE`. Possible future work — would need `MERGE` to be safe under concurrency on Exasol, which is itself unverified.

### D4. Catalog integrations: graceful no-op, not an error on parse

**Decision:** A `catalogs.yml` file in the user's project must parse without error on Exasol. Only when a model sets `config(catalog=...)` does the run fail — with a clear `DbtRuntimeError` from `build_catalog_relation` (or an adapter-side override) stating "Exasol does not support catalog integrations".

**Rationale:** Users running dbt against multiple warehouses in one repository (common pattern) shouldn't have to delete `catalogs.yml` for Exasol runs. Failing only when a model actively requests a catalog is the principle of least surprise.

**Implementation:** `CATALOG_INTEGRATIONS = []` (the inherited default) already gives us "parse succeeds". The error-on-use path may already work via the base class — the smoke test will tell us whether we need an adapter-level override or not.

### D5. Subclass upstream tests instead of writing new ones, where possible

**Decision:** For clone, snapshot 1.9+ features, sample mode, and catalog integrations, subclass `dbt.tests.adapter.*` base classes rather than writing custom tests.

**Rationale:** The upstream test class IS the parity contract. If we write our own equivalent tests, we may drift from the contract over time and lose the "passes the upstream suite" claim. Custom tests stay for Exasol-specific concerns (e.g. existing `test_snapshot_hard_deletes.py` exercises Exasol-specific column behaviour) but the upstream subclasses become primary.

### D6. Behavior-flag scaffolding now, real flags later

**Decision:** Override `_behavior_flags` to return `[]` with a docstring explaining the pattern. No actual flags are introduced in this change.

**Rationale:** Behavior flags are how dbt-labs ships opt-in behaviour changes (e.g. Snowflake's `enable_iceberg_materializations`). We don't need any *today*, but having the override slot present, documented, and grep-able lowers the cost of adding the first one (and signals reviewers we know it exists).

### D7. Hard-deprecation audit runs in CI, not just locally

**Decision:** Add a nox/CI step that runs `dbt parse` against a sample project with `warn-error: true`. Fails the build if any adapter-owned macro or fixture triggers a deprecation.

**Rationale:** A spot-check today catches today's issues; an automated check catches regressions from future dbt-core minor bumps. The cost is one extra ~5-second CI step.

**Alternatives considered:** Adding to `lint:code`. Rejected — `lint:code` doesn't currently invoke dbt. Cleaner as its own step.

### D8. Parity matrix lives in README.md, not a separate doc

**Decision:** The user-facing parity matrix goes into `README.md` under a "dbt-core version parity" section, modelled on dbt-labs' adapter feature matrix.

**Rationale:** First place users look. A separate `docs/1.11-parity.md` could be added later if the matrix grows.

## Risks / Trade-offs

[Risk] Declaring `GetCatalogForSingleRelation: Full` exposes a code path that previously fell back to whole-schema catalog queries — any bug in the new macro affects `dbt docs generate` for single-model selection.
→ Mitigation: implementation is a thin filter on top of the existing `exasol__get_catalog` macro; subclass the upstream catalog tests; add a unit test asserting identical column-list shape for single vs. all-relations paths.

[Risk] The catalog-integrations smoke test may surface a *real* incompatibility (e.g. dbt-core requires the adapter to register at least one no-op integration to parse `catalogs.yml`).
→ Mitigation: the smoke test is the spike. If it fails, we add a minimal `NoOpCatalogIntegration` subclass and document it. Scope expands by ~1 task; no fundamental redesign.

[Risk] `warn-error: true` in the new CI step may surface deprecations in third-party packages (e.g. `dbt-utils` patterns) that we can't fix.
→ Mitigation: the audit runs only against an adapter-controlled fixture project that does NOT install third-party packages. Scope is adapter-owned macros and example yamls only.

[Risk] Upstream test subclasses may rely on platform features Exasol lacks (e.g. case-sensitive identifier comparison), causing the upstream test to fail for unrelated reasons.
→ Mitigation: each subclass is added one-by-one, run locally, and the test is either accepted, parameterized, or skipped with a documented reason in the test file. If skipping, the parity matrix entry downgrades from `✅ Supported` to `⚠️ Conditional`.

[Risk] The `dbt-core-version-parity` spec is unusual — it talks about *meta-requirements* (capability dict shape, test subclasses) rather than database behaviour. May confuse future reviewers expecting traditional behavioural specs.
→ Mitigation: spec intro paragraph explicitly frames it as a meta-spec covering the version-compatibility contract. Future minor-version bumps create delta files against this same spec.

[Risk] Microbatch-concurrency `Unsupported` declaration may be wrong if Exasol's transaction-conflict behaviour is more permissive than we assume (e.g. if DELETE+INSERT on disjoint row sets doesn't actually conflict).
→ Mitigation: a small spike — two threads each microbatching a non-overlapping date window into the same target — is included as a task. If it succeeds reliably, we upgrade the declaration to `Full` and add it as a test. If it fails (the expected outcome), the declaration stays and we keep the spike as the rationale.

## Migration Plan

No user-facing migration. The change is additive at the adapter level:

1. Land `add-udf-function-support` first (already complete per task list).
2. Land this change.
3. Bump `__version__.py` patch version on release.
4. Update README parity matrix.
5. Future minor-version work (`add-dbt-112-parity`, etc.) follows the same template: spike → declare → subclass → document.

## Open Questions

- Should the parity matrix in README.md cover *all* dbt-core features (including ones unchanged for years like seeds, snapshots) or only 1.11-era features? **Tentative answer:** all features, because the matrix's primary audience is users comparing warehouses; they don't care which dbt-core version introduced what.
- Does `dbt-tests-adapter` 1.11 ship a top-level "version-parity" suite that we should subclass wholesale? **To verify during tasks** — if yes, that's one subclass instead of many.
- Is there a CI matrix entry we should add for `--warn-error` runs of the integration suite (not just `dbt parse`)? **Deferred** — could be its own change; this one only commits to `dbt parse`.
