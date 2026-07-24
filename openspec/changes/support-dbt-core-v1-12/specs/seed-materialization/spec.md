## ADDED Requirements

### Requirement: Empty seeds create zero-row tables
When `dbt seed --empty` is run, the adapter SHALL create the seed table with the inferred schema and zero rows. The Exasol CSV `IMPORT` path SHALL NOT be invoked when the seed has no rows.

#### Scenario: Seed with --empty creates an empty table
- **WHEN** `dbt seed --empty` is run for a seed CSV
- **THEN** the target table SHALL be created
- **AND** the table SHALL contain zero rows.

#### Scenario: Seed without --empty loads all rows
- **WHEN** `dbt seed` is run for the same seed CSV without `--empty`
- **THEN** the target table SHALL contain all rows from the CSV.

#### Scenario: build --empty materializes seed and downstream model
- **WHEN** `dbt build --empty` is run for a project with one seed and one model referencing it
- **THEN** both nodes SHALL materialize successfully
- **AND** the seed table SHALL contain zero rows.

### Requirement: Numeric column types are preserved for empty seeds
When a seed is materialized from a zero-row agate table (as produced by `--empty`, where dbt-core loads the CSV and then truncates it to zero rows), the adapter's numeric type conversion SHALL NOT degrade a numeric column to `integer`. The populated-seed type-inference path SHALL remain unchanged.

#### Scenario: Decimal column is not degraded to integer under --empty
- **WHEN** `convert_number_type` is called for a numeric column of an agate table with zero rows
- **THEN** the resolved Exasol type SHALL NOT be `integer`
- **AND** it SHALL be `float` (or the type given by an explicit `column_types` override).

#### Scenario: Populated seed type inference is unchanged
- **WHEN** `convert_number_type` is called for a numeric column of an agate table containing rows
- **THEN** the resolved type SHALL be `integer` for whole-number columns and `float` for columns with decimal precision, exactly as before this change.

#### Scenario: Empty seed then full-refresh seed loads data
- **WHEN** `dbt seed --empty` is run, followed by `dbt seed --full-refresh` for a CSV containing a decimal column
- **THEN** the full-refresh run SHALL recreate the table and load all rows
- **AND** the decimal values SHALL be loaded without type error.
