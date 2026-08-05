"""Unit tests for the Agent Orchestration pattern."""

import pytest

from src.agent_orchestration import AgentOrchestration, AgentOrchestrationConfig


class TestAgentOrchestrationConfig:
    """Tests for AgentOrchestrationConfig."""

    def test_default_config(self) -> None:
        config = AgentOrchestrationConfig()
        assert config.pattern_name == "agent-orchestration"


class TestAgentOrchestration:
    """Tests for AgentOrchestration."""

    def test_init_default_config(self) -> None:
        pattern = AgentOrchestration()
        assert pattern.config.pattern_name == "agent-orchestration"

    def test_init_custom_config(self) -> None:
        config = AgentOrchestrationConfig()
        pattern = AgentOrchestration(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = AgentOrchestration()
        result = pattern.execute("test_data")
        assert result == "test_data"
