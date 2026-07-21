"""Functional tests for the latest_version_pointer feature (dbt-core 1.12).

In dbt 1.12, when a model is declared with ``versions:`` in schema.yml,
dbt-core automatically materialises a pointer view whose identifier is the
base model name (without the version suffix).  The pointer is a plain
``SELECT * FROM <latest_versioned_relation>`` view and reuses Exasol's
existing ``view.sql`` macro — no adapter changes are required.

The ``generate_latest_version_pointer_alias`` macro (dbt-adapters 1.24.2)
controls the alias of the pointer view; by default it is the base model name.

Test 5.1 / 5.2: define a versioned model, run it, and assert that:
- the versioned model itself (``<name>_v1``) exists and is selectable
- the pointer view (named after the base model, ``<name>``) exists and is
  selectable, confirming that Exasol's view materialization handles the
  synthetic pointer node correctly.
"""

import pytest
from dbt.tests.util import (
    relation_from_name,
    run_dbt,
)

# ---------------------------------------------------------------------------
# Fixture content
# ---------------------------------------------------------------------------

_MODEL_V1_SQL = "select 1 as id, 'hello' as greeting"

_SCHEMA_YML = """\
version: 2

models:
  - name: versioned_greeting
    latest_version: 1
    versions:
      - v: 1
"""


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestLatestVersionPointer:
    """Task 5.1/5.2: pointer view is created via the existing view materialization.

    Defines ``versioned_greeting_v1.sql`` as a versioned model, declares
    ``latest_version: 1`` in schema.yml, runs ``dbt run``, and confirms that
    both the versioned model and the automatically-created pointer view are
    present and queryable on Exasol.
    """

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "versioned_greeting_v1.sql": _MODEL_V1_SQL,
            "schema.yml": _SCHEMA_YML,
        }

    def _relation_exists(self, project, name: str) -> bool:
        """Return True if a relation with the given name is queryable."""
        try:
            relation = relation_from_name(project.adapter, name)
            result = project.run_sql(f"select count(*) from {relation}", fetch="one")
            return result is not None
        except Exception:
            return False

    def test_versioned_model_runs(self, project):
        """The versioned model (versioned_greeting__v1) runs without error."""
        results = run_dbt(["run"])
        # At least the versioned model node ran
        assert len(results) >= 1
        assert all(r.status == "success" for r in results), [(r.node.name, r.status) for r in results]

    def test_versioned_model_is_selectable(self, project):
        """The versioned model relation exists and is selectable."""
        run_dbt(["run"])
        # dbt names the versioned relation as <name>_v<n> in most configs
        assert self._relation_exists(
            project, "versioned_greeting_v1"
        ), "Versioned model relation 'versioned_greeting_v1' not found after dbt run"

    def test_pointer_view_is_created_and_selectable(self, project):
        """Task 5.1: pointer view named after the base model exists and is selectable.

        dbt-core 1.12 automatically materialises a pointer view named
        ``versioned_greeting`` (the base model name) that selects from
        the latest versioned relation.  This view is created via Exasol's
        standard view materialization (task 5.2 — no adapter changes needed).
        """
        run_dbt(["run"])
        assert self._relation_exists(project, "versioned_greeting"), (
            "Pointer view 'versioned_greeting' not found after dbt run. "
            "Expected dbt-core 1.12 to automatically create a pointer view "
            "using Exasol's view materialization."
        )
