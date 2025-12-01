# Agent Guidelines for dbt-exasol

## Data Build Tool - adapter for Exasol 

- www.exasol.com - data platform 
- conforms to https://github.com/dbt-labs/dbt-adapters/tree/main/dbt-adapters
- adapter guide: https://docs.getdbt.com/guides/adapter-creation?step=1
- tested according to https://github.com/dbt-labs/dbt-adapters/tree/main/dbt-tests-adapter

## Build, Lint & Test Commands

**Run all tests:**
```bash
devbox run pytest
```


**Run a single test:**
```bash
devbox run pytest test_name.py::TestClass::test_method
```

**Run tests for a specific adapter feature:**
```bash
devbox run pytest -n4
```

**Lint with pylint:**
```bash
devbox run pylint dbt
pylint dbt/
```

**Format with black:**
```bash
devbox run ruff .
```

## Code Style Guidelines

**Imports:** Group imports as: stdlib → third-party → dbt → local. Disable pylint rules for wrong-import-order if needed (see `# pylint: disable=wrong-import-order`).

**Formatting:** Use Black for code formatting (target line length: 88 chars). Disable specific pylint warnings with `# pylint: disable=<rule>` when necessary.

**Type Hints:** Use Python type hints throughout (from `typing` module). Include docstrings for public functions/classes using triple-quoted format.

**Naming:** Use snake_case for functions/variables, PascalCase for classes. Prefix private methods with underscore `_`.

**Error Handling:** Raise `dbt_common.exceptions.CompilationError` for dbt-related errors. Use `AdapterLogger` (initialized as `LOGGER = AdapterLogger("<module>")`) for logging.

**SQL/Macros:** Store Jinja2 SQL macros in `dbt/include/exasol/macros/`. Follow dbt materialization patterns (table, incremental, view, snapshot).

**Testing:** Inherit from `dbt.tests.base` test classes. Store test fixtures in `tests/functional/adapter/fixtures/`. Use pytest with `-n4` for parallel execution (xdist).
