"""Unit tests for the Encryption pattern."""

import pytest

from src.encryption import Encryption, EncryptionConfig


class TestEncryptionConfig:
    """Tests for EncryptionConfig."""

    def test_default_config(self) -> None:
        config = EncryptionConfig()
        assert config.pattern_name == "encryption"


class TestEncryption:
    """Tests for Encryption."""

    def test_init_default_config(self) -> None:
        pattern = Encryption()
        assert pattern.config.pattern_name == "encryption"

    def test_init_custom_config(self) -> None:
        config = EncryptionConfig()
        pattern = Encryption(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Encryption()
        result = pattern.execute("test_data")
        assert result == "test_data"
