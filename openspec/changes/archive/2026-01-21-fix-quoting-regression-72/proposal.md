# Change: Fix Quoting Regression (Issue #72)

## Why
Users report that quoting options in source configurations and table configurations are being ignored.
Specifically, setting `quoting: {database: true, schema: true, identifier: true}` still results in unquoted identifiers in the generated SQL.
This regression prevents users from correctly querying case-sensitive or reserved-keyword tables/schemas in Exasol.

## What Changes
- Implement a regression test case reproducing the reported issue (Issue #72).
- Fix the `dbt-exasol` adapter to correctly respect `quoting` configurations from sources and models.
- Ensure `ExasolQuotePolicy` or the relation rendering logic correctly applies quotes when requested.

## Impact
- **Affected specs:** `quoting`
- **Affected code:** `dbt/adapters/exasol/relation.py`, `dbt/adapters/exasol/impl.py` (potentially)
