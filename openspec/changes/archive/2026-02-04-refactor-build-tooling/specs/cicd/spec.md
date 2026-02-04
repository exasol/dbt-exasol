## MODIFIED Requirements

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
