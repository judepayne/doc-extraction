"""
Rule facility 004 v1: Interest terms consistency.

Checks that extracted interest mechanics are internally coherent for fixed,
floating and reference-rate-only facilities.
"""

from typing import Tuple

from rules.base import ValidationRule


class Rule(ValidationRule):
    """Checks interest term consistency."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "facility"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "Facility interest terms must be internally consistent"

    def set_required_data(self, data: dict) -> None:
        """Receive required data before execution."""
        pass

    def run(self) -> Tuple[str, str]:
        """Execute interest consistency checks."""
        data = self.entity._data
        document_type = data.get("core", {}).get("document", {}).get("document_type")
        interest = data.get("optional_blocks", {}).get("interest_terms")
        errors = []
        warnings = []

        if not interest:
            if document_type == "facility_agreement":
                return ("WARN", "facility_agreement should usually include interest_terms")
            return ("PASS", "")

        rate_type = interest.get("rate_type")
        if rate_type == "fixed":
            fixed_rate = interest.get("fixed_rate_pct")
            if not isinstance(fixed_rate, (int, float)) or fixed_rate < 0:
                errors.append("fixed interest requires non-negative fixed_rate_pct")
        elif rate_type == "floating_reference_plus_margin":
            if not (interest.get("reference_rate_name") or interest.get("reference_rate_canonical")):
                errors.append("floating interest requires reference_rate_name or reference_rate_canonical")
            margin_pct = interest.get("margin_pct")
            margin_bps = interest.get("margin_bps")
            if margin_pct is None and margin_bps is None:
                errors.append("floating interest requires margin_pct or margin_bps")
            if isinstance(margin_pct, (int, float)) and margin_pct < 0:
                errors.append("margin_pct must not be negative")
            if isinstance(margin_bps, (int, float)) and margin_bps < 0:
                errors.append("margin_bps must not be negative")
        elif rate_type == "reference_rate_only":
            if not (interest.get("reference_rate_name") or interest.get("reference_rate_canonical")):
                errors.append("reference_rate_only requires reference_rate_name or reference_rate_canonical")
        elif not rate_type:
            errors.append("interest_terms.rate_type is required when interest_terms is present")

        default_uplift = interest.get("default_interest_uplift_pct")
        if isinstance(default_uplift, (int, float)) and default_uplift < 0:
            errors.append("default_interest_uplift_pct must not be negative")

        capitalisation = interest.get("capitalisation") or {}
        if capitalisation.get("permitted") is True and not capitalisation.get("frequency"):
            warnings.append("capitalised interest should state capitalisation.frequency")

        if errors:
            return ("FAIL", "; ".join(errors + warnings))
        if warnings:
            return ("WARN", "; ".join(warnings))
        return ("PASS", "")
