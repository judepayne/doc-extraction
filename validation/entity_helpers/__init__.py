"""
Entity helper classes for validation rules.

Provides a stable, data-driven interface to entity data that shields
validation rules from internal data model structure changes.
"""

from .read import Reader
from .version_registry import get_registry

__all__ = ["Reader", "get_registry", "create_entity_helper"]


def create_entity_helper(
    entity_type: str, entity_data: dict, track_access: bool = False
) -> Reader:
    """
    Factory: return a Reader for the correct schema version of entity_data.

    Args:
        entity_type: Type of entity ('loan', 'facility', 'deal')
        entity_data: Raw entity data as a dict (may contain a '$schema' field)
        track_access: If True, record field accesses for discover_rules

    Returns:
        Reader instance configured for the resolved schema version.
    """
    registry = get_registry()
    return registry.get_helper(entity_data, entity_type, track_access=track_access)
