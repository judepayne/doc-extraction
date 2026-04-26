"""
Rule deal 006 v1: Security, intercreditor and collateral consistency.

Checks that deal-level security fields and optional security mechanics do not
contradict each other.
"""

from typing import Tuple

from rules.base import ValidationRule


class Rule(ValidationRule):
    """Checks deal security and intercreditor consistency."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "deal"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "Deal security, intercreditor, and collateral fields must be internally consistent"

    def set_required_data(self, data: dict) -> None:
        """Receive required data before execution."""
        pass

    def run(self) -> Tuple[str, str]:
        """Execute security/intercreditor checks."""
        data = self.entity._data
        core = data.get("core", {})
        optional = data.get("optional_blocks", {})
        finance_parties = core.get("finance_parties", {})
        security = optional.get("security_and_guarantees") or {}
        intercreditor = (
            optional.get("intercreditor_and_subordination")
            or security.get("intercreditor_and_subordination")
            or {}
        )
        collateral = (
            optional.get("collateral_perfection_timetable")
            or security.get("collateral_perfection_timetable")
            or {}
        )
        errors = []
        warnings = []

        secured = security.get("secured")
        assets = security.get("assets") or []
        guarantors = security.get("guarantors") or []
        security_agent = finance_parties.get("security_agent_or_trustee") or security.get("security_agent_or_trustee")
        perfection_required = collateral.get("perfection_required")
        perfection_steps = (
            collateral.get("all_steps")
            or collateral.get("initial_cp_steps")
            or collateral.get("post_closing_steps")
            or []
        )

        if secured is True:
            if not security_agent:
                warnings.append("secured deal should identify a security agent or security trustee where available")
            if not (assets or guarantors or perfection_steps or security.get("security_documents")):
                errors.append("secured deal requires security assets, guarantors, security documents, or perfection steps")
        elif secured is False:
            if assets or perfection_steps or perfection_required is True:
                errors.append("unsecured deal should not include security assets or collateral perfection requirements")

        if perfection_required is True and secured is False:
            errors.append("collateral_perfection_timetable.perfection_required conflicts with secured false")

        if intercreditor.get("intercreditor_agreement_required") is True:
            if not intercreditor.get("intercreditor_agreement_ref"):
                warnings.append("intercreditor agreement is required but no reference is captured")
            if not intercreditor.get("creditor_classes"):
                warnings.append("intercreditor mechanics should identify creditor classes where available")

        if errors:
            return ("FAIL", "; ".join(errors + warnings))
        if warnings:
            return ("WARN", "; ".join(warnings))
        return ("PASS", "")
