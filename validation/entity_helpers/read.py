"""
read.py — data-driven entity field reader.

Instantiate a Reader with a schema name and a raw data dict. Field access
by logical name navigates the dot-notation physical path and applies any
configured type conversion automatically.

Example:
    reader = Reader("loan_v1", loan_data, track_access=True)
    reader.principal      # → 500000.0
    reader.maturity       # → date(2029, 1, 15)
    reader.get_accesses() # → [("principal", "financial.principal_amount"), ...]
"""

import json
from pathlib import Path
from typing import List, Tuple

from . import conversions

# Resolve all public conversion functions by name so JSON string refs work.
_CONVERSIONS = {
    name: fn
    for name, fn in vars(conversions).items()
    if callable(fn) and not name.startswith("_")
}

_SCHEMA_DIR = Path(__file__).parent


class Reader:
    """Data-driven reader for a versioned entity schema.

    Args:
        schema_name: Name of the JSON field definition file without extension
                     (e.g. 'loan_v1' loads 'loan_v1.json' from this directory).
        data:        The raw entity dict to read from.
        track_access: If True, records every field access for dependency
                      introspection via get_accesses().
    """

    def __init__(self, schema_name: str, data: dict, track_access: bool = False):
        schema_path = _SCHEMA_DIR / f"{schema_name}.json"
        with open(schema_path) as f:
            self._fields = json.load(f)
        self._data = data
        self._track_access = track_access
        self._accesses: dict = {}  # (logical, physical) → None, ordered + deduplicated

    def __getattr__(self, logical_name: str):
        # Guard: avoid infinite recursion on private/dunder names.
        if logical_name.startswith("_"):
            raise AttributeError(logical_name)
        field = self._fields.get(logical_name)
        if field is None:
            raise AttributeError(f"Unknown logical field: '{logical_name}'")
        physical_path = field["physical_path"]
        value = self._navigate(physical_path)
        converter = _CONVERSIONS.get(field.get("to_logical"))
        if converter is not None:
            value = converter(value)
        if self._track_access:
            self._accesses[(logical_name, physical_path)] = None
        return value

    def _navigate(self, path: str):
        """Walk a dot-notation path through the raw data dict."""
        node = self._data
        for key in path.split("."):
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        return node

    def get_accesses(self) -> List[Tuple[str, str]]:
        """Return (logical_name, physical_path) pairs in access order."""
        return list(self._accesses.keys())
