"""Unit tests for the Business Glossary pattern."""

import pytest

from src.business_glossary import BusinessGlossary, BusinessGlossaryConfig


class TestBusinessGlossaryConfig:
    """Tests for BusinessGlossaryConfig."""

    def test_default_config(self) -> None:
        config = BusinessGlossaryConfig()
        assert config.pattern_name == "business-glossary"


class TestBusinessGlossary:
    """Tests for BusinessGlossary."""

    def test_init_default_config(self) -> None:
        pattern = BusinessGlossary()
        assert pattern.config.pattern_name == "business-glossary"

    def test_init_custom_config(self) -> None:
        config = BusinessGlossaryConfig()
        pattern = BusinessGlossary(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = BusinessGlossary()
        result = pattern.execute("test_data")
        assert result == "test_data"
