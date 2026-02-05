# Change: Add Global Connection Pooling with Locking

## Why

Profiling functional tests reveals that **41 new database connections** are created for a single test taking 60 seconds, with ~40 seconds (67%) spent on connection establishment overhead. Each Exasol connection requires SSL handshake and WebSocket setup, taking ~1 second per connection. Connection pooling will dramatically reduce test execution time and improve adapter performance.

## What Changes

- Add global connection pool to `ExasolConnectionManager` with thread-safe locking
- Use `threading.Lock` to protect pool access across threads
- Cache and reuse connections based on credential hash
- Validate pooled connections with `SELECT 1` before reuse
- Override `_close_handle()` to return connections to pool instead of closing
- Add `cleanup_pool()` method for explicit pool cleanup
- Add `initialize_pool(credentials, size)` method to pre-warm pool with connections
- Add pytest fixture for session-scoped pool initialization and cleanup
- Support `DBT_CONN_POOL_SIZE` environment variable (default: 5) to configure pool size

## Impact

- Affected specs: New capability `connection-pooling`
- Affected code:
  - `dbt/adapters/exasol/connections.py` - Pool implementation
  - `tests/conftest.py` - Pool initialization and cleanup fixtures
  - `tests/unit/test_connection_pool.py` - New unit tests

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DBT_CONN_POOL_SIZE` | 5 | Number of connections to pre-initialize in the pool |

## Expected Results

| Metric | Before | After |
|--------|--------|-------|
| Connections per test | ~41 | ~1-3 |
| Connection overhead | ~40s | ~2-5s |
| Single test time | ~60s | ~20-25s |
