"""Seed CSV line-ending hardening.

Exasol's ``IMPORT ... ROW SEPARATOR`` must match the bytes in the seed file. The
row separator used to be derived from the *client* OS (``os.linesep``), which says
nothing about the bytes on disk: git ``core.autocrlf``, Windows-authored seeds and
Linux CI routinely disagree. Both mismatches fail silently:

* CRLF file imported as ``LF`` -> a stray ``\\r`` is appended to the last column of
  every row.
* LF file imported as ``CRLF`` -> zero rows are loaded and ``dbt seed`` still
  reports success.

The adapter now detects the separator per seed file, so both conventions -- and a
mix of them within one project -- import correctly. An explicit ``row_separator``
in ``profiles.yml`` still wins, for backwards compatibility.
"""

import os

import pytest
from dbt.tests.util import run_dbt

# Written to disk as raw bytes by the fixture below so the line endings are exact
# on every platform, independent of Python's newline translation.
_HEADER = b"id,name"
_ROWS = (b"1,alice", b"2,bob")

SEED_LF = b"\n".join((_HEADER, *_ROWS)) + b"\n"
SEED_CRLF = b"\r\n".join((_HEADER, *_ROWS)) + b"\r\n"
# A CRLF file whose final row has no terminator: exercises the end-of-file path.
SEED_CRLF_NO_TRAILING = b"\r\n".join((_HEADER, *_ROWS))

SEED_FILES = {
    "seed_lf.csv": SEED_LF,
    "seed_crlf.csv": SEED_CRLF,
    "seed_crlf_no_trailing.csv": SEED_CRLF_NO_TRAILING,
}


class BaseSeedLineEndings:
    """Seeds a project containing both LF and CRLF fixtures."""

    @pytest.fixture(scope="class")
    def seeds(self):
        # Placeholder content only; `seed_files` below replaces it byte-for-byte.
        return {name: "id,name\n" for name in SEED_FILES}

    @pytest.fixture(scope="class")
    def seed_files(self, project):
        """Write the seed CSVs as exact bytes, bypassing newline translation."""
        for name, content in SEED_FILES.items():
            with open(os.path.join(project.project_root, "seeds", name), "wb") as handle:
                handle.write(content)
        return SEED_FILES

    @staticmethod
    def _rows(project, relation):
        return project.run_sql(
            f"select id, name from {project.test_schema}.{relation} order by id",
            fetch="all",
        )


class TestSeedLineEndingsAutoDetected(BaseSeedLineEndings):
    """With no `row_separator` configured, every convention imports correctly."""

    def test_all_line_endings_import_correctly(self, project, seed_files):
        assert len(run_dbt(["seed"])) == len(SEED_FILES)

        expected = [(1, "alice"), (2, "bob")]
        for relation in ("seed_lf", "seed_crlf", "seed_crlf_no_trailing"):
            rows = self._rows(project, relation)
            # A wrong separator yields either [] (LF file read as CRLF) or
            # trailing '\r' in the last column (CRLF file read as LF).
            assert rows == expected, f"{relation} imported as {rows}"

    def test_no_trailing_carriage_return(self, project, seed_files):
        """Pin the exact corruption from the original bug report."""
        run_dbt(["seed"])

        for relation in SEED_FILES:
            table = relation.removesuffix(".csv")
            rows = self._rows(project, table)
            assert rows, f"{table} imported zero rows"
            for _, name in rows:
                assert "\r" not in name, f"{table} kept a carriage return: {name!r}"


class TestExplicitRowSeparatorOverrides(BaseSeedLineEndings):
    """An explicit profiles.yml `row_separator` still wins over detection.

    This is the backwards-compatibility guard for projects that already set the
    value. ``CRLF`` is forced here, so the CRLF seeds load and the LF seed loads
    zero rows -- exactly the pre-fix behaviour.
    """

    @pytest.fixture(scope="class")
    def dbt_profile_target(self, dbt_profile_target):
        """Add `row_separator` to the target itself (not the profile root)."""
        return {**dbt_profile_target, "row_separator": "CRLF"}

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"seed_lf.csv": "id,name\n", "seed_crlf.csv": "id,name\n"}

    @pytest.fixture(scope="class")
    def seed_files(self, project):
        for name in ("seed_lf.csv", "seed_crlf.csv"):
            with open(os.path.join(project.project_root, "seeds", name), "wb") as handle:
                handle.write(SEED_FILES[name])
        return None

    def test_forced_separator_is_used(self, project, seed_files):
        assert len(run_dbt(["seed"])) == 2

        # The CRLF file matches the forced separator and imports correctly.
        assert self._rows(project, "seed_crlf") == [(1, "alice"), (2, "bob")]
        # The LF file does not, so it silently loads nothing. Asserting this
        # documents that the override is honored verbatim rather than "fixed".
        assert self._rows(project, "seed_lf") == []
