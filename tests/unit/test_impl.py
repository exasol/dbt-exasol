"""Unit tests for ExasolAdapter methods."""

import unittest
from unittest.mock import Mock, patch

import agate
from dbt.adapters.base.impl import _expect_row_value
from dbt.adapters.base.relation import BaseRelation
from dbt.adapters.capability import Capability
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
        self.adapter._make_match_kwargs = (
            lambda *args: ExasolAdapter._make_match_kwargs(self.adapter, *args)
        )

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
        self.adapter.timestamp_add_sql = (
            lambda *args, **kwargs: ExasolAdapter.timestamp_add_sql(
                self.adapter, *args, **kwargs
            )
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
        self.adapter.quote_seed_column = lambda *args: ExasolAdapter.quote_seed_column(
            self.adapter, *args
        )

    def test_quote_seed_column_with_true(self):
        """Test quote_seed_column with quote_config=True."""
        result = self.adapter.quote_seed_column("column_name", True)
        self.assertEqual(result, '"column_name"')

    def test_quote_seed_column_with_false(self):
        """Test quote_seed_column with quote_config=False."""
        result = self.adapter.quote_seed_column("column_name", False)
        self.assertEqual(result, "column_name")

    def test_quote_seed_column_with_none(self):
        """Test quote_seed_column with quote_config=None for non-keyword column."""
        # Setup mock for should_identifier_be_quoted to return False for non-keywords
        self.adapter.should_identifier_be_quoted = lambda x, y=None: False
        result = self.adapter.quote_seed_column("column_name", None)
        self.assertEqual(result, "column_name")

    def test_quote_seed_column_with_invalid_type(self):
        """Test quote_seed_column raises error with invalid type."""
        # Setup mock for should_identifier_be_quoted (needed to reach the else branch)
        self.adapter.should_identifier_be_quoted = lambda x, y=None: False
        with self.assertRaises(CompilationError) as context:
            self.adapter.quote_seed_column("column_name", "invalid")
        self.assertIn("invalid type", str(context.exception))

    def test_quote_seed_column_with_keyword(self):
        """Test quote_seed_column automatically quotes SQL keywords."""
        # Setup mock for should_identifier_be_quoted
        self.adapter.should_identifier_be_quoted = lambda x, y=None: x.upper() in [
            "ORDER",
            "STATE",
            "FROM",
            "USER",
        ]

        # Test that keywords are quoted even with quote_config=None
        result = self.adapter.quote_seed_column("order", None)
        self.assertEqual(result, '"order"')

        result = self.adapter.quote_seed_column("state", None)
        self.assertEqual(result, '"state"')

        result = self.adapter.quote_seed_column("from", None)
        self.assertEqual(result, '"from"')

        result = self.adapter.quote_seed_column("user", None)
        self.assertEqual(result, '"user"')

    def test_quote_seed_column_with_non_keyword(self):
        """Test quote_seed_column doesn't quote non-keywords unless configured."""
        # Setup mock for should_identifier_be_quoted
        self.adapter.should_identifier_be_quoted = lambda x, y=None: x.upper() in [
            "ORDER",
            "STATE",
        ]

        # Test that non-keywords are not quoted with quote_config=None
        result = self.adapter.quote_seed_column("regular_column", None)
        self.assertEqual(result, "regular_column")

        # But they are quoted with quote_config=True
        result = self.adapter.quote_seed_column("regular_column", True)
        self.assertEqual(result, '"regular_column"')


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
        result = ExasolAdapter.list_relations_without_caching(
            self.adapter, schema_relation
        )

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
        result = ExasolAdapter.list_relations_without_caching(
            self.adapter, schema_relation
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].identifier, "external_table")


class TestValidIncrementalStrategies(unittest.TestCase):
    """Test valid_incremental_strategies method."""

    def test_valid_incremental_strategies(self):
        """Test valid_incremental_strategies returns expected strategies."""
        adapter = Mock(spec=ExasolAdapter)
        adapter.valid_incremental_strategies = (
            lambda: ExasolAdapter.valid_incremental_strategies(adapter)
        )
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


