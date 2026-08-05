"""Unit tests for the Self-Service Provisioning pattern."""

import pytest

from src.self_service_provisioning import SelfServiceProvisioning, SelfServiceProvisioningConfig


class TestSelfServiceProvisioningConfig:
    """Tests for SelfServiceProvisioningConfig."""

    def test_default_config(self) -> None:
        config = SelfServiceProvisioningConfig()
        assert config.pattern_name == "self-service-provisioning"


class TestSelfServiceProvisioning:
    """Tests for SelfServiceProvisioning."""

    def test_init_default_config(self) -> None:
        pattern = SelfServiceProvisioning()
        assert pattern.config.pattern_name == "self-service-provisioning"

    def test_init_custom_config(self) -> None:
        config = SelfServiceProvisioningConfig()
        pattern = SelfServiceProvisioning(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = SelfServiceProvisioning()
        result = pattern.execute("test_data")
        assert result == "test_data"
