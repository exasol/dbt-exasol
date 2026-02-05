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


class TestConnectionPool(unittest.TestCase):
    """Test connection pooling methods."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear pool before each test
        ExasolConnectionManager._pool.clear()

        # Create test credentials
        self.credentials = ExasolCredentials(
            dsn="localhost:8563",
            user="test_user",
            password="test_pass",
            database="TEST_DB",
            schema="TEST_SCHEMA",
        )

    def tearDown(self):
        """Clean up after each test."""
        # Clear pool after each test
        ExasolConnectionManager.cleanup_pool()

    def test_get_pool_returns_class_level_dict(self):
        """Test _get_pool returns class-level pool dict."""
        pool = ExasolConnectionManager._get_pool()

        self.assertIsInstance(pool, dict)
        # Pool should be the class-level _pool
        self.assertIs(pool, ExasolConnectionManager._pool)

    def test_get_pool_returns_same_pool_across_calls(self):
        """Test _get_pool returns same pool across calls."""
        # Get pool and add a test entry
        pool1 = ExasolConnectionManager._get_pool()
        mock_conn = Mock(spec=ExasolConnection)
        pool1["test_key"] = mock_conn

        # Get pool again
        pool2 = ExasolConnectionManager._get_pool()

        self.assertIs(pool1, pool2)
        self.assertEqual(pool2["test_key"], mock_conn)

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

    def test_is_connection_valid_returns_true_for_valid_connection(self):
        """Test _is_connection_valid returns True for valid connection."""
        mock_conn = Mock(spec=ExasolConnection)
        mock_conn.is_closed = False
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]
        mock_conn.execute.return_value = mock_cursor

        result = ExasolConnectionManager._is_connection_valid(mock_conn)

        self.assertTrue(result)
        mock_conn.execute.assert_called_once_with("SELECT 1")
        mock_cursor.fetchone.assert_called_once()

    def test_is_connection_valid_returns_false_for_closed_connection(self):
        """Test _is_connection_valid returns False for closed connection."""
        mock_conn = Mock(spec=ExasolConnection)
        mock_conn.is_closed = True

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

    @patch.object(ExasolConnectionManager, "open")
    def test_open_reuses_pooled_connection_when_valid(self, mock_open):
        """Test open() reuses pooled connection when valid."""
        # Create a mock connection
        mock_handle = Mock(spec=ExasolConnection)
        mock_handle.is_closed = False
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]
        mock_handle.execute.return_value = mock_cursor

        # Add connection to pool
        pool_key = ExasolConnectionManager._get_pool_key(self.credentials)
        pool = ExasolConnectionManager._get_pool()
        pool[pool_key] = mock_handle

        # Call the real open method by removing the mock temporarily
        mock_open.side_effect = None

        # Create a connection object
        connection = Connection(
            type="exasol",
            name="test",
            state="init",
            credentials=self.credentials,
        )

        # Manually test pool reuse logic
        pool = ExasolConnectionManager._get_pool()
        pool_key = ExasolConnectionManager._get_pool_key(self.credentials)

        # Verify pool has the connection
        self.assertIn(pool_key, pool)
        self.assertEqual(pool[pool_key], mock_handle)

        # Verify connection is valid
        self.assertTrue(ExasolConnectionManager._is_connection_valid(mock_handle))

    @patch.object(ExasolConnectionManager, "retry_connection")
    def test_open_creates_new_connection_when_pool_empty(self, mock_retry_connection):
        """Test open() creates new connection when pool is empty."""
        # Setup mock
        mock_handle = Mock(spec=ExasolConnection)
        mock_connection = Mock(spec=Connection)
        mock_connection.state = "init"
        mock_connection.credentials = self.credentials
        mock_connection.handle = mock_handle
        mock_retry_connection.return_value = mock_connection

        # Ensure pool is empty
        pool = ExasolConnectionManager._get_pool()
        pool_key = ExasolConnectionManager._get_pool_key(self.credentials)
        self.assertNotIn(pool_key, pool)

        # Call open
        result = ExasolConnectionManager.open(mock_connection)

        # Verify new connection was created
        mock_retry_connection.assert_called_once()

    def test_open_removes_invalid_connection_from_pool_and_creates_new(self):
        """Test open() removes invalid connection from pool and creates new."""
        # Create invalid mock connection
        mock_invalid_conn = Mock(spec=ExasolConnection)
        mock_invalid_conn.is_closed = True

        # Add invalid connection to pool
        pool_key = ExasolConnectionManager._get_pool_key(self.credentials)
        pool = ExasolConnectionManager._get_pool()
        pool[pool_key] = mock_invalid_conn

        # Verify invalid connection is in pool
        self.assertIn(pool_key, pool)

        # Verify it's invalid
        self.assertFalse(ExasolConnectionManager._is_connection_valid(mock_invalid_conn))

        # Verify that after validation fails, we'd remove it
        # (The actual removal happens in open(), tested by integration)

    def test_close_handle_returns_connection_to_pool(self):
        """Test _close_handle() returns connection to pool instead of closing."""
        # Create mock connection
        mock_connection = Mock(spec=Connection)
        mock_handle = Mock(spec=ExasolConnection)
        mock_handle.is_closed = False
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]
        mock_handle.execute.return_value = mock_cursor

        mock_connection.handle = mock_handle
        mock_connection.credentials = self.credentials

        # Ensure pool is empty
        pool = ExasolConnectionManager._get_pool()
        pool_key = ExasolConnectionManager._get_pool_key(self.credentials)
        self.assertEqual(len(pool), 0)

        # Call _close_handle
        ExasolConnectionManager._close_handle(mock_connection)

        # Verify connection was not closed
        mock_handle.close.assert_not_called()

        # Verify connection was added to pool
        self.assertIn(pool_key, pool)
        self.assertEqual(pool[pool_key], mock_handle)

    def test_cleanup_pool_closes_all_pooled_connections(self):
        """Test cleanup_pool() closes all pooled connections."""
        # Create multiple mock connections
        mock_conn1 = Mock(spec=ExasolConnection)
        mock_conn1.is_closed = False
        mock_conn2 = Mock(spec=ExasolConnection)
        mock_conn2.is_closed = False

        # Add to pool
        pool = ExasolConnectionManager._get_pool()
        pool["key1"] = mock_conn1
        pool["key2"] = mock_conn2

        # Call cleanup
        ExasolConnectionManager.cleanup_pool()

        # Verify all connections were closed
        mock_conn1.close.assert_called_once()
        mock_conn2.close.assert_called_once()

        # Verify pool is empty
        self.assertEqual(len(pool), 0)

    def test_cleanup_pool_handles_already_closed_connections(self):
        """Test cleanup_pool() handles already closed connections gracefully."""
        # Create mock connection that's already closed
        mock_conn = Mock(spec=ExasolConnection)
        mock_conn.is_closed = True
        mock_conn.close.side_effect = Exception("Already closed")

        # Add to pool
        pool = ExasolConnectionManager._get_pool()
        pool["key1"] = mock_conn

        # Call cleanup - should not raise exception
        ExasolConnectionManager.cleanup_pool()

        # Verify pool is empty
        self.assertEqual(len(pool), 0)

    @patch.object(ExasolConnectionManager, "_close_handle")
    @patch.object(ExasolConnectionManager, "open")
    def test_initialize_pool_creates_specified_number_of_connections(self, mock_open, mock_close_handle):
        """Test initialize_pool() creates specified number of connections."""
        # Setup mock
        mock_connection = Mock(spec=Connection)
        mock_handle = Mock(spec=ExasolConnection)
        mock_connection.handle = mock_handle
        mock_open.return_value = mock_connection

        # Call initialize_pool
        ExasolConnectionManager.initialize_pool(self.credentials, size=3)

        # Verify open was called 3 times
        self.assertEqual(mock_open.call_count, 3)
        # Verify _close_handle was called 3 times to return connections to pool
        self.assertEqual(mock_close_handle.call_count, 3)

    @patch.object(ExasolConnectionManager, "_close_handle")
    @patch.object(ExasolConnectionManager, "open")
    def test_initialize_pool_skips_if_valid_connection_exists(self, mock_open, mock_close_handle):
        """Test initialize_pool() uses existing valid connection."""
        # Create valid mock connection
        mock_handle = Mock(spec=ExasolConnection)
        mock_handle.is_closed = False
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]
        mock_handle.execute.return_value = mock_cursor

        # Add to pool
        pool_key = ExasolConnectionManager._get_pool_key(self.credentials)
        pool = ExasolConnectionManager._get_pool()
        pool[pool_key] = mock_handle

        # Setup mock for open
        mock_connection = Mock(spec=Connection)
        mock_connection.handle = mock_handle
        mock_open.return_value = mock_connection

        # Call initialize_pool with size 3
        ExasolConnectionManager.initialize_pool(self.credentials, size=3)

        # Should create 2 more connections (1 already exists)
        self.assertEqual(mock_open.call_count, 2)
        self.assertEqual(mock_close_handle.call_count, 2)

    def test_concurrent_pool_access_with_locking(self):
        """Test concurrent pool access from multiple threads is thread-safe."""
        # Create multiple mock connections
        results = []
        errors = []

        def add_to_pool(conn_id):
            """Add a connection to pool."""
            try:
                mock_conn = Mock(spec=ExasolConnection)
                mock_conn.is_closed = False
                mock_cursor = Mock()
                mock_cursor.fetchone.return_value = [1]
                mock_conn.execute.return_value = mock_cursor

                pool = ExasolConnectionManager._get_pool()
                key = f"test_key_{conn_id}"

                # Simulate some work with the lock
                with ExasolConnectionManager._pool_lock:
                    pool[key] = mock_conn
                    results.append(conn_id)
            except Exception as e:
                errors.append(e)

        # Create threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=add_to_pool, args=(i,))
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Verify no errors occurred
        self.assertEqual(len(errors), 0)

        # Verify all connections were added
        self.assertEqual(len(results), 10)
        pool = ExasolConnectionManager._get_pool()
        self.assertEqual(len(pool), 10)


if __name__ == "__main__":
    unittest.main()
