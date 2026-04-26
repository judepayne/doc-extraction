"""
conversions.py — bidirectional type conversion functions for entity fields.

Each pair of functions converts between the physical representation (what is
stored in JSON) and the logical representation (what rules and helpers work with).

Designed to be passed as coercion functions in BiDict field definitions.
"""

from datetime import date, datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# date  ←→  ISO 8601 string  ("2024-01-15")
# ---------------------------------------------------------------------------

def str_to_date(value: Optional[str]) -> Optional[date]:
    """Parse an ISO 8601 date string into a date object. Returns None if absent."""
    if not value:
        return None
    return date.fromisoformat(value)


def date_to_str(value: Optional[date]) -> Optional[str]:
    """Serialise a date object to an ISO 8601 string. Returns None if absent."""
    if value is None:
        return None
    return value.isoformat()


# ---------------------------------------------------------------------------
# datetime  ←→  ISO 8601 string with UTC Z  ("2024-01-15T09:00:00Z")
# ---------------------------------------------------------------------------

def str_to_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO 8601 datetime string (with optional Z suffix) into a
    timezone-aware datetime object. Returns None if absent."""
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def datetime_to_str(value: Optional[datetime]) -> Optional[str]:
    """Serialise a datetime object to an ISO 8601 string with a trailing Z.
    Naive datetimes are assumed to be UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")
