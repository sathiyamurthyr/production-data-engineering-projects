"""Policy engine for rule-based policy enforcement."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from shared.utils.helpers import utc_now_iso

class PolicyEffect(Enum):
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"

@dataclass
class Policy:
    name: str
    description: str = ""
    effect: PolicyEffect = PolicyEffect.ALLOW
    conditions: list = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    priority: int = 0
    enabled: bool = True

@dataclass
class PolicyDecision:
    policy_name: str
    effect: PolicyEffect
    matched: bool
    reason: str = ""
    timestamp: str = field(default_factory=utc_now_iso)

class PolicyEngine:
    def __init__(self, default_effect: PolicyEffect = PolicyEffect.DENY) -> None:
        self._policies: list[Policy] = []
        self.default_effect = default_effect
        self._decisions: list[PolicyDecision] = []
    def add_policy(self, policy: Policy) -> None:
        self._policies.append(policy)
        self._policies.sort(key=lambda p: p.priority, reverse=True)
    def evaluate(self, action: str, resource: str, context: dict[str, Any] | None = None) -> PolicyDecision:
        ctx = context or {}
        for policy in self._policies:
            if not policy.enabled: continue
            if policy.actions and action not in policy.actions: continue
            if policy.resources and resource not in policy.resources: continue
            if all(cond(ctx) for cond in policy.conditions):
                d = PolicyDecision(policy_name=policy.name, effect=policy.effect, matched=True, reason=f"Policy '{policy.name}' matched")
                self._decisions.append(d)
                return d
        d = PolicyDecision(policy_name="default", effect=self.default_effect, matched=False, reason="No matching policy")
        self._decisions.append(d)
        return d
    def get_decisions(self) -> list[PolicyDecision]:
        return list(self._decisions)

