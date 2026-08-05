"""Unit tests for the Domain Driven Design pattern."""

import pytest

from src.domain_driven_design import DomainDrivenDesign, DomainDrivenDesignConfig


class TestDomainDrivenDesignConfig:
    """Tests for DomainDrivenDesignConfig."""

    def test_default_config(self) -> None:
        config = DomainDrivenDesignConfig()
        assert config.pattern_name == "domain-driven-design"


class TestDomainDrivenDesign:
    """Tests for DomainDrivenDesign."""

    def test_init_default_config(self) -> None:
        pattern = DomainDrivenDesign()
        assert pattern.config.pattern_name == "domain-driven-design"

    def test_init_custom_config(self) -> None:
        config = DomainDrivenDesignConfig()
        pattern = DomainDrivenDesign(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DomainDrivenDesign()
        result = pattern.execute("test_data")
        assert result == "test_data"
