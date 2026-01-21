# quoting Specification

## Purpose
TBD - created by archiving change fix-quoting-regression-72. Update Purpose after archive.
## Requirements
### Requirement: Respect Source and Model Quoting Configuration
The adapter MUST respect `quoting` configurations defined in sources and models.
If `quoting` is set to `true` for `database`, `schema`, or `identifier`, the generated SQL MUST use double quotes for those components.

#### Scenario: Source Quoting Enabled
- **WHEN** a source is defined with `quoting: {schema: true, identifier: true}`
- **AND** the source schema is `TEST` and table is `order`
- **THEN** the generated SQL selects from `"TEST"."order"` (quoted) instead of `TEST.order` (unquoted).

#### Scenario: Table Quoting Overwrite
- **WHEN** a table config overwrites quoting (e.g., `quoting: {identifier: true}`)
- **THEN** the identifier MUST be quoted in the generated SQL.

#### Scenario: Partial Quoting Override
- **WHEN** a source defines `quoting: {schema: true, identifier: true}`
- **AND** a table within that source overrides with `quoting: {identifier: false}`
- **THEN** the schema MUST remain quoted (inherited)
- **AND** the identifier MUST NOT be quoted (overridden).

#### Scenario: Quoting Disabled
- **WHEN** quoting is disabled or not configured for schema and identifier
- **THEN** the generated SQL MUST NOT contain quotes around schema and identifier.

### Requirement: Unit Test Coverage for Quoting Behavior
Unit tests MUST verify quoting behavior without requiring external database connections.

#### Scenario: Quote Policy as Dictionary
- **WHEN** `ExasolRelation.create()` is called with `quote_policy` as a dict
- **THEN** the relation MUST correctly apply the quoting configuration.

#### Scenario: Quote Policy as ExasolQuotePolicy Object
- **WHEN** `ExasolRelation.create()` is called with `quote_policy` as an `ExasolQuotePolicy` instance
- **THEN** the relation MUST correctly apply the quoting configuration.

#### Scenario: Render with All Components Quoted
- **WHEN** a relation is created with `quote_policy: {database: true, schema: true, identifier: true}`
- **THEN** `str(relation)` MUST include double quotes around schema and identifier.

#### Scenario: Render with Quoting Disabled
- **WHEN** a relation is created with `quote_policy: {schema: false, identifier: false}`
- **THEN** `str(relation)` MUST NOT include double quotes around schema and identifier.

#### Scenario: Reserved Keywords as Identifiers
- **WHEN** an identifier is a SQL reserved keyword (e.g., `order`, `select`, `from`)
- **AND** quoting is enabled for identifier
- **THEN** the identifier MUST be rendered with double quotes.

