"""Unit tests for the Policy Enforcement pattern."""

import pytest

from src.policy_enforcement import PolicyEnforcement, PolicyEnforcementConfig


class TestPolicyEnforcementConfig:
    """Tests for PolicyEnforcementConfig."""

    def test_default_config(self) -> None:
        config = PolicyEnforcementConfig()
        assert config.pattern_name == "policy-enforcement"


class TestPolicyEnforcement:
    """Tests for PolicyEnforcement."""

    def test_init_default_config(self) -> None:
        pattern = PolicyEnforcement()
        assert pattern.config.pattern_name == "policy-enforcement"

    def test_init_custom_config(self) -> None:
        config = PolicyEnforcementConfig()
        pattern = PolicyEnforcement(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = PolicyEnforcement()
        result = pattern.execute("test_data")
        assert result == "test_data"
