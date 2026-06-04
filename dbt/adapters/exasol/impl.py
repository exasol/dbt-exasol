"""dbt-exasol Adapter implementation extending SQLAdapter"""

from collections.abc import Iterable
from typing import Any

import agate  # type: ignore[import-untyped]
from dbt.adapters.base.impl import (
    AdapterConfig,
    ConstraintSupport,
    PythonJobHelper,
    _expect_row_value,
)
from dbt.adapters.base.meta import available
from dbt.adapters.base.relation import BaseRelation
from dbt.adapters.capability import (
    Capability,
    CapabilityDict,
    CapabilitySupport,
    Support,
)
from dbt.adapters.catalogs import CatalogIntegration
from dbt.adapters.contracts.connection import AdapterResponse
from dbt.adapters.contracts.relation import RelationConfig
from dbt.adapters.sql import SQLAdapter
from dbt_common.behavior_flags import BehaviorFlag
from dbt_common.contracts.constraints import ConstraintType
from dbt_common.contracts.metadata import (
    CatalogTable,
    ColumnMetadata,
    StatsDict,
    TableMetadata,
)
from dbt_common.exceptions import (
    CompilationError,
    DbtRuntimeError,
)
from dbt_common.utils import filter_null_values

from dbt.adapters.exasol.column import ExasolColumn
from dbt.adapters.exasol.connections import ExasolConnectionManager
from dbt.adapters.exasol.relation import ExasolRelation

LIST_RELATIONS_MACRO_NAME = "list_relations_without_caching"
PYTHON_MODEL_NOT_SUPPORTED = "Python models are not supported on Exasol"
CATALOG_INTEGRATION_NOT_SUPPORTED = (
    "Exasol does not support catalog integrations (e.g. Iceberg / external table "
    "formats). Remove the `catalog` config from this model to run it on Exasol."
)


class ExasolNoOpCatalogIntegration(CatalogIntegration):
    """Placeholder catalog integration so a project's ``catalogs.yml`` can parse.

    Exasol has no external table-format / catalog integration. Registering this
    no-op (instead of leaving ``CATALOG_INTEGRATIONS = []``) lets a project that
    declares a ``catalogs.yml`` parse and run as long as no model actually uses a
    catalog. The moment a model resolves a relation against this integration,
    ``build_relation`` raises a clear, Exasol-specific error.
    """

    catalog_type = "built_in"
    allows_writes = True

    def build_relation(self, config: RelationConfig) -> Any:
        raise DbtRuntimeError(CATALOG_INTEGRATION_NOT_SUPPORTED)


class ExasolConfig(
    AdapterConfig
):  # pylint: disable=too-many-ancestors  # Inherits from dbt-core's AdapterConfig chain (unavoidable)
    """Exasol-specific adapter configuration."""

    partition_by_config: str | list[str] | None = None
    distribute_by_config: str | list[str] | None = None
    primary_key_config: str | list[str] | None = None


