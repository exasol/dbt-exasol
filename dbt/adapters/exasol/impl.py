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
from dbt.adapters.contracts.connection import AdapterResponse
from dbt.adapters.contracts.relation import RelationConfig
from dbt.adapters.sql import SQLAdapter
from dbt_common.contracts.constraints import ConstraintType
from dbt_common.contracts.metadata import CatalogTable
from dbt_common.exceptions import CompilationError
from dbt_common.utils import filter_null_values

from dbt.adapters.exasol.column import ExasolColumn
from dbt.adapters.exasol.connections import ExasolConnectionManager
from dbt.adapters.exasol.relation import ExasolRelation

LIST_RELATIONS_MACRO_NAME = "list_relations_without_caching"
PYTHON_MODEL_NOT_SUPPORTED = "Python models are not supported on Exasol"


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

    _capabilities = CapabilityDict(
        {
            Capability.SchemaMetadataByRelations: CapabilitySupport(support=Support.Full),
            Capability.TableLastModifiedMetadata: CapabilitySupport(support=Support.Full),
        }
    )

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
                f'The seed configuration value of "quote_columns" has an ' f"invalid type {type(quote_config)}"
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

    def get_catalog_for_single_relation(self, relation: BaseRelation) -> CatalogTable | None:
        """Get catalog information for a single relation."""
        raise NotImplementedError("`get_catalog_for_single_relation` is not implemented for this adapter")
