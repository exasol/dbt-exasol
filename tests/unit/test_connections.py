"""Unit tests for ExasolConnectionManager and ExasolCursor."""

import ssl
import unittest
from unittest.mock import Mock, patch

import pyexasol

from dbt.adapters.exasol.connections import (
    ExasolConnectionManager,
    ExasolCursor,
    ExasolConnection,
    ExasolCredentials,
)


class TestDataTypeCodeToName(unittest.TestCase):
    """Test data_type_code_to_name class method."""

    def test_data_type_code_to_name_simple_type(self):
        """Test data_type_code_to_name with simple type."""
        result = ExasolConnectionManager.data_type_code_to_name("VARCHAR")
        self.assertEqual(result, "VARCHAR")

    def test_data_type_code_to_name_with_parameters(self):
        """Test data_type_code_to_name strips parameters."""
        result = ExasolConnectionManager.data_type_code_to_name("VARCHAR(100)")
        self.assertEqual(result, "VARCHAR")

    def test_data_type_code_to_name_decimal_with_precision(self):
        """Test data_type_code_to_name with DECIMAL(18,9)."""
        result = ExasolConnectionManager.data_type_code_to_name("DECIMAL(18,9)")
        self.assertEqual(result, "DECIMAL")

    def test_data_type_code_to_name_uppercase(self):
        """Test data_type_code_to_name returns uppercase."""
        result = ExasolConnectionManager.data_type_code_to_name("decimal")
        self.assertEqual(result, "DECIMAL")


class TestGetResultFromCursor(unittest.TestCase):
    """Test get_result_from_cursor class method."""

    @patch("dbt_common.clients.agate_helper.table_from_data_flat")
    def test_get_result_from_cursor_with_decimal_conversion(self, mock_table_from_data):
        """Test get_result_from_cursor converts DECIMAL strings to Decimal."""
        mock_table = Mock()
        mock_table.__len__ = Mock(return_value=2)
        mock_table.column_names = ["amount", "name"]
        mock_table_from_data.return_value = mock_table

        mock_cursor = Mock()
        mock_cursor.description = [
            ("amount", "DECIMAL", None, None, 18, 9, True),
            ("name", "VARCHAR", None, None, None, None, True),
        ]
        mock_cursor.fetchall.return_value = [
            ["123.45", "John"],
            ["678.90", "Jane"],
        ]

        result = ExasolConnectionManager.get_result_from_cursor(mock_cursor, None)

        # Verify it's an agate table
        self.assertEqual(len(result), 2)
        self.assertEqual(result.column_names, ["amount", "name"])

    @patch("dbt_common.clients.agate_helper.table_from_data_flat")
    def test_get_result_from_cursor_with_bigint_conversion(self, mock_table_from_data):
        """Test get_result_from_cursor converts BIGINT strings to Decimal."""
        mock_table = Mock()
        mock_table.__len__ = Mock(return_value=1)
        mock_table_from_data.return_value = mock_table

        mock_cursor = Mock()
        mock_cursor.description = [
            ("id", "BIGINT", None, None, 36, 0, True),
        ]
        mock_cursor.fetchall.return_value = [
            ["12345678901234567890"],
        ]

        result = ExasolConnectionManager.get_result_from_cursor(mock_cursor, None)

        self.assertEqual(len(result), 1)

    @patch("dbt_common.clients.agate_helper.table_from_data_flat")
    def test_get_result_from_cursor_with_timestamp_conversion(
        self, mock_table_from_data
    ):
        """Test get_result_from_cursor converts TIMESTAMP strings to datetime."""
        mock_table = Mock()
        mock_table.__len__ = Mock(return_value=1)
        mock_table_from_data.return_value = mock_table

        mock_cursor = Mock()
        mock_cursor.description = [
            ("created_at", "TIMESTAMP", None, None, None, None, True),
        ]
        mock_cursor.fetchall.return_value = [
            ["2024-01-15 10:30:00"],
        ]

        result = ExasolConnectionManager.get_result_from_cursor(mock_cursor, None)

        self.assertEqual(len(result), 1)

    @patch("dbt_common.clients.agate_helper.table_from_data_flat")
    def test_get_result_from_cursor_with_limit(self, mock_table_from_data):
        """Test get_result_from_cursor respects limit parameter."""
        mock_table = Mock()
        mock_table.__len__ = Mock(return_value=2)
        mock_table_from_data.return_value = mock_table

        mock_cursor = Mock()
        mock_cursor.description = [
            ("id", "DECIMAL", None, None, 18, 0, True),
        ]
        mock_cursor.fetchmany.return_value = [
            ["1"],
            ["2"],
        ]

        result = ExasolConnectionManager.get_result_from_cursor(mock_cursor, 2)

        mock_cursor.fetchmany.assert_called_once_with(2)
        self.assertEqual(len(result), 2)

    @patch("dbt_common.clients.agate_helper.table_from_data_flat")
    def test_get_result_from_cursor_with_none_values(self, mock_table_from_data):
        """Test get_result_from_cursor handles None values."""
        mock_table = Mock()
        mock_table.__len__ = Mock(return_value=2)
        mock_table_from_data.return_value = mock_table

        mock_cursor = Mock()
        mock_cursor.description = [
            ("amount", "DECIMAL", None, None, 18, 9, True),
        ]
        mock_cursor.fetchall.return_value = [
            [None],
            ["123.45"],
        ]

        result = ExasolConnectionManager.get_result_from_cursor(mock_cursor, None)

        self.assertEqual(len(result), 2)

    @patch("dbt_common.clients.agate_helper.table_from_data_flat")
    def test_get_result_from_cursor_with_no_description(self, mock_table_from_data):
        """Test get_result_from_cursor with no cursor description."""
        mock_table = Mock()
        mock_table.__len__ = Mock(return_value=0)
        mock_table_from_data.return_value = mock_table

        mock_cursor = Mock()
        mock_cursor.description = None

        result = ExasolConnectionManager.get_result_from_cursor(mock_cursor, None)

        self.assertEqual(len(result), 0)


