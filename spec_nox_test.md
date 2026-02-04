# Spec: Override Nox Test Sessions for Custom Paths

## Problem

The exasol-toolbox hardcodes test paths in `exasol/toolbox/nox/_test.py`:
- Unit tests: `{root_path}/test/unit`
- Integration tests: `{root_path}/test/integration`

This project uses different paths:
- Unit tests: `tests/unit`
- Functional tests: `tests/functional`

There is no built-in configuration option in `BaseConfig` to change these paths.

## Solution

Override the three test-related nox sessions in `noxfile.py` to use project-specific paths while reusing the toolbox's helper functions (`_test_command`, `_context`) to avoid code duplication.

## Implementation

### Step 1: Add Imports

**File:** `noxfile.py` (after line 7)

```python
from exasol.toolbox.nox._shared import _context
from exasol.toolbox.nox._test import _test_command
from exasol.toolbox.nox.plugin import NoxTasks
```

### Step 2: Add Session Overrides

**File:** `noxfile.py` (append at end, after line 143)

```python
# Override test sessions to use project-specific test paths
# (tests/unit and tests/functional instead of test/unit and test/integration)


@nox.session(name="test:unit", python=False)
def unit_tests(session: Session) -> None:
    """Runs all unit tests"""
    context = _context(session)
    command = _test_command(
        PROJECT_CONFIG.root_path / "tests" / "unit", PROJECT_CONFIG, context
    )
    session.run(*command)


@nox.session(name="test:integration", python=False)
def integration_tests(session: Session) -> None:
    """Runs all integration/functional tests"""
    context = _context(session)
    pm = NoxTasks.plugin_manager(PROJECT_CONFIG)
    pm.hook.pre_integration_tests_hook(
        session=session, config=PROJECT_CONFIG, context=context
    )
    command = _test_command(
        PROJECT_CONFIG.root_path / "tests" / "functional", PROJECT_CONFIG, context
    )
    session.run(*command)
    pm.hook.post_integration_tests_hook(
        session=session, config=PROJECT_CONFIG, context=context
    )


@nox.session(name="test:coverage", python=False)
def coverage(session: Session) -> None:
    """Runs all tests (unit + integration) and reports the code coverage"""
    context = _context(session, coverage=True)
    coverage_file = PROJECT_CONFIG.root_path / ".coverage"
    coverage_file.unlink(missing_ok=True)
    unit_tests(session)
    integration_tests(session)
    session.run("coverage", "report", "-m")
```

### Step 3: Format Code

```bash
nox -s format:fix
```

## Verification

```bash
nox -l                                    # List sessions
nox -s test:unit -- --collect-only        # Verify unit test path
nox -s test:integration -- --collect-only # Verify integration test path
```

## Files Changed

| File | Change |
|------|--------|
| `noxfile.py` | +3 import lines, +~40 lines for session overrides |

## Notes

- Session names remain `test:unit`, `test:integration`, `test:coverage` for toolbox compatibility
- Plugin hooks (`StartDB`, `StopDB`) continue to work via `pre_integration_tests_hook` and `post_integration_tests_hook`
- The `_test_command` function handles both regular pytest and coverage-enabled runs
- Nox uses the last-defined session when names collide, so these overrides take precedence
