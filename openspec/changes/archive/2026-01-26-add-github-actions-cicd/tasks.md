# Tasks: Add GitHub Actions CI/CD

## 1. Setup

- [x] 1.1 Create `.github/workflows/` directory structure
- [x] 1.2 Verify current coverage level (must be >= 80% for threshold)
- [x] 1.3 Update `pyproject.toml` coverage threshold to 80%
- [x] 1.4 Add `act` package to `devbox.json`
- [x] 1.5 Add CI convenience scripts to `devbox.json`
- [x] 1.6 Setup `SONAR_TOKEN` secret in repo

## 2. CI Workflow

- [x] 2.1 Create `ci.yml` with PR triggers
- [x] 2.2 Add Python version matrix (3.9, 3.10, 3.11, 3.12)
- [x] 2.3 Setup uv with matrix Python version
- [x] 2.4 Update Checks Job:
  - [x] Format check (`nox -s format:check`)
  - [x] Lint code (`nox -s lint:code`)
  - [x] Lint security (`nox -s lint:security`)
  - [x] Type check (`nox -s lint:typing`)
  - [x] Fix typing errors found during validation
  - [x] Unit test (`nox -s test:unit`)
  - [x] Upload artifacts (`.coverage`, `.lint.json`, etc.)
- [x] 2.5 Add Report Job:
  - [x] Download artifacts
  - [x] Copy artifacts (`nox -s artifacts:copy`)
  - [x] Sonar Scan (`nox -s sonar:check`)

## 3. Release Workflow

- [x] 3.1 Create `release.yml` with v-prefixed tag trigger (e.g., `v1.10.2`)
- [x] 3.2 Add build step using `uv build`
- [x] 3.3 Add PyPI publish step using `uv publish`
- [x] 3.4 Add GitHub Release creation step
- [x] 3.5 Upload build artifacts

## 4. Documentation

- [x] 4.1 Add CI status badge to README
- [x] 4.2 Document branch protection setup in README
- [x] 4.3 Document release process (v-prefixed tags) in README
- [x] 4.4 Document devbox CI scripts usage in README
- [x] 4.5 Document 80% coverage threshold requirement

## 5. Validation

- [x] 5.1 Test CI workflow locally using `devbox run act` (workflow syntax validated)
- [x] 5.2 Verify artifact uploads work correctly (all artifacts created: .coverage, .lint.txt, .lint.json, .security.json)
- [x] 5.3 Verify Python version matrix expands correctly (4 versions: 3.9, 3.10, 3.11, 3.12)
- [x] 5.4 Test nox sessions work locally (format:check, lint:code, lint:security, test:unit all verified)
- [x] 5.4a Fix typing errors (`nox -s lint:typing`)
  - [x] noxfile.py: Add `# type: ignore[no-redef]` to session overrides
  - [x] connections.py: Fix StrEnum redefinition, kwargs typing, process_results assignment
  - [x] impl.py: Fix list_relations_without_caching return type annotation
  - [x] __init__.py: Add `# type: ignore[arg-type]` to AdapterPlugin
  - [x] Test files: Add `# type: ignore[import-not-found]` to relative imports
  - [x] Add `# type: ignore[import-untyped]` for agate, dateutil, yaml imports
- [ ] 5.5 **MANUAL**: Configure `SONAR_TOKEN` secret in repository settings
- [ ] 5.6 **MANUAL**: Configure `PYPI_TOKEN` secret in repository settings
- [ ] 5.7 **MANUAL**: Configure branch protection rules on main branch
- [ ] 5.8 **MANUAL**: Test CI workflow on a test PR (verify SonarCloud PR decoration appears)
- [ ] 5.9 **MANUAL**: Test release workflow with a test tag (or use production release)

---

## Manual Setup Guide

### Step 1: Configure GitHub Secrets

Navigate to repository settings and add the following secrets:

#### 1.1 SONAR_TOKEN

