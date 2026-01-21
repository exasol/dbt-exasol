# Project Context

## Purpose
This project, `dbt-exasol`, is a **dbt adapter** that enables `dbt-core` to interact with the **Exasol** analytical database. It allows data analysts and engineers to transform data within Exasol using dbt's software engineering practices (modular SQL, testing, version control).

## Tech Stack
- **Language:** Python 3.9 - 3.12
- **Core Frameworks:**
  - `dbt-core` (Data Build Tool)
  - `dbt-adapters` (Base adapter logic)
  - `pyexasol` (Python driver for Exasol)
- **Build & Packaging:**
  - `hatchling` (Build backend)
  - `uv` (Dependency management)
- **Testing & Quality:**
  - `pytest` (Test runner)
  - `tox` (Multi-environment testing)
  - `sqlfluff` (SQL Linter)
  - `ruff` (Python Linter/Formatter)

## Project Conventions

### Code Style
- **Python:** Follows standard PEP 8 with specific dbt adapter conventions.
  - **Imports:** Standard library first, then third-party, then local `dbt` imports.
  - **Naming:** `PascalCase` for adapter classes (e.g., `ExasolAdapter`), `snake_case` for methods/variables.
  - **Type Hinting:** Strongly encouraged for all new code. Use `dbt-core` types where applicable.
  - **Docstrings:** Required for modules and classes; encouraged for complex methods.

### Architecture Patterns
- **Adapter Pattern:** Inherits from `dbt.adapters` base classes (`Adapter`, `Credentials`, `ConnectionManager`).
- **SQL Generation:** Uses Jinja2 templates located in `dbt/include/exasol/macros`.
- **Microbatching:** Implements specific strategies for Exasol (e.g., DELETE+INSERT transactions) to handle large datasets.
- **Shim Packages:** Relies on `exasol-utils` for compatibility with `dbt-utils`.

### Testing Strategy
- **Functional Tests:** Inherit from `dbt-tests-adapter` to verify adapter compliance with dbt core features.
- **Parallel Execution:** Uses `pytest-xdist` (default `-n4` or `-n48`) for faster test runs.
- **Environment:** Requires an Exasol database instance (configured in `test.env` or environment variables).

### Git Workflow
- **Versioning:** Semantic versioning matching `dbt-core` minor versions (e.g., `1.10.x`).
- **Contributions:** Pull Request based workflow.
- **Issues:** GitHub Issues for bug tracking.

## Domain Context
- **Exasol Behavior:**
  - **NULL Handling:** Empty strings `''` are treated as `NULL`.
  - **Timestamps:** Do not support timezone suffixes (e.g., `+00:00`). Adapter handles stripping these.
  - **Constraints:** `NOT NULL`, `PRIMARY KEY`, `FOREIGN KEY` are enforced. `CHECK` and `UNIQUE` are *not* supported.
  - **Keywords:** `FINAL` is a reserved keyword in Exasol.
- **Unsupported Features:** `split_part` SQL function, `listagg` with `num_part`, Materialized Views, Clones.

## Important Constraints
- **Version Compatibility:** Must maintain compatibility with specific `dbt-core` versions (see README matrix).
- **Encryption:** Exasol 8+ enforces encryption by default; adapter defaults to `encryption=True`.
- **License:** Apache License 2.0 (changed from GPLv3 in v1.8).

## External Dependencies
- **Exasol Database:** Target data warehouse (versions 7.x, 8.x).
- **dbt-core:** The core dbt logic that this adapter extends.
