# Change: Acquire a pooled connection on demand for thread-unbound adapter calls

## Why

dbt-exasol's pooled `ExasolConnectionManager` returns a connection handle to the pool and clears the per-thread binding as soon as a unit of work finishes. When dbt-core (or a test) later calls an adapter metadata method such as `adapter.list_relations(...)` on a thread that has no bound connection — without an enclosing `with adapter.connection_named(...)` block — the inherited `get_thread_connection()` raises `InvalidConnectionError: connection never acquired for thread (...), have []`.

Non-pooled adapters (e.g. dbt-postgres) leave a connection bound to the thread between operations, so the same call path succeeds. This divergence surfaces concretely in the upstream `dbt.tests.adapter.dbt_clone.BaseCloneNotPossible` test: the `dbt clone --target otherschema` command itself succeeds, but the test's subsequent direct `project.adapter.list_relations(database=..., schema=other_schema)` call fails with `InvalidConnectionError`. That test is currently skipped in the `add-dbt-111-parity` change with this exact reason; this change unblocks it.

## What Changes

- Make Exasol adapter metadata calls robust when invoked on a thread that has no currently bound connection: instead of raising `InvalidConnectionError`, the connection manager SHALL lazily acquire (open) a pooled connection for the active thread, mirroring the behaviour callers get inside a `connection_named` block.
- Preserve the existing pool lifecycle guarantees: connections are still returned to the pool promptly, sessions are not leaked, and concurrency/LIFO reuse behaviour is unchanged.
- Unskip `tests/functional/adapter/dbt_clone/test_clone.py::TestExasolCloneNotPossible` and verify it passes against a live Exasol instance.
- Update the `add-dbt-111-parity` README parity matrix footnote for `dbt clone` (drop the "cross-target clones not yet supported" caveat once the test passes) — or, if the fix lands after that change archives, note it in this change's matrix update.

### Out of scope
- `BaseCloneSameSourceAndTarget` remains skipped: it asserts the zero-copy "skipping clone for relation" log line that dbt-core only emits when `can_clone_table == True`. Exasol clones as views (`can_clone_table == False`), so that branch is structurally never taken — independent of connection handling.
- No change to clone macros, materializations, or `can_clone_table`.
- No change to the pool key, pool sizing, or credential handling.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `connection-pooling`: Add a requirement that adapter operations performed on a thread without a bound connection acquire one from the pool on demand (rather than raising `InvalidConnectionError`), while keeping prompt return-to-pool and session-leak prevention intact.

## Impact

- **Code**: `dbt/adapters/exasol/connections.py` — connection acquisition / thread-binding lifecycle (e.g. an override of `get_thread_connection` or `list_relations_without_caching` that opens a pooled connection when the thread is unbound).
- **Tests**: unskip `tests/functional/adapter/dbt_clone/test_clone.py::TestExasolCloneNotPossible`; add a focused unit/functional test asserting a thread-unbound metadata call (e.g. `list_relations`) succeeds and does not leak a session.
- **Docs**: `README.md` dbt-core parity matrix footnote for `dbt clone`.
- **Risk**: the thread-binding/pool-return logic is shared by every query path, so the full functional suite (connection-pool tests, concurrency, incremental) must be re-run to confirm no session leaks or double-binding regressions.
- **No breaking changes** for end users; this only makes a previously-erroring call path succeed.
