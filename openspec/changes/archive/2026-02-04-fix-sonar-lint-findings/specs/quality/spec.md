## ADDED Requirements

### Requirement: Module Docstrings
All Python modules in the adapter package SHALL include a module-level docstring explaining the module's purpose.

#### Scenario: Package Metadata Modules
- **GIVEN** the `__init__.py` or `__version__.py` module
- **WHEN** inspected by a linter
- **THEN** a module docstring is present at the top of the file

### Requirement: Class Docstrings
All public classes in the adapter SHALL include a class-level docstring explaining the class's purpose and responsibilities.

#### Scenario: Adapter Implementation Class
- **GIVEN** the `ExasolAdapter` class in `impl.py`
- **WHEN** inspected by a linter
- **THEN** a class docstring is present immediately after the class definition

#### Scenario: Shim Classes
- **GIVEN** compatibility shim classes (e.g., StrEnum backport)
- **WHEN** inspected by a linter
- **THEN** a brief docstring explaining the shim's purpose is present

### Requirement: Import Ordering
All Python modules SHALL organize imports in the standard order: standard library, third-party packages, then local imports, with blank lines separating each group.

#### Scenario: Connections Module Imports
- **GIVEN** the `connections.py` module
- **WHEN** imports are organized
- **THEN** `pyexasol` appears in the third-party group, not as a special import at arbitrary locations
- **AND** `dbt` imports appear in the local group

#### Scenario: Automated Formatting
- **GIVEN** any Python module with imports
- **WHEN** `ruff check --fix` is run
- **THEN** imports are automatically reordered to comply with PEP 8

### Requirement: Naming Conventions
Python identifiers SHALL follow PEP 8 naming conventions: `UPPER_CASE` for constants, `snake_case` for variables and functions, `PascalCase` for classes.

#### Scenario: Version Constant
- **GIVEN** the package version identifier in `__version__.py`
- **WHEN** the module is imported
- **THEN** the identifier is named `VERSION` (not `version`)

#### Scenario: Plugin Constant
- **GIVEN** the plugin registration constant in `__init__.py`
- **WHEN** the module is imported
- **THEN** the identifier is named `PLUGIN` (not `Plugin`) if it is a constant

#### Scenario: Keyword Set
- **GIVEN** the Exasol reserved keywords collection in `impl.py`
- **WHEN** referenced in code
- **THEN** the identifier follows `UPPER_CASE` convention (e.g., `EXASOL_KEYWORDS`)

### Requirement: No Commented-Out Code
Production code SHALL NOT contain commented-out code blocks unless they are annotated with a clear reason for preservation (e.g., migration notes, historical context with issue reference).

#### Scenario: Removed Imports
- **GIVEN** the `connections.py` module
- **WHEN** inspected for commented code
- **THEN** the line `# from dbt.adapters.base import Credentials` is removed or annotated with a reason

### Requirement: String Literal Constants
Frequently repeated string literals (3+ occurrences) SHALL be extracted into named constants to improve maintainability.

#### Scenario: Error Message Constant in Python
- **GIVEN** the error message "Cannot fetch on unset statement" appearing 3 times in `connections.py`
- **WHEN** the module is refactored
- **THEN** a module-level constant `_UNSET_STATEMENT_ERROR` is defined and used in all locations

#### Scenario: Jinja Macro Constants
- **GIVEN** a string literal repeated 7+ times in `snapshot.sql`
- **WHEN** the macro is refactored
- **THEN** a Jinja `{% set %}` variable is defined at the top of the file and referenced in all locations

### Requirement: Control Flow Simplification
Code SHALL NOT use `else` or `elif` immediately after a `return` statement, as the branch is logically unreachable.

#### Scenario: Early Return Pattern
- **GIVEN** a function with pattern `if condition: return value; else: other_logic`
- **WHEN** refactored for clarity
- **THEN** the `else:` is removed and `other_logic` is dedented

### Requirement: No Empty Code Blocks
Code SHALL NOT contain empty blocks (e.g., empty `except:`, `if:`, or method bodies) unless they contain a comment explaining why the block is intentionally empty.

#### Scenario: Empty Block in impl.py
- **GIVEN** an empty block at line 110 in `impl.py`
- **WHEN** the code is reviewed
- **THEN** the block is either removed or filled with implementation/explanation

### Requirement: SQL String Formatting
SQL strings in Jinja macros SHALL NOT contain literal newline characters (character code 10) that trigger SonarQube warnings. Multi-line SQL should use concatenation or single-line formatting.

#### Scenario: Adapters Macro SQL
- **GIVEN** a SQL string literal with embedded newlines at line 212 in `adapters.sql`
- **WHEN** the macro is refactored
- **THEN** the newlines are replaced with space separators or explicit concatenation

#### Scenario: Apply Grants Macro SQL
- **GIVEN** a SQL string literal with embedded newlines at line 11 in `apply_grants.sql`
- **WHEN** the macro is refactored
- **THEN** the newlines are replaced with space separators or explicit concatenation

### Requirement: Line Length Limits
Python source lines SHALL NOT exceed 120 characters unless necessary for readability (e.g., long URLs or imports).

#### Scenario: Relation Module Line Length
- **GIVEN** a line in `relation.py` that is 138 characters long
- **WHEN** the line is refactored
- **THEN** it is split across multiple lines while preserving readability

### Requirement: Abstract Method Implementation
Adapter classes SHALL implement all abstract methods required by their base classes, or explicitly raise `NotImplementedError` with clear messaging when features are not supported.

#### Scenario: Python Submission Methods
- **GIVEN** `ExasolAdapter` inheriting from `SQLAdapter`
- **WHEN** the class is instantiated
- **THEN** the following methods are implemented:
  - `default_python_submission_method` (raises `NotImplementedError` with message explaining Exasol does not support Python models)
  - `generate_python_submission_response` (raises `NotImplementedError`)
  - `get_catalog_for_single_relation` (implements or delegates to base)
  - `python_submission_helpers` (returns empty dict or raises `NotImplementedError`)

### Requirement: Security Warning Documentation
Security scanner warnings (Bandit) for false positives SHALL be suppressed with inline comments explaining why the warning does not apply.

#### Scenario: Password Field Name
- **GIVEN** a `password` field in the `Credentials` dataclass
- **WHEN** Bandit scans the code
- **THEN** the field has a `# nosec B105` comment with explanation: "Field name for user-provided credential, not a hardcoded password"

## MODIFIED Requirements

### Requirement: Unused Imports
The codebase SHALL NOT contain unused imports in source files or tests, unless explicitly required for side-effects or re-exports (which should be documented or included in `__all__`).

#### Scenario: Clean Module Imports
- **GIVEN** the `dbt.adapters.exasol` package
- **WHEN** inspected by a linter
- **THEN** no unused imports are reported in `__init__.py` or other modules

#### Scenario: Column Module Import Order
- **GIVEN** the `column.py` module
- **WHEN** imports are organized
- **THEN** all imports are in correct order groups (stdlib, third-party, local)
- **AND** no imports are unused