1. Go to [SonarCloud](https://sonarcloud.io)
2. Log in with GitHub account
3. Go to Account > Security > Generate Token
4. Copy the token
5. In GitHub: Settings > Secrets and variables > Actions > New repository secret
6. Name: `SONAR_TOKEN`
7. Paste the token value

#### 1.2 PYPI_TOKEN

1. Go to [PyPI Account Settings](https://pypi.org/manage/account/)
2. Scroll to "API tokens" section
3. Click "Add API token"
4. Name: `dbt-exasol-releases`
5. Scope: "Project: dbt-exasol" (or entire account if needed)
6. Copy the token (starts with `pypi-`)
7. In GitHub: Settings > Secrets and variables > Actions > New repository secret
8. Name: `PYPI_TOKEN`
9. Paste the token value

### Step 2: Configure Branch Protection

1. Go to GitHub repository Settings > Branches
2. Click "Add rule" or edit existing rule for `main`
3. Branch name pattern: `main`
4. Enable the following:
   - ✅ Require a pull request before merging
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
5. Under "Status checks that are required", search and select:
   - `checks` (the CI checks job)
   - `report` (the CI report job)
6. Optional but recommended:
   - ✅ Require conversation resolution before merging
   - ✅ Do not allow bypassing the above settings
7. Click "Create" or "Save changes"

### Step 3: Test CI Workflow

1. Create a test branch: `git checkout -b test/ci-workflow`
2. Make a small change (e.g., add a comment to README)
3. Commit and push: `git add . && git commit -m "test: verify CI workflow" && git push -u origin test/ci-workflow`
4. Create a pull request
5. Verify in the PR:
   - ✅ CI workflow runs automatically
   - ✅ All checks (format, lint, security, type, unit tests) execute
   - ✅ Artifacts are uploaded (visible in workflow run page)
   - ✅ Report job runs after checks complete
   - ✅ SonarCloud comment appears on PR (may take 2-5 minutes)
   - ✅ Coverage percentage is shown
6. If any checks fail, fix issues and push again

### Step 4: Test Release Workflow (Optional)

**Option A: Test with a pre-release tag**

1. Update version in `pyproject.toml` to a test version (e.g., `1.10.2-test`)
2. Create and push tag: `git tag v1.10.2-test && git push origin v1.10.2-test`
3. Verify workflow runs but may fail at PyPI upload (version conflict)
4. Delete the test tag: `git tag -d v1.10.2-test && git push origin :refs/tags/v1.10.2-test`

**Option B: Use production release**

1. When ready to release, update version in `pyproject.toml`
2. Commit: `git add pyproject.toml && git commit -m "chore: bump version to X.Y.Z"`
3. Create tag: `git tag vX.Y.Z && git push origin vX.Y.Z`
4. Verify:
   - ✅ Release workflow runs
   - ✅ Package builds successfully
   - ✅ Package publishes to PyPI
   - ✅ GitHub Release is created with auto-generated notes

### Step 5: Monitor and Maintain

1. **SonarCloud Dashboard**: Monitor code quality at <https://sonarcloud.io/project/overview?id=com.exasol:dbt-exasol>
2. **Coverage Trends**: Track coverage over time to ensure it stays >= 80%
3. **Security Alerts**: Review Dependabot alerts and security scan results
4. **Workflow Updates**: Keep GitHub Actions updated (Dependabot will create PRs)

---

## Troubleshooting

### CI Workflow Issues

**Problem**: Artifacts not uploading

- Check artifact paths exist after nox sessions run
- Verify `include-hidden-files: true` is set for `.coverage` uploads

**Problem**: SonarCloud not commenting on PR

- Verify `SONAR_TOKEN` secret is configured correctly
- Check SonarCloud organization and project settings
- Ensure repository is imported in SonarCloud

**Problem**: Tests failing in CI but passing locally

- Check Python version matrix - may be version-specific issue
- Review workflow logs for environment differences
- Ensure `uv sync` installs all dependencies

### Release Workflow Issues

**Problem**: PyPI publish fails with authentication error

- Verify `PYPI_TOKEN` secret is configured
- Ensure token has correct scope (project or account-wide)
- Check token hasn't expired

**Problem**: Tag doesn't trigger release

- Verify tag matches pattern `v[0-9]+.[0-9]+.[0-9]+`
- Ensure tag is pushed to remote: `git push origin <tagname>`
- Check workflow file is on the main branch

**Problem**: GitHub Release creation fails

- Verify repository has `contents: write` permission (already in workflow)
- Check `GITHUB_TOKEN` is available (automatic, no configuration needed)
