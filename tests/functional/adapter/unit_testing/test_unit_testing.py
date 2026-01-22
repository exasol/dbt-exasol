import pytest
from dbt.tests.adapter.unit_testing.test_types import BaseUnitTestingTypes
from dbt.tests.adapter.unit_testing.test_case_insensitivity import BaseUnitTestCaseInsensivity
from dbt.tests.adapter.unit_testing.test_invalid_input import BaseUnitTestInvalidInput


class TestExasolUnitTestingTypes(BaseUnitTestingTypes):
    @pytest.fixture
    def data_types(self):
        # sql_value, yaml_value
        return [
            ["1", "1"],
            ["2.0", "2.0"],
            ["'12345'", "12345"],
            ["'string'", "string"],
            ["cast('2019-01-01' as date)", "'2019-01-01'"],
            ["true", "true"],
            ["cast('2013-11-03T00:00:00.000000' as timestamp)", "'2013-11-03T00:00:00.000000'"],
            ["cast('1.0' as decimal(10,2))", "1.0"],
        ]
    


class TestExasolUnitTestCaseInsensitivity(BaseUnitTestCaseInsensivity):
    pass

class TestExasolUnitTestInvalidInput(BaseUnitTestInvalidInput):
    pass