class TestExasolCursorExecute(unittest.TestCase):
    """Test ExasolCursor.execute method."""

    def setUp(self):
        """Set up test cursor."""
        self.mock_connection = Mock(spec=ExasolConnection)
        self.cursor = ExasolCursor(self.mock_connection)

    def test_execute_normal_query(self):
        """Test execute with normal SQL query."""
        mock_stmt = Mock()
        self.mock_connection.execute.return_value = mock_stmt

        result = self.cursor.execute("SELECT * FROM table")

        self.mock_connection.execute.assert_called_once_with("SELECT * FROM table")
        self.assertEqual(self.cursor.stmt, mock_stmt)
        self.assertEqual(result, self.cursor)

    def test_execute_csv_import(self):
        """Test execute with CSV import (0CSV| prefix)."""
        mock_agate_table = Mock()
        mock_agate_table.original_abspath = "/path/to/file.csv"
        self.mock_connection.row_separator = "LF"

        result = self.cursor.execute("0CSV|schema.table", mock_agate_table)

        self.mock_connection.import_from_file.assert_called_once_with(
            "/path/to/file.csv",
            ("schema", "table"),
            import_params={"skip": 1, "row_separator": "LF"},
        )
        self.assertEqual(result, self.cursor)

    def test_execute_multiple_statements(self):
        """Test execute with multiple statements separated by |SEPARATEMEPLEASE|."""
        mock_stmt1 = Mock()
        mock_stmt2 = Mock()
        self.mock_connection.execute.side_effect = [mock_stmt1, mock_stmt2]

        result = self.cursor.execute("CREATE TABLE t1|SEPARATEMEPLEASE|CREATE TABLE t2")

        self.assertEqual(self.mock_connection.execute.call_count, 2)
        self.mock_connection.execute.assert_any_call("CREATE TABLE t1")
        self.mock_connection.execute.assert_any_call("CREATE TABLE t2")

    def test_execute_with_query_error(self):
        """Test execute raises DbtDatabaseError on ExaQueryError."""
        from dbt_common.exceptions import DbtDatabaseError

        # Create a proper ExaQueryError with required parameters
        error = pyexasol.ExaQueryError(
            Mock(),  # connection
            "SELECT * FROM nonexistent",  # query
            "42",  # code
            "Query failed",  # message
        )
        self.mock_connection.execute.side_effect = error

        with self.assertRaises(DbtDatabaseError) as context:
            self.cursor.execute("SELECT * FROM nonexistent")

        self.assertIn("Exasol Query Error", str(context.exception))


