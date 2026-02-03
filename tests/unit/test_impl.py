"""Unit tests for ExasolAdapter methods."""

import unittest
from unittest.mock import Mock

import agate
from dbt_common.exceptions import CompilationError

from dbt.adapters.exasol import ExasolAdapter


class TestIsValidIdentifier(unittest.TestCase):
    """Test is_valid_identifier static method."""

    def test_valid_identifier_alpha_start(self):
        """Test is_valid_identifier with alphabetic start."""
        self.assertTrue(ExasolAdapter.is_valid_identifier("table_name"))

    def test_valid_identifier_alphanumeric(self):
        """Test is_valid_identifier with alphanumeric characters."""
        self.assertTrue(ExasolAdapter.is_valid_identifier("table123"))

    def test_valid_identifier_with_underscore(self):
        """Test is_valid_identifier with underscore."""
        self.assertTrue(ExasolAdapter.is_valid_identifier("table_name_123"))

    def test_valid_identifier_with_hash(self):
        """Test is_valid_identifier with hash character."""
        self.assertTrue(ExasolAdapter.is_valid_identifier("table#name"))

    def test_valid_identifier_with_dollar(self):
        """Test is_valid_identifier with dollar character."""
        self.assertTrue(ExasolAdapter.is_valid_identifier("table$name"))

    def test_valid_identifier_single_char(self):
        """Test is_valid_identifier with single alphabetic character."""
        self.assertTrue(ExasolAdapter.is_valid_identifier("T"))

    def test_invalid_identifier_numeric_start(self):
        """Test is_valid_identifier returns False when starting with number."""
        self.assertFalse(ExasolAdapter.is_valid_identifier("123table"))

    def test_invalid_identifier_special_char_start(self):
        """Test is_valid_identifier returns False when starting with special char."""
        self.assertFalse(ExasolAdapter.is_valid_identifier("_table"))
        self.assertFalse(ExasolAdapter.is_valid_identifier("#table"))

    def test_invalid_identifier_invalid_special_chars(self):
        """Test is_valid_identifier returns False with invalid special characters."""
        self.assertFalse(ExasolAdapter.is_valid_identifier("table-name"))
        self.assertFalse(ExasolAdapter.is_valid_identifier("table.name"))
        self.assertFalse(ExasolAdapter.is_valid_identifier("table@name"))

    def test_invalid_identifier_empty_string(self):
        """Test is_valid_identifier returns False for empty string."""
        self.assertFalse(ExasolAdapter.is_valid_identifier(""))

    def test_valid_identifier_all_special_chars(self):
        """Test is_valid_identifier with all valid special characters."""
        self.assertTrue(ExasolAdapter.is_valid_identifier("a#$_123"))


