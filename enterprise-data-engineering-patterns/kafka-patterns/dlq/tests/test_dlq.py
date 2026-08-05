"""Unit tests for the Dead Letter Queue pattern."""

import pytest

from src.dlq import Dlq, DlqConfig


class TestDlqConfig:
    """Tests for DlqConfig."""

    def test_default_config(self) -> None:
        config = DlqConfig()
        assert config.pattern_name == "dlq"


class TestDlq:
    """Tests for Dlq."""

    def test_init_default_config(self) -> None:
        pattern = Dlq()
        assert pattern.config.pattern_name == "dlq"

    def test_init_custom_config(self) -> None:
        config = DlqConfig()
        pattern = Dlq(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Dlq()
        result = pattern.execute("test_data")
        assert result == "test_data"
