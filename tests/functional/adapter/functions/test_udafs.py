import pytest
from dbt.artifacts.schemas.results import RunStatus
from dbt.events.types import RunResultError
from dbt.tests.adapter.functions import files
from dbt.tests.adapter.functions.test_udafs import (
    BasicPythonUDAF,
    BasicSQLUDAF,
    PythonUDAFDefaultArgSupport,
)
from dbt.tests.util import run_dbt
from dbt_common.events.base_types import EventMsg
from dbt_common.events.event_catcher import EventCatcher

# `value` is a reserved word in Exasol, so the dbt-core base ``BASIC_MODEL_SQL``
# fixture (``1 as value``) is not parseable. Use a non-reserved column alias.
EXASOL_BASIC_MODEL_SQL = """
SELECT 1 as id, 1 as val
UNION ALL
SELECT 2 as id, 2 as val
UNION ALL
SELECT 3 as id, 3 as val
"""

# Exasol-specific fixtures
EXASOL_SUM_SQUARED_UDAF_PYTHON_YML = """
functions:
  - name: sum_squared
    description: Sums all the values, then squares the result
    config:
      type: aggregate
      entry_point: SumSquared
      runtime_version: "3.11"
    arguments:
      - name: value
        data_type: DOUBLE
        description: The value to to agg (and in the end square the result)
    returns:
      data_type: DOUBLE
      description: The sum of the input values, then squared
"""

EXASOL_SUM_SQUARED_UDAF_PYTHON_WITH_DEFAULT_ARG_YML = """
functions:
  - name: sum_squared
    description: Sums all the values, then squares the result
    config:
      type: aggregate
      entry_point: SumSquared
      runtime_version: "3.11"
    arguments:
      - name: value
        data_type: DOUBLE
        description: The value to to agg (and in the end square the result)
        default_value: 1
    returns:
      data_type: DOUBLE
      description: The sum of the input values, then squared
"""


class ExasolPythonSetScriptEventMixin:
    """Shared mixin: recognize Exasol's PYTHON3 SET SCRIPT create event.

    Also overrides the ``models`` fixture with an Exasol-compatible
    ``basic_model.sql`` because the dbt-core base fixture aliases a column as
    ``value`` (a reserved word in Exasol).
    """

    function_name = "sum_squared"
    script_marker = "CREATE OR REPLACE PYTHON3 SET SCRIPT"

    def is_function_create_event(self, event: EventMsg) -> bool:
        return event.data.node_info.node_name == self.function_name and self.script_marker in event.data.sql

    @pytest.fixture(scope="class")
    def models(self):
        return {"basic_model.sql": EXASOL_BASIC_MODEL_SQL}


class TestExasolAggregateSQLError(BasicSQLUDAF):
    """Override to expect a build failure with a clear error message.

    The base ``test_udaf`` asserts on ``sql_event_catcher`` after a successful
    build. When the build fails, the event catcher catches nothing, so the
    test method must be overridden.

    The base fixture also ships a ``basic_model.sql`` that references the
    failing UDAF; when the UDAF compile-errors, the dependent model also
    errors, producing more than one result. We must therefore:

    1. Filter results by ``resource_type == 'function'`` rather than asserting
       a total count.
    2. Filter caught events by message content rather than asserting a total
       event count.
    """

    def test_udaf(self, project, sql_event_catcher):
        run_result_error_catcher = EventCatcher(RunResultError)
        result = run_dbt(
            ["build", "--debug"],
            expect_pass=False,
            callbacks=[run_result_error_catcher.catch],
        )

        function_results = [r for r in result.results if r.node.resource_type == "function"]
        assert len(function_results) == 1
        assert function_results[0].status == RunStatus.Error

        function_errors = [
            e
            for e in run_result_error_catcher.caught_events
            if "SQL aggregate UDFs are not supported in Exasol" in e.data.msg
        ]
        assert len(function_errors) == 1


class TestExasolAggregatePython(ExasolPythonSetScriptEventMixin, BasicPythonUDAF):
    @pytest.fixture(scope="class")
    def functions(self):
        return {
            "sum_squared.py": files.SUM_SQUARED_UDAF_PYTHON,
            "sum_squared.yml": EXASOL_SUM_SQUARED_UDAF_PYTHON_YML,
        }

    def test_udaf(self, project, sql_event_catcher):
        """Override: the base inline query references the reserved column
        ``value``; Exasol's compatible model exposes it as ``val``."""
        run_dbt(["build", "--debug"], callbacks=[sql_event_catcher.catch])

        assert len(sql_event_catcher.caught_events) == 1
        self.check_function_volatility(sql_event_catcher.caught_events[0].data.sql)

        result = run_dbt(
            [
                "show",
                "--inline",
                "SELECT {{ function('sum_squared') }}(val) FROM {{ ref('basic_model') }}",
            ]
        )
        assert len(result.results) == 1
        # 1 + 2 + 3 = 6, then 6^2 = 36
        assert result.results[0].agate_table.rows[0].values()[0] == 36.0


class TestExasolAggregatePythonDefaultArg(ExasolPythonSetScriptEventMixin, PythonUDAFDefaultArgSupport):
    expect_default_arg_support = False

    @pytest.fixture(scope="class")
    def functions(self):
        return {
            "sum_squared.py": files.SUM_SQUARED_UDAF_PYTHON,
            "sum_squared.yml": EXASOL_SUM_SQUARED_UDAF_PYTHON_WITH_DEFAULT_ARG_YML,
        }
