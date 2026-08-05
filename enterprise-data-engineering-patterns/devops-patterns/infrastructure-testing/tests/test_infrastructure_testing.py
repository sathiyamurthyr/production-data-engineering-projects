"""Unit tests for the Infrastructure Testing pattern."""

import pytest

from src.infrastructure_testing import InfrastructureTesting, InfrastructureTestingConfig


class TestInfrastructureTestingConfig:
    """Tests for InfrastructureTestingConfig."""

    def test_default_config(self) -> None:
        config = InfrastructureTestingConfig()
        assert config.pattern_name == "infrastructure-testing"


class TestInfrastructureTesting:
    """Tests for InfrastructureTesting."""

    def test_init_default_config(self) -> None:
        pattern = InfrastructureTesting()
        assert pattern.config.pattern_name == "infrastructure-testing"

    def test_init_custom_config(self) -> None:
        config = InfrastructureTestingConfig()
        pattern = InfrastructureTesting(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = InfrastructureTesting()
        result = pattern.execute("test_data")
        assert result == "test_data"
