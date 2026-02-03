<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# Agent Instructions for dbt-exasol

## Build & Test Commands
- Install: `uv sync`
- Run all tests: `uv run pytest -n48` (uses `-n4` parallel by default from pytest.ini)
- Run single test: `pytest tests/functional/adapter/test_basic.py::TestClass::test_method -n0`
- Run with tox: `tox` (tests across Python 3.9-3.12)
- Format: `uv run ruff check .`
- Lint SQL: `uv run sqlfluff lint`

## Code Style
- **Formatting**: ALL code changes MUST conform to the formatting enforced by `nox -s format:check`. Run `nox -s format:fix` to auto-format before committing.
- **Imports**: stdlib first, then third-party, then local. Use `# pylint: disable=` for import order issues.
- **Naming**: PascalCase for classes (`ExasolAdapter`), snake_case for functions/variables, UPPER_CASE for constants.
- **Types**: Use type hints where practical. `# type: ignore` acceptable for dbt base class issues.
- **Errors**: Use dbt exceptions (`DbtRuntimeError`, `DbtDatabaseError`). Use `@contextmanager` for exception handlers.
- **Dataclasses**: Use `@dataclass` for data models (credentials, columns, relations).
- **Tests**: Inherit from dbt base test classes. Use fixtures and module-level string constants for test data.
- **Docstrings**: Include module and class docstrings. Method docstrings optional but encouraged.
