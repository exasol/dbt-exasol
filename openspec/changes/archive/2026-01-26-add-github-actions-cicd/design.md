# Design: GitHub Actions CI/CD

## Context

The project uses:
- `uv` for dependency management (not Poetry)
- `nox` for task automation with exasol-toolbox sessions
- `tox` for multi-Python version testing
- `itde` (exasol-integration-test-docker-environment) for DB testing
- `devbox` for development environment management

`pyexasol` uses a strict `nox`-based workflow with SonarCloud integration. `dbt-exasol` will adopt this pattern.

## Goals

- Automated checks on every PR (Format, Lint, Security, Type, Unit Tests)
- **SonarCloud Integration** for quality gates and coverage
- **Strict Nox Usage**: All steps via `nox` sessions
- **Follow pyexasol pattern**: Checks Job -> Artifacts -> Report Job
- Tag-triggered releases to PyPI
- Local CI testing with `act`

## Non-Goals

- Integration tests in CI (requires Exasol container, runs locally via `nox -s test:integration`)
- Documentation publishing
- SonarCloud integration
- Pre-release/RC tags (e.g., `v1.10.2-rc1`) - only final releases are published to PyPI

## Decisions

### Decision: Follow pyexasol Architecture

We will structure `ci.yml` to mirror the `pyexasol` flow, but adapted for `uv` and a single file (for now):

**1. Checks Job (Matrix)**
Runs on Python 3.9, 3.10, 3.11, 3.12.
Executes:
- `nox -s format:check`
- `nox -s lint:code`
- `nox -s lint:security`
- `nox -s lint:typing`
- `nox -s test:unit -- --coverage`

Artifacts are uploaded for each matrix entry:
- `.coverage` (renamed to avoid collision)
- `.lint.json` (if produced)
- `.security.json` (if produced)

**2. Report Job**
Runs once after Checks.
Executes:
- Download artifacts
- `nox -s artifacts:copy` (Consolidates artifacts)
- `nox -s sonar:check` (Uploads to SonarCloud)
- `nox -s project:report` (Generates summary)

### Decision: SonarCloud

SonarCloud will handle the "PR comments" and coverage enforcement.
- Requires `SONAR_TOKEN` secret.
- Requires `[tool.sonar]` in `pyproject.toml`.

### Decision: Use `uv` instead of Poetry

dbt-exasol already uses `uv` for dependency management. Using Poetry would require migration.

**Workflow commands:**
```yaml
- run: uv sync
- run: uv run nox -s format:check
- run: uv run nox -s lint:code  
- run: uv run nox -s test:unit -- --coverage
```

### Decision: Python version matrix in CI

CI SHALL test against all supported Python versions (3.9, 3.10, 3.11, 3.12) using a matrix strategy.

**Rationale:** Ensures compatibility across all supported versions as documented in `README.md`. 
*Note: This aligns with `dbt-core` support. Current `tox.ini` tests 3.10-3.13, but `requires-python` allows 3.9+. We prioritize the stated support range.*

### Decision: Tag-triggered releases

Format: semantic version with `v` prefix (e.g., `v1.10.2`) to match existing GitHub releases

```yaml
on:
  push:
    tags:
      - 'v[0-9]+.[0-9]+.[0-9]+'
```

This matches the existing release format (e.g., `v1.10.1`, `v1.8.1`).

### Decision: Use uv publish for PyPI

```yaml
- run: uv build
- run: uv publish --token ${{ secrets.PYPI_TOKEN }}
```

Simpler than setting up twine or Poetry.

### Decision: PR comments for results documentation

Use `actions/github-script` to post a formatted comment with:
- Format check: pass/fail
- Lint results: pass/fail with issue count
- Test results: pass/fail with test count
- Coverage: percentage and pass/fail against 80% threshold

This provides immediate visibility without leaving the PR page.

### Decision: 80% coverage threshold

Update `pyproject.toml`:
```toml
[tool.coverage.report]
fail_under = 80
```

CI will fail if coverage drops below 80%.

### Decision: Local CI testing with `act`

Add `act` to devbox for testing GitHub Actions locally before pushing.

**Benefits:**
- Fast feedback loop
- Debug workflow issues locally
- No need to create test PRs to validate workflow changes

## Devbox Configuration

### Updated devbox.json

