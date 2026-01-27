import pytest
from dbt.tests.adapter.constraints.fixtures import (
    my_incremental_model_sql,
    my_model_incremental_wrong_name_sql,
    my_model_incremental_wrong_order_sql,
    my_model_sql,
    my_model_with_quoted_column_name_sql,
    my_model_wrong_name_sql,
    my_model_wrong_order_sql,
)
from dbt.tests.adapter.constraints.test_constraints import (
    BaseConstraintQuotedColumn,
    BaseConstraintsRollback,
    BaseConstraintsRuntimeDdlEnforcement,
    BaseContractSqlHeader,
    BaseIncrementalConstraintsColumnsEqual,
    BaseIncrementalConstraintsRollback,
    BaseIncrementalConstraintsRuntimeDdlEnforcement,
    BaseModelConstraintsRuntimeEnforcement,
    BaseTableConstraintsColumnsEqual,
    BaseViewConstraintsColumnsEqual,
)
from dbt.tests.util import (
    run_dbt,
    write_file,
)

from tests.functional.adapter.constraints.fixtures import (
    exasol_constrained_model_schema_yml,
    exasol_expected_sql,
    exasol_model_contract_header_schema_yml,
    exasol_model_contract_sql_header_sql,
    exasol_model_incremental_contract_sql_header,
    exasol_model_schema_yml,
    exasol_quoted_column_schema_yml,
    my_model_view_wrong_name_sql,
    my_model_view_wrong_order_sql,
)


class ExasolColumnEqualSetup:
    @pytest.fixture
    def string_type(self):
        return "CHAR(50)"

    @pytest.fixture
    def int_type(self):
        return "INTEGER"

    @pytest.fixture
    def data_types(self, schema_int_type, int_type, string_type):
        # sql_column_value, schema_data_type, error_data_type
        return [
            ["1", schema_int_type, int_type],
            ["'1'", string_type, string_type],
            ["cast('2019-01-01' as date)", "date", "DATE"],
            ["true", "boolean", "BOOLEAN"],
            [
                "cast('2013-11-03T00:00:00.000000' as TIMESTAMP)",
                "timestamp(6)",
                "TIMESTAMP",
            ],
            ["cast('1.0' as DECIMAL(10,2))", "DECIMAL", "DECIMAL"],
        ]


class TestExasolTableConstraintsColumnsEqual(ExasolColumnEqualSetup, BaseTableConstraintsColumnsEqual):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "my_model_wrong_order.sql": my_model_wrong_order_sql,
            "my_model_wrong_name.sql": my_model_wrong_name_sql,
            "constraints_schema.yml": exasol_model_schema_yml,
        }

    def test__constraints_wrong_column_data_types(
        self,
        project,
        string_type,
        int_type,
        schema_string_type,
        schema_int_type,
        data_types,
    ):
        pass


class TestExasolViewConstraintsColumnsEqual(ExasolColumnEqualSetup, BaseViewConstraintsColumnsEqual):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "my_model_wrong_order.sql": my_model_view_wrong_order_sql,
            "my_model_wrong_name.sql": my_model_view_wrong_name_sql,
            "constraints_schema.yml": exasol_model_schema_yml,
        }

    def test__constraints_wrong_column_data_types(
        self,
        project,
        string_type,
        int_type,
        schema_string_type,
        schema_int_type,
        data_types,
    ):
        pass


class TestExasolIncrementalConstraintsColumnsEqual(ExasolColumnEqualSetup, BaseIncrementalConstraintsColumnsEqual):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "my_model_wrong_order.sql": my_model_incremental_wrong_order_sql,
            "my_model_wrong_name.sql": my_model_incremental_wrong_name_sql,
            "constraints_schema.yml": exasol_model_schema_yml,
        }

    def test__constraints_wrong_column_data_types(
        self,
        project,
        string_type,
        int_type,
        schema_string_type,
        schema_int_type,
        data_types,
    ):
        pass


class TestExasolTableConstraintsRuntimeDdlEnforcement(BaseConstraintsRuntimeDdlEnforcement):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "my_model.sql": my_model_wrong_order_sql,
            "constraints_schema.yml": exasol_model_schema_yml,
        }

    @pytest.fixture(scope="class")
    def expected_sql(self):
        return exasol_expected_sql


