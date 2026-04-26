"""
Rule facility 007 v1: Conditions precedent consistency.

Checks that regulatory consent and security requirements are reflected in the
conditions precedent block when those concerns are extracted.
"""

from typing import Tuple

from rules.base import ValidationRule


def _condition_text(conditions: dict) -> str:
    items = conditions.get("items") or []
    return " ".join((item.get("description") or "") for item in items).lower()


class Rule(ValidationRule):
    """Checks CP consistency for regulatory and security concerns."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "facility"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "Facility conditions precedent should reflect regulatory and security dependencies"

    def set_required_data(self, data: dict) -> None:
        """Receive required data before execution."""
        pass

    def run(self) -> Tuple[str, str]:
        """Execute conditions precedent consistency checks."""
        optional = self.entity._data.get("optional_blocks", {})
        conditions = optional.get("conditions_precedent") or {}
        regulatory = optional.get("regulatory_and_consents") or {}
        term_sheet = optional.get("term_sheet_terms") or {}
        security = optional.get("security_and_guarantees") or {}
        warnings = []

        condition_text = _condition_text(conditions)
        has_conditions = bool(conditions.get("items"))
        regulator_consents = (
            regulatory.get("regulator_consents_required")
            or term_sheet.get("regulator_consents_required")
            or []
        )

        if regulator_consents:
            if not has_conditions:
                warnings.append("regulatory consents are captured but conditions_precedent has no items")
            elif not any(word in condition_text for word in ("regulator", "regulatory", "approval", "consent", "reserve bank")):
                warnings.append("conditions_precedent should include the captured regulatory consent requirement")

        if security.get("secured") is True:
            if not has_conditions:
                warnings.append("secured facility has no conditions_precedent items")
            elif not any(word in condition_text for word in ("security", "secured", "collateral", "charge", "pledge")):
                warnings.append("conditions_precedent should reflect the security requirement")

        if term_sheet.get("definitive_documents_required") is True and not has_conditions:
            warnings.append("definitive documents are required but no conditions_precedent items are captured")

        if warnings:
            return ("WARN", "; ".join(warnings))
        return ("PASS", "")
