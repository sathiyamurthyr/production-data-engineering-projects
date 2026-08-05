"""Unit tests for the Checkpointing pattern."""

import pytest

from src.checkpointing import Checkpointing, CheckpointingConfig


class TestCheckpointingConfig:
    """Tests for CheckpointingConfig."""

    def test_default_config(self) -> None:
        config = CheckpointingConfig()
        assert config.pattern_name == "checkpointing"


class TestCheckpointing:
    """Tests for Checkpointing."""

    def test_init_default_config(self) -> None:
        pattern = Checkpointing()
        assert pattern.config.pattern_name == "checkpointing"

    def test_init_custom_config(self) -> None:
        config = CheckpointingConfig()
        pattern = Checkpointing(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Checkpointing()
        result = pattern.execute("test_data")
        assert result == "test_data"
