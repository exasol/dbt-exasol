# connection-pooling Specification

## Purpose
TBD - created by archiving change add-connection-pooling. Update Purpose after archive.
## Requirements
### Requirement: Global Connection Pool with Locking

The adapter SHALL maintain a global connection pool with thread-safe locking that caches database connections per unique credential set to reduce connection overhead.

#### Scenario: Pool storage initialization
- **GIVEN** an `ExasolConnectionManager` class
- **WHEN** accessed from any thread
- **THEN** a class-level pool dictionary SHALL be available via `_get_pool()`
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

The adapter SHALL reuse valid pooled connections instead of creating new ones when `open()` is called, using locking to ensure thread safety.

#### Scenario: Reuse valid pooled connection
- **GIVEN** a valid connection exists in the pool for the credential key
- **WHEN** `open()` is called with matching credentials
- **THEN** the pool lock SHALL be acquired
- **AND** the pooled connection SHALL be removed from the pool and reused
- **AND** the lock SHALL be released
- **AND** no new connection SHALL be created

#### Scenario: Create new connection when pool empty
- **GIVEN** no connection exists in the pool for the credential key
- **WHEN** `open()` is called
- **THEN** a new connection SHALL be created
- **AND** no lock contention SHALL occur during connection creation

#### Scenario: Replace invalid pooled connection
- **GIVEN** an invalid (closed) connection exists in the pool for the credential key
- **WHEN** `open()` is called with matching credentials
- **THEN** the invalid connection SHALL be removed from the pool
- **AND** a new connection SHALL be created

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

The adapter SHALL return connections to the pool when `_close_handle()` is called instead of closing them, using locking to ensure thread safety.

#### Scenario: Close handle returns connection to pool
- **GIVEN** a connection that was opened via the pool
- **WHEN** `_close_handle(connection)` is called
- **THEN** the pool lock SHALL be acquired
- **AND** the underlying pyexasol connection SHALL NOT be closed
- **AND** the connection SHALL be returned to the pool for reuse
- **AND** the lock SHALL be released

### Requirement: Pool Initialization

The adapter SHALL provide an `initialize_pool(credentials, size)` method to pre-warm the pool with connections.

#### Scenario: Initialize pool with specified size
- **GIVEN** valid credentials and a pool size of N
- **WHEN** `initialize_pool(credentials, size=N)` is called
- **THEN** N connections SHALL be created and stored in the pool
- **AND** the pool lock SHALL be used when adding connections

#### Scenario: Pool size from environment variable
- **GIVEN** the environment variable `DBT_CONN_POOL_SIZE` is set to "3"
- **WHEN** the test fixture reads the pool size
- **THEN** it SHALL use 3 as the pool size

#### Scenario: Default pool size
- **GIVEN** the environment variable `DBT_CONN_POOL_SIZE` is not set
- **WHEN** the test fixture reads the pool size
- **THEN** it SHALL use 5 as the default pool size

### Requirement: Thread-Safe Pool Cleanup

The adapter SHALL provide a `cleanup_pool()` method to close all pooled connections with thread-safe locking.

#### Scenario: Cleanup closes all pooled connections
- **GIVEN** multiple connections exist in the global pool
- **WHEN** `cleanup_pool()` is called
- **THEN** the pool lock SHALL be acquired
- **AND** all pooled connections SHALL be closed
- **AND** the pool SHALL be empty
- **AND** the lock SHALL be released

#### Scenario: Cleanup handles already-closed connections
- **GIVEN** a pooled connection that is already closed
- **WHEN** `cleanup_pool()` is called
- **THEN** it SHALL NOT raise an exception
- **AND** the connection SHALL be removed from the pool

