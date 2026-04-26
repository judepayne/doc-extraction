"""
Rule facility 003 v1: Document subtype consistency.

Checks that specialised facility document types have the matching optional
blocks needed to preserve their commercial/legal meaning.
"""

from typing import Tuple

from rules.base import ValidationRule


class Rule(ValidationRule):
    """Checks document subtype and optional-block consistency."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "facility"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "Facility document subtype must be consistent with optional blocks"

    def set_required_data(self, data: dict) -> None:
        """Receive required data before execution."""
        pass

    def run(self) -> Tuple[str, str]:
        """Execute subtype consistency checks."""
        data = self.entity._data
        document = data.get("core", {}).get("document", {})
        parties = data.get("core", {}).get("parties", {})
        optional = data.get("optional_blocks", {})
        document_type = document.get("document_type")
        errors = []
        warnings = []

        if document_type == "loan_facility_term_sheet":
            term_sheet = optional.get("term_sheet_terms")
            if not term_sheet:
                errors.append("loan_facility_term_sheet requires optional_blocks.term_sheet_terms")
            elif "binding" not in term_sheet:
                warnings.append("term_sheet_terms should state whether the term sheet is binding")

        if document_type in {"credit_agreement_amendment", "facility_amendment"}:
            amendment = optional.get("amendment_overlay")
            if not amendment:
                errors.append(f"{document_type} requires optional_blocks.amendment_overlay")
            elif not amendment.get("base_agreement"):
                warnings.append("amendment_overlay should identify the base agreement")

        public_lenders = [
            party for party in parties.get("lenders", [])
            if party.get("party_type") == "government_or_public_body"
        ]
        if public_lenders and not optional.get("public_sector_terms"):
            warnings.append("public-body lender should be supported by public_sector_terms")

        if document_type != "loan_facility_term_sheet" and optional.get("term_sheet_terms"):
            warnings.append("term_sheet_terms present but document_type is not loan_facility_term_sheet")

        if errors:
            message = "; ".join(errors + warnings)
            return ("FAIL", message)
        if warnings:
            return ("WARN", "; ".join(warnings))
        return ("PASS", "")