class TestMakeMatchKwargs(unittest.TestCase):
    """Test _make_match_kwargs method."""

    def setUp(self):
        """Set up test adapter with mock config."""
        mock_config = Mock()
        mock_config.quoting = {
            "database": False,
            "schema": False,
            "identifier": False,
        }
        self.adapter = Mock(spec=ExasolAdapter)
        self.adapter.config = mock_config
        # Call the real _make_match_kwargs method
        self.adapter._make_match_kwargs = lambda *args: ExasolAdapter._make_match_kwargs(self.adapter, *args)

    def test_make_match_kwargs_no_quoting(self):
        """Test _make_match_kwargs converts to lowercase when quoting is False."""
        self.adapter.config = Mock()
        self.adapter.config.quoting = {
            "database": False,
            "schema": False,
            "identifier": False,
        }

        result = self.adapter._make_match_kwargs("DB", "SCHEMA", "TABLE")

        self.assertEqual(result["schema"], "schema")
        self.assertEqual(result["identifier"], "table")
        self.assertNotIn("database", result)

    def test_make_match_kwargs_with_quoting(self):
        """Test _make_match_kwargs preserves case when quoting is True."""
        self.adapter.config = Mock()
        self.adapter.config.quoting = {
            "database": True,
            "schema": True,
            "identifier": True,
        }

        result = self.adapter._make_match_kwargs("DB", "SCHEMA", "TABLE")

        self.assertEqual(result["schema"], "SCHEMA")
        self.assertEqual(result["identifier"], "TABLE")

    def test_make_match_kwargs_mixed_quoting(self):
        """Test _make_match_kwargs with mixed quoting settings."""
        self.adapter.config = Mock()
        self.adapter.config.quoting = {
            "database": False,
            "schema": True,
            "identifier": False,
        }

        result = self.adapter._make_match_kwargs("DB", "SCHEMA", "TABLE")

        self.assertEqual(result["schema"], "SCHEMA")
        self.assertEqual(result["identifier"], "table")

    def test_make_match_kwargs_with_none_values(self):
        """Test _make_match_kwargs filters out None values."""
        self.adapter.config = Mock()
        self.adapter.config.quoting = {
            "database": False,
            "schema": False,
            "identifier": False,
        }

        result = self.adapter._make_match_kwargs(None, "schema", None)

        self.assertEqual(result, {"schema": "schema"})
        self.assertNotIn("identifier", result)
        self.assertNotIn("database", result)


class TestConvertNumberType(unittest.TestCase):
    """Test convert_number_type class method."""

    def test_convert_number_type_with_decimals(self):
        """Test convert_number_type returns 'float' when decimals present."""
        # Create a mock agate table with decimal values
        mock_table = Mock(spec=agate.Table)
        mock_table.aggregate.return_value = 2  # Has decimals

        result = ExasolAdapter.convert_number_type(mock_table, 0)

        self.assertEqual(result, "float")
        mock_table.aggregate.assert_called_once()

    def test_convert_number_type_without_decimals(self):
        """Test convert_number_type returns 'integer' when no decimals."""
        mock_table = Mock(spec=agate.Table)
        mock_table.aggregate.return_value = 0  # No decimals

        result = ExasolAdapter.convert_number_type(mock_table, 0)

        self.assertEqual(result, "integer")


class TestTimestampAddSql(unittest.TestCase):
    """Test timestamp_add_sql method."""

    def setUp(self):
        """Set up test adapter."""
        self.adapter = Mock(spec=ExasolAdapter)
        # Call the real timestamp_add_sql method
        self.adapter.timestamp_add_sql = lambda *args, **kwargs: ExasolAdapter.timestamp_add_sql(
            self.adapter, *args, **kwargs
        )

    def test_timestamp_add_sql_default(self):
        """Test timestamp_add_sql with default parameters."""
        result = self.adapter.timestamp_add_sql("created_at")
        self.assertEqual(result, "created_at + interval '1' hour")

    def test_timestamp_add_sql_custom_number(self):
        """Test timestamp_add_sql with custom number."""
        result = self.adapter.timestamp_add_sql("created_at", 5)
        self.assertEqual(result, "created_at + interval '5' hour")

    def test_timestamp_add_sql_custom_interval(self):
        """Test timestamp_add_sql with custom interval."""
        result = self.adapter.timestamp_add_sql("created_at", 1, "day")
        self.assertEqual(result, "created_at + interval '1' day")

    def test_timestamp_add_sql_minutes(self):
        """Test timestamp_add_sql with minutes interval."""
        result = self.adapter.timestamp_add_sql("updated_at", 30, "minute")
        self.assertEqual(result, "updated_at + interval '30' minute")


