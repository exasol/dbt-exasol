## Why

The dbt-exasol project relies on `exasol-toolbox` (PTB) for standardized Nox sessions and matrix orchestration, but the dependency was previously pinned to `<7` due to legacy version file incompatibilities (`version.py` and `_version` removal). Furthermore, PTB 11 has removed the legacy `matrix:python` Nox session, replacing it with the dynamic `matrix:generate` task, and introduced `zizmor` workflow security scanning (`workflow:audit`). We need to upgrade to PTB 11.0 to support flexible multi-dimensional build matrices (Python versions × Exasol DB versions) in CI/CD, adopt modern version resolution via `importlib.metadata`, and establish automated workflow security auditing.

## What Changes

- **Upgrade PTB**: Upgrade `exasol-toolbox` dependency from `>=5.1.0,<7` to `>=11.0.0,<12` in `pyproject.toml` and re-lock dependencies.
- **Dynamic Build Matrix**: Replace deprecated `nox -s matrix:python` in CI with PTB 11's `nox -s matrix:generate -- <keys>`.
- **Multi-Dimensional Testing**: Add `@computed_field` aliases (`python_version`, `exasol_version`) to `Config` in `noxconfig.py` to drive Cartesian product testing across Python and Exasol versions in CI integration tests.
- **Fast PR Matrix**: Structure CI to run a single Python 3.14 + Exasol 8.29.13 combination on PRs for fast developer feedback, while executing the full multi-dimensional matrix on pushes and nightly schedules.
- **Package Versioning Migration**: **BREAKING (internal)**: Remove `dbt/adapters/exasol/version.py`, set `__version__ = version("dbt-exasol")` via `importlib.metadata` in `dbt/adapters/exasol/__init__.py`, and remove `version_filepath` and `_version` checks.
- **Internal Nox API Migration**: Update `noxfile.py` to use PTB 10/11 context functions (`_unit_test_context`, `_integration_test_context`), and remove `.lint.txt` references (superseded by `.lint.json`).
- **Workflow Security Audit (Zizmor)**: Add `.zizmor.yml` configuration and integrate `nox -s workflow:audit` into the CI checks pipeline and local check suites.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `cicd`: Update CI requirements to use `nox -s matrix:generate`, support multi-dimensional matrix combinations (Python × Exasol DB), run `workflow:audit` (zizmor), remove `.lint.txt` from artifacts, and support fast PR matrix execution.

## Impact

- `pyproject.toml`: Dependency bump for `exasol-toolbox>=11.0.0,<12`, removal of `version.py` from coverage omissions.
- `dbt/adapters/exasol/version.py`: Removed.
- `dbt/adapters/exasol/__init__.py`: Added `__version__` export using `importlib.metadata`.
- `noxconfig.py`: Added `python_version`, `exasol_version`, `has_documentation=False`; removed `version_filepath`.
- `noxfile.py`: Migrated context helpers to `_unit_test_context` and `_integration_test_context`; removed `_version` and `.lint.txt`.
- `.zizmor.yml`: Created with action pinning policies.
- `.github/workflows/ci.yml`: Updated setup matrix generation, checks, integration parameters, and zizmor audit.
