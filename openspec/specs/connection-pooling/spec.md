# connection-pooling Specification

## Purpose
TBD - created by archiving change add-connection-pooling. Update Purpose after archive.
## Requirements
### Requirement: Global Connection Pool with Locking

The adapter SHALL maintain a global connection pool with thread-safe locking that caches multiple database connections per unique credential set to reduce connection overhead. The pool SHALL store up to the effective pool size connections per credentials key, where the effective pool size is determined by `credentials.pool_size` if set, or `profile.threads` otherwise.

#### Scenario: Pool storage initialization
- **GIVEN** an `ExasolConnectionManager` class
- **WHEN** accessed from any thread
- **THEN** a class-level pool dictionary SHALL be available via `_get_pool()`
- **AND** the pool SHALL be typed as `dict[str, list[ExaConnection]]`
- **AND** a class-level `threading.Lock` SHALL protect pool access

#### Scenario: Pool key generation
- **GIVEN** an `ExasolCredentials` instance
- **WHEN** `_get_pool_key(credentials)` is called
- **THEN** it SHALL return a consistent hash based on `(dsn, user, database, schema)`

#### Scenario: Same credentials produce same key
- **GIVEN** two `ExasolCredentials` instances with identical `dsn`, `user`, `database`, and `schema`
- **WHEN** `_get_pool_key()` is called on each
- **THEN** both calls SHALL return the same key

### Requirement: Thread-Safe Connection Reuse

The adapter SHALL reuse valid pooled connections instead of creating new ones when `open()` is called, using locking to ensure thread safety. When multiple connections are pooled for the same credentials, the most recently returned connection SHALL be reused first (LIFO order).

#### Scenario: Reuse valid pooled connection
- **GIVEN** one or more valid connections exist in the pool list for the credential key
- **WHEN** `open()` is called with matching credentials
- **THEN** the pool lock SHALL be acquired
- **AND** the most recently returned connection SHALL be popped from the pool list
- **AND** the lock SHALL be released
- **AND** no new connection SHALL be created

#### Scenario: Create new connection when pool empty
- **GIVEN** no connection exists in the pool for the credential key
- **WHEN** `open()` is called
- **THEN** a new connection SHALL be created
- **AND** no lock contention SHALL occur during connection creation

#### Scenario: Replace invalid pooled connection
- **GIVEN** only invalid (closed) connections exist in the pool for the credential key
- **WHEN** `open()` is called with matching credentials
- **THEN** the invalid connections SHALL be closed and removed from the pool
- **AND** a new connection SHALL be created

#### Scenario: Replace invalid pooled connection above valid connection
- **GIVEN** an invalid connection sits on top of a valid connection in the pool list for the credential key
- **WHEN** `open()` is called with matching credentials
- **THEN** the invalid connection SHALL be closed and removed from the pool
- **AND** the older valid connection SHALL be popped and reused
- **AND** no new connection SHALL be created

#### Scenario: Concurrent pool access
- **GIVEN** multiple threads accessing the pool simultaneously
- **WHEN** they attempt to checkout or return connections
- **THEN** the lock SHALL serialize access
- **AND** no race conditions SHALL occur

### Requirement: Connection Validation

The adapter SHALL validate pooled connections before reuse by executing `SELECT 1`.

#### Scenario: Valid connection passes validation
- **GIVEN** a pooled connection that can execute queries
- **WHEN** `_is_connection_valid(conn)` is called
- **THEN** it SHALL return `True`

#### Scenario: Closed connection fails validation
- **GIVEN** a pooled connection with `is_closed` attribute set to `True`
- **WHEN** `_is_connection_valid(conn)` is called
- **THEN** it SHALL return `False`

#### Scenario: Connection with network error fails validation
- **GIVEN** a pooled connection that raises an exception on `execute()`
- **WHEN** `_is_connection_valid(conn)` is called
- **THEN** it SHALL return `False`

### Requirement: Thread-Safe Connection Return

The adapter SHALL return connections to the pool when `_close_handle()` is called, up to the effective pool size limit. Connections that exceed the pool capacity or are invalid SHALL be closed immediately to prevent session leaks.

#### Scenario: Close handle returns connection to pool when capacity available
- **GIVEN** a valid connection and the pool list for its credentials has fewer than the effective pool size entries
- **WHEN** `_close_handle(connection)` is called
- **THEN** the connection SHALL be appended to the pool list
- **AND** the underlying pyexasol connection SHALL NOT be closed

#### Scenario: Close handle closes connection when pool is at capacity
- **GIVEN** a valid connection and the pool list for its credentials already has the effective pool size entries
- **WHEN** `_close_handle(connection)` is called
- **THEN** the connection SHALL be closed immediately
- **AND** it SHALL NOT be added to the pool

#### Scenario: Close handle closes invalid connection
- **GIVEN** a connection that fails validation
- **WHEN** `_close_handle(connection)` is called
- **THEN** the connection SHALL be closed immediately
- **AND** it SHALL NOT be added to the pool

#### Scenario: Close handle tolerates close failure
- **GIVEN** a connection that cannot be pooled and whose `close()` raises an exception
- **WHEN** `_close_handle(connection)` is called
- **THEN** the exception SHALL be caught and logged
- **AND** no exception SHALL propagate to the caller

### Requirement: Pool Initialization