class TestExasolTableConstraintsRollback(BaseConstraintsRollback):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "my_model.sql": my_model_sql,
            "constraints_schema.yml": exasol_model_schema_yml,
        }

    @pytest.fixture(scope="class")
    def expected_error_messages(self):
        return ["constraint violation - not null"]

    # Exasol constraint failures generate their own error messages which have to be handled differently than in the standard tests
    def test__constraints_enforcement_rollback(self, project, expected_color, expected_error_messages, null_model_sql):
        results = run_dbt(["run", "-s", "my_model"])
        assert len(results) == 1

        # Make a contract-breaking change to the model
        write_file(null_model_sql, "models", "my_model.sql")

        failing_results = run_dbt(["run", "-s", "my_model"], expect_pass=False)
        assert len(failing_results) == 1
        assert expected_error_messages[0] in failing_results[0].message


class TestExasolIncrementalConstraintsRuntimeDdlEnforcement(BaseIncrementalConstraintsRuntimeDdlEnforcement):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "my_model.sql": my_model_incremental_wrong_order_sql,
            "constraints_schema.yml": exasol_model_schema_yml,
        }

    @pytest.fixture(scope="class")
    def expected_sql(self):
        return exasol_expected_sql


class TestExasolIncrementalConstraintsRollback(BaseIncrementalConstraintsRollback):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "my_model.sql": my_incremental_model_sql,
            "constraints_schema.yml": exasol_model_schema_yml,
        }

    @pytest.fixture(scope="class")
    def expected_error_messages(self):
        return ["constraint violation - not null"]

    # Exasol constraint failures generate their own error messages which have to be handled differently than in the standard tests
    def test__constraints_enforcement_rollback(self, project, expected_color, expected_error_messages, null_model_sql):
        results = run_dbt(["run", "-s", "my_model"])
        assert len(results) == 1

        # Make a contract-breaking change to the model
        write_file(null_model_sql, "models", "my_model.sql")

        failing_results = run_dbt(["run", "-s", "my_model"], expect_pass=False)
        assert len(failing_results) == 1
        assert expected_error_messages[0] in failing_results[0].message


class TestExasolModelConstraintsRuntimeEnforcement(BaseModelConstraintsRuntimeEnforcement):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "my_model.sql": my_model_sql,
            "constraints_schema.yml": exasol_constrained_model_schema_yml,
        }

    @pytest.fixture(scope="class")
    def expected_sql(self):
        return """
create or replace table <model_identifier> ( 
    id decimal(18,0) not null, 
    color char(50), 
    date_day char(50), 
    primary key (id) ) ; 
    |separatemeplease| 
    insert into <model_identifier> 
    select 
    id, 
    color, 
    date_day 
    from ( 
        select 1 as id, 
        'blue' as color, 
        '2019-01-01' as date_day ) as model_subq
"""


class TestExasolConstraintQuotedColumn(BaseConstraintQuotedColumn):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "my_model.sql": my_model_with_quoted_column_name_sql,
            "constraints_schema.yml": exasol_quoted_column_schema_yml,
        }

    @pytest.fixture(scope="class")
    def expected_sql(self):
        return """
        create or replace table <model_identifier> (
            id decimal(18,0) not null,
            "from" char(50) not null,
            date_day char(50)
        ) ;
        |separatemeplease|
        insert into <model_identifier>
        
            select id, "from", date_day
            from (
                select
                'blue' as "from",
                1 as id,
                '2019-01-01' as date_day
            ) as model_subq
        """


class BaseExasolTableContractSqlHeader(BaseContractSqlHeader):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "my_model_contract_sql_header.sql": exasol_model_contract_sql_header_sql,
            "constraints_schema.yml": exasol_model_contract_header_schema_yml,
        }


class BaseExasolIncrementalContractSqlHeader(BaseContractSqlHeader):
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "my_model_contract_sql_header.sql": exasol_model_incremental_contract_sql_header,
            "constraints_schema.yml": exasol_model_contract_header_schema_yml,
        }


class TestExasolTableContractSqlHeader(BaseExasolTableContractSqlHeader):
    pass


class TestExasolIncrementalContractSqlHeader(BaseExasolIncrementalContractSqlHeader):
    pass
