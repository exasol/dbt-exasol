## MODIFIED Requirements

### Requirement: Continuous Integration

The CI workflow SHALL run automated checks on every pull request to the main branch.

The workflow SHALL execute the following checks in order:
1. Code format validation using `nox -s format:check`
2. Code linting using `nox -s lint:code`
3. Security linting using `nox -s lint:security`
4. Type checking using `nox -s lint:typing`
5. Workflow security auditing using `nox -s workflow:audit`
6. Deprecation auditing using `nox -s lint:deprecations`
7. Unit tests with coverage using `nox -s test:unit -- --coverage`

The workflow SHALL fail if any check fails.

The workflow SHALL dynamically derive runtime matrices from `noxconfig.py` using `nox -s matrix:generate`.

The workflow SHALL support testing across supported Python versions (3.11, 3.12, 3.13, and 3.14).

#### Scenario: PR triggers CI checks

- **WHEN** a pull request is opened or updated against the main branch
- **THEN** the CI workflow runs format, lint, security, typing, workflow security audit, deprecation, and unit test checks
- **AND** the integration test job runs against a single fast matrix combination (Python 3.14, Exasol 8.29.13)
- **AND** the PR status reflects pass/fail of all checks

#### Scenario: Push to main triggers CI

- **WHEN** a commit is pushed directly to the main branch
- **THEN** the CI workflow runs all checks to validate the branch state across the full matrix combinations

#### Scenario: Python matrix derived from noxconfig

- **WHEN** the CI workflow starts
- **THEN** a setup job runs `nox -s matrix:generate -- python_version` to output the Python versions
- **AND** the checks job uses the output as its matrix

### Requirement: Artifact Uploads

The CI workflow SHALL upload test artifacts for debugging and audit purposes.

The workflow SHALL upload:
- Coverage reports (`.coverage`) for each Python version in the test matrix
- Lint results (`.lint.json`)
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

### Requirement: Local CI Testing

The mise environment SHALL provide tasks that delegate to nox sessions for consistent local/CI behavior.

mise SHALL provide the following tasks:
- `lint` - Run linters via `nox -s lint:code lint:security`
- `format` - Auto-fix formatting via `nox -s format:fix`
- `format-check` - Check formatting via `nox -s format:check`
- `test` - Run all tests with coverage via `nox -s test:coverage`
- `test:unit` - Run unit tests via `nox -s test:unit`
- `test:integration` - Run integration tests via `nox -s test:integration`
- `check` - Run all checks via `nox -s format:check lint:code lint:security lint:typing workflow:audit`

#### Scenario: Developer runs lint locally

- **WHEN** a developer runs `mise run lint`
- **THEN** `nox -s lint:code lint:security` executes
- **AND** the developer sees the same results as CI

#### Scenario: Developer runs full check locally

- **WHEN** a developer runs `mise run check`
- **THEN** format, lint, security, typing, and workflow audit checks execute
- **AND** the developer gets comprehensive feedback before pushing

## ADDED Requirements

### Requirement: Multi-Dimensional Integration Testing

The CI workflow SHALL run integration tests across a multi-dimensional matrix combining Python versions and Exasol DB image versions.

The workflow SHALL:
1. Dynamically generate the integration matrix using `nox -s matrix:generate -- python_version exasol_version`.
2. Pass `--db-version <version>` to `nox -s test:integration` for each matrix dimension.
3. Automatically start and stop the corresponding Exasol container version via pre/post integration test hooks.

#### Scenario: Integration test runs against specific Exasol DB version

- **WHEN** an integration matrix job runs with `exasol_version=8.29.13`
- **THEN** `nox -s test:integration` receives `--db-version 8.29.13`
- **AND** `itde spawn-test-environment` starts a container with image version `8.29.13`
- **AND** functional tests run against that database

### Requirement: Workflow Security Configuration

The repository SHALL maintain a `.zizmor.yml` configuration specifying GitHub Actions security policies.

The configuration SHALL:
1. Allow referential version pinning (`ref-pin`) for trusted action prefixes (`actions/*`, `exasol/*`, `astral-sh/*`, `jdx/*`, `dorny/*`).
2. Enforce SHA hash pinning (`hash-pin`) for all other third-party actions.
3. Be verifiable locally and in CI using `nox -s workflow:audit`.

#### Scenario: Valid actions pass security audit

- **WHEN** workflows reference approved actions using version tags matching configured policies
- **THEN** `nox -s workflow:audit` passes with 0 security findings