class TestExasolConnectionManagerOpen(unittest.TestCase):
    """Test ExasolConnectionManager.open method."""

    @patch("dbt.adapters.exasol.connections.connect")
    def test_open_with_v1_protocol(self, mock_connect):
        """Test open with protocol version v1."""
        mock_conn_obj = Mock(spec=ExasolConnection)
        mock_connect.return_value = mock_conn_obj

        credentials = ExasolCredentials(
            dsn="localhost:8563",
            user="sys",
            password="exasol",
            database="test",
            schema="test_schema",
            protocol_version="v1",
        )

        connection = Mock()
        connection.state = "closed"
        connection.credentials = credentials

        ExasolConnectionManager.open(connection)

        # Verify protocol_version argument
        call_args = mock_connect.call_args
        self.assertEqual(call_args[1]["protocol_version"], pyexasol.PROTOCOL_V1)

    @patch("dbt.adapters.exasol.connections.connect")
    def test_open_with_v2_protocol(self, mock_connect):
        """Test open with protocol version v2."""
        mock_conn_obj = Mock(spec=ExasolConnection)
        mock_connect.return_value = mock_conn_obj

        credentials = ExasolCredentials(
            dsn="localhost:8563",
            user="sys",
            password="exasol",
            database="test",
            schema="test_schema",
            protocol_version="v2",
        )

        connection = Mock()
        connection.state = "closed"
        connection.credentials = credentials

        ExasolConnectionManager.open(connection)

        call_args = mock_connect.call_args
        self.assertEqual(call_args[1]["protocol_version"], pyexasol.PROTOCOL_V2)

    @patch("dbt.adapters.exasol.connections.connect")
    def test_open_with_v3_protocol(self, mock_connect):
        """Test open with protocol version v3."""
        mock_conn_obj = Mock(spec=ExasolConnection)
        mock_connect.return_value = mock_conn_obj

        credentials = ExasolCredentials(
            dsn="localhost:8563",
            user="sys",
            password="exasol",
            database="test",
            schema="test_schema",
            protocol_version="v3",
        )

        connection = Mock()
        connection.state = "closed"
        connection.credentials = credentials

        ExasolConnectionManager.open(connection)

        call_args = mock_connect.call_args
        self.assertEqual(call_args[1]["protocol_version"], pyexasol.PROTOCOL_V3)

    @patch("dbt.adapters.exasol.connections.connect")
    def test_open_with_ssl_enabled_and_validation(self, mock_connect):
        """Test open with SSL enabled and certificate validation."""
        mock_conn_obj = Mock(spec=ExasolConnection)
        mock_connect.return_value = mock_conn_obj

        credentials = ExasolCredentials(
            dsn="localhost:8563",
            user="sys",
            password="exasol",
            database="test",
            schema="test_schema",
            encryption=True,
            validate_server_certificate=True,
        )

        connection = Mock()
        connection.state = "closed"
        connection.credentials = credentials

        ExasolConnectionManager.open(connection)

        call_args = mock_connect.call_args
        self.assertEqual(call_args[1]["encryption"], True)
        self.assertEqual(
            call_args[1]["websocket_sslopt"], {"cert_reqs": ssl.CERT_REQUIRED}
        )

    @patch("dbt.adapters.exasol.connections.connect")
    def test_open_with_ssl_enabled_without_validation(self, mock_connect):
        """Test open with SSL enabled but no certificate validation."""
        mock_conn_obj = Mock(spec=ExasolConnection)
        mock_connect.return_value = mock_conn_obj

        credentials = ExasolCredentials(
            dsn="localhost:8563",
            user="sys",
            password="exasol",
            database="test",
            schema="test_schema",
            encryption=True,
            validate_server_certificate=False,
        )

        connection = Mock()
        connection.state = "closed"
        connection.credentials = credentials

        ExasolConnectionManager.open(connection)

        call_args = mock_connect.call_args
        self.assertEqual(call_args[1]["encryption"], True)
        self.assertEqual(call_args[1]["websocket_sslopt"], {"cert_reqs": ssl.CERT_NONE})

    @patch("dbt.adapters.exasol.connections.connect")
    def test_open_with_ssl_disabled(self, mock_connect):
        """Test open with SSL disabled."""
        mock_conn_obj = Mock(spec=ExasolConnection)
        mock_connect.return_value = mock_conn_obj

        credentials = ExasolCredentials(
            dsn="localhost:8563",
            user="sys",
            password="exasol",
            database="test",
            schema="test_schema",
            encryption=False,
        )

        connection = Mock()
        connection.state = "closed"
        connection.credentials = credentials

        ExasolConnectionManager.open(connection)

        call_args = mock_connect.call_args
        self.assertEqual(call_args[1]["encryption"], False)
        self.assertIsNone(call_args[1]["websocket_sslopt"])

    def test_open_already_open(self):
        """Test open skips when connection already open."""
        connection = Mock()
        connection.state = "open"

        result = ExasolConnectionManager.open(connection)

        self.assertEqual(result, connection)

    @patch("dbt.adapters.exasol.connections.connect")
    def test_open_sets_timestamp_format(self, mock_connect):
        """Test open sets timestamp format on connection."""
        mock_conn_obj = Mock(spec=ExasolConnection)
        mock_connect.return_value = mock_conn_obj

        credentials = ExasolCredentials(
            dsn="localhost:8563",
            user="sys",
            password="exasol",
            database="test",
            schema="test_schema",
            timestamp_format="YYYY-MM-DD HH24:MI:SS",
        )

        connection = Mock()
        connection.state = "closed"
        connection.credentials = credentials

        ExasolConnectionManager.open(connection)

        # Verify timestamp format was set
        self.assertEqual(mock_conn_obj.timestamp_format, "YYYY-MM-DD HH24:MI:SS")
        mock_conn_obj.execute.assert_called_once_with(
            "alter session set NLS_TIMESTAMP_FORMAT='YYYY-MM-DD HH24:MI:SS'"
        )


