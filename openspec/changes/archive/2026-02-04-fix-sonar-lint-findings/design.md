# Design: Fix SonarQube and Linting Findings

## Context
This change addresses technical debt accumulated from incomplete linting enforcement and SonarQube integration. The project already has comprehensive linting infrastructure (`ruff`, `pylint`, `sqlfluff`, `bandit`) configured in `nox` sessions, but not all violations have been resolved. SonarQube analysis has surfaced additional quality issues including code smells, duplicated literals, and formatting inconsistencies.

The work spans multiple module types:
- Python adapter modules (connections, impl, column, relation)
- Package metadata modules (__init__.py, __version__.py)
- Jinja2/SQL macro templates

## Goals / Non-Goals

**Goals:**
- Eliminate all fixable pylint, ruff, and SonarQube violations
- Enable strict linting gates in CI without exceptions
- Improve code readability and maintainability
- Implement or properly stub missing abstract methods
- Establish patterns for constants vs literals in Jinja macros

**Non-Goals:**
- Refactoring adapter architecture (e.g., reducing `too-many-ancestors` through inheritance changes)
- Adding new features or changing behavior
- Addressing dbt-core base class design issues (`# type: ignore` may still be needed)
- Comprehensive docstring coverage beyond fixing missing ones flagged by linters

## Decisions

### 1. Abstract Method Implementation Strategy
**Decision**: Implement stub methods for Python submission support that raise `NotImplementedError` with clear messages.

**Rationale**:
- Exasol does not currently support dbt Python models
- Leaving methods unimplemented causes linter/IDE errors
- Explicit `NotImplementedError` provides clear user feedback if someone attempts to use the feature
- Allows future implementation without breaking changes

**Alternatives considered**:
- Ignoring the abstract method warnings → Creates confusing type checker errors
- Implementing full Python submission support → Out of scope, requires Exasol UDF research

### 2. Duplicate Literal Handling in Jinja Macros
**Decision**: Use Jinja `{% set %}` variables at the top of macro files for frequently repeated literals.

**Rationale**:
- SonarQube flags 3+ occurrences of same literal as code smell
- Jinja2 doesn't support module-level constants like Python
- `{% set %}` variables provide named references within macro scope
- Improves maintainability (change once vs. change everywhere)

**Example**:
```jinja
{% set SNAPSHOT_META_COLUMN_NAMES = 'dbt_scd_id,dbt_updated_at,dbt_valid_from,dbt_valid_to' %}
```

**Alternatives considered**:
- Suppressing SonarQube rules → Hides legitimate maintainability issues
- Creating separate macro library for constants → Overkill for this use case

### 3. Import Ordering and Organization
**Decision**: Enforce ruff/isort rules strictly: stdlib → third-party → local, with blank lines between groups.

**Rationale**:
- Already configured in `pyproject.toml`
- Automated by `nox -s format:fix`
- Industry standard (PEP 8 recommendation)
- Improves readability and merge conflict resolution

**Implementation**:
- Run `ruff check --fix` for automatic reordering
- Manually verify `pyexasol` import placement (should be in third-party group, not top-of-file special case)

### 4. Naming Conventions
**Decision**: Follow strict PEP 8 naming:
- Constants: `UPPER_CASE` (e.g., `VERSION`, `PLUGIN`, `EXASOL_KEYWORDS`)
- Variables/functions: `snake_case`
- Classes: `PascalCase`

**Rationale**:
- Aligns with Python ecosystem standards
- Improves code scanning and IDE support
- `ExasolKeywords` → `EXASOL_KEYWORDS` signals immutability

**Migration**:
- Rename in source files
- Check for any internal references (unlikely for these cases)

### 5. Handling `too-many-ancestors` Warning
**Decision**: Document the inheritance chain and suppress with `# pylint: disable=too-many-ancestors` if necessary.

**Rationale**:
- `ExasolAdapter` inherits from dbt-core's `SQLAdapter`, which has a deep chain
- Restructuring would require changes to dbt-adapters base classes (out of scope)
- The inheritance depth is unavoidable for dbt adapter pattern compliance
- Documenting the reason is more valuable than forcing arbitrary limits

### 6. SQL Newline Character Issues
**Decision**: Replace multi-line strings in Jinja with explicit concatenation or single-line strings.

**Rationale**:
- SonarQube flags literal newlines (`\n` as character code 10) in SQL string literals
- SQL syntax allows string concatenation or single-line formatting
- Improves SQL portability and tooling compatibility

**Example fix**:
```jinja
{# Before #}
{% set sql = "SELECT *
FROM table" %}

{# After #}
{% set sql = "SELECT * FROM table" %}
```

## Risks / Trade-offs

### Risk: Breaking Change from Renaming
**Mitigation**: Review all renamed identifiers for external references. Constants like `version` and `Plugin` are likely only used internally within package initialization.

### Risk: Incomplete Abstract Method Stubs
**Mitigation**: Add comprehensive docstrings explaining why methods are not implemented and what would be required for future support.

### Risk: Over-suppression of Warnings
**Mitigation**: Only use `# pylint: disable` or `# type: ignore` with inline comments explaining why suppression is necessary (e.g., "Bandit false positive: 'password' is field name, not hardcoded credential").

### Trade-off: Jinja Constant Verbosity
Introducing `{% set %}` variables at file tops adds lines but significantly improves maintainability. This is acceptable given the duplication levels (7-13 occurrences).

## Migration Plan

**Phase 1: Automated Fixes**
1. Run `nox -s format:fix` to auto-fix import ordering and formatting
2. Run `ruff check --fix` for additional auto-fixable issues
3. Commit automated changes separately for easy review

**Phase 2: Manual Fixes**
1. Add docstrings (modules, classes, methods)
2. Rename constants (VERSION, PLUGIN, EXASOL_KEYWORDS)
3. Define literal constants in connections.py and macros
4. Remove commented code and empty blocks
5. Implement abstract method stubs
6. Fix control flow issues (unnecessary else after return)

**Phase 3: Validation**
1. Run all lint sessions and fix any remaining issues
2. Run test suite to catch regressions
3. Verify SonarQube scan improvements

**Rollback**: All changes are code-quality improvements without behavior changes. Rollback is straightforward git revert.

## Open Questions

1. **Should `ExasolKeywords` remain a class or become a module-level set constant?**
   - Current: Class with class variable
   - Option: `EXASOL_KEYWORDS = frozenset([...])`
   - Recommendation: Keep as class for namespace organization, but rename to follow convention if pylint requires it

2. **What is the acceptable approach for the global statement usage in impl.py?**
   - Need to review context (likely in keyword checking or caching)
   - Options: Remove global, use class variable, use function parameter
   - Recommendation: Review code and refactor to class-level state if possible

3. **Should the password field Bandit warning be suppressed or documented differently?**
   - Current: Likely flagging `password: str` field in Credentials dataclass
   - Recommendation: Add `# nosec B105` comment with explanation: "Field name for user-provided credential, not a hardcoded password"
