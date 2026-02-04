# Change: Refactor Build Tooling for Simplified Maintenance

## Why

The current build configuration has accumulated technical debt:
- 405-line `noxfile.py` with 6 overridden exasol-toolbox sessions, primarily due to non-standard test directory names (`tests/` instead of `test/`)
- Python version matrix defined in 3 places (`noxconfig.py`, `ci.yml`, `pyproject.toml`) leading to drift (CI tests 3.10-3.12 but noxconfig defines 3.10-3.13)
- `mise.toml` tasks run independent tools (ruff, sqlfluff) instead of delegating to nox, causing inconsistent behavior between local and CI
- 70+ lines of sqlite debug logging in `artifacts:copy` session

## What Changes

1. **Rename test directories** to match exasol-toolbox conventions:
   - `tests/unit/` → `test/unit/`
   - `tests/functional/` → `test/integration/`
   - `tests/conftest.py` → `test/conftest.py`

2. **Simplify noxfile.py** (~80% reduction):
   - Remove overridden `unit_tests`, `integration_tests`, `coverage`, `project:check` sessions
   - Remove debug logging from `artifacts:copy`
   - Keep only `db:start`, `db:stop`, and simplified `artifacts:copy`/`sonar:check`

3. **Update CI workflow**:
   - Add Python 3.13 to test matrix
   - Use `nox -s matrix:python` to dynamically derive Python versions from `noxconfig.py`

4. **Align mise tasks with nox**:
   - `mise run lint` → `uv run nox -s lint:code lint:security`
   - `mise run test` → `uv run nox -s test:coverage`
   - Add: `format`, `format-check`, `test:unit`, `test:integration`, `check`

5. **Update related configuration**:
   - `pytest.ini`: testpaths = test
   - `pyproject.toml`: mypy overrides `test.*`
   - `AGENTS.md`: Update test path examples

## Impact

- **Affected specs**: `cicd`
- **Affected code**: noxfile.py, noxconfig.py, ci.yml, mise.toml, pytest.ini, pyproject.toml, AGENTS.md, test/

| Metric | Before | After |
|--------|--------|-------|
| noxfile.py lines | 405 | ~80 |
| Overridden sessions | 6 | 2 |
| Python version definitions | 3 places | 1 |
| mise-nox alignment | None | Full |
