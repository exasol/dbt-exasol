from __future__ import annotations

from pathlib import Path

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
    with_certificate: bool = False,
) -> None:
    # For Docker in a VM setup, refer to the ``doc/user_guide/developer_guide.rst``
    command = [
        "direnv exec . devbox run itde",
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
        "8GB",
    ]
    if with_certificate:
        command.append(
            "--create-certificates",
        )

    session.run(*command, external=True)

    # Note: Test role setup is now handled by pytest fixture in tests/conftest.py
    # This ensures it runs for both nox and pure pytest calls


def stop_test_db(session: Session) -> None:
    session.run("docker", "kill", CONTAINER_NAME, external=True)


class StartDB:
    @hookimpl
    def pre_integration_tests_hook(self, session, config, context):
        port = context.get("port", DEFAULT_PORT)
        # Override the default 7.1.9 from toolbox if not explicitly set
        db_version = context.get("db_version")
        if db_version == "7.1.9":  # toolbox default
            db_version = DEFAULT_DB_VERSION
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

    @computed_field  # type: ignore[misc]
    @property
    def version_filepath(self) -> Path:
        """
        Override version file path to avoid shadowing dbt-core's dbt/version.py.
        Move version.py to dbt/adapters/exasol/ to keep it as part of the adapter.
        """
        return self.root_path / "dbt" / "adapters" / "exasol" / "version.py"


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
