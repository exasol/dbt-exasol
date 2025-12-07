# dbt-exasol 1.10 Compatibility Plan

## Overview

This document outlines the steps required to upgrade dbt-exasol to support dbt-core 1.10.0, based on the [Adapter Maintainers Upgrade Guide](https://github.com/dbt-labs/dbt-core/discussions/11864).

**Current version**: 1.8.2  
**Target version**: 1.10.0  
**dbt-core 1.10 release date**: June 16, 2025

---

## Feature Assessment

| Feature | Required for Exasol | Current Status | Effort |
|---------|---------------------|----------------|--------|
| Version bump to 1.10 | ✅ Yes | ✅ Done (pyproject.toml) | None |
| Deprecation fixes | ✅ Yes | 🟡 Needs testing | Low |
| Iceberg Catalogs | ❌ No (N/A) | N/A | None |
| Sample Mode | 🟡 Recommended | 🔴 Not implemented | Medium |
| Microbatch Strategy | 🟡 Recommended | 🔴 Not implemented | Medium |

---

## Phase 1: Version Bump & Deprecation Fixes

**Estimated effort**: 1-2 days  
**Priority**: High (blocking)

### Tasks

- [ ] Update `dbt/adapters/exasol/__version__.py` to `1.10.0`
- [ ] Run full test suite against dbt-core 1.10
- [ ] Review and fix any deprecation warnings in:
  - [ ] Python adapter code (`impl.py`, `connections.py`, `relation.py`, `column.py`)
  - [ ] Jinja macros (all `.sql` files in `dbt/include/exasol/macros/`)
- [ ] Verify all existing functional tests pass
- [ ] Update `pyproject.toml` version to `1.10.0`

### Deprecations to Check

From dbt 1.10 deprecation warnings:
- `GenericJSONSchemaValidationDeprecation`
- `UnexpectedJinjaBlockDeprecation`
- `DuplicateYAMLKeysDeprecation`
- `CustomTopLevelKeyDeprecation`
- `CustomKeyInConfigDeprecation`
- `CustomKeyInObjectDeprecation`
- `MissingPlusPrefixDeprecation`

---

## Phase 2: Sample Mode / Microbatch Support

**Estimated effort**: 3-5 days  
**Priority**: Medium-High (feature enhancement)

### Background

Sample mode (`--sample` flag) runs dbt in "small-data" mode by building time-based slices of models. Per the upgrade guide:

> If an adapter supports microbatch incremental models, then it already has all the technical implementation needed to support sample mode.

### Tasks

- [ ] Research microbatch implementation in reference adapters:
  - dbt-postgres
  - dbt-bigquery  
  - dbt-spark (see `dbt-adapters#897`)
- [ ] Implement microbatch incremental strategy:
  - [ ] Add `"microbatch"` to `valid_incremental_strategies()` in `impl.py`
  - [ ] Create `exasol__get_incremental_microbatch_sql()` macro
  - [ ] Implement batch iteration logic with `event_time` filtering
  - [ ] Support `batch_id` and `lookback` configuration
- [ ] Add sample mode test from dbt-adapters:
  - Reference: `dbt-adapters#878` (base test case)
  - Reference: `dbt-adapters#886` (cross-adapter testing)
- [ ] Verify `--sample` flag works correctly with Exasol

### Implementation Notes

Exasol already has the prerequisite SQL functions:
- `timestamp_add_sql()` method in `impl.py:89-96`
- `dateadd` macro (`add_days()`, `add_hours()`, etc.)
- `datediff` macro (`days_between()`, `hours_between()`, etc.)
- `current_timestamp()` macro

---

## Phase 3: Testing & Documentation

**Estimated effort**: 1-2 days  
**Priority**: Medium

### Tasks

- [ ] Add functional tests for microbatch/sample mode
- [ ] Test against Exasol 7.x and 8.x
- [ ] Update `README.md` with:
  - [ ] New version compatibility matrix
  - [ ] Sample mode usage (if implemented)
  - [ ] Microbatch incremental strategy (if implemented)
- [ ] Document Exasol-specific limitations

---

## Phase 4: Release

**Estimated effort**: 1 day  
**Priority**: High

### Tasks

- [ ] Create release notes / CHANGELOG entry
- [ ] Tag release `v1.10.0`
- [ ] Publish to PyPI
- [ ] Close GitHub issue [exasol/dbt-exasol#137](https://github.com/exasol/dbt-exasol/issues/137)

---

## Not Applicable for Exasol

### Iceberg Data Catalogs

Iceberg catalog integration is designed for warehouse-agnostic interfaces to manage datasets in object storage (Snowflake, BigQuery, Spark). Exasol does not natively support Iceberg table format.

**Action**: None required unless Exasol adds Iceberg support in future versions.

---

## References

- [dbt-core 1.10 Adapter Upgrade Discussion](https://github.com/dbt-labs/dbt-core/discussions/11864)
- [dbt 1.10 Deprecation Warnings](https://docs.getdbt.com/reference/deprecations)
- [Sample Mode Documentation](https://docs.getdbt.com/docs/build/sample-flag)
- [Microbatch Documentation](https://docs.getdbt.com/docs/build/incremental-microbatch)
- [dbt-adapters Sample Mode Tests](https://github.com/dbt-labs/dbt-adapters/issues/878)
