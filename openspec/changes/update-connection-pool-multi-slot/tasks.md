## 0. Preparation
- [ ] 0.1 Rebase `pr183` onto `origin/master` to incorporate latest test coverage changes
- [ ] 0.2 Verify rebase is clean and unit tests pass (`uv run nox -s test:unit`)

## 1. Pool Data Structure & Configuration
- [ ] 1.1 Change `_pool` type annotation from `dict[str, ExaConnection]` to `dict[str, list[ExaConnection]]`
- [ ] 1.2 Add `pool_size: int | None = None` field to `ExasolCredentials`
- [ ] 1.3 Add `_pool_sizes: dict[str, int]` class attribute (defaulting to empty dict) to `ExasolConnectionManager` to store resolved capacity per pool key
- [ ] 1.4 Override `__init__` on `ExasolConnectionManager` to resolve effective pool size for the current credentials key: use `credentials.pool_size` if set, otherwise `profile.threads`. Store it in `cls._pool_sizes[key]`

## 2. Pool Checkout (`_try_get_pooled_connection`)
- [ ] 2.1 Update to pop from the list (LIFO) instead of deleting the single key entry
- [ ] 2.2 Remove empty lists from the pool dict after last connection is popped
- [ ] 2.3 Continuously pop and close invalid connections until a valid connection is found or the list is exhausted (to avoid missing older valid reusable handles beneath invalid ones)

## 3. Pool Return (`_close_handle`)
- [ ] 3.1 Move `_is_connection_valid()` call outside the lock (best-effort pre-check)
- [ ] 3.2 Inside the lock: resolve capacity (`cls._pool_sizes.get(key) or credentials.pool_size or 1`) and check `is_closed` and `len(pool[key]) < capacity` before appending
- [ ] 3.3 Close connection immediately when pool is at capacity or connection is invalid
- [ ] 3.4 Retain defensive exception handling for close failures

## 4. Pool Cleanup (`cleanup_pool`)
- [ ] 4.1 Update to iterate `list[ExaConnection]` values and close each connection in each list

## 5. Pool Initialization (`initialize_pool`)
- [ ] 5.1 Update existing-count check to use `len(pool.get(key, []))` instead of single-entry check
- [ ] 5.2 Bypass checkout logic (do not use `open()` then `_close_handle()`) to guarantee N distinct handles are created and appended to the list, up to the maximum pool size

## 6. atexit Handler
- [ ] 6.1 Retain existing `_ensure_atexit_handler()` and `_atexit_registered` flag, but wrap the check and registration logic in the `_pool_lock` to prevent racy duplicate registration
- [ ] 6.2 Verify `cleanup_pool()` is registered via `atexit.register` exactly once on first `open()` call

## 7. Unit Tests
- [ ] 7.1 Update existing pool tests to work with `list`-based pool structure
- [ ] 7.2 Add test: multiple connections pooled for same credentials (up to effective pool size)
- [ ] 7.3 Add test: excess connections closed when pool is at capacity
- [ ] 7.4 Add test: LIFO checkout order
- [ ] 7.5 Add test: `pool_size` credential parameter defaults to `None`
- [ ] 7.6 Add test: effective pool size resolves from `profile.threads` when `pool_size` is `None`
- [ ] 7.7 Add test: explicit `pool_size` overrides `profile.threads`
- [ ] 7.8 Update concurrent access test for list-based pool
- [ ] 7.9 Add test: invalid connections closed (not just discarded) during checkout
- [ ] 7.10 Add test: atexit handler registered exactly once (run concurrent threads racing the first `open()` call)
- [ ] 7.11 Add leak invariant test: after N open/close cycles with M threads, assert every mock handle is either in pool or had `close()` called -- no handle is silently dropped
- [ ] 7.12 Add leak invariant test: with pool at capacity, excess connections have `close()` called
- [ ] 7.13 Add test: `initialize_pool()` produces N distinct handles in the pool list (assert size correctly bounded by capacity)
- [ ] 7.14 Add test: mixed valid/invalid list during checkout closes invalid entry and returns the older valid entry without allocating new connection

## 8. Integration Tests
- [ ] 8.1 Update existing integration tests for list-based pool assertions
- [ ] 8.2 Add test: N open/close cycles with threads=N result in N pooled connections, zero leaked sessions
- [ ] 8.3 Add test: `cleanup_pool()` after cycles leaves zero open connections
- [ ] 8.4 Add test: atexit handler is registered after first `open()`

## 9. Validation
- [ ] 9.1 Run format check (`uv run nox -s format:fix`)
- [ ] 9.2 Run lint (`uv run nox -s lint:code lint:security`)
- [ ] 9.3 Run unit tests (`uv run nox -s test:unit`)
- [ ] 9.4 Run integration tests if Exasol instance available (`uv run nox -s test:integration`)
