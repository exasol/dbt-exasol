# Agent Instructions for dbt-exasol

## Build & Test Commands
- Install: `uv sync`
- Run all tests: `uv run pytest -n48` (uses `-n4` parallel by default from pytest.ini)
- Run single test: `pytest tests/functional/adapter/test_basic.py::TestClass::test_method -n0`
- Run with tox: `tox` (tests across Python 3.9-3.12)
- Format: `uv run ruff check .`
- Lint SQL: `uv run sqlfluff lint`

## Code Style
- **Imports**: stdlib first, then third-party, then local. Use `# pylint: disable=` for import order issues.
- **Naming**: PascalCase for classes (`ExasolAdapter`), snake_case for functions/variables, UPPER_CASE for constants.
- **Types**: Use type hints where practical. `# type: ignore` acceptable for dbt base class issues.
- **Errors**: Use dbt exceptions (`DbtRuntimeError`, `DbtDatabaseError`). Use `@contextmanager` for exception handlers.
- **Dataclasses**: Use `@dataclass` for data models (credentials, columns, relations).
- **Tests**: Inherit from dbt base test classes. Use fixtures and module-level string constants for test data.
- **Docstrings**: Include module and class docstrings. Method docstrings optional but encouraged.
