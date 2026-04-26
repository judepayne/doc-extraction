"""
Rule deal 003 v1: Facility portfolio consistency.

Checks facility IDs, currencies and summary totals across the facility array.
"""

from typing import Tuple

from rules.base import ValidationRule


class Rule(ValidationRule):
    """Checks the consistency of the deal facility portfolio."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "deal"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "Deal facilities must have unique IDs, valid totals, and coherent summary currencies"

    def set_required_data(self, data: dict) -> None:
        """Receive required data before execution."""
        pass

    def run(self) -> Tuple[str, str]:
        """Execute facility portfolio checks."""
        core = self.entity._data.get("core", {})
        summary = core.get("deal_summary", {})
        facilities = core.get("facilities") or []
        errors = []
        warnings = []

        ids = [facility.get("facility_id") for facility in facilities]
        duplicate_ids = sorted({facility_id for facility_id in ids if ids.count(facility_id) > 1})
        if duplicate_ids:
            errors.append("duplicate facility_id values: " + ", ".join(duplicate_ids))

        if len(facilities) < 2:
            warnings.append("deal-level extraction has fewer than two facilities/tranches")

        facility_currencies = {
            facility.get("currency") for facility in facilities if facility.get("currency")
        }
        summary_currencies = set(summary.get("currencies") or [])
        if summary_currencies and not facility_currencies.issubset(summary_currencies):
            missing = sorted(facility_currencies - summary_currencies)
            warnings.append("deal_summary.currencies omits facility currencies: " + ", ".join(missing))

        base_currency = summary.get("base_currency")
        total_facility_amount = summary.get("total_facility_amount")
        if (
            isinstance(total_facility_amount, (int, float))
            and base_currency
            and facility_currencies == {base_currency}
        ):
            facility_sum = sum(facility.get("total_commitment", 0) for facility in facilities)
            tolerance = max(1.0, abs(total_facility_amount) * 0.0001)
            if abs(facility_sum - total_facility_amount) > tolerance:
                errors.append(
                    "deal_summary.total_facility_amount does not equal sum of same-currency facility commitments"
                )

        for facility in facilities:
            facility_id = facility.get("facility_id") or "<missing facility_id>"
            base_equivalent = facility.get("base_currency_equivalent")
            if base_equivalent is not None and not facility.get("base_currency"):
                warnings.append(f"{facility_id}: base_currency_equivalent present without base_currency")
            if facility.get("currency") != base_currency and facility.get("total_commitment") == base_equivalent:
                warnings.append(
                    f"{facility_id}: total_commitment equals base_currency_equivalent; check facility-currency discipline"
                )

        if errors:
            return ("FAIL", "; ".join(errors + warnings))
        if warnings:
            return ("WARN", "; ".join(warnings))
        return ("PASS", "")
