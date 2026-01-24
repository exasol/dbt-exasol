## 1. Column Type Detection Tests
- [x] 1.1 Create `tests/unit/test_column.py`
- [x] 1.2 Add tests for `is_numeric()` with DECIMAL, DOUBLE, and non-numeric types
- [x] 1.3 Add tests for `is_integer()` with scale=0 and scale>0 decimals
- [x] 1.4 Add tests for `is_float()` with DOUBLE and non-float types
- [x] 1.5 Add tests for `is_string()` with CHAR, VARCHAR, and non-string types
- [x] 1.6 Add tests for `is_hashtype()`, `is_boolean()`, `is_date()`, `is_timestamp()`
- [x] 1.7 Add tests for `string_size()` including error case

## 2. Column Parsing Tests
- [x] 2.1 Add tests for `from_description()` with simple types (VARCHAR, DECIMAL, TIMESTAMP)
- [x] 2.2 Add tests for `from_description()` with sized types (VARCHAR(100), DECIMAL(18,9))
- [x] 2.3 Add tests for `from_description()` with HASHTYPE(16 BYTE) format
- [x] 2.4 Add tests for `from_description()` error cases (invalid format, non-numeric size)

## 3. Identifier Validation Tests
- [x] 3.1 Create `tests/unit/test_impl.py`
- [x] 3.2 Add tests for `is_valid_identifier()` with valid identifiers (alpha start, alphanumeric)
- [x] 3.3 Add tests for `is_valid_identifier()` with valid special chars (#, $, _)
- [x] 3.4 Add tests for `is_valid_identifier()` with invalid identifiers (numeric start, special chars)
- [x] 3.5 Add tests for `is_valid_identifier()` edge cases (empty string, single char)

## 4. Connection Manager Tests
- [x] 4.1 Create `tests/unit/test_connections.py`
- [x] 4.2 Add tests for `data_type_code_to_name()` with simple types
- [x] 4.3 Add tests for `data_type_code_to_name()` with parameterized types (VARCHAR(100))
- [x] 4.4 Add tests for `get_result_from_cursor()`:
    - [x] Mock cursor description and rows
    - [x] Verify DECIMAL string -> Decimal conversion
    - [x] Verify TIMESTAMP string -> datetime conversion
- [x] 4.5 Add tests for `ExasolCursor.execute()`:
    - [x] Verify "0CSV|" prefix triggers `import_from_file`
    - [x] Verify normal queries call `connection.execute`

## 5. Relation Tests
- [x] 5.1 Create `tests/unit/test_relation.py` (already exists as test_relation_quoting.py)
- [x] 5.2 Add tests for `ExasolRelation.create` (verify database is None)
- [x] 5.3 Add tests for `_render_event_time_filtered` (verify timestamp format)
- [x] 5.4 Add tests for `_render_subquery_alias`

## 6. Adapter Helper Tests
- [x] 6.1 Add tests to `tests/unit/test_impl.py` for `_make_match_kwargs`:
    - [x] Verify casing logic when quoting is False
    - [x] Verify casing logic when quoting is True
- [x] 6.2 Add tests for `convert_number_type` (float vs integer based on precision)
- [x] 6.3 Add tests for `timestamp_add_sql` (formatting)
- [x] 6.4 Add tests for `quote_seed_column` (config types and defaults)
- [x] 6.5 Add tests for `list_relations_without_caching` (mock execute_macro results)

## 7. Connection Open Tests
- [x] 7.1 Add tests to `tests/unit/test_connections.py` for `ExasolConnectionManager.open`:
    - [x] Mock `pyexasol` import/connect
    - [x] Test protocol version mapping (v1/v2/v3)
    - [x] Test SSL/Encryption flag logic (`websocket_sslopt`)
    - [x] Test retry wrapper usage

## 8. Validation
- [x] 8.1 Run all unit tests: `uv run pytest tests/unit/ -v`
- [x] 8.2 Verify tests pass with `uv run pytest -n48`
