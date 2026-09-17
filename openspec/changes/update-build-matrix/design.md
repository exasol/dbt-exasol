## Context

The repository combines Astral `uv` and `mise` for fast package management and developer environments with Exasol's `python-toolbox` (PTB) for standardized Nox tasks (`format`, `lint`, `sonar`, `test`). See `proposal.md` for motivation.

Key technical constraints shaping this design:
- PTB >= 7 removed `version.py` file generation and internal `_version` checks.
- PTB 9/11 introduced `matrix:generate` and removed deprecated matrix sessions (`matrix:python`, `matrix:exasol`, `matrix:all`).
- PTB's upstream `.github/workflows/matrix.yml` uses Poetry, whereas `dbt-exasol` strictly uses `uv` + `mise`.
- PTB 10+ introduces `zizmor` security scanning via `nox -s workflow:audit` against `.zizmor.yml`.

## Goals / Non-Goals

**Goals:**
- Upgrade `exasol-toolbox` dependency to `>=11.0.0,<12`.
- Enable dynamic multi-dimensional matrix generation (Python × Exasol DB) using `nox -s matrix:generate`.
- Retain sub-second `uv` package operations in CI without adopting Poetry.
- Migrate adapter versioning to standard `importlib.metadata.version`.
- Enforce GitHub Actions workflow security with `zizmor` auditing both locally and in CI.

**Non-Goals:**
- Adopting PTB's multi-file workflow template generation (`workflow:generate -- all`).
- Migrating dependency management to Poetry.
- Publishing documentation via PTB's Sphinx pipeline (documentation is handled externally).

## Decisions

### Decision 1: Direct Upgrade to PTB 11.0.0
We will upgrade directly to `exasol-toolbox>=11.0.0,<12` rather than intermediate 10.x.
- **Rationale**: PTB 11 cleans up deprecated sessions completely. Since fixing the breaking changes (`version.py`, `_shared` APIs) is required for any version >6.4, upgrading directly to 11 avoids future migration overhead.
- **Alternatives Considered**: Upgrading to 10.5.0 (rejected: keeps technical debt and deprecated matrix sessions).

### Decision 2: Hybrid In-Workflow Matrix Invocation
We will execute `mise run nox -- -s matrix:generate -- <keys>` inside `.github/workflows/ci.yml` `setup` job.
- **Rationale**: Preserves `dbt-exasol`'s ultra-fast UV build pipeline while consuming PTB's dynamic Pydantic-backed matrix generator.
- **Alternatives Considered**: Calling PTB's remote reusable `matrix.yml` (rejected: upstream workflow requires Poetry and `actions/python-environment@v10`).

### Decision 3: Singular Matrix Key Aliases on `BaseConfig`
In `noxconfig.py::Config`, expose `@computed_field` properties `python_version` and `exasol_version` aliasing the plural configuration fields.
- **Rationale**: `matrix:generate` outputs JSON keys matching field names. Singular keys produce clean GitHub Actions matrix references (`matrix.python_version`, `matrix.exasol_version`) and readable job names.
- **Alternatives Considered**: Using plural fields throughout GitHub Actions (rejected: clunkier job names such as `Checks (Python-${{ matrix.python_versions }})`).

### Decision 4: Fast PR Matrix vs. Full Nightly Matrix Branching
In `ci.yml`'s `setup` job, conditionally branch matrix output:
- Pull Requests: Output a single-version matrix (`{"python_version": ["3.14"], "exasol_version": ["8.29.13"]}`).
- Nightly Schedule / Push to main / Manual Dispatch: Run `nox -s matrix:generate -- python_version exasol_version`.
- **Rationale**: Keeps PR feedback fast and avoids consuming unnecessary runner minutes while guaranteeing full compatibility checks before release.

### Decision 5: Package Versioning via `importlib.metadata`
Delete `dbt/adapters/exasol/version.py`, export `__version__ = version("dbt-exasol")` in `dbt/adapters/exasol/__init__.py`, and remove `version_filepath` from `BaseConfig`.
- **Rationale**: Aligns with PEP 566 / PEP 621 and PTB 7+ standards. `pyproject.toml` remains the single source of truth for versioning.
- **Alternatives Considered**: Maintaining a static `version.py` manually (rejected: error-prone and rejected by PTB 7+ checks).

### Decision 6: Zizmor Security Audit with Pragmatic Pinning
Create `.zizmor.yml` configured to allow tag pinning (`ref-pin`) for trusted vendor actions (`actions/*`, `exasol/*`, `astral-sh/*`, `jdx/*`, `dorny/*`) and SHA hash-pinning (`hash-pin`) for all other third-party actions. Integrate `nox -s workflow:audit` into the `checks` job.
- **Rationale**: Establishes continuous workflow security scanning without unreadable 40-character SHAs for trusted standard actions.

## Risks / Trade-offs

- **[Risk]**: Uninstalled package causes `importlib.metadata.PackageNotFoundError` during local development when running without editable install.
  → **Mitigation**: `uv sync` installs the package in editable mode by default in `.venv`. Fall back gracefully or ensure `__init__.py` catches `PackageNotFoundError` with `"unknown"`.
- **[Risk]**: Multi-dimensional integration matrix runs out of runner concurrency when testing multiple Exasol DB images.
  → **Mitigation**: PRs run a single DB image; full matrix runs only on schedule/push with `fail-fast: false`.
- **[Risk]**: PTB 11 context functions change internal signatures again in future major releases.
  → **Mitigation**: We consume public Nox task interfaces (`_unit_test_context`, `_integration_test_context`) and keep test overrides localized to `noxfile.py`.

## Migration Plan

1. Update `pyproject.toml` dependency and lock with `uv lock`.
2. Migrate `dbt/adapters/exasol/__init__.py` and delete `version.py`.
3. Update `noxconfig.py` with matrix computed fields and `has_documentation=False`.
4. Update `noxfile.py` to PTB 11 context APIs and remove `.lint.txt`.
5. Create `.zizmor.yml` and verify `nox -s workflow:audit` passes.
6. Update `.github/workflows/ci.yml` matrix generation, integration parameters, and artifact globs.
7. Verify all local checks (`mise run check` / `uv run nox -s project:check`).
