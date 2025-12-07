# dbt-exasol Security & Code Quality Issues

Analysis Date: 2025-12-07

## HIGH Priority Issues

| # | Category | Location | Description |
|---|----------|----------|-------------|
| 1 | **Credentials** | `okteto.yml:11-12` | Hardcoded database credentials (`sys`/`start123`) in version control |
| 2 | **Exception Handling** | `connections.py:217` | Bare `except:` clause catches all exceptions including `SystemExit`, `KeyboardInterrupt` |
| 3 | **SQL Injection Risk** | `adapters.sql:27,61,123-124` | Schema/identifier values directly interpolated without proper quoting in SQL WHERE clauses |
| 4 | **Missing Identifier Quoting** | `adapters.sql:53,71,82,92,104` | DDL statements use unquoted identifiers - fails with reserved words/special chars |
| 5 | **SQL Injection Risk** | `metadata.sql:12-13`, `apply_grants.sql:4-5` | Direct string interpolation in WHERE clauses |
| 6 | **Test Bug** | `test_dbt_debug.py:32` | Assertion always passes: `assert "Using profiles dir at NONE"` (missing comparison) |

## MEDIUM Priority Issues

| # | Category | Location | Description |
|---|----------|----------|-------------|
| 7 | **SQL Injection** | `connections.py:253-254` | `timestamp_format` from user config directly interpolated into SQL |
| 8 | **Input Validation** | `impl.py:127-139` | `is_valid_identifier()` crashes on empty string (no bounds check) |
| 9 | **Dependencies** | `pyproject.toml` | `pyexasol>=1.0.0` has no upper bound - allows breaking major versions |
| 10 | **Dependencies** | `pyproject.toml` | `dbt-adapters`, `dbt-core` have no upper bounds |
| 11 | **Race Conditions** | `incremental.sql:22-31`, `snapshot.sql:254-256` | Non-atomic DDL operations (drop + rename, check + create schema) |
| 12 | **Environment** | `tox.ini:9` | `passenv = *` exposes all env vars to test environments |
| 13 | **Empty Tests** | `constraints/test_constraints.py:83-92,106-115,129-138` | Three `test__constraints_wrong_column_data_types` methods have `pass` body |
| 14 | **Test Naming** | `debug/test_dbt_debug.py:13` | Typo: `TestDebugInvliadProjectExasol` (should be "Invalid") |
| 15 | **Test Naming** | `debug/test_dbt_debug.py:49,53` | Classes named `*Postgres` but testing Exasol |
| 16 | **Code Smell** | `connections.py:308-313` | Magic string separators (`\|SEPARATEMEPLEASE\|`, `0CSV\|`) are fragile |
| 17 | **Error Handling** | `adapters.sql:110` | `truncate table {{ relation \| replace('"', '') }}` silently strips quotes |
| 18 | **Input Validation** | `impl.py:96-103` | `interval` parameter in `timestamp_add_sql` not validated against allowed values |

## LOW Priority Issues

| # | Category | Location | Description |
|---|----------|----------|-------------|
| 19 | **Logging** | `connections.py:155` | SQL logged at DEBUG level on error - potential sensitive data exposure |
| 20 | **SSL** | `connections.py:231-232` | `CERT_NONE` option available (intentional but should warn users) |
| 21 | **Dependencies** | `pyproject.toml` | Test deps (`pytest`, `pytest-xdist`) in main dependencies instead of dev |
| 22 | **Dependencies** | `pyproject.toml` | `tox` has conflicting min versions (`>=4.30.3` vs `>=3.26.0`) |
| 23 | **Test Fixtures** | Multiple test files | `dbt_profile_target` fixture duplicated in 7+ locations |
| 24 | **Test Isolation** | `test_snapshot_hard_deletes.py:178-211` | Tests depend on shared state - order-dependent |
| 25 | **Code Duplication** | `snapshot.sql:45-49,152-156,204-208` | `dbt_valid_to_current` check pattern duplicated 3 times |
| 26 | **Code Duplication** | `catalog.sql:4-15,26-37` | CTE structure duplicated between `get_catalog` variants |
| 27 | **Reproducibility** | `devbox.json:3-6` | `@latest` versions make builds non-reproducible |
| 28 | **xfail Tests** | `test_utils.py:47-59,107-109` | `@pytest.mark.xfail` without `reason` parameter |
| 29 | **Unused Import** | `test_unit_testing.py:1` | `os` module imported but never used |
| 30 | **Test Cleanup** | `test_docs_generate.py:376-384` | Env var cleanup could fail if setup errors first |
| 31 | **Syntax Error** | `constraints/fixtures.py:176-186` | `my_model_view_wrong_data_type_sql` has trailing `)` without opening |
| 32 | **Missing .gitignore** | `.gitignore` | Missing entries for `*.pem`, `*.key`, `profiles.yml`, `.secrets` |
| 33 | **Test Coverage** | Multiple | Missing edge cases: NULL unique keys, empty results, concurrent modifications |

