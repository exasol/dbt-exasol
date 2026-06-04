## Context

`ExasolConnectionManager` subclasses `SQLConnectionManager`/`BaseConnectionManager` and adds a class-level connection pool keyed by `(dsn, user, database, schema)`. dbt-core's normal execution path wraps each node/operation in `connection_named(...)`, which calls `set_connection_name()` → binds a `Connection` (with a `LazyHandle`) into `self.thread_connections[thread_id]`. The first query opens the handle (`open()` pulls a connection from the pool or creates one); on release the handle is returned to the pool.

The failure mode: when an adapter metadata method (e.g. `adapter.list_relations(...)`) is called on a thread that is **not** inside a `connection_named` block, the inherited `get_thread_connection()` finds no entry in `thread_connections` and raises:

```
InvalidConnectionError: connection never acquired for thread (pid, tid), have []
```

This is reproducible via `dbt.tests.adapter.dbt_clone.BaseCloneNotPossible`: the `dbt clone --target otherschema` command succeeds (`PASS=4`), then the test body calls `project.adapter.list_relations(database=..., schema=other_schema)` directly (no `connection_named` wrapper) and that call raises. The clone-as-view semantics themselves are correct; only the thread-binding contract differs from non-pooled adapters that the upstream test assumes.

The fix is a small, localized change to how a thread acquires its connection. Everything else (pool key, sizing, LIFO reuse, return-to-pool, session-leak prevention) stays as-is.

## Goals / Non-Goals

**Goals:**
- An adapter operation issued on a thread with no bound connection acquires one from the pool on demand instead of raising `InvalidConnectionError`.
- Behaviour matches the implicit contract non-pooled adapters satisfy, so upstream `dbt-tests-adapter` classes that call adapter methods directly work unchanged.
- Unblock and pass `TestExasolCloneNotPossible` against a live Exasol instance.
- Keep prompt return-to-pool and zero session leaks.

**Non-Goals:**
- Changing clone macros, `can_clone_table`, or materializations.
- Making `BaseCloneSameSourceAndTarget` pass (it asserts zero-copy-only log output; structurally N/A for clone-as-view).
- Altering pool key, pool sizing, or credentials.
- Supporting concurrent multi-target writes or microbatch concurrency (separate concerns).

## Decisions

### D1. Lazily acquire a thread connection in `get_thread_connection`

**Decision:** Override `ExasolConnectionManager.get_thread_connection()` so that, when the current thread has no bound connection, it calls `self.set_connection_name()` (the same entry point `connection_named` uses) to create and bind a `Connection` with a `LazyHandle`, then returns it. The subsequent `add_query` opens that handle, which pulls from the pool exactly like any other query.

**Rationale:** This is the single, shared choke point every query path funnels through (`add_query` → `get_thread_connection`). Fixing it once covers `list_relations`, `get_columns_in_relation`, catalog calls, and any other metadata method, and mirrors the behaviour other adapters get implicitly. The lazily-bound connection lives in `thread_connections`, so the existing `release()` / `cleanup` / `cleanup_pool` paths return it to the pool normally — no new leak surface.

**Alternatives considered:**
- *Override each metadata method (`list_relations_without_caching`, etc.) to wrap in `connection_named`.* Rejected — many methods, easy to miss one, more code than the choke-point fix.
- *Modify the upstream test to add a `connection_named` wrapper.* Rejected — the upstream test is the parity contract; we cannot edit vendored test classes, and a local copy would drift.
- *Eagerly keep a connection bound after each operation (postgres-style).* Rejected — fights the pool's prompt return-to-pool design and risks holding pool slots.

### D2. Preserve return-to-pool and leak prevention unchanged

**Decision:** Do not touch `_close_handle` / `_return_handle_to_pool` / `release`. A connection acquired lazily is indistinguishable from one acquired via `connection_named` once bound, so the existing teardown returns it to the pool and the `atexit`/`cleanup_pool` safety net still applies.

**Rationale:** Keeps the blast radius to acquisition only; the validated pooling/cleanup behaviour (and its session-leak guards) is untouched.

### D3. Treat lazy acquisition as a compatibility shim, documented in code

**Decision:** Add an inline comment on the override explaining that it restores the implicit "a thread can always reach a connection" contract that non-pooled adapters provide, and that it is required for upstream test classes (and any caller) that invoke adapter metadata methods outside an explicit `connection_named` block.

**Rationale:** Prevents a future contributor from "simplifying" the override away and re-introducing the `InvalidConnectionError`.

## Risks / Trade-offs

- **[Risk] Masking a genuine "forgot connection_named" programming error.** Auto-acquiring could hide a real missing-context bug elsewhere.
  → Mitigation: this matches the documented base-adapter expectation other adapters meet; the acquired connection is still tracked and released. Net behaviour is strictly more permissive and consistent, not silently wrong.
- **[Risk] Session/pool-slot leak if a lazily-acquired connection is never released.** A thread that acquires but is never `release`d could hold a pool slot.
  → Mitigation: lazily-acquired connections are stored in `thread_connections` like any other, so `release`/`cleanup_all`/`cleanup_pool` reclaim them; `_return_handle_to_pool` already closes handles beyond pool capacity. Add a functional test asserting no session growth after repeated thread-unbound metadata calls.
- **[Risk] Shared choke-point change affects every query path.**
  → Mitigation: re-run the full functional suite — connection-pool integration tests, concurrency, incremental, snapshots — against a live Exasol instance before unskipping the clone test.
- **[Trade-off] `BaseCloneSameSourceAndTarget` stays skipped.** Accepted: it asserts zero-copy-only output that Exasol's clone-as-view path never produces; out of scope here.
