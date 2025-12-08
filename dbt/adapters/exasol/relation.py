"""dbt-exasol adapter relation module"""

from dataclasses import dataclass, field
from typing import Optional, Type, TypeVar

from dbt.adapters.base.relation import BaseRelation, EventTimeFilter
from dbt.adapters.contracts.relation import Policy, RelationType


@dataclass
class ExasolQuotePolicy(Policy):
    """quote policy - not quotes"""

    database: bool = False
    schema: bool = False
    identifier: bool = False


Self = TypeVar("Self", bound="BaseRelation")


@dataclass(frozen=True, eq=False, repr=False)
class ExasolRelation(BaseRelation):
    """Relation implementation for exasol"""

    quote_policy: ExasolQuotePolicy = field(default_factory=lambda: ExasolQuotePolicy())

    @classmethod
    # pylint: disable=too-many-arguments
    # pylint: disable=redefined-builtin
    # pylint: disable=unused-argument
    def create(
        cls: Type[Self],
        database: Optional[str] = None,
        schema: Optional[str] = None,
        identifier: Optional[str] = None,
        type: Optional[RelationType] = None,
        quote_policy: Type[ExasolQuotePolicy] = quote_policy,
        **kwargs,
    ) -> Self:
        """updating kwargs to set schema and identifier
        Args:
            cls (Type[Self]): _description_
            database (Optional[str], optional): _description_. Defaults to None.
            schema (Optional[str], optional): _description_. Defaults to None.
            identifier (Optional[str], optional): _description_. Defaults to None.
            type (Optional[RelationType], optional): _description_. Defaults to None.

        Returns:
            Self: _description_
        """
        kwargs.update(
            {
                "path": {
                    "schema": schema,
                    "identifier": identifier,
                },
                "type": type,
            }
        )
        return cls.from_dict(kwargs)

    @staticmethod
    def add_ephemeral_prefix(name: str):
        return f"dbt__CTE__{name}"

    def _render_limited_alias(self) -> str:
        """Some databases require an alias for subqueries (postgres, mysql) for all others we want to avoid adding
        an alias as it has the potential to introduce issues with the query if the user also defines an alias.
        """
        if self.require_alias:
            return f" dbt_limit_subq_{self.table}"
        return ""

    def _render_event_time_filtered(self, event_time_filter: EventTimeFilter) -> str:
        """Render event time filter for Exasol.

        Overrides base implementation to format timestamps without timezone suffix,
        as Exasol's TIMESTAMP type doesn't accept timezone notation like '+00:00'.
        """

        # Format datetime to Exasol-compatible format (no timezone)
        def format_ts(dt):
            if dt is None:
                return None
            # Convert datetime to string without timezone
            return dt.strftime("%Y-%m-%d %H:%M:%S")

        start_str = format_ts(event_time_filter.start)
        end_str = format_ts(event_time_filter.end)

        if start_str and end_str:
            return f"{event_time_filter.field_name} >= TIMESTAMP '{start_str}' and {event_time_filter.field_name} < TIMESTAMP '{end_str}'"
        elif start_str:
            return f"{event_time_filter.field_name} >= TIMESTAMP '{start_str}'"
        elif end_str:
            return f"{event_time_filter.field_name} < TIMESTAMP '{end_str}'"
        else:
            return ""

    def _render_subquery_alias(self, namespace: str) -> str:
        """Render subquery alias for Exasol.

        Exasol requires:
        1. The AS keyword before subquery aliases in certain contexts
        2. Quoted identifiers for names starting with underscore
        """
        if self.require_alias:
            # Use dbt_ prefix instead of _dbt_ to avoid needing quotes
            # (Exasol doesn't allow unquoted identifiers starting with _)
            return f" AS dbt_{namespace}_subq_{self.table}"
        return ""
