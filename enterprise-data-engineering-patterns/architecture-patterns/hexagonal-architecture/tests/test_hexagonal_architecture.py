"""Unit tests for the Hexagonal Architecture pattern."""

import pytest

from src.hexagonal_architecture import HexagonalArchitecture, HexagonalArchitectureConfig


class TestHexagonalArchitectureConfig:
    """Tests for HexagonalArchitectureConfig."""

    def test_default_config(self) -> None:
        config = HexagonalArchitectureConfig()
        assert config.pattern_name == "hexagonal-architecture"


class TestHexagonalArchitecture:
    """Tests for HexagonalArchitecture."""

    def test_init_default_config(self) -> None:
        pattern = HexagonalArchitecture()
        assert pattern.config.pattern_name == "hexagonal-architecture"

    def test_init_custom_config(self) -> None:
        config = HexagonalArchitectureConfig()
        pattern = HexagonalArchitecture(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = HexagonalArchitecture()
        result = pattern.execute("test_data")
        assert result == "test_data"
