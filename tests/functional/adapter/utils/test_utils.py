import os

import pytest
from dbt.tests.adapter.utils.base_utils import BaseUtils
from dbt.tests.adapter.utils.test_any_value import BaseAnyValue
from dbt.tests.adapter.utils.test_array_append import BaseArrayAppend
from dbt.tests.adapter.utils.test_array_concat import BaseArrayConcat
from dbt.tests.adapter.utils.test_array_construct import BaseArrayConstruct
from dbt.tests.adapter.utils.test_bool_or import BaseBoolOr
from dbt.tests.adapter.utils.test_cast_bool_to_text import BaseCastBoolToText
from dbt.tests.adapter.utils.test_concat import BaseConcat
from dbt.tests.adapter.utils.test_current_timestamp import BaseCurrentTimestampNaive
from dbt.tests.adapter.utils.test_date_trunc import BaseDateTrunc
from dbt.tests.adapter.utils.test_dateadd import BaseDateAdd
from dbt.tests.adapter.utils.test_datediff import BaseDateDiff
from dbt.tests.adapter.utils.test_escape_single_quotes import (
    BaseEscapeSingleQuotesBackslash,
)
from dbt.tests.adapter.utils.test_except import BaseExcept
from dbt.tests.adapter.utils.test_hash import BaseHash
from dbt.tests.adapter.utils.test_intersect import BaseIntersect
from dbt.tests.adapter.utils.test_last_day import BaseLastDay
from dbt.tests.adapter.utils.test_length import BaseLength
from dbt.tests.adapter.utils.test_listagg import BaseListagg
from dbt.tests.adapter.utils.test_position import BasePosition
from dbt.tests.adapter.utils.test_replace import BaseReplace
from dbt.tests.adapter.utils.test_right import BaseRight
from dbt.tests.adapter.utils.test_safe_cast import BaseSafeCast
from dbt.tests.adapter.utils.test_split_part import BaseSplitPart
from dbt.tests.adapter.utils.test_string_literal import BaseStringLiteral
from dbt.tests.util import run_dbt
from dbt_common.exceptions import CompilationError
from utils_fixtures import *  # type: ignore[import-not-found] # noqa: F403


class TestAnyValueExasol(BaseAnyValue):
    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_any_value.yml": exasol__models__test_any_value_yml,
            "test_any_value.sql": exasol__models__test_any_value_sql,
        }


@pytest.mark.xfail(reason="Not supported on Exasol")
class TestArrayAppendExasol(BaseArrayAppend):
    pass


@pytest.mark.xfail(reason="Not supported on Exasol")
class TestArrayConcatExasol(BaseArrayConcat):
    pass


@pytest.mark.xfail(reason="Not supported on Exasol")
class TestArrayConstructExasol(BaseArrayConstruct):
    pass


class TestBoolOrExasol(BaseBoolOr):
    @pytest.fixture(scope="class")
    @classmethod
    def seeds(cls):
        return {
            "data_bool_or.csv": exasol__seeds__data_bool_or_csv,
            "data_bool_or_expected.csv": exasol__seeds__data_bool_or_expected_csv,
        }

    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_bool_or.yml": exasol__models__test_bool_or_yml,
            "test_bool_or.sql": exasol__models__test_bool_or_sql,
        }


class TestCastBoolToTextExasol(BaseCastBoolToText):
    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_cast_bool_to_text.yml": exasol__models__test_cast_bool_to_text_yml,
            "test_cast_bool_to_text.sql": exasol__models__test_cast_bool_to_text_sql,
        }


class TestConcatExasol(BaseConcat):
    @pytest.fixture(scope="class")
    @classmethod
    def seeds(cls):
        return {"data_concat.csv": exasol__seeds__data_concat_csv}

    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_concat.yml": exasol__models__test_concat_yml,
            "test_concat.sql": exasol__models__test_concat_sql,
        }


# Use either BaseCurrentTimestampAware or BaseCurrentTimestampNaive but not both
@pytest.mark.xfail(reason="Not supported on Exasol")
class TestCurrentTimestampExasol(BaseCurrentTimestampNaive):
    pass


class TestDateAddExasol(BaseDateAdd):
    @pytest.fixture(scope="class")
    @classmethod
    def project_config_update(cls):
        return {
            "name": "test",
            # this is only needed for BigQuery, right?
            # no harm having it here until/unless there's an adapter that doesn't support the 'timestamp' type
            "seeds": {
                "test": {
                    "data_dateadd": {
                        "+column_types": {
                            "from_time": "timestamp",
                            "res": "timestamp",
                        },
                    },
                },
            },
        }

    @pytest.fixture(scope="class")
    @classmethod
    def seeds(cls):
        return {"data_dateadd.csv": exasol__seeds__data_dateadd_csv}

    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_dateadd.yml": exasol__models__test_dateadd_yml,
            "test_dateadd.sql": exasol__models__test_dateadd_sql,
        }


