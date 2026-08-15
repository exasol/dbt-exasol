"""End-to-end quoting consistency between DDL, ref(), source() and seeds (issue #223).

Issue #223 reported that `quoting:` in `dbt_project.yml` was honored by `ref()` but
ignored by the DDL macros, so `ref('model_a')` compiled to a quoted reference while
`CREATE TABLE` created the Exasol-uppercased object. These tests pin the fixed
contract from both directions:

* ``TestDefaultQuotingPolicy`` -- the default policy (all components unquoted) keeps
  working across every materialization and command. This is the non-breaking guard:
  existing projects must be unaffected.
* ``TestQuotedIdentifierPolicy`` -- with ``quoting: {identifier: true}`` the same
  project works end-to-end, including the paths the original fix missed
  (``--full-refresh`` renames, a second ``snapshot`` run, and seed ``IMPORT INTO``).
"""

import os

import pytest
from dbt.tests.util import run_dbt

MODEL_A = """
{{ config(materialized='table') }}
select 1 as id, 'a' as val
"""

# Model B exercises ref() against a table created by the DDL path -- the exact
# combination from the bug report.
MODEL_B = """
{{ config(materialized='table') }}
select * from {{ ref('model_a') }}
"""

MODEL_VIEW = """
{{ config(materialized='view') }}
select * from {{ ref('model_a') }}
"""

MODEL_INCREMENTAL = """
{{ config(materialized='incremental', unique_key='id') }}
select * from {{ ref('model_a') }}
"""

# An ALL_CAPS filename was the workaround suggested in the issue. It must keep
# working once quoting is enabled, which exercises rename_relation on full refresh.
MODEL_UPPERCASE_INCREMENTAL = """
{{ config(materialized='incremental', unique_key='id') }}
select * from {{ ref('model_a') }}
"""

MODEL_FROM_SOURCE = """
{{ config(materialized='table') }}
select * from {{ source('seed_source', 'my_seed') }}
"""

SEED_CSV = """id,name
1,alpha
2,beta
"""

SOURCES_YML = """
version: 2
sources:
  - name: seed_source
    schema: "{{ var('test_schema') }}"
    tables:
      - name: my_seed
"""

# dbt-core deliberately ignores project-level `quoting:` for sources, so a source
# pointing at a quoted (case-sensitive) object must declare quoting itself.
SOURCES_QUOTED_YML = """
version: 2
sources:
  - name: seed_source
    schema: "{{ var('test_schema') }}"
    quoting:
      identifier: true
    tables:
      - name: my_seed
"""

SNAPSHOT_SQL = """
{% snapshot quoting_snap %}
{{ config(target_schema=schema, unique_key='id', strategy='check', check_cols=['val']) }}
select * from {{ ref('model_a') }}
{% endsnapshot %}
"""


class BaseQuotingConsistency:
    """Runs a full project lifecycle and asserts every node succeeds."""

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"my_seed.csv": SEED_CSV}

    @pytest.fixture(scope="class")
    def snapshots(self):
        return {"quoting_snap.sql": SNAPSHOT_SQL}

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "sources.yml": self.sources_yml,
            "model_a.sql": MODEL_A,
            "model_b.sql": MODEL_B,
            "model_view.sql": MODEL_VIEW,
            "model_inc.sql": MODEL_INCREMENTAL,
            "MODEL_UPPER_INC.sql": MODEL_UPPERCASE_INCREMENTAL,
            "model_from_source.sql": MODEL_FROM_SOURCE,
        }

    def test_full_lifecycle_succeeds(self, project):
        """Every command must succeed under the policy under test.

        The commands are ordered to cover the render paths that quoting touches:
        seed IMPORT INTO, CREATE TABLE/VIEW, ref(), source(), the incremental
        merge, the full-refresh rename, and the snapshot merge on a second run.
        """
        assert len(run_dbt(["seed"])) == 1

        # First run: creates every relation via CREATE TABLE / CREATE VIEW.
        assert len(run_dbt(["run"])) == 6

        # Second run: relations already exist, so this exercises cache lookup and
        # the incremental merge against the previously created objects.
        assert len(run_dbt(["run"])) == 6

        # Full refresh: exercises make_intermediate_relation + rename_relation,
        # which is where an uppercase-named incremental model used to break.
        assert len(run_dbt(["run", "--full-refresh"])) == 6

        # First snapshot creates the target; the second must find and merge into it.
        assert len(run_dbt(["snapshot"])) == 1
        assert len(run_dbt(["snapshot"])) == 1

        run_dbt(["test"])

    def test_ddl_and_ref_agree(self, project):
        """The DDL that created a model and the ref() to it must render identically.

        This is the core invariant of issue #223. `compiled_code` in
        run_results.json holds only the SELECT body, so the DDL is read from
        `target/run/...`, which is where the materialized statement is written.
        """
        run_dbt(["seed"])
        run_dbt(["run"])

        run_dir = os.path.join(project.project_root, "target", "run", "test", "models")
        compiled_dir = os.path.join(project.project_root, "target", "compiled", "test", "models")

        def expected(schema, identifier):
            if self.quoted:
                return f'{schema}."{identifier}"'
            return f"{schema}.{identifier}"

        def read(path):
            with open(path, encoding="utf-8") as handle:
                return handle.read()

        # Table DDL vs the ref() body that selects from it -- the core invariant.
        table_ddl = read(os.path.join(run_dir, "model_a.sql"))
        ref_body = read(os.path.join(compiled_dir, "model_b.sql"))
        model_a = expected(project.test_schema, "model_a")
        assert model_a in table_ddl, f"DDL did not contain {model_a}: {table_ddl}"
        assert model_a in ref_body, f"ref() did not contain {model_a}: {ref_body}"

        # View DDL must follow the same policy.
        view_ddl = read(os.path.join(run_dir, "model_view.sql"))
        model_view = expected(project.test_schema, "model_view")
        assert model_view in view_ddl, f"view DDL did not contain {model_view}: {view_ddl}"

        # source() must render the seed object with source-level quoting.
        source_body = read(os.path.join(compiled_dir, "model_from_source.sql"))
        my_seed = expected(project.test_schema, "my_seed")
        assert my_seed in source_body, f"source() did not contain {my_seed}: {source_body}"


class TestDefaultQuotingPolicy(BaseQuotingConsistency):
    """No `quoting:` config -- the pre-existing default must be preserved."""

    quoted = False
    sources_yml = SOURCES_YML

    @pytest.fixture(scope="class")
    def project_config_update(self, unique_schema):
        return {"vars": {"test_schema": unique_schema}}


class TestQuotedIdentifierPolicy(BaseQuotingConsistency):
    """`quoting: {identifier: true}` must be honored consistently everywhere."""

    quoted = True
    sources_yml = SOURCES_QUOTED_YML

    @pytest.fixture(scope="class")
    def project_config_update(self, unique_schema):
        return {
            "vars": {"test_schema": unique_schema},
            "quoting": {"identifier": True},
        }
