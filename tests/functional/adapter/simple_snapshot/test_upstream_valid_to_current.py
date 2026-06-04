"""Upstream parity proof for snapshot `dbt_valid_to_current` (1.9+).

The existing Exasol-specific `test_snapshot_valid_to_current.py` stays (it covers
Exasol-specific concerns); this subclass of the upstream base class is the
authoritative parity proof discoverable via `pytest --collect-only`.

The upstream fixtures hardcode three-part ``{database}.{schema}.table`` /
``{{target.database}}.{{target.schema}}.seed`` identifiers, which Exasol does not
support (Exasol uses two-part ``schema.table`` naming). We override the seed, delete
and snapshot SQL fixtures to drop the database qualifier; everything else is
inherited unchanged.
"""

import pytest
from dbt.tests.adapter.simple_snapshot.new_record_dbt_valid_to_current import (
    BaseSnapshotNewRecordDbtValidToCurrent,
)

_seed_new_record_mode_statements = [
    "create table {schema}.seed (id INTEGER, first_name VARCHAR(50));",
    "insert into {schema}.seed (id, first_name) values (1, 'Judith'), (2, 'Arthur');",
]

_snapshot_actual_sql = """
{% snapshot snapshot_actual %}
    select * from {{target.schema}}.seed
{% endsnapshot %}
"""

_delete_sql = "delete from {schema}.seed where id = 1"

# Upstream sets `dbt_valid_to_current: "date('9999-12-31')"`, but Exasol's
# snapshot_string_as_time wraps the value as `to_timestamp('<value>')`, so it must
# be a bare timestamp string (T-separated to match Exasol's NLS_TIMESTAMP_FORMAT) —
# matching the Exasol-specific test_snapshot_valid_to_current.py.
_snapshots_yml = """
snapshots:
  - name: snapshot_actual
    config:
      unique_key: id
      strategy: check
      check_cols: all
      hard_deletes: new_record
      dbt_valid_to_current: "9999-12-31T23:59:59"
"""


class TestExasolSnapshotNewRecordDbtValidToCurrent(BaseSnapshotNewRecordDbtValidToCurrent):
    @pytest.fixture(scope="class")
    def models(self):
        return {"snapshots.yml": _snapshots_yml}

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {"snapshot.sql": _snapshot_actual_sql}

    @pytest.fixture(scope="class")
    def seed_new_record_mode_statements(self):
        return _seed_new_record_mode_statements

    @pytest.fixture(scope="class")
    def delete_sql(self):
        return _delete_sql
