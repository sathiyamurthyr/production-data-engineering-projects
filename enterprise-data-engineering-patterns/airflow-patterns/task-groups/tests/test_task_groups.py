"""Unit tests for the Task Groups pattern."""

import pytest

from src.task_groups import TaskGroups, TaskGroupsConfig


class TestTaskGroupsConfig:
    """Tests for TaskGroupsConfig."""

    def test_default_config(self) -> None:
        config = TaskGroupsConfig()
        assert config.pattern_name == "task-groups"


class TestTaskGroups:
    """Tests for TaskGroups."""

    def test_init_default_config(self) -> None:
        pattern = TaskGroups()
        assert pattern.config.pattern_name == "task-groups"

    def test_init_custom_config(self) -> None:
        config = TaskGroupsConfig()
        pattern = TaskGroups(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = TaskGroups()
        result = pattern.execute("test_data")
        assert result == "test_data"
