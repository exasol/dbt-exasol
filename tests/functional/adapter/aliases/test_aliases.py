import pytest
from dbt.tests.adapter.aliases.test_aliases import BaseAliases

MACROS__EXASOL_CAST_SQL = """
{% macro exasol__string_literal(s) %}
    TO_CHAR('{{ s }}')
{% endmacro %}
"""

MACROS__EXPECT_VALUE_SQL = """
-- cross-db compatible test, similar to accepted_values

{% test expect_value(model, field, value) %}

select *
from {{ model }}
where {{ field }} != '{{ value }}'

{% endtest %}
"""


class TestAliasesExasol(BaseAliases):
    @pytest.fixture(scope="class")
    def macros(self):
        return {
            "exasol_cast.sql": MACROS__EXASOL_CAST_SQL,
            "expect_value.sql": MACROS__EXPECT_VALUE_SQL,
        }
