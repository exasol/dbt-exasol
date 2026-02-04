# Change: Fix SonarQube and Linting Findings

## Why
The codebase currently has multiple code quality violations identified by SonarQube and linting tools (pylint, ruff). These issues reduce code maintainability, create potential bugs, and prevent the CI pipeline from passing cleanly. Addressing these findings will improve code quality, ensure compliance with project standards, and enable stricter quality gates.

## What Changes
- Fix Python import positioning and ordering across all modules
- Add missing module and class docstrings
- Resolve naming convention violations (variables, constants, classes)
- Remove commented-out code and empty code blocks
- Replace duplicate string literals with constants
- Implement missing abstract methods for Python submission support
- Fix SQL/Jinja macro formatting issues (illegal newline characters)
- Remove unnecessary `else`/`elif` after `return` statements
- Eliminate unused imports and global statement usage
- Resolve line-too-long violations

**BREAKING**: None - all changes are internal code quality improvements

## Impact
- **Affected specs**: `quality`
- **Affected code**:
  - `dbt/adapters/exasol/connections.py` (imports, docstrings, duplicate literals, commented code)
  - `dbt/adapters/exasol/impl.py` (naming, docstrings, abstract methods, imports, global statements, empty blocks)
  - `dbt/adapters/exasol/__init__.py` (docstrings, naming)
  - `dbt/adapters/exasol/__version__.py` (docstrings, naming)
  - `dbt/adapters/exasol/column.py` (import order)
  - `dbt/adapters/exasol/relation.py` (line length)
  - `dbt/include/exasol/macros/materializations/snapshot.sql` (duplicate literals)
  - `dbt/include/exasol/macros/adapters.sql` (illegal newline in literal)
  - `dbt/include/exasol/macros/apply_grants.sql` (illegal newline in literal)
- **CI/CD Impact**: All linting checks (`nox -s lint:code`, `lint:security`, `lint:typing`) will pass cleanly after this change
