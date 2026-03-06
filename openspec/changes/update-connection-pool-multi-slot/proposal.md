# Change: Expand connection pool from single-slot to multi-slot per credentials

## Why

The current connection pool stores at most one connection per unique credentials hash (`dict[str, ExaConnection]`). When dbt runs with `threads=N`, all N threads share the same credentials key. On every model completion, `_close_handle()` is called -- the first thread's connection fills the single pool slot, and the remaining N-1 connections are closed (or leaked, before the recent bugfix). When the next batch of models starts, N-1 threads must create brand new connections (SSL handshake + WebSocket setup + ALTER SESSION), wasting ~1 second per connection per model batch.

## What Changes

- Change pool data structure from `dict[str, ExaConnection]` (one slot per key) to `dict[str, list[ExaConnection]]` (multiple slots per key)
- `_close_handle()`: append returned connections to the pool list instead of rejecting when a slot is occupied; close connections explicitly when the list exceeds the resolved effective pool size for that key or when the connection is invalid -- **no connection is ever silently dropped**
- `_try_get_pooled_connection()`: continuously pop from the list (LIFO); close and discard any invalid connections encountered during checkout until a valid connection is found or the list is exhausted
- `cleanup_pool()`: iterate and close all connections in all lists
- `initialize_pool()`: adapt to work with list-based pool by bypassing `open()`/checkout to guarantee N distinct new handles are pre-warmed
- Add an optional `pool_size` credential parameter (default: `None`) to control max pool size per credentials key; when omitted, the effective pool size is automatically resolved from dbt's `threads` setting via `profile.threads` during connection manager initialization
- Override `__init__` on `ExasolConnectionManager` to resolve and store the effective pool size per credential key as a class-level dictionary map `_pool_sizes`
- Register `atexit` handler on first `open()` call to close all pooled connections on process exit, explicitly protecting the check/registration flag with a lock to avoid racy duplicates
- `_is_connection_valid()` inside `_close_handle()`: move validation outside the lock to reduce lock contention (validate before acquiring lock, re-check `is_closed` inside lock)
- Add comprehensive leak prevention tests verifying that every connection is either pooled or closed after multi-threaded open/close cycles

## Impact

- Affected specs: `connection-pooling`
- Affected code: `dbt/adapters/exasol/connections.py` (ExasolConnectionManager, ExasolCredentials)
- Affected tests: `tests/unit/test_connection_pool.py`, `tests/functional/adapter/test_connection_pool_integration.py`
- No breaking changes to external API or profiles.yml (new `pool_size` parameter is optional and defaults to the `threads` value)
