## 1. Dependency bump and pre-release policy

- [x] 1.1 In `pyproject.toml` `[project].dependencies`, change `dbt-core>=1.10.0` → `dbt-core>=1.12.0b1,<1.13` and `dbt-adapters>=1.10.0` → `dbt-adapters>=1.24.1`
- [x] 1.2 In `pyproject.toml` `[dependency-groups].dev`, change `dbt-tests-adapter>=1.10.0` → `dbt-tests-adapter>=1.20.0`
- [x] 1.3 Add a `[tool.uv]` table to `pyproject.toml` with `prerelease = "explicit"`
- [x] 1.4 Run `uv lock` and commit the refreshed `uv.lock`; confirm it resolves `dbt-core==1.12.0b2` (or newer 1.12.x), `dbt-adapters>=1.24.1`, `dbt-tests-adapter>=1.20.0`, and that no other dependency resolved to a pre-release
- [x] 1.5 Run `uv sync` and verify `uv run python -c "import dbt.version; print(dbt.version.__version__)"` reports a 1.12 version
- [x] 1.6 Verify the adapter imports cleanly: `uv run python -c "from dbt.adapters.exasol.impl import ExasolAdapter; assert not ExasolAdapter.__abstractmethods__"`

## 2. Harden `convert_number_type` for empty seeds

- [x] 2.1 In `dbt/adapters/exasol/impl.py`, update `convert_number_type` so that when `len(agate_table.rows) == 0` it returns `"float"` instead of running `agate.MaxPrecision` (which returns `0` on an empty column and degrades to `integer`). Preserve the existing populated-table logic byte-for-byte.
- [x] 2.2 Add a unit test (no DB) constructing a zero-row agate `Number` column and asserting `convert_number_type` returns `"float"`
- [x] 2.3 Add a unit test asserting the populated path is unchanged: a decimal-precision column returns `"float"` and a whole-number column returns `"integer"`

## 3. ExasolCursor exception hardening

- [x] 3.1 In `dbt/adapters/exasol/connections.py`, replace the three `raise RuntimeError(_UNSET_STATEMENT_ERROR)` statements in `fetchone`, `fetchmany`, and `fetchall` with `raise dbt_common.exceptions.DbtRuntimeError(_UNSET_STATEMENT_ERROR)`
- [x] 3.2 Update/extend the connections unit tests to assert `DbtRuntimeError` is raised on fetch against an unset statement

## 4. Empty-seed adapter test coverage

- [x] 4.1 Add `tests/functional/adapter/empty/test_empty.py` defining `class TestEmptySeedFlag(BaseTestEmptySeedFlag): pass` (import `BaseTestEmptySeedFlag` from `dbt.tests.adapter.empty.test_empty`)
- [ ] 4.2 Run the empty-seed suite against the Exasol docker DB (`nox -s start:db` then the integration session) and confirm all four cases pass: zero-row create, type preservation via full-refresh, full load without `--empty`, and `build --empty`
- [x] 4.3 (Optional, per design Open Question) Add a regression test for the `--empty` → plain (non-`--full-refresh`) `seed` sequence on a decimal column; if it cannot pass without deeper changes, mark it `xfail` and document the limitation

## 5. latest_version_pointer coverage

- [x] 5.1 Add a functional test that defines a versioned model with `latest_version_pointer.enabled: true`, runs it, and asserts the pointer view (named after the base model) exists and is selectable
- [x] 5.2 Confirm the pointer is created through Exasol's existing `view` materialization (no `ExasolRelation` change required)

## 6. Full validation

- [x] 6.1 Run `uv run nox -s test:unit`
- [ ] 6.2 Run `uv run nox -s test:integration` against the Exasol docker DB
- [x] 6.3 Run `uv run nox -s format:check lint:code lint:security lint:typing` and fix any findings
- [ ] 6.4 Confirm a CI run resolves and installs `dbt-core` 1.12 the same way as local (deterministic via committed `uv.lock`)
- [x] 6.5 Update README / supported-version docs to state dbt-core 1.12 support and note the `--empty` empty→plain-seed decimal edge as a known limitation
