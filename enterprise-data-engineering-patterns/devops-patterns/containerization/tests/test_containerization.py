"""Unit tests for the Containerization pattern."""

import pytest

from src.containerization import Containerization, ContainerizationConfig


class TestContainerizationConfig:
    """Tests for ContainerizationConfig."""

    def test_default_config(self) -> None:
        config = ContainerizationConfig()
        assert config.pattern_name == "containerization"


class TestContainerization:
    """Tests for Containerization."""

    def test_init_default_config(self) -> None:
        pattern = Containerization()
        assert pattern.config.pattern_name == "containerization"

    def test_init_custom_config(self) -> None:
        config = ContainerizationConfig()
        pattern = Containerization(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Containerization()
        result = pattern.execute("test_data")
        assert result == "test_data"
