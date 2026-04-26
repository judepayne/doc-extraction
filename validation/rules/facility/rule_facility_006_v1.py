"""
Rule facility 006 v1: Security consistency.

Checks that security, guarantee and collateral fields do not contradict each
other and that secured facilities carry meaningful supporting detail.
"""

from typing import Tuple

from rules.base import ValidationRule


class Rule(ValidationRule):
    """Checks security and guarantee consistency."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "facility"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "Facility security and guarantee fields must be internally consistent"

    def set_required_data(self, data: dict) -> None:
        """Receive required data before execution."""
        pass

    def run(self) -> Tuple[str, str]:
        """Execute security consistency checks."""
        optional = self.entity._data.get("optional_blocks", {})
        security = optional.get("security_and_guarantees")
        collateral = optional.get("collateral_perfection") or {}
        if not security and not collateral:
            return ("PASS", "")
        security = security or {}

        errors = []
        warnings = []
        secured = security.get("secured")
        priority = security.get("priority")
        assets = security.get("assets") or []
        guarantors = security.get("guarantors") or []
        perfection_steps = (
            security.get("perfection_steps")
            or collateral.get("steps")
            or collateral.get("post_closing_obligations")
            or collateral.get("all_steps")
            or []
        )
        perfection_summary = (
            security.get("collateral_perfection_summary")
            or collateral.get("perfection_summary")
        )
        perfection_required = collateral.get("perfection_required")
        guarantee_type = security.get("guarantee_type")

        if secured is True:
            has_detail = bool(assets or guarantors or perfection_steps or perfection_summary)
            if not has_detail:
                errors.append("secured facility requires assets, guarantors, perfection steps, or a collateral summary")
            if priority == "unsecured":
                errors.append("secured facility cannot have priority 'unsecured'")
        elif secured is False:
            if assets or perfection_steps or perfection_required is True:
                errors.append("unsecured facility should not include security assets or perfection requirements")

        if priority == "unsecured" and (assets or perfection_steps or perfection_required is True):
            errors.append("priority 'unsecured' conflicts with security assets/perfection requirements")

        if guarantee_type and guarantee_type != "none" and not guarantors:
            warnings.append("guarantee_type is present but no guarantors are listed in security_and_guarantees")

        if perfection_required is True and secured is False:
            errors.append("collateral_perfection.perfection_required conflicts with secured false")

        if secured is True and not priority:
            warnings.append("secured facility should state security priority where available")

        if errors:
            return ("FAIL", "; ".join(errors + warnings))
        if warnings:
            return ("WARN", "; ".join(warnings))
        return ("PASS", "")
