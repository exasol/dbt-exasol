## 1. Reproduce and confirm root cause

- [x] 1.1 Temporarily unskip `tests/functional/adapter/dbt_clone/test_clone.py::TestExasolCloneNotPossible` (or add a probe test) and capture the traceback, confirming the failure is `InvalidConnectionError: connection never acquired for thread` raised from a thread-unbound `adapter.list_relations(...)` call after `dbt clone --target otherschema` succeeds
- [x] 1.2 Confirm via a minimal repro (a bare `project.adapter.list_relations(...)` outside `connection_named`) that the error is independent of clone

## 2. Implement on-demand thread connection acquisition

- [x] 2.1 In `dbt/adapters/exasol/connections.py`, override `get_thread_connection()` so that when the current thread has no entry in `thread_connections`, it calls `self.set_connection_name()` to bind a `Connection` (with a `LazyHandle`) and returns it; otherwise defer to the inherited behaviour
- [x] 2.2 Add an inline comment documenting why the override exists (restores the implicit "a thread can always reach a connection" contract that non-pooled adapters provide; required by upstream test classes and any caller outside `connection_named`)
- [x] 2.3 Verify the lazily acquired connection opens via the existing pool path (`open()` → `_try_get_pooled_connection`) and is bound in `thread_connections` so `release`/`cleanup_pool` reclaim it

## 3. Tests

- [x] 3.1 Add a focused functional test asserting a thread-unbound metadata call (e.g. `list_relations` outside `connection_named`) succeeds without `InvalidConnectionError`
- [x] 3.2 Add an assertion (in the same or a sibling test) that repeated thread-unbound metadata calls do not grow the number of open Exasol sessions (no session leak), e.g. by checking pool size / session count stays bounded
- [x] 3.3 Unskip `TestExasolCloneNotPossible` and run it against a live Exasol instance until green
- [x] 3.4 Keep `TestExasolCloneSameSourceAndTarget` skipped (document that it is structurally N/A for clone-as-view, unchanged by this fix)

## 4. Regression and validation

- [x] 4.1 Run the connection-pool integration tests (`tests/functional/adapter/test_connection_pool_integration.py`) and the concurrency tests to confirm no session leaks or double-binding regressions
- [x] 4.2 Run `mise run check` (format, lint, typing, deprecations) — all green
- [x] 4.3 Run `mise run test` (unit + integration) — all green
- [x] 4.4 Run `openspec validate fix-pooled-connection-thread-binding --strict`

## 5. Documentation

- [x] 5.1 Update the `dbt clone` entry/footnote in the `README.md` dbt-core parity matrix to drop the "cross-target clones not yet supported" caveat (clone-as-view across targets now works); keep the note that same-source-and-target zero-copy semantics are N/A
- [x] 5.2 Add a CHANGELOG entry noting the pooled-connection thread-binding fix and the now-passing upstream clone test
