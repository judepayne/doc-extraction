"""
Rule deal 008 v1: Provenance and source trace.

Checks that deal extraction records enough provenance and source evidence for
audit and human review.
"""

from typing import Tuple

from rules.base import ValidationRule


MATERIAL_BLOCKS = (
    "transaction_context",
    "lender_commitments",
    "lender_classes_and_voting",
    "trading_transfers_and_assignments",
    "amendments_and_waivers",
    "agency_payments_and_settlement",
    "cash_waterfalls",
    "security_and_guarantees",
    "intercreditor_and_subordination",
    "collateral_perfection_timetable",
    "financial_covenants",
    "covenant_calculation_definitions",
    "repayment_and_amortisation",
    "interest_and_benchmark_terms",
    "prepayment_and_cancellation",
    "conditions_precedent",
)


class Rule(ValidationRule):
    """Checks deal extraction provenance and source trace."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "deal"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "Deal extraction should include source trace and evidence for material blocks"

    def set_required_data(self, data: dict) -> None:
        """Receive required data before execution."""
        pass

    def run(self) -> Tuple[str, str]:
        """Execute provenance checks."""
        data = self.entity._data
        source_trace = data.get("source_trace") or {}
        optional = data.get("optional_blocks") or {}
        errors = []
        warnings = []

        if not source_trace.get("source_document"):
            errors.append("source_trace.source_document is required for auditability")
        if not source_trace.get("extraction_method"):
            errors.append("source_trace.extraction_method is required for auditability")

        facilities = data.get("core", {}).get("facilities") or []
        facilities_without_refs = [
            facility.get("facility_id") or "<missing facility_id>"
            for facility in facilities
            if not facility.get("source_refs")
        ]
        if facilities_without_refs:
            warnings.append(
                "core facilities lack source_refs: " + ", ".join(facilities_without_refs)
            )

        blocks_without_refs = []
        for block_name in MATERIAL_BLOCKS:
            block = optional.get(block_name)
            if isinstance(block, dict) and block and not block.get("source_refs"):
                blocks_without_refs.append(block_name)

        if blocks_without_refs:
            warnings.append(
                "material optional blocks lack block-level source_refs: "
                + ", ".join(blocks_without_refs)
            )

        if errors:
            return ("FAIL", "; ".join(errors + warnings))
        if warnings:
            return ("WARN", "; ".join(warnings))
        return ("PASS", "")
