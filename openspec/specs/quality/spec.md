# quality Specification

## Purpose
TBD - created by archiving change fix-code-quality-issues. Update Purpose after archive.
## Requirements
### Requirement: Specific Exception Catching
The adapter SHALL NOT use bare `except:` clauses which catch `SystemExit` and `KeyboardInterrupt`. It SHALL catch specific exceptions when validating configuration or connection parameters.

#### Scenario: Invalid Protocol Version
- **GIVEN** a `credentials` object with an invalid `protocol_version`
- **WHEN** `ExasolConnectionManager.open()` is called
- **THEN** a `DbtRuntimeError` is raised wrapping the specific underlying error (e.g., `ValueError` or `KeyError`)
- **AND** the application remains responsive to interrupts

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

### Requirement: Consistent Formatting
SQL and Jinja macros SHALL follow standard formatting rules defined by the project's `sqlfluff` configuration, including indentation and spacing.

#### Scenario: Formatted Macros
- **GIVEN** a macro file in `dbt/include/exasol/macros/`
- **WHEN** `sqlfluff lint` is run on the file
- **THEN** no formatting violations are reported

### Requirement: Empty Identifier Guard
The `is_valid_identifier()` method SHALL handle empty strings gracefully without raising an exception.

#### Scenario: Empty String Input
- **GIVEN** an empty string `""`
- **WHEN** `ExasolAdapter.is_valid_identifier("")` is called
- **THEN** the method returns `False`
- **AND** no `IndexError` is raised

### Requirement: Column Type Detection Unit Tests
The adapter SHALL have unit tests for all `ExasolColumn` type detection methods (`is_numeric`, `is_integer`, `is_float`, `is_string`, `is_hashtype`, `is_boolean`, `is_timestamp`, `is_date`, `string_size`).

#### Scenario: Numeric Type Detection
- **GIVEN** an `ExasolColumn` with dtype "DECIMAL"
- **WHEN** `is_numeric()` is called
- **THEN** it returns `True`

#### Scenario: Integer Detection with Scale
- **GIVEN** an `ExasolColumn` with dtype "DECIMAL" and numeric_scale=0
- **WHEN** `is_integer()` is called
- **THEN** it returns `True`

#### Scenario: String Size Error
- **GIVEN** an `ExasolColumn` with dtype "DECIMAL" (non-string)
- **WHEN** `string_size()` is called
- **THEN** a `DbtRuntimeError` is raised

### Requirement: Column Parsing Unit Tests
The adapter SHALL have unit tests for `ExasolColumn.from_description()` covering simple types, sized types, and error cases.

#### Scenario: Parse Simple Type
- **GIVEN** raw_data_type "TIMESTAMP"
- **WHEN** `from_description("col", "TIMESTAMP")` is called
- **THEN** a Column with dtype="TIMESTAMP" and no size info is returned

#### Scenario: Parse Sized Type
- **GIVEN** raw_data_type "VARCHAR(100)"
- **WHEN** `from_description("col", "VARCHAR(100)")` is called
- **THEN** a Column with dtype="VARCHAR" and char_size=100 is returned

#### Scenario: Parse Precision and Scale
- **GIVEN** raw_data_type "DECIMAL(18,9)"
- **WHEN** `from_description("col", "DECIMAL(18,9)")` is called
- **THEN** a Column with dtype="DECIMAL", numeric_precision=18, numeric_scale=9 is returned

#### Scenario: Parse HASHTYPE Format
- **GIVEN** raw_data_type "HASHTYPE(16 BYTE)"
- **WHEN** `from_description("col", "HASHTYPE(16 BYTE)")` is called
- **THEN** a Column with dtype="HASHTYPE" and char_size=16 is returned

#### Scenario: Invalid Data Type Format
- **GIVEN** raw_data_type with unparseable format
- **WHEN** `from_description()` is called
- **THEN** a `DbtRuntimeError` is raised

### Requirement: Identifier Validation Unit Tests
The adapter SHALL have unit tests for `ExasolAdapter.is_valid_identifier()` covering valid identifiers, invalid identifiers, and edge cases.

#### Scenario: Valid Alphanumeric Identifier
- **GIVEN** identifier "MY_TABLE123"
- **WHEN** `is_valid_identifier("MY_TABLE123")` is called
- **THEN** it returns `True`

#### Scenario: Valid Special Characters
- **GIVEN** identifier "TABLE$NAME#1_"
- **WHEN** `is_valid_identifier("TABLE$NAME#1_")` is called
- **THEN** it returns `True`

