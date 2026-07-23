"""Upstream parity proof for snapshot `hard_deletes` (1.9+).

The existing Exasol-specific `test_snapshot_hard_deletes.py` stays (it covers
Exasol-specific column behaviour); this subclass of the upstream base class is the
authoritative parity proof discoverable via `pytest --collect-only`.

The upstream fixtures hardcode three-part ``{database}.{schema}.table`` identifiers,
which Exasol does not support (Exasol uses two-part ``schema.table`` naming). We
override the SQL fixtures to drop the database qualifier; everything else is
inherited unchanged.
"""

import pytest
from dbt.tests.adapter.simple_snapshot.test_ephemeral_snapshot_hard_deletes import (
    BaseSnapshotEphemeralHardDeletes,
)

_source_create_sql = """
create table {schema}.src_customers (
    id INTEGER,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(50),
    updated_at TIMESTAMP
);
"""

# Use explicit TIMESTAMP literals: Exasol's session NLS_TIMESTAMP_FORMAT uses a
# 'T' separator, so implicit casts of space-separated string literals fail.
_source_insert_sql = """
insert into {schema}.src_customers (id, first_name, last_name, email, updated_at) values
(1, 'John', 'Doe', 'john.doe@example.com', TIMESTAMP '2023-01-01 10:00:00'),
(2, 'Jane', 'Smith', 'jane.smith@example.com', TIMESTAMP '2023-01-02 11:00:00'),
(3, 'Bob', 'Johnson', 'bob.johnson@example.com', TIMESTAMP '2023-01-03 12:00:00');
"""

_source_alter_sql = """
alter table {schema}.src_customers add column dummy_column VARCHAR(50) default 'dummy_value';
"""


class TestExasolSnapshotEphemeralHardDeletes(BaseSnapshotEphemeralHardDeletes):
    @pytest.fixture(scope="class")
    def source_create_sql(self):
        return _source_create_sql

    @pytest.fixture(scope="class")
    def source_insert_sql(self):
        return _source_insert_sql

    @pytest.fixture(scope="class")
    def source_alter_sql(self):
        return _source_alter_sql
