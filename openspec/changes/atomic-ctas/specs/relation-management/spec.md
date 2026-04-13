## MODIFIED Requirements

### Requirement: Per-Type Replace Macros
The adapter SHALL implement `exasol__get_replace_table_sql` and `exasol__get_replace_view_sql` macros that generate Exasol-compatible `CREATE OR REPLACE` SQL. These macros are dispatched by the `get_replace_sql` framework macro when atomically replacing relations.

#### Scenario: Replace a table
- **WHEN** `get_replace_table_sql` is called with a table relation and SQL
- **THEN** the adapter SHALL generate SQL using a single atomic `CREATE OR REPLACE TABLE ... AS <sql>` statement via the `exasol__create_table_as` macro, followed by `ALTER TABLE` statements for DISTRIBUTE BY, PARTITION BY, and PRIMARY KEY if configured (connected via `|SEPARATEMEPLEASE|`)
- **AND** the generated SQL SHALL NOT use the `WITH NO DATA` + `INSERT INTO` pattern

#### Scenario: Replace a view
- **WHEN** `get_replace_view_sql` is called with a view relation and SQL
- **THEN** the adapter SHALL generate SQL using `CREATE OR REPLACE VIEW` with the provided query, consistent with the existing `exasol__create_view_as` pattern
