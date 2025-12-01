import decimal
from dbt.tests.util import get_connection


class TestMixedTypeRetrieval:
    # A Decimal followed by a NULL used to raise an exception.
    # Verify that it no longer does.
    def test_decimal_followed_by_null(self, project):
        sql = "select * from values 1.2, null"
        with get_connection(project.adapter):
            _, res = project.adapter.execute(sql, fetch=True)
        assert res.rows.values() == ((decimal.Decimal("1.2"),), (None,))
