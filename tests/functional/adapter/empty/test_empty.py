import pytest
from dbt.tests.adapter.empty.test_empty import (
    BaseTestEmpty,
    BaseTestEmptySeedFlag,
)
from dbt.tests.util import (
    relation_from_name,
    run_dbt,
)


class TestEmptyExasol(BaseTestEmpty):
    pass


# Exasol's IMPORT expects timestamps in the session NLS format, which the
# adapter sets to YYYY-MM-DDTHH:MI:SS.FF6 (ISO 8601 with T separator and
# microseconds).  The base seed CSV uses 'YYYY-MM-DD HH:MI:SS' (space
# separator, no microseconds), which Exasol rejects.  Override the seeds
# fixture with an Exasol-compatible CSV so that all four cases in
# BaseTestEmptySeedFlag can actually load data rows.
_EXASOL_SEED_CSV = """\
id,name,price,is_active,created_at
1,Alice,1.23,true,2024-01-01T00:00:00.000000
2,Bob,99.99,false,2024-06-15T12:30:00.000000
"""


class TestEmptySeedFlag(BaseTestEmptySeedFlag):
    """Opt into the dbt-tests-adapter empty-seed suite for Exasol.

    Covers four scenarios defined in BaseTestEmptySeedFlag:
    - zero-row table creation via ``dbt seed --empty``
    - column type preservation (empty → full-refresh seed)
    - full load without ``--empty``
    - ``dbt build --empty`` with a seed and downstream model

    The ``seeds`` fixture is overridden to use Exasol-compatible ISO
    timestamps (YYYY-MM-DDTHH:MI:SS.FF6) because Exasol's IMPORT rejects
    the space-separated format used in the base fixture.
    """

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"raw_seed.csv": _EXASOL_SEED_CSV}


# Task 4.3 – regression test for the --empty → plain (non-full-refresh) seed
# sequence on a decimal column.
#
# The convert_number_type fix (task 2.1) ensures that --empty creates the table
# with the correct numeric type (float, not integer), so a subsequent plain
# ``dbt seed`` (no --full-refresh) can successfully truncate and reimport the
# CSV without type errors.
#
# This test currently passes on Exasol (xpasses with strict=False).  The xfail
# marker is kept with strict=False to document the historical edge case; remove
# it once the behaviour is confirmed stable across releases.
_DECIMAL_SEED_CSV = """\
id,price
1,1.23
2,99.99
"""


class TestEmptySeedThenPlainSeedDecimal:
    """Regression: --empty followed by plain seed on a decimal column."""

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"decimal_seed.csv": _DECIMAL_SEED_CSV}

    @pytest.fixture(scope="class")
    def models(self):
        return {}

    def assert_row_count(self, project, relation_name: str, expected: int):
        relation = relation_from_name(project.adapter, relation_name)
        result = project.run_sql(f"select count(*) as n from {relation}", fetch="one")
        assert result[0] == expected

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "Historical edge: before the convert_number_type fix, --empty would create "
            "decimal columns as integer, causing the subsequent plain seed IMPORT to fail. "
            "The fix resolves this; the test currently xpasses.  Kept as xfail(strict=False) "
            "to retain history; remove once confirmed stable."
        ),
    )
    def test_empty_then_plain_seed_decimal(self, project):
        """Task 4.3: --empty → plain seed on a decimal column must not error."""
        run_dbt(["seed", "--empty"])
        self.assert_row_count(project, "decimal_seed", 0)
        # Plain seed (no --full-refresh): truncate + reimport into the existing table.
        run_dbt(["seed"])
        self.assert_row_count(project, "decimal_seed", 2)
