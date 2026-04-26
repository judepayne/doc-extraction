"""
Version Registry - Schema Version Routing System

Maps schema URLs to schema names, routing each piece of entity data to the
correct Reader (and its JSON field definitions) based on the declared $schema URL.
"""

import json
import re
import urllib.request
from typing import Optional

from .read import Reader


class VersionRegistry:
    """Maps schema URLs to schema names and creates Reader instances."""

    def __init__(self, config):
        """
        Args:
            config: Either a dict (business config) or a ConfigLoader instance.
        """
        if hasattr(config, "get_business_config"):
            business_config = config.get_business_config()
        elif isinstance(config, dict):
            business_config = config
        else:
            raise ValueError("config must be a dict or ConfigLoader instance")

        self._schema_map = business_config.get("schema_to_helper_mapping", {})
        self._default_helpers = business_config.get("default_helpers", {})
        self._version_compat = business_config.get("version_compatibility", {})
        self._allow_minor_fallback = self._version_compat.get(
            "allow_minor_version_fallback", False
        )
        self._strict_major = self._version_compat.get("strict_major_version", True)

    def detect_schema_version(self, entity_data: dict) -> Optional[str]:
        """Extract and normalise the $schema URL from entity data."""
        schema_uri = entity_data.get("$schema")
        if not schema_uri:
            return None
        if schema_uri in self._schema_map:
            return schema_uri
        if schema_uri.endswith(".json") and (
            "file://" in schema_uri or "https://" in schema_uri
        ):
            try:
                with urllib.request.urlopen(schema_uri, timeout=10) as response:
                    schema = json.loads(response.read())
                    return schema.get("$id", schema_uri)
            except Exception:
                return schema_uri
        return schema_uri

    def parse_schema_url(self, schema_url: str) -> tuple:
        """Parse schema URL into (entity_type, version, major)."""
        parts = schema_url.rstrip("/").split("/")
        if len(parts) < 2:
            raise ValueError(f"Cannot parse schema URL: {schema_url}")
        version_part = parts[-1]

        filename_match = re.match(
            r"^(?P<entity>[A-Za-z0-9_-]+)\.schema\.v(?P<version>\d+\.\d+\.\d+)\.json$",
            version_part,
        )
        if filename_match:
            entity_part = filename_match.group("entity")
            version = filename_match.group("version")
            major = version.split(".")[0]
            return (entity_part, version, major)

        entity_part = parts[-2]
        if not version_part.startswith("v"):
            raise ValueError(f"Version segment must start with 'v': {version_part}")
        version = version_part[1:]
        major = version.split(".")[0]
        return (entity_part, version, major)

    def get_helper(
        self,
        entity_data: dict,
        entity_type: str = None,
        track_access: bool = False,
    ) -> Reader:
        """Resolve the correct Reader instance for the given entity data."""
        schema_name = self._resolve_schema_name(entity_data, entity_type)
        return Reader(schema_name, entity_data, track_access=track_access)

    def _resolve_schema_name(self, entity_data: dict, entity_type: str = None) -> str:
        """Resolve a schema name string (e.g. 'loan_v1') for the given entity data."""
        schema_url = self.detect_schema_version(entity_data)

        if schema_url:
            # Exact match
            schema_name = self._schema_map.get(schema_url)
            if schema_name:
                return schema_name

            # Minor version fallback
            if self._allow_minor_fallback:
                schema_name = self._try_minor_version_fallback(schema_url)
                if schema_name:
                    return schema_name

            if self._strict_major:
                try:
                    entity_part, _, major = self.parse_schema_url(schema_url)
                    for registered_url in self._schema_map:
                        try:
                            reg_entity, _, reg_major = self.parse_schema_url(
                                registered_url
                            )
                            if reg_entity == entity_part and reg_major == major:
                                break
                        except ValueError:
                            continue
                    else:
                        raise ValueError(
                            f"No schema name registered for schema URL: {schema_url}. "
                            f"Unknown major version."
                        )
                except ValueError as e:
                    if "No schema name registered" in str(e):
                        raise

        # Fall back to entity_type default
        resolved_type = entity_type
        if not resolved_type and schema_url:
            try:
                resolved_type, _, _ = self.parse_schema_url(schema_url)
            except ValueError:
                pass

        if resolved_type:
            schema_name = self._default_helpers.get(resolved_type)
            if schema_name:
                return schema_name

        raise ValueError(
            f"Cannot resolve schema name. "
            f"schema_url={schema_url!r}, entity_type={entity_type!r}"
        )

    def _try_minor_version_fallback(self, schema_url: str) -> Optional[str]:
        try:
            entity_type, _, major = self.parse_schema_url(schema_url)
        except ValueError:
            return None
        for registered_url, schema_name in self._schema_map.items():
            try:
                reg_entity, _, reg_major = self.parse_schema_url(registered_url)
                if reg_entity == entity_type and reg_major == major:
                    return schema_name
            except ValueError:
                continue
        return None


_registry: Optional[VersionRegistry] = None


def get_registry(config=None) -> VersionRegistry:
    """Get or initialise the singleton VersionRegistry."""
    global _registry
    if _registry is None:
        if config is None:
            raise RuntimeError(
                "VersionRegistry not initialized. Call get_registry(config) first."
            )
        _registry = VersionRegistry(config)
    return _registry


def reset_registry():
    """Reset the singleton registry (for testing)."""
    global _registry
    _registry = None
