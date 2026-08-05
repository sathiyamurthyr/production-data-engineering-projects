"""Unit tests for the Infrastructure as Code pattern."""

import pytest

from src.infrastructure_as_code import InfrastructureAsCode, InfrastructureAsCodeConfig


class TestInfrastructureAsCodeConfig:
    """Tests for InfrastructureAsCodeConfig."""

    def test_default_config(self) -> None:
        config = InfrastructureAsCodeConfig()
        assert config.pattern_name == "infrastructure-as-code"


class TestInfrastructureAsCode:
    """Tests for InfrastructureAsCode."""

    def test_init_default_config(self) -> None:
        pattern = InfrastructureAsCode()
        assert pattern.config.pattern_name == "infrastructure-as-code"

    def test_init_custom_config(self) -> None:
        config = InfrastructureAsCodeConfig()
        pattern = InfrastructureAsCode(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = InfrastructureAsCode()
        result = pattern.execute("test_data")
        assert result == "test_data"
