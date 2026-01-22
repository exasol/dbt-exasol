import json

from dbt.tests.util import run_dbt

from dbt.tests.adapter.persist_docs.test_persist_docs import (
    BasePersistDocs,
    BasePersistDocsColumnMissing,
    BasePersistDocsCommentOnQuotedColumn,
)


class TestPersistDocsExasol(BasePersistDocs):

    def _assert_has_table_comments(self, table_node):
        table_comment = table_node["metadata"]["comment"]
        assert table_comment.startswith("Table model description")

        table_id_comment = table_node["columns"]["ID"]["comment"]
        assert table_id_comment.startswith("id Column description")

        table_name_comment = table_node["columns"]["NAME"]["comment"]
        assert table_name_comment.startswith("Some stuff here and then a call to")

        self._assert_common_comments(table_comment, table_id_comment, table_name_comment)

    def _assert_has_view_comments(
        self, view_node, has_node_comments=True, has_column_comments=True
    ):
        view_comment = view_node["metadata"]["comment"]
        if has_node_comments:
            assert view_comment.startswith("View model description")
            self._assert_common_comments(view_comment)
        else:
            assert not view_comment

        view_id_comment = view_node["columns"]["ID"]["comment"]
        if has_column_comments:
            assert view_id_comment.startswith("id Column description")
            self._assert_common_comments(view_id_comment)
        else:
            assert not view_id_comment

        view_name_comment = view_node["columns"]["NAME"]["comment"]
        assert not view_name_comment


class TestPersistDocsColumnMissingExasol(BasePersistDocsColumnMissing):
    def test_missing_column(self, project):
        run_dbt(["docs", "generate"])
        with open("target/catalog.json") as fp:
            catalog_data = json.load(fp)
        assert "nodes" in catalog_data

        table_node = catalog_data["nodes"]["model.test.missing_column"]
        table_id_comment = table_node["columns"]["ID"]["comment"]
        assert table_id_comment.startswith("test id column description")


class TestPersistDocsCommentOnQuotedColumnExasol(BasePersistDocsCommentOnQuotedColumn):
    pass