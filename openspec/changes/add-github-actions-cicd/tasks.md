# Tasks: Add GitHub Actions CI/CD

## 1. Setup

- [ ] 1.1 Create `.github/workflows/` directory structure
- [ ] 1.2 Verify current coverage level (must be >= 80% for threshold)
- [ ] 1.3 Update `pyproject.toml` coverage threshold to 80%
- [ ] 1.4 Add `act` package to `devbox.json`
- [ ] 1.5 Add CI convenience scripts to `devbox.json`

## 2. CI Workflow

- [ ] 2.1 Create `ci.yml` with PR triggers
- [ ] 2.2 Add Python version matrix (3.9, 3.10, 3.11, 3.12)
- [ ] 2.3 Setup uv with matrix Python version
- [ ] 2.4 Add format check step (`nox -s format:check`)
- [ ] 2.5 Add lint step (`nox -s lint:code`)
- [ ] 2.6 Add unit test step with coverage (`nox -s test:unit -- --coverage`)
- [ ] 2.7 Add coverage report generation and threshold check
- [ ] 2.8 Add artifact upload step for coverage reports
- [ ] 2.9 Add PR comment step for lint/test/coverage results with failure summaries

## 3. Release Workflow

- [ ] 3.1 Create `release.yml` with v-prefixed tag trigger (e.g., `v1.10.2`)
- [ ] 3.2 Add build step using `uv build`
- [ ] 3.3 Add PyPI publish step using `uv publish`
- [ ] 3.4 Add GitHub Release creation step
- [ ] 3.5 Upload build artifacts

## 4. Documentation

- [ ] 4.1 Add CI status badge to README
- [ ] 4.2 Document branch protection setup in README
- [ ] 4.3 Document release process (v-prefixed tags) in README
- [ ] 4.4 Document devbox CI scripts usage in README
- [ ] 4.5 Document 80% coverage threshold requirement

## 5. Validation

- [ ] 5.1 Test CI workflow locally using `devbox run act`
- [ ] 5.2 Test CI workflow on a test PR (verify PR comment appears with failure details)
- [ ] 5.3 Verify artifact uploads work correctly
- [ ] 5.4 Test release workflow with a test tag (or dry-run)
- [ ] 5.5 Configure `PYPI_TOKEN` secret in repository settings
- [ ] 5.6 Configure branch protection rules on main branch
- [ ] 5.7 Verify Python version matrix runs all versions
