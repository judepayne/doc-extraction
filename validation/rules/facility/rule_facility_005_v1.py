"""
Rule facility 005 v1: Date and maturity sanity.

Checks that agreement, availability, maturity and termination information is
chronologically plausible when present.
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
    """Checks date and maturity sanity."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "facility"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "Facility dates and maturity terms must be chronologically plausible"

    def set_required_data(self, data: dict) -> None:
        """Receive required data before execution."""
        pass

    def run(self) -> Tuple[str, str]:
        """Execute date sanity checks."""
        data = self.entity._data
        document = data.get("core", {}).get("document", {})
        optional = data.get("optional_blocks", {})
        availability = optional.get("availability_and_utilisation") or {}
        repayment = optional.get("repayment_and_maturity") or {}
        errors = []
        warnings = []

        start = (
            _parse_date(document.get("agreement_date"))
            or _parse_date(document.get("effective_date"))
            or _parse_date(document.get("document_date"))
        )
        availability_start = _parse_date(availability.get("availability_period_start"))
        availability_end = _parse_date(availability.get("availability_period_end"))
        maturity = _parse_date(repayment.get("maturity_date"))
        termination = _parse_date(repayment.get("termination_date"))
        end = maturity or termination

        if availability_start and availability_end and availability_end < availability_start:
            errors.append("availability_period_end is before availability_period_start")
        if start and availability_end and availability_end < start:
            errors.append("availability_period_end is before the document start date")
        if start and end and end <= start:
            errors.append("maturity/termination date must be after the document start date")
        if availability_end and end and end < availability_end:
            errors.append("maturity/termination date is before availability_period_end")

        tenor_months = repayment.get("tenor_months")
        if tenor_months is not None and tenor_months <= 0:
            errors.append("tenor_months must be positive")

        if not end and not tenor_months and not repayment.get("termination_basis"):
            warnings.append("No maturity date, termination date, tenor, or termination basis captured")

        if errors:
            return ("FAIL", "; ".join(errors + warnings))
        if warnings:
            return ("WARN", "; ".join(warnings))
        return ("PASS", "")
