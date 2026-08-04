"""Data Mesh Governance Engine."""

from collections.abc import Sequence
from typing import Any

from .policy import DataPolicy, EnforcementMode, PolicyViolation
from .validator import PolicyValidator


class GovernanceEngine:
    """Main governance engine for policy enforcement."""

    def __init__(self) -> None:
        self._policies: dict[str, DataPolicy] = {}
        self._violations: list[PolicyViolation] = []

    def add_policy(self, policy: DataPolicy) -> None:
        """Add a policy to the engine."""
        key = f"{policy.domain}.{policy.id}"
        self._policies[key] = policy

    def get_policies_for_domain(self, domain: str) -> list[DataPolicy]:
        """Get all policies applicable to a domain."""
        domain_policies = [p for p in self._policies.values() if p.domain in ("*", domain)]
        return list(domain_policies)

    def enforce_policies(
        self,
        product: dict[str, Any],
        domain: str,
    ) -> list[PolicyViolation]:
        """Enforce all applicable policies against a product."""
        policies = self.get_policies_for_domain(domain)
        violations: list[PolicyViolation] = []

        for policy in policies:
            violation = policy.validate(product)
            if violation:
                violations.append(violation)
                self._handle_violation(violation, policy.enforcement)

        self._violations.extend(violations)
        return violations

    def _handle_violation(
        self,
        violation: PolicyViolation,
        enforcement: EnforcementMode,
    ) -> None:
        """Handle a policy violation based on enforcement mode."""
        if enforcement == EnforcementMode.PREVENT:
            raise ValueError(f"Policy violation: {violation.message}")
        if enforcement == EnforcementMode.ALERT:
            self._send_alert(violation)

    def _send_alert(self, violation: PolicyViolation) -> None:
        """Send alert for policy violation (placeholder)."""
        print(f"ALERT: {violation.message}")  # noqa: T201

    def get_violations(
        self,
        domain: str | None = None,
        resolved: bool = False,
    ) -> Sequence[PolicyViolation]:
        """Get violations, optionally filtered by domain."""
        violations = [v for v in self._violations if v.resolved == resolved]
        if domain:
            violations = [v for v in violations if v.domain == domain]
        return violations

    def resolve_violation(self, violation_id: str) -> bool:
        """Mark a violation as resolved."""
        for v in self._violations:
            if f"{v.policy_id}.{v.product}" == violation_id:
                v.resolved = True
                return True
        return False


# Global governance engine instance
_engine: GovernanceEngine | None = None


def get_governance_engine() -> GovernanceEngine:
    """Get or create the global governance engine."""
    global _engine
    if _engine is None:
        _engine = GovernanceEngine()
    return _engine


def enforce_governance(product: dict[str, Any], domain: str) -> bool:
    """Convenience function to enforce governance."""
    engine = get_governance_engine()
    violations = engine.enforce_policies(product, domain)
    return len(violations) == 0