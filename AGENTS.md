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
- Run all tests: `uv run nox -s test:coverage` (or `mise run test`)
- Run unit tests: `uv run nox -s test:unit` (or `mise run test:unit`)
- Run integration tests: `uv run nox -s test:integration` (or `mise run test:integration`)
- Run single test: `pytest test/integration/adapter/test_basic.py::TestClass::test_method -n0`
- Run with tox: `tox` (tests across Python 3.10-3.13)
- Format: `uv run nox -s format:fix` (or `mise run format`)
- Check format: `uv run nox -s format:check` (or `mise run format-check`)
- Lint: `uv run nox -s lint:code lint:security` (or `mise run lint`)
- All checks: `uv run nox -s format:check lint:code lint:security lint:typing` (or `mise run check`)

## Code Style
- **Formatting**: ALL code changes MUST conform to the formatting enforced by `nox -s format:check`. Run `nox -s format:fix` to auto-format before committing.
- **Imports**: stdlib first, then third-party, then local. Use `# pylint: disable=` for import order issues.
- **Naming**: PascalCase for classes (`ExasolAdapter`), snake_case for functions/variables, UPPER_CASE for constants.
- **Types**: Use type hints where practical. `# type: ignore` acceptable for dbt base class issues.
- **Errors**: Use dbt exceptions (`DbtRuntimeError`, `DbtDatabaseError`). Use `@contextmanager` for exception handlers.
- **Dataclasses**: Use `@dataclass` for data models (credentials, columns, relations).
- **Tests**: Inherit from dbt base test classes. Use fixtures and module-level string constants for test data.
- **Docstrings**: Include module and class docstrings. Method docstrings optional but encouraged.
