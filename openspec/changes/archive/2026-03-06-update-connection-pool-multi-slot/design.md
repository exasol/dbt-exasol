# Design: Multi-Slot Connection Pool

## Context

The connection pool was introduced to reduce connection overhead during dbt runs and test sessions. The original design uses `dict[str, ExaConnection]` -- one connection per unique credentials hash. With dbt's `threads=N` (default 4), N worker threads share the same credentials. When each thread finishes a model and calls `_close_handle()`, only the first thread's connection is pooled; the remaining N-1 are closed. When the next model batch starts, N-1 threads must create new connections from scratch (~1s each for SSL + WebSocket + session setup).

**Constraints:**
- pyexasol connections are not thread-safe for concurrent use, but can be passed between threads when not in use
- dbt calls `release()` -> `close()` -> `_close_handle()` after each model, not just at end of run
- dbt calls `open()` (via `LazyHandle`) when a thread picks up its next model
- The pool must handle concurrent checkout/return from N threads

## Goals / Non-Goals

**Goals:**
- Pool up to N connections per credentials key, where N matches dbt's thread count
- Eliminate redundant connection teardown/setup between model executions
- Guarantee zero connection leaks: every connection is either pooled or explicitly closed
- Maintain thread safety
- Keep the change minimal -- same file, same patterns, list instead of single value

**Non-Goals:**
- Connection-per-thread affinity (threads get whichever connection is available)
- Dynamic pool resizing based on load
- Connection health monitoring / background eviction
- External connection pool library dependency

## Decisions

### Decision 1: List-based pool (`dict[str, list[ExaConnection]]`)

Replace `dict[str, ExaConnection]` with `dict[str, list[ExaConnection]]`. Use `list.pop()` for checkout and `list.append()` for return.

**Rationale:** Minimal structural change. A list naturally supports LIFO ordering, which keeps recently-used connections (most likely still valid) at the top. No new dependencies.

**Alternatives considered:**
- `collections.deque`: Thread-safe for append/pop but we already hold the lock, so no benefit over list. Adds import.
- `queue.Queue`: Built-in blocking semantics we don't need. Harder to iterate for cleanup. Overkill.
- Third-party pool (e.g., `sqlalchemy.pool`): Heavy dependency for a simple use case.

### Decision 2: Optional `pool_size` credential, mapped per credentials key

Add `pool_size: int | None = None` to `ExasolCredentials`. When `None` (the default), the effective pool size is resolved from dbt's `threads` setting at runtime. Users can override it explicitly in `profiles.yml`.

**Runtime resolution:** `BaseConnectionManager.__init__` receives `profile: AdapterRequiredConfig` which exposes `profile.threads: int`. During `__init__`, the connection manager generates the `pool_key` and stores the resolved pool size in a class-level dictionary `_pool_sizes: dict[str, int]`. The classmethods (`_close_handle`, `_try_get_pooled_connection`) read this value. If `credentials.pool_size` is explicitly set, that value takes precedence; otherwise `profile.threads` is used. The dictionary mapping approach correctly scopes the capacity limit to each distinct credential hash and handles environments where tests use `open()` prior to explicit instantiation safely by falling back to `credentials.pool_size` or 1.

**Rationale:** The pool size should match the thread count by default — users shouldn't need to duplicate the `threads` value as `pool_size`. Making it optional with auto-detection is the least-surprise behavior. A class-level dictionary avoids bugs inherent to a single shared `_effective_pool_size` scalar scalar attribute where different profiles or test suites could conflict or fail to be set at all before `open()` is called.

**Alternatives considered:**
- `_effective_pool_size: int = 1` scalar: Fragile class-level property that easily silently fails in multi-credential suites or direct classmethod fixture access without instantiation.
- `pool_size: int = 4` (hardcoded default): Requires users to manually keep `pool_size` in sync with `threads`. Easy to misconfigure.
- Environment variable only: Less discoverable than a profiles.yml parameter.
- Read `threads` in classmethods: Not possible — `open()` and `_close_handle()` are classmethods that only receive the `Connection` object, which has `credentials` but not `threads`.

### Decision 3: Validate before acquiring lock, guard inside lock

Move `_is_connection_valid()` call in `_close_handle()` to before the lock acquisition. Inside the lock, only check `is_closed` (fast attribute check) before appending. This reduces lock hold time from ~1ms (network round-trip for SELECT 1) to microseconds.

