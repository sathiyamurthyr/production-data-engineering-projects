"""Unit tests for the CDC with Checkpointing pattern."""

import pytest

from src.cdc_checkpointing import CdcCheckpointing, CdcCheckpointingConfig


class TestCdcCheckpointingConfig:
    """Tests for CdcCheckpointingConfig."""

    def test_default_config(self) -> None:
        config = CdcCheckpointingConfig()
        assert config.pattern_name == "cdc-checkpointing"


class TestCdcCheckpointing:
    """Tests for CdcCheckpointing."""

    def test_init_default_config(self) -> None:
        pattern = CdcCheckpointing()
        assert pattern.config.pattern_name == "cdc-checkpointing"

    def test_init_custom_config(self) -> None:
        config = CdcCheckpointingConfig()
        pattern = CdcCheckpointing(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = CdcCheckpointing()
        result = pattern.execute("test_data")
        assert result == "test_data"
