# pylint: disable=wrong-import-order  # Necessary due to conditional Python 3.11+ StrEnum import
# pylint: disable=ungrouped-imports  # Required for proper conditional StrEnum import grouping
"""
DBT adapter connection implementation for Exasol.
"""

import decimal
import hashlib
import os
import ssl

# Python 3.11+ has StrEnum built-in, use shim for 3.9/3.10
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import agate  # type: ignore[import-untyped]
import dbt_common.exceptions
import pyexasol
from dateutil import parser  # type: ignore[import-untyped]
from dbt.adapters.contracts.connection import (
    AdapterResponse,
    Connection,
    ConnectionState,
    Credentials,
    Identifier,
)
from dbt.adapters.events.logging import AdapterLogger
from dbt.adapters.sql import SQLConnectionManager  # type: ignore
from pyexasol import ExaConnection

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        """
        Backport of StrEnum for Python < 3.11.

        StrEnum members are strings and can be used in string contexts.
        This shim provides compatibility with the built-in StrEnum
        available in Python 3.11+.
        """


ROW_SEPARATOR_DEFAULT = "LF" if os.linesep == "\n" else "CRLF"
TIMESTAMP_FORMAT_DEFAULT = "YYYY-MM-DDTHH:MI:SS.FF6"
_UNSET_STATEMENT_ERROR = "Cannot fetch on unset statement"

LOGGER = AdapterLogger("exasol")


def connect(**kwargs: Any):
    """
    Global connect method initializing ExasolConnection
    """
    if "autocommit" not in kwargs:
        kwargs["autocommit"] = False
    return ExasolConnection(**kwargs)  # type: ignore[arg-type]


class ProtocolVersionType(StrEnum):
    """Exasol protocol versions"""

    V1 = "v1"
    V2 = "v2"
    V3 = "v3"


class ExasolConnection(ExaConnection):
    """
    Override to instantiate ExasolCursor
    """

    row_separator: str = ROW_SEPARATOR_DEFAULT
    timestamp_format: str = TIMESTAMP_FORMAT_DEFAULT

    def cursor(self):
        """Instance of ExasolCursor"""
        return ExasolCursor(self)


@dataclass
class ExasolAdapterResponse(AdapterResponse):
    """
    Override AdapterResponse
    """

    execution_time: float | None = None


# pylint: disable=too-many-instance-attributes  # All attributes are required Exasol connection parameters from pyexasol
@dataclass
class ExasolCredentials(Credentials):
    """Profile parameters for Exasol in dbt profiles.yml"""

    dsn: str
    database: str
    schema: str
    # One of user+pass, access_token, or refresh_token needs to be specified in profiles.yml
    user: str = ""
    password: str = ""  # Field name for user credential, not a hardcoded password
    access_token: str = ""
    refresh_token: str = ""
    # optional statements that can be set in profiles.yml
    # some options might interfere with dbt, so caution is advised
    connection_timeout: int = pyexasol.constant.DEFAULT_CONNECTION_TIMEOUT
    socket_timeout: int = pyexasol.constant.DEFAULT_SOCKET_TIMEOUT
    query_timeout: int = pyexasol.constant.DEFAULT_QUERY_TIMEOUT
    compression: bool = False
    encryption: bool = True
    validate_server_certificate: bool = True
    ## Because of potential interference with dbt,
    # the following statements are not (yet) implemented
    # fetch_dict: bool
    # fetch_size_bytes: int
    # lower_ident: bool
    # quote_ident: bool
    # verbose_error: bool
    # debug: bool
    # udf_output_port: int
    protocol_version: str = "v3"
    retries: int = 1
    row_separator: str = ROW_SEPARATOR_DEFAULT
    timestamp_format: str = TIMESTAMP_FORMAT_DEFAULT

    _ALIASES = {"dbname": "database", "pass": "password"}  # nosec: B105 - field name alias, not actual password

    @property
    def type(self):
        return "exasol"

    @property
    def unique_field(self):
        return self.dsn

    def _connection_keys(self):
        return (
            "dsn",
            "user",
            "database",
            "schema",
            "connection_timeout",
            "socket_timeout",
            "query_timeout",
            "compression",
            "encryption",
            "validate_server_certificate",
            "protocol_version",
            "row_separator",
            "timestamp_format",
        )


