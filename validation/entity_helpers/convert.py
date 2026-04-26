"""
convert.py — bidirectional conversion between physical and logical representations.

A Converter is instantiated with a schema name (e.g. 'loan_v1') and provides two
methods:

  convert_to_logical(physical_data)
      Takes a raw nested physical dict and returns a flat dict keyed by logical
      field names, with type conversions applied (e.g. date strings → date objects).
      All defined fields are included; absent fields appear with a None value.

  convert_to_physical(logical_data)
      Takes a flat dict keyed by logical field names and returns a nested physical
      dict with the correct dot-notation structure and reverse type conversions
      applied (e.g. date objects → ISO strings). None values are omitted so no
      empty nested structure is created.

Example:
    converter = Converter("loan_v1")

    logical = converter.convert_to_logical(raw_loan)
    # → {"id": "LOAN-1", "principal": 500000, "inception": date(2024, 1, 15), ...}

    physical = converter.convert_to_physical(logical)
    # → {"id": "LOAN-1", "financial": {"principal_amount": 500000}, ...}
"""

import json
from pathlib import Path

from . import conversions

# Resolve all public conversion functions by name so JSON string refs work.
_CONVERSIONS = {
    name: fn
    for name, fn in vars(conversions).items()
    if callable(fn) and not name.startswith("_")
}

_SCHEMA_DIR = Path(__file__).parent


class Converter:
    """Bidirectional converter between physical and logical entity representations.

    Args:
        schema_name: Name of the JSON field definition file without extension
                     (e.g. 'loan_v1' loads 'loan_v1.json' from this directory).
    """

    def __init__(self, schema_name: str):
        schema_path = _SCHEMA_DIR / f"{schema_name}.json"
        with open(schema_path) as f:
            self._fields = json.load(f)

    def convert_to_logical(self, physical_data: dict) -> dict:
        """Convert a raw nested physical dict to a flat logical dict.

        Every field defined in the schema is included. Fields absent from the
        physical data appear as None. Type conversions (e.g. str → date) are
        applied where defined.

        Args:
            physical_data: Raw entity dict as stored/exchanged in JSON.

        Returns:
            Flat dict keyed by logical field names.
        """
        result = {}
        for logical_name, field in self._fields.items():
            value = self._navigate(physical_data, field["physical_path"])
            converter = _CONVERSIONS.get(field.get("to_logical"))
            if converter is not None:
                value = converter(value)
            result[logical_name] = value
        return result

    def convert_to_physical(self, logical_data: dict) -> dict:
        """Convert a flat logical dict back to a nested physical dict.

        Only fields defined in the schema are written; unknown logical keys are
        ignored. None values are skipped so no empty nested structure is created.
        Reverse type conversions (e.g. date → str) are applied where defined.

        Args:
            logical_data: Flat dict keyed by logical field names.

        Returns:
            Nested physical dict suitable for JSON serialisation.
        """
        result = {}
        for logical_name, value in logical_data.items():
            if value is None:
                continue
            field = self._fields.get(logical_name)
            if field is None:
                continue
            converter = _CONVERSIONS.get(field.get("to_physical"))
            if converter is not None:
                value = converter(value)
            self._set(result, field["physical_path"], value)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _navigate(self, data: dict, path: str):
        """Walk a dot-notation path through a nested dict. Returns None if absent."""
        node = data
        for key in path.split("."):
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        return node

    def _set(self, data: dict, path: str, value) -> None:
        """Set a value at a dot-notation path, creating intermediate dicts as needed."""
        keys = path.split(".")
        node = data
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        node[keys[-1]] = value
