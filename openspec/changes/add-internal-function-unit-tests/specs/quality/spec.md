## ADDED Requirements

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
