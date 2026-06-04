## ADDED Requirements

### Requirement: On-Demand Thread Connection Acquisition

The adapter SHALL acquire a pooled connection on demand for the current thread when an adapter operation is issued on a thread that has no bound connection, instead of raising `InvalidConnectionError`. This restores the implicit contract — satisfied by non-pooled adapters — that a thread can always reach a connection, so callers (including upstream `dbt-tests-adapter` classes) may invoke adapter metadata methods without an explicit `connection_named(...)` block.

The lazily acquired connection SHALL be bound into the thread's connection registry so that the existing release / cleanup paths return it to the pool, and SHALL NOT bypass the pool, change the pool key, or leak database sessions.

#### Scenario: Metadata call on a thread with no bound connection succeeds
- **GIVEN** a thread that is not inside a `connection_named(...)` block and has no bound connection
- **WHEN** an adapter metadata method such as `list_relations` (which internally reaches `get_thread_connection()`) is called
- **THEN** the connection manager SHALL acquire a connection from the pool for that thread
- **AND** the call SHALL complete successfully
- **AND** no `InvalidConnectionError` SHALL be raised

#### Scenario: Lazily acquired connection is returned to the pool
- **GIVEN** a connection was acquired on demand for a thread with no prior binding
- **WHEN** the connection is released (via `release`) or the pool is cleaned up (via `cleanup_pool`)
- **THEN** the connection handle SHALL be returned to the pool or closed per the existing pool-capacity rules
- **AND** repeated thread-unbound metadata calls SHALL NOT cause the number of open database sessions to grow unbounded

#### Scenario: Existing bound connection is reused, not replaced
- **GIVEN** a thread that already has a bound, open connection (e.g. inside a `connection_named(...)` block)
- **WHEN** an adapter operation issues a query on that thread
- **THEN** the existing bound connection SHALL be reused
- **AND** no additional connection SHALL be acquired for that thread
