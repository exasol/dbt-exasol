"""pytest conftest for functional tests - sets up test environment"""

import os

import pyexasol
import pytest

from dbt.adapters.exasol.connections import (
    ExasolConnectionManager,
    ExasolCredentials,
)


def _setup_test_roles(dsn: str, user: str, password: str) -> None:
    """Create test roles needed for grants tests.

    Reads role names from environment variables:
    - DBT_TEST_USER_1
    - DBT_TEST_USER_2
    - DBT_TEST_USER_3

    Args:
        dsn: Database connection string (e.g., 'localhost:8563' or 'host/nocertcheck:8563')
        user: Database user (typically 'sys')
        password: Database password
    """
    # Get role names from environment
    role_env_vars = ["DBT_TEST_USER_1", "DBT_TEST_USER_2", "DBT_TEST_USER_3"]
    roles_to_create = []
    for env_var in role_env_vars:
        role_name = os.getenv(env_var)
        if role_name:
            roles_to_create.append(role_name)

    if not roles_to_create:
        print("ℹ No test roles configured in environment variables")
        return

    # Connect to database (itde already waits for db to be ready)
    conn = pyexasol.connect(dsn=dsn, user=user, password=password)

    # Create roles
    created = []
    skipped = []
    for role_name in roles_to_create:
        try:
            conn.execute(f"CREATE ROLE {role_name}")
            created.append(role_name)
        except pyexasol.ExaQueryError as e:
            # Role already exists - this is fine
            if e.code == "42500" and "conflicts" in str(e).lower():
                skipped.append(role_name)
            else:
                # Different error - re-raise
                conn.close()
                raise

    conn.close()

    # Report results
    if created:
        print(f"✓ Created test roles: {', '.join(created)}")
    if skipped:
        print(f"ℹ Test roles already exist: {', '.join(skipped)}")


@pytest.fixture(scope="session", autouse=True)
def initialize_connection_pool():
    """Initialize connection pool at start of functional test session."""
    pool_size = int(os.getenv("DBT_CONN_POOL_SIZE", "5"))

    # Create credentials from environment variables
    dsn = os.getenv("DBT_DSN", "localhost:8563")
    user = os.getenv("DBT_USER", "sys")
    password = os.getenv("DBT_PASS", "exasol")
    database = os.getenv("DBT_DATABASE", "DB")
    schema = os.getenv("DBT_SCHEMA", "public")

    credentials = ExasolCredentials(
        dsn=dsn,
        user=user,
        password=password,
        database=database,
        schema=schema,
        validate_server_certificate=False,
    )

    # Initialize pool
    ExasolConnectionManager.initialize_pool(credentials, pool_size)

    yield

    # Cleanup is handled by cleanup_connection_pool fixture


@pytest.fixture(scope="session", autouse=True)
def cleanup_connection_pool():
    """Cleanup connection pool at end of functional test session."""
    yield
    ExasolConnectionManager.cleanup_pool()


def pytest_sessionstart(session):
    """Called before test session starts.

    This hook runs once before any functional tests and sets up test roles
    needed for grants tests. It runs for both nox and pure pytest calls,
    but ONLY when running functional tests.
    """
    dsn = os.getenv("DBT_DSN", "localhost:8563")
    user = os.getenv("DBT_USER", "sys")
    password = os.getenv("DBT_PASS", "exasol")

    try:
        _setup_test_roles(dsn=dsn, user=user, password=password)
    except Exception as e:
        print(f"⚠ Warning: Failed to create test roles: {e}")
        print("  Tests requiring grants may fail")
