"""
Rule deal 007 v1: Voting, amendment and transfer mechanics consistency.

Checks that detailed voting/amendment/transfer blocks are not internally thin
or contradictory when they are present.
"""

from typing import Tuple

from rules.base import ValidationRule


class Rule(ValidationRule):
    """Checks voting, amendment and transfer mechanics."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "deal"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "Deal voting, amendment and transfer mechanics should be coherent when captured"

    def set_required_data(self, data: dict) -> None:
        """Receive required data before execution."""
        pass

    def run(self) -> Tuple[str, str]:
        """Execute voting/amendment/transfer checks."""
        optional = self.entity._data.get("optional_blocks", {})
        voting = optional.get("lender_classes_and_voting") or {}
        amendments = optional.get("amendments_and_waivers") or {}
        transfers = optional.get("trading_transfers_and_assignments") or {}
        errors = []
        warnings = []

        if voting:
            has_thresholds = any(
                voting.get(key)
                for key in (
                    "majority_lenders_definition",
                    "super_majority_lenders_definition",
                    "all_lender_matters",
                    "class_matters",
                    "ordinary_voting_thresholds",
                )
            )
            if not has_thresholds:
                warnings.append("lender_classes_and_voting is present but has no voting thresholds or majority definitions")

        if amendments:
            has_threshold = any(
                amendments.get(key)
                for key in (
                    "general_consent_threshold",
                    "all_lender_matters",
                    "majority_lender_matters",
                    "affected_lender_matters",
                    "agent_discretion_matters",
                )
            )
            if not has_threshold:
                warnings.append("amendments_and_waivers is present but no consent threshold mechanics are captured")

        if transfers:
            assignment_permitted = transfers.get("assignment_permitted")
            transfer_permitted = transfers.get("transfer_permitted")
            if assignment_permitted is False and transfer_permitted is False:
                warnings.append("both assignment and transfer are marked false; confirm this is source-supported")
            minimum_amount = transfers.get("minimum_transfer_amount")
            if isinstance(minimum_amount, (int, float)) and minimum_amount < 0:
                errors.append("minimum_transfer_amount must not be negative")
            if minimum_amount is not None and not transfers.get("minimum_transfer_currency"):
                warnings.append("minimum_transfer_amount is present without minimum_transfer_currency")

        if errors:
            return ("FAIL", "; ".join(errors + warnings))
        if warnings:
            return ("WARN", "; ".join(warnings))
        return ("PASS", "")
