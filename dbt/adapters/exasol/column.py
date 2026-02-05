"""
dbt exasol adapter column module
"""

import re
from dataclasses import dataclass
from typing import ClassVar

from dbt.adapters.base.column import Column
from dbt_common.exceptions import DbtRuntimeError  # pylint: disable=wrong-import-order


@dataclass
# pylint: disable=missing-function-docstring
class ExasolColumn(Column):
    """Column implementation for exasol"""

    # https://docs.exasol.com/db/latest/sql_references/data_types/datatypealiases.htm
    TYPE_LABELS: ClassVar[dict[str, str]] = {
        "STRING": "VARCHAR(2000000) UTF8",
        "TIMESTAMP": "TIMESTAMP",
        "FLOAT": "DOUBLE PRECISION",
        "INTEGER": "DECIMAL(18,0)",
        "BIGINT": "DECIMAL(36,0)",
        "NUMERIC": "DECIMAL(18,9)",
    }

    def is_numeric(self) -> bool:
        return self.dtype.lower() in ["decimal", "double"]

    def is_integer(self) -> bool:
        # everything that smells like an int is actually a DECIMAL(18, 0)
        return self.is_numeric() and self.numeric_scale == 0

    def is_float(self):
        return self.dtype.lower() == "double"

    def is_string(self) -> bool:
        return self.dtype.lower() in ["char", "varchar"]

    def is_hashtype(self) -> bool:
        return self.dtype.lower() == "hashtype"

    def is_boolean(self) -> bool:
        return self.dtype.lower() == "boolean"

    def is_timestamp(self) -> bool:
        # handle TIMESTAMP and TIMESTAMP WITH LOCAL TIME ZONE
        return self.dtype.lower().startswith("timestamp")

    def is_date(self) -> bool:
        return self.dtype.lower() == "date"

    def string_size(self) -> int:
        if not self.is_string():
            raise DbtRuntimeError("Called string_size() on non-string field!")
        if self.char_size is None:
            return 2000000
        return int(self.char_size)

    @classmethod
    def string_type(cls, size: int) -> str:
        return f"VARCHAR({size})"

    @classmethod
    # pylint: disable=raise-missing-from
    def from_description(cls, name: str, raw_data_type: str) -> "Column":
        match = re.match(r"([^(]+)(\([^)]+\))?", raw_data_type)
        if match is None:
            raise DbtRuntimeError(f'Could not interpret data type "{raw_data_type}"')
        data_type, size_info = match.groups()
        char_size = None
        numeric_precision = None
        numeric_scale = None
        if size_info is not None:
            # strip out the parentheses
            size_info = size_info[1:-1]
            parts = size_info.split(",")
            if len(parts) == 1:
                try:
                    # handle things like HASHTYPE(16 BYTE)
                    size = re.sub(r"[^\d]", "", parts[0])
                    char_size = int(size)
                except ValueError:
                    raise DbtRuntimeError(
                        f'Could not interpret data_type "{raw_data_type}": could not convert "{parts[0]}" to an integer'
                    )
            elif len(parts) == 2:
                try:
                    numeric_precision = int(parts[0])
                except ValueError:
                    raise DbtRuntimeError(
                        f'Could not interpret data_type "{raw_data_type}": could not convert "{parts[0]}" to an integer'
                    )
                try:
                    numeric_scale = int(parts[1])
                except ValueError:
                    raise DbtRuntimeError(
                        f'Could not interpret data_type "{raw_data_type}": could not convert "{parts[1]}" to an integer'
                    )

        return cls(name, data_type, char_size, numeric_precision, numeric_scale)
