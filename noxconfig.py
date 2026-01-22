from __future__ import annotations

import os
from pathlib import Path

import pyexasol
from exasol.toolbox.config import BaseConfig
from exasol.toolbox.nox.plugin import hookimpl
from nox import Session
from pydantic import (
    computed_field,
)

DEFAULT_PORT = 8563
DEFAULT_DB_VERSION = "8.29.13"
CONTAINER_SUFFIX = "test"
CONTAINER_NAME = f"db_container_{CONTAINER_SUFFIX}"


def start_test_db(
    session: Session,
    port: int = DEFAULT_PORT,
    db_version: str = DEFAULT_DB_VERSION,
    with_certificate: bool = True,
) -> None:
    # For Docker in a VM setup, refer to the ``doc/user_guide/developer_guide.rst``
    command = [
        "itde",
        "spawn-test-environment",
        "--environment-name",
        CONTAINER_SUFFIX,
        "--database-port-forward",
        f"{port}",
        "--bucketfs-port-forward",
        "2580",
        "--docker-db-image-version",
        db_version,
        "--db-mem-size",
        "16GB",
    ]
    if with_certificate:
        command.append(
            "--create-certificates",
        )

    session.run(*command, external=True)

    # Set up test roles after database starts
    # Use DBT_DSN from env if available, otherwise construct from port
    # DBT_DSN may include options like 'host/nocertcheck:8563'
    dsn = os.getenv("DBT_DSN")
    if not dsn:
        dsn = f"localhost:{port}"

    user = os.getenv("DBT_USER", "sys")
    password = os.getenv("DBT_PASS", "exasol")

    try:
        _setup_test_roles(dsn=dsn, user=user, password=password)
    except Exception as e:
        print(f"⚠ Warning: Failed to create test roles: {e}")
        print("  Tests requiring grants may fail")


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


def stop_test_db(session: Session) -> None:
    session.run("docker", "kill", CONTAINER_NAME, external=True)


class StartDB:
    @hookimpl
    def pre_integration_tests_hook(self, session, config, context):
        port = context.get("port", DEFAULT_PORT)
        db_version = context.get("db_version", DEFAULT_DB_VERSION)
        start_test_db(session=session, port=port, db_version=db_version)


class StopDB:
    @hookimpl
    def post_integration_tests_hook(self, session, config, context):
        stop_test_db(session=session)


class Config(BaseConfig):
    @computed_field  # type: ignore[misc]
    @property
    def source_code_path(self) -> Path:
        """
        Path to the source code of the project.

        Override to use dbt/ directory instead of project_name.
        The project name is dbt-exasol, but source code is in dbt/.
        """
        return self.root_path / "dbt"


PROJECT_CONFIG = Config(
    root_path=Path(__file__).parent,
    project_name="dbt-exasol",
    plugins_for_nox_sessions=(StartDB, StopDB),
    # Python 3.14 is left out due to issues installing pyarrow
    # & a known issue in the ITDE & will be resolved in:
    # https://github.com/exasol/pyexasol/issues/285
    python_versions=("3.10", "3.11", "3.12", "3.13"),
    # Changes for 7.x and 2025.1.x have not yet been made. 7.x works for all tests,
    # except for the examples/UDFs. These will be resolved in:
    # https://github.com/exasol/pyexasol/issues/273
    exasol_versions=("8.29.13",),
)