class TestShouldIdentifierBeQuoted(unittest.TestCase):
    """Test should_identifier_be_quoted method."""

    def setUp(self):
        """Reset keywords cache before each test."""
        ExasolAdapter._exasol_keywords = None

    def test_should_identifier_be_quoted_fetches_keywords(self):
        """Test should_identifier_be_quoted fetches keywords from DB."""
        adapter = Mock()
        mock_handle = Mock()
        mock_handle.meta.list_sql_keywords.return_value = ["SELECT", "FROM", "WHERE"]
        mock_connection = Mock()
        mock_connection.handle = mock_handle
        adapter.connections = Mock()
        adapter.connections.get_thread_connection.return_value = mock_connection

        result = ExasolAdapter.should_identifier_be_quoted(adapter, "select")

        self.assertTrue(result)
        mock_handle.meta.list_sql_keywords.assert_called_once()

    def test_should_identifier_be_quoted_keyword(self):
        """Test should_identifier_be_quoted returns True for keywords."""
        ExasolAdapter._exasol_keywords = ["SELECT", "FROM", "WHERE"]
        adapter = Mock()
        adapter.connections = Mock()
        adapter.connections.get_thread_connection = Mock()

        result = ExasolAdapter.should_identifier_be_quoted(adapter, "select")
        self.assertTrue(result)

    def test_should_identifier_be_quoted_invalid_identifier(self):
        """Test should_identifier_be_quoted returns True for invalid identifiers."""
        ExasolAdapter._exasol_keywords = []
        adapter = Mock()
        adapter.connections = Mock()
        adapter.connections.get_thread_connection = Mock()
        adapter.is_valid_identifier = ExasolAdapter.is_valid_identifier

        result = ExasolAdapter.should_identifier_be_quoted(adapter, "123invalid")
        self.assertTrue(result)

    def test_should_identifier_be_quoted_with_model_column_dict_quote_true(self):
        """Test should_identifier_be_quoted with model column dict."""
        ExasolAdapter._exasol_keywords = []
        adapter = Mock()
        adapter.connections = Mock()
        adapter.connections.get_thread_connection = Mock()
        adapter.is_valid_identifier = ExasolAdapter.is_valid_identifier

        models_column_dict = {"col1": {"quote": True}}
        result = ExasolAdapter.should_identifier_be_quoted(
            adapter, "col1", models_column_dict
        )
        self.assertTrue(result)

    def test_should_identifier_be_quoted_with_quoted_column_in_dict(self):
        """Test should_identifier_be_quoted checks quoted identifier in dict."""
        ExasolAdapter._exasol_keywords = []
        adapter = Mock()
        adapter.connections = Mock()
        adapter.connections.get_thread_connection = Mock()
        adapter.is_valid_identifier = ExasolAdapter.is_valid_identifier
        adapter.quote = lambda x: f'"{x}"'

        models_column_dict = {'"col1"': {"quote": True}}
        result = ExasolAdapter.should_identifier_be_quoted(
            adapter, "col1", models_column_dict
        )
        self.assertTrue(result)

    def test_should_identifier_be_quoted_returns_false_for_valid_non_keyword(self):
        """Test should_identifier_be_quoted returns False for valid non-keyword."""
        ExasolAdapter._exasol_keywords = []
        adapter = Mock()
        adapter.connections = Mock()
        adapter.connections.get_thread_connection = Mock()
        adapter.is_valid_identifier = ExasolAdapter.is_valid_identifier

        result = ExasolAdapter.should_identifier_be_quoted(adapter, "regular_column")
        self.assertFalse(result)


class TestCheckAndQuoteIdentifier(unittest.TestCase):
    """Test check_and_quote_identifier method."""

    def setUp(self):
        """Reset keywords cache before each test."""
        ExasolAdapter._exasol_keywords = None

    def test_check_and_quote_identifier_needs_quoting(self):
        """Test check_and_quote_identifier quotes when needed."""
        adapter = Mock(spec=ExasolAdapter)
        adapter.should_identifier_be_quoted = Mock(return_value=True)
        adapter.quote = Mock(side_effect=lambda x: f'"{x}"')

        result = ExasolAdapter.check_and_quote_identifier(adapter, "order")
        self.assertEqual(result, '"order"')

    def test_check_and_quote_identifier_no_quoting(self):
        """Test check_and_quote_identifier doesn't quote when not needed."""
        adapter = Mock(spec=ExasolAdapter)
        adapter.should_identifier_be_quoted = Mock(return_value=False)

        result = ExasolAdapter.check_and_quote_identifier(adapter, "regular_column")
        self.assertEqual(result, "regular_column")