class ExasolAdapter(SQLAdapter):
    """
    Exasol database adapter implementation.

    Provides Exasol-specific implementations for dbt operations including
    relation management, type conversion, and incremental strategies.
    """

    Relation = ExasolRelation
    Column = ExasolColumn
    ConnectionManager = ExasolConnectionManager

    _exasol_keywords: list[str] | None = None

    CONSTRAINT_SUPPORT = {
        ConstraintType.check: ConstraintSupport.NOT_SUPPORTED,
        ConstraintType.not_null: ConstraintSupport.ENFORCED,
        ConstraintType.unique: ConstraintSupport.NOT_SUPPORTED,
        ConstraintType.primary_key: ConstraintSupport.ENFORCED,
        ConstraintType.foreign_key: ConstraintSupport.ENFORCED,
    }

    # Catalog integrations (Iceberg / external table formats) are not supported by
    # Exasol. We register a single no-op integration so a project's `catalogs.yml`
    # parses and runs when unused; any model that actively resolves a catalog fails
    # with a clear error (see `build_catalog_relation` and
    # `ExasolNoOpCatalogIntegration.build_relation`).
    CATALOG_INTEGRATIONS = [ExasolNoOpCatalogIntegration]

    # Every value of `dbt.adapters.capability.Capability` is declared explicitly so
    # no capability is left implicitly `Unknown` (see the dbt-core-version-parity
    # spec). A unit test asserts this dict covers the full enum.
    _capabilities = CapabilityDict(
        {
            Capability.SchemaMetadataByRelations: CapabilitySupport(support=Support.Full),
            Capability.TableLastModifiedMetadata: CapabilitySupport(support=Support.Full),
            Capability.TableLastModifiedMetadataBatch: CapabilitySupport(support=Support.Full),
            Capability.GetCatalogForSingleRelation: CapabilitySupport(support=Support.Full),
            # Exasol uses optimistic transaction-conflict detection at table
            # granularity: concurrent DELETE+INSERT batches against the same target
            # relation abort each other with "transaction conflict". Microbatch
            # batches must therefore run sequentially. See design.md decision D3 and
            # openspec/changes/add-dbt-111-parity/spike-notes.md.
            Capability.MicrobatchConcurrency: CapabilitySupport(support=Support.Unsupported),
        }
    )

    @property
    def _behavior_flags(self) -> list[BehaviorFlag]:
        """Platform-specific behavior flags for Exasol.

        Behavior flags are how dbt-labs ships opt-in behaviour changes (e.g.
        Snowflake's ``enable_iceberg_materializations``). Exasol needs none today,
        so this returns an empty list. To add one, append a ``BehaviorFlag``
        ``{"name": ..., "default": ..., "description": ...}`` dict here; dbt-core
        merges these with ``DEFAULT_BASE_BEHAVIOR_FLAGS``.

        See ``dbt.adapters.base.impl.BaseAdapter._behavior_flags``.
        """
        return []

    @classmethod
    def date_function(cls):
        return "current_timestamp()"

    @classmethod
    def is_cancelable(cls):
        return False

    @classmethod
    def convert_text_type(cls, agate_table, col_idx):
        return f"varchar({2000000})"

    def _make_match_kwargs(self, database: str, schema: str, identifier: str) -> dict[str, str]:
        quoting = self.config.quoting
        if identifier is not None and quoting["identifier"] is False:
            identifier = identifier.lower()

        if schema is not None and quoting["schema"] is False:
            schema = schema.lower()

        if database is not None and quoting["database"] is False:
            database = database.lower()

        return filter_null_values(
            {
                "identifier": identifier,
                "schema": schema,
            }
        )

    @classmethod
    def convert_number_type(cls, agate_table: agate.Table, col_idx: int) -> str:
        decimals = agate_table.aggregate(agate.MaxPrecision(col_idx))
        return "float" if decimals else "integer"

    def timestamp_add_sql(self, add_to: str, number: int = 1, interval: str = "hour") -> str:
        """
        Overriding BaseAdapter default method because Exasol's syntax expects
        the number in quotes without the interval
        """
        return f"{add_to} + interval '{number}' {interval}"

    def quote_seed_column(self, column: str, quote_config: bool | None) -> str:  # type: ignore
        quote_columns: bool = False
        if isinstance(quote_config, bool):
            quote_columns = quote_config
        elif self.should_identifier_be_quoted(column):
            quote_columns = True
        elif quote_config is not None:
            raise CompilationError(
                f'The seed configuration value of "quote_columns" has an invalid type {type(quote_config)}'
            )

        if quote_columns:
            return self.quote(column)
        return column

    def valid_incremental_strategies(self):
        """The set of standard builtin strategies which this adapter supports out-of-the-box.
        Not used to validate custom strategies defined by end users.
        """
        return ["append", "merge", "delete+insert", "microbatch"]

    @staticmethod
    def is_valid_identifier(identifier) -> bool:
        """
        Check if an identifier is valid according to Exasol naming rules.

        Valid identifiers must start with a letter and contain only
        alphanumeric characters or '#', '$', '_'.
        """
        # Empty string is not a valid identifier
        if not identifier:
            return False
        # The first character should be alphabetic
        if not identifier[0].isalpha():
            return False
        # Rest of the characters is either alphanumeric or any one of the literals '#', '$', '_'
        idx = 1
        while idx < len(identifier):
            identifier_chr = identifier[idx]
            if not identifier_chr.isalnum() and identifier_chr not in ("#", "$", "_"):
                return False
            idx += 1
        return True

    @available
    def should_identifier_be_quoted(self, identifier, models_column_dict=None) -> bool:
        """
        Determine if an identifier should be quoted.

        Returns True if the identifier is a reserved keyword, contains invalid
        characters, or is configured to be quoted in the model.
        """
        # Populate _exasol_keywords List if empty
        if ExasolAdapter._exasol_keywords is None:
            ExasolAdapter._exasol_keywords = self.connections.get_thread_connection().handle.meta.list_sql_keywords()
        # Check if identifier is an Exasol keyword
        if identifier.upper() in ExasolAdapter._exasol_keywords:
            return True
        # Check if the naming is valid
        if not self.is_valid_identifier(identifier):
            return True
        # check if the column is set to be quoted in the model config
        if models_column_dict and identifier in models_column_dict:
            return models_column_dict[identifier].get("quote", False)
        if models_column_dict and self.quote(identifier) in models_column_dict:
            return models_column_dict[self.quote(identifier)].get("quote", False)
        return False

    @available
    def check_and_quote_identifier(self, identifier, models_column_dict=None) -> str:
        """
        Quote an identifier if necessary based on Exasol naming rules.

        Checks if quoting is needed and returns the quoted or unquoted identifier.
        """
        if self.should_identifier_be_quoted(identifier, models_column_dict):
            return self.quote(identifier)
        return identifier

    def get_filtered_catalog(
        self,
        relation_configs: Iterable[RelationConfig],
        used_schemas: frozenset[tuple[str, str]],
        relations: set[BaseRelation] | None = None,
    ):
        catalogs: agate.Table
        if relations is None or len(relations) > 100 or not self.supports(Capability.SchemaMetadataByRelations):
            # Do it the traditional way. We get the full catalog.
            catalogs, exceptions = self.get_catalog(relation_configs, used_schemas)
        else:
            # Do it the new way. We try to save time by selecting information
            # only for the exact set of relations we are interested in.
            catalogs, exceptions = self.get_catalog_by_relations(used_schemas, relations)

        if relations and catalogs:
            relation_map = {
                (
                    r.schema.casefold() if r.schema else None,
                    r.identifier.casefold() if r.identifier else None,
                )
                for r in relations
            }

            def in_map(row: agate.Row):
                s = _expect_row_value("table_schema", row)
                i = _expect_row_value("table_name", row)
                s = s.casefold() if s is not None else None
                i = i.casefold() if i is not None else None
                return (s, i) in relation_map

            catalogs = catalogs.where(in_map)

        return catalogs, exceptions

    def list_relations_without_caching(
        self,
        schema_relation: BaseRelation,
    ) -> list[BaseRelation]:
        kwargs = {"schema_relation": schema_relation}
        results = self.execute_macro(LIST_RELATIONS_MACRO_NAME, kwargs=kwargs)

        relations: list[BaseRelation] = []
        quote_policy = self.config.quoting
        for _database, name, _schema, _type in results:
            try:
                _type = self.Relation.get_relation_type(_type)
            except ValueError:
                _type = self.Relation.External
            relations.append(
                self.Relation.create(
                    database=_database,
                    schema=_schema,
                    identifier=name,
                    quote_policy=quote_policy,
                    type=_type,
                )
            )
        return relations

    @property
    def default_python_submission_method(self) -> str:
        """Python models are not supported on Exasol."""
        raise NotImplementedError(PYTHON_MODEL_NOT_SUPPORTED)

    @property
    def python_submission_helpers(self) -> dict[str, type[PythonJobHelper]]:
        """Python models are not supported on Exasol."""
        raise NotImplementedError(PYTHON_MODEL_NOT_SUPPORTED)

    def generate_python_submission_response(self, submission_result: Any) -> AdapterResponse:
        """Python models are not supported on Exasol."""
        raise NotImplementedError(PYTHON_MODEL_NOT_SUPPORTED)

    def build_catalog_relation(self, config: RelationConfig) -> Any:
        """Reject models that actively request a catalog integration.

        Exasol has no external table-format / catalog integration (Iceberg, etc.).
        A project may still declare a ``catalogs.yml`` and parse/run fine — only a
        model that sets ``config(catalog=...)`` reaches here. We raise a clear
        ``DbtRuntimeError`` instead of letting the base implementation surface a
        ``DbtCatalogIntegrationNotFoundError`` that doesn't mention the platform.
        """
        if config.config and (config.config.get("catalog_name") or config.config.get("catalog")):
            raise DbtRuntimeError(CATALOG_INTEGRATION_NOT_SUPPORTED)
        return None  # pylint: disable=useless-return  # explicit: no catalog relation

    def get_catalog_for_single_relation(self, relation: BaseRelation) -> CatalogTable | None:
        """Get catalog metadata (table + columns) for a single relation.

        Delegates to the ``get_catalog_for_single_relation`` macro, which reuses the
        relation-filtered ``exasol__get_catalog_relations`` where-clause logic so the
        column shape matches the full-schema ``get_catalog`` path. Returns ``None``
        when the relation does not exist (zero rows) so dbt-core's caller can handle
        the absence gracefully.
        """
        from typing import cast

        from dbt_common.clients.agate_helper import table_from_rows

        table = cast(
            agate.Table,
            self.execute_macro(
                "get_catalog_for_single_relation",
                kwargs={"relation": relation},
            ),
        )

        if table is None or len(table) == 0:
            return None

        # The macro already scopes results to this single relation, so we do NOT
        # re-filter by schema (the inherited _catalog_filter_table would drop every
        # row whenever the catalog's literal 'DB' table_database disagrees with the
        # relation's database). We only coerce the metadata columns to text, matching
        # the full-schema catalog path.
        filtered = table_from_rows(
            table.rows,
            table.column_names,
            text_only_columns=[
                "table_database",
                "table_schema",
                "table_name",
                "table_type",
                "table_comment",
                "table_owner",
                "column_name",
                "column_type",
                "column_comment",
            ],
        )

        first = filtered.rows[0]
        table_metadata = TableMetadata(
            type=_expect_row_value("table_type", first),
            database=_expect_row_value("table_database", first),
            schema=_expect_row_value("table_schema", first),
            name=_expect_row_value("table_name", first),
            comment=_expect_row_value("table_comment", first),
            owner=_expect_row_value("table_owner", first),
        )

        columns: dict[str, ColumnMetadata] = {}
        for row in filtered.rows:
            column_name = _expect_row_value("column_name", row)
            columns[column_name] = ColumnMetadata(
                type=_expect_row_value("column_type", row),
                index=int(_expect_row_value("column_index", row)),
                name=column_name,
                comment=_expect_row_value("column_comment", row),
            )

        stats: StatsDict = {}
        return CatalogTable(metadata=table_metadata, columns=columns, stats=stats)
