"""Unit tests for ExasolColumn type detection and parsing."""

import unittest

from dbt_common.exceptions import DbtRuntimeError

from dbt.adapters.exasol import ExasolColumn


class TestExasolColumnTypeDetection(unittest.TestCase):
    """Test type detection methods in ExasolColumn."""

    def test_is_numeric_with_decimal(self):
        """Test is_numeric returns True for DECIMAL type."""
        col = ExasolColumn("test_col", "DECIMAL", None, 18, 0)
        self.assertTrue(col.is_numeric())

    def test_is_numeric_with_double(self):
        """Test is_numeric returns True for DOUBLE type."""
        col = ExasolColumn("test_col", "DOUBLE", None, None, None)
        self.assertTrue(col.is_numeric())

    def test_is_numeric_with_non_numeric_type(self):
        """Test is_numeric returns False for VARCHAR type."""
        col = ExasolColumn("test_col", "VARCHAR", 100, None, None)
        self.assertFalse(col.is_numeric())

    def test_is_numeric_case_insensitive(self):
        """Test is_numeric works with mixed case type names."""
        col = ExasolColumn("test_col", "Decimal", None, 18, 0)
        self.assertTrue(col.is_numeric())

    def test_is_integer_with_scale_zero(self):
        """Test is_integer returns True for DECIMAL with scale=0."""
        col = ExasolColumn("test_col", "DECIMAL", None, 18, 0)
        self.assertTrue(col.is_integer())

    def test_is_integer_with_scale_greater_than_zero(self):
        """Test is_integer returns False for DECIMAL with scale>0."""
        col = ExasolColumn("test_col", "DECIMAL", None, 18, 9)
        self.assertFalse(col.is_integer())

    def test_is_integer_with_double(self):
        """Test is_integer returns False for DOUBLE type."""
        col = ExasolColumn("test_col", "DOUBLE", None, None, None)
        self.assertFalse(col.is_integer())

    def test_is_float_with_double(self):
        """Test is_float returns True for DOUBLE type."""
        col = ExasolColumn("test_col", "DOUBLE", None, None, None)
        self.assertTrue(col.is_float())

    def test_is_float_with_decimal(self):
        """Test is_float returns False for DECIMAL type."""
        col = ExasolColumn("test_col", "DECIMAL", None, 18, 9)
        self.assertFalse(col.is_float())

    def test_is_string_with_varchar(self):
        """Test is_string returns True for VARCHAR type."""
        col = ExasolColumn("test_col", "VARCHAR", 100, None, None)
        self.assertTrue(col.is_string())

    def test_is_string_with_char(self):
        """Test is_string returns True for CHAR type."""
        col = ExasolColumn("test_col", "CHAR", 10, None, None)
        self.assertTrue(col.is_string())

    def test_is_string_with_non_string_type(self):
        """Test is_string returns False for DECIMAL type."""
        col = ExasolColumn("test_col", "DECIMAL", None, 18, 0)
        self.assertFalse(col.is_string())

    def test_is_hashtype_with_hashtype(self):
        """Test is_hashtype returns True for HASHTYPE."""
        col = ExasolColumn("test_col", "HASHTYPE", 16, None, None)
        self.assertTrue(col.is_hashtype())

    def test_is_hashtype_with_non_hashtype(self):
        """Test is_hashtype returns False for VARCHAR type."""
        col = ExasolColumn("test_col", "VARCHAR", 100, None, None)
        self.assertFalse(col.is_hashtype())

    def test_is_boolean_with_boolean(self):
        """Test is_boolean returns True for BOOLEAN type."""
        col = ExasolColumn("test_col", "BOOLEAN", None, None, None)
        self.assertTrue(col.is_boolean())

    def test_is_boolean_with_non_boolean(self):
        """Test is_boolean returns False for VARCHAR type."""
        col = ExasolColumn("test_col", "VARCHAR", 100, None, None)
        self.assertFalse(col.is_boolean())

    def test_is_timestamp_with_timestamp(self):
        """Test is_timestamp returns True for TIMESTAMP type."""
        col = ExasolColumn("test_col", "TIMESTAMP", None, None, None)
        self.assertTrue(col.is_timestamp())

    def test_is_timestamp_with_timestamp_with_local_time_zone(self):
        """Test is_timestamp returns True for TIMESTAMP WITH LOCAL TIME ZONE."""
        col = ExasolColumn("test_col", "TIMESTAMP WITH LOCAL TIME ZONE", None, None, None)
        self.assertTrue(col.is_timestamp())

    def test_is_timestamp_with_non_timestamp(self):
        """Test is_timestamp returns False for DATE type."""
        col = ExasolColumn("test_col", "DATE", None, None, None)
        self.assertFalse(col.is_timestamp())

    def test_is_date_with_date(self):
        """Test is_date returns True for DATE type."""
        col = ExasolColumn("test_col", "DATE", None, None, None)
        self.assertTrue(col.is_date())

    def test_is_date_with_non_date(self):
        """Test is_date returns False for TIMESTAMP type."""
        col = ExasolColumn("test_col", "TIMESTAMP", None, None, None)
        self.assertFalse(col.is_date())

    def test_string_size_with_char_size(self):
        """Test string_size returns char_size for VARCHAR."""
        col = ExasolColumn("test_col", "VARCHAR", 100, None, None)
        self.assertEqual(col.string_size(), 100)

    def test_string_size_without_char_size(self):
        """Test string_size returns default 2000000 when char_size is None."""
        col = ExasolColumn("test_col", "VARCHAR", None, None, None)
        self.assertEqual(col.string_size(), 2000000)

    def test_string_size_on_non_string_raises_error(self):
        """Test string_size raises error when called on non-string field."""
        col = ExasolColumn("test_col", "DECIMAL", None, 18, 0)
        with self.assertRaises(DbtRuntimeError) as context:
            col.string_size()
        self.assertIn("Called string_size() on non-string field", str(context.exception))