class ExasolConnectionManager(SQLConnectionManager):
    """Managing Exasol connections"""

    TYPE = "exasol"
    _pool: dict[str, ExaConnection] = {}
    _pool_lock = threading.Lock()

    @contextmanager
    def exception_handler(self, sql):
        try:
            yield

        except Exception as yielded_exception:
            LOGGER.debug(f"Error running SQL: {sql}")
            LOGGER.debug("Rolling back transaction.")
            self.rollback_if_open()
            if isinstance(yielded_exception, dbt_common.exceptions.DbtRuntimeError):
                # during a sql query, an internal to dbt exception was raised.
                # this sounds a lot like a signal handler and probably has
                # useful information, so raise it without modification.
                raise

            raise dbt_common.exceptions.DbtRuntimeError(yielded_exception)

    @classmethod
    def _get_pool(cls) -> dict[str, ExaConnection]:
        """Get the class-level connection pool."""
        return cls._pool

    @classmethod
    def _get_pool_key(cls, credentials: ExasolCredentials) -> str:
        """Generate pool key from credentials hash."""
        key_parts = (
            credentials.dsn,
            credentials.user,
            credentials.database,
            credentials.schema,
        )
        return hashlib.sha256(str(key_parts).encode()).hexdigest()

    @classmethod
    def _is_connection_valid(cls, conn: ExaConnection) -> bool:
        """Validate connection with SELECT 1 query."""
        try:
            if conn.is_closed:
                return False
            cursor = conn.execute("SELECT 1")
            cursor.fetchone()
            return True
        except Exception:  # pylint: disable=broad-except
            return False

    @classmethod
    def cleanup_pool(cls) -> None:
        """Close all pooled connections with thread-safe locking."""
        with cls._pool_lock:
            pool = cls._get_pool()
            for conn in pool.values():
                try:
                    if not conn.is_closed:
                        conn.close()
                except Exception:  # pylint: disable=broad-except
                    # Best-effort cleanup - log and continue closing other connections
                    LOGGER.debug("Failed to close pooled connection during cleanup")
            pool.clear()

    @classmethod
    def initialize_pool(cls, credentials: ExasolCredentials, size: int) -> None:
        """Pre-warm pool with connections for given credentials."""
        pool_key = cls._get_pool_key(credentials)

        # Check existing connections with lock
        with cls._pool_lock:
            pool = cls._get_pool()
            existing_count = 0
            if pool_key in pool and cls._is_connection_valid(pool[pool_key]):
                existing_count = 1

        # Calculate how many more connections we need
        connections_to_create = max(0, size - existing_count)

        # Create connections and close them so they get added to the pool
        for i in range(connections_to_create):
            connection = Connection(
                type=Identifier(cls.TYPE),
                name=f"pool_init_{i}",
                state=ConnectionState.INIT,
                credentials=credentials,
            )
            # Open connection (creates it)
            cls.open(connection)
            # Close it so it gets added to the pool
            cls._close_handle(connection)

    @classmethod
    def _fetch_rows(cls, cursor: Any, limit: int | None) -> list[Any]:
        """Fetch rows from cursor based on limit."""
        if limit:
            return cursor.fetchmany(limit)
        return cursor.fetchall()

    @classmethod
    def _needs_type_conversion(cls, rows: list[Any], col_idx: int) -> bool:
        """Check if column needs type conversion from string."""
        return len(rows) > 0 and isinstance(rows[0][col_idx], str)

    @classmethod
    def _convert_column_to_decimal(cls, rows: list[Any], col_idx: int) -> list[Any]:
        """Convert string column values to Decimal."""
        for rownum, row in enumerate(rows):
            if row[col_idx] is not None:
                tmp = list(row)
                tmp[col_idx] = decimal.Decimal(row[col_idx])
                rows[rownum] = tmp
        return rows

    @classmethod
    def _convert_column_to_timestamp(cls, rows: list[Any], col_idx: int) -> list[Any]:
        """Convert string column values to datetime."""
        for rownum, row in enumerate(rows):
            if row[col_idx] is not None:
                tmp = list(row)
                tmp[col_idx] = parser.parse(row[col_idx])
                rows[rownum] = tmp
        return rows

    @classmethod
    def _apply_type_conversions(cls, rows: list[Any], col_idx: int, col_type: str) -> list[Any]:
        """Apply appropriate type conversion based on column type."""
        if not cls._needs_type_conversion(rows, col_idx):
            return rows

        if col_type in ["DECIMAL", "BIGINT"]:
            return cls._convert_column_to_decimal(rows, col_idx)
        if col_type.startswith("TIMESTAMP"):
            return cls._convert_column_to_timestamp(rows, col_idx)
        return rows

    @classmethod
    def get_result_from_cursor(cls, cursor: Any, limit: int | None) -> agate.Table:
        data: list[Any] = []
        column_names: list[str] = []

        if cursor.description is not None:
            rows = cls._fetch_rows(cursor, limit)

            for idx, col in enumerate(cursor.description):
                column_names.append(col[0])
                rows = cls._apply_type_conversions(rows, idx, col[1])

            data = list(cls.process_results(column_names, rows))

        return dbt_common.clients.agate_helper.table_from_data_flat(data, column_names)  # type: ignore

    @classmethod
    def _try_get_pooled_connection(cls, credentials: ExasolCredentials) -> ExaConnection | None:
        """Try to get a valid connection from the pool.

        Returns the connection if found and valid, None otherwise.
        Removes invalid connections from the pool.
        """
        pool_key = cls._get_pool_key(credentials)

        with cls._pool_lock:
            pool = cls._get_pool()
            if pool_key not in pool:
                return None

            conn = pool[pool_key]
            if cls._is_connection_valid(conn):
                LOGGER.debug("Reusing pooled connection")
                # Remove from pool while in use
                del pool[pool_key]
                return conn

            # Remove invalid connection from pool
            LOGGER.debug("Removing invalid connection from pool")
            del pool[pool_key]
            return None

    @classmethod
    def _parse_protocol_version(cls, protocol_version_str: str) -> Any:
        """Parse protocol version string to pyexasol constant.

        Args:
            protocol_version_str: Version string like 'v1', 'v2', 'v3'

        Returns:
            pyexasol protocol version constant

        Raises:
            DbtRuntimeError: If protocol version is invalid
        """
        try:
            version = ProtocolVersionType(protocol_version_str.lower())

            if version == ProtocolVersionType.V1:
                return pyexasol.PROTOCOL_V1
            if version == ProtocolVersionType.V2:
                return pyexasol.PROTOCOL_V2
            return pyexasol.PROTOCOL_V3
        except (ValueError, KeyError, AttributeError) as exc:
            raise dbt_common.exceptions.DbtRuntimeError(
                f"{protocol_version_str} is not a valid protocol version."
            ) from exc

    @classmethod
    def _build_ssl_options(cls, credentials: ExasolCredentials) -> dict | None:
        """Build SSL options based on credentials settings.

        Returns:
            SSL options dict if encryption is enabled, None otherwise
        """
        if not credentials.encryption:
            return None

        if credentials.validate_server_certificate:
            # Explicitly set CERT_REQUIRED to suppress PyExasol warnings
            return {"cert_reqs": ssl.CERT_REQUIRED}
        # Allow connections without certificate validation
        return {"cert_reqs": ssl.CERT_NONE}

    @classmethod
    def _create_connection(cls, credentials: ExasolCredentials, protocol_version: Any) -> ExasolConnection:
        """Create a new Exasol connection with the given credentials.

        Args:
            credentials: Connection credentials
            protocol_version: pyexasol protocol version constant

        Returns:
            Configured ExasolConnection
        """
        websocket_sslopt = cls._build_ssl_options(credentials)

        conn = connect(
            dsn=credentials.dsn,
            user=credentials.user,
            password=credentials.password,
            access_token=credentials.access_token,
            refresh_token=credentials.refresh_token,
            autocommit=True,
            connection_timeout=credentials.connection_timeout,
            socket_timeout=credentials.socket_timeout,
            query_timeout=credentials.query_timeout,
            compression=credentials.compression,
            encryption=credentials.encryption,
            websocket_sslopt=websocket_sslopt,
            protocol_version=protocol_version,
        )
        # exasol adapter specific attributes that are unknown to pyexasol
        # those can be added to ExasolConnection as members
        conn.row_separator = credentials.row_separator
        conn.timestamp_format = credentials.timestamp_format
        conn.execute(f"alter session set NLS_TIMESTAMP_FORMAT='{conn.timestamp_format}'")

        return conn

    @classmethod
    def open(cls, connection):
        """Open a connection to Exasol database.

        Attempts to reuse a pooled connection if available, otherwise creates
        a new connection with retry support.
        """
        if connection.state == "open":
            LOGGER.debug("Connection is already open, skipping open.")
            return connection

        credentials = connection.credentials

        # Try to get a valid connection from the pool
        pooled_conn = cls._try_get_pooled_connection(credentials)
        if pooled_conn is not None:
            connection.handle = pooled_conn
            connection.state = "open"
            return connection

        # Parse protocol version
        protocol_version = cls._parse_protocol_version(credentials.protocol_version)

        # Create connection factory for retry logic
        def _connect():
            return cls._create_connection(credentials, protocol_version)

        connection = cls.retry_connection(
            connection,
            connect=_connect,
            logger=LOGGER,
            retry_limit=credentials.retries,
            retryable_exceptions=[pyexasol.ExaError],
        )

        # Don't store new connection in pool immediately - it will be returned
        # to the pool when _close_handle() is called

        return connection

    def add_begin_query(self):
        return

    def cancel(self, connection):
        connection.abort_query()  # type: ignore

    @classmethod
    def _close_handle(cls, connection) -> None:
        """Override to return connection to pool instead of closing."""
        if connection.handle is None or connection.credentials is None:
            return

        # Return connection to pool with locking
        pool_key = cls._get_pool_key(connection.credentials)
        with cls._pool_lock:
            pool = cls._get_pool()
            # Only add to pool if it's still valid and not already there
            if cls._is_connection_valid(connection.handle) and pool_key not in pool:
                pool[pool_key] = connection.handle

    @classmethod
    def get_response(cls, cursor) -> ExasolAdapterResponse:
        return ExasolAdapterResponse(
            _message="OK",
            rows_affected=cursor.rowcount,
            execution_time=cursor.execution_time,
        )

    @classmethod
    def data_type_code_to_name(cls, type_code) -> str:
        return type_code.split("(")[0].upper()