#### Scenario: Invalid Numeric Start
- **GIVEN** identifier "123TABLE"
- **WHEN** `is_valid_identifier("123TABLE")` is called
- **THEN** it returns `False`

#### Scenario: Invalid Special Character
- **GIVEN** identifier "TABLE-NAME"
- **WHEN** `is_valid_identifier("TABLE-NAME")` is called
- **THEN** it returns `False`

#### Scenario: Empty String
- **GIVEN** identifier ""
- **WHEN** `is_valid_identifier("")` is called
- **THEN** it returns `False`

### Requirement: Data Type Code Conversion Unit Tests
The adapter SHALL have unit tests for `ExasolConnectionManager.data_type_code_to_name()`.

#### Scenario: Simple Type Code
- **GIVEN** type_code "varchar"
- **WHEN** `data_type_code_to_name("varchar")` is called
- **THEN** it returns "VARCHAR"

#### Scenario: Parameterized Type Code
- **GIVEN** type_code "varchar(100)"
- **WHEN** `data_type_code_to_name("varchar(100)")` is called
- **THEN** it returns "VARCHAR"

### Requirement: Exasol Relation Unit Tests
The adapter SHALL have unit tests for `ExasolRelation` custom rendering methods.

#### Scenario: Render Event Time Filter
- **GIVEN** an `EventTimeFilter` with start and end times
- **WHEN** `_render_event_time_filtered()` is called
- **THEN** it returns SQL with `TIMESTAMP` literals and NO timezone information (e.g. `2023-01-01 12:00:00`)

#### Scenario: Relation Creation
- **GIVEN** a dictionary with "database", "schema", "identifier"
- **WHEN** `ExasolRelation.create()` is called
- **THEN** the returned relation has `database=None` (compatibility override)

### Requirement: Connection Result Parsing Unit Tests
The adapter SHALL have unit tests for `ExasolConnectionManager.get_result_from_cursor()` handling Exasol-specific type conversions.

#### Scenario: Convert DECIMAL types
- **GIVEN** a mock cursor returning strings for DECIMAL columns
- **WHEN** `get_result_from_cursor()` is called
- **THEN** the resulting Agate table contains `decimal.Decimal` objects

#### Scenario: Convert TIMESTAMP types
- **GIVEN** a mock cursor returning strings for TIMESTAMP columns
- **WHEN** `get_result_from_cursor()` is called
- **THEN** the resulting Agate table contains `datetime.datetime` objects

### Requirement: Exasol Cursor Unit Tests
The adapter SHALL have unit tests for `ExasolCursor` special command handling.

#### Scenario: CSV Import Command
- **GIVEN** a query string starting with "0CSV|"
- **WHEN** `execute()` is called
- **THEN** it calls `import_from_file` on the connection instead of `execute`

### Requirement: Adapter Helper Unit Tests
The adapter SHALL have unit tests for `ExasolAdapter` helper methods.

#### Scenario: Make Match Kwargs Case Sensitivity
- **GIVEN** quoting config set to False for all
- **WHEN** `_make_match_kwargs` is called with mixed-case identifier/schema
- **THEN** it returns lower-cased strings

#### Scenario: Timestamp Add SQL
- **GIVEN** add_to="col", number=1, interval="hour"
- **WHEN** `timestamp_add_sql` is called
- **THEN** it returns "col + interval '1' hour" (Exasol specific syntax)

#### Scenario: Quote Seed Column
- **GIVEN** quote_config=True
- **WHEN** `quote_seed_column` is called
- **THEN** it returns quoted column
- **GIVEN** quote_config=None
- **WHEN** `quote_seed_column` is called
- **THEN** it returns unquoted column
- **GIVEN** invalid quote_config type
- **WHEN** `quote_seed_column` is called
- **THEN** it raises CompilationError

#### Scenario: List Relations Parsing
- **GIVEN** mock execution result of [('DB', 'tbl', 'schema', 'table')]
- **WHEN** `list_relations_without_caching` is called
- **THEN** it returns a list of ExasolRelation objects with correct attributes

### Requirement: Connection Open Unit Tests
The adapter SHALL have unit tests for `ExasolConnectionManager.open` configuration logic.

#### Scenario: Connection Protocol Version
- **GIVEN** credentials with protocol_version="v1"
- **WHEN** `open()` is called
- **THEN** pyexasol is called with protocol_v1 constant

#### Scenario: SSL Configuration
- **GIVEN** credentials with encryption=True, validate_server_certificate=False
- **WHEN** `open()` is called
- **THEN** pyexasol is called with `websocket_sslopt={"cert_reqs": ssl.CERT_NONE}`

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

