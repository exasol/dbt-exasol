"""Unit tests for the exasol__get_empty_subquery_sql Jinja2 macro.

Regression coverage for a class of bug that is invisible to Jinja rendering but
fatal at execution time: Exasol accepts exactly *one* statement per request.

A model may declare a ``sql_header`` via ``{% call set_sql_header(config) %}``.
dbt-core's ``default__get_empty_subquery_sql`` concatenates that header directly
in front of the ``select``, which works on databases that accept multi-statement
requests. On Exasol a statement-style header such as::

    alter session set TIME_ZONE = 'Asia/Kolkata';

concatenated with the following ``select`` raises::

    syntax error, unexpected SELECT_, expecting END_OF_INPUT_

The adapter therefore appends the ``|SEPARATEMEPLEASE|`` sentinel after a
statement-style header so that ``ExasolCursor.execute`` submits the header and
the select as two requests on the same connection (session settings still apply).

Headers that are only a syntactic *prefix* of the query rather than a standalone
statement -- most notably a leading ``with ... as (...)`` CTE -- must stay inline
and must NOT be split.

Unlike the sibling macro unit tests, this module parses the macro out of the real
``adapters.sql`` so the test cannot silently drift from the shipped macro.
"""

import re
import unittest
from pathlib import Path

from jinja2 import Environment

MACRO_NAME = "exasol__get_empty_subquery_sql"
SEPARATOR = "|SEPARATEMEPLEASE|"

ADAPTERS_SQL = Path(__file__).resolve().parents[2] / "dbt" / "include" / "exasol" / "macros" / "adapters.sql"


def normalize_whitespace(value: str) -> str:
    """Collapse runs of whitespace so assertions ignore Jinja indentation."""
    return re.sub(r"\s+", " ", value).strip()


def load_macro_source(name: str) -> str:
    """Extract a single ``{% macro name(...) %}...{% endmacro %}`` block.

    Reading the shipped macro file instead of copying the macro body keeps this
    regression test bound to the real implementation.
    """
    source = ADAPTERS_SQL.read_text(encoding="utf-8")
    match = re.search(
        r"\{%-?\s*macro\s+" + re.escape(name) + r"\(.*?\{%-?\s*endmacro\s*-?%\}",
        source,
        re.DOTALL,
    )
    if match is None:  # pragma: no cover - guards against a macro rename
        raise AssertionError(f"macro {name} not found in {ADAPTERS_SQL}")
    return match.group(0)


class TestExasolGetEmptySubquerySql(unittest.TestCase):
    """Test exasol__get_empty_subquery_sql output."""

    @classmethod
    def setUpClass(cls):
        cls.macro_source = load_macro_source(MACRO_NAME)

    def _render(self, select_sql: str, select_sql_header=None) -> str:
        env = Environment()  # nosec B701 - SQL generation, not HTML
        template = env.from_string(self.macro_source + "{{ " + MACRO_NAME + "(sql, header) }}")
        return template.render(sql=select_sql, header=select_sql_header)

    def test_no_header_is_a_single_statement(self):
        """Without a header the macro must emit exactly one statement."""
        rendered = self._render("select 1 as id")

        self.assertNotIn(SEPARATOR, rendered)
        self.assertEqual(
            normalize_whitespace(rendered),
            "select * from ( select 1 as id ) dbt_sbq_tmp where false limit 0",
        )

    def test_zero_row_guarantee(self):
        """The empty subquery must never scan data."""
        rendered = normalize_whitespace(self._render("select 1 as id"))

        self.assertIn("where false", rendered)
        self.assertIn("limit 0", rendered)

    def test_subquery_alias_is_not_underscore_prefixed(self):
        """Exasol rejects unquoted identifiers starting with `_`."""
        rendered = self._render("select 1 as id")

        self.assertIn("dbt_sbq_tmp", rendered)
        self.assertNotIn("__dbt_sbq", rendered)

    def test_statement_style_header_is_separated(self):
        """`alter session ...;` must be submitted as its own statement."""
        header = "alter session set TIME_ZONE = 'Asia/Kolkata';"
        rendered = self._render(
            "select session_parameter(current_session, 'TIME_ZONE') as column_name",
            header,
        )

        self.assertIn(SEPARATOR, rendered)
        header_part, select_part = rendered.split(SEPARATOR)
        self.assertEqual(normalize_whitespace(header_part), header)
        self.assertTrue(normalize_whitespace(select_part).startswith("select * from ("))
        self.assertNotIn(";", normalize_whitespace(select_part))

    def test_statement_style_header_with_trailing_whitespace_is_separated(self):
        """A trailing newline/spaces after the `;` must not defeat detection."""
        rendered = self._render(
            "select 1 as id",
            "\nalter session set TIME_ZONE = 'Asia/Kolkata';\n",
        )

        self.assertIn(SEPARATOR, rendered)

    def test_multi_statement_header_is_separated_once(self):
        """Several `alter session` statements stay in one header chunk.

        ExasolCursor.execute splits on every sentinel, so the header chunk itself
        must not be split -- it is submitted as one request. This documents the
        current (working) behaviour for a header ending in `;`.
        """
        header = "alter session set TIME_ZONE = 'Asia/Kolkata'; alter session set QUERY_TIMEOUT = 10;"
        rendered = self._render("select 1 as id", header)

        self.assertEqual(rendered.count(SEPARATOR), 1)

    def test_cte_header_stays_inline(self):
        """A leading CTE is a query prefix, not a statement -- keep it inline."""
        header = "with variables as (\n    select 1 as my_variable\n)"
        rendered = self._render("select my_variable from variables", header)

        self.assertNotIn(SEPARATOR, rendered)
        self.assertEqual(
            normalize_whitespace(rendered),
            "with variables as ( select 1 as my_variable ) "
            "select * from ( select my_variable from variables ) dbt_sbq_tmp "
            "where false limit 0",
        )

    def test_header_precedes_the_select(self):
        """The header must never end up after the select."""
        for header in (
            "alter session set TIME_ZONE = 'Asia/Kolkata';",
            "with variables as (select 1 as my_variable)",
        ):
            with self.subTest(header=header):
                rendered = self._render("select 1 as id", header)
                self.assertLess(rendered.index(header.strip()[:5]), rendered.index("select * from"))


if __name__ == "__main__":
    unittest.main()
