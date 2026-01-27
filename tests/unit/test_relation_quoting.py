"""Unit tests for ExasolRelation quoting behavior."""

import unittest
from datetime import datetime

from dbt.adapters.base.relation import EventTimeFilter

from dbt.adapters.exasol import ExasolRelation
from dbt.adapters.exasol.relation import ExasolQuotePolicy


class TestExasolRelationQuoting(unittest.TestCase):
    """Test that ExasolRelation respects quote_policy configuration."""

    def test_create_with_quote_policy_dict(self):
        """Test that create method accepts quote_policy as a dict."""
        # Create a relation with quoting enabled
        quote_policy = {
            "database": False,
            "schema": True,
            "identifier": True,
        }

        relation = ExasolRelation.create(
            schema="TEST",
            identifier="order",
            quote_policy=quote_policy,
        )

        # Verify the quote_policy was applied
        self.assertTrue(relation.quote_policy.schema)
        self.assertTrue(relation.quote_policy.identifier)
        self.assertFalse(relation.quote_policy.database)

    def test_create_with_default_quote_policy(self):
        """Test that create method uses default quote_policy when not provided."""
        relation = ExasolRelation.create(
            schema="TEST",
            identifier="my_table",
        )

        # Default quote policy should have all False
        self.assertFalse(relation.quote_policy.schema)
        self.assertFalse(relation.quote_policy.identifier)
        self.assertFalse(relation.quote_policy.database)

    def test_create_preserves_all_kwargs(self):
        """Test that create method preserves all kwargs including quote_policy."""
        quote_policy = {
            "schema": True,
            "identifier": False,
        }

        relation = ExasolRelation.create(
            schema="my_schema",
            identifier="my_table",
            quote_policy=quote_policy,
        )

        # Verify schema and identifier are set
        self.assertEqual(relation.schema, "my_schema")
        self.assertEqual(relation.identifier, "my_table")

        # Verify quote_policy was applied
        self.assertTrue(relation.quote_policy.schema)
        self.assertFalse(relation.quote_policy.identifier)

    def test_render_with_quoting_enabled(self):
        """Test that relation renders with quotes when quote_policy is enabled."""
        quote_policy = {
            "schema": True,
            "identifier": True,
        }

        relation = ExasolRelation.create(
            schema="TEST",
            identifier="order",
            quote_policy=quote_policy,
        )

        # Render the relation
        rendered = str(relation)

        # Should contain quotes around schema and identifier
        self.assertIn('"TEST"', rendered)
        self.assertIn('"order"', rendered)

    def test_render_without_quoting(self):
        """Test that relation renders without quotes when quote_policy is disabled."""
        quote_policy = {
            "schema": False,
            "identifier": False,
        }

        relation = ExasolRelation.create(
            schema="test",
            identifier="my_table",
            quote_policy=quote_policy,
        )

        # Render the relation
        rendered = str(relation)

        # Verify it renders successfully with the expected values
        self.assertIsNotNone(rendered)
        self.assertIn("test", rendered.lower())
        self.assertIn("my_table", rendered.lower())

        # Explicit negative assertions: quotes should NOT be present
        self.assertNotIn('"test"', rendered)
        self.assertNotIn('"my_table"', rendered)

    def test_create_with_quote_policy_object(self):
        """Test that create method accepts quote_policy as an ExasolQuotePolicy instance."""
        quote_policy = ExasolQuotePolicy(
            database=False,
            schema=True,
            identifier=True,
        )

        relation = ExasolRelation.create(
            schema="TEST",
            identifier="order",
            quote_policy=quote_policy,
        )

        # Verify the quote_policy was applied
        self.assertTrue(relation.quote_policy.schema)
        self.assertTrue(relation.quote_policy.identifier)
        self.assertFalse(relation.quote_policy.database)

        # Verify rendering respects the policy
        rendered = str(relation)
        self.assertIn('"TEST"', rendered)
        self.assertIn('"order"', rendered)

    def test_render_with_all_quoting_enabled(self):
        """Test that all three components are quoted when quote_policy enables all."""
        quote_policy = {
            "database": True,
            "schema": True,
            "identifier": True,
        }

        relation = ExasolRelation.create(
            database="DB",
            schema="TEST",
            identifier="order",
            quote_policy=quote_policy,
        )

        # Render the relation
        rendered = str(relation)

        # All components should be quoted
        self.assertIn('"TEST"', rendered)
        self.assertIn('"order"', rendered)

    def test_partial_quote_policy_override(self):
        """Test partial quoting: schema quoted but identifier not quoted.

        This mirrors the functional test's order_overwrite scenario where
        schema quoting is inherited (true) but identifier is overridden (false).
        """
        quote_policy = {
            "schema": True,
            "identifier": False,
        }

        relation = ExasolRelation.create(
            schema="TEST",
            identifier="seed_order",
            quote_policy=quote_policy,
        )

        # Render the relation
        rendered = str(relation)

        # Schema should be quoted
        self.assertIn('"TEST"', rendered)

        # Identifier should NOT be quoted
        self.assertNotIn('"seed_order"', rendered)
        self.assertIn("seed_order", rendered)

    def test_reserved_keyword_identifier_quoting(self):
        """Test that SQL reserved keywords as identifiers are properly quoted."""
        reserved_keywords = ["order", "select", "from", "where", "group", "table"]

        for keyword in reserved_keywords:
            with self.subTest(keyword=keyword):
                quote_policy = {
                    "schema": True,
                    "identifier": True,
                }

                relation = ExasolRelation.create(
                    schema="TEST",
                    identifier=keyword,
                    quote_policy=quote_policy,
                )

                # Render the relation
                rendered = str(relation)

                # Identifier should be quoted
                self.assertIn(f'"{keyword}"', rendered)


