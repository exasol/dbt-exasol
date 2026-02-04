# CI/CD Specification

## Purpose

This specification defines the continuous integration and deployment workflows for the dbt-exasol project. It ensures automated quality checks on every pull request and provides a streamlined release process to PyPI.
## Requirements
### Requirement: Continuous Integration

The CI workflow SHALL run automated checks on every pull request to the main branch.

The workflow SHALL execute the following checks in order:
1. Code format validation using `nox -s format:check`
2. Code linting using `nox -s lint:code`
3. Security linting using `nox -s lint:security`
4. Type checking using `nox -s lint:typing`
5. Unit tests with coverage using `nox -s test:unit -- --coverage`

The workflow SHALL fail if any check fails.

The workflow SHALL dynamically derive the Python version matrix from `noxconfig.py` using `nox -s matrix:python`.

The workflow SHALL test across Python versions 3.10, 3.11, 3.12, and 3.13.

#### Scenario: PR triggers CI checks

- **WHEN** a pull request is opened against the main branch
- **THEN** the CI workflow runs format, lint, security, typing, and unit test checks
- **AND** the PR status reflects pass/fail of all checks

#### Scenario: Push to main triggers CI

- **WHEN** a commit is pushed directly to the main branch
- **THEN** the CI workflow runs all checks to validate the branch state

#### Scenario: Python matrix derived from noxconfig

- **WHEN** the CI workflow starts
- **THEN** a setup job runs `nox -s matrix:python` to output the Python versions
- **AND** the checks job uses the output as its matrix

### Requirement: SonarCloud Integration

The CI workflow SHALL integrate with SonarCloud for quality gates and coverage reporting.

The workflow SHALL:
1. Upload test coverage and linting artifacts from the checks job.
2. Run a report job that consumes these artifacts.
3. Execute `nox -s sonar:check` to push analysis to SonarCloud.

#### Scenario: SonarCloud Analysis

- **WHEN** the checks job completes successfully
- **THEN** the report job runs
- **AND** coverage and quality metrics are sent to SonarCloud
- **AND** the PR is decorated with SonarCloud results

### Requirement: Coverage Enforcement

The CI workflow SHALL enforce a minimum code coverage threshold.

The threshold SHALL be 80%.

This enforcement SHALL be handled by SonarCloud Quality Gates OR by the check itself.

#### Scenario: Coverage meets threshold

- **WHEN** unit tests complete with 85% coverage
- **THEN** the coverage check passes
- **AND** the workflow continues successfully

#### Scenario: Coverage below threshold

- **WHEN** unit tests complete with 75% coverage
- **THEN** the coverage check fails
- **AND** the workflow fails with a coverage error

### Requirement: Artifact Handover

The CI workflow SHALL use the artifact handover pattern.

#### Scenario: Artifacts passed to report
- **WHEN** the checks job runs on multiple Python versions
- **THEN** it uploads artifacts (coverage, lint results)
- **AND** the report job downloads all artifacts
- **AND** `nox -s artifacts:copy` consolidates them for the Sonar scan

#### Scenario: Coverage below threshold fails

- **WHEN** unit tests complete with coverage below threshold
- **THEN** the coverage check fails
- **AND** the workflow fails with coverage error

### Requirement: Artifact Uploads

The CI workflow SHALL upload test artifacts for debugging and audit purposes.

The workflow SHALL upload:
- Coverage reports (`.coverage`) for each Python version in the test matrix
- Lint results (`.lint.txt`, `.lint.json`)
- Security scan results (`.security.json`)

Artifacts SHALL be retained for 30 days.

#### Scenario: Coverage report uploaded

- **WHEN** the CI workflow completes unit tests with coverage
- **THEN** the coverage file is uploaded as an artifact
- **AND** the artifact is associated with the Python version matrix job

#### Scenario: Artifact retention policy

- **WHEN** coverage artifacts are uploaded
- **THEN** they are automatically deleted after 30 days
- **AND** storage costs are minimized

### Requirement: Tag-Triggered Release

The release workflow SHALL be triggered when a semantic version tag is pushed.

The tag format SHALL be `vMAJOR.MINOR.PATCH` (e.g., `v1.10.2`) with a `v` prefix to match existing GitHub releases.

The workflow SHALL:
1. Build the Python package using `uv build`
2. Publish the package to PyPI using `uv publish`
3. Create a GitHub Release with auto-generated notes

#### Scenario: Version tag triggers release

- **WHEN** a tag matching pattern `v[0-9]+.[0-9]+.[0-9]+` is pushed
- **THEN** the package is built and published to PyPI
- **AND** a GitHub Release is created with the tag name
- **AND** the built artifacts are attached to the release

#### Scenario: Non-version tag does not trigger release

- **WHEN** a tag not matching the version pattern is pushed (e.g., `test-tag`)
- **THEN** the release workflow does not run

### Requirement: PyPI Authentication

The release workflow SHALL authenticate to PyPI using a repository secret.

The secret SHALL be named `PYPI_TOKEN`.

#### Scenario: Valid PyPI token publishes successfully

- **WHEN** the release workflow runs with a valid `PYPI_TOKEN` secret configured
- **THEN** the package is published to PyPI successfully

#### Scenario: Missing PyPI token fails release

- **WHEN** the release workflow runs without `PYPI_TOKEN` configured
- **THEN** the workflow fails with an authentication error

### Requirement: Branch Protection Documentation

The README SHALL document the recommended branch protection configuration.

The documentation SHALL instruct maintainers to:
- Require pull requests before merging to main
- Require CI status checks to pass
- Require branches to be up to date

#### Scenario: Maintainer configures branch protection

- **WHEN** a maintainer follows the README documentation
- **THEN** they can configure branch protection rules in GitHub settings
- **AND** direct pushes to main are blocked
- **AND** PRs require passing CI before merge

### Requirement: Local CI Testing

The mise environment SHALL provide tasks that delegate to nox sessions for consistent local/CI behavior.

mise SHALL provide the following tasks:
- `lint` - Run linters via `nox -s lint:code lint:security`
- `format` - Auto-fix formatting via `nox -s format:fix`
- `format-check` - Check formatting via `nox -s format:check`
- `test` - Run all tests with coverage via `nox -s test:coverage`
- `test:unit` - Run unit tests via `nox -s test:unit`
- `test:integration` - Run integration tests via `nox -s test:integration`
- `check` - Run all checks via `nox -s format:check lint:code lint:security lint:typing`

#### Scenario: Developer runs lint locally

- **WHEN** a developer runs `mise run lint`
- **THEN** `nox -s lint:code lint:security` executes
- **AND** the developer sees the same results as CI

#### Scenario: Developer runs full check locally

- **WHEN** a developer runs `mise run check`
- **THEN** format, lint, security, and type checks execute
- **AND** the developer gets comprehensive feedback before pushing

