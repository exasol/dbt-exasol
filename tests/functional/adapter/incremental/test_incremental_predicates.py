import pytest
from dbt.tests.adapter.incremental.test_incremental_predicates import (
    BaseIncrementalPredicates,
)


class TestIncrementalPredicatesDeleteInsertExasol(BaseIncrementalPredicates):
    pass


class TestPredicatesDeleteInsertExasol(BaseIncrementalPredicates):
    @pytest.fixture(scope="class")
    @classmethod
    def project_config_update(cls):
        return {"models": {"+predicates": ["id != 2"], "+incremental_strategy": "delete+insert"}}


class TestIncrementalPredicatesMergeExasol(BaseIncrementalPredicates):
    @pytest.fixture(scope="class")
    @classmethod
    def project_config_update(cls):
        return {
            "models": {
                "+incremental_predicates": ["dbt_internal_dest.id != 2"],
                "+incremental_strategy": "merge",
            }
        }


class TestPredicatesMergeExasol(BaseIncrementalPredicates):
    @pytest.fixture(scope="class")
    @classmethod
    def project_config_update(cls):
        return {
            "models": {
                "+predicates": ["dbt_internal_dest.id != 2"],
                "+incremental_strategy": "merge",
            }
        }
