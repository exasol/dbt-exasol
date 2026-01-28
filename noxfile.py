from __future__ import annotations

import argparse
import warnings
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

# Suppress FutureWarning about duplicate nox session registration
# We intentionally override toolbox sessions to customize test paths
warnings.filterwarnings("ignore", message=".*session.*already been registered.*", category=FutureWarning)

import nox
from exasol.toolbox.nox._shared import _context
from exasol.toolbox.nox.plugin import NoxTasks
from exasol.toolbox.nox.tasks import *  # pylint: disable=wildcard-import disable=unused-wildcard-import
from nox import Session

from noxconfig import (
    DEFAULT_DB_VERSION,
    PROJECT_CONFIG,
    start_test_db,
    stop_test_db,
)

# default actions to be run if nothing is explicitly specified with the -s option
nox.options.sessions = ["format:fix"]

# Note: unit_tests, integration_tests, coverage, and project:check sessions are
# intentionally overridden below to use tests/unit and tests/functional instead
# of the default test/unit and test/integration paths expected by exasol-toolbox


def _create_start_db_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nox -s start:db",
        usage="nox -s start:db -- [-h] [-t | --port {int} --db-version {str} --with-certificate]",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--port", default=8563, type=int, help="forward port for the Exasol DB")
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
    path: Path,
    config: Any,
    context: MutableMapping[str, Any],
    parallel_workers: int | None = None,
) -> list[str]:
    """Build the pytest command with optional coverage.

    Args:
        path: Path to test directory
        config: Project configuration
        context: Nox context with additional settings
        parallel_workers: Number of parallel workers for pytest-xdist.
                         None means use pytest.ini default. 0 means disable parallelism.
    """
    is_coverage = context.get("coverage", False)
    coverage_command = (
        [
            "coverage",
            "run",
            "-a",
            f"--rcfile={config.root_path / 'pyproject.toml'}",
            "-m",
        ]
        if is_coverage
        else []
    )
    pytest_command = ["pytest", "-v", f"{path}"]

    # When coverage is enabled, disable pytest-xdist parallelism (-n 0) because
    # 'coverage run' only measures the main process, not subprocess workers.
    # pytest-xdist with -n >= 1 spawns workers as subprocesses, causing 0% coverage.
    if is_coverage:
        pytest_command.extend(["-n", "0"])
    elif parallel_workers is not None:
        if parallel_workers == 0:
            # Disable parallelism explicitly
            pytest_command.extend(["-n", "0"])
        else:
            # Set specific number of workers
            pytest_command.extend(["-n", str(parallel_workers)])

    return coverage_command + pytest_command + context.get("fwd-args", [])


def _unit_tests(session: Session, config: Any, context: MutableMapping[str, Any]) -> None:
    """Internal helper to run unit tests from tests/unit directory.

    Unit tests run with 1 worker (sequential) for simpler debugging.
    """
    command = _test_command(config.root_path / "tests" / "unit", config, context, parallel_workers=1)
    session.run(*command)


def _integration_tests(session: Session, config: Any, context: MutableMapping[str, Any]) -> None:
    """Internal helper to run integration tests from tests/functional directory.

    Functional tests run with 32 parallel workers for maximum throughput.
    """
    pm = NoxTasks.plugin_manager(config)

    # Run pre-integration test hook (starts test database)
    pm.hook.pre_integration_tests_hook(session=session, config=config, context=context)

    # Run integration tests from tests/functional directory
    command = _test_command(config.root_path / "tests" / "functional", config, context, parallel_workers=32)
    session.run(*command)

    # Run post-integration test hook (stops test database)
    pm.hook.post_integration_tests_hook(session=session, config=config, context=context)


@nox.session(name="test:unit", python=False)  # type: ignore[no-redef]
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


@nox.session(name="test:integration", python=False)  # type: ignore[no-redef]
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


@nox.session(name="test:coverage", python=False)  # type: ignore[no-redef]
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


@nox.session(name="project:check", python=False)  # type: ignore[no-redef]
def check(session: Session) -> None:
    """
    Runs all available checks on the project.

    Custom override to use our local _coverage implementation with correct test paths.

    Usage:
        nox -s project:check
    """
    # Import required toolbox components
    from exasol.toolbox.nox._shared import (
        Mode,
        get_filtered_python_files,
        _version,
    )
    from exasol.toolbox.nox._format import _code_format
    from exasol.toolbox.nox._lint import (
        _pylint,
        _type_check,
    )

    context = _context(session, coverage=True)
    py_files = get_filtered_python_files(PROJECT_CONFIG.root_path)
    _version(session, Mode.Check)
    _code_format(session, Mode.Check, py_files)
    _pylint(session, py_files)
    _type_check(session, py_files)

    # Use our local coverage implementation instead of toolbox's
    # Remove any existing coverage file
    coverage_file = PROJECT_CONFIG.root_path / ".coverage"
    coverage_file.unlink(missing_ok=True)

    # Run unit tests with coverage
    _unit_tests(session, PROJECT_CONFIG, context)

    # Run integration tests with coverage
    _integration_tests(session, PROJECT_CONFIG, context)

    # Generate coverage report
    session.run("coverage", "report", "-m")


@nox.session(name="artifacts:copy", python=False)  # type: ignore[no-redef]
def artifacts_copy(session: Session) -> None:
    """
    Copy artifacts from CI jobs and generate coverage XML for SonarQube.

    Custom override to ensure coverage XML is generated after combining coverage files.

    Usage:
        nox -s artifacts:copy -- <artifacts_dir>
    """
    # Import the toolbox artifacts copy task
    # isort: skip_file
    from exasol.toolbox.nox.tasks import artifacts_copy as toolbox_artifacts_copy  # type: ignore[attr-defined] # noqa: E501

    # Run the original artifacts:copy from toolbox
    toolbox_artifacts_copy(session)  # type: ignore[operator]

    # Generate XML coverage report for SonarQube
    # The toolbox session combines .coverage files, now we need to convert to XML
    session.run(
        "coverage",
        "xml",
        "-o",
        "ci-coverage.xml",
        f"--rcfile={PROJECT_CONFIG.root_path / 'pyproject.toml'}",
    )
