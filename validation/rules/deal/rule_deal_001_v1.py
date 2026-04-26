"""
Rule deal 001 v1: JSON Schema validation.

Validates that a deal extraction conforms to its declared JSON schema.
"""

from typing import Tuple

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from rules.base import ValidationRule
from schema_helpers import load_schema


class Rule(ValidationRule):
    """Validates deal entity data against its declared JSON schema."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "deal"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "Deal extraction must conform to its declared JSON schema"

    def set_required_data(self, data: dict) -> None:
        """Receive required data before execution."""
        pass

    def run(self) -> Tuple[str, str]:
        """Execute schema validation."""
        entity_data = self.entity._data
        schema_url = entity_data.get("$schema")
        if not schema_url:
            return ("FAIL", "Deal extraction missing required $schema field")

        try:
            schema = load_schema(schema_url)
        except RuntimeError as e:
            return ("NORUN", str(e))

        try:
            validator = Draft202012Validator(
                schema,
                format_checker=FormatChecker(),
            )
            validator.validate(entity_data)
            return ("PASS", "")
        except ValidationError as e:
            error_path = " -> ".join(str(p) for p in e.path) if e.path else "root"
            return ("FAIL", f"Schema validation failed at {error_path}: {e.message}")
        except Exception as e:
            return ("FAIL", f"Schema validation error: {str(e)}")