class TestGetFilteredCatalog(unittest.TestCase):
    """Test get_filtered_catalog method."""

    def test_get_filtered_catalog_with_no_relations(self):
        """Test get_filtered_catalog uses traditional method when relations is None."""
        adapter = Mock(spec=ExasolAdapter)
        mock_catalog = Mock(spec=agate.Table)
        adapter.get_catalog.return_value = (mock_catalog, [])

        result, exceptions = ExasolAdapter.get_filtered_catalog(
            adapter,
            relation_configs=[],
            used_schemas=frozenset(),
            relations=None,
        )

        adapter.get_catalog.assert_called_once()
        self.assertEqual(result, mock_catalog)

    def test_get_filtered_catalog_with_many_relations(self):
        """Test get_filtered_catalog uses traditional method with >100 relations."""
        adapter = Mock(spec=ExasolAdapter)
        adapter.supports = Mock(return_value=True)
        mock_catalog = Mock(spec=agate.Table)
        adapter.get_catalog.return_value = (mock_catalog, [])

        # Create 101 relations
        relations = {Mock(schema="test", identifier=f"table{i}") for i in range(101)}

        result, exceptions = ExasolAdapter.get_filtered_catalog(
            adapter,
            relation_configs=[],
            used_schemas=frozenset(),
            relations=relations,
        )

        adapter.get_catalog.assert_called_once()

    def test_get_filtered_catalog_with_few_relations_and_capability(self):
        """Test get_filtered_catalog uses new method with <100 relations."""
        adapter = Mock(spec=ExasolAdapter)
        adapter.supports = Mock(return_value=True)
        mock_catalog = Mock(spec=agate.Table)
        adapter.get_catalog_by_relations.return_value = (mock_catalog, [])

        relations = {Mock(schema="test", identifier="table1")}

        result, exceptions = ExasolAdapter.get_filtered_catalog(
            adapter,
            relation_configs=[],
            used_schemas=frozenset(),
            relations=relations,
        )

        adapter.get_catalog_by_relations.assert_called_once()

    def test_get_filtered_catalog_without_capability(self):
        """Test get_filtered_catalog uses traditional method without capability."""
        adapter = Mock(spec=ExasolAdapter)
        adapter.supports = Mock(return_value=False)
        mock_catalog = Mock(spec=agate.Table)
        adapter.get_catalog.return_value = (mock_catalog, [])

        relations = {Mock(schema="test", identifier="table1")}

        result, exceptions = ExasolAdapter.get_filtered_catalog(
            adapter,
            relation_configs=[],
            used_schemas=frozenset(),
            relations=relations,
        )

        adapter.get_catalog.assert_called_once()

    def test_get_filtered_catalog_filters_relations(self):
        """Test get_filtered_catalog filters catalog by relations."""
        adapter = Mock(spec=ExasolAdapter)
        adapter.supports = Mock(return_value=True)

        # Create mock catalog with rows
        mock_filtered_catalog = Mock(spec=agate.Table)
        mock_catalog = Mock(spec=agate.Table)
        mock_catalog.where.return_value = mock_filtered_catalog

        adapter.get_catalog_by_relations.return_value = (mock_catalog, [])

        relation1 = Mock(schema="schema1", identifier="table1")
        relations = {relation1}

        result, exceptions = ExasolAdapter.get_filtered_catalog(
            adapter,
            relation_configs=[],
            used_schemas=frozenset(),
            relations=relations,
        )

        mock_catalog.where.assert_called_once()

    def test_get_filtered_catalog_with_empty_catalog(self):
        """Test get_filtered_catalog handles empty catalog."""
        adapter = Mock(spec=ExasolAdapter)
        adapter.supports = Mock(return_value=True)
        mock_catalog = None
        adapter.get_catalog_by_relations.return_value = (mock_catalog, [])

        relations = {Mock(schema="test", identifier="table1")}

        result, exceptions = ExasolAdapter.get_filtered_catalog(
            adapter,
            relation_configs=[],
            used_schemas=frozenset(),
            relations=relations,
        )

        # Should not call where on None catalog
        self.assertIsNone(result)


class TestPythonModelNotSupported(unittest.TestCase):
    """Test Python model not supported methods."""

    def test_default_python_submission_method_not_implemented(self):
        """Test default_python_submission_method raises NotImplementedError."""
        adapter = ExasolAdapter(Mock(), Mock())

        with self.assertRaises(NotImplementedError) as context:
            _ = adapter.default_python_submission_method

        self.assertIn("Python models are not supported", str(context.exception))

    def test_python_submission_helpers_not_implemented(self):
        """Test python_submission_helpers raises NotImplementedError."""
        adapter = ExasolAdapter(Mock(), Mock())

        with self.assertRaises(NotImplementedError) as context:
            _ = adapter.python_submission_helpers

        self.assertIn("Python models are not supported", str(context.exception))

    def test_generate_python_submission_response_not_implemented(self):
        """Test generate_python_submission_response raises NotImplementedError."""
        adapter = ExasolAdapter(Mock(), Mock())

        with self.assertRaises(NotImplementedError) as context:
            adapter.generate_python_submission_response(None)

        self.assertIn("Python models are not supported", str(context.exception))


class TestGetCatalogForSingleRelation(unittest.TestCase):
    """Test get_catalog_for_single_relation method."""

    def test_get_catalog_for_single_relation_not_implemented(self):
        """Test get_catalog_for_single_relation raises NotImplementedError."""
        adapter = ExasolAdapter(Mock(), Mock())

        with self.assertRaises(NotImplementedError) as context:
            adapter.get_catalog_for_single_relation(Mock())

        self.assertIn("is not implemented for this adapter", str(context.exception))


if __name__ == "__main__":
    unittest.main()
