# Change: Add GitHub Actions CI/CD Workflows

## Why

The dbt-exasol project currently lacks automated CI/CD workflows. Adding GitHub Actions will enable automated testing on pull requests, consistent quality gates, PR-based change documentation, and a streamlined release process to PyPI.

## What Changes

- Add `.github/workflows/ci.yml` for PR testing (lint, format, unit tests with coverage)
- Add `.github/workflows/release.yml` for tag-triggered releases to PyPI
- **PR result documentation**: Post lint/test/coverage results as PR comments
- **Coverage enforcement**: Fail CI if coverage drops below 80%
- **Local CI testing**: Add `act` tool to devbox for testing workflows locally
- **Devbox scripts**: Add convenience commands (`format`, `lint`, `unit-test`, `coverage`, `ci`, `act`)
- Leverage existing nox sessions (`format:check`, `lint:code`, `test:unit`) for consistency
- Use `uv` for dependency management (not Poetry as in pyexasol)
- Document branch protection requirements for PR-based workflow

## Design Decisions

### PR-Based Workflow

All changes to main SHALL go through pull requests:
- CI runs on every PR
- Results (lint, test, coverage) posted as PR comment
- Branch protection (documented, manual setup required)

### Local CI Testing with `act`

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
- **Secrets required**: `PYPI_TOKEN` must be configured in repository settings
- **Manual setup**: Branch protection rules on main branch