**Rationale:** With N threads returning connections concurrently, holding the lock during a network query causes unnecessary serialization. Validation before the lock is a best-effort check; the `is_closed` guard inside the lock catches the rare case where the connection dies between validation and lock acquisition.

### Decision 4: Excess connections closed immediately

When `_close_handle()` is called and the pool list for that key is already at `pool_size` capacity, the connection is closed immediately rather than pooled.

**Rationale:** Prevents unbounded pool growth. In normal operation with `pool_size` matching `threads`, this path is rarely hit (only during pool initialization or abnormal conditions).

### Decision 5: atexit handler for process exit cleanup with locked registration

Register `atexit.register(cls.cleanup_pool)` on the first call to `open()`. A class-level `_atexit_registered` flag protected by `cls._pool_lock` ensures the handler is registered exactly once.

**Rationale:** Connections sitting in the pool at process exit would otherwise leak database sessions. The atexit handler ensures they are always closed. Wrapping the flag and registration check inside `_pool_lock` prevents race conditions when N worker threads simultaneously execute `open()`.

### Decision 6: Exhaust invalid connections during checkout

When `_try_get_pooled_connection()` encounters an invalid connection in the pool list, it must continuously call `close()` and pop the entry until either a valid connection is found or the list is exhausted. Simply removing it from the list leaves the underlying socket/session open on the server, and failing to loop through the list could cause the pool to skip over an older, perfectly valid reusable handle underneath.

**Rationale:** An invalid connection (e.g., one where `SELECT 1` fails due to a network error) may still have a half-open socket. Calling `close()` ensures the server-side session is released. Exhausting the list is necessary to uncover correctly established sessions pooled prior to the invalid entry.

### Decision 8: `initialize_pool` explicitly creates new handles

Rather than using a loop of `open(conn)` and `_close_handle(conn)`, `initialize_pool()` must invoke connection creation directly and append to the list.

**Rationale:** When pre-warming a pool to capacity N, reusing `open` leads to the first connection being immediately pooled by `_close_handle`, then falsely re-checked-out by the next `open`, so N iterations only result in 1 handle. Explicit creation bypassed the checkout, assuring N distinct handles.

### Decision 9: Leak-free invariant, enforced by tests

The implementation must guarantee the invariant: after any sequence of `open()` / `_close_handle()` calls, every connection handle is either (a) in the pool, or (b) has had `close()` called. No connection is ever silently dropped.

**Testing strategy:**
- Unit tests: use mocks to track `close()` calls on every handle and assert the invariant
- Integration tests: track unique connection handles across multiple open/close cycles and verify `open_count == pooled_count` after cycles complete

## Architecture

```
ExasolConnectionManager
  _pool: dict[str, list[ExaConnection]] = {}   # key -> [conn, conn, ...]
  _pool_sizes: dict[str, int] = {}             # key -> capacity map
  _pool_lock: threading.Lock()

  open(connection):
    key = hash(credentials)
    with lock:
      if not cls._atexit_registered:
        atexit.register(cls.cleanup_pool)
        cls._atexit_registered = True
      while pool[key] has connections:
        conn = pool[key].pop()        # LIFO checkout
        if conn valid:
          use it
          break
        else:
          conn.close()
    if no valid conn:
      create new

  __init__(profile):
    super().__init__(profile)
    key = hash(credentials)
    if credentials.pool_size is not None:
      cls._pool_sizes[key] = credentials.pool_size
    else:
      cls._pool_sizes[key] = profile.threads

  _close_handle(connection):
    if valid (outside lock):
      with lock:
        capacity = cls._pool_sizes.get(key) or credentials.pool_size or 1
        if len(pool[key]) < capacity and not conn.is_closed:
          pool[key].append(conn)      # return to pool
        else:
          conn.close()                # pool full, close
    else:
      conn.close()                    # invalid, close

  cleanup_pool():
    with lock:
      for key, conns in pool.items():
        for conn in conns:
          conn.close()
      pool.clear()
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Pool size mismatch with threads | Defaults to `threads` automatically; explicit override available |
| Stale connections accumulate in pool | LIFO order keeps hot connections; validation on checkout |
| Validation outside lock is racy | `is_closed` guard inside lock catches concurrent invalidation |
| More connections kept open | Bounded by `pool_size`; same connections dbt would create anyway |
| Connection leak on process exit | atexit handler calls `cleanup_pool()` |
| Invalid connections leak during checkout | `_try_get_pooled_connection` explicitly closes invalid connections |

## Open Questions

None -- the change is straightforward and confined to a single file.
