"""Catalog-integration handling on Exasol.

Exasol has no external table-format / catalog integration (Iceberg, etc.). The
inherited `CATALOG_INTEGRATIONS = []` default means:

  (a) a project may declare a non-empty `catalogs.yml` and still parse/run, as long
      as no model actively requests a catalog; and
  (b) a model setting `config(catalog=...)` fails with a clear `DbtRuntimeError`
      mentioning Exasol (via `ExasolAdapter.build_catalog_relation`).

This subclasses the upstream `BaseCatalogIntegrationValidation` so the parity claim
is discoverable via `pytest --collect-only`.
"""

import pytest
from dbt.tests.adapter.catalog_integrations.test_catalog_integration import (
    BaseCatalogIntegrationValidation,
)
from dbt.tests.util import run_dbt
from dbt_common.exceptions import DbtRuntimeError

_CATALOGS_YML = {
    "catalogs": [
        {
            "name": "my_catalog",
            "active_write_integration": "my_integration",
            "write_integrations": [
                {
                    "name": "my_integration",
                    "external_volume": "my_volume",
                    "table_format": "iceberg",
                    "catalog_type": "built_in",
                }
            ],
        }
    ]
}

plain_model_sql = "select 1 as id"
catalog_model_sql = """
{{ config(materialized='table', catalog='my_catalog') }}
select 1 as id
"""


class TestCatalogIntegrationUnused(BaseCatalogIntegrationValidation):
    """(a) catalogs.yml present, no model uses it -> run succeeds."""

    @pytest.fixture(scope="class")
    def catalogs(self):
        return _CATALOGS_YML

    @pytest.fixture(scope="class")
    def models(self):
        return {"plain_model.sql": plain_model_sql}

    def test_unused_catalog_runs(self, project):
        run_dbt(["run"])


class TestCatalogIntegrationRequested(BaseCatalogIntegrationValidation):
    """(b) a model requests a catalog -> clear DbtRuntimeError mentioning Exasol."""

    @pytest.fixture(scope="class")
    def catalogs(self):
        return _CATALOGS_YML

    @pytest.fixture(scope="class")
    def models(self):
        return {"catalog_model.sql": catalog_model_sql}

    def test_requested_catalog_fails_clearly(self, project):
        result = run_dbt(["run"], expect_pass=False)
        message = str(result.results[0].message) if result.results else ""
        assert "Exasol" in message or any("Exasol" in str(r.message) for r in result.results)

    def test_build_catalog_relation_raises(self, project):
        """Direct unit-style assertion against the adapter override."""

        class _Cfg:
            config = {"catalog": "my_catalog"}

        with pytest.raises(DbtRuntimeError, match="Exasol"):
            project.adapter.build_catalog_relation(_Cfg())