class TestQuoteSeedColumn(unittest.TestCase):
    """Test quote_seed_column method."""

    def setUp(self):
        """Set up test adapter."""
        self.adapter = Mock(spec=ExasolAdapter)
        self.adapter.quote = Mock(side_effect=lambda x: f'"{x}"')
        # Call the real quote_seed_column method
        self.adapter.quote_seed_column = lambda *args: ExasolAdapter.quote_seed_column(self.adapter, *args)

    def test_quote_seed_column_with_true(self):
        """Test quote_seed_column with quote_config=True."""
        result = self.adapter.quote_seed_column("column_name", True)
        self.assertEqual(result, '"column_name"')

    def test_quote_seed_column_with_false(self):
        """Test quote_seed_column with quote_config=False."""
        result = self.adapter.quote_seed_column("column_name", False)
        self.assertEqual(result, "column_name")

    def test_quote_seed_column_with_none(self):
        """Test quote_seed_column with quote_config=None."""
        result = self.adapter.quote_seed_column("column_name", None)
        self.assertEqual(result, "column_name")

    def test_quote_seed_column_with_invalid_type(self):
        """Test quote_seed_column raises error with invalid type."""
        with self.assertRaises(CompilationError) as context:
            self.adapter.quote_seed_column("column_name", "invalid")
        self.assertIn("invalid type", str(context.exception))


class TestListRelationsWithoutCaching(unittest.TestCase):
    """Test list_relations_without_caching method."""

    def setUp(self):
        """Set up test adapter."""
        self.adapter = Mock(spec=ExasolAdapter)
        self.adapter.Relation = ExasolAdapter.Relation
        self.adapter.config = Mock()
        self.adapter.config.quoting = {
            "database": False,
            "schema": False,
            "identifier": False,
        }

    def test_list_relations_without_caching_basic(self):
        """Test list_relations_without_caching with basic results."""
        # Mock the macro results
        self.adapter.execute_macro = Mock(
            return_value=[
                ("DB", "table1", "schema1", "table"),
                ("DB", "view1", "schema1", "view"),
            ]
        )

        schema_relation = Mock()
        result = ExasolAdapter.list_relations_without_caching(self.adapter, schema_relation)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].identifier, "table1")
        self.assertEqual(result[0].schema, "schema1")
        self.assertEqual(result[1].identifier, "view1")

        self.adapter.execute_macro.assert_called_once_with(
            "list_relations_without_caching",
            kwargs={"schema_relation": schema_relation},
        )

    def test_list_relations_without_caching_external_type(self):
        """Test list_relations_without_caching handles external type."""
        # Mock the macro results with an unknown type
        self.adapter.execute_macro = Mock(
            return_value=[
                ("DB", "external_table", "schema1", "unknown_type"),
            ]
        )

        schema_relation = Mock()
        result = ExasolAdapter.list_relations_without_caching(self.adapter, schema_relation)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].identifier, "external_table")


class TestValidIncrementalStrategies(unittest.TestCase):
    """Test valid_incremental_strategies method."""

    def test_valid_incremental_strategies(self):
        """Test valid_incremental_strategies returns expected strategies."""
        adapter = Mock(spec=ExasolAdapter)
        adapter.valid_incremental_strategies = lambda: ExasolAdapter.valid_incremental_strategies(adapter)
        strategies = adapter.valid_incremental_strategies()

        expected = ["append", "merge", "delete+insert", "microbatch"]
        self.assertEqual(strategies, expected)


class TestDateFunction(unittest.TestCase):
    """Test date_function class method."""

    def test_date_function(self):
        """Test date_function returns current_timestamp()."""
        result = ExasolAdapter.date_function()
        self.assertEqual(result, "current_timestamp()")


class TestIsCancelable(unittest.TestCase):
    """Test is_cancelable class method."""

    def test_is_cancelable(self):
        """Test is_cancelable returns False."""
        result = ExasolAdapter.is_cancelable()
        self.assertFalse(result)


class TestConvertTextType(unittest.TestCase):
    """Test convert_text_type class method."""

    def test_convert_text_type(self):
        """Test convert_text_type returns varchar with max size."""
        result = ExasolAdapter.convert_text_type(Mock(), 0)
        self.assertEqual(result, "varchar(2000000)")


if __name__ == "__main__":
    unittest.main()
