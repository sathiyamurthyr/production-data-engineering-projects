"""Unit tests for the Workflows pattern."""

import pytest

from src.workflows import Workflows, WorkflowsConfig


class TestWorkflowsConfig:
    """Tests for WorkflowsConfig."""

    def test_default_config(self) -> None:
        config = WorkflowsConfig()
        assert config.pattern_name == "workflows"


class TestWorkflows:
    """Tests for Workflows."""

    def test_init_default_config(self) -> None:
        pattern = Workflows()
        assert pattern.config.pattern_name == "workflows"

    def test_init_custom_config(self) -> None:
        config = WorkflowsConfig()
        pattern = Workflows(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Workflows()
        result = pattern.execute("test_data")
        assert result == "test_data"
