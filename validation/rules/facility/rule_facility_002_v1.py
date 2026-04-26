"""
Rule facility 002 v1: Core business completeness.

Checks that the facility extraction contains the minimum high-value business
facts a bank user needs, beyond mere JSON Schema object presence.
"""

from typing import Tuple

from rules.base import ValidationRule


class Rule(ValidationRule):
    """Checks facility core business completeness."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "facility"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "Facility core must contain borrower, finance party, economics, and governing law"

    def set_required_data(self, data: dict) -> None:
        """Receive required data before execution."""
        pass

    def run(self) -> Tuple[str, str]:
        """Execute core completeness checks."""
        errors = []
        data = self.entity._data
        core = data.get("core", {})
        parties = core.get("parties", {})
        facility = core.get("facility", {})
        legal = core.get("legal", {})

        borrowers = parties.get("borrowers") or []
        if not borrowers or not any((p.get("name") or "").strip() for p in borrowers):
            errors.append("At least one borrower with a name is required")

        finance_parties = []
        for key in ("lenders", "agents", "arrangers"):
            finance_parties.extend(parties.get(key) or [])
        if not any((p.get("name") or "").strip() for p in finance_parties):
            errors.append("At least one lender, agent, or arranger with a name is required")

        if not (facility.get("facility_id") or "").strip():
            errors.append("core.facility.facility_id is required and must be non-empty")
        if not (facility.get("type") or "").strip():
            errors.append("core.facility.type is required and must be non-empty")
        if not (facility.get("currency") or "").strip():
            errors.append("core.facility.currency is required and must be non-empty")

        commitment = facility.get("commitment_amount")
        if not isinstance(commitment, (int, float)) or commitment <= 0:
            errors.append("core.facility.commitment_amount must be a positive number")

        if not (legal.get("governing_law") or "").strip():
            errors.append("core.legal.governing_law is required and must be non-empty")

        if errors:
            return ("FAIL", "; ".join(errors))
        return ("PASS", "")
