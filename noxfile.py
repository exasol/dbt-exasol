from __future__ import annotations

import argparse
import shutil

import nox
from exasol.toolbox.nox._format import _code_format
from exasol.toolbox.nox._lint import (
    _pylint,
    _type_check,
)
from exasol.toolbox.nox._shared import (
    Mode,
    _context,
    _version,
    get_filtered_python_files,
)
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


@nox.session(name="artifacts:copy", python=False)  # type: ignore[no-redef]
def artifacts_copy(session: Session) -> None:
    """
    Copy artifacts from CI jobs and generate coverage XML for SonarQube.

    Usage:
        nox -s artifacts:copy -- <artifacts_dir>
    """
    # Parse artifacts directory argument
    artifacts_dir = session.posargs[0] if session.posargs else "artifacts"
    artifacts_path = PROJECT_CONFIG.root_path / artifacts_dir

    # Find all coverage files from all Python versions (unit and integration tests)
    unit_coverage = list(artifacts_path.glob("coverage-python*/.coverage"))
    integration_coverage = list(artifacts_path.glob("integration-coverage-python*/.coverage"))
    coverage_files = unit_coverage + integration_coverage

    if not coverage_files:
        session.error(f"No coverage files found in {artifacts_path}")

    session.log(f"Found {len(coverage_files)} coverage file(s)")

    # Combine all coverage files from all Python versions
    session.run(
        "coverage",
        "combine",
        "--keep",
        f"--rcfile={PROJECT_CONFIG.root_path / 'pyproject.toml'}",
        *[str(f) for f in coverage_files],
    )

    # Copy lint and security artifacts from Python 3.10 (they're identical across versions)
    lint_txt = artifacts_path / "lint-python3.10" / ".lint.txt"
    lint_json = artifacts_path / "lint-python3.10" / ".lint.json"
    security_json = artifacts_path / "security-python3.10" / ".security.json"

    for artifact_file in [lint_txt, lint_json, security_json]:
        if artifact_file.exists():
            session.log(f"Copying {artifact_file.name}")
            shutil.copy(str(artifact_file), str(PROJECT_CONFIG.root_path))

    # Generate coverage report
    session.run(
        "coverage",
        "report",
        "-m",
        f"--rcfile={PROJECT_CONFIG.root_path / 'pyproject.toml'}",
    )

    # Generate XML coverage report for SonarQube
    session.run(
        "coverage",
        "xml",
        "-o",
        "ci-coverage.xml",
        f"--rcfile={PROJECT_CONFIG.root_path / 'pyproject.toml'}",
    )


@nox.session(name="sonar:check", python=False)  # type: ignore[no-redef]
def sonar_check(session: Session) -> None:
    """
    Upload artifacts to sonar for analysis.

    Usage:
        nox -s sonar:check
    """
    import os

    sonar_token = os.getenv("SONAR_TOKEN")
    if not sonar_token:
        session.error("SONAR_TOKEN environment variable is not set")

    # Build pysonar command
    # Note: Most settings are in sonar-project.properties file
    command = [
        "pysonar",
        "--sonar-token",
        sonar_token,
    ]

    session.log(f"Running pysonar")
    session.run(*command)


# Override test sessions to use project-specific test paths
# (tests/unit and tests/functional instead of test/unit and test/integration)


def _run_unit_tests(session: Session, context) -> None:
    """Helper to run unit tests with the correct path."""
    test_path = PROJECT_CONFIG.root_path / "tests" / "unit"
    if context["coverage"]:
        command = [
            "pytest",
            "-v",
            f"--cov=dbt",
            "--cov-append",
            f"--cov-config={PROJECT_CONFIG.root_path / 'pyproject.toml'}",
            str(test_path),
        ] + context["fwd-args"]
    else:
        command = ["pytest", "-v", str(test_path)] + context["fwd-args"]
    session.run(*command)


def _run_integration_tests(session: Session, context) -> None:
    """Helper to run integration/functional tests with the correct path."""
    pm = NoxTasks.plugin_manager(PROJECT_CONFIG)
    pm.hook.pre_integration_tests_hook(session=session, config=PROJECT_CONFIG, context=context)
    test_path = PROJECT_CONFIG.root_path / "tests" / "functional"

    # Check if -n flag is already in fwd-args, if not add -n 8 for parallel execution
    has_n_flag = any(arg.startswith("-n") or arg.startswith("--numprocesses") for arg in context["fwd-args"])
    parallel_args = [] if has_n_flag else ["-n8"]

    if context["coverage"]:
        command = (
            [
                "pytest",
                "-v",
                f"--cov=dbt",
                "--cov-append",
                f"--cov-config={PROJECT_CONFIG.root_path / 'pyproject.toml'}",
            ]
            + parallel_args
            + [str(test_path)]
            + context["fwd-args"]
        )
    else:
        command = ["pytest", "-v"] + parallel_args + [str(test_path)] + context["fwd-args"]
    session.run(*command)
    pm.hook.post_integration_tests_hook(session=session, config=PROJECT_CONFIG, context=context)


@nox.session(name="test:unit", python=False)  # type: ignore[no-redef]
def unit_tests(session: Session) -> None:
    """Runs all unit tests"""
    context = _context(session)
    _run_unit_tests(session, context)


@nox.session(name="test:integration", python=False)  # type: ignore[no-redef]
def integration_tests(session: Session) -> None:
    """Runs all integration/functional tests"""
    context = _context(session)
    _run_integration_tests(session, context)


@nox.session(name="test:coverage", python=False)  # type: ignore[no-redef]
def coverage(session: Session) -> None:
    """Runs all tests (unit + integration) and reports the code coverage"""
    context = _context(session, coverage=True)
    coverage_file = PROJECT_CONFIG.root_path / ".coverage"
    coverage_file.unlink(missing_ok=True)
    _run_unit_tests(session, context)
    _run_integration_tests(session, context)
    session.run("coverage", "report", "-m")


@nox.session(name="project:check", python=False)  # type: ignore[no-redef]
def project_check(session: Session) -> None:
    """Runs all available checks on the project"""
    context = _context(session, coverage=True)
    py_files = get_filtered_python_files(PROJECT_CONFIG.root_path)
    coverage_file = PROJECT_CONFIG.root_path / ".coverage"
    coverage_file.unlink(missing_ok=True)
    _version(session, Mode.Check)
    _code_format(session, Mode.Check, py_files)
    _pylint(session, py_files)
    _type_check(session, py_files)
    _run_unit_tests(session, context)
    _run_integration_tests(session, context)
    session.run("coverage", "report", "-m")