class TestDateDiffExasol(BaseDateDiff):
    @pytest.fixture(scope="class")
    @classmethod
    def dbt_profile_target(cls):
        return {
            "type": "exasol",
            "threads": 8,
            "dsn": os.getenv("DBT_DSN", "localhost:8563"),
            "user": os.getenv("DBT_USER", "sys"),
            "pass": os.getenv("DBT_PASS", "exasol"),
            "dbname": "DB",
            "timestamp_format": "YYYY-MM-DD HH:MI:SS.FF6",
            "validate_server_certificate": False,
        }

    @pytest.fixture(scope="class")
    @classmethod
    def seeds(cls):
        return {"data_datediff.csv": exasol__seeds__data_datediff_csv}

    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_datediff.yml": exasol__models__test_datediff_yml,
            "test_datediff.sql": exasol__models__test_datediff_sql,
        }


class TestDateTruncExasol(BaseDateTrunc):
    @pytest.fixture(scope="class")
    @classmethod
    def seeds(cls):
        return {"data_date_trunc.csv": exasol__seeds__data_date_trunc_csv}

    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_date_trunc.yml": exasol__models__test_date_trunc_yml,
            "test_date_trunc.sql": exasol__models__test_date_trunc_sql,
        }


class TestEscapeSingleQuotesExasol(BaseEscapeSingleQuotesBackslash):
    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_escape_single_quotes.yml": exasol__models__test_escape_single_quotes_yml,
            "test_escape_single_quotes.sql": exasol__models__test_escape_single_quotes_quote_sql,
        }


class BaseEscapeSingleQuotesBackslashExasol(BaseUtils):
    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_escape_single_quotes.yml": exasol__models__test_escape_single_quotes_yml,
            "test_escape_single_quotes.sql": exasol__models__test_escape_single_quotes_backslash_sql,
        }


class TestExceptExasol(BaseExcept):
    pass


class TestHashExasol(BaseHash):
    @pytest.fixture(scope="class")
    @classmethod
    def seeds(cls):
        return {"data_hash.csv": exasol__seeds__data_hash_csv}

    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_hash.yml": exasol__models__test_hash_yml,
            "test_hash.sql": exasol__models__test_hash_sql,
        }


class TestIntersectExasol(BaseIntersect):
    pass


class TestLastDayExasol(BaseLastDay):
    @pytest.fixture(scope="class")
    @classmethod
    def seeds(cls):
        return {"data_last_day.csv": exasol__seeds__data_last_day_csv}

    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_last_day.yml": exasol__models__test_last_day_yml,
            "test_last_day.sql": exasol__models__test_last_day_sql,
        }


class TestLengthExasol(BaseLength):
    @pytest.fixture(scope="class")
    @classmethod
    def seeds(cls):
        return {"data_length.csv": exasol__seeds__data_length_csv}

    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_length.yml": exasol__models__test_length_yml,
            "test_length.sql": exasol__models__test_length_sql,
        }


class TestListaggExasol(BaseListagg):
    @pytest.fixture(scope="class")
    @classmethod
    def seeds(cls):
        return {
            "data_listagg.csv": exasol__seeds__data_listagg_csv,
            "data_listagg_output.csv": exasol__seeds__data_listagg_output_csv,
        }

    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_listagg.yml": exasol__models__test_listagg_yml,
            "test_listagg.sql": exasol__models__test_listagg_sql,
        }

    def test_build_assert_equal(self, project):
        with pytest.raises(CompilationError) as exc_info:
            run_dbt(["build"], expect_pass=False)
        assert exc_info.value.msg == "`limit_num` parameter is not supported on Exasol!"


class TestPositionExasol(BasePosition):
    @pytest.fixture(scope="class")
    @classmethod
    def seeds(cls):
        return {"data_position.csv": exasol__seeds__data_position_csv}

    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_position.yml": exasol__models__test_position_yml,
            "test_position.sql": exasol__models__test_position_sql,
        }


class TestReplaceExasol(BaseReplace):
    @pytest.fixture(scope="class")
    @classmethod
    def seeds(cls):
        return {"data_replace.csv": exasol__seeds__data_replace_csv}

    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_replace.yml": exasol__models__test_replace_yml,
            "test_replace.sql": exasol__models__test_replace_sql,
        }


class TestRightExasol(BaseRight):
    @pytest.fixture(scope="class")
    @classmethod
    def seeds(cls):
        return {"data_right.csv": exasol__seeds__data_right_csv}

    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_right.yml": exasol__models__test_right_yml,
            "test_right.sql": exasol__models__test_right_sql,
        }


class TestSafeCastExasol(BaseSafeCast):
    @pytest.fixture(scope="class")
    @classmethod
    def seeds(cls):
        return {"data_safe_cast.csv": exasol__seeds__data_safe_cast_csv}

    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_safe_cast.yml": exasol__models__test_safe_cast_yml,
            "test_safe_cast.sql": exasol__models__test_safe_cast_sql,
        }


class TestSplitPartExasol(BaseSplitPart):
    @pytest.fixture(scope="class")
    @classmethod
    def seeds(cls):
        return {"data_split_part.csv": exasol__seeds__data_split_part_csv}

    @pytest.fixture(scope="class")
    @classmethod
    def models(cls):
        return {
            "test_split_part.yml": exasol__models__test_split_part_yml,
            "test_split_part.sql": exasol__models__test_split_part_sql,
        }

    def test_build_assert_equal(self, project):
        with pytest.raises(CompilationError) as exc_info:
            run_dbt(["build"], expect_pass=False)
        assert exc_info.value.msg == "Unsupported on Exasol! Sorry..."


class TestStringLiteralExasol(BaseStringLiteral):
    pass
