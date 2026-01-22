from __future__ import annotations

import argparse
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

import nox
from nox import Session
from exasol.toolbox.nox.tasks import *  # pylint: disable=wildcard-import disable=unused-wildcard-import
from exasol.toolbox.nox._shared import _context
from exasol.toolbox.nox.plugin import NoxTasks
from noxconfig import (
    DEFAULT_DB_VERSION,
    PROJECT_CONFIG,
    start_test_db,
    stop_test_db,
)

# default actions to be run if nothing is explicitly specified with the -s option
nox.options.sessions = ["format:fix"]

# Note: unit_tests, integration_tests, and coverage are overridden below to use
# tests/unit and tests/functional instead of the default test/unit and
# test/integration paths expected by exasol-toolbox
__all__ = [
    "unit_tests",
    "integration_tests",
    "coverage",
]


def _create_start_db_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nox -s start:db",
        usage="nox -s start:db -- [-h] [-t | --port {int} --db-version {str} --with-certificate]",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--port", default=8563, type=int, help="forward port for the Exasol DB"
    )
    parser.add_argument(
        "--db-version",
        default=DEFAULT_DB_VERSION,
        type=str,
        help="Exasol DB version to be used",
    )
    parser.add_argument(
        "--with-certificate",
        default=False,
        action="store_true",
        help="Add a certificate to the Exasol DB",
    )
    return parser


@nox.session(name="db:start", python=False)
def start_db(session: Session) -> None:
    """Start a test database"""
    parser = _create_start_db_parser()
    args = parser.parse_args(session.posargs)
    start_test_db(
        session=session,
        port=args.port,
        db_version=args.db_version,
        with_certificate=args.with_certificate,
    )


@nox.session(name="db:stop", python=False)
def stop_db(session: Session) -> None:
    """Stop the test database"""
    stop_test_db(session=session)


def _test_command(
    path: Path, config: Any, context: MutableMapping[str, Any]
) -> list[str]:
    """Build the pytest command with optional coverage."""
    coverage_command = (
        [
            "coverage",
            "run",
            "-a",
            f"--rcfile={config.root_path / 'pyproject.toml'}",
            "-m",
        ]
        if context.get("coverage", False)
        else []
    )
    pytest_command = ["pytest", "-v", f"{path}"]
    return coverage_command + pytest_command + context.get("fwd-args", [])


def _unit_tests(
    session: Session, config: Any, context: MutableMapping[str, Any]
) -> None:
    """Internal helper to run unit tests from tests/unit directory."""
    command = _test_command(config.root_path / "tests" / "unit", config, context)
    session.run(*command)


def _integration_tests(
    session: Session, config: Any, context: MutableMapping[str, Any]
) -> None:
    """Internal helper to run integration tests from tests/functional directory."""
    pm = NoxTasks.plugin_manager(config)

    # Run pre-integration test hook (starts test database)
    pm.hook.pre_integration_tests_hook(session=session, config=config, context=context)

    # Run integration tests from tests/functional directory
    command = _test_command(config.root_path / "tests" / "functional", config, context)
    session.run(*command)

    # Run post-integration test hook (stops test database)
    pm.hook.post_integration_tests_hook(session=session, config=config, context=context)


@nox.session(name="test:unit", python=False)
def unit_tests(session: Session) -> None:
    """
    Runs all unit tests from tests/unit directory.

    Custom override to use tests/unit instead of test/unit.

    Usage:
        nox -s test:unit
        nox -s test:unit -- --coverage
        nox -s test:unit -- -v -k test_specific
    """
    context = _context(session)
    _unit_tests(session, PROJECT_CONFIG, context)


@nox.session(name="test:integration", python=False)
def integration_tests(session: Session) -> None:
    """
    Runs all integration tests from tests/functional directory.

    Custom override to use tests/functional instead of test/integration.
    Maintains compatibility with exasol-toolbox pre/post hooks.

    Usage:
        nox -s test:integration
        nox -s test:integration -- --db-version 8.29.13
        nox -s test:integration -- --coverage
    """
    context = _context(session)
    _integration_tests(session, PROJECT_CONFIG, context)


@nox.session(name="test:coverage", python=False)
def coverage(session: Session) -> None:
    """
    Runs all tests (unit + integration) and reports the code coverage.

    Custom override to use tests/unit and tests/functional directories.

    Usage:
        nox -s test:coverage
        nox -s test:coverage -- --db-version 8.29.13
    """
    context = _context(session, coverage=True)

    # Remove any existing coverage file
    coverage_file = PROJECT_CONFIG.root_path / ".coverage"
    coverage_file.unlink(missing_ok=True)

    # Run unit tests with coverage
    _unit_tests(session, PROJECT_CONFIG, context)

    # Run integration tests with coverage
    _integration_tests(session, PROJECT_CONFIG, context)

    # Generate coverage report
    session.run("coverage", "report", "-m")
