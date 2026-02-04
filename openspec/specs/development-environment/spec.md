# development-environment Specification

## Purpose
TBD - created by archiving change replace-devbox-with-mise. Update Purpose after archive.
## Requirements
### Requirement: Tool Management
The development environment SHALL be managed by `mise-en-place`.

#### Scenario: Install dependencies
- **WHEN** a developer runs `mise install`
- **THEN** `uv`, `gh`, `bun`, and `usage` are installed with specified versions.

#### Scenario: Tool version constraints
- **WHEN** tools are defined in `mise.toml`
- **THEN** each tool SHOULD have a version constraint (e.g., `"latest"`, `"0.4"`, `"2.x"`).

### Requirement: Environment Configuration
The system SHALL configure environment variables automatically using mise-native features.

#### Scenario: Load default environment
- **WHEN** `test.env` exists in the project root
- **THEN** variables from `test.env` are loaded as defaults via `env._.file`.

#### Scenario: Load local overrides
- **WHEN** a `.env` file exists in the project root
- **THEN** variables from `.env` are loaded and override `test.env` values.
- **AND** `.env` SHALL be listed in `.gitignore`.

#### Scenario: Docker SSH Tunnel (conditional)
- **WHEN** `DOCKER_SSH_HOST` is set in the environment (before mise loads)
- **THEN** `DOCKER_HOST` is set to `ssh://${DOCKER_SSH_HOST}` using mise templates.
- **AND** `DOCKER_BUILDKIT` is set to `1`.
- **AND** `DOCKER_API_VERSION` is set to `1.41`.

### Requirement: Required Environment Variables
The development environment SHALL use mise's native `required` directive to enforce mandatory variables.

#### Scenario: dbt connection variables
- **WHEN** the environment is loaded
- **THEN** `DBT_DSN`, `DBT_USER`, and `DBT_PASS` MUST be defined.
- **AND** if missing, mise SHALL display a helpful error message.

#### Scenario: dbt test role variables
- **WHEN** the environment is loaded
- **THEN** `DBT_TEST_USER_1`, `DBT_TEST_USER_2`, and `DBT_TEST_USER_3` MUST be defined.

#### Scenario: Exasol release variable
- **WHEN** the environment is loaded
- **THEN** `EXASOL_RELEASE` MUST be defined.

### Requirement: Task Management
The system SHALL provide standard development tasks via mise with descriptions.

#### Scenario: Run tests
- **WHEN** `mise run test` is executed
- **THEN** `uv run pytest -n48` is run.
- **AND** the task SHALL have a description for discoverability.

#### Scenario: Run Nox
- **WHEN** `mise run nox` is executed
- **THEN** `uv run nox` is run, passing any arguments.

#### Scenario: Sync dependencies
- **WHEN** `mise run sync` is executed
- **THEN** `uv sync` is run.

#### Scenario: Linting
- **WHEN** `mise run lint` is executed
- **THEN** both `uv run ruff check .` and `uv run sqlfluff lint` are run.

### Requirement: Developer Onboarding
The system SHALL document the setup process for new developers.

#### Scenario: Shell activation
- **WHEN** a developer sets up the project
- **THEN** README SHALL document adding `eval "$(mise activate <shell>)"` to their shell rc file.

#### Scenario: Trust configuration
- **WHEN** a developer clones the repository
- **THEN** README SHALL document running `mise trust` to trust the project configuration.

#### Scenario: Local overrides
- **WHEN** a developer needs project-specific settings
- **THEN** they MAY create `mise.local.toml` which is gitignored.

### Requirement: IDE Integration
The system SHALL support IDE autocompletion for configuration.

#### Scenario: JSON schema
- **WHEN** `mise.toml` is created
- **THEN** it SHALL include the JSON schema reference as the first line.

