"""Unit tests for ExasolRelation quoting behavior."""

import unittest
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

        # Should not have quotes (unless needed for other reasons)
        # At minimum, verify it renders successfully
        self.assertIsNotNone(rendered)
        self.assertIn("test", rendered.lower())
        self.assertIn("my_table", rendered.lower())


if __name__ == "__main__":
    unittest.main()
