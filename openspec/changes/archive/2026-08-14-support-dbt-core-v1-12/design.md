## Context

`dbt-exasol` extends `dbt-adapters`' `SQLAdapter`. Today `pyproject.toml` pins `dbt-core>=1.10.0` / `dbt-adapters>=1.10.0` and `uv.lock` resolves to dbt-core 1.11.9, dbt-adapters 1.23.0, dbt-tests-adapter 1.19.7.

Empirical findings that drive this design (all verified against a scratch venv with dbt-core 1.12.0b2 + dbt-adapters 1.24.2 + dbt-tests-adapter 1.20.0):

- **dbt-core 1.12 is beta-only.** PyPI exposes `1.12.0b1` and `1.12.0b2`; latest stable is `1.11.11`. `dbt-core 1.12.0b2` requires `dbt-adapters>=1.24.1`.
- **dbt-adapters / dbt-tests-adapter are version-decoupled** from dbt-core. The v1.12 adapter features (`--empty` seed support, `generate_latest_version_pointer_alias`, JS UDFs, `Capability.CatalogsV2`) live in dbt-adapters 1.23.0–1.24.2 and dbt-tests-adapter 1.20.0 — not a "1.12" tag.
- **`dbt-core 2.0.0a1` exists** (the Rust rewrite). Under PEP 440, `2.0.0a1` satisfies `<2.0`, so a naive `<2.0` cap plus pre-release allowance could resolve to it.
- **No new required adapter surface.** `ExasolAdapter` imports against dbt-adapters 1.24.2 with `__abstractmethods__ == ∅`.
- **`latest_version_pointer` reuses the `view` materialization.** dbt-core builds a synthetic `select * from <source>` node with `type='view'` and runs the standard view macro (`dbt/task/run.py`). Exasol's existing `view.sql` satisfies it.
- **`--empty` seed mechanics:** dbt-core loads the seed CSV (inferring agate column types from the full data) then calls `table.limit(0)` (`dbt/context/providers.py`). The default seed materialization skips `load_csv_rows` when `rows_affected == 0`, so Exasol's CSV `IMPORT` path is never triggered for empty seeds. The table is still created via the default `create_csv_table`, which calls `adapter.convert_type` per column.

## Goals / Non-Goals

**Goals:**
- Install and pass tests against dbt-core 1.12 (beta) with a precise, non-viral pre-release policy.
- Guarantee `dbt seed --empty` creates correctly-typed, zero-row tables on Exasol.
- Add regression coverage for `--empty` seeds and `latest_version_pointer`.
- Keep the adapter installable on stable dbt-core 1.11 as well (the new dbt-adapters floor is satisfied by both).

**Non-Goals:**
- Implementing `Capability.CatalogsV2` / catalogs.yml v2 (opt-in, separate effort).
- Implementing JavaScript / Python / overloaded UDFs (Exasol has no equivalent surface here).
- Adopting the opt-in v2 (Rust) parser or any dbt-core 2.0 work.
- Adding `pointer_table` / `function` handling to `ExasolRelation` (not needed — pointer uses `view`).

## Decisions

### D1: Pin `dbt-core>=1.12.0b1,<1.13` with uv `prerelease = "explicit"`
Use uv's `explicit` pre-release mode rather than `allow`. In `explicit` mode uv permits pre-releases **only** for packages whose version specifier itself contains a pre-release marker (here, just `dbt-core` via `b1`). This avoids globally enabling pre-releases for every transitive dependency.
- The `<1.13` upper bound (not `<2.0`) is deliberate: under pre-release resolution, `2.0.0a1` would satisfy `<2.0` and could be selected. `<1.13` confines resolution to the 1.12 line.
- Alternative considered — `prerelease = "allow"` (rejected: viral, would let any dep float to a pre-release). Alternative — pin exact `==1.12.0b2` (rejected: blocks automatic uptake of the eventual stable `1.12.0`; `>=1.12.0b1,<1.13` upgrades cleanly to stable when released).

### D2: `dbt-adapters>=1.24.1`, `dbt-tests-adapter>=1.20.0`
1.24.1 is the floor required by dbt-core 1.12.0b2 and is where the `generate_latest_version_pointer_alias` macro and the JS-UDF `KeyError` fix landed. dbt-tests-adapter 1.20.0 is the floor that ships `BaseTestEmptySeedFlag`. Both are stable releases and are also compatible with stable dbt-core 1.11.11 (`dbt-adapters<2.0,>=1.15.5`), so the bump does not strand non-beta users.

### D3: Harden `convert_number_type` for zero-row agate tables
`agate.MaxPrecision(col_idx)` returns `0` on an empty column, so the current `"float" if decimals else "integer"` degrades every numeric column to `integer` under `--empty` (verified). Decision: when `len(agate_table.rows) == 0`, return `"float"` (the wider, lossless numeric type) unless an explicit `column_types` override is present. This keeps the populated-seed path byte-for-byte identical and only changes the empty path.
- Alternative — trust agate's preserved `Number` data type instead of re-aggregating (rejected for this change: larger behavioral change to the populated path; out of scope). Fallback-to-float is the minimal, safe fix.

### D4: Opt into `BaseTestEmptySeedFlag` and add a pointer test
`dbt-tests-adapter` ships the empty-seed coverage only as `Base...`, so a `Test...` subclass is required to activate it. Add a small functional test that enables `latest_version_pointer` on a versioned model and asserts the pointer view is created and selectable.

### D5: `RuntimeError` → `DbtRuntimeError` in `ExasolCursor`
Swap the three `raise RuntimeError(_UNSET_STATEMENT_ERROR)` sites for `dbt_common.exceptions.DbtRuntimeError`. Low-risk alignment with v1.12 exception philosophy; the `exception_handler` already wraps stray exceptions, so this is a clarity/consistency improvement, not a behavior fix.

## Risks / Trade-offs

- **dbt-core 1.12 beta churn** → The `>=1.12.0b1,<1.13` range absorbs new betas and the eventual stable automatically; pin is re-validated whenever `uv.lock` is refreshed.
- **Pre-release policy leaks to other packages** → Mitigated by `prerelease = "explicit"` (scoped to specifiers that name a pre-release) rather than `allow`.
- **Accidental dbt-core 2.0 alpha resolution** → Mitigated by the `<1.13` cap.
- **CI resolves differently than local** → tox uses `uv-venv-lock-runner`, which consumes the committed `uv.lock`; refreshing and committing the lock makes CI deterministic. Verify a CI run actually installs `1.12.0b2`.
- **Empty-seed type edge remains** → `--empty` then non-`--full-refresh` `seed` of decimals is not covered by `BaseTestEmptySeedFlag`; D3 removes the most likely break (decimal→integer) but the sequence is documented as a thin edge rather than fully guaranteed.

## Migration Plan

1. Update `pyproject.toml` (deps + `[tool.uv]`), run `uv lock` / `uv sync`, commit the refreshed `uv.lock`.
2. Apply the `convert_number_type` and `ExasolCursor` code changes.
3. Add tests; run `nox -s test:unit` then `test:integration` (needs the Exasol docker DB).
4. Rollback: revert the dependency + `[tool.uv]` changes and restore the prior `uv.lock`; code changes are independently revertible and backward-compatible with 1.11.

## Open Questions

- Should we additionally add a non-`--full-refresh` empty→seed regression test for decimals (beyond what `BaseTestEmptySeedFlag` covers), or is documenting the edge sufficient? (Leaning: add it if cheap during implementation.)
