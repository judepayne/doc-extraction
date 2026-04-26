"""
write.py — entity field writer with automatic audit noting.

Wraps a raw entity dict, applies field mutations via dot-notation physical
paths, captures before/after values, and appends a structured audit note
for every write operation.

Example:
    writer = Writer(loan_data)
    note = writer.write(
        business_event="edited",
        message="Updated interest rate following rate reset clause",
        changes={"financial.interest_rate": 0.07}
    )
    # note → "Updated interest rate following rate reset clause:
    #          financial.interest_rate: 0.05 → 0.07"
    # loan_data["notes"] now contains a new structured entry.

    # Note-only write (no field mutations):
    note = writer.write(
        business_event="passed-validated",
        message="Validated against 'quick': all rules passed"
    )
"""

from datetime import datetime, timezone


def _now_iso() -> str:
    """Current UTC time as ISO 8601 string with trailing Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Writer:
    """Wraps a raw entity dict and provides a single, uniform write interface.

    Each call to write() optionally mutates fields, always appends an audit
    note, and returns the note text so callers can include it in responses.

    Args:
        data: The raw entity dict to mutate. Modified in place.
    """

    def __init__(self, data: dict):
        self._data = data

    @property
    def data(self) -> dict:
        """The (possibly mutated) entity dict."""
        return self._data

    def write(self, business_event: str, message: str,
              changes: dict = None) -> str:
        """Apply field changes and append an audit note.

        Args:
            business_event: Operation type recorded in the note
                            (e.g. 'edited', 'passed-validated',
                            'failed-validated', 'note').
            message:        Human-readable description of the operation.
            changes:        Optional dict mapping physical dot-notation paths
                            to their new values, e.g.
                            {'financial.interest_rate': 0.07, 'status': 'closed'}.
                            Before values are captured automatically and appended
                            to the note text.

        Returns:
            The full note text that was written into the entity.
        """
        text = message

        if changes:
            parts = []
            for path, new_value in changes.items():
                old_value = self._navigate(path)
                self._set(path, new_value)
                parts.append(f"{path}: {old_value} → {new_value}")
            text = f"{message}: {'; '.join(parts)}"

        self._data.setdefault("notes", []).append({
            "datetime": _now_iso(),
            "operation_type": business_event,
            "text": text,
        })

        return text

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _navigate(self, path: str):
        """Return the value at a dot-notation path, or None if absent."""
        node = self._data
        for key in path.split("."):
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        return node

    def _set(self, path: str, value) -> None:
        """Set a value at a dot-notation path, creating dicts as needed."""
        keys = path.split(".")
        node = self._data
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        node[keys[-1]] = value
