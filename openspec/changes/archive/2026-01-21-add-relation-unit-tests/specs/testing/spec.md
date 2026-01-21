## ADDED Requirements

### Requirement: ExasolRelation Unit Test Coverage
The test suite SHALL provide unit test coverage for all methods in `ExasolRelation` class.

#### Scenario: add_ephemeral_prefix returns correct CTE prefix
- **WHEN** `add_ephemeral_prefix` is called with a name
- **THEN** the result SHALL be prefixed with `dbt__CTE__`

#### Scenario: _render_limited_alias returns alias when required
- **WHEN** `_render_limited_alias` is called on a relation with `require_alias=True`
- **THEN** the result SHALL include ` dbt_limit_subq_` followed by the table name

#### Scenario: _render_limited_alias returns empty when not required
- **WHEN** `_render_limited_alias` is called on a relation with `require_alias=False`
- **THEN** the result SHALL be an empty string

#### Scenario: _render_event_time_filtered handles start and end timestamps
- **WHEN** `_render_event_time_filtered` is called with both start and end datetimes
- **THEN** the result SHALL contain a range filter with Exasol-compatible TIMESTAMP literals (no timezone)

#### Scenario: _render_event_time_filtered handles start-only timestamp
- **WHEN** `_render_event_time_filtered` is called with only a start datetime
- **THEN** the result SHALL contain a >= comparison with Exasol-compatible TIMESTAMP literal

#### Scenario: _render_event_time_filtered handles end-only timestamp
- **WHEN** `_render_event_time_filtered` is called with only an end datetime
- **THEN** the result SHALL contain a < comparison with Exasol-compatible TIMESTAMP literal

#### Scenario: _render_event_time_filtered handles no timestamps
- **WHEN** `_render_event_time_filtered` is called with neither start nor end datetime
- **THEN** the result SHALL be an empty string

#### Scenario: _render_subquery_alias returns alias when required
- **WHEN** `_render_subquery_alias` is called on a relation with `require_alias=True`
- **THEN** the result SHALL include ` AS dbt_` followed by namespace and table name

#### Scenario: _render_subquery_alias returns empty when not required
- **WHEN** `_render_subquery_alias` is called on a relation with `require_alias=False`
- **THEN** the result SHALL be an empty string
