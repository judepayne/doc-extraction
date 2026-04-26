"""
Rule deal 002 v1: Core business completeness.

Checks that a deal extraction contains the minimum high-value business facts
needed by bank users beyond bare JSON Schema object presence.
"""

from typing import Tuple

from rules.base import ValidationRule


def _has_party_name(value) -> bool:
    if isinstance(value, dict):
        return bool((value.get("name") or "").strip())
    if isinstance(value, list):
        return any(_has_party_name(item) for item in value)
    return False


class Rule(ValidationRule):
    """Checks deal core business completeness."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "deal"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "Deal core must contain obligor group, agent, facilities, and governing law"

    def set_required_data(self, data: dict) -> None:
        """Receive required data before execution."""
        pass

    def run(self) -> Tuple[str, str]:
        """Execute core completeness checks."""
        data = self.entity._data
        core = data.get("core", {})
        summary = core.get("deal_summary", {})
        obligors = core.get("obligor_group", {})
        finance_parties = core.get("finance_parties", {})
        facilities = core.get("facilities") or []
        legal = core.get("legal", {})
        errors = []

        if not summary.get("agreement_date"):
            errors.append("core.deal_summary.agreement_date is required")

        if not any(
            _has_party_name(obligors.get(key))
            for key in ("company", "borrower", "borrowers", "original_borrowers")
        ):
            errors.append("obligor_group must identify a company, borrower, borrowers, or original_borrowers")

        if not _has_party_name(finance_parties.get("agent")):
            errors.append("core.finance_parties.agent with a name is required")

        if not facilities:
            errors.append("core.facilities must contain at least one facility")
        for facility in facilities:
            facility_id = facility.get("facility_id") or "<missing facility_id>"
            if not (facility.get("facility_id") or "").strip():
                errors.append("each facility requires a non-empty facility_id")
            if not (facility.get("type") or "").strip():
                errors.append(f"{facility_id}: facility type is required")
            if not (facility.get("currency") or "").strip():
                errors.append(f"{facility_id}: currency is required")
            total = facility.get("total_commitment")
            if not isinstance(total, (int, float)) or total <= 0:
                errors.append(f"{facility_id}: total_commitment must be a positive number")

        if not (legal.get("governing_law") or "").strip():
            errors.append("core.legal.governing_law is required and must be non-empty")

        if errors:
            return ("FAIL", "; ".join(errors))
        return ("PASS", "")
