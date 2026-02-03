from __future__ import annotations

import argparse
import shutil
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


def _is_xdist_available() -> bool:
    """Check if pytest-xdist is available."""
    import importlib.util

    return importlib.util.find_spec("xdist") is not None


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

    # Only add -n argument if pytest-xdist is available
    xdist_available = _is_xdist_available()

    # When coverage is enabled, disable pytest-xdist parallelism (-n 0) because
    # 'coverage run' only measures the main process, not subprocess workers.
    # pytest-xdist with -n >= 1 spawns workers as subprocesses, causing 0% coverage.
    if is_coverage and xdist_available:
        pytest_command.extend(["-n", "0"])
    elif parallel_workers is not None and xdist_available:
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
    from exasol.toolbox.nox._format import _code_format
    from exasol.toolbox.nox._lint import (
        _pylint,
        _type_check,
    )
    from exasol.toolbox.nox._shared import (
        Mode,
        _version,
        get_filtered_python_files,
    )

    context = _context(session, coverage=True)
    all_py_files = get_filtered_python_files(PROJECT_CONFIG.root_path)
    # Exclude tests directory from linting
    py_files = [f for f in all_py_files if "/tests/" not in str(f)]
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

    Custom override to ensure ALL coverage files from all Python versions are combined.

    Usage:
        nox -s artifacts:copy -- <artifacts_dir>
    """
    # Parse artifacts directory argument
    artifacts_dir = session.posargs[0] if session.posargs else "artifacts"
    artifacts_path = PROJECT_CONFIG.root_path / artifacts_dir

    # Find all coverage files from all Python versions
    coverage_files = list(artifacts_path.glob("coverage-python*/.coverage"))

    if not coverage_files:
        session.error(f"No coverage files found in {artifacts_path}")

    session.log(f"Found {len(coverage_files)} coverage file(s): {[str(f) for f in coverage_files]}")

    # Debug: Show paths in first coverage file before combining
    import sqlite3

    first_cov = coverage_files[0]
    conn = sqlite3.connect(first_cov)
    cursor = conn.cursor()

    # Count total files
    cursor.execute("SELECT COUNT(*) FROM file")
    total_files = cursor.fetchone()[0]
    session.log(f"Total files in {first_cov}: {total_files}")

    # Show all paths (not just first 5) to understand what's being measured
    cursor.execute("SELECT path FROM file")
    session.log(f"All paths in {first_cov}:")
    for row in cursor.fetchall():
        session.log(f"  {row[0]}")
    conn.close()

    # Combine all coverage files from all Python versions
    # Use --rcfile to ensure relative_files and paths settings are applied
    session.run(
        "coverage",
        "combine",
        "--keep",
        f"--rcfile={PROJECT_CONFIG.root_path / 'pyproject.toml'}",
        *[str(f) for f in coverage_files],
    )

    # Debug: Show paths in combined coverage file
    combined_cov = PROJECT_CONFIG.root_path / ".coverage"
    conn = sqlite3.connect(combined_cov)
    cursor = conn.cursor()

    # Count total files after combining
    cursor.execute("SELECT COUNT(*) FROM file")
    total_files = cursor.fetchone()[0]
    session.log(f"Total files in combined .coverage: {total_files}")

    # Show all paths to see if path remapping worked
    cursor.execute("SELECT path FROM file")
    session.log("All paths in combined .coverage:")
    for row in cursor.fetchall():
        session.log(f"  {row[0]}")
    conn.close()

    # Copy lint and security artifacts from Python 3.10 (they're identical across versions)
    lint_txt = artifacts_path / "lint-python3.10" / ".lint.txt"
    lint_json = artifacts_path / "lint-python3.10" / ".lint.json"
    security_json = artifacts_path / "security-python3.10" / ".security.json"

    for artifact_file in [lint_txt, lint_json, security_json]:
        if artifact_file.exists():
            session.log(f"Copying file {artifact_file}")
            shutil.copy(str(artifact_file), str(PROJECT_CONFIG.root_path))

    # Debug: Show coverage report before generating XML
    session.log("Coverage report (before XML generation):")
    session.run(
        "coverage",
        "report",
        "-m",
        f"--rcfile={PROJECT_CONFIG.root_path / 'pyproject.toml'}",
    )

    # Generate XML coverage report for SonarQube
    # The combined .coverage file now contains data from all Python versions
    session.run(
        "coverage",
        "xml",
        "-o",
        "ci-coverage.xml",
        f"--rcfile={PROJECT_CONFIG.root_path / 'pyproject.toml'}",
    )

    # Debug: Show first 30 lines of generated XML
    xml_file = PROJECT_CONFIG.root_path / "ci-coverage.xml"
    if xml_file.exists():
        session.log("Generated ci-coverage.xml (first 30 lines):")
        with open(xml_file) as f:
            for i, line in enumerate(f):
                if i >= 30:
                    break
                session.log(f"  {line.rstrip()}")


@nox.session(name="sonar:check", python=False)  # type: ignore[no-redef]
def sonar_check(session: Session) -> None:
    """
    Upload artifacts to sonar for analysis.

    Custom override: Skip _prepare_coverage_xml() because our artifacts:copy
    session already generates ci-coverage.xml with correct path mappings.

    The default toolbox implementation calls _prepare_coverage_xml() which
    regenerates ci-coverage.xml with --include filters that don't match
    the absolute paths stored in the .coverage database from CI runners,
    resulting in 0% coverage being reported to SonarQube.

    Usage:
        nox -s sonar:check
    """
    import os
    from pathlib import Path

    sonar_token = os.getenv("SONAR_TOKEN")
    if not sonar_token:
        session.error("SONAR_TOKEN environment variable is not set")

    # Build pysonar command manually to use relative paths
    # This ensures coverage XML paths match what SonarCloud expects
    # Note: Most settings are in sonar-project.properties file
    command = [
        "pysonar",
        "--sonar-token",
        sonar_token,
    ]

    session.log(f"Running pysonar with command: {' '.join(str(c) for c in command)}")
    session.run(*command)
