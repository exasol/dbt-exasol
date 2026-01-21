# Change: Add unit tests for ExasolRelation methods

## Why
The `dbt/adapters/exasol/relation.py` module has 52% unit test coverage. Four methods lack any test coverage: `add_ephemeral_prefix`, `_render_limited_alias`, `_render_event_time_filtered`, and `_render_subquery_alias`. Adding tests ensures these Exasol-specific behaviors are verified and protected against regressions.

## What Changes
- Add unit tests for `add_ephemeral_prefix` static method
- Add unit tests for `_render_limited_alias` method (both branches)
- Add unit tests for `_render_event_time_filtered` method (all four conditional branches)
- Add unit tests for `_render_subquery_alias` method (both branches)

## Impact
- Affected specs: None (testing only)
- Affected code: `tests/unit/test_relation_quoting.py` (extend existing test file)
- Coverage target: Increase `relation.py` coverage from 52% to 100%
