# Design: Global Connection Pooling with Locking

## Context

Profiling of `pytest tests/functional` shows that a single test creates 41 database connections, consuming ~40 seconds of a 60-second test run. Each connection requires SSL handshake + WebSocket setup (~1s each). The pyexasol driver does not provide built-in connection pooling.

**Constraints:**
- pyexasol connections are not thread-safe ("Threads may share the module, but not connections")
- dbt-core uses `LazyHandle` pattern that calls `open()` when `connection.handle` is accessed
- dbt creates multiple connection contexts during test runs (fixtures, model runs, schema ops)

## Goals / Non-Goals

**Goals:**
- Reduce connection overhead by 80%+ through connection reuse
- Share connections across threads using a global pool with locking
- Ensure thread safety through explicit mutex locking
- Transparent to existing adapter code
- Validate connections before reuse to prevent stale connection errors

**Non-Goals:**
- Async connection handling
- Dynamic pool resizing at runtime
- Connection-per-thread isolation (using global shared pool instead)

## Decisions

### Decision 1: Global Pool with Mutex Locking

Use a class-level `dict` for the connection pool and `threading.Lock()` for thread-safe access.

**Rationale:** A global pool allows connection sharing across threads, maximizing reuse. While pyexasol connections are not thread-safe for concurrent use, they can be safely passed between threads when protected by a lock. The lock ensures only one thread accesses the pool at a time during checkout/return operations.

**Alternatives considered:**
- Thread-local pool: Simpler but wastes connections when work moves between threads
- Process-level pool: Not applicable, connections can't be pickled

### Decision 2: Pool Key by Credentials Hash

Generate pool key from `(dsn, user, database, schema)` tuple hash.

**Rationale:** Same credentials = same connection can be reused. Schema included because session state depends on it.

### Decision 3: Validate with SELECT 1

Run `SELECT 1` on pooled connections before returning.

**Rationale:** Detects closed/stale connections with minimal overhead (~1ms). Safer than just checking `is_closed` attribute.

**Alternatives considered:**
- Check `is_closed` only: Faster but may miss network failures
- Periodic background validation: Overkill for test scenarios

### Decision 4: Override _close_handle()

Override `_close_handle()` to skip actual close, keeping connection in pool.

**Rationale:** dbt-core calls `close()` frequently. Override prevents actual close while maintaining dbt's expected behavior.

### Decision 5: Configurable Pool Size via Environment Variable

Use `DBT_CONN_POOL_SIZE` environment variable (default: 5) to configure pool initialization size.

**Rationale:** Environment variables are the standard way to configure test infrastructure without code changes. Default of 5 balances pre-warming benefit with resource usage.

**Alternatives considered:**
- pytest.ini option: Less portable across CI environments
- Command-line argument: Requires test runner modifications
- Hardcoded value: Inflexible for different environments

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  ExasolConnectionManager                     │
├─────────────────────────────────────────────────────────────┤
│  _pool: dict[str, ExaConnection] = {}  (class-level)        │
│  _pool_lock: threading.Lock() = Lock() (class-level)        │
├─────────────────────────────────────────────────────────────┤
│  open(connection)                                            │
│    1. Generate pool key from credentials                     │
│    2. Acquire lock                                           │
│    3. Check pool for existing connection                     │
│    4. If found & valid → remove from pool, release lock      │
│    5. If not found → release lock, create new                │
│    6. Attach handle to connection object                     │
├─────────────────────────────────────────────────────────────┤
│  _close_handle(connection)                                   │
│    - Acquire lock                                            │
│    - Return connection to pool instead of close              │
│    - Release lock                                            │
│    - Only truly close on explicit cleanup                    │
├─────────────────────────────────────────────────────────────┤
│  initialize_pool(credentials, size)  [class method]         │
│    - Pre-create `size` connections for given credentials     │
│    - Called at start of test session via pytest fixture      │
│    - Size configurable via DBT_CONN_POOL_SIZE (default: 5)   │
│    - Thread-safe via lock                                    │
├─────────────────────────────────────────────────────────────┤
│  cleanup_pool()  [class method]                              │
│    - Acquire lock                                            │
│    - Close all pooled connections                            │
│    - Clear pool dictionary                                   │
│    - Release lock                                            │
└─────────────────────────────────────────────────────────────┘
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Stale connection state between tests | Validation query (`SELECT 1`) before reuse |
| Schema context issues | Pool key includes schema; `ALTER SESSION` only on new connections |
| Transaction leaks | dbt-core handles rollback before close |
| Thread contention | Lock held only briefly during pool access, not during connection use |
| Deadlocks | Single lock with no nested locking; always release in finally block |
| Memory leaks | `cleanup_pool()` called via session-scoped pytest fixture |

## Open Questions

None - all decisions confirmed during planning phase.