class TestExasolColumnParsing(unittest.TestCase):
    """Test from_description method in ExasolColumn."""

    def test_from_description_simple_varchar(self):
        """Test from_description with simple VARCHAR type."""
        col = ExasolColumn.from_description("name", "VARCHAR")
        self.assertEqual(col.name, "name")
        self.assertEqual(col.dtype, "VARCHAR")
        self.assertIsNone(col.char_size)
        self.assertIsNone(col.numeric_precision)
        self.assertIsNone(col.numeric_scale)

    def test_from_description_simple_decimal(self):
        """Test from_description with simple DECIMAL type."""
        col = ExasolColumn.from_description("amount", "DECIMAL")
        self.assertEqual(col.name, "amount")
        self.assertEqual(col.dtype, "DECIMAL")
        self.assertIsNone(col.char_size)

    def test_from_description_simple_timestamp(self):
        """Test from_description with simple TIMESTAMP type."""
        col = ExasolColumn.from_description("created_at", "TIMESTAMP")
        self.assertEqual(col.name, "created_at")
        self.assertEqual(col.dtype, "TIMESTAMP")

    def test_from_description_varchar_with_size(self):
        """Test from_description with VARCHAR(100)."""
        col = ExasolColumn.from_description("name", "VARCHAR(100)")
        self.assertEqual(col.name, "name")
        self.assertEqual(col.dtype, "VARCHAR")
        self.assertEqual(col.char_size, 100)

    def test_from_description_decimal_with_precision_and_scale(self):
        """Test from_description with DECIMAL(18,9)."""
        col = ExasolColumn.from_description("amount", "DECIMAL(18,9)")
        self.assertEqual(col.name, "amount")
        self.assertEqual(col.dtype, "DECIMAL")
        self.assertEqual(col.numeric_precision, 18)
        self.assertEqual(col.numeric_scale, 9)
        self.assertIsNone(col.char_size)

    def test_from_description_hashtype_with_byte_format(self):
        """Test from_description with HASHTYPE(16 BYTE) format."""
        col = ExasolColumn.from_description("hash_col", "HASHTYPE(16 BYTE)")
        self.assertEqual(col.name, "hash_col")
        self.assertEqual(col.dtype, "HASHTYPE")
        self.assertEqual(col.char_size, 16)

    def test_from_description_char_with_size(self):
        """Test from_description with CHAR(10)."""
        col = ExasolColumn.from_description("code", "CHAR(10)")
        self.assertEqual(col.name, "code")
        self.assertEqual(col.dtype, "CHAR")
        self.assertEqual(col.char_size, 10)

    def test_from_description_invalid_format_raises_error(self):
        """Test from_description raises error with invalid format."""
        # This is a malformed type that won't match the regex
        with self.assertRaises(DbtRuntimeError) as context:
            ExasolColumn.from_description("bad_col", "")
        self.assertIn("Could not interpret data type", str(context.exception))

    def test_from_description_non_numeric_size_raises_error(self):
        """Test from_description raises error when size is not numeric."""
        with self.assertRaises(DbtRuntimeError) as context:
            ExasolColumn.from_description("bad_col", "VARCHAR(abc)")
        self.assertIn("could not convert", str(context.exception))

    def test_from_description_non_numeric_precision_raises_error(self):
        """Test from_description raises error when precision is not numeric."""
        with self.assertRaises(DbtRuntimeError) as context:
            ExasolColumn.from_description("bad_col", "DECIMAL(abc,9)")
        self.assertIn("could not convert", str(context.exception))

    def test_from_description_non_numeric_scale_raises_error(self):
        """Test from_description raises error when scale is not numeric."""
        with self.assertRaises(DbtRuntimeError) as context:
            ExasolColumn.from_description("bad_col", "DECIMAL(18,xyz)")
        self.assertIn("could not convert", str(context.exception))

    def test_from_description_decimal_36_0(self):
        """Test from_description with DECIMAL(36,0) for BIGINT alias."""
        col = ExasolColumn.from_description("big_id", "DECIMAL(36,0)")
        self.assertEqual(col.name, "big_id")
        self.assertEqual(col.dtype, "DECIMAL")
        self.assertEqual(col.numeric_precision, 36)
        self.assertEqual(col.numeric_scale, 0)

    def test_from_description_double_precision(self):
        """Test from_description with DOUBLE PRECISION."""
        col = ExasolColumn.from_description("rate", "DOUBLE PRECISION")
        self.assertEqual(col.name, "rate")
        self.assertEqual(col.dtype, "DOUBLE PRECISION")


class TestExasolColumnStringType(unittest.TestCase):
    """Test string_type class method."""

    def test_string_type_with_size(self):
        """Test string_type returns VARCHAR with specified size."""
        result = ExasolColumn.string_type(100)
        self.assertEqual(result, "VARCHAR(100)")

    def test_string_type_with_default_size(self):
        """Test string_type returns VARCHAR with max size."""
        result = ExasolColumn.string_type(2000000)
        self.assertEqual(result, "VARCHAR(2000000)")

    def test_string_type_with_small_size(self):
        """Test string_type returns VARCHAR with small size."""
        result = ExasolColumn.string_type(10)
        self.assertEqual(result, "VARCHAR(10)")


if __name__ == "__main__":
    unittest.main()
