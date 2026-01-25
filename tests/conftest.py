"""pytest conftest to load base dbt project fixtures"""

import os

import pytest
from dotenv import load_dotenv

load_dotenv()

pytest_plugins = ["dbt.tests.fixtures.project"]


@pytest.fixture(scope="class")
def dbt_profile_target():
    """Fixture overwrite from dbt-core to configure profiles.yml

    Returns:
        dict: key values for profiles.yml
    """
    return {
        "type": "exasol",
        "threads": 1,
        "dsn": os.getenv("DBT_DSN", "localhost:8563"),
        "user": os.getenv("DBT_USER", "sys"),
        "pass": os.getenv("DBT_PASS", "exasol"),
        "dbname": "DB",
        "validate_server_certificate": False,
    }
