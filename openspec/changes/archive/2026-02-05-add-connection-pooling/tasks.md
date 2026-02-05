# Tasks: Add Connection Pooling

## 1. Core Implementation

- [x] 1.1 Add `threading` and `hashlib` imports to `connections.py`
- [x] 1.2 Add `_pool: dict[str, ExaConnection] = {}` class attribute to `ExasolConnectionManager`
- [x] 1.3 Add `_pool_lock = threading.Lock()` class attribute to `ExasolConnectionManager`
- [x] 1.4 Implement `_get_pool()` class method to return the class-level pool dict
- [x] 1.5 Implement `_get_pool_key(credentials)` class method to generate credential hash
- [x] 1.6 Implement `_is_connection_valid(conn)` class method with `SELECT 1` validation
- [x] 1.7 Modify `open()` to acquire lock and check pool before creating new connection
- [x] 1.8 Modify `open()` to store new connections in pool after creation (with locking)
- [x] 1.9 Override `_close_handle()` to return connections to pool with locking instead of closing
- [x] 1.10 Implement `cleanup_pool()` class method to close all pooled connections (with locking)
- [x] 1.11 Implement `initialize_pool(credentials, size)` class method to pre-warm pool (with locking)

## 2. Test Infrastructure

- [x] 2.1 Add session-scoped `initialize_connection_pool` fixture to `tests/conftest.py`
- [x] 2.2 Read pool size from `DBT_CONN_POOL_SIZE` environment variable (default: 5)
- [x] 2.3 Add session-scoped `cleanup_connection_pool` fixture to `tests/conftest.py`

## 3. Unit Tests

- [x] 3.1 Create `tests/unit/test_connection_pool.py`
- [x] 3.2 Test `_get_pool_key()` generates consistent keys for same credentials
- [x] 3.3 Test `_get_pool_key()` generates different keys for different credentials
- [x] 3.4 Test `_is_connection_valid()` returns True for valid connection
- [x] 3.5 Test `_is_connection_valid()` returns False for closed connection
- [x] 3.6 Test `open()` reuses pooled connection when valid (with locking)
- [x] 3.7 Test `open()` creates new connection when pool empty
- [x] 3.8 Test `open()` removes invalid connection from pool and creates new
- [x] 3.9 Test `_close_handle()` returns connection to pool (with locking)
- [x] 3.10 Test `cleanup_pool()` closes all pooled connections (with locking)
- [x] 3.11 Test `initialize_pool()` creates specified number of connections (with locking)
- [x] 3.12 Test `initialize_pool()` with size from environment variable
- [x] 3.13 Test concurrent pool access from multiple threads

## 4. Validation

- [x] 4.1 Run existing unit tests to verify no regressions
- [x] 4.2 Run functional tests to verify improvement
- [x] 4.3 Profile test run to confirm reduced connection count
- [x] 4.4 Run linting and formatting checks
