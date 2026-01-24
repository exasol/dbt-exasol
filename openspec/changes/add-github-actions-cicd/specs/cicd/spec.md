## ADDED Requirements

### Requirement: Continuous Integration

The CI workflow SHALL run automated checks on every pull request to the main branch.

The workflow SHALL execute the following checks in order:
1. Code format validation using `nox -s format:check`
2. Code linting using `nox -s lint:code`
3. Unit tests with coverage using `nox -s test:unit -- --coverage`

The workflow SHALL fail if any check fails or coverage drops below 80%.

#### Scenario: PR triggers CI checks

- **WHEN** a pull request is opened against the main branch
- **THEN** the CI workflow runs format, lint, and unit test checks
- **AND** the PR status reflects pass/fail of all checks

#### Scenario: Push to main triggers CI

- **WHEN** a commit is pushed directly to the main branch
- **THEN** the CI workflow runs all checks to validate the branch state

### Requirement: PR Result Documentation

The CI workflow SHALL post a comment on each pull request with check results.

The comment SHALL include:
- Format check status (pass/fail)
- Lint check status (pass/fail)
- Test status (pass/fail)
- Coverage percentage

#### Scenario: CI posts results comment on PR

- **WHEN** the CI workflow completes on a pull request
- **THEN** a comment is posted to the PR with format/lint/test/coverage results
- **AND** each result shows pass or fail status

#### Scenario: CI results visible without leaving PR

- **WHEN** a reviewer views a pull request
- **THEN** the CI results are visible in the PR comments
- **AND** the reviewer can assess quality without navigating to the Actions tab

### Requirement: Coverage Enforcement

The CI workflow SHALL enforce a minimum code coverage threshold.

The threshold SHALL be 80%.

The workflow SHALL fail if the coverage percentage is below the configured threshold.

#### Scenario: Coverage above threshold passes

- **WHEN** unit tests complete with 85% coverage
- **THEN** the coverage check passes
- **AND** the PR comment shows "85%" coverage

#### Scenario: Coverage below threshold fails

- **WHEN** unit tests complete with 55% coverage
- **THEN** the coverage check fails
- **AND** the workflow fails with coverage error
- **AND** the PR comment shows "55%" coverage

### Requirement: Artifact Uploads

The CI workflow SHALL upload test artifacts for debugging and audit purposes.

The workflow SHALL upload:
- Coverage reports (`coverage.json`) for each Python version in the test matrix
- Test result files if available

Artifacts SHALL be retained for 30 days.

#### Scenario: Coverage report uploaded

- **WHEN** the CI workflow completes unit tests with coverage
- **THEN** the coverage.json file is uploaded as an artifact
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

The devbox environment SHALL include `act` for testing GitHub Actions workflows locally.

Devbox SHALL provide convenience scripts for running CI steps:
- `format` - Run format check
- `lint` - Run linting
- `unit-test` - Run unit tests
- `coverage` - Run unit tests with coverage report
- `ci` - Run complete CI pipeline
- `act` - Run GitHub Actions workflow locally using `act`

#### Scenario: Developer runs CI locally

- **WHEN** a developer runs `devbox run ci`
- **THEN** format check, lint, and unit tests with coverage execute locally
- **AND** the developer sees the same results as CI would produce

#### Scenario: Developer tests workflow with act

- **WHEN** a developer runs `devbox run act`
- **THEN** the GitHub Actions CI workflow runs in a local Docker container
- **AND** the developer can validate workflow changes before pushing

#### Scenario: Developer runs individual CI step

- **WHEN** a developer runs `devbox run lint`
- **THEN** only the linting step executes
- **AND** the developer gets fast feedback on a specific check
