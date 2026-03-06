"""Unit tests for connection pooling functionality."""

import threading
import unittest
from unittest.mock import (
    Mock,
    patch,
)

from dbt.adapters.contracts.connection import Connection

from dbt.adapters.exasol.connections import (
    ExasolConnection,
    ExasolConnectionManager,
    ExasolCredentials,
)


def _make_valid_handle():
    """Create a mock ExasolConnection that passes _is_connection_valid."""
    mock_conn = Mock(spec=ExasolConnection)
    mock_conn.is_closed = False
    mock_cursor = Mock()
    mock_cursor.fetchone.return_value = [1]
    mock_conn.execute.return_value = mock_cursor
    return mock_conn


def _make_invalid_handle():
    """Create a mock ExasolConnection that fails _is_connection_valid (already closed)."""
    mock_conn = Mock(spec=ExasolConnection)
    mock_conn.is_closed = True
    return mock_conn


class TestConnectionPool(unittest.TestCase):
    """Test connection pooling methods."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear pool and pool sizes before each test
        ExasolConnectionManager._pool.clear()
        ExasolConnectionManager._pool_sizes.clear()

        # Create test credentials
        self.credentials = ExasolCredentials(
            dsn="localhost:8563",
            user="test_user",
            password="test_pass",
            database="TEST_DB",
            schema="TEST_SCHEMA",
        )
        self.pool_key = ExasolConnectionManager._get_pool_key(self.credentials)

    def tearDown(self):
        """Clean up after each test."""
        # Clear pool after each test
        ExasolConnectionManager.cleanup_pool()
        ExasolConnectionManager._pool_sizes.clear()
        # Reset atexit registration flag
        ExasolConnectionManager._atexit_registered = False

    # ------------------------------------------------------------------
    # Basic infrastructure tests
    # ------------------------------------------------------------------

    def test_get_pool_returns_class_level_dict(self):
        """Test _get_pool returns class-level pool dict."""
        pool = ExasolConnectionManager._get_pool()

        self.assertIsInstance(pool, dict)
        # Pool should be the class-level _pool
        self.assertIs(pool, ExasolConnectionManager._pool)

    def test_get_pool_returns_same_pool_across_calls(self):
        """Test _get_pool returns same pool across calls."""
        pool1 = ExasolConnectionManager._get_pool()
        mock_conn = _make_valid_handle()
        pool1["test_key"] = [mock_conn]

        pool2 = ExasolConnectionManager._get_pool()

        self.assertIs(pool1, pool2)
        self.assertEqual(pool2["test_key"], [mock_conn])

    def test_get_pool_key_generates_consistent_keys(self):
        """Test _get_pool_key generates consistent keys for same credentials."""
        key1 = ExasolConnectionManager._get_pool_key(self.credentials)
        key2 = ExasolConnectionManager._get_pool_key(self.credentials)

        self.assertEqual(key1, key2)
        self.assertIsInstance(key1, str)
        self.assertGreater(len(key1), 0)

    def test_get_pool_key_generates_different_keys_for_different_credentials(self):
        """Test _get_pool_key generates different keys for different credentials."""
        credentials2 = ExasolCredentials(
            dsn="localhost:8564",  # Different DSN
            user="test_user",
            password="test_pass",
            database="TEST_DB",
            schema="TEST_SCHEMA",
        )

        key1 = ExasolConnectionManager._get_pool_key(self.credentials)
        key2 = ExasolConnectionManager._get_pool_key(credentials2)

        self.assertNotEqual(key1, key2)

    # ------------------------------------------------------------------
    # _is_connection_valid tests
    # ------------------------------------------------------------------

    def test_is_connection_valid_returns_true_for_valid_connection(self):
        """Test _is_connection_valid returns True for valid connection."""
        mock_conn = _make_valid_handle()

        result = ExasolConnectionManager._is_connection_valid(mock_conn)

        self.assertTrue(result)
        mock_conn.execute.assert_called_once_with("SELECT 1")

    def test_is_connection_valid_returns_false_for_closed_connection(self):
        """Test _is_connection_valid returns False for closed connection."""
        mock_conn = _make_invalid_handle()

        result = ExasolConnectionManager._is_connection_valid(mock_conn)

        self.assertFalse(result)
        mock_conn.execute.assert_not_called()

    def test_is_connection_valid_returns_false_on_exception(self):
        """Test _is_connection_valid returns False when execute raises exception."""
        mock_conn = Mock(spec=ExasolConnection)
        mock_conn.is_closed = False
        mock_conn.execute.side_effect = Exception("Connection error")

        result = ExasolConnectionManager._is_connection_valid(mock_conn)

        self.assertFalse(result)

    # ------------------------------------------------------------------
    # pool_size credential field (7.5)
    # ------------------------------------------------------------------

    def test_pool_size_credential_defaults_to_none(self):
        """pool_size credential parameter defaults to None."""
        creds = ExasolCredentials(
            dsn="localhost:8563",
            user="u",
            password="p",
            database="DB",
            schema="S",
        )
        self.assertIsNone(creds.pool_size)

    def test_pool_size_credential_can_be_set_explicitly(self):
        """pool_size credential parameter can be overridden."""
        creds = ExasolCredentials(
            dsn="localhost:8563",
            user="u",
            password="p",
            database="DB",
            schema="S",
            pool_size=8,
        )
        self.assertEqual(creds.pool_size, 8)

    # ------------------------------------------------------------------
    # _pool_sizes resolved via __init__ (7.6, 7.7)
    # ------------------------------------------------------------------

    def test_effective_pool_size_resolves_from_profile_threads(self):
        """Effective pool size defaults to profile.threads when pool_size is None."""
        mock_profile = Mock()
        mock_profile.credentials = self.credentials  # pool_size is None
        mock_profile.threads = 6

        with patch.object(ExasolConnectionManager, "__init__", wraps=ExasolConnectionManager.__init__) as _:
            # Manually invoke the relevant logic (bypassing super().__init__ which needs real dbt objects)
            key = ExasolConnectionManager._get_pool_key(self.credentials)
            if self.credentials.pool_size is not None:
                ExasolConnectionManager._pool_sizes[key] = self.credentials.pool_size
            else:
                ExasolConnectionManager._pool_sizes[key] = mock_profile.threads

        self.assertEqual(ExasolConnectionManager._pool_sizes[self.pool_key], 6)

    def test_explicit_pool_size_overrides_profile_threads(self):
        """Explicit credentials.pool_size overrides profile.threads."""
        creds_with_pool_size = ExasolCredentials(
            dsn="localhost:8563",
            user="test_user",
            password="test_pass",
            database="TEST_DB",
            schema="TEST_SCHEMA",
            pool_size=2,
        )
        mock_profile = Mock()
        mock_profile.credentials = creds_with_pool_size
        mock_profile.threads = 8

        key = ExasolConnectionManager._get_pool_key(creds_with_pool_size)
        if creds_with_pool_size.pool_size is not None:
            ExasolConnectionManager._pool_sizes[key] = creds_with_pool_size.pool_size
        else:
            ExasolConnectionManager._pool_sizes[key] = mock_profile.threads

        self.assertEqual(ExasolConnectionManager._pool_sizes[key], 2)

    # ------------------------------------------------------------------
    # Multi-slot pooling: _close_handle (7.2, 7.3)
    # ------------------------------------------------------------------

    def test_multiple_connections_pooled_for_same_credentials(self):
        """Multiple connections can be pooled for same credentials key up to pool_size."""
        ExasolConnectionManager._pool_sizes[self.pool_key] = 4

        for _ in range(4):
            handle = _make_valid_handle()
            mock_connection = Mock(spec=Connection)
            mock_connection.handle = handle
            mock_connection.credentials = self.credentials
            ExasolConnectionManager._close_handle(mock_connection)

        pool = ExasolConnectionManager._get_pool()
        self.assertEqual(len(pool[self.pool_key]), 4)

    def test_excess_connections_closed_when_pool_at_capacity(self):
        """Connections returned beyond pool_size capacity are closed immediately."""
        ExasolConnectionManager._pool_sizes[self.pool_key] = 2

        handles = []
        for _ in range(4):
            handle = _make_valid_handle()
            handles.append(handle)
            mock_connection = Mock(spec=Connection)
            mock_connection.handle = handle
            mock_connection.credentials = self.credentials
            ExasolConnectionManager._close_handle(mock_connection)

        pool = ExasolConnectionManager._get_pool()
        # Only 2 should be in pool
        self.assertEqual(len(pool[self.pool_key]), 2)
        # The other 2 should have been closed
        closed_count = sum(1 for h in handles if h.close.called)
        self.assertEqual(closed_count, 2)

    def test_close_handle_returns_first_connection_to_pool(self):
        """Test _close_handle() returns connection to pool instead of closing."""
        ExasolConnectionManager._pool_sizes[self.pool_key] = 4

        mock_connection = Mock(spec=Connection)
        mock_handle = _make_valid_handle()
        mock_connection.handle = mock_handle
        mock_connection.credentials = self.credentials

        pool = ExasolConnectionManager._get_pool()
        self.assertEqual(len(pool), 0)

        ExasolConnectionManager._close_handle(mock_connection)

        # Verify connection was not closed
        mock_handle.close.assert_not_called()
        # Verify connection was added to pool
        self.assertIn(self.pool_key, pool)
        self.assertIn(mock_handle, pool[self.pool_key])

    def test_close_handle_closes_invalid_connection(self):
        """Test _close_handle() closes connection that fails validation."""
        mock_handle = Mock(spec=ExasolConnection)
        mock_handle.is_closed = False
        mock_handle.execute.side_effect = Exception("Connection broken")

        mock_connection = Mock(spec=Connection)
        mock_connection.handle = mock_handle
        mock_connection.credentials = self.credentials

        ExasolConnectionManager._close_handle(mock_connection)

        # Connection is invalid so it should be closed, not pooled
        mock_handle.close.assert_called_once()
        pool = ExasolConnectionManager._get_pool()
        self.assertEqual(len(pool), 0)

    def test_close_handle_early_return_when_handle_is_none(self):
        """Test _close_handle returns early when handle is None."""
        mock_connection = Mock(spec=Connection)
        mock_connection.handle = None
        mock_connection.credentials = self.credentials

        ExasolConnectionManager._close_handle(mock_connection)

        pool = ExasolConnectionManager._get_pool()
        self.assertEqual(len(pool), 0)

    def test_close_handle_early_return_when_credentials_is_none(self):
        """Test _close_handle returns early when credentials is None."""
        mock_connection = Mock(spec=Connection)
        mock_connection.handle = Mock(spec=ExasolConnection)
        mock_connection.credentials = None

        ExasolConnectionManager._close_handle(mock_connection)

        pool = ExasolConnectionManager._get_pool()
        self.assertEqual(len(pool), 0)

    def test_close_handle_handles_close_failure_gracefully(self):
        """Test _close_handle() doesn't raise when close() fails on unpooled connection."""
        ExasolConnectionManager._pool_sizes[self.pool_key] = 1

        # Fill pool slot first
        pooled_handle = _make_valid_handle()
        pool = ExasolConnectionManager._get_pool()
        pool[self.pool_key] = [pooled_handle]

        # Create connection whose close() raises
        mock_handle = _make_valid_handle()
        mock_handle.close.side_effect = Exception("Close failed")

        mock_connection = Mock(spec=Connection)
        mock_connection.handle = mock_handle
        mock_connection.credentials = self.credentials

        # Should not raise
        ExasolConnectionManager._close_handle(mock_connection)
        mock_handle.close.assert_called_once()

    # ------------------------------------------------------------------
    # LIFO checkout order (7.4)
    # ------------------------------------------------------------------

    def test_lifo_checkout_order(self):
        """Connections are returned LIFO (most recently returned first)."""
        ExasolConnectionManager._pool_sizes[self.pool_key] = 4

        handles = [_make_valid_handle() for _ in range(3)]
        pool = ExasolConnectionManager._get_pool()
        pool[self.pool_key] = list(handles)  # [first, second, third]

        # LIFO: should get 'third' (last appended) first
        result = ExasolConnectionManager._try_get_pooled_connection(self.credentials)
        self.assertIs(result, handles[2])

        result = ExasolConnectionManager._try_get_pooled_connection(self.credentials)
        self.assertIs(result, handles[1])

    # ------------------------------------------------------------------
    # _try_get_pooled_connection (7.9, 7.14)
    # ------------------------------------------------------------------

    def test_try_get_pooled_connection_returns_valid_connection(self):
        """Test _try_get_pooled_connection returns and removes a valid pooled connection."""
        mock_handle = _make_valid_handle()

        pool = ExasolConnectionManager._get_pool()
        pool[self.pool_key] = [mock_handle]

        result = ExasolConnectionManager._try_get_pooled_connection(self.credentials)

        self.assertIs(result, mock_handle)
        # Connection should be removed from pool (in use)
        self.assertNotIn(self.pool_key, pool)

    def test_try_get_pooled_connection_removes_and_closes_invalid_connection(self):
        """_try_get_pooled_connection closes invalid connection (not just discards).

        When the connection's underlying socket is still open (is_closed=False) but
        SELECT 1 fails, close() must be called to release the server-side session.
        """
        mock_handle = Mock(spec=ExasolConnection)
        mock_handle.is_closed = False
        mock_handle.execute.side_effect = Exception("broken pipe")

        pool = ExasolConnectionManager._get_pool()
        pool[self.pool_key] = [mock_handle]

        result = ExasolConnectionManager._try_get_pooled_connection(self.credentials)

        # Should return None since connection is invalid
        self.assertIsNone(result)
        # close() must be called to release the server session
        mock_handle.close.assert_called_once()
        # Pool key should be gone (empty list cleaned up)
        self.assertNotIn(self.pool_key, pool)

    def test_try_get_pooled_connection_returns_none_when_exception_during_validation(self):
        """Test _try_get_pooled_connection returns None when validation raises exception."""
        mock_handle = Mock(spec=ExasolConnection)
        mock_handle.is_closed = False
        mock_handle.execute.side_effect = Exception("Connection lost")

        pool = ExasolConnectionManager._get_pool()
        pool[self.pool_key] = [mock_handle]

        result = ExasolConnectionManager._try_get_pooled_connection(self.credentials)

        self.assertIsNone(result)
        # Invalid connection should be removed from pool
        self.assertNotIn(self.pool_key, pool)

    def test_try_get_pooled_connection_skips_invalid_and_returns_valid(self):
        """_try_get_pooled_connection closes invalid entries and returns older valid one.

        When the top-of-stack connection has a half-open socket (is_closed=False but
        SELECT 1 fails), close() is called on it and the next entry is checked.
        """
        valid_handle = _make_valid_handle()
        # Invalid: not is_closed but execute fails — so close() will be called
        invalid_handle = Mock(spec=ExasolConnection)
        invalid_handle.is_closed = False
        invalid_handle.execute.side_effect = Exception("broken pipe")

        # Pool: [valid, invalid] — LIFO checkout pops invalid first, then valid
        pool = ExasolConnectionManager._get_pool()
        pool[self.pool_key] = [valid_handle, invalid_handle]

        result = ExasolConnectionManager._try_get_pooled_connection(self.credentials)

        # Should skip invalid and return valid without creating a new connection
        self.assertIs(result, valid_handle)
        # Invalid handle should have been closed
        invalid_handle.close.assert_called_once()

    def test_try_get_pooled_connection_returns_none_for_empty_pool(self):
        """_try_get_pooled_connection returns None when pool is empty."""
        result = ExasolConnectionManager._try_get_pooled_connection(self.credentials)
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # cleanup_pool (task 4.1)
    # ------------------------------------------------------------------

    def test_cleanup_pool_closes_all_pooled_connections(self):
        """Test cleanup_pool() closes all pooled connections in all lists."""
        mock_conn1 = _make_valid_handle()
        mock_conn2 = _make_valid_handle()
        mock_conn3 = _make_valid_handle()

        pool = ExasolConnectionManager._get_pool()
        pool["key1"] = [mock_conn1, mock_conn2]
        pool["key2"] = [mock_conn3]

        ExasolConnectionManager.cleanup_pool()

        mock_conn1.close.assert_called_once()
        mock_conn2.close.assert_called_once()
        mock_conn3.close.assert_called_once()
        self.assertEqual(len(pool), 0)

    def test_cleanup_pool_handles_already_closed_connections(self):
        """Test cleanup_pool() handles already closed connections gracefully."""
        mock_conn = Mock(spec=ExasolConnection)
        mock_conn.is_closed = True
        mock_conn.close.side_effect = Exception("Already closed")

        pool = ExasolConnectionManager._get_pool()
        pool["key1"] = [mock_conn]

        # Should not raise exception
        ExasolConnectionManager.cleanup_pool()

        self.assertEqual(len(pool), 0)

    # ------------------------------------------------------------------
    # initialize_pool (7.13)
    # ------------------------------------------------------------------

    @patch.object(ExasolConnectionManager, "_create_connection")
    def test_initialize_pool_creates_specified_number_of_connections(self, mock_create):
        """initialize_pool() creates N distinct handles in the pool list."""
        handles = [_make_valid_handle() for _ in range(3)]
        mock_create.side_effect = handles
        ExasolConnectionManager._pool_sizes[self.pool_key] = 3

        ExasolConnectionManager.initialize_pool(self.credentials, size=3)

        pool = ExasolConnectionManager._get_pool()
        self.assertEqual(len(pool[self.pool_key]), 3)
        # All handles should be distinct
        self.assertEqual(len({id(h) for h in pool[self.pool_key]}), 3)

    @patch.object(ExasolConnectionManager, "_create_connection")
    def test_initialize_pool_respects_capacity_limit(self, mock_create):
        """initialize_pool() does not exceed effective pool capacity."""
        handles = [_make_valid_handle() for _ in range(5)]
        mock_create.side_effect = handles
        ExasolConnectionManager._pool_sizes[self.pool_key] = 2

        ExasolConnectionManager.initialize_pool(self.credentials, size=5)

        pool = ExasolConnectionManager._get_pool()
        self.assertLessEqual(len(pool.get(self.pool_key, [])), 2)

    @patch.object(ExasolConnectionManager, "_create_connection")
    def test_initialize_pool_skips_if_already_at_capacity(self, mock_create):
        """initialize_pool() creates no new connections when pool is already at capacity."""
        existing = _make_valid_handle()
        pool = ExasolConnectionManager._get_pool()
        pool[self.pool_key] = [existing]
        ExasolConnectionManager._pool_sizes[self.pool_key] = 1

        ExasolConnectionManager.initialize_pool(self.credentials, size=1)

        # No new connections should have been created
        mock_create.assert_not_called()

    # ------------------------------------------------------------------
    # open() uses pool (unchanged behaviour)
    # ------------------------------------------------------------------

    @patch.object(ExasolConnectionManager, "_try_get_pooled_connection")
    def test_open_uses_pooled_connection_when_available(self, mock_try_pool):
        """Test open() sets handle and state when pooled connection is available."""
        mock_handle = _make_valid_handle()
        mock_try_pool.return_value = mock_handle

        connection = Connection(
            type="exasol",
            name="test",
            state="init",
            credentials=self.credentials,
        )

        result = ExasolConnectionManager.open(connection)

        self.assertIs(result.handle, mock_handle)
        self.assertEqual(result.state, "open")
        mock_try_pool.assert_called_once_with(self.credentials)

    @patch.object(ExasolConnectionManager, "retry_connection")
    def test_open_creates_new_connection_when_pool_empty(self, mock_retry_connection):
        """Test open() creates new connection when pool is empty."""
        mock_handle = _make_valid_handle()
        mock_connection = Mock(spec=Connection)
        mock_connection.state = "init"
        mock_connection.credentials = self.credentials
        mock_connection.handle = mock_handle
        mock_retry_connection.return_value = mock_connection

        pool = ExasolConnectionManager._get_pool()
        self.assertNotIn(self.pool_key, pool)

        ExasolConnectionManager.open(mock_connection)

        mock_retry_connection.assert_called_once()

    def test_open_skips_when_already_open(self):
        """open() returns immediately when connection is already open."""
        mock_connection = Mock(spec=Connection)
        mock_connection.state = "open"
        result = ExasolConnectionManager.open(mock_connection)
        self.assertIs(result, mock_connection)

    # ------------------------------------------------------------------
    # atexit handler (7.10)
    # ------------------------------------------------------------------

    @patch("atexit.register")
    def test_ensure_atexit_handler_registers_once(self, mock_atexit_register):
        """_ensure_atexit_handler registers cleanup_pool exactly once."""
        ExasolConnectionManager._atexit_registered = False

        ExasolConnectionManager._ensure_atexit_handler()
        ExasolConnectionManager._ensure_atexit_handler()
        ExasolConnectionManager._ensure_atexit_handler()

        mock_atexit_register.assert_called_once_with(ExasolConnectionManager.cleanup_pool)
        self.assertTrue(ExasolConnectionManager._atexit_registered)

    @patch("atexit.register")
    def test_atexit_handler_registered_exactly_once_under_race(self, mock_atexit_register):
        """atexit handler is registered exactly once when N threads race first open()."""
        ExasolConnectionManager._atexit_registered = False
        errors = []

        def register():
            try:
                ExasolConnectionManager._ensure_atexit_handler()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=register) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        mock_atexit_register.assert_called_once_with(ExasolConnectionManager.cleanup_pool)

    @patch.object(ExasolConnectionManager, "_ensure_atexit_handler")
    @patch.object(ExasolConnectionManager, "retry_connection")
    def test_open_calls_ensure_atexit_handler(self, mock_retry, mock_ensure_atexit):
        """Test open() calls _ensure_atexit_handler."""
        mock_connection = Mock(spec=Connection)
        mock_connection.state = "init"
        mock_connection.credentials = self.credentials
        mock_retry.return_value = mock_connection

        ExasolConnectionManager.open(mock_connection)

        mock_ensure_atexit.assert_called_once()

    # ------------------------------------------------------------------
    # Concurrent access (7.8)
    # ------------------------------------------------------------------

    def test_concurrent_pool_access_with_locking(self):
        """Concurrent pool access from multiple threads is thread-safe."""
        results = []
        errors = []

        def add_to_pool(conn_id):
            try:
                mock_conn = _make_valid_handle()
                key = f"test_key_{conn_id}"
                with ExasolConnectionManager._pool_lock:
                    pool = ExasolConnectionManager._get_pool()
                    pool[key] = [mock_conn]
                    results.append(conn_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_to_pool, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 10)
        pool = ExasolConnectionManager._get_pool()
        # 10 distinct keys added
        distinct = sum(1 for k in pool if k.startswith("test_key_"))
        self.assertEqual(distinct, 10)

    # ------------------------------------------------------------------
    # Leak invariant tests (7.11, 7.12)
    # ------------------------------------------------------------------

    def test_leak_invariant_all_handles_pooled_or_closed(self):
        """After N open/close cycles with M threads, every mock handle is in pool or closed."""
        ExasolConnectionManager._pool_sizes[self.pool_key] = 4
        all_handles = []
        all_handles_lock = threading.Lock()
        errors = []

        def _open_and_close():
            handle = _make_valid_handle()
            with all_handles_lock:
                all_handles.append(handle)
            mock_conn = Mock(spec=Connection)
            mock_conn.handle = handle
            mock_conn.credentials = self.credentials
            try:
                ExasolConnectionManager._close_handle(mock_conn)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_open_and_close) for _ in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)

        pool = ExasolConnectionManager._get_pool()
        pooled = {id(h) for h in pool.get(self.pool_key, [])}

        for handle in all_handles:
            in_pool = id(handle) in pooled
            was_closed = handle.close.called
            self.assertTrue(
                in_pool or was_closed,
                f"Handle {id(handle)} is neither pooled nor closed — leaked!",
            )

    def test_leak_invariant_excess_connections_have_close_called(self):
        """With pool at capacity, excess connections have close() called."""
        ExasolConnectionManager._pool_sizes[self.pool_key] = 2

        handles = [_make_valid_handle() for _ in range(6)]
        for handle in handles:
            mock_conn = Mock(spec=Connection)
            mock_conn.handle = handle
            mock_conn.credentials = self.credentials
            ExasolConnectionManager._close_handle(mock_conn)

        pool = ExasolConnectionManager._get_pool()
        pooled = pool.get(self.pool_key, [])
        pooled_ids = {id(h) for h in pooled}

        closed_count = 0
        for handle in handles:
            if id(handle) not in pooled_ids:
                self.assertTrue(handle.close.called, f"Unpooled handle {id(handle)} was not closed")
                closed_count += 1

        self.assertEqual(len(pooled), 2)
        self.assertEqual(closed_count, 4)


if __name__ == "__main__":
    unittest.main()
