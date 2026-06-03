import pytest
from dbt.artifacts.schemas.results import RunStatus
from dbt.events.types import RunResultError
from dbt.tests.adapter.functions import files
from dbt.tests.adapter.functions.test_udfs import (
    DeterministicUDF,
    ErrorForUnsupportedType,
    NonDeterministicUDF,
    PythonUDFDefaultArgSupport,
    PythonUDFEntryPointRequired,
    PythonUDFRuntimeVersionRequired,
    PythonUDFSupported,
    PythonUDFVolatilitySupport,
    SqlUDFDefaultArgSupport,
    StableUDF,
    UDFsBasic,
)
from dbt.tests.util import run_dbt
from dbt_common.events.base_types import EventMsg
from dbt_common.events.event_catcher import EventCatcher

# Exasol-specific fixtures
EXASOL_MY_UDF_YML = """
functions:
  - name: price_for_xlarge
    description: Calculate the price for the xlarge version of a standard item
    arguments:
      - name: price
        data_type: DOUBLE
        description: The price of the standard item
    returns:
      data_type: DOUBLE
      description: The resulting xlarge price
"""

EXASOL_MY_UDF_WITH_DEFAULT_ARG_YML = """
functions:
  - name: price_for_xlarge
    description: Calculate the price for the xlarge version of a standard item
    arguments:
      - name: price
        data_type: DOUBLE
        description: The price of the standard item
        default_value: 100
    returns:
      data_type: DOUBLE
      description: The resulting xlarge price
"""

EXASOL_MY_UDF_PYTHON_YML = """
functions:
  - name: price_for_xlarge
    description: Calculate the price for the xlarge version of a standard item
    config:
      entry_point: price_for_xlarge
      runtime_version: "3.12"
    arguments:
      - name: price
        data_type: DOUBLE
        description: The price of the standard item
    returns:
      data_type: DOUBLE
      description: The resulting xlarge price
"""

EXASOL_MY_UDF_PYTHON_WITH_DEFAULT_ARG_YML = """
functions:
  - name: price_for_xlarge
    description: Calculate the price for the xlarge version of a standard item
    config:
      entry_point: price_for_xlarge
      runtime_version: "3.12"
    arguments:
      - name: price
        data_type: DOUBLE
        description: The price of the standard item
        default_value: 100
    returns:
      data_type: DOUBLE
      description: The resulting xlarge price
"""


class ExasolVolatilityMixin:
    """Shared mixin asserting Exasol omits all volatility keywords."""

    def check_function_volatility(self, sql: str):
        assert "IMMUTABLE" not in sql
        assert "STABLE" not in sql
        assert "VOLATILE" not in sql


class ExasolPythonScalarScriptEventMixin:
    """Shared mixin: recognize Exasol's PYTHON3 SCALAR SCRIPT create event.

    The base test classes look for ``CREATE OR REPLACE FUNCTION``; Exasol's
    Python UDFs use a different DDL. Subclasses can override ``function_name``
    if their fixture uses a different name.
    """

    function_name = "price_for_xlarge"
    script_marker = "CREATE OR REPLACE PYTHON3 SCALAR SCRIPT"

    def is_function_create_event(self, event: EventMsg) -> bool:
        return event.data.node_info.node_name == self.function_name and self.script_marker in event.data.sql


class _PythonUDFValidationTest:
    """Shared body for tests asserting a dbt-core validation error message.

    Subclasses set ``expected_error`` to the substring expected in the error
    message. The original base class asserts a "macro not found" error which
    doesn't apply to Exasol (we implement the macro); dbt-core's validation
    fires instead.
    """

    expected_error: str = ""

    def test_udfs(self, project, sql_event_catcher):
        run_result_error_catcher = EventCatcher(RunResultError)
        result = run_dbt(
            ["build", "--debug"],
            expect_pass=False,
            callbacks=[run_result_error_catcher.catch],
        )
        assert len(result.results) == 1
        node_result = result.results[0]
        assert node_result.status == RunStatus.Error

        assert len(run_result_error_catcher.caught_events) == 1
        assert self.expected_error in run_result_error_catcher.caught_events[0].data.msg


class TestExasolUDFsBasic(UDFsBasic):
    @pytest.fixture(scope="class")
    def functions(self):
        return {
            "price_for_xlarge.sql": files.MY_UDF_SQL,
            "price_for_xlarge.yml": EXASOL_MY_UDF_YML,
        }


class TestExasolDeterministicUDF(ExasolVolatilityMixin, DeterministicUDF):
    pass


class TestExasolStableUDF(ExasolVolatilityMixin, StableUDF):
    pass


class TestExasolNonDeterministicUDF(ExasolVolatilityMixin, NonDeterministicUDF):
    pass


class TestExasolErrorForUnsupportedType(ErrorForUnsupportedType):
    pass


class TestExasolPythonUDF(ExasolPythonScalarScriptEventMixin, PythonUDFSupported):
    @pytest.fixture(scope="class")
    def functions(self):
        return {
            "price_for_xlarge.py": files.MY_UDF_PYTHON,
            "price_for_xlarge.yml": EXASOL_MY_UDF_PYTHON_YML,
        }


class TestExasolPythonUDFRuntimeVersionRequired(_PythonUDFValidationTest, PythonUDFRuntimeVersionRequired):
    expected_error = "A `runtime_version` is required for python functions"


class TestExasolPythonUDFEntryPointRequired(_PythonUDFValidationTest, PythonUDFEntryPointRequired):
    expected_error = "An `entry_point` is required for python functions"


class TestExasolSqlUDFDefaultArg(SqlUDFDefaultArgSupport):
    expect_default_arg_support = False

    @pytest.fixture(scope="class")
    def functions(self):
        return {
            "price_for_xlarge.sql": files.MY_UDF_SQL,
            "price_for_xlarge.yml": EXASOL_MY_UDF_WITH_DEFAULT_ARG_YML,
        }


class TestExasolPythonUDFDefaultArg(ExasolPythonScalarScriptEventMixin, PythonUDFDefaultArgSupport):
    expect_default_arg_support = False

    @pytest.fixture(scope="class")
    def functions(self):
        return {
            "price_for_xlarge.py": files.MY_UDF_PYTHON,
            "price_for_xlarge.yml": EXASOL_MY_UDF_PYTHON_WITH_DEFAULT_ARG_YML,
        }


class TestExasolPythonUDFVolatility(
    ExasolVolatilityMixin,
    ExasolPythonScalarScriptEventMixin,
    PythonUDFVolatilitySupport,
):
    @pytest.fixture(scope="class")
    def functions(self):
        return {
            "price_for_xlarge.py": files.MY_UDF_PYTHON,
            "price_for_xlarge.yml": EXASOL_MY_UDF_PYTHON_YML,
        }
