import pytest, os

from dbt.tests.adapter.basic.test_adapter_methods import BaseAdapterMethod
from dbt.tests.adapter.basic.test_base import BaseSimpleMaterializations
from dbt.tests.adapter.basic.test_empty import BaseEmpty
from dbt.tests.adapter.basic.test_ephemeral import BaseEphemeral
from dbt.tests.adapter.basic.test_generic_tests import BaseGenericTests
from dbt.tests.adapter.basic.test_incremental import (
    BaseIncremental,
    BaseIncrementalNotSchemaChange,
)
from dbt.tests.adapter.basic.test_singular_tests import BaseSingularTests
from dbt.tests.adapter.basic.test_singular_tests_ephemeral import (
    BaseSingularTestsEphemeral,
)
from dbt.tests.adapter.basic.test_snapshot_check_cols import BaseSnapshotCheckCols
from dbt.tests.adapter.basic.test_snapshot_timestamp import BaseSnapshotTimestamp
from dbt.tests.adapter.basic.test_validate_connection import BaseValidateConnection
from test_docs_generate import BaseDocsGenerate, BaseDocsGenReferences
from expected_catalog import (
    base_expected_catalog,
    no_stats,
    expected_references_catalog,
)


class TestSimpleMaterializationsExasol(BaseSimpleMaterializations):
    pass


class TestSingularTestsExasol(BaseSingularTests):
    pass


class TestSingularTestsEphemeralExasol(BaseSingularTestsEphemeral):
    pass


class TestEmptyExasol(BaseEmpty):
    pass


class TestEphemeralExasol(BaseEphemeral):
    pass


class TestIncrementalExasol(BaseIncremental):
    pass


class TestGenericTestsExasol(BaseGenericTests):
    pass


class TestSnapshotCheckColsExasol(BaseSnapshotCheckCols):
    pass


class TestSnapshotTimestampExasol(BaseSnapshotTimestamp):
    pass


class TestBaseAdapterMethodExasol(BaseAdapterMethod):
    pass


class TestBaseCachingExasol(BaseAdapterMethod):
    pass


class TestValidateConnectionExasol(BaseValidateConnection):
    pass


class TestDocsGenerateExasol(BaseDocsGenerate):
    @pytest.fixture(scope="class")
    def dbt_profile_target(self):
        return {
            "type": "exasol",
            "threads": 1,
            "dsn": os.getenv("DBT_DSN", "localhost:8563"),
            "user": os.getenv("DBT_USER", "sys"),
            "pass": os.getenv("DBT_PASS", "exasol"),
            "dbname": "DB",
            "timestamp_format": "YYYY-MM-DD HH:MI:SS.FF6",
            "validate_server_certificate": False,
        }


class TestDocsGenReferencesExasol(BaseDocsGenReferences):
    @pytest.fixture(scope="class")
    def dbt_profile_target(self):
        return {
            "type": "exasol",
            "threads": 1,
            "dsn": os.getenv("DBT_DSN", "localhost:8563"),
            "user": os.getenv("DBT_USER", "sys"),
            "pass": os.getenv("DBT_PASS", "exasol"),
            "dbname": "DB",
            "timestamp_format": "YYYY-MM-DD HH:MI:SS.FF6",
            "validate_server_certificate": False,
        }


class TestBaseIncrementalNotSchemaChangeExasol(BaseIncrementalNotSchemaChange):
    pass
