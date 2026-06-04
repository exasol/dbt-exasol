"""Functional test for `ExasolAdapter.get_catalog_for_single_relation`.

Creates one table and calls the adapter method directly, asserting that metadata
and columns are populated (Capability.GetCatalogForSingleRelation: Full).
"""

import pytest

my_model_sql = """
select
    1 as id,
    cast('exasol' as varchar(100)) as name
"""


class TestSingleRelationCatalog:
    @pytest.fixture(scope="class")
    def models(self):
        return {"my_model.sql": my_model_sql}

    def test_get_catalog_for_single_relation(self, project):
        from dbt.tests.util import run_dbt

        run_dbt(["run"])

        relation = project.adapter.Relation.create(
            database=project.database,
            schema=project.test_schema,
            identifier="my_model",
        )

        with project.adapter.connection_named("__test"):
            catalog_table = project.adapter.get_catalog_for_single_relation(relation)

        assert catalog_table is not None
        assert catalog_table.metadata.name.upper() == "MY_MODEL"
        assert catalog_table.metadata.schema.upper() == project.test_schema.upper()
        assert {c.upper() for c in catalog_table.columns} == {"ID", "NAME"}
        # Columns are returned in ordinal position order.
        indexes = [catalog_table.columns[c].index for c in catalog_table.columns]
        assert indexes == sorted(indexes)

    def test_returns_none_for_missing_relation(self, project):
        relation = project.adapter.Relation.create(
            database=project.database,
            schema=project.test_schema,
            identifier="does_not_exist",
        )
        with project.adapter.connection_named("__test"):
            assert project.adapter.get_catalog_for_single_relation(relation) is None
