"""dbt-exasol adapter package initialization"""

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
    "PLUGIN",
    "Plugin",
]

PLUGIN = AdapterPlugin(
    adapter=ExasolAdapter,  # type: ignore[arg-type]
    credentials=ExasolCredentials,
    include_path=exasol.PACKAGE_PATH,
)

# dbt-core 1.11+ expects Plugin (capital P only) instead of PLUGIN
Plugin = PLUGIN