```json
{
  "$schema": "https://raw.githubusercontent.com/jetify-com/devbox/0.16.0/.schema/devbox.schema.json",
  "packages": [
    "uv@latest",
    "direnv@latest",
    "gh@latest",
    "bun@latest",
    "docker-client@latest",
    "act@latest"
  ],
  "env": {
    "PATH": "$PWD/.devbox/bin:$HOME/.local/bin:$PATH"
  },
  "shell": {
    "init_hook": [
      "echo 'Welcome to devbox!' > /dev/null"
    ],
    "scripts": {
      "format": "uv run nox -s format:check",
      "lint": "uv run nox -s lint:code",
      "unit-test": "uv run nox -s test:unit",
      "coverage": "uv run nox -s test:unit -- --coverage && uv run coverage report -m",
      "ci": "uv run nox -s format:check && uv run nox -s lint:code && uv run nox -s test:unit -- --coverage && uv run coverage report -m",
      "act": "act pull_request --container-architecture linux/amd64"
    }
  }
}
```

### Script Descriptions

| Script | Description |
|--------|-------------|
| `devbox run format` | Run format check only |
| `devbox run lint` | Run linting only |
| `devbox run unit-test` | Run unit tests only |
| `devbox run coverage` | Run unit tests with coverage report |
| `devbox run ci` | Run complete CI pipeline locally |
| `devbox run act` | Run GitHub Actions workflow locally using `act` |

### act Usage Notes

`act` requires Docker to be running. The `--container-architecture linux/amd64` flag ensures compatibility on Apple Silicon Macs.

To test specific workflows:
```bash
# Test CI workflow (pull_request event)
devbox run act

# Test with specific workflow file
act pull_request -W .github/workflows/ci.yml

# Dry run (list what would run)
act pull_request -n
```

## Workflow Structure

```
.github/
  workflows/
    ci.yml          # PR: lint, format, unit tests, coverage, PR comment
    release.yml     # Tag: build, publish, release
```

### ci.yml

```yaml
name: CI

on:
  pull_request:
    branches: [main, master]
  push:
    branches: [main, master]

jobs:
  checks:
    name: Checks (Python-${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v5
      
      - name: Setup uv
        uses: astral-sh/setup-uv@v5
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: uv sync
      
      - name: Format Check
        run: uv run nox -s format:check
      
      - name: Lint Code
        run: uv run nox -s lint:code

      - name: Lint Security
        run: uv run nox -s lint:security
        
      - name: Type Check
        run: uv run nox -s lint:typing

      - name: Unit Tests
        run: uv run nox -s test:unit -- --coverage
      
      - name: Upload Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: artifacts-python-${{ matrix.python-version }}
          path: |
            .coverage
            .lint.txt
            .lint.json
            .security.json
          include-hidden-files: true

  report:
    name: Report
    needs: checks
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      
      - name: Setup uv
        uses: astral-sh/setup-uv@v5
      
      - name: Install dependencies
        run: uv sync
        
      - name: Download Artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts
          
      - name: Copy Artifacts
        run: uv run nox -s artifacts:copy -- artifacts
        
      - name: Sonar Scan
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: uv run nox -s sonar:check
```

### release.yml

```yaml
name: Release

on:
  push:
    tags:
      - 'v[0-9]+.[0-9]+.[0-9]+'

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v5
      
      - name: Setup uv
        uses: astral-sh/setup-uv@v5
      
      - name: Build package
        run: uv build
      
      - name: Publish to PyPI
        run: uv publish --token ${{ secrets.PYPI_TOKEN }}
      
      - name: Create GitHub Release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: gh release create ${{ github.ref_name }} --generate-notes dist/*
```

## Branch Protection

Document in README that maintainers should configure:

1. Go to Settings > Branches > Add rule
2. Branch name pattern: `main`
3. Enable:
   - Require a pull request before merging
   - Require status checks to pass before merging
   - Select "test" as required status check
   - Require branches to be up to date before merging

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Unit tests pass but integration fails | Run `nox -s test:integration` locally before releasing |
| Python version compatibility issues | Matrix strategy tests all supported versions (3.9-3.12) |
| PYPI_TOKEN exposure | Use GitHub repository secrets, not environment variables |
| Coverage threshold enforcement | 80% threshold enforced from start |
| Tag format mismatch with existing releases | Use `v` prefix (e.g., `v1.10.2`) to match existing format |
| PR comment spam on multiple pushes | Consider updating existing comment instead of creating new |
| `act` differences from real GitHub Actions | Use `act` for quick validation, real CI for final verification |
| Artifact storage costs | Set 30-day retention policy, minimal size |
| Repository URL discrepancy | pyproject.toml shows `tglunde/dbt-exasol` but remote is `exasol/dbt-exasol` - ensure secrets are configured on correct repo |

## Open Questions

- Should we add a scheduled workflow for nightly integration tests? (Deferred for now - requires Exasol container)
- Should format/lint/test be separate jobs for parallelism? (Single job is simpler, faster for small projects)
- Should we update existing PR comment or create new on each push? (Creating new for now, simpler)

