"""Test dbt seed with SQL keyword column names."""

import os

import pytest
from dbt.tests.util import run_dbt

# CSV with SQL keyword column names
seeds__keywords_csv = """id,name,order,from,date,user,group,time
1,active,100,source1,2024-01-01,alice,admin,10:00
2,pending,101,source2,2024-01-02,bob,users,11:00
3,completed,102,source3,2024-01-03,charlie,admin,12:00
"""

# Model that selects from the seed
# Note: When quote_columns=true is set, ALL columns are quoted (lowercase preserved)
# So we need to use quoted lowercase names for all columns
models__test_keywords_sql = """
select 
    "id",
    "name",
    "order",
    "from",
    "date",
    "user",
    "group",
    "time"
from {{ ref('keywords_seed') }}
where "id" = 1
"""

# Schema with quote config
seeds__schema_yml = """
version: 2
seeds:
  - name: keywords_seed
    config:
      quote_columns: true
"""


class TestSeedWithKeywords:
    """Test that seeds with SQL keyword columns work correctly."""

    @pytest.fixture(scope="class")
    def dbt_profile_target(self):
        return {
            "type": "exasol",
            "threads": 1,
            "dsn": os.getenv("DBT_DSN", "localhost:8563"),
            "user": os.getenv("DBT_USER", "sys"),
            "pass": os.getenv("DBT_PASS", "exasol"),
            "dbname": "DB",
            "timestamp_format": "YYYY-MM-DD HH:MI:SS.FF6",
            "validate_server_certificate": False,
        }

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"keywords_seed.csv": seeds__keywords_csv}

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "test_keywords.sql": models__test_keywords_sql,
            "schema.yml": seeds__schema_yml,
        }

    def test_seed_with_keywords(self, project):
        """Test seeding CSV with keyword column names."""
        # Run seed
        results = run_dbt(["seed"])
        assert len(results) == 1

        # Verify data loaded correctly
        sql = "SELECT COUNT(*) as cnt FROM {schema}.keywords_seed"
        result = project.run_sql(sql, fetch="one")
        assert result[0] == 3

        # Verify columns are accessible with quotes
        # Note: quote_columns=true so ALL columns are quoted (lowercase preserved)
        # So we must use quoted lowercase names for all columns
        sql = """SELECT "name", "order", "from" 
                 FROM {schema}.keywords_seed 
                 WHERE "id" = 1"""
        result = project.run_sql(sql, fetch="one")
        assert result[0] == "active"
        assert result[1] == 100  # order is inferred as integer
        assert result[2] == "source1"

        # Verify model referencing seed works
        results = run_dbt(["run"])
        assert len(results) == 1


class TestSeedKeywordsAutoDetect:
    """Test automatic keyword detection without explicit quote config."""

    @pytest.fixture(scope="class")
    def dbt_profile_target(self):
        return {
            "type": "exasol",
            "threads": 1,
            "dsn": os.getenv("DBT_DSN", "localhost:8563"),
            "user": os.getenv("DBT_USER", "sys"),
            "pass": os.getenv("DBT_PASS", "exasol"),
            "dbname": "DB",
            "timestamp_format": "YYYY-MM-DD HH:MI:SS.FF6",
            "validate_server_certificate": False,
        }

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"auto_keywords.csv": seeds__keywords_csv}

    def test_seed_auto_quote_keywords(self, project):
        """Test that keywords are auto-quoted even without config."""
        # Run seed without quote_columns config
        results = run_dbt(["seed"])
        assert len(results) == 1

        # Verify columns with keywords are accessible (quoted)
        # Regular columns like id and name are unquoted (or uppercased)
        sql = """SELECT NAME, "from", "user" 
                 FROM {schema}.auto_keywords 
                 WHERE ID = 2"""
        result = project.run_sql(sql, fetch="one")
        assert result[0] == "pending"
        assert result[1] == "source2"
        assert result[2] == "bob"


class TestSeedMixedQuoting:
    """Test seeds with mixed keyword and regular columns."""

    @pytest.fixture(scope="class")
    def dbt_profile_target(self):
        return {
            "type": "exasol",
            "threads": 1,
            "dsn": os.getenv("DBT_DSN", "localhost:8563"),
            "user": os.getenv("DBT_USER", "sys"),
            "pass": os.getenv("DBT_PASS", "exasol"),
            "dbname": "DB",
            "timestamp_format": "YYYY-MM-DD HH:MI:SS.FF6",
            "validate_server_certificate": False,
        }

    @pytest.fixture(scope="class")
    def seeds(self):
        return {
            "mixed_cols.csv": """id,name,value,description,order
1,Product A,active,desc1,100
2,Product B,pending,desc2,200
"""
        }

    def test_seed_mixed_columns(self, project):
        """Test that only keyword columns are quoted."""
        results = run_dbt(["seed"])
        assert len(results) == 1

        # Regular columns should work unquoted (uppercased by Exasol)
        sql = "SELECT ID, NAME FROM {schema}.mixed_cols WHERE ID = 1"
        result = project.run_sql(sql, fetch="one")
        assert result[0] == 1
        assert result[1] == "Product A"

        # Keyword columns must be quoted (VALUE and ORDER are both keywords)
        # Note: 'value' column uses lowercase in CSV, so it's quoted as "value"
        sql = 'SELECT "value", "order" FROM {schema}.mixed_cols WHERE ID = 2'
        result = project.run_sql(sql, fetch="one")
        assert result[0] == "pending"
        assert result[1] == 200  # order is inferred as integer


class TestSeedKeywordsUppercase:
    """Test seeds with uppercase SQL keyword column names."""

    @pytest.fixture(scope="class")
    def dbt_profile_target(self):
        return {
            "type": "exasol",
            "threads": 1,
            "dsn": os.getenv("DBT_DSN", "localhost:8563"),
            "user": os.getenv("DBT_USER", "sys"),
            "pass": os.getenv("DBT_PASS", "exasol"),
            "dbname": "DB",
            "timestamp_format": "YYYY-MM-DD HH:MI:SS.FF6",
            "validate_server_certificate": False,
        }

    @pytest.fixture(scope="class")
    def seeds(self):
        return {
            "uppercase_keywords.csv": """ID,VALUE,ORDER,FROM
1,active,100,source1
2,pending,101,source2
"""
        }

    def test_seed_uppercase_keywords(self, project):
        """Test that uppercase keyword columns are properly quoted."""
        results = run_dbt(["seed"])
        assert len(results) == 1

        # Verify columns are accessible (keywords should be quoted)
        # Note: Since column names in CSV are uppercase (VALUE, ORDER, FROM),
        # they are quoted preserving case as "VALUE", "ORDER", "FROM"
        sql = 'SELECT "VALUE", "ORDER", "FROM" FROM {schema}.uppercase_keywords WHERE ID = 1'
        result = project.run_sql(sql, fetch="one")
        assert result[0] == "active"
        assert result[1] == 100  # order is inferred as integer
        assert result[2] == "source1"
