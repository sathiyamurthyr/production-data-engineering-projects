"""Unit tests for the CDC with Dead Letter Queue pattern."""

import pytest

from src.cdc_dlq import CdcDlq, CdcDlqConfig


class TestCdcDlqConfig:
    """Tests for CdcDlqConfig."""

    def test_default_config(self) -> None:
        config = CdcDlqConfig()
        assert config.pattern_name == "cdc-dlq"


class TestCdcDlq:
    """Tests for CdcDlq."""

    def test_init_default_config(self) -> None:
        pattern = CdcDlq()
        assert pattern.config.pattern_name == "cdc-dlq"

    def test_init_custom_config(self) -> None:
        config = CdcDlqConfig()
        pattern = CdcDlq(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = CdcDlq()
        result = pattern.execute("test_data")
        assert result == "test_data"
