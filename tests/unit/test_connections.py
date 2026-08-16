"""Unit tests for ExasolConnectionManager and ExasolCursor."""

import ssl
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import (
    Mock,
    patch,
)

import pyexasol
from dbt_common.exceptions import DbtRuntimeError

from dbt.adapters.exasol.connections import (
    ROW_SEPARATOR_DEFAULT,
    ExasolConnection,
    ExasolConnectionManager,
    ExasolCredentials,
    ExasolCursor,
    ProtocolVersionType,
    _detect_row_separator,
    _split_relation_path,
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
    def test_get_result_from_cursor_with_timestamp_conversion(self, mock_table_from_data):
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


class TestSplitRelationPath(unittest.TestCase):
    """Test _split_relation_path, which parses the 0CSV| seed target (issue #223)."""

    def test_unquoted_components_are_upper_cased(self):
        """Exasol folds unquoted identifiers to upper case; the seed target must match."""
        self.assertEqual(_split_relation_path("my_schema.my_seed"), ("MY_SCHEMA", "MY_SEED"))

    def test_quoted_components_keep_exact_case(self):
        """Quoted identifiers are case-sensitive and must be passed through verbatim."""
        self.assertEqual(_split_relation_path('"my_schema"."my_seed"'), ("my_schema", "my_seed"))

    def test_mixed_quoting(self):
        """Only the quoted component keeps its case (quoting: {identifier: true})."""
        self.assertEqual(_split_relation_path('MY_SCHEMA."my_seed"'), ("MY_SCHEMA", "my_seed"))

    def test_escaped_inner_quote(self):
        """A doubled quote inside a quoted identifier collapses to one quote."""
        self.assertEqual(_split_relation_path('"a""b"."c"'), ('a"b', "c"))

    def test_dot_inside_quoted_component_is_not_a_separator(self):
        """A dot inside quotes belongs to the identifier, not the path."""
        self.assertEqual(_split_relation_path('"my.schema"."t"'), ("my.schema", "t"))

    def test_malformed_paths_raise(self):
        """Anything that is not exactly schema.identifier is a hard error."""
        for bad in ("justone", '"unterminated.x', "a.b.c", ".x", "x."):
            with self.subTest(path=bad), self.assertRaises(DbtRuntimeError):
                _split_relation_path(bad)

    def test_partially_quoted_components_raise(self):
        """A component must be fully quoted or fully unquoted, not a mix."""
        for bad in ('ab"cd".x', 'x."y"z', '"a"b.c', '"a"b"c"'):
            with self.subTest(path=bad), self.assertRaises(DbtRuntimeError):
                _split_relation_path(bad)


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
        """Test execute with CSV import (0CSV| prefix).

        Unquoted components are upper-cased to match Exasol's folding of
        unquoted identifiers, so the IMPORT target resolves to the object the
        seed's CREATE TABLE actually created.
        """
        mock_agate_table = Mock()
        mock_agate_table.original_abspath = "/path/to/file.csv"
        self.mock_connection.row_separator = "LF"

        result = self.cursor.execute("0CSV|schema.table", mock_agate_table)

        self.mock_connection.import_from_file.assert_called_once_with(
            "/path/to/file.csv",
            ("SCHEMA", "TABLE"),
            import_params={"skip": 1, "row_separator": "LF"},
        )
        self.assertEqual(result, self.cursor)

    def test_execute_csv_import_quoted_relation(self):
        """Quoted components keep their exact case (issue #223)."""
        mock_agate_table = Mock()
        mock_agate_table.original_abspath = "/path/to/file.csv"
        self.mock_connection.row_separator = "LF"

        self.cursor.execute('0CSV|"my_schema"."my_seed"', mock_agate_table)

        self.mock_connection.import_from_file.assert_called_once_with(
            "/path/to/file.csv",
            ("my_schema", "my_seed"),
            import_params={"skip": 1, "row_separator": "LF"},
        )

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
        self.assertTrue(call_args[1]["encryption"])
        self.assertEqual(call_args[1]["websocket_sslopt"], {"cert_reqs": ssl.CERT_REQUIRED})

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
        self.assertTrue(call_args[1]["encryption"])
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
        self.assertFalse(call_args[1]["encryption"])
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
        mock_conn_obj.execute.assert_called_once_with("alter session set NLS_TIMESTAMP_FORMAT='YYYY-MM-DD HH24:MI:SS'")


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
        mock_connect.side_effect = self._create_exa_error("Persistent connection failure")

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
    def test_retry_passes_exa_error_as_retryable_exception(self, mock_sleep, mock_connect):
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


class TestStrEnumBackport(unittest.TestCase):
    """Test StrEnum backport for Python < 3.11."""

    def test_protocol_version_type_is_string(self):
        """Test ProtocolVersionType enum values are strings."""
        self.assertEqual(ProtocolVersionType.V1, "v1")
        self.assertEqual(ProtocolVersionType.V2, "v2")
        self.assertEqual(ProtocolVersionType.V3, "v3")

    def test_protocol_version_type_is_str_subclass(self):
        """Test ProtocolVersionType is a string subclass."""
        self.assertIsInstance(ProtocolVersionType.V1, str)
        self.assertIsInstance(ProtocolVersionType.V2, str)
        self.assertIsInstance(ProtocolVersionType.V3, str)


class TestConnectFunction(unittest.TestCase):
    """Test global connect function."""

    @patch("dbt.adapters.exasol.connections.ExasolConnection")
    def test_connect_default_autocommit(self, mock_exa_connection):
        """Test connect function sets autocommit=False by default."""
        from dbt.adapters.exasol.connections import connect

        connect(dsn="test:8563", user="sys", password="exasol")
        mock_exa_connection.assert_called_once()
        self.assertFalse(mock_exa_connection.call_args[1]["autocommit"])

    @patch("dbt.adapters.exasol.connections.ExasolConnection")
    def test_connect_explicit_autocommit(self, mock_exa_connection):
        """Test connect function respects explicit autocommit."""
        from dbt.adapters.exasol.connections import connect

        connect(dsn="test:8563", user="sys", password="exasol", autocommit=True)
        mock_exa_connection.assert_called_once()
        self.assertTrue(mock_exa_connection.call_args[1]["autocommit"])


class TestExasolConnectionCursor(unittest.TestCase):
    """Test ExasolConnection cursor method."""

    def test_cursor_returns_exasol_cursor(self):
        """Test cursor method returns ExasolCursor instance."""
        # Create a mock connection with required attributes
        mock_conn = Mock(spec=ExasolConnection)
        # Bind the real cursor method to the mock
        mock_conn.cursor = ExasolConnection.cursor.__get__(mock_conn, ExasolConnection)

        cursor = mock_conn.cursor()
        self.assertIsInstance(cursor, ExasolCursor)


class TestExasolCredentialsProperties(unittest.TestCase):
    """Test ExasolCredentials properties and methods."""

    def setUp(self):
        """Set up test credentials."""
        self.credentials = ExasolCredentials(
            dsn="localhost:8563",
            user="sys",
            password="exasol",
            database="test",
            schema="test_schema",
        )

    def test_type_property(self):
        """Test type property returns 'exasol'."""
        self.assertEqual(self.credentials.type, "exasol")

    def test_unique_field_property(self):
        """Test unique_field property returns dsn."""
        self.assertEqual(self.credentials.unique_field, "localhost:8563")

    def test_connection_keys_method(self):
        """Test _connection_keys returns expected keys."""
        keys = self.credentials._connection_keys()
        self.assertIn("dsn", keys)
        self.assertIn("user", keys)
        self.assertIn("database", keys)
        self.assertIn("schema", keys)
        self.assertIn("connection_timeout", keys)
        self.assertIn("encryption", keys)
        self.assertIn("protocol_version", keys)


class TestExceptionHandler(unittest.TestCase):
    """Test exception_handler context manager."""

    @patch.object(ExasolConnectionManager, "rollback_if_open")
    def test_exception_handler_with_dbt_runtime_error(self, mock_rollback):
        """Test exception_handler re-raises DbtRuntimeError."""
        from dbt_common.exceptions import DbtRuntimeError

        manager = ExasolConnectionManager(Mock(), Mock())

        with self.assertRaises(DbtRuntimeError) as context, manager.exception_handler("SELECT 1"):
            raise DbtRuntimeError("Test error")

        self.assertIn("Test error", str(context.exception))
        mock_rollback.assert_called_once()

    @patch.object(ExasolConnectionManager, "rollback_if_open")
    def test_exception_handler_wraps_other_exceptions(self, mock_rollback):
        """Test exception_handler wraps non-DbtRuntimeError exceptions."""
        from dbt_common.exceptions import DbtRuntimeError

        manager = ExasolConnectionManager(Mock(), Mock())

        with self.assertRaises(DbtRuntimeError), manager.exception_handler("SELECT 1"):
            raise ValueError("Some error")

        mock_rollback.assert_called_once()


class TestInvalidProtocolVersion(unittest.TestCase):
    """Test handling of invalid protocol versions."""

    @patch("dbt.adapters.exasol.connections.connect")
    def test_open_with_invalid_protocol_version(self, mock_connect):
        """Test open raises error with invalid protocol version."""
        from dbt_common.exceptions import DbtRuntimeError

        credentials = ExasolCredentials(
            dsn="localhost:8563",
            user="sys",
            password="exasol",
            database="test",
            schema="test_schema",
            protocol_version="invalid",
        )

        connection = Mock()
        connection.state = "closed"
        connection.credentials = credentials

        with self.assertRaises(DbtRuntimeError) as context:
            ExasolConnectionManager.open(connection)

        self.assertIn("is not a valid protocol version", str(context.exception))


class TestConnectionManagerMethods(unittest.TestCase):
    """Test ExasolConnectionManager utility methods."""

    def test_add_begin_query(self):
        """Test add_begin_query returns None."""
        manager = ExasolConnectionManager(Mock(), Mock())
        result = manager.add_begin_query()
        self.assertIsNone(result)

    def test_cancel(self):
        """Test cancel calls abort_query on connection."""
        manager = ExasolConnectionManager(Mock(), Mock())
        mock_connection = Mock()
        manager.cancel(mock_connection)
        mock_connection.abort_query.assert_called_once()


class TestGetThreadConnection(unittest.TestCase):
    """Test ExasolConnectionManager.get_thread_connection on-demand acquisition override.

    Covers connections.py:255-257 -- the current thread has no bound connection
    (i.e. the caller is outside a ``connection_named`` / ``acquire_connection``
    block), so ``set_connection_name`` must be invoked before delegating to the
    base implementation.
    """

    def _make_manager(self):
        mock_profile = Mock()
        mock_profile.credentials = ExasolCredentials(
            dsn="localhost:8563",
            user="u",
            password="p",
            database="DB",
            schema="S",
        )
        mock_profile.threads = 1
        mock_mp_context = Mock()
        mock_mp_context.RLock.return_value = threading.RLock()
        return ExasolConnectionManager(mock_profile, mock_mp_context)

    def test_calls_set_connection_name_when_unbound(self):
        """When no connection is bound to the thread, set_connection_name is called
        to lazily create one, and the resulting connection is returned."""
        manager = self._make_manager()
        fake_connection = Mock()

        def fake_set_connection_name(name=None):
            key = manager.get_thread_identifier()
            manager.thread_connections[key] = fake_connection
            return fake_connection

        manager.get_if_exists = Mock(return_value=None)
        manager.set_connection_name = Mock(side_effect=fake_set_connection_name)

        result = manager.get_thread_connection()

        manager.set_connection_name.assert_called_once()
        self.assertIs(result, fake_connection)

    def test_skips_set_connection_name_when_already_bound(self):
        """When a connection is already bound to the thread, set_connection_name
        must not be called and the existing connection is returned unchanged."""
        manager = self._make_manager()
        existing_connection = Mock()
        key = manager.get_thread_identifier()
        manager.thread_connections[key] = existing_connection

        manager.get_if_exists = Mock(return_value=existing_connection)
        manager.set_connection_name = Mock()

        result = manager.get_thread_connection()

        manager.set_connection_name.assert_not_called()
        self.assertIs(result, existing_connection)


class TestCursorImportFromFile(unittest.TestCase):
    """Test ExasolCursor import_from_file method."""

    def test_import_from_file_with_column_list(self):
        """Test import_from_file with explicit column list."""
        mock_connection = Mock(spec=ExasolConnection)
        mock_connection.row_separator = "LF"
        cursor = ExasolCursor(mock_connection)

        mock_agate_table = Mock()
        mock_agate_table.original_abspath = "/path/to/file.csv"

        table_info = ["schema", "table", '"col1","col2","col3"']

        cursor.import_from_file(mock_agate_table, table_info)

        mock_connection.import_from_file.assert_called_once()
        call_args = mock_connection.import_from_file.call_args
        self.assertEqual(call_args[1]["columns"], ['"col1"', '"col2"', '"col3"'])

    def test_import_from_file_without_column_list(self):
        """Test import_from_file without explicit column list (legacy format)."""
        mock_connection = Mock(spec=ExasolConnection)
        mock_connection.row_separator = "LF"
        cursor = ExasolCursor(mock_connection)

        mock_agate_table = Mock()
        mock_agate_table.original_abspath = "/path/to/file.csv"

        table_info = ["schema", "table"]

        cursor.import_from_file(mock_agate_table, table_info)

        mock_connection.import_from_file.assert_called_once()
        call_args = mock_connection.import_from_file.call_args
        self.assertNotIn("columns", call_args[1])


class TestCursorExecuteVariations(unittest.TestCase):
    """Test ExasolCursor execute method variations."""

    def test_execute_csv_import_with_columns(self):
        """Test execute with CSV import including column list."""
        mock_connection = Mock(spec=ExasolConnection)
        mock_connection.row_separator = "LF"
        cursor = ExasolCursor(mock_connection)

        mock_agate_table = Mock()
        mock_agate_table.original_abspath = "/path/to/file.csv"

        cursor.execute("0CSV|schema.table|col1,col2", mock_agate_table)

        mock_connection.import_from_file.assert_called_once()


class TestCursorFetchMethods(unittest.TestCase):
    """Test ExasolCursor fetch methods with edge cases."""

    def test_fetchone_with_no_statement(self):
        """Task 3.2: fetchone raises DbtRuntimeError when stmt is None."""
        from dbt_common.exceptions import DbtRuntimeError

        cursor = ExasolCursor(Mock())
        with self.assertRaises(DbtRuntimeError) as context:
            cursor.fetchone()
        self.assertIn("Cannot fetch on unset statement", str(context.exception))

    def test_fetchone_with_statement(self):
        """Test fetchone calls stmt.fetchone()."""
        cursor = ExasolCursor(Mock())
        mock_stmt = Mock()
        mock_stmt.fetchone.return_value = [1, "test"]
        cursor.stmt = mock_stmt

        result = cursor.fetchone()
        mock_stmt.fetchone.assert_called_once()
        self.assertEqual(result, [1, "test"])

    def test_fetchmany_with_no_statement(self):
        """Task 3.2: fetchmany raises DbtRuntimeError when stmt is None."""
        from dbt_common.exceptions import DbtRuntimeError

        cursor = ExasolCursor(Mock())
        with self.assertRaises(DbtRuntimeError) as context:
            cursor.fetchmany()
        self.assertIn("Cannot fetch on unset statement", str(context.exception))

    def test_fetchmany_with_custom_size(self):
        """Test fetchmany with custom size."""
        cursor = ExasolCursor(Mock())
        mock_stmt = Mock()
        mock_stmt.fetchmany.return_value = [[1, "test"], [2, "test2"]]
        cursor.stmt = mock_stmt

        result = cursor.fetchmany(10)
        mock_stmt.fetchmany.assert_called_once_with(10)
        self.assertEqual(len(result), 2)

    def test_fetchmany_with_default_size(self):
        """Test fetchmany uses array_size when size is None."""
        cursor = ExasolCursor(Mock())
        cursor.array_size = 5
        mock_stmt = Mock()
        cursor.stmt = mock_stmt

        cursor.fetchmany()
        mock_stmt.fetchmany.assert_called_once_with(5)

    def test_fetchall_with_no_statement(self):
        """Task 3.2: fetchall raises DbtRuntimeError when stmt is None."""
        from dbt_common.exceptions import DbtRuntimeError

        cursor = ExasolCursor(Mock())
        with self.assertRaises(DbtRuntimeError) as context:
            cursor.fetchall()
        self.assertIn("Cannot fetch on unset statement", str(context.exception))

    def test_fetchall_with_statement(self):
        """Test fetchall calls stmt.fetchall()."""
        cursor = ExasolCursor(Mock())
        mock_stmt = Mock()
        mock_stmt.fetchall.return_value = [[1, "test"], [2, "test2"]]
        cursor.stmt = mock_stmt

        result = cursor.fetchall()
        mock_stmt.fetchall.assert_called_once()
        self.assertEqual(len(result), 2)


class TestDetectRowSeparator(unittest.TestCase):
    """Test _detect_row_separator, which keeps seed IMPORT from silently
    corrupting (CRLF file read as LF) or dropping (LF file read as CRLF) rows.
    """

    def _write(self, data: bytes) -> str:
        path = Path(self._tmpdir.name) / "seed.csv"
        path.write_bytes(data)
        return str(path)

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

    def test_detects_lf(self):
        """Unix line endings are detected as LF."""
        self.assertEqual(_detect_row_separator(self._write(b"id,name\n1,alice\n")), "LF")

    def test_detects_crlf(self):
        """Windows line endings are detected as CRLF."""
        self.assertEqual(_detect_row_separator(self._write(b"id,name\r\n1,alice\r\n")), "CRLF")

    def test_detects_cr(self):
        """Classic-Mac CR-only line endings are detected as CR."""
        self.assertEqual(_detect_row_separator(self._write(b"id,name\r1,alice\r")), "CR")

    def test_empty_file_uses_fallback(self):
        """An empty file has no terminator, so the fallback is used."""
        self.assertEqual(_detect_row_separator(self._write(b""), fallback="CRLF"), "CRLF")

    def test_single_line_without_terminator_uses_fallback(self):
        """A header-only file without a newline cannot be sniffed."""
        self.assertEqual(_detect_row_separator(self._write(b"id,name"), fallback="LF"), "LF")

    def test_missing_file_uses_fallback(self):
        """Detection is best-effort: an unreadable path falls back, not raises."""
        missing = str(Path(self._tmpdir.name) / "does-not-exist.csv")
        self.assertEqual(_detect_row_separator(missing, fallback="LF"), "LF")

    def test_default_fallback_is_module_default(self):
        """Omitting `fallback` uses the OS-derived module default."""
        self.assertEqual(_detect_row_separator(self._write(b"")), ROW_SEPARATOR_DEFAULT)

    def test_crlf_file_with_lf_inside_quoted_field(self):
        """The first terminator wins; embedded newlines do not mislead detection."""
        path = self._write(b'id,name\r\n1,"a\nb"\r\n')
        self.assertEqual(_detect_row_separator(path), "CRLF")

    def test_mixed_line_endings_warn_and_pick_first(self):
        """Mixed endings cannot be handled by one separator, so warn."""
        path = self._write(b"id,name\n1,alice\r\n2,bob\n")
        with patch("dbt.adapters.exasol.connections.LOGGER") as mock_logger:
            self.assertEqual(_detect_row_separator(path), "LF")
        mock_logger.warning.assert_called_once()
        self.assertIn("mixes line endings", mock_logger.warning.call_args[0][0])

    def test_uniform_line_endings_do_not_warn(self):
        """A well-formed file must not emit spurious warnings."""
        path = self._write(b"id,name\r\n1,alice\r\n2,bob\r\n")
        with patch("dbt.adapters.exasol.connections.LOGGER") as mock_logger:
            self.assertEqual(_detect_row_separator(path), "CRLF")
        mock_logger.warning.assert_not_called()

    def test_terminator_beyond_first_chunk(self):
        """Chunked reads keep going until a terminator is found."""
        path = self._write(b"x" * 70000 + b"\r\n" + b"1,alice\r\n")
        self.assertEqual(_detect_row_separator(path), "CRLF")


class TestImportRowSeparatorResolution(unittest.TestCase):
    """Test how ExasolCursor.import_from_file resolves the row separator."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.path = Path(self._tmpdir.name) / "seed.csv"
        self.path.write_bytes(b"id,name\r\n1,alice\r\n")
        self.agate_table = Mock()
        self.agate_table.original_abspath = str(self.path)

    def _import(self, configured_separator):
        connection = Mock(spec=ExasolConnection)
        connection.row_separator = configured_separator
        ExasolCursor(connection).import_from_file(self.agate_table, ["SCHEMA", "TABLE"])
        return connection.import_from_file.call_args[1]["import_params"]["row_separator"]

    def test_detects_when_unconfigured(self):
        """With no profiles.yml value, the CRLF file is imported as CRLF."""
        self.assertEqual(self._import(None), "CRLF")

    def test_explicit_value_always_wins(self):
        """An explicit profiles.yml value overrides detection (back-compat)."""
        self.assertEqual(self._import("LF"), "LF")

    def test_detects_per_file_not_per_connection(self):
        """Seeds with different line endings each get the right separator."""
        lf_path = Path(self._tmpdir.name) / "other.csv"
        lf_path.write_bytes(b"id,name\n1,alice\n")
        lf_table = Mock()
        lf_table.original_abspath = str(lf_path)

        connection = Mock(spec=ExasolConnection)
        connection.row_separator = None
        cursor = ExasolCursor(connection)

        cursor.import_from_file(self.agate_table, ["SCHEMA", "TABLE"])
        cursor.import_from_file(lf_table, ["SCHEMA", "OTHER"])

        separators = [call[1]["import_params"]["row_separator"] for call in connection.import_from_file.call_args_list]
        self.assertEqual(separators, ["CRLF", "LF"])


class TestCursorClose(unittest.TestCase):
    """Test ExasolCursor close method."""

    def test_close_with_statement(self):
        """Test close calls stmt.close()."""
        cursor = ExasolCursor(Mock())
        mock_stmt = Mock()
        cursor.stmt = mock_stmt

        cursor.close()
        mock_stmt.close.assert_called_once()

    def test_close_without_statement(self):
        """Test close does nothing when stmt is None."""
        cursor = ExasolCursor(Mock())
        cursor.stmt = None
        cursor.close()  # Should not raise


if __name__ == "__main__":
    unittest.main()