class TestRenderEventTimeFiltered(unittest.TestCase):
    """Test the _render_event_time_filtered method."""

    def setUp(self):
        """Create a relation for testing."""
        self.relation = ExasolRelation.create(
            schema="test",
            identifier="my_table",
        )

    def test_render_event_time_filtered_with_start_and_end(self):
        """Test _render_event_time_filtered with both start and end times."""
        event_filter = EventTimeFilter(
            field_name="created_at",
            start=datetime(2024, 1, 1, 10, 30, 0),
            end=datetime(2024, 12, 31, 23, 59, 59),
        )
        result = self.relation._render_event_time_filtered(event_filter)
        expected = "created_at >= TIMESTAMP '2024-01-01 10:30:00' " "and created_at < TIMESTAMP '2024-12-31 23:59:59'"
        self.assertEqual(result, expected)

    def test_render_event_time_filtered_with_start_only(self):
        """Test _render_event_time_filtered with only start time."""
        event_filter = EventTimeFilter(
            field_name="updated_at",
            start=datetime(2024, 6, 15, 12, 0, 0),
            end=None,
        )
        result = self.relation._render_event_time_filtered(event_filter)
        self.assertEqual(result, "updated_at >= TIMESTAMP '2024-06-15 12:00:00'")

    def test_render_event_time_filtered_with_end_only(self):
        """Test _render_event_time_filtered with only end time."""
        event_filter = EventTimeFilter(
            field_name="event_time",
            start=None,
            end=datetime(2024, 3, 20, 8, 45, 30),
        )
        result = self.relation._render_event_time_filtered(event_filter)
        self.assertEqual(result, "event_time < TIMESTAMP '2024-03-20 08:45:30'")

    def test_render_event_time_filtered_with_neither(self):
        """Test _render_event_time_filtered with neither start nor end time."""
        event_filter = EventTimeFilter(
            field_name="timestamp",
            start=None,
            end=None,
        )
        result = self.relation._render_event_time_filtered(event_filter)
        self.assertEqual(result, "")


class TestRenderLimitedAlias(unittest.TestCase):
    """Test the _render_limited_alias method."""

    def test_render_limited_alias_with_require_alias_true(self):
        """Test _render_limited_alias returns alias when require_alias is True."""
        relation = ExasolRelation.create(
            schema="test",
            identifier="my_table",
            require_alias=True,
        )
        result = relation._render_limited_alias()
        self.assertEqual(result, " dbt_limit_subq_my_table")

    def test_render_limited_alias_with_require_alias_false(self):
        """Test _render_limited_alias returns empty string when require_alias is False."""
        relation = ExasolRelation.create(
            schema="test",
            identifier="my_table",
            require_alias=False,
        )
        result = relation._render_limited_alias()
        self.assertEqual(result, "")


class TestRenderSubqueryAlias(unittest.TestCase):
    """Test the _render_subquery_alias method."""

    def test_render_subquery_alias_with_require_alias_true(self):
        """Test _render_subquery_alias returns alias when require_alias is True."""
        relation = ExasolRelation.create(
            schema="test",
            identifier="my_table",
            require_alias=True,
        )
        result = relation._render_subquery_alias("filtered")
        self.assertEqual(result, " AS dbt_filtered_subq_my_table")

    def test_render_subquery_alias_with_require_alias_false(self):
        """Test _render_subquery_alias returns empty string when require_alias is False."""
        relation = ExasolRelation.create(
            schema="test",
            identifier="my_table",
            require_alias=False,
        )
        result = relation._render_subquery_alias("filtered")
        self.assertEqual(result, "")


class TestAddEphemeralPrefix(unittest.TestCase):
    """Test the add_ephemeral_prefix static method."""

    def test_add_ephemeral_prefix(self):
        """Test that add_ephemeral_prefix adds the correct CTE prefix."""
        result = ExasolRelation.add_ephemeral_prefix("my_model")
        self.assertEqual(result, "dbt__CTE__my_model")

    def test_add_ephemeral_prefix_empty_name(self):
        """Test add_ephemeral_prefix with empty string."""
        result = ExasolRelation.add_ephemeral_prefix("")
        self.assertEqual(result, "dbt__CTE__")

    def test_add_ephemeral_prefix_special_chars(self):
        """Test add_ephemeral_prefix with special characters in name."""
        result = ExasolRelation.add_ephemeral_prefix("model_with_underscores")
        self.assertEqual(result, "dbt__CTE__model_with_underscores")


if __name__ == "__main__":
    unittest.main()
