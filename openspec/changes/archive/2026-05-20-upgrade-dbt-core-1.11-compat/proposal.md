# Change: Upgrade dbt-exasol to dbt-core v1.11 compatibility

## Why
dbt-core v1.11 introduces new features (UDFs, behavior change flags) and deprecations that affect adapter compatibility. Issue #178 requires updating dbt-exasol to support these changes while maintaining backward compatibility for existing projects.

## What Changes

### Dependencies
- **BREAKING**: Bump `dbt-core>=1.11.0` (was >=1.10.0)
- **BREAKING**: Bump `dbt-adapters>=1.11.0` (was >=1.10.0)
- **BREAKING**: Bump `dbt-tests-adapter>=1.11.0` in dev dependencies
- Update `dbt-exasol` version to `1.11.0` in `pyproject.toml` (canonical source)
- Regenerate `__version__.py` and `version.py` via nox

### Behavior Change Flags
- Two new flags are introduced by dbt-core v1.11 (both disabled by default):
  - `require_unique_project_resource_names`
  - `require_ref_searches_node_package_before_root`
- These are user-facing `dbt_project.yml` settings -- no adapter code changes required

### Deprecation Handling
- dbt-core v1.11 enables YAML validation deprecation warnings by default
- Verify existing adapter YAML configs don't trigger false warnings
- No adapter code changes expected -- just test verification

## Impact
- **Affected specs**: `development-environment`
- **Affected code**: `pyproject.toml`, `dbt/adapters/exasol/__version__.py`, `dbt/adapters/exasol/version.py`
- **Risk**: Low -- dependency bumps only, no functional changes to adapter code
- **Backward compatibility**: Breaking for dependency versions, adapter code unchanged

## Dependencies
This change has no dependencies. It must be completed BEFORE `add-udf-function-support`.
