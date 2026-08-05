"""Unit tests for the ELT with Stored Procedures pattern."""

import pytest

from src.stored_procedures import StoredProcedures, StoredProceduresConfig


class TestStoredProceduresConfig:
    """Tests for StoredProceduresConfig."""

    def test_default_config(self) -> None:
        config = StoredProceduresConfig()
        assert config.pattern_name == "stored-procedures"


class TestStoredProcedures:
    """Tests for StoredProcedures."""

    def test_init_default_config(self) -> None:
        pattern = StoredProcedures()
        assert pattern.config.pattern_name == "stored-procedures"

    def test_init_custom_config(self) -> None:
        config = StoredProceduresConfig()
        pattern = StoredProcedures(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = StoredProcedures()
        result = pattern.execute("test_data")
        assert result == "test_data"