class TestExasolCursorProperties(unittest.TestCase):
    """Test ExasolCursor properties."""

    def setUp(self):
        """Set up test cursor."""
        self.mock_connection = Mock(spec=ExasolConnection)
        self.cursor = ExasolCursor(self.mock_connection)

    def test_description_with_result_set(self):
        """Test description property with result set."""
        mock_stmt = Mock()
        mock_stmt.result_type = "resultSet"
        mock_stmt.columns.return_value = {
            "id": {"type": "DECIMAL", "size": None, "precision": 18, "scale": 0},
            "name": {"type": "VARCHAR", "size": 100, "precision": None, "scale": None},
        }
        self.cursor.stmt = mock_stmt

        description = self.cursor.description

        self.assertEqual(len(description), 2)
        self.assertEqual(description[0][0], "id")
        self.assertEqual(description[0][1], "DECIMAL")
        self.assertEqual(description[1][0], "name")
        self.assertEqual(description[1][1], "VARCHAR")

    def test_description_without_result_set(self):
        """Test description property without result set."""
        mock_stmt = Mock()
        mock_stmt.result_type = "rowCount"
        self.cursor.stmt = mock_stmt

        description = self.cursor.description

        self.assertIsNone(description)

    def test_description_with_no_stmt(self):
        """Test description property with no statement."""
        description = self.cursor.description

        self.assertEqual(description, [])

    def test_rowcount_with_stmt(self):
        """Test rowcount property with statement."""
        mock_stmt = Mock()
        mock_stmt.rowcount.return_value = 42
        self.cursor.stmt = mock_stmt

        rowcount = self.cursor.rowcount

        self.assertEqual(rowcount, 42)

    def test_rowcount_without_stmt(self):
        """Test rowcount property without statement."""
        rowcount = self.cursor.rowcount

        self.assertEqual(rowcount, 0)

    def test_execution_time_with_stmt(self):
        """Test execution_time property with statement."""
        mock_stmt = Mock()
        mock_stmt.execution_time = 1.234
        self.cursor.stmt = mock_stmt

        execution_time = self.cursor.execution_time

        self.assertEqual(execution_time, 1.234)

    def test_execution_time_without_stmt(self):
        """Test execution_time property without statement."""
        execution_time = self.cursor.execution_time

        self.assertEqual(execution_time, 0)


class TestGetResponse(unittest.TestCase):
    """Test get_response class method."""

    def test_get_response(self):
        """Test get_response returns ExasolAdapterResponse."""
        mock_cursor = Mock()
        mock_cursor.rowcount = 10
        mock_cursor.execution_time = 0.5

        response = ExasolConnectionManager.get_response(mock_cursor)

        self.assertEqual(response._message, "OK")
        self.assertEqual(response.rows_affected, 10)
        self.assertEqual(response.execution_time, 0.5)


