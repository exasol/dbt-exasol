# Phase 1: Version Bump & Deprecation Fixes - TDD Implementation Plan

**Estimated effort**: 1-2 days  
**Priority**: High (blocking)

---

## Overview

This document details the TDD-based implementation steps for Phase 1 of the dbt-exasol 1.10 upgrade.

---

## TDD Workflow

### Cycle 1: Baseline

| Step | Type | Action | Command |
|------|------|--------|---------|
| 1 | **TEST** | Run baseline tests (expect PASS) | `uv run pytest tests/ -n48` |

**Purpose**: Establish a green baseline before making any changes.

---

### Cycle 2: Version Bump

| Step | Type | Action | Details |
|------|------|--------|---------|
| 2 | **GREEN** | Update `__version__.py` | `"1.8.2"` → `"1.10.0"` |
| 3 | **GREEN** | Update `pyproject.toml` | `"1.8.2"` → `"1.10.0"` |
| 4 | **TEST** | Run tests | `uv run pytest tests/ -n48` |

**Files**:
- `dbt/adapters/exasol/__version__.py`
- `pyproject.toml` (line 3)

---

### Cycle 3: Remove hologram Dependency

| Step | Type | Action | Details |
|------|------|--------|---------|
| 5 | **GREEN** | Replace import in `connections.py:21` | See shim code below |
| 6 | **GREEN** | Remove from `pyproject.toml:16` | Delete `"hologram>=0.0.16",` |
| 7 | **SYNC** | Update environment | `uv sync` |
| 8 | **TEST** | Run tests | `uv run pytest tests/ -n48` |

**StrEnum Shim Code** (for `connections.py`):

Replace:
```python
from hologram.helpers import StrEnum
```

With:
```python
# Python 3.11+ has StrEnum built-in, use shim for 3.9/3.10
try:
    from enum import StrEnum
except ImportError:
    from enum import Enum
    class StrEnum(str, Enum):
        pass
```

**Files**:
- `dbt/adapters/exasol/connections.py` (line 21)
- `pyproject.toml` (line 16)

---

### Cycle 4: Import Cleanup (Refactor)

| Step | Type | Action | Details |
|------|------|--------|---------|
| 9 | **REFACTOR** | Clean `impl.py` imports | Remove unused, deduplicate |
| 10 | **TEST** | Run tests | `uv run pytest tests/ -n48` |

**impl.py Changes**:

Current imports (lines 8-17):
```python
from dbt.adapters.base.relation import BaseRelation, InformationSchema
from dbt.adapters.contracts.relation import RelationConfig
from dbt.adapters.base.impl import GET_CATALOG_MACRO_NAME, ConstraintSupport, GET_CATALOG_RELATIONS_MACRO_NAME, _expect_row_value
from dbt.adapters.capability import CapabilityDict, CapabilitySupport, Support, Capability
from dbt.adapters.sql import SQLAdapter
from dbt_common.exceptions import CompilationError
from dbt_common.utils import filter_null_values
from dbt.adapters.base.meta import available
from dbt.adapters.base.impl import ConstraintSupport, AdapterConfig
from dbt_common.contracts.constraints import ConstraintType
```

Cleaned imports:
```python
from dbt.adapters.base.relation import BaseRelation
from dbt.adapters.contracts.relation import RelationConfig
from dbt.adapters.base.impl import _expect_row_value, ConstraintSupport, AdapterConfig
from dbt.adapters.capability import CapabilityDict, CapabilitySupport, Support, Capability
from dbt.adapters.sql import SQLAdapter
from dbt_common.exceptions import CompilationError
from dbt_common.utils import filter_null_values
from dbt.adapters.base.meta import available
from dbt_common.contracts.constraints import ConstraintType
```

**Removed**:
- `InformationSchema` (unused)
- `GET_CATALOG_MACRO_NAME` (unused)
- `GET_CATALOG_RELATIONS_MACRO_NAME` (unused)
- Duplicate `ConstraintSupport` import (line 16)

**Files**:
- `dbt/adapters/exasol/impl.py` (lines 8-17)

---

### Cycle 5: Deprecation Check

| Step | Type | Action | Command |
|------|------|--------|---------|
| 11 | **TEST** | Run with deprecation warnings as errors | `uv run pytest tests/ -n48 -W error::DeprecationWarning` |
| 12 | **FIX** | Address any failures | TBD based on output |
| 13 | **REFACTOR** | Update `pytest.ini` if needed | TBD based on output |

**Potential Macro Issues to Watch**:

| File | Concern | Action |
|------|---------|--------|
| `snapshot.sql:278` | `model['compiled_sql']` may be deprecated | Verify during tests |
| `strategies.sql:8,16` | `node['injected_sql']` attribute | Verify during tests |
| `incremental.sql:48` | `predicates` vs `incremental_predicates` | Verify during tests |
| `timestamps.sql:14-20` | `*_backcompat` macros | May be obsolete |

---

### Cycle 6: Final Verification

| Step | Type | Action | Command |
|------|------|--------|---------|
| 14 | **TEST** | Final full test run | `uv run pytest tests/ -n48` |

---

## Summary

| Cycle | Focus | Files Modified | Test Checkpoint |
|-------|-------|----------------|-----------------|
| 1 | Baseline | None | Establish green state |
| 2 | Version bump | `__version__.py`, `pyproject.toml` | Verify no breakage |
| 3 | hologram removal | `connections.py`, `pyproject.toml` | Verify StrEnum works |
| 4 | Import cleanup | `impl.py` | Verify no breakage |
| 5 | Deprecations | TBD | Catch & fix warnings |
| 6 | Final | None | Confirm all green |

---

## Checklist

- [x] Cycle 1: Baseline tests pass
- [x] Cycle 2: Version updated, tests pass
- [ ] Cycle 3: hologram removed, StrEnum shim works, tests pass
- [ ] Cycle 4: impl.py imports cleaned, tests pass
- [ ] Cycle 5: No deprecation warnings (or documented/addressed)
- [ ] Cycle 6: Final verification complete

---

## References

- Parent plan: [phase-1.10.md](./phase-1.10.md)
- dbt-core 1.10 Adapter Upgrade: https://github.com/dbt-labs/dbt-core/discussions/11864
- dbt 1.10 Deprecation Warnings: https://docs.getdbt.com/reference/deprecations
