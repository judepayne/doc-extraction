"""
Rule deal 005 v1: Facility economics and date sanity.

Checks facility-level margins, dates, termination and availability fields within
a deal-level extraction.
"""

from datetime import date
from typing import Tuple

from rules.base import ValidationRule


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


class Rule(ValidationRule):
    """Checks facility economics and date sanity."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "deal"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "Deal facility economics and dates must be plausible"

    def set_required_data(self, data: dict) -> None:
        """Receive required data before execution."""
        pass

    def run(self) -> Tuple[str, str]:
        """Execute facility economics/date checks."""
        core = self.entity._data.get("core", {})
        agreement_date = _parse_date(core.get("deal_summary", {}).get("agreement_date"))
        facilities = core.get("facilities") or []
        errors = []
        warnings = []

        for facility in facilities:
            facility_id = facility.get("facility_id") or "<missing facility_id>"
            margin = facility.get("margin_pct")
            if isinstance(margin, (int, float)) and margin < 0:
                errors.append(f"{facility_id}: margin_pct must not be negative")

            availability_end = _parse_date(facility.get("availability_period_end"))
            termination = _parse_date(facility.get("termination_date"))
            if agreement_date and availability_end and availability_end < agreement_date:
                errors.append(f"{facility_id}: availability_period_end is before agreement_date")
            if agreement_date and termination and termination <= agreement_date:
                errors.append(f"{facility_id}: termination_date must be after agreement_date")
            if availability_end and termination and termination < availability_end:
                errors.append(f"{facility_id}: termination_date is before availability_period_end")

            reference_name = facility.get("reference_rate_name")
            reference_canonical = facility.get("reference_rate_canonical")
            if reference_name and not reference_canonical:
                warnings.append(f"{facility_id}: reference_rate_name present without reference_rate_canonical")
            if facility.get("type") in {"term_loan_bullet", "term_loan_amortising"}:
                if facility.get("letters_of_credit_permitted") is True:
                    warnings.append(f"{facility_id}: term facility has letters_of_credit_permitted true; confirm source")

        if errors:
            return ("FAIL", "; ".join(errors + warnings))
        if warnings:
            return ("WARN", "; ".join(warnings))
        return ("PASS", "")
