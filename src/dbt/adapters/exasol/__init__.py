from dbt.adapters.exasol.connections import (
    ExasolConnectionManager as ExasolConnectionManager,
)
from dbt.adapters.exasol.connections import ExasolCredentials
from dbt.adapters.exasol.column import ExasolColumn as ExasolColumn
from dbt.adapters.exasol.relation import ExasolRelation as ExasolRelation
from dbt.adapters.exasol.impl import ExasolAdapter

from dbt.adapters.base import AdapterPlugin
from dbt.include import exasol


Plugin = AdapterPlugin(
    adapter=ExasolAdapter,
    credentials=ExasolCredentials,
    include_path=exasol.PACKAGE_PATH,
)
