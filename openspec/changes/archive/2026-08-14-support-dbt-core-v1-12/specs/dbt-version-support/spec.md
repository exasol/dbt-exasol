## ADDED Requirements

### Requirement: Supported dbt-core version range
The adapter SHALL declare a runtime dependency on dbt-core in the 1.12 line, expressed as `dbt-core>=1.12.0b1,<1.13`. The lower bound permits installation of the dbt-core 1.12 pre-release(s) currently published on PyPI and upgrades automatically to the stable `1.12.0` once released. The upper bound `<1.13` SHALL prevent resolution to the dbt-core 2.0 line (including `2.0.0a1`), which would otherwise satisfy a `<2.0` constraint under pre-release resolution.

#### Scenario: Installs the dbt-core 1.12 beta
- **WHEN** dependencies are resolved with the project's pre-release policy active
- **THEN** dbt-core resolves to a `1.12.x` release (e.g. `1.12.0b2`)
- **AND** dbt-core SHALL NOT resolve to any `2.0.0` pre-release or final.

#### Scenario: Upgrades to stable 1.12.0 when available
- **WHEN** a stable `dbt-core==1.12.0` is published and the lock is refreshed
- **THEN** the `>=1.12.0b1,<1.13` constraint SHALL resolve to `1.12.0` without a specifier change.

### Requirement: Supported dbt-adapters and dbt-tests-adapter versions
The adapter SHALL depend on `dbt-adapters>=1.24.1` (the floor required by dbt-core 1.12 and the line carrying the v1.12 adapter features) and, for development, on `dbt-tests-adapter>=1.20.0` (the line that ships the empty-seed adapter test suite). These packages are versioned independently of dbt-core and MUST NOT be pinned to a "1.12" tag.

#### Scenario: Adapter imports against the bumped dependencies
- **WHEN** `dbt.adapters.exasol.impl.ExasolAdapter` is imported against `dbt-adapters>=1.24.1`
- **THEN** the import SHALL succeed
- **AND** the adapter SHALL have no unimplemented abstract methods.

### Requirement: Scoped pre-release resolution policy
The project SHALL configure uv with `prerelease = "explicit"` so that pre-release versions are permitted only for dependencies whose version specifier explicitly contains a pre-release marker. Enabling the dbt-core 1.12 beta SHALL NOT cause other dependencies to resolve to pre-release versions.

#### Scenario: Pre-release allowance is limited to dbt-core
- **WHEN** the dependency set is resolved with `prerelease = "explicit"` and only `dbt-core` carries a pre-release marker in its specifier
- **THEN** dbt-core MAY resolve to a pre-release
- **AND** every other dependency SHALL resolve to a stable (non-pre-release) version.
