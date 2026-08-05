"""Unit tests for the File Drop pattern."""

import pytest

from src.file_drop import FileDrop, FileDropConfig


class TestFileDropConfig:
    """Tests for FileDropConfig."""

    def test_default_config(self) -> None:
        config = FileDropConfig()
        assert config.pattern_name == "file-drop"


class TestFileDrop:
    """Tests for FileDrop."""

    def test_init_default_config(self) -> None:
        pattern = FileDrop()
        assert pattern.config.pattern_name == "file-drop"

    def test_init_custom_config(self) -> None:
        config = FileDropConfig()
        pattern = FileDrop(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = FileDrop()
        result = pattern.execute("test_data")
        assert result == "test_data"