class ExasolCursor:
    """Exasol dbt-adapter cursor implementation"""

    array_size = 1

    def __init__(self, connection):
        self.connection = connection
        self.stmt = None

    def import_from_file(self, agate_table, table_info):
        """
        Import CSV data into pre-created table with proper column quoting.

        Args:
            agate_table: agate table with CSV data
            table_info: tuple of (schema, table_name, column_names_csv)
                        or tuple of (schema, table_name) for backwards compat
        """
        if len(table_info) == 3:
            # New format with explicit column names
            schema, table_name, columns_csv = table_info
            column_list = [col.strip() for col in columns_csv.split(",")]
        else:
            # Legacy format (shouldn't happen after migration)
            schema, table_name = table_info
            # Fallback: use agate column names without quoting
            column_list = None

        import_params = {
            "skip": 1,  # Skip CSV header row
            "row_separator": self.connection.row_separator,
        }

        # Use column list if available (for proper quoting support)
        if column_list:
            self.connection.import_from_file(
                agate_table.original_abspath,
                (schema, table_name),
                import_params=import_params,
                columns=column_list,
            )
        else:
            # Fallback without column specification
            self.connection.import_from_file(
                agate_table.original_abspath,
                (schema, table_name),
                import_params=import_params,
            )

        return self

    def execute(self, query, bindings: Any | None = None):
        """executing query"""
        if query.startswith("0CSV|"):
            # Format: "0CSV|schema.table" or "0CSV|schema.table|col1,col2,col3"
            parts = query.split("|", 2)[1:]  # Skip "0CSV" prefix
            table_path = parts[0]
            columns_csv = parts[1] if len(parts) > 1 else None

            # Parse schema.table
            schema, table_name = table_path.split(".", 1)

            # Build table_info tuple
            if columns_csv:
                table_info = [schema, table_name, columns_csv]
            else:
                table_info = [schema, table_name]

            self.import_from_file(bindings, table_info)  # type: ignore
        elif "|SEPARATEMEPLEASE|" in query:
            sqls = query.split("|SEPARATEMEPLEASE|")
            for sql in sqls:
                self.stmt = self.connection.execute(sql)
        else:
            try:
                self.stmt = self.connection.execute(query)
            except pyexasol.ExaQueryError as e:
                raise dbt_common.exceptions.DbtDatabaseError("Exasol Query Error: " + e.message)
        return self

    def fetchone(self):
        """fetch single row"""
        if self.stmt is None:
            raise RuntimeError(_UNSET_STATEMENT_ERROR)
        return self.stmt.fetchone()

    def fetchmany(self, size=None):
        """fetch single row"""
        if size is None:
            size = self.array_size

        if self.stmt is None:
            raise RuntimeError(_UNSET_STATEMENT_ERROR)
        return self.stmt.fetchmany(size)

    def fetchall(self):
        """fetch single row"""
        if self.stmt is None:
            raise RuntimeError(_UNSET_STATEMENT_ERROR)
        return self.stmt.fetchall()

    @property
    def description(self):
        """columns in cursor"""
        cols = []
        if self.stmt is None:
            return cols

        if self.stmt.result_type != "resultSet":
            return None

        for k, value_set in self.stmt.columns().items():
            cols.append(
                (
                    k,
                    value_set.get("type", None),
                    value_set.get("size", None),
                    value_set.get("size", None),
                    value_set.get("precision", None),
                    value_set.get("scale", None),
                    True,
                )
            )

        return cols

    @property
    def rowcount(self):
        """number of rows in result set"""
        if self.stmt is not None:
            return self.stmt.rowcount()
        return 0

    @property
    def execution_time(self):
        """elapsed time for query"""
        if self.stmt is not None:
            return self.stmt.execution_time
        return 0

    def close(self):
        """closing the cursor / statement"""
        if self.stmt is not None:
            self.stmt.close()
