"""
Snapshot unique_key values longer than 100 characters.

exasol__snapshot_hash_arguments used to cast every hash argument to
varchar(100), so such keys failed with "string data, right truncation".
"""

import pytest
from dbt.tests.util import run_dbt

snapshots__snapshot_long_key_sql = """
{% snapshot snapshot_long_key %}
    {{
        config(
            target_schema=schema,
            strategy='timestamp',
            unique_key=['long_id', 'region'],
            updated_at='updated_at'
        )
    }}
    select
        rpad('x', 150, 'x') as long_id,
        'EU' as region,
        timestamp '{{ var("updated_at", "2020-01-01 00:00:00") }}' as updated_at
{% endsnapshot %}
"""


class TestSnapshotLongKey:
    @pytest.fixture(scope="class")
    @classmethod
    def snapshots(cls):
        return {"snapshot_long_key.sql": snapshots__snapshot_long_key_sql}

    def test_snapshot_long_key(self, project):
        run_dbt(["snapshot"])
        results = project.run_sql("SELECT COUNT(*) FROM {schema}.snapshot_long_key", fetch="one")
        assert results[0] == 1

        # A changed updated_at must close the old version and add a new one
        run_dbt(["snapshot", "--vars", "{updated_at: '2020-01-02 00:00:00'}"])
        results = project.run_sql("SELECT COUNT(*), COUNT(dbt_valid_to) FROM {schema}.snapshot_long_key", fetch="one")
        assert results[0] == 2
        assert results[1] == 1
