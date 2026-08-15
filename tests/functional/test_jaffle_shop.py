"""Functional smoke test for the upstream dbt-labs jaffle_shop_duckdb sample.

Rather than vendoring the sample project, this test clones the upstream
``jaffle_shop_duckdb`` repo (branch ``duckdb``) into a temporary directory,
applies the minimal set of Exasol-specific porting changes in memory, and runs
``dbt build`` against it. This keeps the test in sync with upstream and makes
the Exasol differences explicit.
"""

import subprocess
from pathlib import Path

import pytest
from dbt.tests.util import run_dbt

UPSTREAM_REPO = "https://github.com/dbt-labs/jaffle_shop_duckdb.git"
UPSTREAM_BRANCH = "duckdb"

# Exasol reserved words that the upstream sample uses as CTE aliases. ``source``
# and ``final`` are valid in DuckDB but rejected by the Exasol SQL parser.
_SQL_RENAMES = (
    ("with source as (", "with source_data as ("),
    ("from source", "from source_data"),
    ("final as (", "final_data as ("),
    ("select * from final", "select * from final_data"),
)

# Connection details come from the repository-root .env (loaded via mise/nox),
# so this profiles.yml stays free of hardcoded credentials.
_PROFILES_YML = """\
jaffle_shop:
  target: dev
  outputs:
    dev:
      type: exasol
      threads: 8
      dsn: "{{ env_var('DBT_DSN', 'localhost:8563') }}"
      user: "{{ env_var('DBT_USER', 'sys') }}"
      pass: "{{ env_var('DBT_PASS', 'exasol') }}"
      dbname: "DB"
      schema: "jaffle_shop"
      validate_server_certificate: false
"""


def _port_to_exasol(project_dir: Path) -> None:
    """Rewrite the cloned duckdb sample in-place so it runs on Exasol."""
    # 1. Rename reserved-word CTE aliases in every model.
    for sql_file in (project_dir / "models").rglob("*.sql"):
        text = sql_file.read_text(encoding="utf-8")
        for old, new in _SQL_RENAMES:
            text = text.replace(old, new)
        sql_file.write_text(text, encoding="utf-8")

    # 2. Replace the duckdb profile with an Exasol profile.
    #
    #    Note: `seeds/raw_orders.csv` ships with Windows line endings while the
    #    other seeds use Unix ones. No normalization is applied here on purpose --
    #    the adapter detects the row separator per seed file, so this sample doubles
    #    as a real-world regression test for mixed line endings in one project.
    (project_dir / "profiles.yml").write_text(_PROFILES_YML, encoding="utf-8")


@pytest.fixture(scope="session")
def jaffle_shop_project(tmp_path_factory):
    """Clone upstream jaffle_shop_duckdb and port it to Exasol.

    Session-scoped so the clone happens once per test session (per xdist worker).
    """
    base = tmp_path_factory.mktemp("jaffle-shop-exasol")
    project_dir = base / "jaffle_shop_duckdb"

    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", UPSTREAM_BRANCH, UPSTREAM_REPO, str(project_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to clone {UPSTREAM_REPO} (branch {UPSTREAM_BRANCH}): {result.stderr}")

    _port_to_exasol(project_dir)
    return project_dir


class TestJaffleShopSmoke:
    """The upstream jaffle-shop sample builds and its tests pass on Exasol."""

    def test_build(self, jaffle_shop_project: Path) -> None:
        """``dbt build --full-refresh`` succeeds (seeds + views + tables + tests)."""
        run_dbt(
            [
                "build",
                "--full-refresh",
                # In dbt-core >= 1.12, --project-dir/--profiles-dir are
                # subcommand options and must follow the command.
                "--project-dir",
                str(jaffle_shop_project),
                "--profiles-dir",
                str(jaffle_shop_project),
            ]
        )
