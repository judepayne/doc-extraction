"""
Rule facility 008 v1: Provenance and source trace.

Checks that the extraction records enough provenance to support audit and
human review.
"""

from typing import Tuple

from rules.base import ValidationRule


MATERIAL_BLOCKS = (
    "interest_terms",
    "repayment_and_maturity",
    "security_and_guarantees",
    "collateral_perfection",
    "conditions_precedent",
    "events_of_default",
    "prepayment_and_cancellation",
    "amendment_overlay",
)


class Rule(ValidationRule):
    """Checks extraction provenance and source trace."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "facility"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "Facility extraction should include source trace and evidence for material blocks"

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
