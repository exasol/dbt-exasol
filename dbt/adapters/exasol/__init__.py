from dbt.adapters.base import AdapterPlugin

from dbt.adapters.exasol.column import ExasolColumn
from dbt.adapters.exasol.connections import (
    ExasolConnectionManager,
    ExasolCredentials,
)
from dbt.adapters.exasol.impl import ExasolAdapter
from dbt.adapters.exasol.relation import ExasolRelation
from dbt.include import exasol

__all__ = [
    "ExasolAdapter",
    "ExasolColumn",
    "ExasolConnectionManager",
    "ExasolCredentials",
    "ExasolRelation",
    "Plugin",
]

Plugin = AdapterPlugin(
    adapter=ExasolAdapter,
    credentials=ExasolCredentials,
    include_path=exasol.PACKAGE_PATH,
)
