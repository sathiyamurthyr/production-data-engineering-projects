"""Unit tests for the GitOps Concepts pattern."""

import pytest

from src.gitops import Gitops, GitopsConfig


class TestGitopsConfig:
    """Tests for GitopsConfig."""

    def test_default_config(self) -> None:
        config = GitopsConfig()
        assert config.pattern_name == "gitops"


class TestGitops:
    """Tests for Gitops."""

    def test_init_default_config(self) -> None:
        pattern = Gitops()
        assert pattern.config.pattern_name == "gitops"

    def test_init_custom_config(self) -> None:
        config = GitopsConfig()
        pattern = Gitops(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Gitops()
        result = pattern.execute("test_data")
        assert result == "test_data"
