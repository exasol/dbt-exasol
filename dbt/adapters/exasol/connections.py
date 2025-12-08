# pylint: disable=wrong-import-order
# pylint: disable=ungrouped-imports
"""
DBT adapter connection implementation for Exasol.
"""

import decimal
import os
import ssl
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, List, Optional

import agate
import dbt_common.exceptions
import pyexasol
from dateutil import parser

# from dbt.adapters.base import Credentials  # type: ignore
from dbt.adapters.sql import SQLConnectionManager  # type: ignore
from dbt.adapters.contracts.connection import AdapterResponse, Credentials
from dbt.adapters.events.logging import AdapterLogger

# Python 3.11+ has StrEnum built-in, use shim for 3.9/3.10
try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass


from pyexasol import ExaConnection

ROW_SEPARATOR_DEFAULT = "LF" if os.linesep == "\n" else "CRLF"
TIMESTAMP_FORMAT_DEFAULT = "YYYY-MM-DDTHH:MI:SS.FF6"

LOGGER = AdapterLogger("exasol")


def connect(**kwargs: bool):
    """
    Global connect method initializing ExasolConnection
    """
    if "autocommit" not in kwargs:
        kwargs["autocommit"] = False
    return ExasolConnection(**kwargs)


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

    execution_time: Optional[float] = None


# pylint: disable=too-many-instance-attributes
@dataclass
class ExasolCredentials(Credentials):
    """Profile parameters for Exasol in dbt profiles.yml"""

    dsn: str
    database: str
    schema: str
    # One of user+pass, access_token, or refresh_token needs to be specified in profiles.yml
    user: str = ""
    password: str = ""
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

    _ALIASES = {"dbname": "database", "pass": "password"}

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
    def get_result_from_cursor(cls, cursor: Any, limit: Optional[int]) -> agate.Table:
        data: List[Any] = []
        column_names: List[str] = []

        if cursor.description is not None:
            # column_names = [col[0] for col in cursor.description]
            if limit:
                rows = cursor.fetchmany(limit)
            else:
                rows = cursor.fetchall()
            for idx, col in enumerate(cursor.description):
                column_names.append(col[0])
                if len(rows) > 0 and isinstance(rows[0][idx], str):
                    if col[1] in ["DECIMAL", "BIGINT"]:
                        for rownum, row in enumerate(rows):
                            if row[idx] is None:
                                continue
                            tmp = list(row)
                            tmp[idx] = decimal.Decimal(row[idx])
                            rows[rownum] = tmp
                    elif col[1].startswith("TIMESTAMP"):
                        for rownum, row in enumerate(rows):
                            if row[idx] is None:
                                continue
                            tmp = list(row)
                            tmp[idx] = parser.parse(row[idx])
                            rows[rownum] = tmp
            data = cls.process_results(column_names, rows)

        return dbt_common.clients.agate_helper.table_from_data_flat(data, column_names)  # type: ignore

    @classmethod
    # pylint: disable=raise-missing-from
    def open(cls, connection):
        if connection.state == "open":
            LOGGER.debug("Connection is already open, skipping open.")
            return connection
        credentials = connection.credentials

        # Support protocol versions
        try:
            format_protocol_version = credentials.protocol_version.lower()
            version = ProtocolVersionType(format_protocol_version)

            if version == ProtocolVersionType.V1:
                protocol_version = pyexasol.PROTOCOL_V1
            elif version == ProtocolVersionType.V2:
                protocol_version = pyexasol.PROTOCOL_V2
            else:
                protocol_version = pyexasol.PROTOCOL_V3
        except:
            raise dbt_common.exceptions.DbtRuntimeError(
                f"{credentials.protocol_version} is not a valid protocol version."
            )

        def _connect():
            # Build SSL options based on validate_server_certificate setting
            # Only applies when encryption is enabled
            websocket_sslopt = None
            if credentials.encryption:
                if credentials.validate_server_certificate:
                    # Explicitly set CERT_REQUIRED to suppress PyExasol warnings
                    websocket_sslopt = {"cert_reqs": ssl.CERT_REQUIRED}
                else:
                    # Allow connections without certificate validation
                    websocket_sslopt = {"cert_reqs": ssl.CERT_NONE}

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
            conn.execute(
                f"alter session set NLS_TIMESTAMP_FORMAT='{conn.timestamp_format}'"
            )

            return conn

        repeatable_exceptions = [pyexasol.ExaError]

        return cls.retry_connection(
            connection,
            connect=_connect,
            logger=LOGGER,
            retry_limit=credentials.retries,
            retryable_exceptions=repeatable_exceptions,
        )

    def add_begin_query(self):
        return

    def cancel(self, connection):
        connection.abort_query()  # type: ignore

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

    def import_from_file(self, agate_table, table):
        """importing csv skip=1 parameter for header row"""
        self.connection.import_from_file(
            agate_table.original_abspath,
            (table.split(".")[0], table.split(".")[1]),
            import_params={"skip": 1, "row_separator": self.connection.row_separator},
        )
        return self

    def execute(self, query, bindings: Optional[Any] = None):
        """executing query"""
        if query.startswith("0CSV|"):
            self.import_from_file(bindings, query.split("|", 1)[1])  # type: ignore
        elif query.__contains__("|SEPARATEMEPLEASE|"):
            sqls = query.split("|SEPARATEMEPLEASE|")
            for sql in sqls:
                self.stmt = self.connection.execute(sql)
        else:
            try:
                self.stmt = self.connection.execute(query)
            except pyexasol.ExaQueryError as e:
                raise dbt_common.exceptions.DbtDatabaseError(
                    "Exasol Query Error: " + e.message
                )
        return self

    def fetchone(self):
        """fetch single row"""
        if self.stmt is None:
            raise RuntimeError("Cannot fetch on unset statement")
        return self.stmt.fetchone()

    def fetchmany(self, size=None):
        """fetch single row"""
        if size is None:
            size = self.array_size

        if self.stmt is None:
            raise RuntimeError("Cannot fetch on unset statement")
        return self.stmt.fetchmany(size)

    def fetchall(self):
        """fetch single row"""
        if self.stmt is None:
            raise RuntimeError("Cannot fetch on unset statement")
        return self.stmt.fetchall()

    @property
    def description(self):
        """columns in cursor"""
        cols = []
        if self.stmt is None:
            return cols

        if "resultSet" != self.stmt.result_type:
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
