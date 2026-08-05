"""Unit tests for the Incident Response pattern."""

import pytest

from src.incident_response_sre import IncidentResponseSre, IncidentResponseSreConfig


class TestIncidentResponseSreConfig:
    """Tests for IncidentResponseSreConfig."""

    def test_default_config(self) -> None:
        config = IncidentResponseSreConfig()
        assert config.pattern_name == "incident-response-sre"


class TestIncidentResponseSre:
    """Tests for IncidentResponseSre."""

    def test_init_default_config(self) -> None:
        pattern = IncidentResponseSre()
        assert pattern.config.pattern_name == "incident-response-sre"

    def test_init_custom_config(self) -> None:
        config = IncidentResponseSreConfig()
        pattern = IncidentResponseSre(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = IncidentResponseSre()
        result = pattern.execute("test_data")
        assert result == "test_data"
