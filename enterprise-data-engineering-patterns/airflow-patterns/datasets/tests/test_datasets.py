"""Unit tests for the Datasets pattern."""

import pytest

from src.datasets import Datasets, DatasetsConfig


class TestDatasetsConfig:
    """Tests for DatasetsConfig."""

    def test_default_config(self) -> None:
        config = DatasetsConfig()
        assert config.pattern_name == "datasets"


class TestDatasets:
    """Tests for Datasets."""

    def test_init_default_config(self) -> None:
        pattern = Datasets()
        assert pattern.config.pattern_name == "datasets"

    def test_init_custom_config(self) -> None:
        config = DatasetsConfig()
        pattern = Datasets(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Datasets()
        result = pattern.execute("test_data")
        assert result == "test_data"
