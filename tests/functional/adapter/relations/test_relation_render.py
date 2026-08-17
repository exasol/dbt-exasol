# pylint: disable=protected-access,duplicate-code
"""Functional tests for ``ExasolRelation`` rendering methods.

Covers branches that are unreachable through the standard dbt materialisation
flow because ``require_alias`` is always ``True`` and ``event_time_filter``
is only set by microbatch / sample mode, which always passes both bounds.

Coverage target (relation.py):
  83   (_render_limited_alias -> "" when require_alias=False)
  95   (format_ts returns None for None input)
  107-108  (start-only event_time_filter)
  109-110  (end-only event_time_filter)
  111  (no bounds -> empty string)
  124  (_render_subquery_alias -> "" when require_alias=False)
"""

from datetime import datetime

from dbt.adapters.base.relation import EventTimeFilter


class TestRelationRenderLimitedAlias:
    """Exercise ``_render_limited_alias`` and ``_render_subquery_alias``
    with ``require_alias=False``, which never occurs during normal dbt
    operations (the base default is ``True`` and Exasol inherits it).
    """

    def test_no_alias_when_require_alias_false(self, project):
        """Lines 83, 124: both alias methods return empty strings."""
        rel = project.adapter.Relation.create(
            schema="my_schema",
            identifier="my_table",
            type=project.adapter.Relation.Table,
            require_alias=False,
        )

        # _render_limited_alias → ""
        assert rel._render_limited_alias() == ""

        # _render_subquery_alias → ""
        assert rel._render_subquery_alias("et_filter") == ""

    def test_no_alias_appears_in_render_limited_output(self, project):
        """When require_alias=False, render_limited omits the alias suffix."""
        rel = project.adapter.Relation.create(
            schema="my_schema",
            identifier="my_table",
            type=project.adapter.Relation.Table,
            limit=10,
            require_alias=False,
        )
        rendered = rel.render_limited()
        # No alias appended — should end with the parenthesis from the limit clause
        assert rendered.endswith("limit 10)")
        assert "dbt_limit_subq" not in rendered

    def test_alias_when_require_alias_true(self, project):
        """Sanity-check: the default (True) still produces an alias."""
        rel = project.adapter.Relation.create(
            schema="my_schema",
            identifier="my_table",
            type=project.adapter.Relation.Table,
            limit=10,
        )
        assert "dbt_limit_subq_my_table" in rel.render_limited()


class TestRelationEventTimeFilter:
    """Exercise ``_render_event_time_filtered`` for Exasol's timezone-free format.

    dbt's base implementation emits ``'2025-01-01 00:00:00+00:00'``, which
    Exasol rejects. The Exasol override strips the timezone suffix.
    """

    def test_both_bounds(self, project):
        """Line 107-108 (via 95): both start and end produce a BETWEEN-like clause."""
        f = EventTimeFilter(
            field_name="event_time",
            start=datetime(2025, 1, 1, 0, 0, 0),
            end=datetime(2025, 1, 2, 0, 0, 0),
        )
        rel = project.adapter.Relation.create(
            schema="my_schema",
            identifier="my_table",
            type=project.adapter.Relation.Table,
        )
        result = rel._render_event_time_filtered(f)
        assert "TIMESTAMP '2025-01-01 00:00:00'" in result
        assert "TIMESTAMP '2025-01-02 00:00:00'" in result
        assert ">=" in result
        assert "<" in result
        # Must NOT contain the timezone suffix that the base class adds
        assert "+00:00" not in result
        assert "+" not in result  # no stray timezone

    def test_start_only(self, project):
        """Lines 107-108: only start bound set."""
        f = EventTimeFilter(
            field_name="event_time",
            start=datetime(2025, 3, 15, 12, 30, 0),
        )
        rel = project.adapter.Relation.create(
            schema="my_schema",
            identifier="my_table",
            type=project.adapter.Relation.Table,
        )
        result = rel._render_event_time_filtered(f)
        assert ">=" in result
        assert "<" not in result
        assert "TIMESTAMP '2025-03-15 12:30:00'" in result

    def test_end_only(self, project):
        """Lines 109-110: only end bound set."""
        f = EventTimeFilter(
            field_name="event_time",
            end=datetime(2025, 6, 30, 23, 59, 59),
        )
        rel = project.adapter.Relation.create(
            schema="my_schema",
            identifier="my_table",
            type=project.adapter.Relation.Table,
        )
        result = rel._render_event_time_filtered(f)
        assert ">" not in result
        assert "<" in result
        assert "TIMESTAMP '2025-06-30 23:59:59'" in result

    def test_no_bounds(self, project):
        """Line 111: neither bound set → empty string."""
        f = EventTimeFilter(field_name="event_time")
        rel = project.adapter.Relation.create(
            schema="my_schema",
            identifier="my_table",
            type=project.adapter.Relation.Table,
        )
        result = rel._render_event_time_filtered(f)
        assert result == ""

    def test_format_ts_returns_none(self, project):
        """Line 95: format_ts(None) returns None."""
        f = EventTimeFilter(field_name="event_time")
        rel = project.adapter.Relation.create(
            schema="my_schema",
            identifier="my_table",
            type=project.adapter.Relation.Table,
        )
        # Internal coverage: format_ts(None) is called for both start and end
        result = rel._render_event_time_filtered(f)
        assert result == ""
