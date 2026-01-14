## ADDED Requirements

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