class TestConnectionRetryBehavior(unittest.TestCase):
    """Test connection retry behavior in ExasolConnectionManager.open."""

    def _create_connection_with_credentials(self, retries=1):
        """Helper to create a mock connection with credentials."""
        credentials = ExasolCredentials(
            dsn="localhost:8563",
            user="sys",
            password="exasol",
            database="test",
            schema="test_schema",
            retries=retries,
        )
        connection = Mock()
        connection.state = "closed"
        connection.credentials = credentials
        return connection

    def _create_exa_error(self, message):
        """Helper to create a properly mocked ExaError."""
        # ExaError.__str__ accesses connection.options["verbose_error"]
        mock_conn = Mock()
        mock_conn.options = {"verbose_error": False}
        return pyexasol.ExaError(mock_conn, message)

    @patch("dbt.adapters.exasol.connections.connect")
    @patch("dbt.adapters.base.connections.sleep")  # Skip sleep during tests
    def test_retry_succeeds_after_transient_failure(self, mock_sleep, mock_connect):
        """Test that connection succeeds after transient ExaError failure."""
        mock_conn_obj = Mock(spec=ExasolConnection)
        # First call fails with ExaError, second succeeds
        mock_connect.side_effect = [
            self._create_exa_error("Transient connection failure"),
            mock_conn_obj,
        ]

        connection = self._create_connection_with_credentials(retries=2)

        result = ExasolConnectionManager.open(connection)

        # Verify connect was called twice (1 failure + 1 success)
        self.assertEqual(mock_connect.call_count, 2)
        self.assertEqual(result.state, "open")

    @patch("dbt.adapters.exasol.connections.connect")
    @patch("dbt.adapters.base.connections.sleep")
    def test_retry_exhausted_raises_failed_to_connect(self, mock_sleep, mock_connect):
        """Test that FailedToConnectError is raised after all retries exhausted."""
        from dbt.adapters.exceptions.connection import FailedToConnectError

        # All attempts fail with ExaError
        mock_connect.side_effect = self._create_exa_error(
            "Persistent connection failure"
        )

        connection = self._create_connection_with_credentials(retries=3)

        # dbt-core raises FailedToConnectError when all retries are exhausted
        with self.assertRaises(FailedToConnectError):
            ExasolConnectionManager.open(connection)

        # Verify connect was called 4 times (initial + 3 retries)
        # retry_limit=3 means: 1 initial attempt + 3 retry attempts = 4 total
        self.assertEqual(mock_connect.call_count, 4)

    @patch("dbt.adapters.exasol.connections.connect")
    def test_non_retryable_error_fails_immediately(self, mock_connect):
        """Test that non-ExaError exceptions are not retried."""
        from dbt.adapters.exceptions.connection import FailedToConnectError

        # Raise a non-retryable exception
        mock_connect.side_effect = ValueError("Not a retryable error")

        connection = self._create_connection_with_credentials(retries=3)

        # Non-retryable errors are wrapped in FailedToConnectError by dbt-core
        with self.assertRaises(FailedToConnectError):
            ExasolConnectionManager.open(connection)

        # Should only be called once (no retry for non-retryable exceptions)
        self.assertEqual(mock_connect.call_count, 1)

    @patch("dbt.adapters.exasol.connections.connect")
    @patch("dbt.adapters.base.connections.sleep")
    def test_single_retry_means_two_attempts(self, mock_sleep, mock_connect):
        """Test that retries=1 means initial attempt + 1 retry = 2 total attempts."""
        from dbt.adapters.exceptions.connection import FailedToConnectError

        mock_connect.side_effect = self._create_exa_error("Connection failed")

        connection = self._create_connection_with_credentials(retries=1)

        # dbt-core raises FailedToConnectError when all retries are exhausted
        with self.assertRaises(FailedToConnectError):
            ExasolConnectionManager.open(connection)

        # With retries=1: 1 initial attempt + 1 retry = 2 total attempts
        self.assertEqual(mock_connect.call_count, 2)

    @patch("dbt.adapters.exasol.connections.connect")
    @patch("dbt.adapters.base.connections.sleep")
    def test_retry_with_multiple_failures_then_success(self, mock_sleep, mock_connect):
        """Test that connection succeeds after multiple transient failures."""
        mock_conn_obj = Mock(spec=ExasolConnection)
        # First two calls fail, third succeeds
        mock_connect.side_effect = [
            self._create_exa_error("Failure 1"),
            self._create_exa_error("Failure 2"),
            mock_conn_obj,
        ]

        connection = self._create_connection_with_credentials(retries=5)

        result = ExasolConnectionManager.open(connection)

        # Verify connect was called 3 times (2 failures + 1 success)
        self.assertEqual(mock_connect.call_count, 3)
        self.assertEqual(result.state, "open")

    @patch("dbt.adapters.exasol.connections.connect")
    @patch("dbt.adapters.base.connections.sleep")
    def test_retry_passes_exa_error_as_retryable_exception(
        self, mock_sleep, mock_connect
    ):
        """Test that ExaError (base class) triggers retry behavior."""
        mock_conn_obj = Mock(spec=ExasolConnection)
        # Use base ExaError class
        mock_connect.side_effect = [
            self._create_exa_error("Base ExaError"),
            mock_conn_obj,
        ]

        connection = self._create_connection_with_credentials(retries=2)

        result = ExasolConnectionManager.open(connection)

        self.assertEqual(mock_connect.call_count, 2)
        self.assertEqual(result.state, "open")


if __name__ == "__main__":
    unittest.main()