The adapter SHALL provide an `initialize_pool(credentials, size)` method to pre-warm the pool with N distinct connections using the list-based pool structure, without utilizing standard connection checkout which could inadvertently reuse handles.

#### Scenario: Initialize pool with specified size
- **GIVEN** valid credentials and a pool size of N
- **WHEN** `initialize_pool(credentials, size=N)` is called
- **THEN** up to N distinct connections SHALL be created and stored in the pool list
- **AND** the pool lock SHALL be used when adding connections
- **AND** standard connection checkout (`open`) SHALL be bypassed to guarantee newly allocated handles

#### Scenario: Pool size from environment variable
- **GIVEN** the environment variable `DBT_CONN_POOL_SIZE` is set to "3"
- **WHEN** the test fixture reads the pool size
- **THEN** it SHALL use 3 as the pool size

#### Scenario: Default pool size
- **GIVEN** the environment variable `DBT_CONN_POOL_SIZE` is not set
- **WHEN** the test fixture reads the pool size
- **THEN** it SHALL use 5 as the default pool size

### Requirement: Thread-Safe Pool Cleanup

The adapter SHALL provide a `cleanup_pool()` method to close all pooled connections across all pool lists with thread-safe locking.

#### Scenario: Cleanup closes all pooled connections
- **GIVEN** multiple connections exist across one or more pool lists
- **WHEN** `cleanup_pool()` is called
- **THEN** the pool lock SHALL be acquired
- **AND** all connections in all pool lists SHALL be closed
- **AND** the pool SHALL be empty
- **AND** the lock SHALL be released

#### Scenario: Cleanup handles already-closed connections
- **GIVEN** a pooled connection that is already closed
- **WHEN** `cleanup_pool()` is called
- **THEN** it SHALL NOT raise an exception
- **AND** the connection SHALL be removed from the pool

### Requirement: Process Exit Cleanup

The adapter SHALL register an `atexit` handler to close all pooled connections when the Python process exits. The handler SHALL be registered exactly once, on the first call to `open()`. A class-level lock SHALL protect the registration check to ensure a single registration event even under concurrent execution.

#### Scenario: atexit handler registered on first open
- **GIVEN** the `ExasolConnectionManager` has not yet opened any connection
- **WHEN** `open()` is called for the first time
- **THEN** an `atexit` handler SHALL be registered that calls `cleanup_pool()`
- **AND** subsequent calls to `open()` SHALL NOT register additional handlers
- **AND** concurrent first calls to `open()` SHALL strictly register exactly once

#### Scenario: Pooled connections closed on process exit
- **GIVEN** connections exist in the pool when the Python process exits
- **WHEN** the `atexit` handler runs
- **THEN** all pooled connections SHALL be closed
- **AND** the pool SHALL be empty

### Requirement: Connection Leak Prevention

The adapter SHALL guarantee that every database connection is either returned to the pool or explicitly closed. No connection SHALL be silently dropped without calling `close()`.

#### Scenario: No leaks during multi-thread open/close cycles
- **GIVEN** N threads each opening and closing connections over multiple model execution cycles
- **WHEN** all cycles complete
- **THEN** the number of open connections SHALL equal the number of connections in the pool
- **AND** all other connections SHALL have been explicitly closed

#### Scenario: No leaks when pool is at capacity
- **GIVEN** the pool is at the effective pool size limit
- **WHEN** additional connections are returned via `_close_handle()`
- **THEN** each excess connection SHALL be explicitly closed
- **AND** no connection handle SHALL be dropped without `close()` being called

#### Scenario: Invalid connections closed during checkout
- **GIVEN** invalid connections exist in the pool list
- **WHEN** `_try_get_pooled_connection()` encounters them during checkout
- **THEN** each invalid connection SHALL be closed
- **AND** it SHALL be removed from the pool list

### Requirement: Pool Size Configuration

The adapter SHALL support an optional `pool_size` parameter in `ExasolCredentials` to control the maximum number of connections pooled per unique credentials key. When `pool_size` is not set, the effective pool size SHALL default to the value of `profile.threads`. The connection manager SHALL resolve the effective pool size during initialization and store it as a class-level dictionary mapping credential keys to capacities. Classmethods SHALL resolve capacity by checking this mapping and falling back to `credentials.pool_size` or 1.

#### Scenario: Default pool size matches threads
- **GIVEN** an `ExasolCredentials` instance with no explicit `pool_size`
- **AND** the dbt profile has `threads: 4`
- **WHEN** the `ExasolConnectionManager` is initialized
- **THEN** the effective pool size SHALL be 4

#### Scenario: Default pool size with custom threads
- **GIVEN** an `ExasolCredentials` instance with no explicit `pool_size`
- **AND** the dbt profile has `threads: 8`
- **WHEN** the `ExasolConnectionManager` is initialized
- **THEN** the effective pool size SHALL be 8

#### Scenario: Explicit pool_size overrides threads
- **GIVEN** a `profiles.yml` with `pool_size: 2` and `threads: 8`
- **WHEN** the `ExasolConnectionManager` is initialized
- **THEN** the effective pool size SHALL be 2

#### Scenario: Pool size limits pooled connections
- **GIVEN** the effective pool size is N
- **WHEN** more than N connections are returned via `_close_handle()`
- **THEN** only N connections SHALL be retained in the pool
- **AND** excess connections SHALL be closed immediately

