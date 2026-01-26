# Change: Add GitHub Actions CI/CD Workflows

## Why

The dbt-exasol project currently lacks automated CI/CD workflows. Adding GitHub Actions will enable automated testing on pull requests, consistent quality gates, PR-based change documentation, and a streamlined release process to PyPI.

## What Changes

- Add `.github/workflows/ci.yml` for PR testing (lint, format, unit tests, security, type checks)
- Add `.github/workflows/release.yml` for tag-triggered releases to PyPI
- **SonarCloud Integration**: Code quality and coverage analysis
- **Strict Nox Usage**: All workflow steps SHALL use `nox` sessions
- **Artifacts Handover**: Use `pyexasol` pattern of uploading artifacts in checks and processing them in a report job
- **Coverage enforcement**: Fail CI if coverage drops below 80% (via Sonar or check)
- **Local CI testing**: Add `act` tool to devbox for testing workflows locally
- **Devbox scripts**: Add convenience commands
- Leverage existing nox sessions (`format:check`, `lint:code`, `lint:typing`, `lint:security`, `test:unit`, `sonar:check`)
- Use `uv` for dependency management

## Design Decisions

### Follow pyexasol Patterns

We SHALL follow the patterns established in `pyexasol` where applicable, adapted for `uv`:
- **Workflow Structure**: Separate `checks` (matrix) and `report` jobs.
- **Artifacts**: `checks` job produces artifacts (`.coverage`, `.lint.txt`, etc.), `report` job consumes them.
- **SonarCloud**: The `report` job executes `nox -s sonar:check` to analyze gathered artifacts.
- **Strict Nox**: Direct shell commands for tools (like `coverage report`) are replaced by `nox` sessions.

### PR-Based Workflow

All changes to main SHALL go through pull requests:
- CI runs on every PR
- Results (lint, test, coverage) posted as PR comment (via SonarCloud or script)
- Branch protection

### Workflow Structure

**`ci.yml`**:
1. **Checks Job** (Matrix: Python 3.9-3.12):
   - Format check (`nox -s format:check`)
   - Lint code (`nox -s lint:code`)
   - Lint security (`nox -s lint:security`)
   - Type check (`nox -s lint:typing`)
   - Unit tests (`nox -s test:unit`)
   - Upload artifacts
2. **Report Job** (Single):
   - Depends on Checks
   - Download artifacts
   - Copy artifacts (`nox -s artifacts:copy`)
   - Sonar Scan (`nox -s sonar:check`)


Add `act` to devbox packages to run GitHub Actions locally:
- Test workflows before pushing
- Debug CI failures locally
- No need to create test PRs

### Lightweight vs pyexasol's approach

pyexasol uses:
- 8+ workflow files with reusable workflows
- Poetry for dependency management
- Manual approval gates for slow tests
- Multiple Python versions matrix
- exasol-toolbox actions

dbt-exasol will use:
- 2 workflow files (ci.yml + release.yml)
- `uv` for dependency management (already in use)
- Unit tests only on PRs (integration tests via `nox -s test:integration` locally)
- Python version matrix (3.9, 3.10, 3.11, 3.12) to match project support
- Direct nox commands without external action dependencies
- Artifact uploads for test results and coverage reports

### Release Process

Tag-based releases:
1. Bump version in `pyproject.toml`
2. Create and push git tag (e.g., `git tag v1.10.2 && git push origin v1.10.2`)
3. Workflow builds wheel, publishes to PyPI, creates GitHub Release

## Impact

- **Affected specs**: New `cicd` capability
- **Affected code**: 
  - `.github/workflows/ci.yml` (new)
  - `.github/workflows/release.yml` (new)
  - `devbox.json` (add `act` package, add CI scripts)
  - `pyproject.toml` (update coverage threshold to 80%)
  - `README.md` (add CI badge, document branch protection)
- **Secrets required**: 
  - `PYPI_TOKEN` for releases
  - `SONAR_TOKEN` for SonarCloud analysis
- **Manual setup**: Branch protection rules on main branch
