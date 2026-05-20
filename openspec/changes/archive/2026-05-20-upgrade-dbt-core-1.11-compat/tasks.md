## 1. Dependency Updates
- [x] 1.1 Update `pyproject.toml`:
  - [x] 1.1.1 Change `version` from `"1.10.5"` to `"1.11.0"`
  - [x] 1.1.2 Change `dbt-adapters>=1.10.0` to `dbt-adapters>=1.11.0`
  - [x] 1.1.3 Change `dbt-core>=1.10.0` to `dbt-core>=1.11.0`
  - [x] 1.1.4 Change `dbt-tests-adapter>=1.10.0` to `dbt-tests-adapter>=1.11.0` (dev)
- [x] 1.2 Regenerate version files:
  - [x] 1.2.1 Update `dbt/adapters/exasol/__version__.py` VERSION to `"1.11.0"`
  - [x] 1.2.2 Run `uv run nox -s version:check -- --fix` to regenerate `version.py` from `pyproject.toml` (do NOT edit `version.py` manually -- it is auto-generated)
- [x] 1.3 Run `uv sync` to update lockfile with new dependency versions

## 2. Verification
- [x] 2.1 Run unit tests: `uv run nox -s test:unit`
- [x] 2.2 Run lint/format checks: `uv run nox -s format:check lint:code`
- [x] 2.3 Run functional tests: `uv run nox -s test:integration`
- [x] 2.4 Verify no new deprecation warnings break existing tests

## 3. Documentation
- [x] 3.1 Update README.md version compatibility matrix (add 1.11.x row)

## 4. Validation
- [x] 4.1 Run `openspec validate upgrade-dbt-core-1.11-compat --strict`
- [x] 4.2 Verify all checklist items complete
