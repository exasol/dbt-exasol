# Proposal: Fix Critical Issues and Code Quality

## Summary
This proposal addresses critical code quality issues and style violations identified in the recent code review (review_glm.md). The primary focus is fixing a critical bare `except` clause that can mask system errors, removing unused imports, and applying consistent SQL formatting across the codebase.

## Motivation
- **Reliability:** A bare `except` clause in `connections.py` catches `SystemExit` and `KeyboardInterrupt`, preventing graceful shutdown and potentially masking unrelated errors.
- **Maintainability:** Unused imports and inconsistent code style make the codebase harder to read and maintain.
- **Consistency:** Enforcing SQL formatting ensures that generated and macro SQL follows a standard style, reducing cognitive load during reviews.

## Proposed Solution
1.  **Refactor Error Handling:** Replace the bare `except` in `connections.py` with specific exception handling (`ValueError`, `KeyError`, etc.).
2.  **Clean Up Python Code:** Use `ruff` to automatically remove unused imports and fix other linting errors.
3.  **Format SQL:** Use `sqlfluff` to auto-format Jinja/SQL macros in `dbt/include/exasol/macros`.
4.  **Refine Imports:** Explicitly define `__all__` or remove unused exports in `__init__.py`.
5.  **Fix Empty Identifier Crash:** Add a length check to `is_valid_identifier()` in `impl.py` to prevent crash on empty string input.

## Out of Scope
- Adding new unit tests (deferred to a separate proposal to keep this focused on cleanup).
- Refactoring `snapshot.sql` (deferred to a separate proposal).
- Implementing credential redaction (deferred to a separate proposal).
