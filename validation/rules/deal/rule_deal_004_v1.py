"""
Rule deal 004 v1: Lender commitment reconciliation.

Checks that original lender commitments use known facility IDs and reconcile to
facility totals where enough data is present.
"""

from typing import Tuple

from rules.base import ValidationRule


class Rule(ValidationRule):
    """Checks lender commitment mappings and totals."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "deal"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "Original lender commitments should use facility IDs and reconcile to facility totals"

    def set_required_data(self, data: dict) -> None:
        """Receive required data before execution."""
        pass

    def run(self) -> Tuple[str, str]:
        """Execute lender commitment checks."""
        data = self.entity._data
        facilities = data.get("core", {}).get("facilities") or []
        optional = data.get("optional_blocks", {})
        commitment_block = optional.get("lender_commitments") or {}
        original_lenders = commitment_block.get("original_lenders") or []
        facility_ids = {facility.get("facility_id") for facility in facilities}
        facility_totals = {
            facility.get("facility_id"): facility.get("total_commitment")
            for facility in facilities
            if facility.get("facility_id")
        }
        errors = []
        warnings = []

        if not original_lenders:
            core_lenders = data.get("core", {}).get("finance_parties", {}).get("original_lenders") or []
            if core_lenders:
                warnings.append("core original_lenders are present but optional_blocks.lender_commitments is absent")
            return ("WARN", "; ".join(warnings)) if warnings else ("PASS", "")

        sums = {facility_id: 0 for facility_id in facility_ids}
        seen_any_by_facility = set()
        for lender in original_lenders:
            name = lender.get("name") or "<unnamed lender>"
            commitments = lender.get("commitments_by_facility") or {}
            if not commitments:
                warnings.append(f"{name}: no commitments_by_facility captured")
                continue
            for facility_id, amount in commitments.items():
                if facility_id not in facility_ids:
                    errors.append(f"{name}: commitment references unknown facility_id '{facility_id}'")
                    continue
                if not isinstance(amount, (int, float)) or amount < 0:
                    errors.append(f"{name}: commitment for {facility_id} must be a non-negative number")
                    continue
                sums[facility_id] += amount
                seen_any_by_facility.add(facility_id)

        totals_by_facility = commitment_block.get("total_commitments_by_facility") or {}
        for facility_id, stated_total in totals_by_facility.items():
            if facility_id not in facility_ids:
                errors.append(f"total_commitments_by_facility references unknown facility_id '{facility_id}'")
            elif isinstance(stated_total, (int, float)) and facility_id in seen_any_by_facility:
                tolerance = max(1.0, abs(stated_total) * 0.0001)
                if abs(sums[facility_id] - stated_total) > tolerance:
                    errors.append(f"summed lender commitments for {facility_id} do not match stated total")

        for facility_id in seen_any_by_facility:
            facility_total = facility_totals.get(facility_id)
            if isinstance(facility_total, (int, float)):
                tolerance = max(1.0, abs(facility_total) * 0.0001)
                if abs(sums[facility_id] - facility_total) > tolerance:
                    errors.append(f"summed lender commitments for {facility_id} do not match core facility total")

        if errors:
            return ("FAIL", "; ".join(errors + warnings))
        if warnings:
            return ("WARN", "; ".join(warnings))
        return ("PASS", "")
