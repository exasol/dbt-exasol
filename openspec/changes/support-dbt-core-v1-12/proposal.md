## Why

dbt Core v1.12 ships adapter-facing changes (the `--empty` flag for `dbt seed`, automatic `latest_version_pointer` views for versioned models, an `on_error` model config, and a broad move from raw Python exceptions to dbt exceptions). `dbt-exasol` currently pins `dbt-core>=1.10.0` / `dbt-adapters>=1.10.0` and resolves to dbt-core 1.11.9 + dbt-adapters 1.23.0. We need the adapter validated and released against the v1.12 line so Exasol users can upgrade. dbt-core 1.12 is currently **beta-only** on PyPI (`1.12.0b2`), and `dbt-core 1.12.0b2` requires `dbt-adapters>=1.24.1`, so the dependency bump is mandatory to install it at all.

## What Changes

- Bump dependencies: `dbt-core>=1.12.0b1,<1.13`, `dbt-adapters>=1.24.1`, and (dev) `dbt-tests-adapter>=1.20.0`. Note `dbt-adapters` / `dbt-tests-adapter` are version-decoupled from dbt-core — their v1.12 features live in the 1.24.x / 1.20.x lines, **not** a "1.12" tag.
- Add `[tool.uv] prerelease = "explicit"` so uv installs the dbt-core 1.12 beta only because its specifier explicitly carries a pre-release marker — without globally enabling pre-releases for every dependency. The `<1.13` cap prevents accidentally resolving to `dbt-core 2.0.0a1` (the Rust rewrite) under pre-release allowance.
- Refresh `uv.lock` against the new constraints.
- Harden `ExasolAdapter.convert_number_type` so a zero-row agate table (produced by `dbt seed --empty`, which loads the CSV then calls `table.limit(0)`) does not silently create decimal columns as `integer`. `agate.MaxPrecision` returns `0` on an empty column, so the current code infers `integer` for every numeric column under `--empty`; the hardened version falls back to `float` (or honors a `column_types` override) when the table has no rows.
- Add adapter test coverage by subclassing the new `BaseTestEmptySeedFlag` from `dbt-tests-adapter` (it ships only as a `Base...` class, so it must be opted into), plus a functional test for `latest_version_pointer` on a versioned model.
- Minor hardening: replace the three raw `RuntimeError(_UNSET_STATEMENT_ERROR)` raises in `ExasolCursor` (`fetchone`/`fetchmany`/`fetchall`) with `dbt_common.exceptions.DbtRuntimeError`, aligning with v1.12's exception-handling philosophy.

## Capabilities

### New Capabilities
- `dbt-version-support`: Defines the supported dbt-core / dbt-adapters / dbt-tests-adapter version ranges for v1.12 compatibility and the uv pre-release resolution policy that lets the project install the dbt-core 1.12 beta without pulling unrelated pre-releases or the dbt-core 2.0 alpha.
- `seed-materialization`: Defines Exasol seed behavior under `dbt seed --empty` — tables are created with the correct schema and zero rows, and numeric column types are not degraded (decimal must not become integer) when the seed is materialized with no rows.

### Modified Capabilities
<!-- None. The latest_version_pointer feature reuses the existing view materialization with no requirement change, and the ExasolCursor exception swap is an implementation-level hardening with no spec-level requirement change. -->

## Impact

- **Dependencies**: `pyproject.toml` (`dependencies`, `dependency-groups.dev`, new `[tool.uv]` table), `uv.lock`.
- **Adapter code**: `dbt/adapters/exasol/impl.py` (`convert_number_type`), `dbt/adapters/exasol/connections.py` (`ExasolCursor.fetchone/fetchmany/fetchall`).
- **Tests**: new functional tests under `tests/functional/adapter/` for empty seeds (`BaseTestEmptySeedFlag`) and `latest_version_pointer`; existing seed tests (`tests/functional/adapter/simple_seed/`) re-run against 1.12.
- **No new abstract methods required**: verified — `ExasolAdapter` imports against dbt-adapters 1.24.2 with zero unimplemented abstract methods. `Capability.CatalogsV2` is opt-in and out of scope.
- **CI / tox**: the `uv-venv-lock-runner` tox runner consumes the refreshed lock; the pre-release policy must resolve in CI the same way it does locally.
- **Known limitation (documented, not fixed here unless trivial)**: `dbt seed --empty` followed by a *non*-`--full-refresh` `dbt seed` of decimal columns is not exercised by `BaseTestEmptySeedFlag`; the `convert_number_type` hardening removes the most likely failure, but the empty→plain-seed sequence remains a thin edge.
