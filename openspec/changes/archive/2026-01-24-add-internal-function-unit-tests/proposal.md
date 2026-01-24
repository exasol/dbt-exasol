# Change: Add Unit Tests for Internal Functions

## Why
The code review (review_glm.md) identified several internal functions with 0% unit test coverage. While functional tests exercise these paths indirectly, direct unit tests would catch edge cases, improve maintainability, and provide faster feedback during development.

## What Changes
- Add unit tests for `ExasolColumn.from_description()` (column.py:66-104)
- Add unit tests for `ExasolAdapter.is_valid_identifier()` (impl.py:129-144)
- Add unit tests for `ExasolConnectionManager.data_type_code_to_name()` (connections.py:284-285)
- Add unit tests for `ExasolColumn` type detection methods (column.py:27-51)
- Add unit tests for `ExasolRelation` rendering logic (relation.py)
- Add unit tests for `ExasolConnectionManager` result parsing and `ExasolCursor` logic (connections.py)
- Add unit tests for `ExasolConnectionManager.open` logic (SSL, protocols) (connections.py)
- Add unit tests for `ExasolAdapter` helper methods (`_make_match_kwargs`, `quote_seed_column`, `timestamp_add_sql`) (impl.py)
- Add unit tests for `ExasolAdapter.list_relations_without_caching` (impl.py)

## Impact
- Affected specs: `quality` (extends test coverage requirements)
- Affected code: `tests/unit/` (new test files)
- No changes to production code