---

## Remediation Plan

### Phase 1: Critical Security Fixes (Immediate)

#### 1.1 Remove Hardcoded Credentials (Issue #1)
- Remove credentials from `okteto.yml`
- Use Okteto secrets management or environment variable references
- Consider adding `okteto.yml` to `.gitignore` if it contains environment-specific values
- Audit git history for credential exposure

#### 1.2 Fix Exception Handling (Issue #2)
```python
# connections.py:217 - Change from:
except:
# To:
except (ValueError, KeyError) as e:
```

#### 1.3 Fix Test Assertion Bug (Issue #6)
```python
# test_dbt_debug.py:32 - Change from:
assert "Using profiles dir at NONE"
# To:
assert "Using profiles dir at NONE" in out
```

### Phase 2: SQL Security Hardening (Short-term)

#### 2.1 Identifier Quoting in Macros (Issues #3, #4, #5)
- Audit all macro files for unquoted identifiers
- Use `adapter.quote()` or `{{ relation.render() }}` consistently
- Create helper macro for safe identifier rendering if needed

#### 2.2 Input Validation (Issues #7, #8, #18)
- Validate `timestamp_format` against whitelist before SQL interpolation
- Add empty string check to `is_valid_identifier()`
- Validate `interval` parameter against allowed SQL interval keywords

### Phase 3: Dependency & Configuration Cleanup (Medium-term)

#### 3.1 Pin Dependencies (Issues #9, #10)
```toml
# pyproject.toml - Add upper bounds:
"pyexasol>=1.0.0,<2.0"
"dbt-adapters>=1.10.0,<2.0"
"dbt-core>=1.10.0,<2.0"
```

#### 3.2 Reorganize Dependencies (Issues #21, #22)
- Move test dependencies to `[project.optional-dependencies.dev]`
- Resolve conflicting `tox` version constraints

#### 3.3 Restrict Environment Passthrough (Issue #12)
```ini
# tox.ini - Change from:
passenv = *
# To:
passenv = DBT_*, EXASOL_*, HOME, PATH
```

### Phase 4: Test Quality Improvements (Ongoing)

#### 4.1 Fix Test Issues (Issues #13, #14, #15, #28, #29)
- Implement or document empty constraint tests
- Fix typo: `TestDebugInvliadProjectExasol` → `TestDebugInvalidProjectExasol`
- Rename `*Postgres` test classes to `*Exasol`
- Add `reason` to all `@pytest.mark.xfail` decorators
- Remove unused imports

#### 4.2 Consolidate Test Fixtures (Issue #23)
- Create shared `dbt_profile_target` fixture in `conftest.py`
- Remove duplicates from individual test files
- Use parameterized fixtures for variations

#### 4.3 Improve Test Isolation (Issue #24)
- Ensure snapshot tests don't depend on execution order
- Reset state at beginning of each test or use separate classes

### Phase 5: Code Quality & Maintenance (Long-term)

#### 5.1 Reduce Code Duplication (Issues #25, #26)
- Extract `dbt_valid_to_current` check into helper macro
- Consolidate `get_catalog` CTE structures

#### 5.2 Documentation & Hardening (Issues #16, #19, #20, #32)
- Document magic string separators or refactor to robust patterns
- Add warning log when certificate validation disabled
- Evaluate DEBUG logging for SQL sensitivity
- Add missing entries to `.gitignore`

#### 5.3 Build Reproducibility (Issue #27)
- Pin devbox package versions
- Document version requirements

---

## Notes

### Acceptable Patterns (Not Issues)
- `_connection_keys()` correctly excludes passwords/tokens from logging
- SSL encryption enabled by default
- Certificate validation enabled by default
- Standard dbt Jinja patterns using `relation` objects from validated upstream sources

### Exasol-Specific Considerations
- Magic string separators are workarounds for Exasol limitations
- Some identifier patterns are standard dbt conventions
- Race conditions in DDL may be unavoidable without database-level transaction support
