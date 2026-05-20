## ADDED Requirements

### Requirement: dbt-core v1.11 Compatibility
The development environment SHALL support dbt-core v1.11.x and dbt-adapters v1.11.x.

#### Scenario: Dependency versions updated
- **GIVEN** a `pyproject.toml` with dependency constraints
- **WHEN** the adapter is installed
- **THEN** it requires `dbt-core>=1.11.0` and `dbt-adapters>=1.11.0`

#### Scenario: Test dependencies updated
- **GIVEN** dev dependencies in `pyproject.toml`
- **WHEN** running test suite
- **THEN** `dbt-tests-adapter>=1.11.0` is available

#### Scenario: Version file consistency
- **GIVEN** `pyproject.toml` version set to `1.11.0`
- **WHEN** running `nox -s version:check`
- **THEN** `__version__.py` reports `1.11.0`
- **AND** `version.py` reports MAJOR=1, MINOR=11, PATCH=0

#### Scenario: Behavior change flags compatibility
- **GIVEN** a `dbt_project.yml` with v1.11 behavior flags (`require_unique_project_resource_names`, `require_ref_searches_node_package_before_root`)
- **WHEN** running dbt commands
- **THEN** the adapter does not error (flags are dbt-core level, no adapter changes needed)

#### Scenario: Deprecation warnings handling
- **GIVEN** existing dbt projects with YAML configurations
- **WHEN** running `dbt parse` or `dbt compile`
- **THEN** deprecation warnings from dbt-core v1.11 do not break existing functionality
