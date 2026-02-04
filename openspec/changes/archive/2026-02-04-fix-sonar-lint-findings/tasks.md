# Implementation Tasks

## 1. Python Module Quality - connections.py
- [x] 1.1 Move `from pyexasol import ExaConnection` import to top of file
- [x] 1.2 Add missing class docstring to StrEnum shim
- [x] 1.3 Remove unnecessary `elif` after `return` statements
- [x] 1.4 Remove commented-out code (Line 27: `# from dbt.adapters.base import Credentials`)
- [x] 1.5 Define constant for duplicated literal "Cannot fetch on unset statement" (3 occurrences)
- [x] 1.6 Review and document/suppress Bandit warning for 'password' field name (credential field, not hardcoded password)

## 2. Python Module Quality - impl.py
- [x] 2.1 Fix `invalid-name` for `ExasolKeywords` constant (rename to EXASOL_KEYWORDS or similar UPPER_CASE)
- [x] 2.2 Add missing class docstring for `ExasolAdapter`
- [x] 2.3 Implement or stub missing abstract methods:
  - [x] 2.3.1 `default_python_submission_method`
  - [x] 2.3.2 `generate_python_submission_response`
  - [x] 2.3.3 `get_catalog_for_single_relation`
  - [x] 2.3.4 `python_submission_helpers`
- [x] 2.4 Add missing function docstrings for key methods
- [x] 2.5 Remove or refactor `global-statement` usage
- [x] 2.6 Fix `no-else-return` violations
- [x] 2.7 Fix `wrong-import-order` and `ungrouped-imports`
- [x] 2.8 Remove or fill empty block of code (Line 110)
- [x] 2.9 Document why `too-many-ancestors` (9/7) is acceptable or refactor if feasible

## 3. Python Module Quality - Other Files
- [x] 3.1 Add module docstring to `__init__.py`
- [x] 3.2 Fix `invalid-name` for `Plugin` in `__init__.py` (rename to PLUGIN if constant)
- [x] 3.3 Add module docstring to `__version__.py`
- [x] 3.4 Fix `invalid-name` for `version` in `__version__.py` (rename to VERSION)
- [x] 3.5 Fix `wrong-import-order` in `column.py`
- [x] 3.6 Fix `line-too-long` (138/120) in `relation.py`

## 4. SQL/Jinja Macro Quality
- [x] 4.1 Define constants for duplicate literals in `snapshot.sql`:
  - [x] 4.1.1 Address 7 occurrences of one literal
  - [x] 4.1.2 Address 13 occurrences of another literal
  - [x] 4.1.3 Address 3 occurrences of third literal
- [x] 4.2 Fix illegal newline character (code point 10) in literal in `adapters.sql` (Line 212)
- [x] 4.3 Fix illegal newline character (code point 10) in literal in `apply_grants.sql` (Line 11)

## 5. Validation
- [x] 5.1 Run `nox -s format:check` and verify passing
- [x] 5.2 Run `nox -s lint:code` and verify passing
- [x] 5.3 Run `nox -s lint:security` and verify passing
- [x] 5.4 Run `nox -s lint:typing` and verify passing
- [x] 5.5 Run full test suite to ensure no regressions
- [x] 5.6 Verify SonarQube scan shows improvements

## 6. Documentation
- [x] 6.1 Update any relevant code comments explaining decisions (e.g., suppressed warnings)
- [x] 6.2 Verify all new docstrings follow project conventions
