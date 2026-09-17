## 1. Dependencies & Version Migration

- [ ] 1.1 Bump `exasol-toolbox` to `>=11.0.0,<12` in `pyproject.toml` and run `uv lock && uv sync` to verify clean resolution
- [ ] 1.2 Export `__version__ = version("dbt-exasol")` in `dbt/adapters/exasol/__init__.py` and delete `dbt/adapters/exasol/version.py`
- [ ] 1.3 Remove `version_filepath` from `noxconfig.py::Config` and remove `dbt/adapters/exasol/version.py` from coverage omissions in `pyproject.toml`
- [ ] 1.4 Remove `_version(session, Mode.Check)` and obsolete `_version` import from `noxfile.py`

## 2. Project Config & Matrix Dimensions

- [ ] 2.1 Add `@computed_field` property `python_version` and `exasol_version` to `Config` in `noxconfig.py`
- [ ] 2.2 Add `@computed_field` property `has_documentation -> bool` returning `False` in `noxconfig.py`
- [ ] 2.3 Verify `uv run nox -s matrix:generate -- python_version` and `uv run nox -s matrix:generate -- python_version exasol_version` return valid JSON outputs

## 3. Noxfile API Migration

- [ ] 3.1 Migrate `_context` import in `noxfile.py` to `_unit_test_context` and `_integration_test_context`
- [ ] 3.2 Update `unit_tests`, `coverage`, and `coverage_unit` sessions to use `_unit_test_context(session, ...)`
- [ ] 3.3 Update `integration_tests` and `coverage_integration` sessions to use `_integration_test_context(session, ...)`
- [ ] 3.4 Remove `.lint.txt` handling from `noxfile.py::artifacts_copy`

## 4. Workflow Security Auditing (Zizmor)

- [ ] 4.1 Create `.zizmor.yml` with pinning policies allowing referential pins for `actions/*`, `exasol/*`, `astral-sh/*`, `jdx/*`, `dorny/*`
- [ ] 4.2 Verify `uv run nox -s workflow:audit` passes with 0 findings across repository workflows
- [ ] 4.3 Update `mise.toml` and `AGENTS.md` check commands to include `workflow:audit`

## 5. CI/CD Workflow Pipeline Updates

- [ ] 5.1 Update `.github/workflows/ci.yml` `setup` job to use `matrix:generate` with singular keys and fast PR matrix branching
- [ ] 5.2 Update `checks` job in `ci.yml` to use `matrix.python_version`, run `workflow:audit`, and remove `.lint.txt` upload
- [ ] 5.3 Update `integration` job in `ci.yml` to consume `matrix.python_version` and `matrix.exasol_version`, forwarding `--db-version ${{ matrix.exasol_version }}`
- [ ] 5.4 Update `report` job artifact download/combine globs to match multi-dimensional integration coverage names
- [ ] 5.5 Add explicit least-privilege `permissions:` across jobs in `ci.yml` to satisfy zizmor audit

## 6. End-to-End Verification

- [ ] 6.1 Run full check suite (`mise run check` / `uv run nox -s format:check lint:code lint:security lint:typing workflow:audit`) and verify green
- [ ] 6.2 Run unit tests with coverage (`uv run nox -s test:unit -- --coverage`) and verify green
- [ ] 6.3 Validate OpenSpec change with `openspec validate update-build-matrix`
