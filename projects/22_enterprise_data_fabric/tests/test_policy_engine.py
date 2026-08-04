"""Tests for Policy Engine."""

import pytest

from platform.policies.models import Policy, Rule, Action, PolicyViolation
from platform.policies.engine import PolicyEngine


@pytest.fixture
def policy_engine():
    """Create a test policy engine."""
    return PolicyEngine()


def test_add_policy(policy_engine):
    """Test adding a policy."""
    policy = Policy(
        name="test_policy",
        description="Test policy",
        rules=[
            Rule(
                name="test_rule",
                condition="sensitivity == 'PII'",
                action=Action.ALERT,
            )
        ],
    )
    
    policy_engine.add_policy(policy)
    assert len(policy_engine.policies) == 1


def test_evaluate_asset_with_violation(policy_engine):
    """Test evaluating an asset that violates policy."""
    policy = Policy(
        name="pii_policy",
        description="PII detection policy",
        rules=[
            Rule(
                name="pii_check",
                condition="sensitivity in ['PII', 'PHI']",
                action=Action.ALERT,
            )
        ],
    )
    policy_engine.add_policy(policy)
    
    asset = {
        "id": "test_asset",
        "name": "customer_data",
        "sensitivity": "PII",
    }
    
    violations = policy_engine.evaluate_asset(asset)
    assert len(violations) == 1
    assert violations[0].policy_id == "pii_policy"


def test_evaluate_asset_without_violation(policy_engine):
    """Test evaluating an asset that doesn't violate policy."""
    policy = Policy(
        name="pii_policy",
        description="PII detection policy",
        rules=[
            Rule(
                name="pii_check",
                condition="sensitivity in ['PII', 'PHI']",
                action=Action.ALERT,
            )
        ],
    )
    policy_engine.add_policy(policy)
    
    asset = {
        "id": "test_asset",
        "name": "public_data",
        "sensitivity": "PUBLIC",
    }
    
    violations = policy_engine.evaluate_asset(asset)
    assert len(violations) == 0


def test_disabled_policy_not_evaluated(policy_engine):
    """Test that disabled policies are not evaluated."""
    policy = Policy(
        name="disabled_policy",
        description="Disabled policy",
        enabled=False,
        rules=[
            Rule(
                name="test_rule",
                condition="sensitivity == 'PII'",
                action=Action.ALERT,
            )
        ],
    )
    policy_engine.add_policy(policy)
    
    asset = {
        "id": "test_asset",
        "sensitivity": "PII",
    }
    
    violations = policy_engine.evaluate_asset(asset)
    assert len(violations) == 0


def test_policy_report(policy_engine):
    """Test policy compliance report."""
    policy1 = Policy(
        name="policy1",
        description="First policy",
        rules=[],
    )
    policy2 = Policy(
        name="policy2",
        description="Second policy",
        enabled=False,
        rules=[],
    )
    
    policy_engine.add_policy(policy1)
    policy_engine.add_policy(policy2)
    
    report = policy_engine.get_policy_report()
    assert report["total_policies"] == 2
    assert report["active_policies"] == 1
    assert report["total_violations"] == 0
    assert report["unresolved_violations"] == 0