"""Policy Engine - Evaluate and enforce governance policies."""

from typing import Any

from .models import Policy, Action, PolicyViolation


class PolicyEngine:
    """Evaluate policies against assets."""

    def __init__(self) -> None:
        """Initialize policy engine."""
        self.policies: list[Policy] = []
        self.violations: list[PolicyViolation] = []

    def add_policy(self, policy: Policy) -> None:
        """Add a policy to the engine."""
        self.policies.append(policy)

    def evaluate_asset(self, asset: dict[str, Any]) -> list[PolicyViolation]:
        """Evaluate all policies against an asset."""
        violations = []
        for policy in self.policies:
            if not policy.enabled:
                continue
            for rule in policy.rules:
                if self._evaluate_condition(rule.condition, asset):
                    violation = PolicyViolation(
                        policy_id=policy.id,
                        asset_id=asset.get("id", ""),
                        rule_condition=rule.condition,
                        action_taken=rule.action,
                    )
                    violations.append(violation)
                    self.violations.append(violation)
        return violations

    def _evaluate_condition(self, condition: str, asset: dict[str, Any]) -> bool:
        """Evaluate a condition against an asset."""
        # Simplified condition evaluation
        # In production, use expression evaluation library
        if "sensitivity" in condition.lower() and "pii" in condition.lower():
            return asset.get("sensitivity") in ["PII", "PHI"]
        return False

    def get_policy_report(self) -> dict[str, Any]:
        """Generate policy compliance report."""
        return {
            "total_policies": len(self.policies),
            "active_policies": len([p for p in self.policies if p.enabled]),
            "total_violations": len(self.violations),
            "unresolved_violations": len([v for v in self.violations if not v.resolved]),
        }